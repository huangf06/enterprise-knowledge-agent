"""Tests for the F1 JudgeScore extractor.

The regex JSON path now lives in `src.llm.judge_client._extract_score_from_text`
and returns a Pydantic JudgeScore (or None) instead of a raw dict. These tests
verify the fallback path still extracts cleanly when an endpoint emits prose +
JSON instead of a tool_use block.
"""

from src.llm.judge_client import JudgeScore, _extract_score_from_text


_RUBRIC_KEYS = (
    "answer_correctness",
    "completeness",
    "tool_selection_quality",
    "governance_compliance",
    "action_recommend_quality",
)


def _build(scores: dict[str, float]) -> str:
    import json

    return json.dumps({k: scores.get(k, 0.0) for k in _RUBRIC_KEYS})


def test_extract_flat_json():
    payload = _build({"answer_correctness": 1.0, "completeness": 0.5})
    out = _extract_score_from_text(payload)
    assert isinstance(out, JudgeScore)
    assert out.answer_correctness == 1.0
    assert out.completeness == 0.5


def test_extract_with_prose_around():
    payload = _build({"answer_correctness": 0.8, "completeness": 0.7})
    text = f"Sure, here is the score: {payload} done."
    out = _extract_score_from_text(text)
    assert isinstance(out, JudgeScore)
    assert out.answer_correctness == 0.8


def test_extract_with_markdown_fence():
    payload = _build({"answer_correctness": 0.3, "completeness": 0.3, "tool_selection_quality": 1.0})
    text = f"```json\n{payload}\n```"
    out = _extract_score_from_text(text)
    assert isinstance(out, JudgeScore)
    assert out.answer_correctness == 0.3
    assert out.tool_selection_quality == 1.0


def test_extract_returns_none_on_no_json():
    assert _extract_score_from_text("just words") is None


def test_extract_returns_none_on_invalid_schema():
    # JSON parses but does not match JudgeScore (missing required fields).
    assert _extract_score_from_text('{"a": 1.0, "meta": {"k": "v"}}') is None


def test_extract_validates_range():
    # Out-of-range value fails Pydantic validation -> None.
    bad = '{"answer_correctness": 2.0, "completeness": 0, "tool_selection_quality": 0, "governance_compliance": 0, "action_recommend_quality": 0}'
    assert _extract_score_from_text(bad) is None
