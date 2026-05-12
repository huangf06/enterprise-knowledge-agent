"""Email query tool."""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from src.governance.pii_redact import redact
from src.tools.base import Tool, ToolContext, load_source, registry, validate_args


class EmailArgs(BaseModel):
    user_email: str = Field(description="email address of the user; only their inbox is searched")
    importance: str | None = Field(default=None, description="high | normal | low")
    unread_only: bool = False
    keyword: str | None = Field(default=None)
    since: str | None = Field(default=None, description="ISO 8601 lower bound on sent_at")
    max_items: int = 15


@lru_cache(maxsize=1)
def _email_data() -> dict[str, Any]:
    return load_source("email")


def _run(args: dict[str, Any], ctx: ToolContext) -> str:
    parsed = validate_args(args, EmailArgs)
    since_dt = datetime.fromisoformat(parsed.since) if parsed.since else None
    emails = _email_data()["emails"]
    rows = []
    for e in emails:
        if parsed.user_email != e["sender"] and parsed.user_email not in e["recipients"]:
            continue
        if parsed.importance and e["importance"] != parsed.importance:
            continue
        if parsed.unread_only and not e["unread"]:
            continue
        if parsed.keyword:
            hay = (e["subject"] + "\n" + e["body"]).lower()
            if parsed.keyword.lower() not in hay:
                continue
        if since_dt and datetime.fromisoformat(e["sent_at"]) < since_dt:
            continue
        rows.append(e)
    rows.sort(key=lambda e: e["sent_at"], reverse=True)
    total = len(rows)
    shown = rows[: parsed.max_items]
    lines = [
        f"email_query(user={parsed.user_email}, importance={parsed.importance}, unread_only={parsed.unread_only}): "
        f"{total} emails"
    ]
    for e in shown:
        flag = "UNREAD" if e["unread"] else "READ"
        prio = e["importance"].upper()
        lines.append(
            f"  [{prio}/{flag}] {e['sent_at']} {e['sender']} -> {e['recipients']}: {e['subject']}  (id={e['email_id']})"
        )
    if total > len(shown):
        lines.append(f"  ... {total - len(shown)} more not shown")
    return redact("\n".join(lines))


TOOL = Tool(
    name="email_query",
    description=(
        "Query a user's inbox by importance, unread state, keyword, or time. "
        "Use this to surface stale high-priority emails or specific subject threads."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "user_email": {"type": "string"},
            "importance": {"type": "string"},
            "unread_only": {"type": "boolean"},
            "keyword": {"type": "string"},
            "since": {"type": "string"},
            "max_items": {"type": "integer"},
        },
        "required": ["user_email"],
    },
    run=_run,
)

registry().register(TOOL)
