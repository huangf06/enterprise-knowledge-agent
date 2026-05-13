"""A1 retrieval ablation: BM25 / dense / hybrid / +reranker on MS Marco subset.

Reports MRR@10 and NDCG@10 per retriever. Cohere rerank calls are skipped
if COHERE_API_KEY is not set.
"""

from __future__ import annotations

import math
from typing import Any

from src.eval.datasets.ms_marco import load_msmarco_subset
from src.retrieval.methods import RETRIEVERS


def _mrr(ranking: list[int], relevant: set[int], k: int) -> float:
    for rank, idx in enumerate(ranking[:k], start=1):
        if idx in relevant:
            return 1.0 / rank
    return 0.0


def _ndcg(ranking: list[int], relevant: set[int], k: int) -> float:
    dcg = 0.0
    for rank, idx in enumerate(ranking[:k], start=1):
        if idx in relevant:
            dcg += 1.0 / math.log2(rank + 1)
    ideal_count = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(r + 1) for r in range(1, ideal_count + 1))
    return dcg / idcg if idcg > 0 else 0.0


def score_retriever(name: str, items: list[dict], top_k: int = 10) -> dict[str, Any]:
    retriever = RETRIEVERS[name]
    mrr_sum = 0.0
    ndcg_sum = 0.0
    n = 0
    for x in items:
        relevant = set(x["relevant_passage_indices"])
        if not relevant:
            continue
        texts = [p["text"] for p in x["passages"]]
        ranking = retriever(x["query"], texts, top_k=top_k)
        mrr_sum += _mrr(ranking, relevant, top_k)
        ndcg_sum += _ndcg(ranking, relevant, top_k)
        n += 1
    return {
        "method": name,
        "n": n,
        "mrr@10": round(mrr_sum / n, 4) if n else 0.0,
        "ndcg@10": round(ndcg_sum / n, 4) if n else 0.0,
    }


def run_ablation(n_queries: int = 50, top_k: int = 10, methods: list[str] | None = None) -> list[dict[str, Any]]:
    items = load_msmarco_subset(n=n_queries)
    methods = methods or list(RETRIEVERS)
    rows: list[dict[str, Any]] = []
    for m in methods:
        rows.append(score_retriever(m, items, top_k=top_k))
    return rows
