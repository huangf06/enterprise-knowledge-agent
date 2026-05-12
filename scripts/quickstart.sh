#!/usr/bin/env bash
# Quickstart smoke. Runs every gate locally end-to-end.
# Assumes: docker is running, .env has DEEPSEEK_API_KEY set, uv installed.

set -euo pipefail

cd "$(dirname "$0")/.."

echo "[1/7] Installing deps..."
uv sync --extra dev > /dev/null

echo "[2/7] Generating synthetic data..."
uv run python scripts/generate_data.py --seed 42 --output data/synthetic > /dev/null

echo "[3/7] Running unit tests..."
uv run pytest tests/ -q

echo "[4/7] Bringing up Qdrant..."
docker compose up -d qdrant
sleep 3

echo "[5/7] Indexing GDocs corpus..."
uv run python scripts/baseline_rag_smoke.py | tail -10

echo "[6/7] W1 hard gate verification..."
uv run python scripts/verify_synthetic.py | tail -25

echo "[7/7] Running 3 adversarial scenarios as a governance smoke..."
uv run python scripts/run_adversarial.py --limit 3

cat <<EOF

==================================================================
Quickstart smoke passed.

Next:
  - uv run uvicorn src.api.main:api --reload          # FastAPI on :8000
  - uv run python -m src.ui.app                       # Gradio on :7860
  - uv run python scripts/run_eval.py                 # full 30-scenario eval (~100 min)
  - uv run python scripts/run_retrieval_sanity.py     # HotpotQA + MS Marco
==================================================================
EOF
