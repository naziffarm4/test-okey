from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SENSITIVE_KEYS = frozenset({
    "token",
    "token_id",
    "session_id",
    "_t",
    "password",
    "salt",
    "secret",
    "handshake",
    "authorization",
    "cookie",
    "set-cookie",
    "h",
    "machash",
})


def _sanitize_url(value: str) -> str:
    try:
        parts = urlsplit(value)
    except ValueError:
        return value
    if not parts.query:
        return value
    cleaned_pairs: list[tuple[str, str]] = []
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
        if k.lower() in SENSITIVE_KEYS:
            cleaned_pairs.append((k, "[REDACTED]"))
        elif k == "d" and v.startswith("{"):
            try:
                parsed = json.loads(v)
                cleaned_pairs.append((k, json.dumps(sanitize_data(parsed), separators=(",", ":"))))
            except ValueError:
                cleaned_pairs.append((k, v))
        else:
            cleaned_pairs.append((k, v))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(cleaned_pairs), parts.fragment))


def sanitize_data(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if str(k).lower() in SENSITIVE_KEYS:
                out[k] = "[REDACTED]"
            else:
                out[k] = sanitize_data(v)
        return out
    if isinstance(obj, list):
        return [sanitize_data(item) for item in obj]
    if isinstance(obj, tuple):
        return tuple(sanitize_data(item) for item in obj)
    if isinstance(obj, str):
        if "://" in obj and "?" in obj:
            return _sanitize_url(obj)
        return obj
    return obj


class EvidenceRecorder:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.entries: list[dict[str, Any]] = []

    def record(
        self,
        *,
        test_id: str,
        environment: str,
        request_type: str,
        response_code: int | str,
        duration_ms: float,
        expected: str,
        actual: str,
        evidence_file: str,
        passed: bool,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        entry = {
            "test_id": test_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": environment,
            "request_type": request_type,
            "response_code": response_code,
            "duration_ms": round(float(duration_ms), 3),
            "expected": expected,
            "actual": actual,
            "evidence_file": evidence_file,
            "passed": bool(passed),
            "details": sanitize_data(details or {}),
        }
        self.entries.append(entry)
        return entry

    def save_ledger(self, filename: str = "test_execution_ledger.json") -> Path:
        target = self.output_dir / filename
        target.write_text(json.dumps(self.entries, indent=2, ensure_ascii=False), encoding="utf-8")
        return target
