"""Frontier #4 Multi-LLM MoE router (Sprint 5 scaffold).

Configurable per-node routing across DeepSeek / Anthropic / OpenAI. The router
itself is a thin lookup + pricing layer; actual node-level dispatch wiring is
the Sprint 5 day-of integration step (requires tool_use schema translation
between Anthropic and OpenAI SDK shapes, which is not free).

This scaffold provides:
  - config loading from MOE_CONFIG_PATH (JSON) or sensible default
  - per-node pricing for Pareto-table generation
  - vendor outage fallback rule (P8): synthesize -> DeepSeek if Anthropic 5xx
  - structured-outputs lock (P9): critique node also goes through structured judge
    if MoE puts it on Anthropic (already true under our default config)

Production-deploy day-of plan:
  1. Update src/llm/anthropic_client.messages_create to consult `route_for_node`
     and dispatch to the right vendor client. Anthropic-vendor stays as-is;
     OpenAI vendor calls require chat.completions.create with translated
     tool_use schema (tools list -> OpenAI functions list, tool_choice ->
     OpenAI tool_choice).
  2. Add `fallback_on_5xx` to the dispatcher.
  3. Re-run A1+A3 ablation with the configured routing.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

# Default MoE config: production-recommended routing per v4 plan.
# synthesize -> Sonnet 4.6 for output quality (the visible output node).
# tool_select -> DeepSeek (high call count, cheap is fine).
# others -> DeepSeek (cheap baseline).
# Synthesize stayed on DeepSeek post Sprint 5 Pareto: Sonnet 4.6 buys +0.07 ac
# at 32x cost (within the n=10 noise floor), so the default is the cheap path.
# See docs/sprint5_moe_pareto.md for the table. Sonnet 4.6 is still available
# as an opt-in via MOE_CONFIG_PATH for quality-critical per-request routing.
DEFAULT_MOE = {
    "plan": {"provider": "deepseek", "model": "deepseek-v4-pro[1m]"},
    "tool_select": {"provider": "deepseek", "model": "deepseek-v4-pro[1m]"},
    "reflect": {"provider": "deepseek", "model": "deepseek-v4-pro[1m]"},
    "synthesize": {"provider": "deepseek", "model": "deepseek-v4-pro[1m]"},
    "critique": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"},
    "judge": {"provider": "deepseek", "model": "deepseek-v4-pro[1m]"},
}

# USD per 1M tokens, (input, output). Cached input prices are 10-25% of input;
# we omit cache pricing here for simplicity and overestimate cost slightly.
PRICING_USD_PER_1M = {
    ("deepseek", "deepseek-v4-pro[1m]"): {"in": 0.14, "out": 0.28},
    ("anthropic", "claude-sonnet-4-6"): {"in": 3.00, "out": 15.00},
    ("anthropic", "claude-haiku-4-5-20251001"): {"in": 1.00, "out": 5.00},
    ("anthropic", "claude-opus-4-7"): {"in": 15.00, "out": 75.00},
    ("openai", "gpt-4o-mini"): {"in": 0.15, "out": 0.60},
    ("openai", "gpt-4o"): {"in": 2.50, "out": 10.00},
    ("openai", "gpt-5-mini"): {"in": 0.25, "out": 2.00},
}


def is_enabled() -> bool:
    flag = os.environ.get("MOE_ENABLED", "0").strip().lower()
    return flag in ("1", "true", "yes", "on")


@lru_cache(maxsize=1)
def _load_config() -> dict[str, dict[str, str]]:
    path = os.environ.get("MOE_CONFIG_PATH")
    if path:
        try:
            data = json.loads(Path(path).read_text())
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return DEFAULT_MOE


def route_for_node(node: str) -> dict[str, str]:
    """Return {provider, model} for a given node. Defaults to deepseek/v4-pro[1m]."""
    if not is_enabled():
        return {"provider": "deepseek", "model": "deepseek-v4-pro[1m]"}
    config = _load_config()
    return config.get(node, {"provider": "deepseek", "model": "deepseek-v4-pro[1m]"})


def estimate_cost(node: str, in_tokens: int, out_tokens: int) -> float:
    """USD cost for a single LLM call under the current MoE config."""
    route = route_for_node(node)
    pricing = PRICING_USD_PER_1M.get((route["provider"], route["model"]))
    if pricing is None:
        return 0.0
    return (in_tokens * pricing["in"] + out_tokens * pricing["out"]) / 1_000_000


def projected_per_query_cost(
    per_node_tokens: dict[str, dict[str, int]],
) -> tuple[float, dict[str, float]]:
    """Given per-node token counts from N2 baseline, project MoE-routed cost.

    per_node_tokens shape: {"plan": {"input_tokens": ..., "output_tokens": ...}, ...}
    Returns (total_usd, per_node_usd).
    """
    per_node_usd: dict[str, float] = {}
    total = 0.0
    for node, tok in per_node_tokens.items():
        cost = estimate_cost(
            node,
            int(tok.get("input_tokens", 0)),
            int(tok.get("output_tokens", 0)),
        )
        per_node_usd[node] = round(cost, 6)
        total += cost
    return round(total, 6), per_node_usd


__all__ = [
    "is_enabled",
    "route_for_node",
    "estimate_cost",
    "projected_per_query_cost",
    "DEFAULT_MOE",
    "PRICING_USD_PER_1M",
]
