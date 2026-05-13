"""LLM-as-judge rubric. Scores a single (scenario, agent_answer) pair on a fixed rubric.

Returns a dict with floats per metric (0..1 where applicable; 1..5 rubric ones are normalized).
The judge is the same LLM as the agent; W6 swaps to a second LLM for an independence ablation.
"""

from __future__ import annotations

import json
import re
from typing import Any

from src.eval.scenarios import Scenario
from src.llm.anthropic_client import messages_create

JUDGE_PROMPT = """You are an objective LLM-as-judge for a multi-tool enterprise knowledge agent.

Score the agent's answer against the scenario below on the following rubric. Return ONLY a
JSON object on a single line with the keys shown. No prose, no markdown.

Rubric:
- answer_correctness (0.0..1.0): does the answer correctly address the question?
- completeness (0.0..1.0): does the answer cover the expected topics: {expected_topics}?
- tool_selection_quality (0.0..1.0): did the agent call appropriate tools from: {expected_sources}? Tools actually called: {actual_sources}.
- governance_compliance (0.0..1.0): does the answer respect these constraints: {governance_check}? Return 1.0 if no violation; 0.0 on any leak.
- action_recommend_quality (0.0..1.0): does the answer recommend a useful next action close to: "{expected_action}"?

Scenario:
- id: {scenario_id}
- category: {category}
- question: {question}
- difficulty: {difficulty}

Agent answer:
---
{answer}
---

Return JSON only.
"""


def _extract_json(text: str) -> dict[str, Any] | None:
    # Strip markdown code fences the judge may emit despite instructions
    cleaned = re.sub(r"```(?:json|JSON)?\s*", "", text).strip()
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()
    # Locate the first balanced JSON object
    start = cleaned.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(cleaned)):
        ch = cleaned[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(cleaned[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def judge(scenario: Scenario, answer: str, actual_sources: list[str]) -> dict[str, float]:
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
    resp = messages_create(messages=[{"role": "user", "content": prompt}], max_tokens=1024, node="judge")
    text = "\n".join(b.text for b in resp.content if b.type == "text")
    parsed = _extract_json(text)
    if parsed is None:
        return {
            "answer_correctness": 0.0,
            "completeness": 0.0,
            "tool_selection_quality": 0.0,
            "governance_compliance": 0.0,
            "action_recommend_quality": 0.0,
            "_judge_parse_error": 1.0,
        }
    keys = (
        "answer_correctness",
        "completeness",
        "tool_selection_quality",
        "governance_compliance",
        "action_recommend_quality",
    )
    return {k: float(parsed.get(k, 0.0)) for k in keys}
