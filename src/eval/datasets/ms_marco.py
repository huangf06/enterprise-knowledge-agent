"""MS Marco passage retrieval validation subset loader.

W1 lands the loader; W4 runs MRR@10 against it as a retrieval component sanity check.
This is NOT the project's main eval anchor — the cross-source self-authored eval is.
"""

from __future__ import annotations

import json
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "reference_baselines" / "ms_marco"


def load_msmarco_subset(n: int = 50, seed: int = 42) -> list[dict]:
    """Return a seeded n-query random sample of MS Marco v2.1 validation.

    Each item: {"query_id", "query", "passages", "relevant_passage_indices"}.
    Cached at data/reference_baselines/ms_marco/subset_n{n}_seed{seed}.json.
    """
    cache = CACHE_DIR / f"subset_n{n}_seed{seed}.json"
    if cache.exists():
        return json.loads(cache.read_text())

    from datasets import load_dataset

    ds = load_dataset("microsoft/ms_marco", "v2.1", split="validation")
    ds = ds.filter(lambda x: any(s == 1 for s in x["passages"]["is_selected"]))
    sampled = ds.shuffle(seed=seed).select(range(n))
    items = []
    for x in sampled:
        passages = x["passages"]
        relevant = [i for i, sel in enumerate(passages["is_selected"]) if sel == 1]
        items.append(
            {
                "query_id": x["query_id"],
                "query": x["query"],
                "passages": [
                    {"text": txt, "is_selected": bool(sel), "url": url}
                    for txt, sel, url in zip(
                        passages["passage_text"],
                        passages["is_selected"],
                        passages["url"],
                        strict=True,
                    )
                ],
                "relevant_passage_indices": relevant,
            }
        )
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(items, ensure_ascii=False))
    return items
