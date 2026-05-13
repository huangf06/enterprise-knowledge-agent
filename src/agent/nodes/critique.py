"""critique node: Self-Refine 4-question checklist over (query, final_answer).

v4 Frontier #3. Per P5 (closed checklist) + P6 (no tool_history visibility).
Drives at most one regeneration of synthesize; subsequent passes are skipped
so a stuck loop cannot run away.

Enable / disable via env SELF_REFINE_ENABLED ("1" / "0"). Default on. Used to
produce the ablation table per v4.1 honesty policy.
"""

from __future__ import annotations

import os
from typing import Any

from src.agent.prompts import render
from src.agent.state import AgentState
from src.llm.anthropic_client import get_client, model_id

CRITIQUE_TOOL = {
    "name": "submit_critique",
    "description": "Submit the self-refine checklist result. All four bools are hard yes/no.",
    "input_schema": {
        "type": "object",
        "required": [
            "citations_ok",
            "action_specific",
            "cross_source",
            "governance_ok",
            "concerns",
        ],
        "properties": {
            "citations_ok": {"type": "boolean"},
            "action_specific": {"type": "boolean"},
            "cross_source": {"type": "boolean"},
            "governance_ok": {"type": "boolean"},
            "concerns": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 3,
            },
        },
    },
}

MAX_REVISIONS = 1


def is_enabled() -> bool:
    flag = os.environ.get("SELF_REFINE_ENABLED", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def critique_node(state: AgentState) -> dict[str, Any]:
    if not is_enabled():
        return {"critique_passed": True, "critique_concerns": [], "finished": True}

    revision_count = state.get("revision_count", 0)
    answer = state.get("final_answer", "")

    if revision_count >= MAX_REVISIONS:
        events = list(state.get("streaming_events", []))
        events.append(
            {"type": "critique", "passed": True, "reason": "max revisions reached", "concerns": []}
        )
        return {
            "critique_passed": True,
            "critique_concerns": [],
            "finished": True,
            "streaming_events": events,
        }

    prompt = render("critique", query=state["query"], answer=answer)
    client = get_client()
    resp = client.messages.create(
        model=model_id(),
        max_tokens=4096,
        tools=[CRITIQUE_TOOL],
        messages=[{"role": "user", "content": prompt}],
    )
    tool_uses = [b for b in resp.content if b.type == "tool_use" and b.name == "submit_critique"]
    if not tool_uses:
        # Critique itself failed to produce structured output; pass-through to avoid blocking.
        events = list(state.get("streaming_events", []))
        events.append({"type": "critique", "passed": True, "reason": "no critique output", "concerns": []})
        return {
            "critique_passed": True,
            "critique_concerns": [],
            "finished": True,
            "streaming_events": events,
        }

    crit = dict(tool_uses[0].input)
    all_ok = bool(
        crit.get("citations_ok")
        and crit.get("action_specific")
        and crit.get("cross_source")
        and crit.get("governance_ok")
    )
    concerns: list[str] = list(crit.get("concerns") or [])

    events = list(state.get("streaming_events", []))
    events.append(
        {
            "type": "critique",
            "passed": all_ok,
            "checks": {
                "citations_ok": bool(crit.get("citations_ok")),
                "action_specific": bool(crit.get("action_specific")),
                "cross_source": bool(crit.get("cross_source")),
                "governance_ok": bool(crit.get("governance_ok")),
            },
            "concerns": concerns,
        }
    )

    return {
        "critique_passed": all_ok,
        "critique_concerns": concerns,
        "revision_count": revision_count + (0 if all_ok else 1),
        "finished": all_ok,
        "streaming_events": events,
    }


__all__ = ["critique_node", "is_enabled"]
