"""LangGraph agent skeleton. 5 core nodes + 1 Self-Refine critique node (v4).

Self-Refine (Frontier #3) is enabled via SELF_REFINE_ENABLED env var (default on).
When enabled, synthesize -> critique -> (synthesize if concerns, else END).
At most MAX_REVISIONS (1) regeneration to avoid runaway loops.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.agent.nodes.critique import critique_node, is_enabled as self_refine_enabled
from src.agent.nodes.plan import plan_node
from src.agent.nodes.reflect import reflect_node
from src.agent.nodes.synthesize import synthesize_node
from src.agent.nodes.tool_execute import tool_execute_node
from src.agent.nodes.tool_select import tool_select_node
from src.agent.state import AgentState


def _route_after_select(state: AgentState) -> str:
    if state.get("finished"):
        return "synthesize"
    return "tool_execute"


def _route_after_reflect(state: AgentState) -> str:
    if state.get("finished"):
        return "synthesize"
    return "tool_select"


def _route_after_critique(state: AgentState) -> str:
    """Self-Refine routing: pass -> END, fail -> regenerate synthesize (capped at MAX_REVISIONS)."""
    if state.get("critique_passed", True):
        return "end"
    if state.get("revision_count", 0) >= 1:
        return "end"
    return "synthesize"


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("plan", plan_node)
    g.add_node("tool_select", tool_select_node)
    g.add_node("tool_execute", tool_execute_node)
    g.add_node("reflect", reflect_node)
    g.add_node("synthesize", synthesize_node)

    g.add_edge(START, "plan")
    g.add_edge("plan", "tool_select")
    g.add_conditional_edges(
        "tool_select", _route_after_select, {"tool_execute": "tool_execute", "synthesize": "synthesize"}
    )
    g.add_edge("tool_execute", "reflect")
    g.add_conditional_edges(
        "reflect", _route_after_reflect, {"tool_select": "tool_select", "synthesize": "synthesize"}
    )

    if self_refine_enabled():
        g.add_node("critique", critique_node)
        g.add_edge("synthesize", "critique")
        g.add_conditional_edges(
            "critique", _route_after_critique, {"synthesize": "synthesize", "end": END}
        )
    else:
        g.add_edge("synthesize", END)

    return g.compile()


_compiled = None


def app():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled
