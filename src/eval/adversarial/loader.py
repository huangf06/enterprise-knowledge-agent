"""Adversarial scenarios loader. Each scenario tests a cross-source attack vector."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

ADV_PATH = Path(__file__).resolve().parents[3] / "data" / "eval" / "adversarial.json"


class AdversarialScenario(BaseModel):
    id: str
    vector: str
    question: str
    user_name: str
    user_role: str
    forbidden_substrings: list[str] = Field(
        default_factory=list,
        description="If any of these appear in the final answer, the test fails.",
    )
    required_refusal_signals: list[str] = Field(
        default_factory=list,
        description="The answer should contain at least one of these (denial, RBAC, refusal, etc.).",
    )


def load_adversarial() -> list[AdversarialScenario]:
    items = json.loads(ADV_PATH.read_text())
    return [AdversarialScenario(**i) for i in items]
