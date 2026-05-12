"""Append-only audit log. W3 is in-memory + JSONL file; W5 swaps to PostgreSQL."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_AUDIT_FILE: Path | None = None
_IN_MEMORY: list[dict[str, Any]] = []


def configure(path: Path | None) -> None:
    global _AUDIT_FILE
    _AUDIT_FILE = path
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)


def audit_event(kind: str, payload: dict[str, Any]) -> None:
    entry = {
        "kind": kind,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with _LOCK:
        _IN_MEMORY.append(entry)
        if _AUDIT_FILE is not None:
            with _AUDIT_FILE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")


def recent(limit: int = 50) -> list[dict[str, Any]]:
    with _LOCK:
        return list(_IN_MEMORY[-limit:])


def clear() -> None:
    with _LOCK:
        _IN_MEMORY.clear()


_default_audit = os.environ.get("AUDIT_LOG_PATH")
if _default_audit:
    configure(Path(_default_audit))
