"""Loader tests for the HotpotQA full-agent benchmark.

These are separate from `test_hotpotqa_loader.py` (which exercises the HF
subset loader used by the retrieval-only sanity check). The full-agent path
uses `src/eval/hotpotqa_loader.py` and reads the raw dev distractor JSON.
"""

import json
from pathlib import Path

import pytest

from src.eval.hotpotqa_loader import RAW_PATH, _to_example, load_dev

pytestmark = pytest.mark.skipif(
    not RAW_PATH.exists(),
    reason="hotpot_dev_distractor_v1.json not cached; run the eval script once to fetch it.",
)


def test_load_dev_returns_first_n_in_source_order():
    a = load_dev(n=3)
    b = load_dev(n=3)
    assert [e.qid for e in a] == [e.qid for e in b]
    assert len(a) == 3


def test_example_has_ten_paragraphs_each():
    examples = load_dev(n=5)
    for ex in examples:
        assert len(ex.paragraphs) == 10
        assert all(isinstance(title, str) for title, _ in ex.paragraphs)
        assert all(isinstance(sents, list) for _, sents in ex.paragraphs)


def test_supporting_facts_titles_subset_of_paragraph_titles():
    examples = load_dev(n=5)
    for ex in examples:
        para_titles = set(ex.paragraph_titles())
        sf_titles = {t for t, _ in ex.supporting_facts}
        # The gold supporting paragraph titles must appear in the 10-paragraph pool
        # (this is the definition of the distractor split).
        assert sf_titles.issubset(para_titles), f"{ex.qid}: {sf_titles - para_titles}"


def test_to_example_handles_legacy_shape():
    raw = {
        "_id": "abc",
        "question": "q?",
        "answer": "ans",
        "context": [
            ["Title A", ["sent 1.", "sent 2."]],
            ["Title B", ["sent 3."]],
        ],
        "supporting_facts": [["Title A", 0]],
        "level": "hard",
        "type": "bridge",
    }
    ex = _to_example(raw)
    assert ex.qid == "abc"
    assert ex.paragraphs[0] == ("Title A", ["sent 1.", "sent 2."])
    assert ex.supporting_facts == [("Title A", 0)]


def test_raw_dev_file_is_a_json_array():
    # Sanity that we did not download a partial / HTML page.
    text = Path(RAW_PATH).read_text()[:1]
    assert text == "[", "Expected dev distractor file to start with a JSON array."
    # And the array is non-empty.
    data = json.loads(Path(RAW_PATH).read_text())
    assert len(data) > 1000
