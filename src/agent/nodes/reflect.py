"""reflect node: short YES/NO call to decide whether to keep going."""

from __future__ import annotations

from typing import Any

from src.agent.prompts import render
from src.agent.state import AgentState
from src.llm.anthropic_client import messages_create


def _format_history(history: list[dict[str, Any]]) -> str:
    if not history:
        return "(none yet)"
    lines = []
    for i, h in enumerate(history, 1):
        lines.append(f"[{i}] {h['tool']}({h['args']}) -> {h['result'][:400]}")
    return "\n".join(lines)


def reflect_node(state: AgentState) -> dict[str, Any]:
    iteration = state.get("iteration", 0)
    max_iter = state.get("max_iterations", 6)
    events = list(state.get("streaming_events", []))

    if iteration >= max_iter:
        events.append({"type": "reflect", "verdict": "cap_reached"})
        return {"finished": True, "streaming_events": events}

    prompt = render(
        "reflect",
        query=state["query"],
        plan=state.get("plan", ""),
        tool_history=_format_history(state.get("tool_history", [])),
        iteration=iteration,
        max_iterations=max_iter,
    )
    resp = messages_create(messages=[{"role": "user", "content": prompt}], max_tokens=256, node="reflect")
    verdict_text = " ".join(b.text for b in resp.content if b.type == "text").strip().upper()
    finished = verdict_text.startswith("YES")
    events.append({"type": "reflect", "verdict": verdict_text})
    return {"finished": finished, "streaming_events": events}
