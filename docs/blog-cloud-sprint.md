# Running a Bitcoin API on Azure: Lessons from a 90-Day Sprint

*Published on dev.to — Draft*

---

I had $1,000 in Azure credits expiring in 90 days and $100 in AWS credits. Here's how I used them to add AI-powered features to an open-source Bitcoin API without creating vendor lock-in.

## The Setup

[Satoshi API](https://bitcoinsapi.com) is a Bitcoin fee intelligence API — it tells you when to send, what fee to pay, and whether to wait. It runs on a home server with a full Bitcoin Core node, served through a Cloudflare Tunnel. Total infrastructure cost: $3/month.

The question wasn't "should I move to the cloud?" — it was "what can free credits teach me that I can't learn locally?"

## What I Built

### 1. AI-Powered Fee Advice (the killer feature)

```
GET /api/v1/ai/fees/advice?urgency=high&context=payment&amount_btc=0.5
```

Response:
```json
{
  "advice": "Since your payment is urgent and current fees are at 1.0 sat/vB,
             now is an excellent time to send. Don't wait — fees could rise.",
  "provider": "azure_openai",
  "fee_data": {"next_block_sat_vb": 1.0, "6_blocks_sat_vb": 1.0}
}
```

This hits Azure OpenAI's GPT-4o mini with live fee data as context. Cost: ~$0.0003 per call. At 100 calls/day, that's $0.77/month.

The key architecture decision: **a provider abstraction layer**.

```python
class AIProvider(Protocol):
    async def complete(self, messages, *, max_tokens, temperature) -> str: ...

# Priority: Azure OpenAI > OpenAI > Ollama > Noop (503)
```

When credits expire, I change one environment variable and the API falls back to Ollama running on a Mac Mini. Zero code changes, zero downtime.

### 2. Fee Alert Webhooks

```
POST /api/v1/alerts/fees
{"webhook_url": "https://your-app.com/hook", "threshold_sat_vb": 5, "condition": "below"}
```

"Notify me when fees drop below 5 sat/vB." The webhook fires from an Azure Function (timer trigger, every 60 seconds). After credits expire? Same logic runs as a cron job on a $150 mini PC.

### 3. Multi-Cloud Staging

The same Docker image runs on:
- Azure Container Apps (staging)
- My home server (production)
- Any Docker host (self-hosted)

No cloud-specific SDKs. No proprietary services in the critical path. OpenTelemetry for observability (works with any OTLP backend).

## What I Learned

**1. Azure for Startups credits are real** — $1,000 covers a lot of experimentation. Container Apps' scale-to-zero means you only pay when traffic hits.

**2. Azure OpenAI is underrated for API products** — GPT-4o mini at $0.15/1M input tokens makes AI features viable even at free tier. The latency (~2s) is acceptable for an advice endpoint.

**3. Not everything needs the cloud** — My Bitcoin node runs locally because it needs 650GB of blockchain data. Trying to put that in the cloud would cost $50+/month in storage alone. The cloud is for compute and AI; the node stays home.

**4. Provider abstractions pay for themselves immediately** — I wrote it once (150 lines) and it saved me from Azure lock-in on day one.

**5. Budget alerts are non-negotiable** — I set $300/month (Azure) and $50/month (AWS) alerts before creating any resources. Credits or not, you need guardrails.

## The Numbers

| What | Cost | Notes |
|---|---|---|
| Container Registry | $5/mo | Stores Docker images |
| Container Apps | $0-10/mo | Scale to zero when idle |
| Azure OpenAI (GPT-4o mini) | $5-25/mo | ~100 calls/day |
| App Insights | $0 | Free tier |
| AWS S3 + Lambda | $0.02/mo | Artifacts + health check |
| **Total** | **~$15-40/mo** | Of $1,000 available |

## What Survives After Credits Expire

Everything customer-facing:
- 4 AI endpoints (fall back to local Ollama)
- Fee alert webhooks (cron job)
- All the code, tests, and infrastructure-as-code scripts

The cloud was scaffolding. The features are permanent.

---

*[Satoshi API](https://github.com/Bortlesboat/bitcoin-api) is open source. The AI endpoints, webhook system, and provider abstraction are all in the repo.*
