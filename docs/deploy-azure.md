# Deploy: Azure Container Apps

> Status: live alongside Fly.io since 2026-05-13. Azure adds a second cloud target for cross-cloud demonstration; Fly.io remains the primary URL cited in the README.

Azure Container Apps deployment for EKA. The project also runs on Fly.io; both clouds serve the same image so the stack stays exercised against two providers.

## Architecture

Three Container Apps share one managed environment in `westeurope` (Amsterdam):

```
                      Azure Container Apps env  (westeurope)
                      eka-env
                      +----------------------------------------+
  https://<fqdn>  --> | eka-api          external, port 8000   |
                      |   FastAPI + LangGraph, ACR image       |
                      |                                        |
                      | eka-qdrant       internal, port 6333   |
                      |   qdrant/qdrant:latest                 |
                      |                                        |
                      | eka-postgres     internal, port 5432   |
                      |   postgres:15-alpine                   |
                      +----------------------------------------+

  Container Registry: ekaregistry<id>.azurecr.io  (Basic SKU, admin enabled)
  Resource group:     eka-rg
```

Service-to-service DNS inside the environment uses the app names (`http://eka-qdrant:6333`, `eka-postgres:5432`).

## Runtime note: what is actually on the request path

The `/query` runtime in v4 does not depend on Qdrant or Postgres. The retrieval stack reads from the gitignored synthetic dataset baked into the image at build time, and the audit log writes to stdout / Langfuse. Qdrant and Postgres are deployed for parity with `docker-compose.yml` and to keep the architecture upgradeable, not because they are on the hot path.

Implication: the API works on a cold start even before any ingestion step. If you later wire Qdrant retrieval into `/query`, run a one-shot ingestion via `az containerapp exec -n eka-api ...` after the API comes up. Container Apps does not attach persistent volumes by default, so collections rebuild on cold start; the dataset is deterministic from `seed=42` so the rebuild is byte-stable.

## Reproduce

The `infra/azure/deploy.sh` script runs the full sequence. Steps below are the same commands, laid out for review. Run from repo root.

```bash
# 1. Resource group and provider registrations
az group create -n eka-rg -l westeurope
for ns in Microsoft.App Microsoft.OperationalInsights Microsoft.ContainerRegistry; do
  az provider register -n "$ns" --wait
done

# 2. Container Registry (name must be globally unique)
ACR_NAME="ekaregistry$(date +%s | tail -c 7)"
az acr create -g eka-rg -n "$ACR_NAME" --sku Basic --admin-enabled true -l westeurope
ACR_LOGIN=$(az acr show -n "$ACR_NAME" --query loginServer -o tsv)
az acr login -n "$ACR_NAME"

# 3. Build + push (local docker; ACR Tasks is not available on the free tier
#    subscription used here, so we cannot use `az acr build`).
docker build -f infra/Dockerfile -t "$ACR_LOGIN/eka-api:latest" .
docker push "$ACR_LOGIN/eka-api:latest"

# 4. Container Apps environment
az extension add -n containerapp --upgrade --yes
az containerapp env create -g eka-rg -n eka-env -l westeurope

# 5. Postgres sidecar (internal, port 5432, single replica)
az containerapp create -g eka-rg -n eka-postgres \
  --environment eka-env \
  --image postgres:15-alpine \
  --ingress internal --transport tcp --target-port 5432 --exposed-port 5432 \
  --min-replicas 1 --max-replicas 1 \
  --secrets "postgres-password=<generated-strong>" \
  --env-vars POSTGRES_USER=eka POSTGRES_DB=eka \
             POSTGRES_PASSWORD=secretref:postgres-password

# 6. Qdrant sidecar (internal, port 6333, single replica)
az containerapp create -g eka-rg -n eka-qdrant \
  --environment eka-env \
  --image qdrant/qdrant:latest \
  --ingress internal --transport tcp --target-port 6333 --exposed-port 6333 \
  --min-replicas 1 --max-replicas 1

# 7. eka-api (external, port 8000, scale-to-zero)
ACR_PASS=$(az acr credential show -n "$ACR_NAME" --query passwords[0].value -o tsv)
az containerapp create -g eka-rg -n eka-api \
  --environment eka-env \
  --image "$ACR_LOGIN/eka-api:latest" \
  --registry-server "$ACR_LOGIN" \
  --registry-username "$ACR_NAME" \
  --registry-password "$ACR_PASS" \
  --ingress external --target-port 8000 --transport auto \
  --min-replicas 0 --max-replicas 3 \
  --cpu 1.0 --memory 2.0Gi \
  --secrets \
      "deepseek-api-key=<from .env>" \
      "langfuse-public-key=<from .env>" \
      "langfuse-secret-key=<from .env>" \
      "postgres-password=<same as step 5>" \
  --env-vars \
      DEEPSEEK_API_KEY=secretref:deepseek-api-key \
      LANGFUSE_PUBLIC_KEY=secretref:langfuse-public-key \
      LANGFUSE_SECRET_KEY=secretref:langfuse-secret-key \
      LANGFUSE_BASE_URL=https://cloud.langfuse.com \
      ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic \
      LLM_MODEL='deepseek-v4-pro[1m]' \
      QDRANT_HOST=eka-qdrant QDRANT_PORT=6333 \
      POSTGRES_HOST=eka-postgres POSTGRES_PORT=5432 \
      POSTGRES_USER=eka POSTGRES_DB=eka

# 8. Verify
FQDN=$(az containerapp show -g eka-rg -n eka-api \
  --query properties.configuration.ingress.fqdn -o tsv)
curl "https://$FQDN/health"
```

## Cost estimate

Warm baseline (one Postgres replica, one Qdrant replica, scale-to-zero API):

| Component | SKU | Monthly cost (approx) |
|---|---|---:|
| Azure Container Registry | Basic | ~$5 |
| Container Apps env baseline | Consumption | $0 fixed (charged per vCPU-second + GB-second) |
| eka-api | min 0, max 3, 1 vCPU + 2 GiB | first 180k vCPU-sec + 360k GiB-sec/month free |
| eka-qdrant | min 1 max 1, 0.5 vCPU + 1 GiB | ~$10-15 (always-on past free tier) |
| eka-postgres | min 1 max 1, 0.5 vCPU + 1 GiB | ~$10-15 (always-on past free tier) |
| **Total** | | **~$20-35/mo at burn-rate**, $0 inside the free trial credit window |

The Free Trial credit ($200 over 30 days) covers the first month. After that, scaling Qdrant and Postgres to min 0 is not safe for stateful workloads, so the steady-state cost sits in the $20-35 band. Fly.io stays the primary URL because that deploy is single-app and runs at $5-10/mo.

## Gotchas

- **No persistent volumes.** Container Apps does not mount Azure Files by default. Qdrant collections and the Postgres audit log are ephemeral and rebuild on cold restart. The synthetic dataset is byte-deterministic from `seed=42`, so the rebuild is reproducible. Azure Files mounts are v1.5 scope.
- **ACR Tasks disabled on free tier.** `az acr build` returns `TasksOperationsNotAllowed` on free-trial subscriptions. Use local `docker build` + `docker push` (above).
- **Internal ingress uses environment DNS.** Inside the env, `http://eka-qdrant` resolves to the qdrant app. No extra service discovery glue.
- **Free tier provider registration.** First-time use of Container Apps needs `Microsoft.App`, `Microsoft.OperationalInsights`, and `Microsoft.ContainerRegistry` registered. The `deploy.sh` script does this idempotently.
- **Secret rotation.** Secrets are scoped to the Container App. Rotate via `az containerapp secret set -n eka-api --secrets <name>=<value>`, then `az containerapp revision restart -n eka-api`.

## Cross-cloud note

Fly.io stays the primary URL in the README hero. The Azure deploy is additive; `fly.toml` is untouched.
