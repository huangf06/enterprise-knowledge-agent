# Deploy

Two supported deploy targets in v1, both Anthropic-operated-free. Pick one.

## Option A — Fly.io (recommended for v4 public demo)

`infra/fly.toml` is pre-configured for the v4 demo: region `ams`, shared-cpu-2x + 2GB RAM (sized for BGE-M3 embedding model in-process), auto-stop when idle for cost control.

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

Cost (post-launch, with auto-stop): ~$5-10/month for shared-cpu-2x + 2GB at typical demo traffic. Qdrant currently expected to run in-cluster via a sister Fly app or via Qdrant Cloud Free; the v4 Sprint 1 deploy assumes Qdrant cloud (sister app deploy is a Sprint 5 cleanup).

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
