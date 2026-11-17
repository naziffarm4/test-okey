from __future__ import annotations

import base64
import hashlib
import os
import socket
import struct
import threading
import time
import urllib.parse
from typing import Any, Callable

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def _compute_ws_accept(sec_key: str) -> str:
    digest = hashlib.sha1((sec_key + WS_GUID).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def run_safe_tcp_probe(host: str = "sistem.okeymuhabbet.com", port: int = 4082, timeout: float = 5.0) -> dict[str, Any]:
    """
    Strictly passive transport-level reachability test (DNS + TCP 3-way handshake + immediate close).
    Transmits ZERO application bytes to honor Section 4 authorization rules.
    """
    t_dns = time.perf_counter()
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    dns_ms = (time.perf_counter() - t_dns) * 1000.0
    ips = sorted({item[4][0] for item in infos})

    t_tcp = time.perf_counter()
    with socket.create_connection((host, port), timeout=timeout) as sock:
        tcp_ms = (time.perf_counter() - t_tcp) * 1000.0
        remote_ip, remote_port = sock.getpeername()[:2]

    return {
        "host": host,
        "port": port,
        "dns_addresses": ips,
        "dns_duration_ms": round(dns_ms, 3),
        "tcp_connected": True,
        "remote_ip": remote_ip,
        "remote_port": remote_port,
        "tcp_handshake_ms": round(tcp_ms, 3),
        "app_bytes_sent": 0,
        "app_protocol_status": "ENGELLENDİ_NO_WRITTEN_AUTHORIZATION",
    }


class WebSocketClient:
    """Minimal RFC 6455 client for local Engine.IO v4 / Socket.IO v4 verification."""

    def __init__(self, timeout: float = 3.0) -> None:
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._rx_buf = bytearray()

    def connect(self, url: str, *, allow_non_local: bool = False) -> dict[str, Any]:
        parts = urllib.parse.urlsplit(url)
        host = (parts.hostname or "").lower()
        if not allow_non_local and host not in {"127.0.0.1", "localhost", "::1"}:
            raise PermissionError(
                f"Refusing application-level WebSocket handshake to non-local host '{host}' without written authorization."
            )
        port = parts.port or (443 if parts.scheme == "wss" else 80)
        path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")

        sec_key = base64.b64encode(os.urandom(16)).decode("ascii")
        t0 = time.perf_counter()
        sock = socket.create_connection((host, port), timeout=self.timeout)
        try:
            sock.settimeout(self.timeout)
            req = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}:{port}\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {sec_key}\r\n"
                "Sec-WebSocket-Version: 13\r\n\r\n"
            )
            sock.sendall(req.encode("ascii"))

            self._rx_buf.clear()
            while b"\r\n\r\n" not in self._rx_buf:
                chunk = sock.recv(4096)
                if not chunk:
                    raise ConnectionError("Connection closed before HTTP 101 Upgrade completed")
                self._rx_buf.extend(chunk)
        except Exception:
            sock.close()
            raise

        sep_idx = self._rx_buf.index(b"\r\n\r\n")
        raw_hdr = bytes(self._rx_buf[:sep_idx]).decode("iso-8859-1")
        del self._rx_buf[: sep_idx + 4]

        lines = raw_hdr.split("\r\n")
        status_parts = lines[0].split(" ", 2)
        status_code = int(status_parts[1]) if len(status_parts) >= 2 and status_parts[1].isdigit() else 0
        headers: dict[str, str] = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        expected_accept = _compute_ws_accept(sec_key)
        accept_valid = headers.get("sec-websocket-accept") == expected_accept
        if status_code != 101 or not accept_valid:
            sock.close()
            raise ConnectionError(f"WebSocket upgrade failed: status={status_code}, accept_valid={accept_valid}")

        self._sock = sock
        return {
            "status_code": status_code,
            "accept_valid": accept_valid,
            "headers": headers,
            "handshake_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    def connect_with_reconnect(
        self,
        url: str,
        *,
        max_attempts: int = 10,
        base_delay: float = 0.1,
        allow_non_local: bool = False,
    ) -> dict[str, Any]:
        last_error: str = ""
        for attempt in range(1, max_attempts + 1):
            try:
                hs = self.connect(url, allow_non_local=allow_non_local)
                return {"connected": True, "attempts": attempt, "handshake": hs}
            except (OSError, ConnectionError, TimeoutError) as exc:
                last_error = str(exc)
                if attempt < max_attempts:
                    time.sleep(base_delay * attempt)
        return {"connected": False, "attempts": max_attempts, "error": last_error}

    def _read_exact(self, n: int) -> bytes:
        assert self._sock is not None
        while len(self._rx_buf) < n:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionError("WebSocket stream closed unexpectedly")
            self._rx_buf.extend(chunk)
        out = bytes(self._rx_buf[:n])
        del self._rx_buf[:n]
        return out

    def send_frame(self, opcode: int, payload: bytes) -> None:
        if self._sock is None:
            raise ConnectionError("WebSocket is not connected")
        mask = os.urandom(4)
        header = bytearray([0x80 | (opcode & 0x0F)])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        header.extend(mask)
        masked = bytes(b ^ mask[i & 3] for i, b in enumerate(payload))
        self._sock.sendall(bytes(header) + masked)

    def send_text(self, text: str) -> None:
        self.send_frame(0x1, text.encode("utf-8"))

    def recv_text(self) -> str:
        while True:
            b0, b1 = self._read_exact(2)
            opcode = b0 & 0x0F
            masked = bool(b1 & 0x80)
            length = b1 & 0x7F
            if length == 126:
                (length,) = struct.unpack("!H", self._read_exact(2))
            elif length == 127:
                (length,) = struct.unpack("!Q", self._read_exact(8))
            mask_key = self._read_exact(4) if masked else b""
            payload = self._read_exact(length)
            if masked:
                payload = bytes(b ^ mask_key[i & 3] for i, b in enumerate(payload))

            if opcode == 0x1:
                return payload.decode("utf-8")
            if opcode == 0x9:
                self.send_frame(0xA, payload)
                continue
            if opcode == 0x8:
                raise ConnectionError("WebSocket closed by peer")

    def close(self) -> None:
        if self._sock is not None:
            try:
                self.send_frame(0x8, struct.pack("!H", 1000))
            except OSError:
                pass
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None


class LocalEngineIOWebSocketServer:
    """Local RFC 6455 + Engine.IO v4 test server."""

    def __init__(
        self,
        *,
        drop_first_connection: bool = False,
        on_client_text: Callable[[LocalEngineIOWebSocketServer, str], None] | None = None,
    ) -> None:
        self.drop_first_connection = drop_first_connection
        self.on_client_text = on_client_text
        self._listen_sock: socket.socket | None = None
        self._accept_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._pong_event = threading.Event()
        self._conn_count = 0
        self._last_client: socket.socket | None = None
        self._send_lock = threading.Lock()
        self.port: int = 0

    def __enter__(self) -> LocalEngineIOWebSocketServer:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        srv.listen(8)
        srv.settimeout(0.2)
        self.port = int(srv.getsockname()[1])
        self._listen_sock = srv
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self._stop_event.set()
        if self._last_client is not None:
            try:
                self._last_client.close()
            except OSError:
                pass
        if self._listen_sock is not None:
            try:
                self._listen_sock.close()
            except OSError:
                pass
        if self._accept_thread is not None:
            self._accept_thread.join(timeout=2.0)

    def _accept_loop(self) -> None:
        assert self._listen_sock is not None
        while not self._stop_event.is_set():
            try:
                conn, _ = self._listen_sock.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            self._conn_count += 1
            if self.drop_first_connection and self._conn_count == 1:
                conn.close()
                continue
            threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()

    def _handle_client(self, conn: socket.socket) -> None:
        conn.settimeout(2.0)
        buf = bytearray()
        try:
            while b"\r\n\r\n" not in buf:
                chunk = conn.recv(4096)
                if not chunk:
                    conn.close()
                    return
                buf.extend(chunk)
            sep = buf.index(b"\r\n\r\n")
            hdr_text = bytes(buf[:sep]).decode("iso-8859-1")
            del buf[: sep + 4]

            sec_key = ""
            for line in hdr_text.split("\r\n")[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    if k.strip().lower() == "sec-websocket-key":
                        sec_key = v.strip()
            accept_val = _compute_ws_accept(sec_key)
            resp = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept_val}\r\n\r\n"
            )
            conn.sendall(resp.encode("ascii"))
            self._last_client = conn

            self.send_text_to_last_client(
                '0{"sid":"eio_mock_01","upgrades":[],"pingInterval":25000,"pingTimeout":20000}'
            )

            while not self._stop_event.is_set():
                frame = self._recv_ws_frame(conn, buf)
                if frame is None:
                    break
                opcode, payload = frame
                if opcode == 0x8:
                    break
                if opcode == 0x1:
                    text = payload.decode("utf-8")
                    if text == "3":
                        self._pong_event.set()
                    if self.on_client_text is not None:
                        self.on_client_text(self, text)
        except (OSError, TimeoutError):
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    @staticmethod
    def _recv_ws_frame(conn: socket.socket, buf: bytearray) -> tuple[int, bytes] | None:
        def read_n(n: int) -> bytes | None:
            while len(buf) < n:
                try:
                    chunk = conn.recv(4096)
                except TimeoutError:
                    continue
                if not chunk:
                    return None
                buf.extend(chunk)
            out = bytes(buf[:n])
            del buf[:n]
            return out

        hdr = read_n(2)
        if hdr is None:
            return None
        b0, b1 = hdr
        opcode = b0 & 0x0F
        masked = bool(b1 & 0x80)
        length = b1 & 0x7F
        if length == 126:
            ext = read_n(2)
            if ext is None:
                return None
            (length,) = struct.unpack("!H", ext)
        elif length == 127:
            ext = read_n(8)
            if ext is None:
                return None
            (length,) = struct.unpack("!Q", ext)
        mask_key = read_n(4) if masked else b""
        if masked and mask_key is None:
            return None
        payload = read_n(length)
        if payload is None:
            return None
        if masked:
            payload = bytes(b ^ mask_key[i & 3] for i, b in enumerate(payload))
        return opcode, payload

    def send_text_to_last_client(self, text: str) -> None:
        if self._last_client is None:
            return
        data = text.encode("utf-8")
        frame = bytearray([0x81])
        if len(data) < 126:
            frame.append(len(data))
        elif len(data) < 65536:
            frame.append(126)
            frame.extend(struct.pack("!H", len(data)))
        else:
            frame.append(127)
            frame.extend(struct.pack("!Q", len(data)))
        frame.extend(data)
        with self._send_lock:
            self._last_client.sendall(bytes(frame))

    def send_ping_to_last_client(self) -> None:
        self._pong_event.clear()
        self.send_text_to_last_client("2")

    def wait_for_pong(self, timeout: float = 2.0) -> bool:
        return self._pong_event.wait(timeout=timeout)
