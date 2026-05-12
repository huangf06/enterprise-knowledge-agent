# Deploy

Two supported deploy targets in v1, both Anthropic-operated-free. Pick one.

## Option A — Fly.io

```bash
fly launch --copy-config --no-deploy  # one-time, picks up infra/fly.toml
fly secrets set DEEPSEEK_API_KEY=sk-...
fly deploy
fly open
```

Fly.io free allowance covers one shared-CPU machine + 3GB persistent volume; this fits the agent. Qdrant runs in-cluster via a sister Fly app, or use Qdrant Cloud Free for an external instance.

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
