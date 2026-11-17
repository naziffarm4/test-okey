import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.socketio.parser import (
    EngineIOPacket,
    EngineIOPacketType,
    LocalOkeyProtocolMockStack,
    SocketIOPacket,
    SocketIOPacketType,
    decode_sio_packet,
    encode_sio_packet,
)


class TestSocketIOAndMock(unittest.TestCase):
    def test_eio_and_sio_v4_packet_codec(self):
        eio = EngineIOPacket.parse_text('0{"sid":"abc","upgrades":[],"pingInterval":25000,"pingTimeout":20000}')
        self.assertEqual(eio.packet_type, EngineIOPacketType.OPEN)

        # Socket.IO v4 CONNECT packet on default namespace with auth payload
        sio_conn = SocketIOPacket(
            packet_type=SocketIOPacketType.CONNECT,
            namespace="/",
            data={"id": "1001", "handshake": "SYNTHETIC_OK"},
        )
        encoded = encode_sio_packet(sio_conn)
        self.assertTrue(encoded.startswith("0{"))
        decoded = decode_sio_packet(encoded)
        self.assertEqual(decoded.packet_type, SocketIOPacketType.CONNECT)
        self.assertEqual(decoded.namespace, "/")
        self.assertEqual(decoded.data["id"], "1001")

        # Server CONNECT ack without sid must raise protocol violation (matching RVA 0x01ACA854)
        with self.assertRaises(ValueError):
            SocketIOPacket.validate_server_connect(decode_sio_packet("0{}"))

        ok_conn = decode_sio_packet('0{"sid":"sio_ns_01"}')
        self.assertEqual(SocketIOPacket.validate_server_connect(ok_conn), "sio_ns_01")

        # Event 'i' carrying {"s":[{"i":...,"d":...}]}
        inner_json = json.dumps({"s": [{"i": "TasAt", "d": {"tas": "52-y-13", "yon": "1"}}]})
        ev_raw = encode_sio_packet(
            SocketIOPacket(packet_type=SocketIOPacketType.EVENT, namespace="/", event="i", data=[inner_json])
        )
        self.assertTrue(ev_raw.startswith('2["i",'))
        ev_dec = decode_sio_packet(ev_raw)
        self.assertEqual(ev_dec.event, "i")
        self.assertEqual(json.loads(ev_dec.data[0])["s"][0]["i"], "TasAt")

    def test_end_to_end_mock_dual_channel_session(self):
        with LocalOkeyProtocolMockStack() as stack:
            outcome = stack.run_simulated_client_flow()
            self.assertTrue(outcome["guest_login_ok"])
            self.assertTrue(outcome["eio_open_ok"])
            self.assertTrue(outcome["sio_connect_ok"])
            self.assertTrue(outcome["ping_pong_ok"])
            self.assertTrue(outcome["push_i_event_ok"])
            self.assertTrue(outcome["disconnect_ok"])


if __name__ == "__main__":
    unittest.main()
