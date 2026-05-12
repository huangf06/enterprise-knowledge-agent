"""Jira query tool: tickets scoped by assignee + status + priority + project."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from src.tools.base import Tool, load_source, registry, validate_args

PRIORITY_ORDER = ["Low", "Medium", "High", "Critical"]


class JiraQueryArgs(BaseModel):
    assignee: str | None = Field(default=None, description="Jira user (== email local part). None = any.")
    statuses: list[str] | None = Field(default=None, description="Filter to these statuses.")
    priority_min: str | None = Field(
        default=None, description="Minimum priority (Low|Medium|High|Critical)."
    )
    project: str | None = Field(default=None, description="Filter to a single project key.")
    has_blockers: bool | None = Field(default=None, description="True = only blocked tickets.")
    max_items: int = 20


@lru_cache(maxsize=1)
def _jira_data() -> dict[str, Any]:
    return load_source("jira")


def _meets_priority(ticket_priority: str, minimum: str | None) -> bool:
    if minimum is None:
        return True
    try:
        return PRIORITY_ORDER.index(ticket_priority) >= PRIORITY_ORDER.index(minimum)
    except ValueError:
        return True


def _run(args: dict[str, Any]) -> str:
    parsed = validate_args(args, JiraQueryArgs)
    tickets = _jira_data()["tickets"]
    results = []
    for t in tickets:
        if parsed.assignee and t["assignee"] != parsed.assignee:
            continue
        if parsed.statuses and t["status"] not in parsed.statuses:
            continue
        if parsed.project and t["project"] != parsed.project:
            continue
        if not _meets_priority(t["priority"], parsed.priority_min):
            continue
        if parsed.has_blockers is True and not t["blockers"]:
            continue
        if parsed.has_blockers is False and t["blockers"]:
            continue
        results.append(t)
    results.sort(key=lambda t: (PRIORITY_ORDER.index(t["priority"]), t["issue_key"]), reverse=True)
    total = len(results)
    shown = results[: parsed.max_items]
    lines = [
        f"jira_query(assignee={parsed.assignee}, status={parsed.statuses}, prio>={parsed.priority_min}): "
        f"{total} tickets"
    ]
    for t in shown:
        blockers = f" blocked_by={t['blockers']}" if t["blockers"] else ""
        lines.append(
            f"  [{t['priority']}/{t['status']}] {t['issue_key']} {t['project']} → {t['assignee']}{blockers}: {t['title']}"
        )
    if total > len(shown):
        lines.append(f"  ... {total - len(shown)} more not shown")
    return "\n".join(lines)


TOOL = Tool(
    name="jira_query",
    description=(
        "Query Jira tickets by assignee, status, priority, project, or blocker state. "
        "Use this to find someone's open work, blocked items, or high-priority queue."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "assignee": {"type": "string"},
            "statuses": {"type": "array", "items": {"type": "string"}},
            "priority_min": {"type": "string"},
            "project": {"type": "string"},
            "has_blockers": {"type": "boolean"},
            "max_items": {"type": "integer"},
        },
    },
    run=_run,
)

registry().register(TOOL)
