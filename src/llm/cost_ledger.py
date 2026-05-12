"""Per-query cost ledger. SQLite-backed in v1; Langfuse self-hosted in v1.5.

DeepSeek V4 Pro pricing (cache-aware tokens via Anthropic-compatible endpoint):
  input  : $0.14 / 1M tokens (cache miss)
  cached : $0.014 / 1M tokens (cache hit)
  output : $0.28 / 1M tokens

These match DeepSeek's published rates as of 2026-05; update as needed.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

PRICE_INPUT_PER_TOKEN = 0.14 / 1_000_000
PRICE_CACHED_PER_TOKEN = 0.014 / 1_000_000
PRICE_OUTPUT_PER_TOKEN = 0.28 / 1_000_000

LEDGER_PATH = Path(__file__).resolve().parents[2] / "eval_results" / "cost_ledger.sqlite"


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0

    @property
    def cost_usd(self) -> float:
        return (
            self.input_tokens * PRICE_INPUT_PER_TOKEN
            + self.cached_input_tokens * PRICE_CACHED_PER_TOKEN
            + self.output_tokens * PRICE_OUTPUT_PER_TOKEN
        )


@contextmanager
def _conn():
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(LEDGER_PATH)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS usage (
                ts TEXT,
                node TEXT,
                input_tokens INTEGER,
                cached_input_tokens INTEGER,
                output_tokens INTEGER,
                cost_usd REAL
            )"""
        )
        yield conn
        conn.commit()
    finally:
        conn.close()


def record(node: str, usage: Usage) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO usage VALUES (?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                node,
                usage.input_tokens,
                usage.cached_input_tokens,
                usage.output_tokens,
                usage.cost_usd,
            ),
        )


def totals() -> dict[str, float | int]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*), SUM(input_tokens), SUM(cached_input_tokens), SUM(output_tokens), SUM(cost_usd) FROM usage"
        ).fetchone()
    return {
        "calls": row[0] or 0,
        "input_tokens": row[1] or 0,
        "cached_input_tokens": row[2] or 0,
        "output_tokens": row[3] or 0,
        "cost_usd": round(row[4] or 0.0, 6),
    }
