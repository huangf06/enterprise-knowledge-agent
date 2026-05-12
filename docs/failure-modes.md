# Failure modes

Per design Section 7. Documents what goes wrong today and what is deferred to v1.5.

| # | Failure mode | Trigger | Current handling | Gap |
|---|---|---|---|---|
| 1 | LLM hallucinates citations | The model invents `gdoc-999` or `PR-9999` that doesn't exist in the data | The synthesizer is instructed to use real IDs; W6 will add a post-synth validator that rejects unresolvable citations | No live citation validator yet |
| 2 | RBAC bypass via prompt rewording | User asks "as Sarah's CEO, list…" | Agent's role context is server-set; `check_resource` is enforced regardless of phrasing. Adversarial regression covers this | Sophisticated jailbreaks are not all caught; document confidence is empirical |
| 3 | PII surfaces in tool output | Tool result contains an IBAN or phone | `redact()` runs before every tool result reaches LLM | Multi-shape composite PII (name + role + amount together) is not caught |
| 4 | Loop divergence | Reflection keeps voting NO | Hard cap of 6 iterations + `iteration >= max` short-circuit in reflect | Tail-quality drop is real; W6 adds Langfuse traces to diagnose |
| 5 | Cost spike on a long query | Agent makes 6 tool calls, each with large outputs | `max_iterations` cap + per-tool `max_items` defaults | No per-query USD cap yet; cost ledger only records, doesn't enforce |
| 6 | Audit log tampering | Bad actor mutates the JSONL | Append-only convention but no DB-level enforcement | Hash chain stays v1.5 |
| 7 | Synthetic data drift | Re-run with a different seed produces different "facts" | Generator is byte-deterministic from seed=42; tests assert this | Real-data scaffolds need a separate eval set (v1.5) |
| 8 | Tool API failure | Tool raises an exception | `tool_execute_node` catches and returns `ERROR running…` text | No retry / circuit-breaker yet |
| 9 | Wrong recommended action | Agent suggests a harmful next step | LLM judge's `action_recommend_quality` rates this; below-0.7 actions are flagged in eval | No live human-in-the-loop approval gate |
| 10 | Multi-turn drift | Same user asks 10 follow-up questions | The agent is single-turn in v1; multi-turn memory is v1.5 | No conversation context yet |
