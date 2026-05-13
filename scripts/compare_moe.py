#!/usr/bin/env python3
"""Frontier #4 MoE Pareto: render the cost-vs-quality table across routes.

Reads the moe-synthesize JSON (4 routes × N scenarios) and emits a Pareto
table sized for `docs/sprint5_moe_pareto.md` / README. The interesting columns
are (quality, cost-per-query, latency); the recommendation column flags which
route lies on the Pareto frontier.

Usage:
  uv run python scripts/compare_moe.py \\
    --input eval_results/runs/moe-synthesize-<stamp>.json \\
    --out docs/sprint5_moe_pareto.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

ROUTE_LABEL = {
    "deepseek": "DeepSeek V4 Pro (baseline)",
    "anthropic_sonnet": "Anthropic Sonnet 4.6",
    "anthropic_haiku": "Anthropic Haiku 4.5",
    "openai_gpt4o_mini": "OpenAI gpt-4o-mini",
}


def _pareto(routes: list[dict]) -> set[str]:
    """Return route names on the (max quality, min cost, min latency) frontier."""
    on_frontier: set[str] = set()
    for r in routes:
        dominated = False
        for s in routes:
            if s["route"] == r["route"]:
                continue
            if (
                s["quality"] >= r["quality"]
                and s["cost"] <= r["cost"]
                and s["latency"] <= r["latency"]
                and (
                    s["quality"] > r["quality"]
                    or s["cost"] < r["cost"]
                    or s["latency"] < r["latency"]
                )
            ):
                dominated = True
                break
        if not dominated:
            on_frontier.add(r["route"])
    return on_frontier


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--out", default=None)
    args = p.parse_args()

    data = json.loads(Path(args.input).read_text())
    summary = data.get("summary", {})
    routes_in_order = data.get("routes", list(summary.keys()))

    routes_for_pareto = []
    for route in routes_in_order:
        s = summary.get(route, {})
        if not s:
            continue
        routes_for_pareto.append(
            {
                "route": route,
                "quality": s.get("answer_correctness", 0.0),
                "cost": s.get("avg_cost_usd", 0.0),
                "latency": s.get("avg_elapsed_s", 0.0),
            }
        )
    frontier = _pareto(routes_for_pareto)

    lines = [
        "# Sprint 5 Frontier #4 MoE — synthesize-only Pareto",
        "",
        f"Source: `{Path(args.input).name}` (tier={data.get('tier')}, "
        f"n_scenarios per route = baseline rows with `ok==True`).",
        "",
        "Each route receives the same `tool_history` from the baseline run and the",
        "same `synthesize` prompt. The only changed variable is the vendor + model.",
        "Quality is single-judge for now; multi-judge consensus addendum follows",
        "if `scripts/run_multi_judge.py` is run on this file.",
        "",
        "| Route | Quality (ac) | Compl. | Cite-grounded | Cost / query | Latency (s) | Pareto? |",
        "|---|---:|---:|---:|---:|---:|:---:|",
    ]
    for route in routes_in_order:
        s = summary.get(route, {})
        if not s:
            continue
        label = ROUTE_LABEL.get(route, route)
        pareto_marker = "✓" if route in frontier else " "
        lines.append(
            f"| {label} | {s.get('answer_correctness', 0):.4f} | "
            f"{s.get('completeness', 0):.4f} | "
            f"{s.get('cite_id_grounded', 0):.4f} | "
            f"${s.get('avg_cost_usd', 0):.6f} | "
            f"{s.get('avg_elapsed_s', 0):.1f} | "
            f"{pareto_marker} |"
        )

    lines.append("")
    lines.append("## Reading the table")
    lines.append("")
    lines.append(
        "**Pareto frontier**: any route that is not strictly dominated on all three of "
        "(quality, cost, latency) by another route. A `✓` does NOT mean \"best\" — it "
        "means \"a defensible pick depending on what you value\"."
    )
    lines.append("")
    lines.append(
        "The headline question is: **does the more expensive vendor actually buy a "
        "meaningful quality lift on the synthesize node?** Compare DeepSeek baseline "
        "to Anthropic Sonnet 4.6 (12× input cost, 53× output cost) and report whether "
        "the answer_correctness delta justifies the spend."
    )
    lines.append("")
    lines.append(
        "Caveat: n=10 has roughly a ±0.07 noise floor on answer_correctness; any "
        "claimed lift smaller than that is not statistically meaningful at this scale. "
        "A v1.5 follow-up with n=30 + 95% bootstrap CI is the way to firm this up if "
        "the headline number looks promising."
    )

    out_md = "\n".join(lines)
    print(out_md)
    if args.out:
        Path(args.out).write_text(out_md + "\n")
        print(f"\nsaved: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
