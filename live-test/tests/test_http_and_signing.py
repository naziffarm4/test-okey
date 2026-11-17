import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.diagnostics.recorder import EvidenceRecorder, sanitize_data
from src.http.probe import CommandEnvelopeBuilder, DuplicateGuard, LocalMockHttpServer, send_signed_command


class TestHttpAndSigning(unittest.TestCase):
    def test_sensitive_fields_are_redacted(self):
        raw = {
            "url": "https://sistem.okeymuhabbet.com/?h=abcdef0123456789abcdef0123456789&d=%7B%22_t%22%3A%22secret_sess%22%7D",
            "token_id": "tok_live_999",
            "session_id": "sess_live_888",
            "_t": "sess_live_888",
            "safe_key": "masatascek-tascek",
        }
        cleaned = sanitize_data(raw)
        self.assertEqual(cleaned["token_id"], "[REDACTED]")
        self.assertEqual(cleaned["session_id"], "[REDACTED]")
        self.assertEqual(cleaned["_t"], "[REDACTED]")
        self.assertNotIn("secret_sess", cleaned["url"])
        self.assertEqual(cleaned["safe_key"], "masatascek-tascek")

    def test_envelope_builder_and_duplicate_guard(self):
        pre = CommandEnvelopeBuilder.build_pre_auth("giris-misafir", {"device_id": "dev-1", "token_id": "", "machash": "abc"})
        self.assertEqual(pre["_e"], "giris-misafir")
        self.assertNotIn("_i", pre)

        in_sess = CommandEnvelopeBuilder.build_in_session("masatascek-tascek", {"tip": "o", "dc": "0"}, session_id="sess-1")
        self.assertEqual(in_sess["_i"], "masatascek-tascek")
        self.assertEqual(in_sess["_t"], "sess-1")

        guard = DuplicateGuard(window_seconds=1)
        payload = json.dumps(in_sess, separators=(",", ":"))
        self.assertTrue(guard.allow(payload, now_sec=1000))
        self.assertFalse(guard.allow(payload, now_sec=1001))
        self.assertTrue(guard.allow(payload, now_sec=1002))

    def test_local_mock_http_signed_command_and_tamper_rejection(self):
        synthetic_salt = "TEST_ONLY_16SALT"
        with LocalMockHttpServer(expected_salt=synthetic_salt) as srv:
            ok_res = send_signed_command(
                base_url=srv.base_url,
                payload={"_i": "versiyonkontrol-versiyonkontrol", "Versiyon": "3.1.33", "os": "ANDROID"},
                session_id="mock-sess-42",
                salt=synthetic_salt,
            )
            self.assertEqual(ok_res["status_code"], 200)
            self.assertIn("s", ok_res["json"])
            self.assertEqual(ok_res["json"]["s"][0]["i"], "VersiyonOnay")

            bad_res = send_signed_command(
                base_url=srv.base_url,
                payload={"_i": "versiyonkontrol-versiyonkontrol", "Versiyon": "3.1.33", "os": "ANDROID"},
                session_id="mock-sess-42",
                salt="WRONG_SALT_VALUE",
            )
            self.assertEqual(bad_res["status_code"], 403)

    def test_evidence_recorder_writes_required_metadata_fields(self):
        tmp_out = ROOT / "reports" / "_unit_test_record.json"
        try:
            rec = EvidenceRecorder(output_dir=ROOT / "reports")
            entry = rec.record(
                test_id="UNIT-HTTP-01",
                environment="LOCAL_MOCK",
                request_type="HTTPS_GET_SIGNED_MOCK",
                response_code=200,
                duration_ms=4.2,
                expected="200 OK with s[] envelope",
                actual="200 OK with s[] envelope",
                evidence_file="_unit_test_record.json",
                passed=True,
                details={"session_id": "should_not_leak"},
            )
            tmp_out.write_text(json.dumps(entry, indent=2), encoding="utf-8")
            for required_key in (
                "test_id", "timestamp", "environment", "request_type",
                "response_code", "duration_ms", "expected", "actual",
                "evidence_file", "passed",
            ):
                self.assertIn(required_key, entry)
            self.assertEqual(entry["details"]["session_id"], "[REDACTED]")
        finally:
            if tmp_out.exists():
                tmp_out.unlink()


if __name__ == "__main__":
    unittest.main()
