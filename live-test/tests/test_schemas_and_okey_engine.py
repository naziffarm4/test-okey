import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.protocol.schemas import (
    OkeyRackEngine,
    Tas,
    validate_event_payload,
    validate_http_command_envelope,
    validate_server_envelope,
)


class TestSchemasAndOkeyEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = json.loads((ROOT / "fixtures" / "protocol_fixtures.json").read_text(encoding="utf-8"))

    def test_envelope_and_all_seven_event_schemas(self):
        self.assertTrue(validate_http_command_envelope(self.fixtures["envelopes"]["http_guest_login_cmd"])["valid"])
        self.assertTrue(validate_http_command_envelope(self.fixtures["envelopes"]["http_draw_tile_cmd"])["valid"])
        self.assertTrue(validate_server_envelope(self.fixtures["envelopes"]["server_batch_response"])["valid"])

        for ev_name, payload in self.fixtures["events"].items():
            res = validate_event_payload(ev_name, payload)
            self.assertTrue(res["valid"], f"{ev_name} failed validation: {res}")

    def test_tile_wire_parsing_and_okey_rules(self):
        # Indicator is k-4 -> active Okey key is k-5
        normal = Tas.from_wire("12-k-12", okey_key="k-5")
        self.assertEqual(normal.tas_id, "12")
        self.assertEqual(normal.tas_renk, "k")
        self.assertEqual(normal.tas_rakam, 12)
        self.assertEqual(normal.tas_key, "k-12")
        self.assertFalse(normal.is_okey_joker())

        active_okey = Tas.from_wire("5-k-5", okey_key="k-5")
        self.assertTrue(active_okey.okeymi)
        self.assertTrue(active_okey.is_okey_joker())

        # Sahte Okey (53 and 106) represent k-5 value, NOT wild joker (RVA 0x01A0A210)
        fake_okey = Tas.from_wire("53-o-0", okey_key="k-5")
        self.assertFalse(fake_okey.is_okey_joker())
        self.assertEqual(fake_okey.effective_key("k-5"), "k-5")

    def test_akilli_diz_and_okey_ile_bit_28_slot_rack(self):
        # 15 tiles where 14 tiles form 4 complete melds (0 remaining points) + 1 active Okey ("5-k-5") to finish!
        wire_tiles = [
            "1-k-1", "2-k-2", "3-k-3",               # Run 1 (k 1-2-3)
            "14-m-1", "15-m-2", "16-m-3",            # Run 2 (m 1-2-3)
            "27-s-7", "40-y-7", "66-k-7", "20-m-7",  # Color set (7s in s, y, k, m)
            "30-s-10", "31-s-11", "32-s-12", "33-s-13",  # Run 3 (s 10-11-12-13)
            "5-k-5",                                 # 15th tile = Active Okey!
        ]
        tiles = [Tas.from_wire(w, okey_key="k-5") for w in wire_tiles]
        arrangement = OkeyRackEngine.akilli_diz(tiles, okey_key="k-5")
        self.assertEqual(arrangement["kalan_toplam"], 0)

        finish_cmd = OkeyRackEngine.build_okey_ile_bit_command(
            tiles=tiles,
            okey_key="k-5",
            session_id="mock-sess-01",
        )
        self.assertIsNotNone(finish_cmd)
        self.assertEqual(finish_cmd["_i"], "masaoyunbitir-oyunbitirbeta")
        self.assertEqual(finish_cmd["bitentas"], "5")
        slots = finish_cmd["taslar"].lstrip("-").split("-")
        self.assertEqual(len(slots), 28)
        self.assertIn("Bos", slots)
        self.assertNotIn("5", slots)


if __name__ == "__main__":
    unittest.main()
