"""plan node: emit a short execution plan, no tools."""

from __future__ import annotations

from datetime import date
from typing import Any

from src.agent.prompts import render
from src.agent.state import AgentState
from src.llm.anthropic_client import messages_create
from src.tools import registry


def _tool_summary() -> str:
    lines = []
    for tool in registry().all():
        lines.append(f"- {tool.name}: {tool.description.splitlines()[0]}")
    return "\n".join(lines)


def plan_node(state: AgentState) -> dict[str, Any]:
    prompt = render(
        "plan",
        query=state["query"],
        user_name=state["user_name"],
        user_role=state["user_role"],
        slack_handle=state["user_identity"].get("slack_handle", ""),
        jira_user=state["user_identity"].get("jira_user", ""),
        email=state["user_identity"].get("email", ""),
        github_username=state["user_identity"].get("github_username", ""),
        calendar_id=state["user_identity"].get("calendar_id", ""),
        tool_summary=_tool_summary(),
        today=str(date(2026, 5, 11)),
    )
    resp = messages_create(messages=[{"role": "user", "content": prompt}], max_tokens=1024, node="plan")
    plan_text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
    return {
        "plan": plan_text or "(no plan emitted, proceeding heuristically)",
        "tool_history": state.get("tool_history", []),
        "iteration": 0,
        "max_iterations": state.get("max_iterations", 6),
        "finished": False,
        "streaming_events": state.get("streaming_events", [])
        + [{"type": "plan", "text": plan_text}],
    }
