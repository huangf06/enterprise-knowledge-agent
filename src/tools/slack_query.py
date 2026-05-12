"""Slack query tool: messages + DMs scoped by user / channel / time."""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from src.governance.audit import audit_event
from src.governance.pii_redact import redact
from src.governance.rbac import check_resource
from src.tools.base import Tool, ToolContext, load_source, registry, validate_args


class SlackQueryArgs(BaseModel):
    user_handle: str = Field(description="Slack handle of the user whose surface to scope to")
    since: str | None = Field(
        default=None,
        description="ISO 8601 timestamp lower bound, inclusive (e.g. 2026-05-08T17:00:00)",
    )
    include_dms: bool = True
    include_mentions: bool = True
    channels: list[str] | None = Field(
        default=None,
        description="Optional channel allowlist (e.g. ['#engineering']). None = all visible channels.",
    )
    keyword: str | None = Field(default=None, description="Optional substring filter on message text")
    max_items: int = 25


@lru_cache(maxsize=1)
def _slack_data() -> dict[str, Any]:
    return load_source("slack")


def _parse_since(since: str | None) -> datetime | None:
    return datetime.fromisoformat(since) if since else None


def _channel_visible(channel: dict[str, Any], handle: str, allow: list[str] | None) -> bool:
    if allow is not None and channel["name"] not in allow:
        return False
    return handle in channel["members"]


def _run(args: dict[str, Any], ctx: ToolContext) -> str:
    parsed = validate_args(args, SlackQueryArgs)
    data = _slack_data()
    since_dt = _parse_since(parsed.since)
    role = ctx.get("role", "IC")
    denied_channels: list[str] = []
    visible_channels: set[str] = set()
    for c in data["channels"]:
        if not _channel_visible(c, parsed.user_handle, parsed.channels):
            continue
        decision = check_resource("slack_channel", c["name"], role)
        if not decision.allow:
            denied_channels.append(c["name"])
            audit_event(
                "rbac.deny",
                {"source": "slack", "resource": c["name"], "role": role, "reason": decision.reason},
            )
            continue
        visible_channels.add(c["name"])

    lines: list[str] = []
    mention_count = 0
    direct_count = 0

    for msg in data["messages"]:
        if msg["channel"] not in visible_channels:
            continue
        ts = datetime.fromisoformat(msg["timestamp"])
        if since_dt and ts < since_dt:
            continue
        mentions = msg.get("mentions", [])
        is_mention = parsed.user_handle in mentions
        is_author = msg["author"] == parsed.user_handle
        if not (is_mention or is_author):
            continue
        if not parsed.include_mentions and is_mention and not is_author:
            continue
        if parsed.keyword and parsed.keyword.lower() not in msg["text"].lower():
            continue
        tag = "MENTION" if is_mention and not is_author else "AUTHOR"
        lines.append(
            f"[{tag}] {msg['channel']} {ts.isoformat()} {msg['author']}: {msg['text']}  (id={msg['message_id']})"
        )
        if is_mention and not is_author:
            mention_count += 1

    if parsed.include_dms:
        for dm in data["dms"]:
            ts = datetime.fromisoformat(dm["timestamp"])
            if since_dt and ts < since_dt:
                continue
            if parsed.user_handle not in (dm["sender"], dm["recipient"]):
                continue
            if parsed.keyword and parsed.keyword.lower() not in dm["text"].lower():
                continue
            direction = "DM_FROM" if dm["recipient"] == parsed.user_handle else "DM_TO"
            other = dm["sender"] if direction == "DM_FROM" else dm["recipient"]
            lines.append(
                f"[{direction}] {ts.isoformat()} {other}: {dm['text']}  (id={dm['dm_id']})"
            )
            direct_count += 1

    lines.sort()
    if len(lines) > parsed.max_items:
        truncated = len(lines) - parsed.max_items
        lines = lines[: parsed.max_items]
        lines.append(f"... {truncated} more items not shown")

    header_parts = [
        f"slack_query(user={parsed.user_handle}, since={parsed.since}): "
        f"{mention_count} mentions, {direct_count} DMs, {len(lines)} lines shown"
    ]
    if denied_channels:
        header_parts.append(f"  RBAC denied: {sorted(denied_channels)} (role={role})")
    body = redact("\n".join(lines))
    return "\n".join(header_parts) + "\n" + body


TOOL = Tool(
    name="slack_query",
    description=(
        "Query Slack channels, mentions, and DMs scoped to a user. Use this to find what "
        "someone was tagged in, what they wrote, or who DM'd them in a time window."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "user_handle": {"type": "string"},
            "since": {"type": "string"},
            "include_dms": {"type": "boolean"},
            "include_mentions": {"type": "boolean"},
            "channels": {"type": "array", "items": {"type": "string"}},
            "keyword": {"type": "string"},
            "max_items": {"type": "integer"},
        },
        "required": ["user_handle"],
    },
    run=_run,
)

registry().register(TOOL)
