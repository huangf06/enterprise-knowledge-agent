"""Anthropic SDK client wired to DeepSeek's Anthropic-compatible endpoint.

The project uses the Anthropic SDK as the LLM framework, but the API key and
base URL point at DeepSeek per Fei's W2 decision. This keeps tool-use and
message shapes Anthropic-canonical while routing inference through DeepSeek.

Prompt caching is intentionally NOT requested with `cache_control` here, because
DeepSeek's Anthropic-compatible endpoint does not implement Anthropic's prompt
cache. DeepSeek runs its own automatic prompt caching server-side based on
prefix bytes; the rendered prompt order (tools then system then messages) and
the determinism of every prefix block remain load-bearing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import anthropic
from dotenv import load_dotenv

from src.llm.cost_ledger import Usage, record
from src.observability.langfuse_tracker import record_generation

load_dotenv()


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    base_url: str
    model: str


def _config() -> LLMConfig:
    api_key = (
        os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or ""
    )
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic")
    model = os.environ.get("LLM_MODEL", "deepseek-v4-pro[1m]")
    if not api_key:
        raise RuntimeError(
            "DEEPSEEK_API_KEY (or ANTHROPIC_API_KEY) not set. Populate .env per .env.example."
        )
    return LLMConfig(api_key=api_key, base_url=base_url, model=model)


@lru_cache(maxsize=1)
def get_client() -> anthropic.Anthropic:
    cfg = _config()
    return anthropic.Anthropic(api_key=cfg.api_key, base_url=cfg.base_url)


@lru_cache(maxsize=1)
def model_id() -> str:
    return _config().model


def messages_create(
    *,
    system: str | list[dict[str, Any]] | None = None,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    max_tokens: int = 4096,
    temperature: float | None = None,
    tool_choice: dict[str, Any] | None = None,
    node: str = "unknown",
) -> anthropic.types.Message:
    client = get_client()
    kwargs: dict[str, Any] = {
        "model": model_id(),
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system is not None:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools
    if tool_choice is not None:
        kwargs["tool_choice"] = tool_choice
    if temperature is not None:
        kwargs["temperature"] = temperature
    resp = client.messages.create(**kwargs)
    usage = resp.usage
    record(
        node,
        Usage(
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            cached_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
        ),
    )
    output_text = "\n".join(b.text for b in resp.content if b.type == "text")
    record_generation(
        node=node,
        model=model_id(),
        input_messages=messages,
        output_text=output_text,
        usage={
            "input": getattr(usage, "input_tokens", 0) or 0,
            "output": getattr(usage, "output_tokens", 0) or 0,
        },
    )
    return resp


def messages_stream(
    *,
    system: str | list[dict[str, Any]] | None = None,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    max_tokens: int = 4096,
    temperature: float | None = None,
):
    client = get_client()
    kwargs: dict[str, Any] = {
        "model": model_id(),
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system is not None:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools
    if temperature is not None:
        kwargs["temperature"] = temperature
    return client.messages.stream(**kwargs)
