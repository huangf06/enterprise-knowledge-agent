"""HotpotQA distractor validation subset loader.

W1 lands the loader; W4 runs EM/F1 against it as a retrieval component sanity check.
This is NOT the project's main eval anchor — the cross-source self-authored eval is.
"""

from __future__ import annotations

import json
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "reference_baselines" / "hotpotqa"


def load_hotpotqa_subset(n: int = 100, seed: int = 42) -> list[dict]:
    """Return a seeded n-question random sample of HotpotQA distractor-validation.

    Results are cached at data/reference_baselines/hotpotqa/subset_n{n}_seed{seed}.json
    so a second call hits disk and does not require network access.
    """
    cache = CACHE_DIR / f"subset_n{n}_seed{seed}.json"
    if cache.exists():
        return json.loads(cache.read_text())

    from datasets import load_dataset

    ds = load_dataset("hotpot_qa", "distractor", split="validation")
    sampled = ds.shuffle(seed=seed).select(range(n))
    items = []
    for x in sampled:
        items.append(
            {
                "id": x["id"],
                "question": x["question"],
                "answer": x["answer"],
                "context": x["context"],
                "supporting_facts": x["supporting_facts"],
                "type": x.get("type"),
                "level": x.get("level"),
            }
        )
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(items, ensure_ascii=False))
    return items
