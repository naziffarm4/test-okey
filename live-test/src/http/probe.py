from __future__ import annotations

import hashlib
import json
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from src.diagnostics.recorder import sanitize_data


class CommandEnvelopeBuilder:
    @staticmethod
    def build_pre_auth(event_name: str, params: dict[str, Any]) -> dict[str, Any]:
        out = dict(params)
        out.pop("_i", None)
        out["_e"] = event_name
        return out

    @staticmethod
    def build_in_session(command_name: str, params: dict[str, Any], session_id: str) -> dict[str, Any]:
        out = dict(params)
        out.pop("_e", None)
        out["_i"] = command_name
        out["_t"] = session_id
        return out


class DuplicateGuard:
    """Matches SuWebRequest.Emit @ RVA 0x019C2C64: allows if hash differs or last_time + window < now."""

    def __init__(self, window_seconds: int = 1) -> None:
        self.window_seconds = window_seconds
        self._last_hash: str | None = None
        self._last_time: float = -1e9

    def allow(self, json_payload: str, now_sec: float | None = None) -> bool:
        now = time.time() if now_sec is None else float(now_sec)
        digest = hashlib.md5(json_payload.encode("utf-8")).hexdigest()
        if self._last_hash != digest or (self._last_time + self.window_seconds) < now:
            self._last_hash = digest
            self._last_time = now
            return True
        return False


def sign_payload(json_str: str, salt: str) -> str:
    return hashlib.md5((json_str + salt).encode("utf-8")).hexdigest()


def send_signed_command(
    *,
    base_url: str,
    payload: dict[str, Any],
    salt: str,
    session_id: str | None = None,
    timeout: float = 5.0,
    allow_non_local: bool = False,
) -> dict[str, Any]:
    parsed = urllib.parse.urlsplit(base_url)
    host = (parsed.hostname or "").lower()
    if not allow_non_local and host not in {"127.0.0.1", "localhost", "::1"}:
        raise PermissionError(
            f"Refusing to send signed application command to non-local host '{host}' without explicit authorization."
        )

    body_dict = dict(payload)
    if session_id is not None and "_e" not in body_dict:
        body_dict["_t"] = session_id

    json_str = json.dumps(body_dict, separators=(",", ":"), ensure_ascii=False)
    sig = sign_payload(json_str, salt)
    query = urllib.parse.urlencode({"h": sig, "d": json_str})
    full_url = urllib.parse.urlunsplit((parsed.scheme or "http", parsed.netloc, parsed.path or "/", query, ""))

    t0 = time.perf_counter()
    req = urllib.request.Request(full_url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            dt_ms = (time.perf_counter() - t0) * 1000.0
            parsed_json = json.loads(raw) if raw.strip().startswith("{") else None
            return {
                "status_code": resp.status,
                "duration_ms": round(dt_ms, 3),
                "raw": raw,
                "json": parsed_json,
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "status_code": exc.code,
            "duration_ms": round(dt_ms, 3),
            "raw": raw,
            "json": json.loads(raw) if raw.strip().startswith("{") else None,
        }


class LocalMockHttpServer:
    """Local mock of https://sistem.okeymuhabbet.com/?h=<md5>&d=<json> for safe offline verification."""

    def __init__(self, expected_salt: str = "SYNTHETIC_HTTP_16") -> None:
        self.expected_salt = expected_salt
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        assert self._server is not None
        return int(self._server.server_address[1])

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    def __enter__(self) -> LocalMockHttpServer:
        expected_salt = self.expected_salt

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                return

            def do_GET(self) -> None:
                qs = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(self.path).query, keep_blank_values=True))
                h_val = qs.get("h", "")
                d_val = qs.get("d", "")
                if not h_val or not d_val:
                    self._reply(400, {"error": "missing_h_or_d"})
                    return
                expected_h = sign_payload(d_val, expected_salt)
                if h_val != expected_h:
                    self._reply(403, {"error": "invalid_signature"})
                    return
                try:
                    cmd = json.loads(d_val)
                except ValueError:
                    self._reply(400, {"error": "invalid_json"})
                    return

                route = cmd.get("_e") or cmd.get("_i") or ""
                if route == "giris-misafir":
                    resp = {
                        "s": [
                            {
                                "i": "MisafirGirisi",
                                "d": {
                                    "id": "1001",
                                    "kullanici": "Misafir_1001",
                                    "token_id": "mock_tok_1001",
                                    "session_id": "mock_sess_1001",
                                },
                            }
                        ]
                    }
                elif route == "versiyonkontrol-versiyonkontrol":
                    resp = {"s": [{"i": "VersiyonOnay", "d": {"durum": 1, "versiyon": cmd.get("Versiyon", "3.1.33")}}]}
                elif route == "masaoyunbitir-oyunbitirbeta":
                    taslar_str = str(cmd.get("taslar", ""))
                    biten = str(cmd.get("bitentas", ""))
                    tokens = taslar_str.lstrip("-").split("-") if taslar_str.startswith("-") else []
                    occupied = [tok for tok in tokens if tok != "Bos"]
                    if len(tokens) == 28 and len(occupied) == 14 and len(set(occupied)) == 14 and biten and biten not in occupied:
                        resp = {
                            "s": [
                                {
                                    "i": "OyunBitir",
                                    "d": {
                                        "Baslik": "Okey İle Bitti (LOCAL_MOCK)",
                                        "BitenTas": biten,
                                        "CanakKirildi": "1",
                                        "Kazananlar": [{"id": "1001", "i": "MockOyuncu", "p": "400", "a": "1", "v": "0"}],
                                        "Taslar": tokens,
                                    },
                                }
                            ]
                        }
                    else:
                        resp = {
                            "s": [
                                {
                                    "i": "OyunBitirHata",
                                    "d": {"hata": [{"Per": 0, "Tip": "GecersizDizilim", "Taslar": occupied[:3]}]},
                                }
                            ]
                        }
                else:
                    resp = {"s": [{"i": "MockAck", "d": {"route": route, "ok": 1}}]}
                self._reply(200, resp)

            def _reply(self, code: int, obj: dict[str, Any]) -> None:
                body = json.dumps(obj, separators=(",", ":")).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)


def run_safe_production_http_probe(url: str = "https://sistem.okeymuhabbet.com/", timeout: float = 8.0) -> dict[str, Any]:
    """
    Strictly read-only, unauthenticated transport & root HTTP check.
    Sends NO '?h=' or '?d=' parameters, NO commands, NO tokens, NO fake IDs.
    """
    parts = urllib.parse.urlsplit(url)
    if parts.query:
        raise ValueError("Safe production probe refuses URLs containing query parameters.")
    host = parts.hostname or "sistem.okeymuhabbet.com"
    port = parts.port or (443 if parts.scheme == "https" else 80)

    result: dict[str, Any] = {
        "target_url": url,
        "host": host,
        "port": port,
        "dns": {},
        "tcp": {},
        "tls": {},
        "http_head": {},
        "http_get": {},
    }

    # 1. DNS Resolution
    t0 = time.perf_counter()
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    dns_ms = (time.perf_counter() - t0) * 1000.0
    ips = sorted({item[4][0] for item in infos})
    result["dns"] = {"resolved": bool(ips), "addresses": ips, "duration_ms": round(dns_ms, 3)}

    # 2. TCP Connect & 3. TLS Validation
    t_tcp = time.perf_counter()
    with socket.create_connection((host, port), timeout=timeout) as raw_sock:
        tcp_ms = (time.perf_counter() - t_tcp) * 1000.0
        remote_ip, remote_port = raw_sock.getpeername()[:2]
        result["tcp"] = {
            "connected": True,
            "remote_ip": remote_ip,
            "remote_port": remote_port,
            "duration_ms": round(tcp_ms, 3),
        }
        if parts.scheme == "https":
            ctx = ssl.create_default_context()
            t_tls = time.perf_counter()
            with ctx.wrap_socket(raw_sock, server_hostname=host) as tls_sock:
                tls_ms = (time.perf_counter() - t_tls) * 1000.0
                cert = tls_sock.getpeercert() or {}
                subject = {k: v for tup in cert.get("subject", ()) for k, v in tup}
                issuer = {k: v for tup in cert.get("issuer", ()) for k, v in tup}
                sans = [val for kind, val in cert.get("subjectAltName", ()) if kind == "DNS"]
                result["tls"] = {
                    "verified": True,
                    "protocol_version": tls_sock.version(),
                    "cipher": tls_sock.cipher(),
                    "subject": subject,
                    "issuer": issuer,
                    "not_before": cert.get("notBefore"),
                    "not_after": cert.get("notAfter"),
                    "san_dns": sans,
                    "duration_ms": round(tls_ms, 3),
                }

    # 4. Safe HEAD / and GET / (no query string, read-only)
    for method, key in (("HEAD", "http_head"), ("GET", "http_get")):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": "OkeyProtocolAudit/1.0 (ReadOnly)"})
        t_req = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body_bytes = resp.read(65536) if method == "GET" else b""
                req_ms = (time.perf_counter() - t_req) * 1000.0
                headers_dict = sanitize_data({k.lower(): v for k, v in resp.headers.items()})
                result[key] = _summarize_http_response(resp.status, headers_dict, body_bytes, req_ms)
        except urllib.error.HTTPError as exc:
            body_bytes = exc.read(65536) if method == "GET" else b""
            req_ms = (time.perf_counter() - t_req) * 1000.0
            headers_dict = sanitize_data({k.lower(): v for k, v in exc.headers.items()}) if exc.headers else {}
            result[key] = _summarize_http_response(exc.code, headers_dict, body_bytes, req_ms)

    return result


def _summarize_http_response(status: int, headers: dict[str, Any], body: bytes, duration_ms: float) -> dict[str, Any]:
    text = body.decode("utf-8", errors="replace").strip()
    if not body:
        structure = "empty_body"
    elif text.startswith("{") or text.startswith("["):
        try:
            parsed = json.loads(text)
            structure = f"json_{type(parsed).__name__}_keys={list(parsed.keys())[:10]}" if isinstance(parsed, dict) else "json_array"
        except ValueError:
            structure = "malformed_json_or_text"
    elif "<html" in text.lower() or "<!doctype html" in text.lower():
        structure = "html_document"
    else:
        structure = "plain_text_or_other"

    return {
        "status_code": status,
        "duration_ms": round(duration_ms, 3),
        "content_type": headers.get("content-type", ""),
        "headers": headers,
        "body_byte_length": len(body),
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "body_structure": structure,
        "body_safe_excerpt": text[:160] if len(text) <= 160 else text[:160] + "...[truncated]",
    }
