import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.http.probe import LocalMockHttpServer, send_signed_command
from src.protocol.schemas import (
    OkeyRackEngine,
    Rack28Model,
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

    def test_rack28_model_and_non_destructive_alternatives_and_no_duplicate_reuse(self):
        wire_tiles = [
            "12-k-12", "13-k-13", "1-k-1",   # Valid 12-13-1 wraparound run!
            "54-k-1", "14-m-1", "27-s-1",    # Distinct color 1s (k, m, s) using second physical k-1 ("54")
            "45-y-8", "98-y-8",              # Pair of y-8
        ]
        tiles = [Tas.from_wire(w, okey_key="k-5") for w in wire_tiles]
        # Place at custom scattered slots on the 28-slot rack
        custom_positions = [0, 3, 5, 10, 14, 17, 22, 27]
        rack = Rack28Model.from_tiles(tiles, positions=custom_positions)
        before_snapshot = rack.to_slot_ids()

        # Duplicate physical TasID on same rack must fail immediately
        with self.assertRaises(ValueError):
            Rack28Model.from_tiles([tiles[0], tiles[0]])

        # Invalid 13-1-2 wraparound must NOT form a meld
        wrap_trap = [
            Tas.from_wire("13-m-13", okey_key="k-5"),
            Tas.from_wire("14-m-1", okey_key="k-5"),
            Tas.from_wire("15-m-2", okey_key="k-5"),
        ]
        trap_res = OkeyRackEngine.akilli_diz(wrap_trap, okey_key="k-5", mode="per")
        self.assertEqual(len(trap_res["melds"]), 0)
        self.assertEqual(trap_res["kalan_toplam"], 16)

        # Non-destructive alternative suggestion preserves user's rack untouched
        suggestions = OkeyRackEngine.suggest_alternatives(rack, okey_key="k-5")
        self.assertEqual(rack.to_slot_ids(), before_snapshot)
        self.assertEqual(suggestions["original_rack_28"], before_snapshot)
        # In 'per' mode: 12-13-1 (k) + 1-1-1 (k,m,s) melded -> only y-8, y-8 left (16 pts); zero duplicate reuse!
        self.assertEqual(len(suggestions["per_alternative"]["melds"]), 2)
        self.assertEqual(suggestions["per_alternative"]["kalan_toplam"], 16)
        # In 'cift' mode: k-1 ("1" & "54") + y-8 ("45" & "98") -> 2 pairs
        self.assertEqual(suggestions["cift_alternative"]["cift_sayisi"], 2)

    def test_akilli_diz_and_okey_ile_bit_per_and_7_pairs_and_mock_submit(self):
        # Case A: 14 tiles form 4 complete melds (0 remaining) + 15th tile = Active Okey ("5-k-5")
        wire_tiles = [
            "1-k-1", "2-k-2", "3-k-3",
            "14-m-1", "15-m-2", "16-m-3",
            "27-s-7", "40-y-7", "66-k-7", "20-m-7",
            "30-s-10", "31-s-11", "32-s-12", "33-s-13",
            "5-k-5",
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
        self.assertTrue(finish_cmd["taslar"].startswith("-"))
        slots = finish_cmd["taslar"][1:].split("-")
        self.assertEqual(len(slots), 28)
        self.assertEqual(slots.count("Bos"), 14)
        self.assertNotIn("5", slots)

        # Case B: 7 Pairs (including Sahte Okey pair 53+106 representing k-5!) + 15th tile = Active Okey ("58-k-5")
        seven_pairs_plus_okey = [
            "1-k-1", "54-k-1",
            "14-m-2", "67-m-2",
            "27-s-3", "80-s-3",
            "40-y-4", "93-y-4",
            "10-k-10", "63-k-10",
            "25-m-12", "78-m-12",
            "53-o-0", "106-o-0",  # Two Fake Okeys form a valid k-5 pair!
            "58-k-5",             # Second copy of active Okey discarded to finish!
        ]
        pair_tiles = [Tas.from_wire(w, okey_key="k-5") for w in seven_pairs_plus_okey]
        pair_finish = OkeyRackEngine.build_okey_ile_bit_command(
            tiles=pair_tiles,
            okey_key="k-5",
            session_id="mock-sess-01",
        )
        self.assertIsNotNone(pair_finish)
        self.assertEqual(pair_finish["bitentas"], "58")

        # Case C: Fake Okey ("53-o-0") is NOT a wild Okey; cannot trigger Okey ile Bit if no active Okey is discarded
        no_real_okey = wire_tiles[:-1] + ["53-o-0"]
        self.assertIsNone(
            OkeyRackEngine.build_okey_ile_bit_command(
                tiles=[Tas.from_wire(w, okey_key="k-5") for w in no_real_okey],
                okey_key="k-5",
                session_id="mock-sess-01",
            )
        )

        # Case D: Verify local mock HTTP server accepts valid 28-slot OyunBitirBeta and rejects malformed rack
        with LocalMockHttpServer(expected_salt="SYNTHETIC_HTTP_16") as srv:
            ok_http = send_signed_command(
                base_url=srv.base_url,
                payload=finish_cmd,
                session_id="mock-sess-01",
                salt="SYNTHETIC_HTTP_16",
            )
            self.assertEqual(ok_http["status_code"], 200)
            self.assertEqual(ok_http["json"]["s"][0]["i"], "OyunBitir")

            bad_cmd = dict(finish_cmd)
            bad_cmd["taslar"] = "-1-2-3-Bos"  # Wrong slot count (not 28)
            err_http = send_signed_command(
                base_url=srv.base_url,
                payload=bad_cmd,
                session_id="mock-sess-01",
                salt="SYNTHETIC_HTTP_16",
            )
            self.assertEqual(err_http["status_code"], 200)
            self.assertEqual(err_http["json"]["s"][0]["i"], "OyunBitirHata")


if __name__ == "__main__":
    unittest.main()
