"""Right-to-erasure stub.

W5 ships an in-memory tombstone list. W6+ persists to PostgreSQL alongside the
audit log. The agent's runtime checks against `is_erased(user_id)` and refuses
to surface that user's data via any tool.
"""

from __future__ import annotations

import threading

_LOCK = threading.Lock()
_TOMBSTONES: set[str] = set()


def request_erasure(user_id: str) -> None:
    with _LOCK:
        _TOMBSTONES.add(user_id)


def restore(user_id: str) -> None:
    with _LOCK:
        _TOMBSTONES.discard(user_id)


def is_erased(user_id: str) -> bool:
    with _LOCK:
        return user_id in _TOMBSTONES


def tombstones() -> list[str]:
    with _LOCK:
        return sorted(_TOMBSTONES)
