# Signature blog outline: "Four frontier techniques. Three honest negatives, one positive."

> Draft outline for Fei's voice. Tone notes: terse, technical, "show your
> losses" framing. The reader is a hiring manager in NL who has seen 50 LLM
> portfolios this quarter.

## Working title

**"I shipped Self-Refine, DSPy, MoE, and Counterfactual in my enterprise agent. Three hurt or were within noise; one held governance under perturbation. Here is the math, including the Goodhart reversal I almost missed."**

Alternate hooks (pick on personal taste):
- "What the LLM optimization papers don't tell you when n=30."
- "Four frontier techniques on a real benchmark. Here are the with-vs-without
  tables I almost did not publish."
- "Multi-judge consensus flipped the sign of one of my ablations. That is the post."

## Opening (1-2 paragraphs)

The hero claim of every LLM-agent paper is "we did X, here are the metrics."
The honest claim almost no paper makes is "we did X, here is the ablation, and
X did not move the needle." After building an enterprise agent end-to-end I
have three of those ablations to ship. Lead with the table.

> Insert: 3-row results summary table (Self-Refine, DSPy, MoE); quality delta
> + cost delta + ship/no-ship verdict.

## Section 1: Setup (1 paragraph)

What the agent does in 2 sentences. What the benchmark is in 2 sentences.
Why "honest with-vs-without" was the project goal from day 1.

## Section 2: Self-Refine: a -0.08 hit on a +0.08 metric

Cite Madaan 2023. State the v4.1 plan choice: prose-only critique per P6
(critique sees `(question, answer)` only, no tool history). Show the table
from `docs/frontier3_self_refine.md`:

- answer_correctness, completeness, id_grounded all regress -0.05 to -0.08
- source_coverage jumps to perfect 1.0
- latency +18%

The diagnosis section is the punchy bit: P6's information bottleneck. The
critique can't read tool history, so when it flags "missing detail" the
regenerated answer loses detail rather than adding it. CRITIC (Gou 2024) would
have fixed this with tool re-querying; but the graph restructure was scoped
out of v4.

Closer: ship `SELF_REFINE_ENABLED=0` default. Keep the code path for the
+0.08 source_coverage in audit-heavy use cases.

## Section 3: DSPy: the Goodhart reversal

Cite the v4.1 DSPy work: P13 (one node only; `synthesize`), P15 (dual judge
regime), N1 (judge-pool isolation). Compilation result table:

- 6 candidate programs scored 78-82 on the 2-judge training metric
- best variant has zero few-shot demonstrations
- agent-level ablation on 10 fast-tier scenarios (see `docs/sprint4_dspy_agent_ablation.md`):

| Metric | OFF | ON (2-judge, training) | ON (3-judge, comparison) |
|---|---:|---:|---:|
| answer_correctness | 0.83 (1J) / 0.825 (2J) / 0.855 (3J) | **+0.05 (2J)** | **-0.03 (3J)** |
| action_recommend_quality | 0.64 (1J) | -0.13 (2J) | -0.05 (3J) |
| cite_source_coverage (algorithmic) | 1.00 | 0.00 | 0.00 |

The headline finding: **the +0.05 lift on the 2-judge regime is a Goodhart
effect**. DSPy trained against a 2-judge metric that excluded DeepSeek (the
agent's own model class, per v4.1 N1). Adding DeepSeek back as a third
judge; the comparison metric every other ablation uses; flips the sign
to **-0.03**. Without dual-regime reporting, this would have shipped as
"+0.05 lift". With it, the project found a class of failure that single-
judge eval cannot see.

The matching cite_source_coverage **-1.0** is unrelated to judges:
algorithmic citation grounding regex'd on platform-prefixed tokens like
`[jira:X]`; the DSPy signature dropped the six citation exemplars from the
manual prompt, so the compiled model emitted generic `[source:N]` tokens.
Anything not in the DSPy signature is gone after compilation.

When DSPy would have paid off: a less-tuned starting prompt, a larger
training set, a signature that includes all the rubric criteria.

## Section 4: Multi-LLM MoE: pick your trade-off

Cite F4 (Switch Transformer of agents); the actual v4.1 instantiation is much
simpler than the literature MoE; it is per-node vendor routing with a
fallback policy. Insert the Pareto table from
`docs/sprint5_moe_pareto.md`:

- DeepSeek (baseline)
- Anthropic Sonnet 4.6
- Anthropic Haiku 4.5
- OpenAI gpt-4o-mini

Quality delta on synthesize, cost-per-query delta, latency delta. Identify
which route is on the Pareto frontier. Explicit "ship-or-skip" call.

Anti-claim: the "use Sonnet 4.6 for synthesize because it is the smartest
model" framing is what every prompt cookbook says. Show whether it actually
beats the cheaper DeepSeek baseline by a margin worth 12x the cost. Be
honest about how small the n=10 confidence intervals are.

## Section 5: Counterfactual robustness: where governance bends

Cite v4 plan R3 / P10 / P11. Three perturbations:

- entity_swap (R3): non-protagonist rename, EY → PwC
- noise_injection (P10): plausible-but-irrelevant chatter padded onto results
- doc_deletion (P11): most-cited paragraph dropped

Insert the table from `docs/sprint6_counterfactual_result.md`. The headline:
**does governance compliance stay at 1.0?** That's the load-bearing test.
Citation and answer_correctness can degrade; they just expose tradeoffs.
Governance is supposed to be hard.

## Section 6: What I learned about benchmarks (1 paragraph)

n=30 LLM-judge eval has a 0.05-0.10 noise floor. Any frontier technique
claiming a smaller lift is indistinguishable from noise. Multi-judge
consensus + dispersion makes this explicit; single-judge claims hide it.

## Closer

The signature lesson of v4: "ship the ablation, not the claim." If a
technique earns its keep, the table shows it. If it does not, the table is
still the right thing to publish. The portfolio signal is the honesty, not
the magnitude.

End with the GitHub link + the leaderboard URL.

## Suggested length

1500-2200 words. Three tables. One code snippet (the DSPy signature). No
sponsored sections, no AI-art header; the seriousness is the brand.

## Pre-publish checklist

- [ ] Run through Hemingway editor: target Grade 8-10
- [ ] Personal sentence in the closer: why you did this and what you would
      change next
- [ ] Two-paragraph "about the project" footer pointing back to the repo
- [ ] Re-check the 4 ablation docs are reachable from the blog
      (`frontier3_self_refine.md`, `sprint4_dspy_agent_ablation.md`,
      `sprint5_moe_pareto.md`, `sprint6_counterfactual_result.md`)
