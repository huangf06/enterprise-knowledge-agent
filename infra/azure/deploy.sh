#!/usr/bin/env bash
# Azure Container Apps deployment for the Enterprise Knowledge Agent.
#
# Reproduces the dual-cloud deploy alongside Fly.io (see docs/deploy-azure.md).
# Idempotent where possible; secret values are read from the local .env and
# injected only as Azure secrets, never committed.
#
# Prerequisites:
#   - Azure CLI 2.86+ with `az login` complete
#   - Docker daemon running (for `docker build` + `docker push`)
#   - A populated .env at repo root with the API keys listed below
#
# Usage:
#   bash infra/azure/deploy.sh [ACR_NAME]
#
# If ACR_NAME is omitted, a fresh `ekaregistry<unix-seconds-tail>` is created.

set -euo pipefail

RG="${RG:-eka-rg}"
LOCATION="${LOCATION:-westeurope}"
ENV_NAME="${ENV_NAME:-eka-env}"
API_APP="${API_APP:-eka-api}"
QDRANT_APP="${QDRANT_APP:-eka-qdrant}"
POSTGRES_APP="${POSTGRES_APP:-eka-postgres}"

if [[ $# -ge 1 ]]; then
  ACR_NAME="$1"
else
  ACR_NAME="ekaregistry$(date +%s | tail -c 7)"
fi

echo ">> Resource group"
az group create -n "$RG" -l "$LOCATION" -o table

echo ">> Provider registration (idempotent)"
for ns in Microsoft.App Microsoft.OperationalInsights Microsoft.ContainerRegistry; do
  az provider register -n "$ns" --wait >/dev/null
done

echo ">> Azure Container Registry: $ACR_NAME"
if ! az acr show -n "$ACR_NAME" -g "$RG" >/dev/null 2>&1; then
  az acr create -g "$RG" -n "$ACR_NAME" --sku Basic --admin-enabled true --location "$LOCATION" -o none
fi
ACR_LOGIN=$(az acr show -n "$ACR_NAME" --query loginServer -o tsv)
az acr login -n "$ACR_NAME"

echo ">> Build + push eka-api image"
docker build -f infra/Dockerfile -t "$ACR_LOGIN/eka-api:latest" .
docker push "$ACR_LOGIN/eka-api:latest"

echo ">> Container Apps extension"
az extension add -n containerapp --upgrade --yes >/dev/null

echo ">> Container Apps environment: $ENV_NAME"
if ! az containerapp env show -n "$ENV_NAME" -g "$RG" >/dev/null 2>&1; then
  az containerapp env create -g "$RG" -n "$ENV_NAME" -l "$LOCATION" -o none
fi

# Read secrets from local .env. They never touch the repo or this script.
set -a
# shellcheck disable=SC1091
source .env
set +a

POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-eka_dev}"

echo ">> Postgres sidecar (internal, port 5432)"
az containerapp create \
  -g "$RG" -n "$POSTGRES_APP" \
  --environment "$ENV_NAME" \
  --image postgres:15-alpine \
  --ingress internal --transport tcp --target-port 5432 \
  --exposed-port 5432 \
  --min-replicas 1 --max-replicas 1 \
  --secrets "postgres-password=$POSTGRES_PASSWORD" \
  --env-vars POSTGRES_USER=eka POSTGRES_DB=eka POSTGRES_PASSWORD=secretref:postgres-password \
  -o none || \
az containerapp update -g "$RG" -n "$POSTGRES_APP" --image postgres:15-alpine -o none

echo ">> Qdrant sidecar (internal, port 6333)"
az containerapp create \
  -g "$RG" -n "$QDRANT_APP" \
  --environment "$ENV_NAME" \
  --image qdrant/qdrant:latest \
  --ingress internal --transport tcp --target-port 6333 \
  --exposed-port 6333 \
  --min-replicas 1 --max-replicas 1 \
  -o none || \
az containerapp update -g "$RG" -n "$QDRANT_APP" --image qdrant/qdrant:latest -o none

echo ">> eka-api (external, port 8000, scale-to-zero up to 3)"
ACR_PASS=$(az acr credential show -n "$ACR_NAME" --query passwords[0].value -o tsv)
az containerapp create \
  -g "$RG" -n "$API_APP" \
  --environment "$ENV_NAME" \
  --image "$ACR_LOGIN/eka-api:latest" \
  --registry-server "$ACR_LOGIN" \
  --registry-username "$ACR_NAME" \
  --registry-password "$ACR_PASS" \
  --ingress external --target-port 8000 --transport auto \
  --min-replicas 0 --max-replicas 3 \
  --cpu 1.0 --memory 2.0Gi \
  --secrets \
      "deepseek-api-key=${DEEPSEEK_API_KEY}" \
      "anthropic-api-key=${ANTHROPIC_API_KEY:-}" \
      "openai-api-key=${OPENAI_API_KEY:-}" \
      "cohere-api-key=${COHERE_API_KEY:-}" \
      "langfuse-public-key=${LANGFUSE_PUBLIC_KEY:-}" \
      "langfuse-secret-key=${LANGFUSE_SECRET_KEY:-}" \
      "langfuse-base-url=${LANGFUSE_BASE_URL:-https://cloud.langfuse.com}" \
      "postgres-password=${POSTGRES_PASSWORD}" \
  --env-vars \
      DEEPSEEK_API_KEY=secretref:deepseek-api-key \
      ANTHROPIC_API_KEY=secretref:anthropic-api-key \
      OPENAI_API_KEY=secretref:openai-api-key \
      COHERE_API_KEY=secretref:cohere-api-key \
      LANGFUSE_PUBLIC_KEY=secretref:langfuse-public-key \
      LANGFUSE_SECRET_KEY=secretref:langfuse-secret-key \
      LANGFUSE_BASE_URL=secretref:langfuse-base-url \
      POSTGRES_PASSWORD=secretref:postgres-password \
      ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic \
      LLM_MODEL=deepseek-v4-pro[1m] \
      SELF_REFINE_ENABLED=0 \
      USE_COMPILED_PROMPTS=0 \
      QDRANT_HOST="$QDRANT_APP" \
      QDRANT_PORT=6333 \
      POSTGRES_HOST="$POSTGRES_APP" \
      POSTGRES_PORT=5432 \
      POSTGRES_USER=eka \
      POSTGRES_DB=eka \
  -o none

FQDN=$(az containerapp show -g "$RG" -n "$API_APP" --query properties.configuration.ingress.fqdn -o tsv)
echo ">> Live at: https://$FQDN"
echo ">> Verify:   curl https://$FQDN/health"
