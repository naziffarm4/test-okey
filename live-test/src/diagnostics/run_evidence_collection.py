from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.diagnostics.recorder import EvidenceRecorder, sanitize_data
from src.http.probe import LocalMockHttpServer, run_safe_production_http_probe, send_signed_command
from src.protocol.schemas import (
    OkeyRackEngine,
    Rack28Model,
    Tas,
    validate_event_payload,
    validate_http_command_envelope,
    validate_server_envelope,
)
from src.socketio.parser import LocalOkeyProtocolMockStack
from src.websocket.handshake import LocalEngineIOWebSocketServer, WebSocketClient, run_safe_tcp_probe


def main() -> int:
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    fixtures = json.loads((ROOT / "fixtures" / "protocol_fixtures.json").read_text(encoding="utf-8"))
    rec = EvidenceRecorder(output_dir=reports_dir)

    # ------------------------------------------------------------------
    # FAZ 2: Safe, unauthenticated, read-only live HTTP probe
    # ------------------------------------------------------------------
    faz2_file = "faz2_live_http_probe.json"
    t0 = time.perf_counter()
    http_live = run_safe_production_http_probe("https://sistem.okeymuhabbet.com/")
    faz2_total_ms = (time.perf_counter() - t0) * 1000.0
    (reports_dir / faz2_file).write_text(json.dumps(sanitize_data(http_live), indent=2, ensure_ascii=False), encoding="utf-8")

    rec.record(
        test_id="LIVE-HTTP-01-DNS",
        environment="PRODUCTION_SAFE_READONLY",
        request_type="DNS_A_AAAA_LOOKUP",
        response_code="RESOLVED" if http_live["dns"]["resolved"] else "FAILED",
        duration_ms=http_live["dns"]["duration_ms"],
        expected="sistem.okeymuhabbet.com resolves to >=1 IP address",
        actual=f"Resolved: {http_live['dns']['addresses']}",
        evidence_file=faz2_file,
        passed=bool(http_live["dns"]["resolved"]),
        details=http_live["dns"],
    )
    rec.record(
        test_id="LIVE-HTTP-02-TCP-TLS",
        environment="PRODUCTION_SAFE_READONLY",
        request_type="TCP_443_AND_TLS_HANDSHAKE",
        response_code=http_live["tls"].get("protocol_version", "NONE"),
        duration_ms=http_live["tcp"]["duration_ms"] + http_live["tls"].get("duration_ms", 0.0),
        expected="TCP 443 connects and TLS certificate validates against system CA store",
        actual=f"TLS={http_live['tls'].get('protocol_version')} verified={http_live['tls'].get('verified')}",
        evidence_file=faz2_file,
        passed=bool(http_live["tls"].get("verified")),
        details={"tcp": http_live["tcp"], "tls": http_live["tls"]},
    )
    rec.record(
        test_id="LIVE-HTTP-03-SAFE-GET",
        environment="PRODUCTION_SAFE_READONLY",
        request_type="HTTPS_READONLY_ROOT_GET",
        response_code=http_live["http_get"]["status_code"],
        duration_ms=http_live["http_get"]["duration_ms"],
        expected="Read-only unauthenticated GET / returns HTTP status and headers without mutating state",
        actual=f"HTTP {http_live['http_get']['status_code']} ({http_live['http_get']['body_byte_length']} bytes, {http_live['http_get']['body_structure']})",
        evidence_file=faz2_file,
        passed=isinstance(http_live["http_get"]["status_code"], int) and http_live["http_get"]["status_code"] > 0,
        details={"head": http_live["http_head"], "get": http_live["http_get"], "probe_total_ms": round(faz2_total_ms, 3)},
    )
    rec.record(
        test_id="LIVE-HTTP-04-APP-CMD-GATE",
        environment="PRODUCTION_SAFE_READONLY",
        request_type="SIGNED_APP_COMMAND_AUTHORIZATION_CHECK",
        response_code="ENGELLENDİ",
        duration_ms=0.0,
        expected="Halt before sending signed ?h=MD5&d=JSON commands without written server owner authorization",
        actual="ENGELLENDİ (0 signed commands sent to production; verified via LOCAL_MOCK instead)",
        evidence_file=faz2_file,
        passed=True,
        details={"reason": "No written authorization from server owner; strictly obeyed Section 3 safety boundary"},
    )

    # ------------------------------------------------------------------
    # FAZ 3: Safe TCP :4082 reachability + Local Mock RFC 6455 / EIO=4
    # ------------------------------------------------------------------
    faz3_file = "faz3_websocket_validation.json"
    tcp_4082 = run_safe_tcp_probe("sistem.okeymuhabbet.com", 4082)

    with LocalEngineIOWebSocketServer() as ws_srv:
        ws_client = WebSocketClient(timeout=3.0)
        hs = ws_client.connect(f"ws://127.0.0.1:{ws_srv.port}/socket.io/?EIO=4&transport=websocket")
        try:
            open_pkt = ws_client.recv_text()
            t_ping = time.perf_counter()
            ws_srv.send_ping_to_last_client()
            rx_ping = ws_client.recv_text()
            ws_client.send_text("3")
            pong_ok = ws_srv.wait_for_pong(timeout=2.0)
            ping_pong_ms = round((time.perf_counter() - t_ping) * 1000.0, 3)
        finally:
            ws_client.close()

    with LocalEngineIOWebSocketServer(drop_first_connection=True) as ws_drop_srv:
        ws_reconn_client = WebSocketClient(timeout=1.5)
        t_rec = time.perf_counter()
        reconn_res = ws_reconn_client.connect_with_reconnect(
            f"ws://127.0.0.1:{ws_drop_srv.port}/socket.io/?EIO=4&transport=websocket",
            max_attempts=3,
            base_delay=0.05,
        )
        reconn_ms = round((time.perf_counter() - t_rec) * 1000.0, 3)
        ws_reconn_client.close()

    faz3_payload = {
        "production_tcp_4082_passive_probe": tcp_4082,
        "production_ws_app_handshake": {
            "status": "ENGELLENDİ",
            "reason": "Section 4 explicitly forbids application-protocol WebSocket connection, auth, or event transmission to production without written authorization.",
        },
        "local_mock_ws_eio4": {
            "http_upgrade_status": hs["status_code"],
            "sec_websocket_accept_valid": hs["accept_valid"],
            "handshake_ms": hs["handshake_ms"],
            "eio4_open_packet": open_pkt,
            "rx_ping_packet": rx_ping,
            "pong_verified": pong_ok,
            "ping_pong_rtt_ms": ping_pong_ms,
            "reconnect_recovery": {**reconn_res, "total_recovery_ms": reconn_ms},
        },
    }
    (reports_dir / faz3_file).write_text(json.dumps(sanitize_data(faz3_payload), indent=2, ensure_ascii=False), encoding="utf-8")

    rec.record(
        test_id="LIVE-WS-01-TCP4082",
        environment="PRODUCTION_SAFE_READONLY",
        request_type="TCP_4082_CONNECT_ZERO_BYTES",
        response_code="OPEN" if tcp_4082["tcp_connected"] else "CLOSED",
        duration_ms=tcp_4082["tcp_handshake_ms"],
        expected="TCP port 4082 reachable with 0 application bytes sent",
        actual=f"TCP connected={tcp_4082['tcp_connected']} to {tcp_4082['remote_ip']}:4082 in {tcp_4082['tcp_handshake_ms']} ms (0 bytes sent)",
        evidence_file=faz3_file,
        passed=bool(tcp_4082["tcp_connected"]),
        details=tcp_4082,
    )
    rec.record(
        test_id="LIVE-WS-02-PROD-APP-GATE",
        environment="PRODUCTION_SAFE_READONLY",
        request_type="WS_UPGRADE_EIO4_AUTHORIZATION_CHECK",
        response_code="ENGELLENDİ",
        duration_ms=0.0,
        expected="Do not initiate unauthorized Engine.IO v4 / Socket.IO v4 session on production :4082",
        actual="ENGELLENDİ per Section 4 rule; verified protocol mechanics on LOCAL_MOCK",
        evidence_file=faz3_file,
        passed=True,
        details=faz3_payload["production_ws_app_handshake"],
    )
    rec.record(
        test_id="MOCK-WS-03-EIO4-HANDSHAKE-PING",
        environment="LOCAL_MOCK",
        request_type="WS_101_UPGRADE_AND_EIO4_PING_PONG",
        response_code=hs["status_code"],
        duration_ms=hs["handshake_ms"] + ping_pong_ms,
        expected="HTTP 101 Switching Protocols + EIO=4 0{sid} + 2/3 ping-pong",
        actual=f"HTTP {hs['status_code']}, accept_valid={hs['accept_valid']}, pong={pong_ok} ({ping_pong_ms} ms)",
        evidence_file=faz3_file,
        passed=hs["status_code"] == 101 and hs["accept_valid"] and pong_ok,
        details=faz3_payload["local_mock_ws_eio4"],
    )
    rec.record(
        test_id="MOCK-WS-04-RECONNECT",
        environment="LOCAL_MOCK",
        request_type="WS_DROP_AND_RECONNECT_RECOVERY",
        response_code=101 if reconn_res["connected"] else 0,
        duration_ms=reconn_ms,
        expected="Client recovers automatically after dropped initial connection",
        actual=f"connected={reconn_res['connected']} on attempt {reconn_res['attempts']} in {reconn_ms} ms",
        evidence_file=faz3_file,
        passed=bool(reconn_res["connected"]) and reconn_res["attempts"] >= 2,
        details=faz3_payload["local_mock_ws_eio4"]["reconnect_recovery"],
    )

    # ------------------------------------------------------------------
    # FAZ 4 & FAZ 5: Dual-channel Mock, 7 Schemas, Akıllı Diz & Okey ile Bit
    # ------------------------------------------------------------------
    faz45_file = "faz4_5_protocol_and_engine.json"
    with LocalMockHttpServer(expected_salt="SYNTHETIC_HTTP_16") as http_mock:
        t_http_mock = time.perf_counter()
        ok_signed = send_signed_command(
            base_url=http_mock.base_url,
            payload={"_i": "versiyonkontrol-versiyonkontrol", "Versiyon": "3.1.33", "os": "ANDROID"},
            session_id="mock-sess-1001",
            salt="SYNTHETIC_HTTP_16",
        )
        bad_signed = send_signed_command(
            base_url=http_mock.base_url,
            payload={"_i": "versiyonkontrol-versiyonkontrol", "Versiyon": "3.1.33", "os": "ANDROID"},
            session_id="mock-sess-1001",
            salt="TAMPERED_SALT_00",
        )
        http_mock_ms = round((time.perf_counter() - t_http_mock) * 1000.0, 3)

    with LocalOkeyProtocolMockStack() as stack:
        t_stack = time.perf_counter()
        dual_outcome = stack.run_simulated_client_flow()
        stack_ms = round((time.perf_counter() - t_stack) * 1000.0, 3)

    t_schema = time.perf_counter()
    schema_checks = {
        "http_guest_login_cmd": validate_http_command_envelope(fixtures["envelopes"]["http_guest_login_cmd"]),
        "http_draw_tile_cmd": validate_http_command_envelope(fixtures["envelopes"]["http_draw_tile_cmd"]),
        "server_batch_response": validate_server_envelope(fixtures["envelopes"]["server_batch_response"]),
        "events": {k: validate_event_payload(k, v) for k, v in fixtures["events"].items()},
    }
    schema_ms = round((time.perf_counter() - t_schema) * 1000.0, 3)
    all_schemas_ok = (
        schema_checks["http_guest_login_cmd"]["valid"]
        and schema_checks["http_draw_tile_cmd"]["valid"]
        and schema_checks["server_batch_response"]["valid"]
        and all(v["valid"] for v in schema_checks["events"].values())
    )

    t_eng = time.perf_counter()
    hand_wires = [
        "1-k-1", "2-k-2", "3-k-3",
        "14-m-1", "15-m-2", "16-m-3",
        "27-s-7", "40-y-7", "66-k-7", "20-m-7",
        "30-s-10", "31-s-11", "32-s-12", "33-s-13",
        "5-k-5",
    ]
    hand_tiles = [Tas.from_wire(w, okey_key="k-5") for w in hand_wires]
    user_rack = Rack28Model.from_tiles(hand_tiles)
    before_rack = user_rack.to_slot_ids()
    alternatives = OkeyRackEngine.suggest_alternatives(user_rack, okey_key="k-5")
    non_destructive_ok = user_rack.to_slot_ids() == before_rack

    akilli_res = alternatives["per_alternative"]
    finish_cmd = OkeyRackEngine.build_okey_ile_bit_command(
        tiles=hand_tiles,
        okey_key="k-5",
        session_id="mock-sess-1001",
    )

    pair_hand_wires = [
        "1-k-1", "54-k-1",
        "14-m-2", "67-m-2",
        "27-s-3", "80-s-3",
        "40-y-4", "93-y-4",
        "10-k-10", "63-k-10",
        "25-m-12", "78-m-12",
        "53-o-0", "106-o-0",
        "58-k-5",
    ]
    pair_tiles = [Tas.from_wire(w, okey_key="k-5") for w in pair_hand_wires]
    cift_res = OkeyRackEngine.akilli_diz(pair_tiles[:-1], okey_key="k-5", mode="cift")
    pair_finish_cmd = OkeyRackEngine.build_okey_ile_bit_command(
        tiles=pair_tiles,
        okey_key="k-5",
        session_id="mock-sess-1001",
    )
    fake_okey_rejected = (
        OkeyRackEngine.build_okey_ile_bit_command(
            tiles=[Tas.from_wire(w, okey_key="k-5") for w in (hand_wires[:-1] + ["53-o-0"])],
            okey_key="k-5",
            session_id="mock-sess-1001",
        )
        is None
    )
    with LocalMockHttpServer(expected_salt="SYNTHETIC_HTTP_16") as fin_mock:
        mock_fin_ok = send_signed_command(
            base_url=fin_mock.base_url,
            payload=finish_cmd or {},
            session_id="mock-sess-1001",
            salt="SYNTHETIC_HTTP_16",
        )
    eng_ms = round((time.perf_counter() - t_eng) * 1000.0, 3)

    faz45_payload = sanitize_data(
        {
            "mock_http_signing": {"valid_status": ok_signed["status_code"], "tampered_status": bad_signed["status_code"]},
            "mock_dual_channel_session": dual_outcome,
            "schema_validations": schema_checks,
            "okey_engine_simulation": {
                "indicator_tile": "4-k-4",
                "active_okey_key": "k-5",
                "input_15_tiles": hand_wires,
                "non_destructive_preview_verified": non_destructive_ok,
                "akilli_diz": akilli_res,
                "akilli_diz_7_pairs": cift_res,
                "okey_ile_bit_command": finish_cmd,
                "okey_ile_bit_7_pairs_command": pair_finish_cmd,
                "fake_okey_finish_rejected": fake_okey_rejected,
                "mock_server_finish_event": mock_fin_ok["json"]["s"][0]["i"] if mock_fin_ok["json"] else None,
            },
        }
    )
    (reports_dir / faz45_file).write_text(json.dumps(faz45_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    rec.record(
        test_id="MOCK-HTTP-05-SIGNING",
        environment="LOCAL_MOCK",
        request_type="SIGNED_GET_MD5_VERIFICATION",
        response_code=f"{ok_signed['status_code']}/{bad_signed['status_code']}",
        duration_ms=http_mock_ms,
        expected="Valid signature returns 200 s[] envelope; tampered signature returns 403",
        actual=f"Valid={ok_signed['status_code']}, Tampered={bad_signed['status_code']}",
        evidence_file=faz45_file,
        passed=ok_signed["status_code"] == 200 and bad_signed["status_code"] == 403,
        details=faz45_payload["mock_http_signing"],
    )
    rec.record(
        test_id="MOCK-SIO4-06-DUAL-CHANNEL",
        environment="LOCAL_MOCK",
        request_type="DUAL_CHANNEL_HTTP_AND_SOCKETIO_V4",
        response_code="ALL_OK" if all(v is True for k, v in dual_outcome.items() if k.endswith("_ok")) else "FAILED",
        duration_ms=stack_ms,
        expected="Guest login + EIO open + SIO 40{sid} + Ping/Pong + 'i' push dispatch + 41 disconnect succeed",
        actual=json.dumps(dual_outcome),
        evidence_file=faz45_file,
        passed=all(v is True for k, v in dual_outcome.items() if k.endswith("_ok")),
        details=dual_outcome,
    )
    rec.record(
        test_id="SIM-SCHEMA-07-ALL-EVENTS",
        environment="LOCAL_SIMULATION",
        request_type="JSON_SCHEMA_VALIDATION_7_EVENTS",
        response_code="7/7_VALID" if all_schemas_ok else "INVALID",
        duration_ms=schema_ms,
        expected="All HTTP/Server envelopes and 7 target event schemas validate against binary handler rules",
        actual=f"all_schemas_ok={all_schemas_ok}",
        evidence_file=faz45_file,
        passed=all_schemas_ok,
        details=schema_checks,
    )
    rec.record(
        test_id="SIM-ENGINE-08-AKILLI-DIZ-OKEY-BIT",
        environment="LOCAL_SIMULATION",
        request_type="AKILLI_DIZ_AND_OKEY_ILE_BIT_28_SLOT",
        response_code="OK" if (akilli_res["kalan_toplam"] == 0 and finish_cmd is not None) else "FAILED",
        duration_ms=eng_ms,
        expected="Akıllı Diz yields kalan_toplam=0 and Okey ile Bit produces 28-slot masaoyunbitir-oyunbitirbeta command",
        actual=f"kalan_toplam={akilli_res['kalan_toplam']}, bitentas={finish_cmd['bitentas'] if finish_cmd else None}",
        evidence_file=faz45_file,
        passed=akilli_res["kalan_toplam"] == 0 and finish_cmd is not None and finish_cmd["bitentas"] == "5",
        details=faz45_payload["okey_engine_simulation"],
    )

    ledger_path = rec.save_ledger("test_execution_ledger.json")
    print(f"Evidence collection completed. Ledger written to: {ledger_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
