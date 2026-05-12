"""Loader for the 30 self-authored cross-source scenarios."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

SCENARIOS_PATH = Path(__file__).resolve().parents[3] / "data" / "eval" / "scenarios.json"


class Scenario(BaseModel):
    id: str
    category: str
    question: str
    user_name: str
    user_role: str
    expected_sources: list[str]
    expected_topics: list[str]
    expected_citations: list[str] = Field(default_factory=list)
    expected_action: str = ""
    governance_check: list[str] = Field(default_factory=list)
    difficulty: str  # easy | medium | hard


def load_scenarios(path: Path | None = None) -> list[Scenario]:
    path = path or SCENARIOS_PATH
    items: list[dict[str, Any]] = json.loads(path.read_text())
    return [Scenario(**i) for i in items]
