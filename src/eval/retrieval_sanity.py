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
from src.llm.anthropic_client import messages_create
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


_HOTPOT_ANSWER_PROMPT = """You are answering HotpotQA-style multi-hop questions.

Use ONLY the passages below to answer. Give the SHORTEST possible answer — usually 1-5 words.
Never explain. Never restate the question. Just the answer string.

Passages:
{passages}

Question: {question}
Answer:"""


def _llm_short_answer(question: str, passages: list[str]) -> str:
    prompt = _HOTPOT_ANSWER_PROMPT.format(
        question=question,
        passages="\n\n".join(f"({i + 1}) {p}" for i, p in enumerate(passages)),
    )
    resp = messages_create(messages=[{"role": "user", "content": prompt}], max_tokens=128)
    return " ".join(b.text for b in resp.content if b.type == "text").strip()


def score_hotpotqa(n: int = 100, top_k: int = 2, mode: str = "naive") -> dict[str, float]:
    """Retrieve top-k passages per question, score EM/F1.

    Modes:
      "naive"      - cheap baseline: pick the retrieved sentence with the most
                     question-token overlap. Documented v1 limitation.
      "llm-answer" - one LLM call per question to extract a short answer from the
                     top-k passages. Closer to published HotpotQA baselines.
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
        retrieved_texts = [passages[int(i)][1] for i in ranked]
        if mode == "llm-answer":
            best = _llm_short_answer(question, retrieved_texts)
        else:
            retrieved = " ".join(retrieved_texts)
            sentences = re.split(r"(?<=[.!?])\s+", retrieved)
            q_tokens = set(_tokens(question))
            best, best_overlap = "", -1
            for sent in sentences:
                overlap = len(q_tokens & set(_tokens(sent)))
                if overlap > best_overlap:
                    best, best_overlap = sent, overlap
        em_sum += _em(best, gold)
        f1_sum += _f1(best, gold)
    return {
        "em": round(em_sum / len(items), 4),
        "f1": round(f1_sum / len(items), 4),
        "n": len(items),
        "mode": mode,
    }


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
