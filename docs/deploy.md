# Deploy

> Status: Fly deploy live at <https://enterprise-knowledge-agent.fly.dev/> since 2026-05-13. Azure Container Apps added as a second live target on the same date; see [docs/deploy-azure.md](deploy-azure.md). HF Spaces is documented but not in production use.

Three deploy targets in v1. Fly.io is the primary URL cited in the README hero. Azure Container Apps is the cross-cloud demonstration (3-app sidecar stack matching `docker-compose.yml`). HF Spaces is the Gradio-UI variant.

## Option A — Fly.io (live)

`fly.toml` at repo root is the canonical config (`infra/fly.toml` is a documentation mirror): region `ams`, shared-cpu-2x + 2GB RAM (sized for BGE-M3 embedding model in-process), `min_machines_running = 1` so one machine stays warm 24/7 to avoid the ~2-3 minute Python import cold-start. The HA replica auto-stops when idle.

```bash
# One-time (from repo root):
fly launch --copy-config --no-deploy

# Set required secrets:
fly secrets set DEEPSEEK_API_KEY=sk-...
fly secrets set LANGFUSE_PUBLIC_KEY=pk-lf-...
fly secrets set LANGFUSE_SECRET_KEY=sk-lf-...
fly secrets set LANGFUSE_BASE_URL=https://cloud.langfuse.com
fly secrets set COHERE_API_KEY=...

# Optional - multi-judge eval (not needed for public demo serving):
fly secrets set ANTHROPIC_API_KEY=sk-ant-...
fly secrets set OPENAI_API_KEY=sk-proj-...

# Deploy:
fly deploy
fly open  # opens https://enterprise-knowledge-agent.fly.dev
```

Cost in production (~$5-10/month) for the warm shared-cpu-2x + 2GB machine + auto-stopping HA replica at typical demo traffic. Qdrant is **not** used by the `/query` runtime in v4 (only by offline retrieval indexing scripts), so the deploy is single-app; the sister-app Qdrant pattern is deferred to v1.5.

Observability after deploy:
- Langfuse Cloud dashboard at https://cloud.langfuse.com (public-read URL captured in project_eka_v4_day1_setup memory).
- Every `/query` POST emits an `agent_query` trace; per-node `messages_create` calls show as child generations with token usage.

## Option B — Hugging Face Space

Push the repo to `https://huggingface.co/spaces/<user>/enterprise-knowledge-agent`. The Space picks up `infra/huggingface-space.yml` for metadata and `infra/Dockerfile.gradio` for the build. Set `DEEPSEEK_API_KEY` as a Secret in Space Settings.

The HF variant launches the Gradio reveal-panel UI on port 7860; the FastAPI endpoint is also reachable internally.

## Option C (deferred, v1.5) — AWS ECS Fargate

Terraform / CDK in `infra/aws/`. AWS Fargate runs the API, RDS Postgres holds the audit log, Secrets Manager carries the API key. Listed in `v1.5_backlog.md`.

## Local-only

Always works:

```bash
docker compose up -d
# FastAPI on http://localhost:8000
# Gradio: uv run python -m src.ui.app  → http://localhost:7860
```
