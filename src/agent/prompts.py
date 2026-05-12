"""Prompt loader: prompts/*.md are version-controlled, the formatting happens here."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


@lru_cache(maxsize=8)
def load(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    return path.read_text()


def render(name: str, **kwargs: object) -> str:
    return load(name).format(**kwargs)
