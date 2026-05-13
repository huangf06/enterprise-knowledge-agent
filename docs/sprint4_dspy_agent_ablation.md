# Sprint 4 Frontier #1 DSPy: agent-level ablation result

> Status: **honest negative on the load-bearing metrics**. DSPy-compiled
> synthesize prompt lifts +0.05 on answer_correctness and completeness but
> regresses -0.17 on action_recommend_quality and breaks citation format
> end-to-end, dropping `cite_source_coverage` from 1.00 to 0.00.

## Setup

Compiled DSPy module: `src/agent/compiled/synthesize.json` (best of 6
BootstrapFewShotWithRandomSearch candidates, zero few-shot demos; see
`docs/sprint4_dspy_result.md` for compilation detail).

Wire: `src/agent/dspy_synthesize_inference.py` loads the compiled JSON on
import and replaces `messages_create` in `synthesize_node` when
`USE_COMPILED_PROMPTS=1`. The same DeepSeek-via-Anthropic-compatible endpoint
handles inference; only the synthesize prompt changes between OFF and ON.

Eval: 10 fast-tier scenarios (`SMOKE_IDS` × 1, full `FAST_IDS` set), both runs
with `SELF_REFINE_ENABLED=0` so the only changed variable is the synthesize
prompt path.

- OFF (manual prompt): filtered from `eval_results/runs/eval-20260513-105857.json`
- ON  (DSPy compiled): `eval_results/runs/eval-20260513-122128.json`

## Headline numbers (single-judge, DeepSeek)

| Metric | OFF (manual) | ON (compiled) | Delta |
|---|---:|---:|---:|
| answer_correctness | 0.7800 | 0.8300 | **+0.0500** |
| completeness | 0.8350 | 0.8850 | **+0.0500** |
| tool_selection_quality | 0.9700 | 0.9850 | +0.0150 |
| governance_compliance | 1.0000 | 1.0000 | 0.0000 |
| action_recommend_quality | 0.6400 | 0.4700 | **-0.1700** |
| cite_well_formedness | 0.6083 | 0.9611 | +0.3528 |
| cite_source_coverage | 1.0000 | 0.0000 | **-1.0000** |
| cite_id_grounded | 0.7750 | 0.0000 | **-0.7750** |
| traj_tool_f1 | 0.7629 | 0.7486 | -0.0143 |
| avg_elapsed_s | 136.35 | 145.75 | +9.40s (+7%) |
| p50_elapsed_s | 148.50 | 151.08 | +2.58s |
| agent_cost_usd_per_query | 0.003243 | 0.001888 | -0.001355 (-42%) |

Multi-judge consensus numbers (per v4.1 P15 dual regime) will be appended
below once `scripts/run_multi_judge.py` finishes on both inputs.

## Diagnosis

The compiled prompt wins the metrics the DSPy training metric saw — and only
those. Two failure modes show up on the metrics it did not see.

### 1. Citation format regression

Sample DSPy ON answer (brief-008):

> - Jira MOBILE-029 [Critical/In Progress] – blocked by MOBILE-018. **[source:2]**

The model emits `[source:1]`, `[source:2]`, `[source:call1]`, generic tokens
that satisfy "inline citation of the form `[source:id]`" literally. Manual
prompt OFF answers use platform-specific tokens:

> - Jira MOBILE-029 [Critical/In Progress] – blocked by MOBILE-018. **[jira:MOBILE-029]**

The `cite_source_coverage` and `cite_id_grounded` metrics regex on the
platform-prefixed forms (`[jira:X]`, `[slack:Y]`, `[gh:Z]`, etc.), so the
generic `[source:N]` form scores zero across the board even though
`cite_well_formedness` (bracket balance only) goes UP to 0.96.

The root cause: `SynthesizeSignature.__doc__` in `src/agent/dspy_synthesize.py`
reads "Inline citations of the form `[source:id]`. End with 'Audit: N tool
calls.' Concise, prioritized." — verbatim. The manual `prompts/synthesize.md`
follows that same sentence with **six explicit examples**:

```
(e.g. [slack:msg-00123], [jira:PLAT-005], [cal:evt-00045],
 [gh:PR-0042], [gdoc:gdoc-001], [email:email-00100])
```

DSPy throws those examples away; the compiled prompt the model sees has no
exemplars. The model interprets `[source:id]` as a literal pattern.

### 2. Action recommendation regression

The signature output field reads "Synthesized answer with citations + audit
line" — no mention of recommending a next step. The manual prompt template
does not explicitly mention "next step" either, but the few-shot context and
the rubric description ("Prioritize by urgency × impact") nudges the model.
DSPy's terse signature description does not.

Result: -0.17 on action_recommend_quality. The rubric expects answers to end
with a concrete action ("Reschedule Alice 1:1", "Escalate to Finance"). The
compiled prompt answers terminate at the data summary.

### 3. What did go right

answer_correctness and completeness lift +0.05 each. The compiled prompt's
ChainOfThought structure (a `Reasoning:` field before `Answer:`) gives the
model an explicit "think step by step" scratchpad that the manual prompt
lacks. On scenarios where the question is well-scoped, this improves the
final answer's factuality.

This is a real lift, but it is dominated by the citation + action regressions
on a balanced rubric. Net production impact is **net negative**.

## Ship decision

**USE_COMPILED_PROMPTS=0 default in v1.** Keep the wire code and compiled JSON
as portfolio artifacts demonstrating DSPy compilation + inference work end to
end; do not gate the public deploy on the compiled path.

The fix-forward (v1.5):
- update `SynthesizeSignature.__doc__` in `src/agent/dspy_synthesize.py` to
  include the six citation exemplars and an explicit "end with a specific
  next action" line; recompile; re-run this ablation
- alternative: a dual-signature module that emits two outputs (answer +
  action), so the rubric metric is directly trainable

## Portfolio framing

The honest-result lesson: DSPy moves the prompt-engineering effort from the
prompt file to the **signature file**. Anything not in the signature is gone
after compilation. The training metric (multi-judge answer_correctness with
expected_topics redacted per P3) cannot see what the compile loses. This is a
class of failure that "the compile is fine, the prompt was wrong" obscures
from anyone who only reads the headline metric.

The matching positive lesson: when the signature is well-specified, the
compiled candidates score 78-82 on a balanced 2-judge metric vs the manual
prompt's open-ended rubric score of 0.69 (different scales, but the relative
improvement is real). The DSPy infrastructure is not the problem; signature
care is.

## Per v4.1 P15 — dual judge regime addendum (multi-judge running)

Multi-judge consensus (`scripts/run_multi_judge.py`) gives both the 2-judge
regime (Anthropic Haiku + OpenAI gpt-4o-mini, the DSPy training metric per
N1) and the 3-judge regime (+ DeepSeek, the comparison metric used by every
other v4 ablation). Numbers will be inserted here when the multi-judge job
completes.

## Reproducibility

```bash
# OFF (manual prompt, baseline tier-fast subset already in 105857):
SELF_REFINE_ENABLED=0 USE_COMPILED_PROMPTS=0 uv run python scripts/run_eval.py --tier fast

# ON (DSPy compiled prompt):
SELF_REFINE_ENABLED=0 USE_COMPILED_PROMPTS=1 uv run python scripts/run_eval.py --tier fast

# Comparison:
uv run python scripts/compare_dspy.py --off <OFF.json> --on <ON.json> \
  --out docs/sprint4_dspy_agent_ablation.md

# Multi-judge (P15 dual regime):
uv run python scripts/run_multi_judge.py --input <OFF.json>
uv run python scripts/run_multi_judge.py --input <ON.json>
```
