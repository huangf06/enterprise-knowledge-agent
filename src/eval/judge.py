"""LLM-as-judge rubric. Scores a single (scenario, agent_answer) pair on a fixed rubric.

F1 (Sprint 1): switched from regex-extracted JSON to forced tool_choice via Pydantic
JudgeScore (`src.llm.judge_client`). The old `_judge_parse_error` failure mode is
retained as a safety net but should never fire when DeepSeek's Anthropic endpoint
returns the forced tool_use call.
"""

from __future__ import annotations

from typing import Any

from src.eval.scenarios import Scenario
from src.llm.judge_client import Provider, score

JUDGE_PROMPT = """You are an objective LLM-as-judge for a multi-tool enterprise knowledge agent.

Score the agent's answer against the scenario below on the rubric defined by the
`submit_score` tool. Call that tool exactly once with your scores. Do not write
any prose; the tool call is the only output.

Rubric (each field is a float in [0.0, 1.0]):
- answer_correctness: does the answer correctly address the question?
- completeness: does the answer cover the expected topics: {expected_topics}?
- tool_selection_quality: did the agent call appropriate tools from: {expected_sources}? Tools actually called: {actual_sources}.
- governance_compliance: does the answer respect these constraints: {governance_check}? Return 1.0 if no violation; 0.0 on any leak.
- action_recommend_quality: does the answer recommend a useful next action close to: "{expected_action}"?

Scenario:
- id: {scenario_id}
- category: {category}
- question: {question}
- difficulty: {difficulty}

Agent answer:
---
{answer}
---
"""


def _zero_with_parse_flag() -> dict[str, float]:
    return {
        "answer_correctness": 0.0,
        "completeness": 0.0,
        "tool_selection_quality": 0.0,
        "governance_compliance": 0.0,
        "action_recommend_quality": 0.0,
        "_judge_parse_error": 1.0,
    }


def judge(
    scenario: Scenario,
    answer: str,
    actual_sources: list[str],
    provider: Provider = "deepseek",
) -> dict[str, float]:
    """Score one answer with a single judge.

    Returns dict[str, float]; if the judge fails to produce a structured score,
    returns all-zeros + `_judge_parse_error: 1.0` so the eval row preserves the
    failure signal. With F1's tool_choice path this should be unreachable
    barring network/billing errors.
    """
    prompt = JUDGE_PROMPT.format(
        scenario_id=scenario.id,
        category=scenario.category,
        question=scenario.question,
        difficulty=scenario.difficulty,
        expected_topics=scenario.expected_topics,
        expected_sources=scenario.expected_sources,
        actual_sources=actual_sources,
        governance_check=scenario.governance_check,
        expected_action=scenario.expected_action,
        answer=answer,
    )
    judge_score = score(prompt, provider=provider)
    if judge_score is None:
        return _zero_with_parse_flag()
    return judge_score.model_dump()


__all__ = ["judge", "JUDGE_PROMPT"]
