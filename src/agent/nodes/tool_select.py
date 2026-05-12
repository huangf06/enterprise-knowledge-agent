"""tool_select node: LLM with the tool catalog. Emits one tool call, or signals done."""

from __future__ import annotations

from typing import Any

from src.agent.prompts import render
from src.agent.state import AgentState
from src.llm.anthropic_client import messages_create
from src.tools import registry


def _format_tool_history(history: list[dict[str, Any]]) -> str:
    if not history:
        return "(none yet)"
    lines = []
    for i, h in enumerate(history, 1):
        lines.append(f"[{i}] {h['tool']}({h['args']}) -> {h['result'][:400]}")
    return "\n".join(lines)


def tool_select_node(state: AgentState) -> dict[str, Any]:
    if state.get("iteration", 0) >= state.get("max_iterations", 6):
        events = state.get("streaming_events", []) + [{"type": "tool_select", "verdict": "cap_reached"}]
        return {"finished": True, "pending_tool": None, "streaming_events": events}
    prompt = render(
        "tool_select",
        query=state["query"],
        user_name=state["user_name"],
        user_role=state["user_role"],
        slack_handle=state["user_identity"].get("slack_handle", ""),
        email=state["user_identity"].get("email", ""),
        plan=state.get("plan", ""),
        tool_history=_format_tool_history(state.get("tool_history", [])),
        iteration=state.get("iteration", 0),
        max_iterations=state.get("max_iterations", 6),
    )
    resp = messages_create(
        messages=[{"role": "user", "content": prompt}],
        tools=registry().schemas(),
        max_tokens=2048,
    )

    tool_use_blocks = [b for b in resp.content if b.type == "tool_use"]
    text_blocks = [b.text for b in resp.content if b.type == "text"]
    events = state.get("streaming_events", []) + [
        {
            "type": "tool_select",
            "thought": "\n".join(text_blocks),
            "picked": tool_use_blocks[0].name if tool_use_blocks else None,
        }
    ]

    if not tool_use_blocks:
        return {
            "finished": True,
            "pending_tool": None,
            "streaming_events": events,
        }

    pending = tool_use_blocks[0]
    return {
        "pending_tool": {"name": pending.name, "args": dict(pending.input)},
        "streaming_events": events,
    }
