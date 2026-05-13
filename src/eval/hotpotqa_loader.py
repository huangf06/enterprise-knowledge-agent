"""HotpotQA dev distractor loader for the full-agent benchmark.

Downloads `hotpot_dev_distractor_v1.json` from the official CMU mirror and
caches it under `data/eval/hotpotqa/` (gitignored). The benchmark protocol
calls for the first n examples in source order, no shuffling, so results are
byte-reproducible across runs and machines.

Each example ships with 10 candidate paragraphs (2 gold supporting + 8
distractors). The agent retrieves from this 10-paragraph pool, never from
full Wikipedia.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DEV_DISTRACTOR_URL = (
    "http://curtis.ml.cmu.edu/datasets/hotpot/hotpot_dev_distractor_v1.json"
)
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "eval" / "hotpotqa"
RAW_PATH = CACHE_DIR / "hotpot_dev_distractor_v1.json"


@dataclass(frozen=True)
class HotpotQAExample:
    qid: str
    question: str
    answer: str
    paragraphs: list[tuple[str, list[str]]]  # (title, sentences) pairs, 10 per example
    supporting_facts: list[tuple[str, int]]  # (title, sent_id) pairs
    level: str | None
    qtype: str | None

    def paragraph_texts(self) -> list[str]:
        """Concatenate each paragraph's sentences into a single text blob."""
        return [" ".join(sents) for _, sents in self.paragraphs]

    def paragraph_titles(self) -> list[str]:
        return [title for title, _ in self.paragraphs]


def _download_raw() -> Path:
    """Fetch the dev distractor JSON to disk if not already cached."""
    if RAW_PATH.exists() and RAW_PATH.stat().st_size > 0:
        return RAW_PATH
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = RAW_PATH.with_suffix(".json.partial")
    urllib.request.urlretrieve(DEV_DISTRACTOR_URL, tmp)
    tmp.rename(RAW_PATH)
    return RAW_PATH


def _to_example(raw: dict) -> HotpotQAExample:
    ctx = raw.get("context", [])
    paragraphs: list[tuple[str, list[str]]] = []
    for entry in ctx:
        # Raw format: [title, [sent1, sent2, ...]]
        if not isinstance(entry, list) or len(entry) != 2:
            continue
        title, sentences = entry[0], entry[1]
        if not isinstance(sentences, list):
            continue
        paragraphs.append((str(title), [str(s) for s in sentences]))
    sf_raw = raw.get("supporting_facts", []) or []
    supporting_facts: list[tuple[str, int]] = []
    for entry in sf_raw:
        if isinstance(entry, list) and len(entry) == 2:
            supporting_facts.append((str(entry[0]), int(entry[1])))
    return HotpotQAExample(
        qid=str(raw["_id"]),
        question=str(raw["question"]),
        answer=str(raw["answer"]),
        paragraphs=paragraphs,
        supporting_facts=supporting_facts,
        level=raw.get("level"),
        qtype=raw.get("type"),
    )


def load_dev(n: int = 100) -> list[HotpotQAExample]:
    """Return the first n examples from the dev distractor split in source order."""
    path = _download_raw()
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        raise ValueError(f"Unexpected HotpotQA dev distractor shape: {type(raw)}")
    examples: list[HotpotQAExample] = []
    for entry in raw[:n]:
        examples.append(_to_example(entry))
    return examples


__all__ = ["HotpotQAExample", "load_dev"]
