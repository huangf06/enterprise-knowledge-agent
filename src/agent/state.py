"""Agent state passed through the LangGraph nodes."""

from __future__ import annotations

from typing import Any, TypedDict


class ToolCallRecord(TypedDict):
    tool: str
    args: dict[str, Any]
    result: str


class AgentState(TypedDict, total=False):
    query: str
    user_name: str
    user_role: str  # IC | manager | HR
    user_identity: dict[str, str]  # slack_handle/jira_user/email/github_username/calendar_id

    plan: str
    tool_history: list[ToolCallRecord]
    iteration: int
    max_iterations: int
    finished: bool

    streaming_events: list[dict[str, Any]]  # accumulating SSE event payloads
    pending_tool: dict[str, Any] | None  # set by tool_select, consumed by tool_execute

    final_answer: str

    # v4 Frontier #3 Self-Refine
    critique_passed: bool
    critique_concerns: list[str]
    revision_count: int
