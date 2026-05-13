"""F6 trajectory metric unit tests."""

from src.eval.trajectory import (
    tool_set_prf,
    trajectory_length_score,
    trajectory_metrics,
)


def test_exact_match():
    out = tool_set_prf(["a", "b"], ["a", "b"])
    assert out["tool_f1"] == 1.0
    assert out["tool_exact_match"] is True


def test_missing_one_tool():
    out = tool_set_prf(["a"], ["a", "b"])
    assert out["tool_precision"] == 1.0
    assert out["tool_recall"] == 0.5
    assert abs(out["tool_f1"] - 2 / 3) < 1e-3


def test_extra_tool():
    out = tool_set_prf(["a", "b", "c"], ["a", "b"])
    assert abs(out["tool_precision"] - 2 / 3) < 1e-3
    assert out["tool_recall"] == 1.0


def test_empty_actual():
    out = tool_set_prf([], ["a"])
    assert out["tool_f1"] == 0.0
    assert out["tool_exact_match"] is False


def test_empty_expected_with_no_actual_is_match():
    out = tool_set_prf([], [])
    assert out["tool_exact_match"] is True
    assert out["tool_f1"] == 1.0


def test_length_score_optimal():
    out = trajectory_length_score(2, 2)
    assert out["trajectory_length_score"] == 1.0


def test_length_score_overcall_penalty():
    out = trajectory_length_score(4, 2)
    assert out["trajectory_length_score"] == 0.5


def test_combined_metric_includes_both_groups():
    out = trajectory_metrics(["a", "b"], ["a", "b"], actual_call_count=3)
    assert "tool_f1" in out and out["tool_f1"] == 1.0
    assert "trajectory_length_score" in out
    # 3 actual calls vs 2 expected unique = 2/3 ratio
    assert abs(out["trajectory_length_score"] - 2 / 3) < 1e-3
