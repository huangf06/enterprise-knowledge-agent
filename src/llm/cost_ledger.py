"""Per-query cost ledger. SQLite-backed in v1; Langfuse self-hosted in v1.5.

DeepSeek V4 Pro pricing (cache-aware tokens via Anthropic-compatible endpoint):
  input  : $0.14 / 1M tokens (cache miss)
  cached : $0.014 / 1M tokens (cache hit)
  output : $0.28 / 1M tokens

These match DeepSeek's published rates as of 2026-05; update as needed.

Process isolation (v4.1 fix 2026-05-13): every row carries the writer's PID so
concurrent eval runs (e.g. Self-Refine ON vs OFF ablation) do not cross-
contaminate each other's per-scenario time-window queries. The default
`query_window` filters by the calling process's PID; pass `pid=None` for
analysis tools that want the whole ledger.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PRICE_INPUT_PER_TOKEN = 0.14 / 1_000_000
PRICE_CACHED_PER_TOKEN = 0.014 / 1_000_000
PRICE_OUTPUT_PER_TOKEN = 0.28 / 1_000_000

LEDGER_PATH = Path(__file__).resolve().parents[2] / "eval_results" / "cost_ledger.sqlite"

_SENTINEL_NO_PID = object()


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


def _ensure_pid_column(conn: sqlite3.Connection) -> None:
    """Migrate pre-pid ledgers in place. Idempotent."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(usage)").fetchall()}
    if "pid" not in cols:
        conn.execute("ALTER TABLE usage ADD COLUMN pid INTEGER")


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
                cost_usd REAL,
                pid INTEGER
            )"""
        )
        _ensure_pid_column(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


def record(node: str, usage: Usage) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO usage(ts, node, input_tokens, cached_input_tokens, output_tokens, cost_usd, pid) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                node,
                usage.input_tokens,
                usage.cached_input_tokens,
                usage.output_tokens,
                usage.cost_usd,
                os.getpid(),
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


def query_window(
    start_iso: str,
    end_iso: str,
    pid: int | None | object = _SENTINEL_NO_PID,
) -> dict[str, Any]:
    """Aggregate usage in a [start, end] timestamp window, broken down by node.

    pid semantics:
      - default (sentinel): filter to current process's pid (the usual runner case)
      - explicit int: filter to that pid (debugging / analysis)
      - explicit None: no pid filter (analysis over whole ledger)
    """
    if pid is _SENTINEL_NO_PID:
        pid_filter: int | None = os.getpid()
    else:
        pid_filter = pid  # type: ignore[assignment]

    sql = (
        "SELECT node, COUNT(*), SUM(input_tokens), SUM(cached_input_tokens), SUM(output_tokens), SUM(cost_usd) "
        "FROM usage WHERE ts >= ? AND ts <= ?"
    )
    params: list[Any] = [start_iso, end_iso]
    if pid_filter is not None:
        sql += " AND pid = ?"
        params.append(pid_filter)
    sql += " GROUP BY node"

    with _conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    per_node: dict[str, dict[str, float | int]] = {}
    total_calls = 0
    total_in = 0
    total_cached = 0
    total_out = 0
    total_cost = 0.0
    for node, calls, in_tok, cached_tok, out_tok, cost in rows:
        per_node[node] = {
            "calls": calls or 0,
            "input_tokens": in_tok or 0,
            "cached_input_tokens": cached_tok or 0,
            "output_tokens": out_tok or 0,
            "cost_usd": round(cost or 0.0, 6),
        }
        total_calls += calls or 0
        total_in += in_tok or 0
        total_cached += cached_tok or 0
        total_out += out_tok or 0
        total_cost += cost or 0.0
    return {
        "per_node": per_node,
        "calls": total_calls,
        "input_tokens": total_in,
        "cached_input_tokens": total_cached,
        "output_tokens": total_out,
        "cost_usd": round(total_cost, 6),
    }
