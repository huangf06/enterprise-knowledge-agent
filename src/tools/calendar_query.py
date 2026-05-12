"""Calendar query tool: events scoped by user + range, with conflict detection."""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from src.governance.pii_redact import redact
from src.tools.base import Tool, ToolContext, load_source, registry, validate_args


class CalendarQueryArgs(BaseModel):
    user_calendar_id: str = Field(description="Calendar id (== email) of the user")
    start: str | None = Field(default=None, description="ISO 8601 lower bound, inclusive")
    end: str | None = Field(default=None, description="ISO 8601 upper bound, exclusive")
    include_conflicts: bool = True
    max_items: int = 30


@lru_cache(maxsize=1)
def _calendar_data() -> dict[str, Any]:
    return load_source("calendar")


def _parse(ts: str | None) -> datetime | None:
    return datetime.fromisoformat(ts) if ts else None


def _conflicts(events: list[dict[str, Any]]) -> list[tuple[str, str]]:
    pairs = []
    for i, a in enumerate(events):
        a_s = datetime.fromisoformat(a["start"])
        a_e = datetime.fromisoformat(a["end"])
        for b in events[i + 1 :]:
            b_s = datetime.fromisoformat(b["start"])
            b_e = datetime.fromisoformat(b["end"])
            if a_s < b_e and b_s < a_e:
                pairs.append((a["event_id"], b["event_id"]))
    return pairs


def _run(args: dict[str, Any], ctx: ToolContext) -> str:
    parsed = validate_args(args, CalendarQueryArgs)
    events_all = _calendar_data()["events"]
    start_dt = _parse(parsed.start)
    end_dt = _parse(parsed.end)
    user_events = []
    for e in events_all:
        if parsed.user_calendar_id != e["organizer"] and parsed.user_calendar_id not in e["attendees"]:
            continue
        ts = datetime.fromisoformat(e["start"])
        if start_dt and ts < start_dt:
            continue
        if end_dt and ts >= end_dt:
            continue
        user_events.append(e)
    user_events.sort(key=lambda e: e["start"])

    conflicts = _conflicts(user_events) if parsed.include_conflicts else []
    total = len(user_events)
    shown = user_events[: parsed.max_items]
    lines = [
        f"calendar_query(user={parsed.user_calendar_id}, range={parsed.start}..{parsed.end}): "
        f"{total} events, {len(conflicts)} conflicts"
    ]
    for e in shown:
        tag = "MANDATORY" if e.get("mandatory") else "OPTIONAL"
        lines.append(
            f"  [{tag}] {e['start']} - {e['end']} {e['title']} (id={e['event_id']}, organizer={e['organizer']})"
        )
    if total > len(shown):
        lines.append(f"  ... {total - len(shown)} more not shown")
    for a, b in conflicts:
        lines.append(f"  CONFLICT: {a} overlaps {b}")
    return redact("\n".join(lines))


TOOL = Tool(
    name="calendar_query",
    description=(
        "Query a user's calendar for events in a time window, with optional conflict detection. "
        "Use this for scheduling questions, conflict resolution, or week-at-a-glance planning."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "user_calendar_id": {"type": "string"},
            "start": {"type": "string"},
            "end": {"type": "string"},
            "include_conflicts": {"type": "boolean"},
            "max_items": {"type": "integer"},
        },
        "required": ["user_calendar_id"],
    },
    run=_run,
)

registry().register(TOOL)
