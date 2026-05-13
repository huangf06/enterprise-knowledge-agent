"""Frontier #1 DSPy compilation scaffold (Sprint 4).

DSPy Signature + ChainOfThought module that mirrors prompts/synthesize.md. The
goal is to let MIPROv2 (or the lighter BootstrapFewShot) re-optimize the
synthesize prompt against the multi-judge metric and ship the compiled prompt
as a drop-in replacement.

v4.1 locks (P1-P4, P13, P15):
  - Compile ONE node at a time, starting with `synthesize`.
  - Use Anthropic Haiku + OpenAI gpt-4o-mini as judges - DeepSeek excluded
    during compilation (N1 contamination guard).
  - Redact expected_topics from the judge's view to prevent keyword leak (P3).
  - Budget cap: $100 of API cost; week-9 day-2 gate.

Not executed in this scaffold. Caller drives via scripts/dspy_compile.py.
"""

from __future__ import annotations

import os
from typing import Any

import dspy

from src.eval.judge import JUDGE_PROMPT
from src.eval.multi_judge import DSPY_TRAINING_POOL, multi_judge


class SynthesizeSignature(dspy.Signature):
    """Synthesize the agent's final answer from question + plan + tool evidence.

    Respect single-tenant + audit-log boundaries. Inline citations of the form
    [source:id]. End with "Audit: N tool calls." Concise, prioritized.
    """

    query: str = dspy.InputField(desc="User's question")
    user_name: str = dspy.InputField(desc="User's display name")
    user_role: str = dspy.InputField(desc="User's role for RBAC context")
    plan: str = dspy.InputField(desc="Execution plan from plan_node")
    tool_history: str = dspy.InputField(desc="Concatenated tool calls + results")
    answer: str = dspy.OutputField(desc="Synthesized answer with citations + audit line")


class SynthesizeModule(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.ChainOfThought(SynthesizeSignature)

    def forward(self, query, user_name, user_role, plan, tool_history):
        return self.predict(
            query=query,
            user_name=user_name,
            user_role=user_role,
            plan=plan,
            tool_history=tool_history,
        )


def configure_dspy_lm() -> None:
    """Point DSPy at the DeepSeek-via-Anthropic-compatible endpoint via litellm."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic")
    model = os.environ.get("LLM_MODEL", "deepseek-v4-pro[1m]")
    lm = dspy.LM(
        f"anthropic/{model}",
        api_key=api_key,
        api_base=base_url,
        max_tokens=4096,
    )
    dspy.configure(lm=lm)


def make_training_metric(scenarios_by_id: dict[str, Any]) -> Any:
    """Return a DSPy metric callable using the v4.1 N1-compliant multi-judge pool.

    The metric expects DSPy examples with attribute `scenario_id`; it pulls the
    matching Scenario from `scenarios_by_id`, scores the predicted answer with
    the 2-judge pool (Haiku + gpt-4o-mini, DeepSeek excluded), and returns the
    median answer_correctness as the scalar reward.

    Per P3, expected_topics is redacted from the judge view to prevent the
    optimizer from keyword-leaking expected topics into the answer.
    """

    def metric(example, pred, trace=None) -> float:
        sid = getattr(example, "scenario_id", None)
        scenario = scenarios_by_id.get(sid)
        if scenario is None:
            return 0.0
        # P3: redact expected_topics
        redacted = scenario.__class__(
            **{**scenario.__dict__, "expected_topics": []}
        )
        try:
            result = multi_judge(
                redacted,
                pred.answer,
                actual_sources=getattr(example, "actual_sources", []),
                pool=DSPY_TRAINING_POOL,
            )
            consensus = result.get("consensus", {})
            return float(consensus.get("answer_correctness", 0.0))
        except Exception:
            return 0.0

    return metric


__all__ = ["SynthesizeSignature", "SynthesizeModule", "configure_dspy_lm", "make_training_metric"]
