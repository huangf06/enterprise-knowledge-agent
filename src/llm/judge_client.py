"""Structured-output judge client for F1 (and base for F3 multi-judge).

Each judge returns a fully-validated JudgeScore (Pydantic), never a free-form
string that has to be regex-extracted. Three providers supported:

  - "deepseek": main path. Uses DeepSeek via the Anthropic-compatible endpoint
    with forced tool_choice — robust across providers that implement the
    Anthropic Messages API.
  - "anthropic": official api.anthropic.com. Same forced tool_choice approach
    for consistency.
  - "openai":  official api.openai.com. Uses chat.completions.parse with
    Pydantic response_format.

F3 multi-judge consensus calls all three; N1 contamination guard drops the
DeepSeek judge during DSPy compilation (Sprint 4) but keeps it for general eval.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Literal

import anthropic
from openai import OpenAI
from pydantic import BaseModel, Field

from src.llm.anthropic_client import get_client as _deepseek_client
from src.llm.anthropic_client import model_id as _deepseek_model_id

Provider = Literal["deepseek", "anthropic", "openai"]


class JudgeScore(BaseModel):
    """Schema all judges return. All fields are 0.0..1.0."""

    answer_correctness: float = Field(..., ge=0.0, le=1.0)
    completeness: float = Field(..., ge=0.0, le=1.0)
    tool_selection_quality: float = Field(..., ge=0.0, le=1.0)
    governance_compliance: float = Field(..., ge=0.0, le=1.0)
    action_recommend_quality: float = Field(..., ge=0.0, le=1.0)


SCORE_TOOL_NAME = "submit_score"


def _judge_tool_schema() -> dict[str, Any]:
    """Anthropic-format tool schema derived from JudgeScore."""
    return {
        "name": SCORE_TOOL_NAME,
        "description": "Submit the rubric score for the agent answer. All fields are floats in [0.0, 1.0].",
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "answer_correctness",
                "completeness",
                "tool_selection_quality",
                "governance_compliance",
                "action_recommend_quality",
            ],
            "properties": {
                "answer_correctness": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "completeness": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "tool_selection_quality": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "governance_compliance": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "action_recommend_quality": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            },
        },
    }


# Pricing (USD per 1M tokens), kept here so non-DeepSeek judge cost is logged too.
_PROVIDER_PRICES = {
    "anthropic": {"in": 1.00, "out": 5.00, "cache_in": 0.10},  # Haiku 4.5
    "openai": {"in": 0.15, "out": 0.60, "cache_in": 0.075},  # gpt-4o-mini
}


_JUDGE_COST_USD: dict[str, float] = {"deepseek": 0.0, "anthropic": 0.0, "openai": 0.0}


def get_judge_cost(provider: Provider) -> float:
    return round(_JUDGE_COST_USD.get(provider, 0.0), 6)


def reset_judge_cost() -> None:
    for k in _JUDGE_COST_USD:
        _JUDGE_COST_USD[k] = 0.0


def _extract_score_from_text(text: str) -> JudgeScore | None:
    """Regex-based JSON extraction fallback for endpoints that don't honor tool_use."""
    import re

    cleaned = re.sub(r"```(?:json|JSON)?\s*", "", text).strip()
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()
    start = cleaned.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(cleaned)):
        ch = cleaned[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    parsed = json.loads(cleaned[start : i + 1])
                except json.JSONDecodeError:
                    return None
                try:
                    return JudgeScore.model_validate(parsed)
                except Exception:
                    return None
    return None


def _score_via_anthropic_style(
    client: anthropic.Anthropic,
    model: str,
    prompt: str,
    max_tokens: int = 4096,
    force_tool: bool = False,
) -> JudgeScore | None:
    """tool_use path used for both DeepSeek and Anthropic endpoints.

    Some endpoints (DeepSeek reasoner) reject forced tool_choice; we ask for
    "auto" and let the prompt instruct the model. If tool_use is missing we
    fall back to regex JSON extraction.
    """
    tool = _judge_tool_schema()
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "tools": [tool],
        "messages": [{"role": "user", "content": prompt}],
    }
    if force_tool:
        kwargs["tool_choice"] = {"type": "tool", "name": SCORE_TOOL_NAME}
    resp = client.messages.create(**kwargs)
    tool_uses = [b for b in resp.content if b.type == "tool_use" and b.name == SCORE_TOOL_NAME]
    if tool_uses:
        try:
            return JudgeScore.model_validate(dict(tool_uses[0].input))
        except Exception:
            pass
    # Fallback: model emitted text instead of (or alongside) tool_use
    text = "\n".join(b.text for b in resp.content if b.type == "text")
    return _extract_score_from_text(text)


def _judge_via_deepseek(prompt: str) -> JudgeScore | None:
    client = _deepseek_client()
    score = _score_via_anthropic_style(client, _deepseek_model_id(), prompt)
    return score


def _anthropic_official_client() -> anthropic.Anthropic:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None  # type: ignore[return-value]
    return anthropic.Anthropic(api_key=key, base_url="https://api.anthropic.com")


def _judge_via_anthropic(
    prompt: str, model: str = "claude-haiku-4-5-20251001"
) -> JudgeScore | None:
    client = _anthropic_official_client()
    if client is None:
        return None
    tool = _judge_tool_schema()
    resp = client.messages.create(
        model=model,
        max_tokens=512,
        tools=[tool],
        tool_choice={"type": "tool", "name": SCORE_TOOL_NAME},
        messages=[{"role": "user", "content": prompt}],
    )
    in_tok = getattr(resp.usage, "input_tokens", 0) or 0
    out_tok = getattr(resp.usage, "output_tokens", 0) or 0
    cache_in = getattr(resp.usage, "cache_read_input_tokens", 0) or 0
    px = _PROVIDER_PRICES["anthropic"]
    cost = (in_tok * px["in"] + cache_in * px["cache_in"] + out_tok * px["out"]) / 1e6
    _JUDGE_COST_USD["anthropic"] = _JUDGE_COST_USD.get("anthropic", 0.0) + cost
    tool_uses = [b for b in resp.content if b.type == "tool_use" and b.name == SCORE_TOOL_NAME]
    if tool_uses:
        try:
            return JudgeScore.model_validate(dict(tool_uses[0].input))
        except Exception:
            pass
    text = "\n".join(b.text for b in resp.content if b.type == "text")
    return _extract_score_from_text(text)


def _openai_client() -> OpenAI | None:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    return OpenAI(api_key=key)


def _judge_via_openai(prompt: str, model: str = "gpt-4o-mini") -> JudgeScore | None:
    client = _openai_client()
    if client is None:
        return None
    try:
        resp = client.chat.completions.parse(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format=JudgeScore,
            max_completion_tokens=512,
        )
    except Exception:
        return None
    usage = getattr(resp, "usage", None)
    if usage is not None:
        in_tok = getattr(usage, "prompt_tokens", 0) or 0
        out_tok = getattr(usage, "completion_tokens", 0) or 0
        cache_in = getattr(getattr(usage, "prompt_tokens_details", None), "cached_tokens", 0) or 0
        px = _PROVIDER_PRICES["openai"]
        cost = (in_tok * px["in"] + cache_in * px["cache_in"] + out_tok * px["out"]) / 1e6
        _JUDGE_COST_USD["openai"] = _JUDGE_COST_USD.get("openai", 0.0) + cost
    parsed = resp.choices[0].message.parsed
    return parsed


def score(prompt: str, provider: Provider = "deepseek") -> JudgeScore | None:
    """Single-provider score. Returns None on hard failure (caller decides fallback)."""
    if provider == "deepseek":
        return _judge_via_deepseek(prompt)
    if provider == "anthropic":
        return _judge_via_anthropic(prompt)
    if provider == "openai":
        return _judge_via_openai(prompt)
    raise ValueError(f"unknown provider: {provider}")
