"""A7 trace replay regression harness.

Compares two eval runs (gold vs candidate) on STRUCTURAL metrics only. The v4.1
plan P12 mandates that CI never invokes the LLM judge - that would burn the
$10/mo OpenAI cap in less than a week of PR traffic. The metrics here run off
the cached JSON fields:

  - tool_f1:           src/eval/trajectory.py tool-set precision/recall/F1
  - citation_groundedness: src/eval/citation.py - well_formedness / source_coverage / id_grounded
  - governance_compliance: scores.governance_compliance carried in the row

A scenario is flagged as a regression if any of the above metrics drop by more
than the per-metric threshold.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REGRESSION_THRESHOLDS = {
    "tool_f1": 0.10,
    "well_formedness": 0.10,
    "source_coverage": 0.10,
    "id_grounded": 0.15,
    "governance_compliance": 0.05,
}


def _row_metrics(row: dict[str, Any]) -> dict[str, float]:
    traj = row.get("trajectory") or {}
    cite = row.get("citations") or {}
    scores = row.get("scores") or {}
    return {
        "tool_f1": float(traj.get("tool_f1", 0.0)),
        "well_formedness": float(cite.get("well_formedness", 0.0)),
        "source_coverage": float(cite.get("source_coverage", 0.0)),
        "id_grounded": float(cite.get("id_grounded", 0.0)),
        "governance_compliance": float(scores.get("governance_compliance", 0.0)),
    }


def compare(gold_path: Path, candidate_path: Path) -> dict[str, Any]:
    """Diff per-scenario structural metrics between two eval JSONs."""
    gold = json.loads(gold_path.read_text())
    cand = json.loads(candidate_path.read_text())
    gold_rows = {r["scenario_id"]: r for r in gold["rows"]}
    cand_rows = {r["scenario_id"]: r for r in cand["rows"]}

    common = sorted(set(gold_rows) & set(cand_rows))
    missing_in_candidate = sorted(set(gold_rows) - set(cand_rows))
    new_in_candidate = sorted(set(cand_rows) - set(gold_rows))

    per_scenario_deltas: list[dict[str, Any]] = []
    regressions: list[dict[str, Any]] = []
    for sid in common:
        g = _row_metrics(gold_rows[sid])
        c = _row_metrics(cand_rows[sid])
        diffs = {k: round(c[k] - g[k], 4) for k in g}
        per_scenario_deltas.append({"scenario_id": sid, "gold": g, "candidate": c, "delta": diffs})
        flagged: list[str] = []
        for k, threshold in REGRESSION_THRESHOLDS.items():
            if g[k] - c[k] > threshold:
                flagged.append(k)
        if flagged:
            regressions.append({"scenario_id": sid, "regressed_on": flagged, "delta": diffs})

    return {
        "n_compared": len(common),
        "n_missing_in_candidate": len(missing_in_candidate),
        "n_new_in_candidate": len(new_in_candidate),
        "missing_in_candidate": missing_in_candidate,
        "new_in_candidate": new_in_candidate,
        "regressions": regressions,
        "n_regressions": len(regressions),
        "per_scenario": per_scenario_deltas,
        "thresholds": REGRESSION_THRESHOLDS,
    }


def is_pass(report: dict[str, Any]) -> bool:
    """A replay passes if no scenario regresses on any structural metric."""
    return report["n_regressions"] == 0 and report["n_missing_in_candidate"] == 0


__all__ = ["compare", "is_pass", "REGRESSION_THRESHOLDS"]
