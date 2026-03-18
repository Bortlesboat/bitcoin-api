#!/usr/bin/env bash
# Azure Cloud Sprint — Teardown Runbook (Run June 14, 2026 or when credits expire)
# Run: bash scripts/azure-teardown.sh
set -euo pipefail

RG="satoshi-api-sprint"
PG_SERVER="satoshi-indexer-pg"
PG_DB="satoshi_index"

echo "=== Azure Cloud Sprint — Teardown ==="
echo "This will delete ALL Azure sprint resources."
echo ""

# --- 1. Export PostgreSQL data before deletion ---
echo "[1/4] Exporting PostgreSQL data..."
PG_HOST=$(python -m azure.cli postgres flexible-server show --resource-group "$RG" --name "$PG_SERVER" --query "fullyQualifiedDomainName" -o tsv 2>/dev/null || echo "SKIPPED")
if [ "$PG_HOST" != "SKIPPED" ]; then
    echo "  Run: pg_dump -h $PG_HOST -U satoshi -d $PG_DB > backup_$(date +%Y%m%d).sql"
    echo "  Press Enter after backup is done (or Ctrl+C to abort)..."
    read -r
fi

# --- 2. Push images to GHCR before deleting ACR ---
echo "[2/4] Push images to GHCR (free)..."
echo "  Run: docker tag satoshiapiacr.azurecr.io/satoshi-api:latest ghcr.io/bortlesboat/satoshi-api:latest"
echo "  Run: docker push ghcr.io/bortlesboat/satoshi-api:latest"
echo "  Press Enter after done..."
read -r

# --- 3. Download any artifacts from S3 ---
echo "[3/4] Download S3 artifacts..."
echo "  Run: aws s3 sync s3://satoshi-api-artifacts ./artifacts-backup/"
echo "  Press Enter after done..."
read -r

# --- 4. Delete the entire resource group (everything in one command) ---
echo "[4/4] Deleting resource group '$RG' and ALL resources within it..."
python -m azure.cli group delete --name "$RG" --yes --no-wait
echo "  Resource group deletion initiated (runs async)."

echo ""
echo "=== Teardown Initiated ==="
echo ""
echo "Fallback status:"
echo "  [x] API → Main PC + Cloudflare Tunnel (already running)"
echo "  [x] AI endpoints → OLLAMA_URL=http://192.168.1.238:11434 (Mac Mini)"
echo "  [x] Fee alerts → scripts/fee_alert_worker.py as GMKtec cron"
echo "  [x] PostgreSQL → Local Docker (docker-compose.yml)"
echo "  [x] Container images → GHCR (free)"
echo "  [x] Metrics → Prometheus /metrics (built-in)"
echo "  [x] CI → WSL2 or GitHub Actions"
echo ""
echo "Don't forget to also:"
echo "  - Delete AWS resources: Lambda, CloudFront, S3 bucket"
echo "  - Update .env to remove AZURE_* and APPLICATIONINSIGHTS_* vars"
echo "  - Set OLLAMA_URL in .env for AI endpoint fallback"
