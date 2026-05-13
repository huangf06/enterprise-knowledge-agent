"""Run a scenario through the agent, then score with the judge."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from src.agent import app
from src.data.entity_consistency import load_users
from src.eval.citation import citation_groundedness
from src.eval.judge import judge
from src.eval.scenarios import Scenario
from src.eval.trajectory import trajectory_metrics
from src.llm.cost_ledger import query_window


def _user_state(scenario: Scenario) -> dict[str, Any]:
    users = {u.name: u for u in load_users()}
    user = users[scenario.user_name]
    return {
        "query": scenario.question,
        "user_name": user.name,
        "user_role": scenario.user_role,
        "user_identity": {
            "slack_handle": user.slack_handle,
            "jira_user": user.jira_user,
            "email": user.email,
            "github_username": user.github_username,
            "calendar_id": user.calendar_id,
            "gdocs_author_id": user.gdocs_author_id,
        },
        "max_iterations": 5,
        "tool_history": [],
        "streaming_events": [],
        "pending_tool": None,
    }


def run_scenario(scenario: Scenario) -> dict[str, Any]:
    state = _user_state(scenario)
    agent_start_iso = datetime.now(timezone.utc).isoformat()
    started = time.time()
    try:
        result = app().invoke(state, config={"recursion_limit": 40})
        answer = result.get("final_answer", "")
        tool_history = result.get("tool_history", [])
        ok = True
    except Exception as exc:  # noqa: BLE001
        answer = f"AGENT ERROR: {exc}"
        tool_history = []
        ok = False
    agent_elapsed = time.time() - started
    agent_end_iso = datetime.now(timezone.utc).isoformat()
    agent_usage = query_window(agent_start_iso, agent_end_iso)

    actual_sources = sorted({t["tool"] for t in tool_history})
    judge_start_iso = datetime.now(timezone.utc).isoformat()
    scores = judge(scenario, answer, actual_sources) if ok else {
        "answer_correctness": 0.0,
        "completeness": 0.0,
        "tool_selection_quality": 0.0,
        "governance_compliance": 1.0,  # no leak if agent errored
        "action_recommend_quality": 0.0,
    }
    judge_end_iso = datetime.now(timezone.utc).isoformat()
    judge_usage = query_window(judge_start_iso, judge_end_iso)

    citations = citation_groundedness(answer, tool_history) if ok else {
        "well_formedness": 0.0,
        "source_coverage": 0.0,
        "id_grounded": 0.0,
        "n_citations": 0,
        "n_brackets": 0,
    }
    trajectory = trajectory_metrics(actual_sources, scenario.expected_sources, len(tool_history))

    return {
        "scenario_id": scenario.id,
        "category": scenario.category,
        "difficulty": scenario.difficulty,
        "ok": ok,
        "answer": answer,
        "tool_calls": len(tool_history),
        "tools_used": actual_sources,
        "tool_history": tool_history,
        "scores": scores,
        "citations": citations,
        "trajectory": trajectory,
        "elapsed_s": round(agent_elapsed, 2),
        "agent_usage": agent_usage,
        "judge_usage": judge_usage,
    }
