"""GitHub PR review queue tool."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from src.governance.pii_redact import redact
from src.tools.base import Tool, ToolContext, load_source, registry, validate_args


class GitHubArgs(BaseModel):
    reviewer: str | None = Field(default=None, description="github_username of reviewer to scope to")
    author: str | None = Field(default=None, description="github_username of author to scope to")
    states: list[str] | None = Field(default=None, description="open|merged|closed")
    label: str | None = Field(default=None)
    max_items: int = 20


@lru_cache(maxsize=1)
def _gh_data() -> dict[str, Any]:
    return load_source("github")


def _run(args: dict[str, Any], ctx: ToolContext) -> str:
    parsed = validate_args(args, GitHubArgs)
    repos = _gh_data()["repos"]
    rows = []
    for repo in repos:
        for pr in repo["prs"]:
            if parsed.reviewer and parsed.reviewer not in pr["reviewers"]:
                continue
            if parsed.author and pr["author"] != parsed.author:
                continue
            if parsed.states and pr["state"] not in parsed.states:
                continue
            if parsed.label and parsed.label not in (pr.get("labels") or []):
                continue
            rows.append(pr)
    rows.sort(key=lambda pr: pr["pr_id"])
    total = len(rows)
    shown = rows[: parsed.max_items]
    lines = [
        f"github_pr_review(reviewer={parsed.reviewer}, author={parsed.author}, state={parsed.states}, label={parsed.label}): "
        f"{total} PRs"
    ]
    for pr in shown:
        labels = f" labels={pr.get('labels', [])}" if pr.get("labels") else ""
        lines.append(
            f"  [{pr['state']}] {pr['pr_id']} {pr['repo']} → reviewers={pr['reviewers']} author={pr['author']}{labels}: {pr['title']}"
        )
    if total > len(shown):
        lines.append(f"  ... {total - len(shown)} more not shown")
    return redact("\n".join(lines))


TOOL = Tool(
    name="github_pr_review",
    description=(
        "Query GitHub PRs by reviewer, author, state, or label. Use this for review queue, "
        "release-blocking PRs, or recent merge history."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "reviewer": {"type": "string"},
            "author": {"type": "string"},
            "states": {"type": "array", "items": {"type": "string"}},
            "label": {"type": "string"},
            "max_items": {"type": "integer"},
        },
    },
    run=_run,
)

registry().register(TOOL)
