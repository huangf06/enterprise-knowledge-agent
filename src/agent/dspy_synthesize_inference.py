"""Frontier #1 DSPy inference path for the `synthesize` node.

Loads `src/agent/compiled/synthesize.json` once, configures `dspy.LM` against
the same DeepSeek-via-Anthropic-compatible endpoint the manual path uses, and
exposes `run_compiled_synthesize(state)` for `synthesize_node` to call when
`USE_COMPILED_PROMPTS=1`.

Token accounting: after each DSPy invocation we walk newly-appended entries in
`lm.history` and write them to `src/llm/cost_ledger` under node=`synthesize`
(same node label as the manual path) so the per-query USD numbers in the
ablation table are apples-to-apples with the OFF run.

Caveat: DSPy's `ChainOfThought` adds a `reasoning` output field, which costs
more tokens than the manual prompt. We do not strip the reasoning; the whole
point of the ablation is to measure whether compiled-prompt quality earns its
keep against that extra spend.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.llm.cost_ledger import Usage, record

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMPILED_PATH = REPO_ROOT / "src" / "agent" / "compiled" / "synthesize.json"


def is_enabled() -> bool:
    flag = os.environ.get("USE_COMPILED_PROMPTS", "0").strip().lower()
    return flag in ("1", "true", "yes", "on")


@lru_cache(maxsize=1)
def _get_compiled_module() -> Any:
    """Build the SynthesizeModule, configure dspy LM, and load the compiled JSON."""
    import dspy  # local import: only required when the flag is on

    from src.agent.dspy_synthesize import SynthesizeModule, configure_dspy_lm

    configure_dspy_lm()
    module = SynthesizeModule()
    compiled_path = Path(os.environ.get("COMPILED_SYNTHESIZE_PATH", DEFAULT_COMPILED_PATH))
    if not compiled_path.exists():
        raise RuntimeError(
            f"USE_COMPILED_PROMPTS=1 but compiled JSON not found at {compiled_path}. "
            "Run scripts/dspy_compile.py first."
        )
    module.load(str(compiled_path))
    return module


def _usage_from_history_entry(entry: dict[str, Any]) -> Usage:
    """Best-effort extraction of input/output tokens from a dspy.LM.history record.

    dspy.LM stores litellm responses; usage may live at top-level `usage` or under
    `response.usage`. We accept either shape and zero-fill the rest.
    """
    usage = entry.get("usage") or {}
    if not usage:
        resp = entry.get("response")
        if resp is not None:
            usage = getattr(resp, "usage", None) or {}
            if hasattr(usage, "model_dump"):
                usage = usage.model_dump()
            elif hasattr(usage, "__dict__"):
                usage = dict(usage.__dict__)
    if not isinstance(usage, dict):
        return Usage(0, 0, 0)
    in_tok = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    out_tok = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    cached = 0
    details = usage.get("prompt_tokens_details")
    if isinstance(details, dict):
        cached = int(details.get("cached_tokens") or 0)
    return Usage(input_tokens=in_tok, cached_input_tokens=cached, output_tokens=out_tok)


def run_compiled_synthesize(
    *,
    query: str,
    user_name: str,
    user_role: str,
    plan: str,
    tool_history_text: str,
    critique_suffix: str = "",
) -> str:
    """Invoke the compiled DSPy synthesize module. Returns the answer text.

    `critique_suffix` is appended to `tool_history_text` so Self-Refine concerns
    from a prior pass still influence regeneration (mirrors the manual path).
    """
    import dspy

    module = _get_compiled_module()
    lm = dspy.settings.lm
    history_before = len(lm.history) if lm is not None else 0

    th = tool_history_text + critique_suffix if critique_suffix else tool_history_text
    pred = module(
        query=query,
        user_name=user_name,
        user_role=user_role,
        plan=plan,
        tool_history=th,
    )

    if lm is not None:
        for entry in lm.history[history_before:]:
            usage = _usage_from_history_entry(entry)
            if usage.input_tokens or usage.output_tokens:
                record("synthesize", usage)

    answer = getattr(pred, "answer", "") or ""
    return answer.strip()


__all__ = ["is_enabled", "run_compiled_synthesize"]
