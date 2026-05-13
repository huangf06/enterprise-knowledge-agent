"""synthesize node: compose the final answer with citations."""

from __future__ import annotations

from typing import Any

from src.agent.dspy_synthesize_inference import is_enabled as compiled_enabled
from src.agent.dspy_synthesize_inference import run_compiled_synthesize
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
    tool_history_text = _format_history(state.get("tool_history", []))
    critique_suffix = _critique_context(state)

    if compiled_enabled():
        final_text = run_compiled_synthesize(
            query=state["query"],
            user_name=state["user_name"],
            user_role=state["user_role"],
            plan=state.get("plan", ""),
            tool_history_text=tool_history_text,
            critique_suffix=critique_suffix,
        )
    else:
        prompt = render(
            "synthesize",
            query=state["query"],
            user_name=state["user_name"],
            user_role=state["user_role"],
            plan=state.get("plan", ""),
            tool_history=tool_history_text,
        )
        prompt += critique_suffix
        resp = messages_create(
            messages=[{"role": "user", "content": prompt}], max_tokens=4096, node="synthesize"
        )
        final_text = "\n".join(b.text for b in resp.content if b.type == "text").strip()

    events = list(state.get("streaming_events", [])) + [{"type": "synthesize", "text": final_text}]
    return {"final_answer": final_text, "streaming_events": events}
