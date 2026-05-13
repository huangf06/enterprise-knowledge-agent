#!/usr/bin/env python3
"""Frontier #1 DSPy compilation runner (Sprint 4).

NOT auto-invoked by anything; user runs this once during Sprint 4 with an
explicit budget check. Each MIPROv2 iteration spends roughly $0.05-0.15 of
Anthropic + OpenAI judge cost; default ITERATIONS=50 should land under $40.

Sanity-check budget before launching:
  uv run python scripts/dspy_compile.py --dry-run

Run real compilation:
  uv run python scripts/dspy_compile.py --iterations 50 --out src/agent/compiled/synthesize.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.agent.dspy_synthesize import (  # noqa: E402
    SynthesizeModule,
    configure_dspy_lm,
    make_training_metric,
)
from src.eval.scenarios import load_scenarios  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--iterations", type=int, default=50)
    p.add_argument("--dry-run", action="store_true", help="Build the program + metric but do not compile")
    p.add_argument("--out", default="src/agent/compiled/synthesize.json")
    p.add_argument(
        "--training-input",
        default=None,
        help="Path to eval JSON used as training data. Defaults to the most recent eval run with tool_history populated.",
    )
    args = p.parse_args()

    configure_dspy_lm()

    scenarios = load_scenarios()
    scenarios_by_id = {s.id: s for s in scenarios}
    metric = make_training_metric(scenarios_by_id)
    module = SynthesizeModule()

    print(f"DSPy scaffolded. n_scenarios={len(scenarios)}, iterations={args.iterations}")
    print(f"Training metric: 2-judge consensus (Haiku + gpt-4o-mini), P3 expected_topics redaction enabled.")
    print(f"DSPy LM: deepseek via litellm.")

    if args.dry_run:
        print("\n--dry-run: stopping before compilation.")
        return 0

    import dspy

    # Build training examples - actual answers come from a recent eval run.
    # Prefer the explicit --training-input; otherwise pick the most recent eval
    # JSON that has tool_history populated (which is what compiled prompts will
    # see at inference time). Older runs (pre commit 790e58e) lacked tool_history
    # and produced empty-context demos that the optimizer can't learn from.
    if args.training_input:
        candidates = [Path(args.training_input)]
    else:
        all_runs = sorted(
            (REPO_ROOT / "eval_results" / "runs").glob("eval-*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        candidates = [p for p in all_runs if "-multijudge" not in p.stem and "-ragas" not in p.stem]
    selected = None
    for p in candidates:
        try:
            sample = json.loads(p.read_text())
        except Exception:
            continue
        rows = sample.get("rows", [])
        with_history = sum(1 for r in rows if r.get("tool_history"))
        if with_history >= max(5, len(rows) // 3):
            selected = p
            break
    if selected is None:
        print("ERROR: no eval run with populated tool_history found; rerun scripts/run_eval.py first")
        return 2
    print(f"Training data: {selected.name} (tool_history populated)")
    data = json.loads(selected.read_text())

    examples = []
    for r in data["rows"]:
        sid = r["scenario_id"]
        sc = scenarios_by_id.get(sid)
        if sc is None or not r.get("ok"):
            continue
        tool_history_text = "\n".join(
            f"[{t['tool']}] {t.get('result', '')[:400]}" for t in r.get("tool_history", [])
        )
        examples.append(
            dspy.Example(
                query=sc.question,
                user_name=sc.user_name,
                user_role=sc.user_role,
                plan="(plan elided)",
                tool_history=tool_history_text,
                scenario_id=sid,
                actual_sources=r.get("tools_used", []),
            ).with_inputs("query", "user_name", "user_role", "plan", "tool_history")
        )

    print(f"Training set size: {len(examples)}")

    # Lightweight optimizer: BootstrapFewShotWithRandomSearch (lower spend than MIPROv2).
    from dspy.teleprompt import BootstrapFewShotWithRandomSearch

    teleprompter = BootstrapFewShotWithRandomSearch(
        metric=metric,
        max_bootstrapped_demos=4,
        num_candidate_programs=max(1, args.iterations // 10),
    )
    compiled = teleprompter.compile(module, trainset=examples)

    out_path = REPO_ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    compiled.save(str(out_path))
    print(f"saved: {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
