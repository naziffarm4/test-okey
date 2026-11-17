from __future__ import annotations

import json
import time
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Any

from src.http.probe import CommandEnvelopeBuilder, LocalMockHttpServer, send_signed_command
from src.websocket.handshake import LocalEngineIOWebSocketServer, WebSocketClient


class EngineIOPacketType(Enum):
    OPEN = "0"
    CLOSE = "1"
    PING = "2"
    PONG = "3"
    MESSAGE = "4"
    UPGRADE = "5"
    NOOP = "6"


@dataclass(frozen=True)
class EngineIOPacket:
    packet_type: EngineIOPacketType
    payload: str = ""

    @classmethod
    def parse_text(cls, raw: str) -> EngineIOPacket:
        if not raw:
            raise ValueError("Empty Engine.IO packet")
        return cls(packet_type=EngineIOPacketType(raw[0]), payload=raw[1:])

    def encode_text(self) -> str:
        return f"{self.packet_type.value}{self.payload}"


class SocketIOPacketType(IntEnum):
    CONNECT = 0
    DISCONNECT = 1
    EVENT = 2
    ACK = 3
    CONNECT_ERROR = 4


@dataclass
class SocketIOPacket:
    packet_type: SocketIOPacketType
    namespace: str = "/"
    event: str | None = None
    data: Any = None
    ack_id: int | None = None

    @staticmethod
    def validate_server_connect(pkt: SocketIOPacket) -> str:
        """Matches SocketIONamespace.Submit @ RVA 0x01ACA854: server CONNECT ack must carry sid."""
        if pkt.packet_type != SocketIOPacketType.CONNECT:
            raise ValueError(f"Expected CONNECT packet, got {pkt.packet_type}")
        if not isinstance(pkt.data, dict) or not pkt.data.get("sid"):
            raise ValueError("Server Socket.IO v4 CONNECT ack is missing required 'sid'")
        return str(pkt.data["sid"])


def encode_sio_packet(pkt: SocketIOPacket) -> str:
    parts = [str(int(pkt.packet_type))]
    if pkt.namespace and pkt.namespace != "/":
        parts.append(f"{pkt.namespace},")
    if pkt.ack_id is not None:
        parts.append(str(pkt.ack_id))

    if pkt.packet_type == SocketIOPacketType.EVENT:
        if not pkt.event:
            raise ValueError("EVENT packet requires event name")
        args = pkt.data if isinstance(pkt.data, list) else ([] if pkt.data is None else [pkt.data])
        parts.append(json.dumps([pkt.event, *args], separators=(",", ":"), ensure_ascii=False))
    elif pkt.data is not None:
        parts.append(json.dumps(pkt.data, separators=(",", ":"), ensure_ascii=False))

    return "".join(parts)


def decode_sio_packet(raw: str) -> SocketIOPacket:
    if not raw or not raw[0].isdigit():
        raise ValueError(f"Invalid Socket.IO packet: {raw!r}")
    ptype = SocketIOPacketType(int(raw[0]))
    idx = 1
    namespace = "/"

    if idx < len(raw) and raw[idx] == "/":
        comma = raw.find(",", idx)
        if comma == -1:
            return SocketIOPacket(packet_type=ptype, namespace=raw[idx:])
        namespace = raw[idx:comma]
        idx = comma + 1

    ack_digits = []
    while idx < len(raw) and raw[idx].isdigit():
        ack_digits.append(raw[idx])
        idx += 1
    ack_id = int("".join(ack_digits)) if ack_digits else None

    rem = raw[idx:]
    if not rem:
        return SocketIOPacket(packet_type=ptype, namespace=namespace, ack_id=ack_id)

    parsed = json.loads(rem)
    if ptype == SocketIOPacketType.EVENT:
        if not isinstance(parsed, list) or not parsed or not isinstance(parsed[0], str):
            raise ValueError("Socket.IO EVENT payload must be a non-empty JSON array starting with event name")
        return SocketIOPacket(
            packet_type=ptype,
            namespace=namespace,
            event=parsed[0],
            data=parsed[1:],
            ack_id=ack_id,
        )
    return SocketIOPacket(packet_type=ptype, namespace=namespace, data=parsed, ack_id=ack_id)


class LocalOkeyProtocolMockStack:
    """
    End-to-end local mock verifying Okey Muhabbet's dual-channel architecture:
    1) HTTPS-equivalent signed GET (?h=MD5&d=JSON) for commands
    2) Engine.IO v4 + Socket.IO v4 WebSocket push channel ('i' -> {"s":[{"i":...,"d":...}]})
    """

    def __init__(self) -> None:
        self.synthetic_http_salt = "SYNTHETIC_HTTP_16"
        self.synthetic_ws_secret = "SYN_WS_10C"
        self._http: LocalMockHttpServer | None = None
        self._ws: LocalEngineIOWebSocketServer | None = None
        self.server_received_disconnect = False

    def __enter__(self) -> LocalOkeyProtocolMockStack:
        self._http = LocalMockHttpServer(expected_salt=self.synthetic_http_salt).__enter__()
        self._ws = LocalEngineIOWebSocketServer(on_client_text=self._on_ws_client_text).__enter__()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._ws is not None:
            self._ws.__exit__(exc_type, exc, tb)
        if self._http is not None:
            self._http.__exit__(exc_type, exc, tb)

    def _on_ws_client_text(self, srv: LocalEngineIOWebSocketServer, raw_eio: str) -> None:
        eio = EngineIOPacket.parse_text(raw_eio)
        if eio.packet_type == EngineIOPacketType.PONG:
            # After Engine.IO pong, send app-level Socket.IO 'ping' (SuWebRequest @ RVA 0x019C5444)
            sio_ping = encode_sio_packet(SocketIOPacket(packet_type=SocketIOPacketType.EVENT, event="ping", data=[]))
            srv.send_text_to_last_client(f"4{sio_ping}")
            return

        if eio.packet_type != EngineIOPacketType.MESSAGE:
            return

        sio = decode_sio_packet(eio.payload)
        if sio.packet_type == SocketIOPacketType.CONNECT:
            if isinstance(sio.data, dict) and sio.data.get("id"):
                ack = encode_sio_packet(
                    SocketIOPacket(packet_type=SocketIOPacketType.CONNECT, data={"sid": "sio_ns_mock_01"})
                )
                srv.send_text_to_last_client(f"4{ack}")
                srv.send_ping_to_last_client()
            else:
                err = encode_sio_packet(
                    SocketIOPacket(packet_type=SocketIOPacketType.CONNECT_ERROR, data={"message": "missing_id"})
                )
                srv.send_text_to_last_client(f"4{err}")
        elif sio.packet_type == SocketIOPacketType.EVENT and sio.event == "pong":
            # Push game table state over unified 'i' envelope (OnSocketGelen -> Receive @ RVA 0x019C5614)
            envelope = json.dumps(
                {
                    "s": [
                        {
                            "i": "MasaTaslariGuncelle",
                            "d": {"mid": "21", "kt": "46", "ot": "4-k-4", "ok": "k-5", "ms": "1"},
                        }
                    ]
                },
                separators=(",", ":"),
            )
            push = encode_sio_packet(SocketIOPacket(packet_type=SocketIOPacketType.EVENT, event="i", data=[envelope]))
            srv.send_text_to_last_client(f"4{push}")
        elif sio.packet_type == SocketIOPacketType.DISCONNECT:
            self.server_received_disconnect = True

    def run_simulated_client_flow(self) -> dict[str, Any]:
        assert self._http is not None and self._ws is not None

        # Step 1: Guest login via signed HTTP GET
        login_cmd = CommandEnvelopeBuilder.build_pre_auth(
            "giris-misafir",
            {"token_id": "", "device_id": "sim-dev-01", "machash": "0123456789abcdef0123456789abcdef"},
        )
        http_res = send_signed_command(
            base_url=self._http.base_url,
            payload=login_cmd,
            salt=self.synthetic_http_salt,
        )
        login_item = http_res["json"]["s"][0]
        guest_login_ok = http_res["status_code"] == 200 and login_item["i"] == "MisafirGirisi"
        player_id = login_item["d"]["id"]

        # Step 2: Engine.IO v4 WebSocket connect
        ws = WebSocketClient(timeout=3.0)
        ws.connect(f"ws://127.0.0.1:{self._ws.port}/socket.io/?EIO=4&transport=websocket")
        try:
            eio_open = EngineIOPacket.parse_text(ws.recv_text())
            eio_open_ok = eio_open.packet_type == EngineIOPacketType.OPEN and "sid" in json.loads(eio_open.payload)

            # Step 3: Socket.IO v4 namespace '/' CONNECT with player id + synthetic handshake marker
            sio_auth = encode_sio_packet(
                SocketIOPacket(
                    packet_type=SocketIOPacketType.CONNECT,
                    namespace="/",
                    data={"id": player_id, "handshake_tag": self.synthetic_ws_secret},
                )
            )
            ws.send_text(f"4{sio_auth}")

            eio_conn_ack = EngineIOPacket.parse_text(ws.recv_text())
            sio_conn_ack = decode_sio_packet(eio_conn_ack.payload)
            ns_sid = SocketIOPacket.validate_server_connect(sio_conn_ack)
            sio_connect_ok = bool(ns_sid)

            # Step 4: Engine.IO ping ('2') -> client pong ('3') + Socket.IO 'ping' -> client 'pong'
            t_ping = time.perf_counter()
            eio_ping = EngineIOPacket.parse_text(ws.recv_text())
            assert eio_ping.packet_type == EngineIOPacketType.PING
            ws.send_text("3")

            sio_ping_frame = EngineIOPacket.parse_text(ws.recv_text())
            sio_ping_pkt = decode_sio_packet(sio_ping_frame.payload)
            assert sio_ping_pkt.event == "ping"
            ws.send_text("4" + encode_sio_packet(SocketIOPacket(packet_type=SocketIOPacketType.EVENT, event="pong")))
            ping_rtt_ms = round((time.perf_counter() - t_ping) * 1000.0, 3)
            ping_pong_ok = True

            # Step 5: Receive 'i' push event carrying {"s":[{"i":"MasaTaslariGuncelle","d":{...}}]}
            push_frame = EngineIOPacket.parse_text(ws.recv_text())
            push_pkt = decode_sio_packet(push_frame.payload)
            inner_env = json.loads(push_pkt.data[0].replace("\\", ""))
            push_i_event_ok = (
                push_pkt.event == "i"
                and inner_env["s"][0]["i"] == "MasaTaslariGuncelle"
                and inner_env["s"][0]["d"]["ok"] == "k-5"
            )

            # Step 6: Graceful Socket.IO namespace DISCONNECT ('41')
            ws.send_text("4" + encode_sio_packet(SocketIOPacket(packet_type=SocketIOPacketType.DISCONNECT)))
            for _ in range(20):
                if self.server_received_disconnect:
                    break
                time.sleep(0.01)
            disconnect_ok = self.server_received_disconnect
        finally:
            ws.close()

        return {
            "guest_login_ok": guest_login_ok,
            "eio_open_ok": eio_open_ok,
            "sio_connect_ok": sio_connect_ok,
            "ping_pong_ok": ping_pong_ok,
            "ping_rtt_ms": ping_rtt_ms,
            "push_i_event_ok": push_i_event_ok,
            "disconnect_ok": disconnect_ok,
        }
