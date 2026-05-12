"""tool_execute node: run the chosen tool, append to history."""

from __future__ import annotations

from typing import Any

from src.agent.state import AgentState
from src.tools import registry


def tool_execute_node(state: AgentState) -> dict[str, Any]:
    pending = state.get("pending_tool")
    history = list(state.get("tool_history", []))
    events = list(state.get("streaming_events", []))

    if not pending:
        return {"streaming_events": events, "finished": True}

    name = pending["name"]
    args = pending["args"]
    ctx = {
        "role": state.get("user_role", "IC"),
        "user_name": state.get("user_name"),
        **state.get("user_identity", {}),
    }
    try:
        tool = registry().get(name)
        result = tool.run(args, ctx)
        ok = True
    except Exception as exc:  # noqa: BLE001 — surface failure to the agent
        result = f"ERROR running {name}: {exc}"
        ok = False

    record = {"tool": name, "args": args, "result": result}
    history.append(record)
    events.append({"type": "tool_execute", "tool": name, "args": args, "ok": ok})

    return {
        "tool_history": history,
        "iteration": state.get("iteration", 0) + 1,
        "pending_tool": None,
        "streaming_events": events,
    }
