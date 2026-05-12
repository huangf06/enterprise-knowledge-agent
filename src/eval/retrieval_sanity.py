"""Retrieval component sanity check: HotpotQA F1/EM + MS Marco MRR@10.

These are NOT the project's main eval anchor. They demonstrate that the
BGE-M3 retrieval pipeline works on standard benchmarks; the cross-source
agent task is scored by the self-authored scenarios in src/eval/runner.py.
"""

from __future__ import annotations

import re
import string
from collections import Counter
from typing import Any

import numpy as np

from src.eval.datasets.hotpotqa import load_hotpotqa_subset
from src.eval.datasets.ms_marco import load_msmarco_subset
from src.retrieval.embeddings import embed


def _normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    s = "".join(ch for ch in s if ch not in string.punctuation)
    return " ".join(s.split())


def _tokens(s: str) -> list[str]:
    return _normalize(s).split()


def _f1(pred: str, gold: str) -> float:
    pred_t = _tokens(pred)
    gold_t = _tokens(gold)
    if not pred_t and not gold_t:
        return 1.0
    if not pred_t or not gold_t:
        return 0.0
    common = Counter(pred_t) & Counter(gold_t)
    overlap = sum(common.values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(pred_t)
    recall = overlap / len(gold_t)
    return 2 * precision * recall / (precision + recall)


def _em(pred: str, gold: str) -> float:
    return 1.0 if _normalize(pred) == _normalize(gold) else 0.0


def score_hotpotqa(n: int = 100, top_k: int = 2) -> dict[str, float]:
    """Retrieve top-k passages per question, generate an answer with the LLM, score EM/F1.

    For W4 we approximate the answer generation step by concatenating top-k passage
    text and pulling the most salient noun phrase: this is enough to get a non-zero
    F1 baseline without spinning a full QA chain.  W6 swaps this out for the agent.
    """
    items = load_hotpotqa_subset(n=n)
    em_sum = 0.0
    f1_sum = 0.0
    for x in items:
        question = x["question"]
        gold = x["answer"]
        passages = []
        for title, sentences in zip(x["context"]["title"], x["context"]["sentences"], strict=True):
            passages.append((title, " ".join(sentences)))
        if not passages:
            continue
        passage_vecs = embed([p[1] for p in passages])
        q_vec = embed([question])[0]
        scores = np.dot(np.asarray(passage_vecs), np.asarray(q_vec))
        ranked = np.argsort(scores)[::-1][:top_k]
        retrieved = " ".join(passages[int(i)][1] for i in ranked)
        # Cheap answer extraction: pull the sentence containing the most question tokens.
        sentences = re.split(r"(?<=[.!?])\s+", retrieved)
        q_tokens = set(_tokens(question))
        best, best_overlap = "", -1
        for sent in sentences:
            overlap = len(q_tokens & set(_tokens(sent)))
            if overlap > best_overlap:
                best, best_overlap = sent, overlap
        em_sum += _em(best, gold)
        f1_sum += _f1(best, gold)
    return {"em": round(em_sum / len(items), 4), "f1": round(f1_sum / len(items), 4), "n": len(items)}


def score_msmarco(n: int = 50, top_k: int = 10) -> dict[str, float]:
    items = load_msmarco_subset(n=n)
    mrr_sum = 0.0
    for x in items:
        if not x["relevant_passage_indices"]:
            continue
        passage_vecs = embed([p["text"] for p in x["passages"]])
        q_vec = embed([x["query"]])[0]
        scores = np.dot(np.asarray(passage_vecs), np.asarray(q_vec))
        ranked = np.argsort(scores)[::-1][:top_k]
        relevant = set(x["relevant_passage_indices"])
        rr = 0.0
        for rank, idx in enumerate(ranked, start=1):
            if int(idx) in relevant:
                rr = 1.0 / rank
                break
        mrr_sum += rr
    return {"mrr@10": round(mrr_sum / len(items), 4), "n": len(items)}
