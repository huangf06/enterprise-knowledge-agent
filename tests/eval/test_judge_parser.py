from src.eval.judge import _extract_json


def test_extract_flat_json():
    text = '{"a": 1.0, "b": 0.5}'
    assert _extract_json(text) == {"a": 1.0, "b": 0.5}


def test_extract_with_prose_around():
    text = 'Sure, here is the score: {"answer_correctness": 0.8, "completeness": 0.7} done.'
    out = _extract_json(text)
    assert out["answer_correctness"] == 0.8


def test_extract_with_markdown_fence():
    text = "```json\n{\"x\": 0.3}\n```"
    assert _extract_json(text) == {"x": 0.3}


def test_extract_returns_none_on_no_json():
    assert _extract_json("just words") is None


def test_extract_balanced_nested_object():
    text = '{"a": 1.0, "meta": {"k": "v"}}'
    out = _extract_json(text)
    assert out["a"] == 1.0
    assert out["meta"] == {"k": "v"}
