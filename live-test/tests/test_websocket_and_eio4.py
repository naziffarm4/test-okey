import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.websocket.handshake import LocalEngineIOWebSocketServer, WebSocketClient


class TestWebSocketAndEio4(unittest.TestCase):
    def test_ws_upgrade_101_and_eio4_handshake_and_ping_pong(self):
        with LocalEngineIOWebSocketServer() as srv:
            client = WebSocketClient(timeout=3.0)
            hs = client.connect(f"ws://127.0.0.1:{srv.port}/socket.io/?EIO=4&transport=websocket")
            try:
                self.assertEqual(hs["status_code"], 101)
                self.assertTrue(hs["accept_valid"])
                open_frame = client.recv_text()
                self.assertTrue(open_frame.startswith("0{"))
                # Server sends Engine.IO ping '2'; client replies '3'
                srv.send_ping_to_last_client()
                ping_pkt = client.recv_text()
                self.assertEqual(ping_pkt, "2")
                client.send_text("3")
                self.assertTrue(srv.wait_for_pong(timeout=2.0))
            finally:
                client.close()

    def test_timeout_and_reconnect_recovery(self):
        with LocalEngineIOWebSocketServer(drop_first_connection=True) as srv:
            client = WebSocketClient(timeout=1.5)
            res = client.connect_with_reconnect(
                f"ws://127.0.0.1:{srv.port}/socket.io/?EIO=4&transport=websocket",
                max_attempts=3,
                base_delay=0.05,
            )
            try:
                self.assertTrue(res["connected"])
                self.assertGreaterEqual(res["attempts"], 2)
                open_frame = client.recv_text()
                self.assertTrue(open_frame.startswith("0{"))
            finally:
                client.close()


if __name__ == "__main__":
    unittest.main()
