"""synthesize node: compose the final answer with citations."""

from __future__ import annotations

from typing import Any

from src.agent.prompts import render
from src.agent.state import AgentState
from src.llm.anthropic_client import messages_create


def _format_history(history: list[dict[str, Any]]) -> str:
    if not history:
        return "(no tool calls were made)"
    lines = []
    for i, h in enumerate(history, 1):
        lines.append(f"--- call {i}: {h['tool']}({h['args']}) ---\n{h['result']}")
    return "\n\n".join(lines)


def _critique_context(state: AgentState) -> str:
    """If Self-Refine critique flagged concerns on a previous pass, surface them."""
    concerns = state.get("critique_concerns") or []
    if not concerns:
        return ""
    bullets = "\n".join(f"- {c}" for c in concerns)
    return (
        "\n\nSelf-Refine concerns from the prior draft (address each before answering):\n"
        f"{bullets}\n"
    )


def synthesize_node(state: AgentState) -> dict[str, Any]:
    prompt = render(
        "synthesize",
        query=state["query"],
        user_name=state["user_name"],
        user_role=state["user_role"],
        plan=state.get("plan", ""),
        tool_history=_format_history(state.get("tool_history", [])),
    )
    prompt += _critique_context(state)
    resp = messages_create(messages=[{"role": "user", "content": prompt}], max_tokens=4096, node="synthesize")
    final_text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
    events = list(state.get("streaming_events", [])) + [{"type": "synthesize", "text": final_text}]
    return {"final_answer": final_text, "streaming_events": events}
