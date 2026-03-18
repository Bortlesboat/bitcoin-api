# Satoshi API — Multi-Cloud Architecture

## System Diagram

```
                     Internet
                        |
            +-----------+-----------+
            |                       |
     Cloudflare Tunnel         Azure CDN
     (production)              (staging)
            |                       |
     Main PC (local)         Azure Container Apps
     +-----------+           +------------------+
     | Satoshi   |           | Satoshi API      |
     | API       |           | (staging)        |
     | :9332     |           | satoshi-staging  |
     +-----------+           +------------------+
            |                       |
     Bitcoin Core            Azure OpenAI
     (full node)             GPT-4o mini
     :8332 RPC               (AI endpoints)
            |                       |
     Local SQLite            Azure App Insights
     (WAL mode)              (telemetry)
            |
     Ollama (fallback AI)
     Mac Mini :11434
     qwen2.5:14b
```

## Component Map

| Component | Production | Azure Staging | After Credits Expire |
|---|---|---|---|
| **API** | Main PC + Cloudflare Tunnel | Container Apps (0-3 replicas) | Main PC only |
| **Bitcoin RPC** | Local Bitcoin Core | N/A (no node) | Local Bitcoin Core |
| **AI Provider** | Azure OpenAI GPT-4o mini | Same (shared) | Ollama on Mac Mini or local |
| **Database** | Local SQLite (WAL) | Local SQLite (ephemeral) | Local SQLite |
| **Observability** | Prometheus /metrics | App Insights (OTLP) | Prometheus only |
| **Fee Alerts** | In-process (planned) | Azure Functions | GMKtec cron job |
| **CI Testing** | WSL2 | ACI (on-demand) | WSL2 |
| **Artifacts** | Local disk | AWS S3 | Local disk |
| **CDN** | Cloudflare (free) | AWS CloudFront | Cloudflare |

## AI Provider Chain

Priority order (first available wins):

1. **Azure OpenAI** — `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_KEY` → GPT-4o mini
2. **OpenAI Direct** — `OPENAI_API_KEY` → gpt-4o-mini
3. **Ollama** — `OLLAMA_URL` → any model (qwen2.5:7b local, qwen2.5:14b Mac Mini)
4. **Noop** — No config → 503 "AI not configured"

Switching providers = change env vars, restart. Zero code changes.

## Cost Summary

| Resource | Monthly Cost | Provider |
|---|---|---|
| Container Registry (Basic) | $5 | Azure |
| Container Apps (0-3 replicas) | $0-10 | Azure |
| Azure OpenAI (GPT-4o mini) | $5-25 | Azure |
| Application Insights | $0 (free tier) | Azure |
| S3 Bucket | $0.02 | AWS |
| Lambda | $0 (free tier) | AWS |
| CloudFront | $5-10 | AWS |
| Budget Alerts | $0 | Both |
| **Total** | **~$15-50/mo** | |

## Security

- Azure OpenAI key in `.env` (gitignored, never committed)
- ACR admin credentials in Container Apps secrets
- AWS credentials in `~/.aws/credentials` (local only)
- Budget alerts at $300/mo (Azure) and $50/mo (AWS)
- No PII or financial data in any cloud resource

## Teardown Runbook

When credits expire (June 14, 2026):

```bash
# 1. Delete all Azure resources
python -m azure.cli group delete --name satoshi-sprint --yes

# 2. Comment out Azure vars in .env, uncomment Ollama
# AZURE_OPENAI_ENDPOINT=...  →  # AZURE_OPENAI_ENDPOINT=...
# OLLAMA_URL=http://192.168.1.238:11434  →  OLLAMA_URL=http://192.168.1.238:11434

# 3. Delete AWS resources
python -m awscli s3 rb s3://satoshi-api-artifacts-2026 --force
python -m awscli lambda delete-function --function-name satoshi-health
python -m awscli cloudfront delete-distribution --id E26RWEYFYQ2CSI
python -m awscli iam delete-role --role-name satoshi-lambda-role

# 4. Restart API
# Production continues unchanged on Main PC + Cloudflare Tunnel
```
