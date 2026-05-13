"""F6 trajectory eval: tool-selection precision/recall/F1.

Set-based metric over distinct tool names. Standard for agent-trajectory
evaluation (BFCL v3 style, see docs/f6_trajectory_eval.md). Cheap and
deterministic; does not invoke an LLM.

Optional: trajectory_length score - bounded scenarios should not over-call
beyond what's necessary. Penalizes runaway tool loops.
"""

from __future__ import annotations

from typing import Iterable


def tool_set_prf(actual: Iterable[str], expected: Iterable[str]) -> dict[str, float | bool]:
    """Precision / Recall / F1 over the unordered set of tool names called."""
    a = set(actual)
    e = set(expected)
    if not e:
        return {
            "tool_precision": 1.0,
            "tool_recall": 1.0,
            "tool_f1": 1.0,
            "tool_exact_match": (not a),
        }
    if not a:
        return {
            "tool_precision": 0.0,
            "tool_recall": 0.0,
            "tool_f1": 0.0,
            "tool_exact_match": False,
        }
    tp = len(a & e)
    p = tp / len(a)
    r = tp / len(e)
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return {
        "tool_precision": round(p, 4),
        "tool_recall": round(r, 4),
        "tool_f1": round(f1, 4),
        "tool_exact_match": a == e,
    }


def trajectory_length_score(actual_calls: int, expected_unique_tools: int) -> dict[str, float | int]:
    """Penalize loops. Optimal length ~ expected unique tools; double counts as half score, etc."""
    if expected_unique_tools == 0:
        return {"trajectory_length_score": 1.0, "actual_calls": actual_calls, "expected_unique": expected_unique_tools}
    if actual_calls == 0:
        return {"trajectory_length_score": 0.0, "actual_calls": actual_calls, "expected_unique": expected_unique_tools}
    # ratio of expected to actual, capped at 1 (over-calling penalized, under-calling penalized symmetrically)
    ratio = min(actual_calls, expected_unique_tools) / max(actual_calls, expected_unique_tools)
    return {
        "trajectory_length_score": round(ratio, 4),
        "actual_calls": actual_calls,
        "expected_unique": expected_unique_tools,
    }


def trajectory_metrics(
    actual_tools: Iterable[str],
    expected_sources: Iterable[str],
    actual_call_count: int,
) -> dict[str, float | bool | int]:
    """Combined trajectory metric set."""
    expected_list = list(expected_sources)
    out: dict[str, float | bool | int] = {}
    out.update(tool_set_prf(actual_tools, expected_list))
    out.update(trajectory_length_score(actual_call_count, len(set(expected_list))))
    return out


__all__ = ["tool_set_prf", "trajectory_length_score", "trajectory_metrics"]
