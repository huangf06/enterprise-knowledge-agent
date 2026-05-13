# Fly.io Deploy Checklist (handoff to Fei)

> **Status: DONE 2026-05-13.** Production URL: <https://enterprise-knowledge-agent.fly.dev/>.
> This document is kept as a record of what was decided + what gotchas the
> first deploy surfaced. See `[[project-eka-v4-deploy-live]]` memory for the
> living configuration state (warm machine, secrets list, app name).
>
> If redeploying from scratch on a different Fly account, follow the steps
> below as-written; the Dockerfile + fly.toml at HEAD already encode the
> fixes that came out of the first run.

## Pre-flight (5 min)

1. Confirm Fly account active and CLI logged in.

   ```bash
   fly auth whoami
   fly orgs list
   ```

2. Confirm the app name `enterprise-knowledge-agent` is free (or pick a unique
   suffix). If taken:

   ```bash
   # In infra/fly.toml, change `app = "..."` to e.g. "eka-fei-demo".
   ```

3. Quick smoke locally first so a broken main does not get pushed to prod:

   ```bash
   uv run python scripts/run_eval.py --tier smoke
   uv run uvicorn src.api.main:api --reload  # POST /query, check SSE
   ```

## Qdrant decision (BLOCKING — pick before deploy)

The fly.toml currently expects `QDRANT_HOST = qdrant.internal`, which means a
sister Fly app named "qdrant" reachable over the Fly private network. Options:

| Option | Effort | Cost | Notes |
|---|---|---|---|
| **A. Qdrant Cloud free tier** (Recommended) | 5 min | $0 | Free 1GB shard. Edit `infra/fly.toml` env to `QDRANT_HOST=<cluster>.qdrant.io`, `QDRANT_PORT=6333`, set `QDRANT_API_KEY` as secret. |
| B. Sister Fly app `qdrant` | 20 min | +~$5/mo | `fly launch -a qdrant --image qdrant/qdrant:latest --region ams --vm-memory 1024`; mount volume; expose 6333 internally. |
| C. Skip retrieval at boot | 0 min | $0 | The agent works without Qdrant up — only retrieval-dependent scenarios degrade. Deploy now, add Qdrant later. |

Recommended: **A** for first deploy. Fei picks.

## Secrets to set (the load-bearing ones)

```bash
fly secrets set --app enterprise-knowledge-agent \
  DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" \
  LANGFUSE_PUBLIC_KEY="$LANGFUSE_PUBLIC_KEY" \
  LANGFUSE_SECRET_KEY="$LANGFUSE_SECRET_KEY" \
  LANGFUSE_BASE_URL="https://cloud.langfuse.com" \
  COHERE_API_KEY="$COHERE_API_KEY"
```

Optional (only if exposing eval endpoints publicly — currently not):

```bash
fly secrets set --app enterprise-knowledge-agent \
  ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  OPENAI_API_KEY="$OPENAI_API_KEY"
```

If option A above is picked:

```bash
fly secrets set --app enterprise-knowledge-agent \
  QDRANT_API_KEY="$QDRANT_API_KEY"
```

Verify (does NOT print values):

```bash
fly secrets list --app enterprise-knowledge-agent
```

## First deploy

```bash
# From repo root.
fly launch --copy-config --no-deploy --org personal --region ams \
  --name enterprise-knowledge-agent
# (Skip the prompts for postgres/redis/etc — they're not used.)

fly deploy --remote-only
```

Wait for `Visit your newly deployed app at https://enterprise-knowledge-agent.fly.dev`.

## Post-deploy smoke (5 min, verifies the deploy is real)

1. **Health endpoint**:

   ```bash
   curl -sf https://enterprise-knowledge-agent.fly.dev/health
   ```

   Expect 200 + `{"status": "ok"}`.

2. **`/query` SSE smoke** (no retrieval-required path so works even without Qdrant):

   ```bash
   curl -N -X POST https://enterprise-knowledge-agent.fly.dev/query \
     -H 'Content-Type: application/json' \
     -d '{"query": "What is on my calendar today?", "user_name": "Sarah Chen", "user_role": "manager"}'
   ```

   Expect SSE events: `plan` → `tool_select` → `tool_execute` → `reflect` → `synthesize`.

3. **Langfuse trace lands**: open <https://cloud.langfuse.com>, project `enterprise-knowledge-agent-v4`, confirm a new trace from the smoke query above is visible with per-node generations.

4. **Auto-stop verification** (the cost guard):

   ```bash
   fly status --app enterprise-knowledge-agent
   ```

   After ~5 min idle the machine should suspend. `fly status` shows `state=stopped`.

## Rollback (in case of disaster)

```bash
fly releases list --app enterprise-knowledge-agent
fly deploy --image <previous-release-id>
# OR: fly scale count 0 --app enterprise-knowledge-agent  (kills traffic)
```

## What I have NOT done (intentional handoff)

- `fly launch` — not run; needs interactive prompts only Fei can answer (account choice, region confirm).
- `fly deploy` — not run; production deploy must be Fei's explicit action.
- Custom domain DNS (kea.feihuang.dev or similar) — out of scope of v4 deploy.
- Production scaling / autoscale rules — current single-VM auto-stop config is correct for demo traffic.

## Cost expectation post-deploy

- Fly.io VM (shared-cpu-2x + 2GB, auto-stop): ~$0.10/day idle, $0.50/day if a sustained visitor session keeps the machine warm. **$5-10/month** typical.
- Langfuse Cloud free tier: $0 (well under 50K observations/month).
- Cohere rerank-v3: $0 (1000 free calls/month, demo will use <100).
- DeepSeek API: pay-as-you-go. Each `/query` is ~$0.003. Hard cap available via DeepSeek dashboard.
- Qdrant Cloud free tier (option A): $0.
- **Total expected**: under $10/month at typical demo traffic.
