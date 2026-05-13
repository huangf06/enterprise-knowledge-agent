"""A3 semantic cache.

Embedding-based cache over (query, user_role) -> {answer, tool_history, elapsed_s}.
A new query embeds and finds the highest-cosine cached entry; if similarity >=
threshold AND user_role matches, return the cached answer.

Storage: SQLite at eval_results/semantic_cache.sqlite. Embeddings stored as
JSON arrays (small enough at BGE-M3 1024-dim, ~8KB per row).

Enable via env SEMANTIC_CACHE_ENABLED. Default off so the v1 baseline is not
silently overwritten. Set to "1" in F7 production deploy where repeat traffic
on the public demo gets the latency / cost lift.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from src.retrieval.embeddings import embed

CACHE_PATH = Path(__file__).resolve().parents[2] / "eval_results" / "semantic_cache.sqlite"
DEFAULT_THRESHOLD = 0.93


def is_enabled() -> bool:
    flag = os.environ.get("SEMANTIC_CACHE_ENABLED", "0").strip().lower()
    return flag in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class CacheHit:
    answer: str
    similarity: float
    cached_at: float
    user_role: str


@contextmanager
def _conn():
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CACHE_PATH)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT,
                user_role TEXT,
                answer TEXT,
                embedding TEXT,
                cached_at REAL
            )"""
        )
        yield conn
        conn.commit()
    finally:
        conn.close()


def put(query: str, user_role: str, answer: str) -> None:
    if not is_enabled():
        return
    vec = embed([query])[0]
    with _conn() as conn:
        conn.execute(
            "INSERT INTO cache(query, user_role, answer, embedding, cached_at) VALUES (?, ?, ?, ?, ?)",
            (query, user_role, answer, json.dumps(vec), time.time()),
        )


def lookup(
    query: str, user_role: str, threshold: float = DEFAULT_THRESHOLD
) -> CacheHit | None:
    """Return the highest-similarity cached answer for the same role, or None."""
    if not is_enabled():
        return None
    qvec = np.asarray(embed([query])[0])
    best: CacheHit | None = None
    best_sim = threshold
    with _conn() as conn:
        rows = conn.execute(
            "SELECT answer, embedding, cached_at FROM cache WHERE user_role = ?",
            (user_role,),
        ).fetchall()
    for answer, emb_json, cached_at in rows:
        try:
            v = np.asarray(json.loads(emb_json))
        except Exception:
            continue
        if v.shape != qvec.shape:
            continue
        sim = float(qvec @ v)  # both normalized in BGE-M3
        if sim > best_sim:
            best_sim = sim
            best = CacheHit(answer=answer, similarity=sim, cached_at=cached_at, user_role=user_role)
    return best


def stats() -> dict[str, Any]:
    with _conn() as conn:
        row = conn.execute("SELECT COUNT(*) FROM cache").fetchone()
    return {"entries": row[0] or 0, "path": str(CACHE_PATH), "enabled": is_enabled()}


def reset() -> None:
    """Wipe the cache. Used for ablation runs to start cold."""
    if CACHE_PATH.exists():
        CACHE_PATH.unlink()


__all__ = ["lookup", "put", "stats", "reset", "is_enabled", "CacheHit", "DEFAULT_THRESHOLD"]
