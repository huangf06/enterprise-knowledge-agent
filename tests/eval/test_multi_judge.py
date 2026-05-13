"""F3 multi-judge unit tests (LLM calls stubbed out)."""

from src.eval.multi_judge import (
    DEFAULT_POOL,
    DSPY_TRAINING_POOL,
    METRIC_KEYS,
    run_inter_judge_agreement,
)


def test_default_pool_has_three_providers():
    assert "deepseek" in DEFAULT_POOL
    assert "anthropic" in DEFAULT_POOL
    assert "openai" in DEFAULT_POOL


def test_dspy_training_pool_excludes_deepseek_per_n1():
    assert "deepseek" not in DSPY_TRAINING_POOL
    assert "anthropic" in DSPY_TRAINING_POOL
    assert "openai" in DSPY_TRAINING_POOL


def test_metric_keys_are_rubric_fields():
    assert set(METRIC_KEYS) == {
        "answer_correctness",
        "completeness",
        "tool_selection_quality",
        "governance_compliance",
        "action_recommend_quality",
    }


def test_inter_judge_agreement_perfect_correlation():
    rows = [
        {
            "deepseek": {k: 1.0 for k in METRIC_KEYS},
            "anthropic": {k: 1.0 for k in METRIC_KEYS},
        },
        {
            "deepseek": {k: 0.5 for k in METRIC_KEYS},
            "anthropic": {k: 0.5 for k in METRIC_KEYS},
        },
        {
            "deepseek": {k: 0.0 for k in METRIC_KEYS},
            "anthropic": {k: 0.0 for k in METRIC_KEYS},
        },
    ]
    out = run_inter_judge_agreement(rows)
    # Constant agreement -> r = 1.0 on each varying metric
    pair = out["anthropic_vs_deepseek"]
    for k in METRIC_KEYS:
        assert pair[k] == 1.0


def test_inter_judge_agreement_handles_constant_series():
    # When one rater is constant the correlation is undefined; helper returns 0.
    rows = [
        {"deepseek": {k: 1.0 for k in METRIC_KEYS}, "anthropic": {k: 0.5 for k in METRIC_KEYS}},
        {"deepseek": {k: 1.0 for k in METRIC_KEYS}, "anthropic": {k: 0.9 for k in METRIC_KEYS}},
    ]
    out = run_inter_judge_agreement(rows)
    for k in METRIC_KEYS:
        assert out["anthropic_vs_deepseek"][k] == 0.0
