"""Official-style HotpotQA F1 / EM scoring.

Re-implements the normalization and token-level F1 from the upstream
`hotpot_evaluate_v1.py` script (https://github.com/hotpotqa/hotpot). Kept
self-contained so this repo does not need to vendor or import the reference
file.

Steps in `_normalize`:
  1. lowercase
  2. drop articles (a, an, the)
  3. strip punctuation
  4. collapse whitespace

F1 is token-level over the normalized prediction and gold answer. Yes/no
questions are scored by the same string match as the upstream script (HotpotQA
ships `yes` / `no` literally as the gold answer).
"""

from __future__ import annotations

import re
import string
from collections import Counter
from dataclasses import dataclass


def _normalize_answer(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    s = "".join(ch for ch in s if ch not in string.punctuation)
    return " ".join(s.split())


def _tokens(s: str) -> list[str]:
    return _normalize_answer(s).split()


def exact_match(prediction: str, gold: str) -> float:
    return 1.0 if _normalize_answer(prediction) == _normalize_answer(gold) else 0.0


def f1_score(prediction: str, gold: str) -> tuple[float, float, float]:
    """Return (f1, precision, recall) over normalized tokens."""
    pred_tokens = _tokens(prediction)
    gold_tokens = _tokens(gold)

    # Handle yes/no/noanswer the way the reference script does: if either side is
    # one of these literal strings, fall back to strict equality to avoid token
    # overlap with longer free-text answers inflating F1.
    sentinel = {"yes", "no", "noanswer"}
    if (
        _normalize_answer(prediction) in sentinel
        or _normalize_answer(gold) in sentinel
    ) and _normalize_answer(prediction) != _normalize_answer(gold):
        return 0.0, 0.0, 0.0

    if not pred_tokens and not gold_tokens:
        return 1.0, 1.0, 1.0
    if not pred_tokens or not gold_tokens:
        return 0.0, 0.0, 0.0

    common = Counter(pred_tokens) & Counter(gold_tokens)
    overlap = sum(common.values())
    if overlap == 0:
        return 0.0, 0.0, 0.0
    precision = overlap / len(pred_tokens)
    recall = overlap / len(gold_tokens)
    f1 = 2 * precision * recall / (precision + recall)
    return f1, precision, recall


@dataclass(frozen=True)
class ScoreResult:
    em: float
    f1: float
    precision: float
    recall: float


def score(prediction: str, gold: str) -> ScoreResult:
    f1, prec, rec = f1_score(prediction, gold)
    return ScoreResult(em=exact_match(prediction, gold), f1=f1, precision=prec, recall=rec)


__all__ = ["ScoreResult", "exact_match", "f1_score", "score"]
