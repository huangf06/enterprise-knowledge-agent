"""Adapter-level unit tests for the HotpotQA agent.

These tests cover the parts that don't need an LLM: the single-tool
registry swap (must restore the default six tools after exit) and the
`retrieve_passage` tool's ranking against a synthetic 10-paragraph pool.
"""

from __future__ import annotations

import numpy as np

from src.eval.hotpotqa_agent import (
    RetrieveContext,
    _RETRIEVE_TOOL,
    _retrieve_run,
    _set_active,
    _single_tool_registry,
)
from src.eval.hotpotqa_loader import HotpotQAExample
from src.tools import registry


def _make_example() -> HotpotQAExample:
    return HotpotQAExample(
        qid="t1",
        question="Where was Marie Curie born?",
        answer="Warsaw",
        paragraphs=[(f"Title {i}", [f"Paragraph {i} body."]) for i in range(10)],
        supporting_facts=[("Title 0", 0)],
        level="medium",
        qtype="bridge",
    )


def test_single_tool_registry_swaps_and_restores():
    before = set(registry().names())
    assert "retrieve_passage" not in before
    with _single_tool_registry():
        names = set(registry().names())
        assert names == {"retrieve_passage"}
    after = set(registry().names())
    assert after == before
    assert "retrieve_passage" not in after


def test_single_tool_registry_restores_on_exception():
    before = set(registry().names())
    try:
        with _single_tool_registry():
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    after = set(registry().names())
    assert after == before


def test_retrieve_run_errors_when_no_active_context():
    _set_active(None)
    out = _retrieve_run({"query": "anything"}, {})
    assert out.startswith("ERROR")


def test_retrieve_run_returns_top_k_passages(monkeypatch):
    """With a stubbed embedder the ranking should put the on-topic paragraph first."""
    ex = _make_example()
    rctx = RetrieveContext(example=ex, top_k=3)

    # Stub embed: the i-th paragraph gets a unit vector in axis i; the query
    # is biased toward axis 0. Cosine for paragraph 0 is highest.
    def fake_embed(texts):
        if len(texts) == 1 and texts[0] == ex.question:
            return [[1.0] + [0.0] * 9]
        out = []
        for i in range(len(texts)):
            vec = [0.0] * 10
            vec[i] = 1.0
            out.append(vec)
        return out

    monkeypatch.setattr("src.eval.hotpotqa_agent.embed", fake_embed)

    _set_active(rctx)
    try:
        result = _retrieve_run({"query": ex.question, "top_k": 3}, {})
    finally:
        _set_active(None)
    assert "passage 1" in result
    assert "passage 2" in result
    assert "passage 3" in result
    # Top-ranked passage should be index 0 (highest cosine in the stub).
    first_block = result.split("[passage 2]")[0]
    assert "idx=0" in first_block


def test_retrieve_tool_schema_well_formed():
    schema = _RETRIEVE_TOOL.schema_dict()
    assert schema["name"] == "retrieve_passage"
    assert "query" in schema["input_schema"]["properties"]
    assert "top_k" in schema["input_schema"]["properties"]
    assert schema["input_schema"]["required"] == ["query"]
