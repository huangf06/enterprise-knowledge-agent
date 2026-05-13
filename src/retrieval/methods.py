"""Retrieval methods for A1 ablation.

5 retrievers compared on the same passage pool per query:

  - bm25:               Sparse lexical BM25.
  - dense:              BGE-M3 cosine over normalized embeddings (existing baseline).
  - hybrid_rrf:         Reciprocal-rank fusion of BM25 + dense (weights configurable).
  - dense_plus_rerank:  Dense top-K, rerank with Cohere rerank-v3.5.
  - hybrid_plus_rerank: Hybrid top-K, rerank with Cohere rerank-v3.5.

All `*_search` functions return a list of int passage indices, descending by score.
"""

from __future__ import annotations

import os
import re
import threading
import time
from functools import lru_cache
from typing import Sequence

import numpy as np
from rank_bm25 import BM25Okapi

from src.retrieval.embeddings import embed

# Cohere trial key allows ~10 calls/minute. Throttle to ~9/min for safety.
_COHERE_MIN_INTERVAL_S = 7.0
_COHERE_LOCK = threading.Lock()
_COHERE_LAST_CALL_TS = 0.0

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(s: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(s)]


# ---------- sparse ----------


def bm25_search(query: str, passages: Sequence[str], top_k: int) -> list[int]:
    tokenized = [_tokenize(p) for p in passages]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(_tokenize(query))
    return np.argsort(scores)[::-1][:top_k].tolist()


# ---------- dense ----------


def dense_search(query: str, passages: Sequence[str], top_k: int) -> list[int]:
    pvecs = np.asarray(embed(list(passages)))
    qvec = np.asarray(embed([query])[0])
    scores = pvecs @ qvec  # both normalized
    return np.argsort(scores)[::-1][:top_k].tolist()


# ---------- hybrid (reciprocal rank fusion) ----------


def hybrid_rrf(
    query: str,
    passages: Sequence[str],
    top_k: int,
    rrf_k: int = 60,
    candidates: int = 50,
) -> list[int]:
    """Reciprocal Rank Fusion of BM25 + dense.

    Score for passage p = sum over rankers r of 1 / (rrf_k + rank_r(p)).
    The classic RRF constant `rrf_k = 60` (Cormack et al.) is provider-agnostic
    and works without per-corpus tuning.
    """
    cand = max(top_k, candidates)
    bm25_ranks = {idx: rank for rank, idx in enumerate(bm25_search(query, passages, cand))}
    dense_ranks = {idx: rank for rank, idx in enumerate(dense_search(query, passages, cand))}
    union = set(bm25_ranks) | set(dense_ranks)
    fused: list[tuple[int, float]] = []
    for idx in union:
        score = 0.0
        if idx in bm25_ranks:
            score += 1.0 / (rrf_k + bm25_ranks[idx])
        if idx in dense_ranks:
            score += 1.0 / (rrf_k + dense_ranks[idx])
        fused.append((idx, score))
    fused.sort(key=lambda x: x[1], reverse=True)
    return [idx for idx, _ in fused[:top_k]]


# ---------- Cohere rerank ----------


@lru_cache(maxsize=1)
def _cohere_client():
    import cohere

    key = os.environ.get("COHERE_API_KEY")
    if not key:
        return None
    return cohere.ClientV2(api_key=key)


def cohere_rerank(
    query: str,
    passages: Sequence[str],
    top_k: int,
    candidate_indices: Sequence[int],
    model: str = "rerank-v3.5",
) -> list[int]:
    """Rerank the supplied candidate indices using Cohere's rerank model.

    candidate_indices is the upstream retriever's shortlist; this function
    re-orders within that shortlist and returns top_k. Free-tier trial key
    allows ~10 calls/minute (1000/month) — we throttle to stay under that
    and back off on 429.
    """
    import cohere

    client = _cohere_client()
    if client is None:
        return list(candidate_indices)[:top_k]
    candidate_texts = [passages[i] for i in candidate_indices]

    def _do_call():
        global _COHERE_LAST_CALL_TS
        with _COHERE_LOCK:
            gap = time.monotonic() - _COHERE_LAST_CALL_TS
            if gap < _COHERE_MIN_INTERVAL_S:
                time.sleep(_COHERE_MIN_INTERVAL_S - gap)
            _COHERE_LAST_CALL_TS = time.monotonic()
        return client.rerank(
            model=model,
            query=query,
            documents=candidate_texts,
            top_n=top_k,
        )

    try:
        resp = _do_call()
    except cohere.errors.too_many_requests_error.TooManyRequestsError:
        time.sleep(65.0)
        resp = _do_call()
    out: list[int] = []
    for r in resp.results:
        out.append(candidate_indices[r.index])
    return out


# ---------- composed: dense / hybrid + rerank ----------


def dense_plus_rerank(
    query: str, passages: Sequence[str], top_k: int, candidates: int = 50
) -> list[int]:
    candidates = max(top_k, candidates)
    shortlist = dense_search(query, passages, candidates)
    return cohere_rerank(query, passages, top_k, shortlist)


def hybrid_plus_rerank(
    query: str, passages: Sequence[str], top_k: int, candidates: int = 50
) -> list[int]:
    candidates = max(top_k, candidates)
    shortlist = hybrid_rrf(query, passages, candidates, candidates=candidates)
    return cohere_rerank(query, passages, top_k, shortlist)


# Public dispatcher used by the ablation harness.
RETRIEVERS = {
    "bm25": bm25_search,
    "dense": dense_search,
    "hybrid_rrf": hybrid_rrf,
    "dense_plus_rerank": dense_plus_rerank,
    "hybrid_plus_rerank": hybrid_plus_rerank,
}
