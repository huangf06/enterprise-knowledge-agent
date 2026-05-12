# Architecture

Single-page reference. The repo layout is in the README; this file explains the *why*.

## Layered view

```
┌────────────────────────────────────────────────────────────────────────┐
│ UI: Gradio chat (W7) / curl / SDK                                      │
└────────────────────────────────────────────────────────────────────────┘
                                  │ POST /query (JSON)
┌────────────────────────────────────────────────────────────────────────┐
│ src/api/main.py                                                        │
│  - FastAPI + sse-starlette                                             │
│  - Resolves user identity from data/eval/users_seed.yaml               │
│  - Streams agent events as SSE                                         │
└────────────────────────────────────────────────────────────────────────┘
                                  │ astream(state)
┌────────────────────────────────────────────────────────────────────────┐
│ src/agent/  (LangGraph state machine)                                  │
│                                                                        │
│   plan ──► tool_select ──► tool_execute ──► reflect ──► (loop / END)   │
│                  │                                                     │
│                  └──no tool needed─────┐                               │
│                                        ▼                               │
│                                   synthesize                           │
│                                                                        │
│  - Each node is a small Python function in src/agent/nodes/            │
│  - State is a TypedDict in src/agent/state.py                          │
│  - Prompts live in prompts/*.md and are git-versioned                  │
│  - Max 6 iterations hard cap                                           │
└────────────────────────────────────────────────────────────────────────┘
            │                       │                          │
            │                       │                          ▼
            │                       │            ┌──────────────────────┐
            │                       │            │ src/governance/      │
            │                       │            │  - rbac.py           │
            │                       │            │  - pii_redact.py     │
            │                       │            │  - injection_guard.py│
            │                       │            │  - audit.py          │
            │                       │            │  - gdpr.py           │
            │                       │            └──────────────────────┘
            │                       ▼
            │            ┌──────────────────────┐
            │            │ src/tools/  6 tools  │
            │            │  - slack_query       │
            │            │  - jira_query        │
            │            │  - calendar_query    │
            │            │  - github_pr_review  │
            │            │  - gdocs_search      │
            │            │  - email_query       │
            │            └──────────────────────┘
            │                       │
            │                       ▼
            │            ┌──────────────────────┐
            │            │ data/synthetic/*.json│ ← scripts/generate_data.py
            │            │ (gitignored, repro from seed=42)
            │            └──────────────────────┘
            ▼
    ┌───────────────────┐    ┌───────────────────┐
    │ src/llm/          │    │ src/retrieval/    │
    │  - anthropic_     │    │  - embeddings     │
    │    client.py      │    │    (BGE-M3)       │
    │  - cost_ledger.py │    │  - vector_store   │
    └───────────────────┘    │    (Qdrant)       │
            │                │  - index_gdocs    │
            ▼                └───────────────────┘
    DeepSeek V4 Pro                  │
    (Anthropic-compatible            ▼
     endpoint)                  Qdrant container
```

## Data flow for one query

1. Client POSTs to `/query`. API resolves user identity → builds initial `AgentState`.
2. `astream` iterates the graph; each node emits `streaming_events` that get pushed onto the SSE channel.
3. `plan` node runs one LLM call, no tools. Emits the plan text.
4. `tool_select` runs one LLM call **with** the 6-tool catalog. If the LLM returns a `tool_use` block, route to `tool_execute`; if text only, route directly to `synthesize`.
5. `tool_execute` runs the chosen tool with `(args, ctx)` where `ctx` carries role + user identity. The result is sanitized + RBAC-filtered inside the tool, then wrapped by `injection_guard.frame_tool_result` so the LLM cannot misread it as instructions.
6. `reflect` runs one short LLM call to decide YES / NO. Caps iterations at 6.
7. `synthesize` runs the final LLM call with the entire tool history and produces the markdown answer with inline citations.

## Why LangGraph and not a single tool-runner loop

The 5-node decomposition is the design's preference for *visibility*. The reveal panel in the UI (W7) shows each node's contribution distinctly, which is harder when a single LLM tool-runner emits one merged trace. Cost is one extra LLM call per query (the reflect step) vs the tool-runner shortcut.

## What is intentionally NOT in this diagram

- Multi-tenant isolation (v1.5)
- Real Okta / SAML federation (v1.5)
- Langfuse self-hosted traces (W6 scaffold, full setup pending)
- The `similar_briefing_history` tool (v1.5; removed from W3 per Codex review)
- Multi-LLM ablation (GPT-4o / Sonnet 4.6 / Haiku 4.5; v1.5 per W2 decision)

## Module reuse — Demo 1 (cross-source) vs Demo 2 (HR Helpdesk single-source)

Demo 2 is an optional W7 case study, not a hard gate. Module reuse table per design Section 4:

| Module | Demo 1 | Demo 2 | Reuse |
|---|---|---|---|
| LangGraph 5-node skeleton | yes | yes | 100% |
| Tool base + registry | yes | yes | 100% |
| RBAC policy engine | 6 tools, 3 roles | 1 tool, 2 roles | 90% (yaml swap) |
| PII redact + injection guard | yes | yes | 100% |
| Audit log | yes | yes | 100% |
| LLM judge harness | yes | yes | 100% |
| Synthetic generator | 6-source | HR handbook only | 0% (new) |
| Tool implementations | 6 tools | 3 tools | 0% (new) |
| Eval scenarios | 30 KW | 5 HR | 0% (new) |
| Gradio chat + reveal | yes | yes | 95% |

Framing: "core agent / governance / eval infrastructure reused; vertical-specific data + tools + scenarios re-authored." This is a modularity demonstration, not a transferability proof.
