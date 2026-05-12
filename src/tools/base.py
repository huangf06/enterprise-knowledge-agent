"""Tool primitive: Anthropic-format JSON schema + Python callable.

Tools accept a parsed dict of arguments and return a string payload that the
agent can quote, reason over, and cite. Tool implementations stay synchronous
and pure-Python in v1, reading from the synthetic data on disk.

W2 lands the registry, base contract, and the first three query tools.
W3 adds the governance hooks (cross-source RBAC, PII redact, audit) on the
tool_execute node, not on each tool.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pydantic

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_DIR = REPO_ROOT / "data" / "synthetic"


ToolFn = Callable[[dict[str, Any]], str]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    run: ToolFn = field(repr=False)

    def schema_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools.keys())

    def all(self) -> list[Tool]:
        return [self._tools[n] for n in sorted(self._tools.keys())]

    def schemas(self) -> list[dict[str, Any]]:
        return [t.schema_dict() for t in self.all()]


_default_registry = ToolRegistry()


def registry() -> ToolRegistry:
    return _default_registry


def load_source(source: str) -> dict[str, Any]:
    """Read a synthetic source JSON file. Caller chooses the slice it needs."""
    path = SYNTHETIC_DIR / source / f"{source}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Synthetic data missing at {path}. Run scripts/generate_data.py."
        )
    return json.loads(path.read_text())


def validate_args(args: dict[str, Any], model: type[pydantic.BaseModel]) -> pydantic.BaseModel:
    try:
        return model(**args)
    except pydantic.ValidationError as exc:
        raise ValueError(str(exc)) from exc
