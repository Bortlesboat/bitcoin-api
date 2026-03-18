#!/usr/bin/env bash
# Azure Cloud Sprint — Sprint 1 Foundation Setup
# Run: bash scripts/azure-setup.sh
# Prereq: az login (run interactively first)
set -euo pipefail

# --- Configuration ---
RG="satoshi-api-sprint"
LOCATION="eastus"
ACR_NAME="satoshiapiacr"
APP_NAME="satoshi-api-staging"
APP_ENV="satoshi-api-env"
PG_SERVER="satoshi-indexer-pg"
PG_DB="satoshi_index"
PG_USER="satoshi"
PG_PASSWORD="${PG_PASSWORD:-$(openssl rand -base64 16)}"

echo "=== Azure Cloud Sprint — Foundation Setup ==="
echo "Resource Group: $RG"
echo "Location: $LOCATION"
echo ""

# --- 1. Resource Group ---
echo "[1/6] Creating resource group..."
python -m azure.cli group create --name "$RG" --location "$LOCATION" -o none

# --- 2. Container Registry (Basic, $5/mo) ---
echo "[2/6] Creating Container Registry..."
python -m azure.cli acr create --resource-group "$RG" --name "$ACR_NAME" --sku Basic --admin-enabled true -o none
ACR_LOGIN=$(python -m azure.cli acr show --name "$ACR_NAME" --query loginServer -o tsv)
echo "  ACR: $ACR_LOGIN"

# --- 3. Push Docker image ---
echo "[3/6] Building and pushing Docker image..."
python -m azure.cli acr login --name "$ACR_NAME"
cd "$(dirname "$0")/.."
docker build -t "$ACR_LOGIN/satoshi-api:latest" .
docker push "$ACR_LOGIN/satoshi-api:latest"
cd -

# --- 4. Container Apps Environment ---
echo "[4/6] Creating Container Apps environment..."
python -m azure.cli containerapp env create \
  --name "$APP_ENV" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  -o none

# --- 5. Deploy Container App ---
echo "[5/6] Deploying Container App..."
ACR_CREDS=$(python -m azure.cli acr credential show --name "$ACR_NAME" --query "{username:username,password:passwords[0].value}" -o json)
ACR_USER=$(echo "$ACR_CREDS" | python -c "import sys,json; print(json.load(sys.stdin)['username'])")
ACR_PASS=$(echo "$ACR_CREDS" | python -c "import sys,json; print(json.load(sys.stdin)['password'])")

python -m azure.cli containerapp create \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --environment "$APP_ENV" \
  --image "$ACR_LOGIN/satoshi-api:latest" \
  --registry-server "$ACR_LOGIN" \
  --registry-username "$ACR_USER" \
  --registry-password "$ACR_PASS" \
  --target-port 9332 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 3 \
  --cpu 0.25 \
  --memory 0.5Gi \
  --env-vars \
    "API_HOST=0.0.0.0" \
    "API_PORT=9332" \
    "BITCOIN_RPC_HOST=${BITCOIN_RPC_HOST:-127.0.0.1}" \
    "CORS_ORIGINS=*" \
  -o none

FQDN=$(python -m azure.cli containerapp show --name "$APP_NAME" --resource-group "$RG" --query "properties.configuration.ingress.fqdn" -o tsv)
echo "  Staging URL: https://$FQDN"

# --- 6. PostgreSQL Flexible Server (B1ms, $12/mo) ---
echo "[6/6] Creating PostgreSQL Flexible Server..."
python -m azure.cli postgres flexible-server create \
  --resource-group "$RG" \
  --name "$PG_SERVER" \
  --location "$LOCATION" \
  --admin-user "$PG_USER" \
  --admin-password "$PG_PASSWORD" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --database-name "$PG_DB" \
  --public-access 0.0.0.0 \
  --yes \
  -o none 2>/dev/null || echo "  (PostgreSQL may already exist)"

PG_HOST=$(python -m azure.cli postgres flexible-server show --resource-group "$RG" --name "$PG_SERVER" --query "fullyQualifiedDomainName" -o tsv 2>/dev/null || echo "$PG_SERVER.postgres.database.azure.com")
PG_DSN="postgresql://$PG_USER:$PG_PASSWORD@$PG_HOST:5432/$PG_DB?sslmode=require"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Staging URL:  https://$FQDN"
echo "ACR:          $ACR_LOGIN"
echo "PostgreSQL:   $PG_HOST"
echo ""
echo "--- Environment variables for .env ---"
echo "INDEXER_POSTGRES_DSN=$PG_DSN"
echo ""
echo "--- Next steps ---"
echo "1. Add BITCOIN_RPC_* env vars to Container App (needs Cloudflare Tunnel)"
echo "2. Update Container App with: python -m azure.cli containerapp update --name $APP_NAME --resource-group $RG --set-env-vars ..."
echo "3. Enable Application Insights: python -m azure.cli monitor app-insights component create --app satoshi-insights --location $LOCATION --resource-group $RG"
