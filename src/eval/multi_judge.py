"""F3 multi-judge consensus + inter-judge agreement.

Runs the same scenario through multiple judges (DeepSeek + Anthropic Haiku +
OpenAI gpt-4o-mini by default) and reports:

  - per-judge JudgeScore
  - element-wise median consensus across judges that returned a score
  - per-metric dispersion (max - min across judges)
  - inter-judge pairwise Pearson correlation across all scored fields,
    aggregated over a list of scenarios (run_inter_judge_agreement below)

N1 contamination guard: callers reduce the judge pool when training (Sprint 4
DSPy compilation drops DeepSeek). The default pool here is the eval-time pool.
"""

from __future__ import annotations

import statistics
from typing import Iterable

from src.eval.judge import JUDGE_PROMPT
from src.eval.scenarios import Scenario
from src.llm.judge_client import JudgeScore, Provider, score

METRIC_KEYS = (
    "answer_correctness",
    "completeness",
    "tool_selection_quality",
    "governance_compliance",
    "action_recommend_quality",
)

DEFAULT_POOL: tuple[Provider, ...] = ("deepseek", "anthropic", "openai")
# Pool used during DSPy training (Sprint 4 N1 lock - drops DeepSeek to avoid
# rewarding hacks against the agent's own model class).
DSPY_TRAINING_POOL: tuple[Provider, ...] = ("anthropic", "openai")


def _format_prompt(scenario: Scenario, answer: str, actual_sources: list[str]) -> str:
    return JUDGE_PROMPT.format(
        scenario_id=scenario.id,
        category=scenario.category,
        question=scenario.question,
        difficulty=scenario.difficulty,
        expected_topics=scenario.expected_topics,
        expected_sources=scenario.expected_sources,
        actual_sources=actual_sources,
        governance_check=scenario.governance_check,
        expected_action=scenario.expected_action,
        answer=answer,
    )


def _median_consensus(scores_by_judge: dict[Provider, JudgeScore]) -> dict[str, float]:
    if not scores_by_judge:
        return {k: 0.0 for k in METRIC_KEYS}
    out: dict[str, float] = {}
    for k in METRIC_KEYS:
        vals = [getattr(s, k) for s in scores_by_judge.values()]
        out[k] = round(statistics.median(vals), 4)
    return out


def _dispersion(scores_by_judge: dict[Provider, JudgeScore]) -> dict[str, float]:
    if len(scores_by_judge) < 2:
        return {k: 0.0 for k in METRIC_KEYS}
    out: dict[str, float] = {}
    for k in METRIC_KEYS:
        vals = [getattr(s, k) for s in scores_by_judge.values()]
        out[k] = round(max(vals) - min(vals), 4)
    return out


def multi_judge(
    scenario: Scenario,
    answer: str,
    actual_sources: list[str],
    pool: Iterable[Provider] = DEFAULT_POOL,
) -> dict[str, object]:
    """Score `answer` with every judge in `pool`. Returns per-judge + consensus + dispersion."""
    prompt = _format_prompt(scenario, answer, actual_sources)
    per_judge: dict[Provider, JudgeScore] = {}
    failures: list[Provider] = []
    for provider in pool:
        s = score(prompt, provider=provider)
        if s is None:
            failures.append(provider)
        else:
            per_judge[provider] = s
    return {
        "per_judge": {p: s.model_dump() for p, s in per_judge.items()},
        "consensus": _median_consensus(per_judge),
        "dispersion": _dispersion(per_judge),
        "failures": list(failures),
        "n_judges": len(per_judge),
    }


def _pearson(xs: list[float], ys: list[float]) -> float:
    """Pearson correlation. Returns 0 when undefined (constant series)."""
    if len(xs) < 2 or len(xs) != len(ys):
        return 0.0
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = sum((x - mx) ** 2 for x in xs) ** 0.5
    deny = sum((y - my) ** 2 for y in ys) ** 0.5
    if denx == 0 or deny == 0:
        return 0.0
    return round(num / (denx * deny), 4)


def run_inter_judge_agreement(
    multi_judge_rows: list[dict[str, dict[str, float]]],
) -> dict[str, dict[str, float]]:
    """Compute pairwise Pearson correlation between judges across scenarios.

    Input: list of `per_judge` dicts (provider -> {metric: score}).
    Output: {"provider_a_vs_provider_b": {metric: pearson_r}}.
    """
    if not multi_judge_rows:
        return {}
    # Collect provider score series
    providers: set[str] = set()
    for row in multi_judge_rows:
        providers.update(row.keys())
    providers_sorted = sorted(providers)
    series: dict[str, dict[str, list[float]]] = {
        p: {k: [] for k in METRIC_KEYS} for p in providers_sorted
    }
    for row in multi_judge_rows:
        for p in providers_sorted:
            scores_dict = row.get(p)
            for k in METRIC_KEYS:
                series[p][k].append(scores_dict.get(k, 0.0) if scores_dict else 0.0)

    out: dict[str, dict[str, float]] = {}
    pairs = [
        (a, b)
        for i, a in enumerate(providers_sorted)
        for b in providers_sorted[i + 1 :]
    ]
    for a, b in pairs:
        per_metric: dict[str, float] = {}
        for k in METRIC_KEYS:
            per_metric[k] = _pearson(series[a][k], series[b][k])
        per_metric["mean"] = round(sum(per_metric.values()) / len(METRIC_KEYS), 4)
        out[f"{a}_vs_{b}"] = per_metric
    return out


__all__ = [
    "multi_judge",
    "run_inter_judge_agreement",
    "DEFAULT_POOL",
    "DSPY_TRAINING_POOL",
    "METRIC_KEYS",
]
