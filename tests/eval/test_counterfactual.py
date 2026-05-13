"""Frontier #7 counterfactual perturbation tests."""

from src.eval.counterfactual import (
    apply_doc_deletion,
    apply_entity_swap,
    apply_noise_injection,
    perturb_tool_history,
)


def test_entity_swap_renames_third_party_companies():
    out = apply_entity_swap("The EY contract is up; PwC partnership intact.")
    assert "PwC contract" in out


def test_entity_swap_does_not_touch_protagonist_names():
    # R3 lock: Sarah stays Sarah.
    out = apply_entity_swap("Sarah Chen will lead the EY renewal.")
    assert "Sarah Chen" in out
    assert "PwC renewal" in out


def test_entity_swap_q3_to_q4():
    out = apply_entity_swap("Q3 launch deadline May 31")
    assert "Q4 launch" in out


def test_noise_injection_appends_block():
    base = "Original tool result."
    out = apply_noise_injection(base)
    assert base in out
    assert "[Background notes]" in out


def test_doc_deletion_drops_most_cited_paragraph():
    text = (
        "First para with [slack:m1] one citation.\n\n"
        "Second para [jira:p1] [jira:p2] two citations.\n\n"
        "Third para no citations."
    )
    out = apply_doc_deletion(text)
    # Most cited (second) dropped
    assert "Second para" not in out
    assert "First para" in out
    assert "Third para" in out


def test_perturb_tool_history_preserves_structure():
    history = [
        {"tool": "jira_query", "args": {}, "result": "Q3 launch info"},
        {"tool": "slack_query", "args": {}, "result": "EY contract update"},
    ]
    out = perturb_tool_history(history, mode="entity_swap")
    assert len(out) == 2
    assert "Q4 launch" in out[0]["result"]
    assert "PwC contract" in out[1]["result"]
    # Original untouched
    assert "Q3 launch info" in history[0]["result"]
    assert "EY contract update" in history[1]["result"]


def test_perturb_unknown_mode_raises():
    import pytest

    with pytest.raises(ValueError):
        perturb_tool_history([{"tool": "x", "args": {}, "result": "y"}], mode="invalid")
