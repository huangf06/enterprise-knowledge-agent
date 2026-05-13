# A3 semantic cache (Sprint 3)

Cache (query, user_role) -> answer, with BGE-M3 cosine similarity over the cached queries. Skips the agent entirely on cache hit, returning the prior answer immediately.

Implementation: `src/agent/semantic_cache.py`. Storage: SQLite at `eval_results/semantic_cache.sqlite` (gitignored). Lookup: linear scan over rows scoped to the requesting user_role, returning the highest-cosine row above `DEFAULT_THRESHOLD = 0.93`.

Wired into `src/api/main.py` `/query` handler: on cache hit, emits `cache_hit` SSE event + `final` event with the stored answer + `done`, skipping graph execution. On cache miss, the agent runs normally and the resulting answer is `put()` into cache for next time.

Disabled by default (`SEMANTIC_CACHE_ENABLED=0`). Production deploy on Fly.io should set this to `1`; eval runs should leave it off so each scenario goes through the full agent graph for honest measurement.

## Smoke

```
exact match: 1.00
paraphrase match: 0.96    -> hit (above 0.93)
role mismatch: None       -> correctly partitioned
```

## Expected lift

Per-query cost (no cache): $0.00203 (from N2 baseline).
Per-query cost (cache hit): ~$0.0001 - 1 BGE-M3 embedding call for the lookup vector.
Cost reduction on hit: ~95%.

Latency baseline: 171s avg / 254s p95 (N2).
Latency on hit: ~0.5s (embedding + SQLite lookup).
Latency reduction on hit: ~340x.

These numbers are *per-hit* gains. The end-to-end lift depends on hit rate, which depends on traffic pattern. For a public demo where most visitors paste the same example query ("Give me Sarah's Monday briefing"), hit rate >50% is realistic and the average per-query cost drops to ~$0.001.

## Ablation

The headline frontier ablation lives at `docs/frontier3_self_refine.md` (Self-Refine ON vs OFF, n=30) and was the source for the README leaderboard row. A combined "Self-Refine ON × cache ON" ablation was not run in v4 because Self-Refine shipped OFF by default per its honest-negative result; running the cache experiment ON-top-of an OFF feature has no end-to-end deploy story. Per-component numbers from the two underlying runs:

| Variant | per-query USD | p50 latency | quality (consensus answer_correctness) | Source |
|---|---:|---:|---:|---|
| Baseline (Self-Refine OFF, cache OFF) | $0.00361 | 163s | 0.69 | `eval_results/runs/eval-20260513-105857.json` (N2 baseline + leaderboard) |
| Self-Refine ON, cache OFF | $0.00388 | 177s | 0.62 | `docs/frontier3_self_refine.md` (honest negative, hence OFF default) |
| + cache ON | not measured (v1.5) | not measured (v1.5) | (quality unchanged on hit by construction) | deferred |

The cache row's "quality on hit" is by construction equal to the cached answer's quality, so the column doesn't move; the point is the cost/latency Pareto, not a quality gain. The v1.5 follow-up is to re-run with the production cache hit rate and report the end-to-end USD/query against a real traffic mix.

## Production hazards

- **Stale answers**: cache TTL not yet implemented; production should evict on age (e.g., 24h) and on tool-data-change events.
- **Cross-user leakage**: partition is per `user_role` (manager / IC / HR), not per user. Two managers see each other's cached answers if their queries are semantically identical. Acceptable for v1 demo; v1.5 should add `user_name` partition or per-user salt.
- **PII in cache**: SQLite at rest is unencrypted. Production deploy must mount the file on an encrypted volume or rotate to an encrypted store.
