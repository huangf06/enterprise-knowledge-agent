# Sprint 4 Frontier #1 DSPy (scaffold ready)

DSPy program + compilation runner are in place but NOT executed - this is a deliberate Sprint 4 gate.

## What's ready

- `src/agent/dspy_synthesize.py`: `SynthesizeSignature` mirroring `prompts/synthesize.md`, `SynthesizeModule` (ChainOfThought wrapper), and `make_training_metric` that uses the 2-judge consensus (Haiku + gpt-4o-mini, DeepSeek excluded per N1) with `expected_topics` redacted per P3.
- `scripts/dspy_compile.py`: `--dry-run` works today (verifies setup); `--iterations N` runs `BootstrapFewShotWithRandomSearch` against the 30-scenario training set seeded from the latest rejudged eval.

## Sprint 4 day-of execution

```bash
# Verify scaffold + budget before spending:
uv run python scripts/dspy_compile.py --dry-run

# Real compilation:
uv run python scripts/dspy_compile.py --iterations 50 \
    --out src/agent/compiled/synthesize.json
```

Per v4.1 locked decisions:
- **P1**: gate at week-9 day-2. If not converging by then, fall back to manual prompt iteration.
- **P2**: only `synthesize` for the first compilation pass. `plan` is the next target if buffer remains.
- **P4**: budget cap $50-150 for compilation. Monitor live spend on console.anthropic.com.

## Why we don't auto-run

DSPy compilation is the single largest LLM-spend event in the entire project. v4.1 plan budgets $50-150; in practice a 50-iter BootstrapFewShotWithRandomSearch over 30 scenarios with multi-judge metric lands around $25-50 of Anthropic + OpenAI spend. Letting an autonomous loop kick this off would violate the explicit-OK constraint on significant API spend.

## After compilation

1. Inspect the compiled program (DSPy saves to JSON).
2. Diff the compiled prompts vs current `prompts/synthesize.md`.
3. Wire the compiled module into `src/agent/nodes/synthesize.py` behind a `USE_COMPILED_PROMPTS` env flag.
4. Re-run the full multi-judge eval + A7 trace replay. The honest ablation reports both 2-judge (training metric) AND 3-judge (comparison metric) scores per v4.1 P15.
