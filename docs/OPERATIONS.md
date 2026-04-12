# Satoshi API -- Operations Guide

Everything you need to run, maintain, and market Satoshi API. This is the "how do I..." doc.

---

## Quick Reference

| What | How |
|------|-----|
| **API is running at** | `http://localhost:9332` (local) / `https://bitcoinsapi.com` (public) |
| **Interactive docs** | `http://localhost:9332/docs` |
| **Process** | `python -m uvicorn bitcoin_api.main:app --host 0.0.0.0 --port 9332` |
| **Config** | Shared `.env` at `C:/Users/andre/Bortlesboat/bitcoin-api/.env`, linked into the promoted release |
| **Database** | Shared `data/bitcoin_api.db` at `C:/Users/andre/Bortlesboat/bitcoin-api/data/`, linked into the promoted release |
| **Auto-start** | Bitcoin Knots: Registry Run key. Cloudflared: Registry Run key. API: Scheduled Task `SatoshiAPI` -> local `start-api.bat` shim -> `ops/bitcoinsapi/start-prod.bat`. Watchdog: `SatoshiAPIWatchdog` (5 min). Backup: `SatoshiAPIBackup` (daily 3 AM) |
| **HTTPS** | Cloudflare Tunnel (`cloudflared` Registry Run key) routes bitcoinsapi.com -> localhost:9332 |
| **Monitoring** | UptimeRobot (5 min), watchdog-api.sh (5 min via "SatoshiAPIWatchdog" task, auto-restart — runs from main repo, resolves API_DIR via `releases/bitcoin-api-current` symlink), smoke-test-api.sh (cron) |
| **Diagnostics** | `bash scripts/diagnose.sh` (node, tunnel, API, cache, DB, version, tests) |
| **IBIT tool source** | `C:/Users/andre/ibit-weekend-calculator` builds the `/ibit` page and exports `dist/index.html` to `static/ibit.html` |
| **Version mgmt** | `bash scripts/release.sh` for git tags plus `powershell -File C:/Users/andre/Bortlesboat/ops/bitcoinsapi/promote-release.ps1 -ReleasePath <release>` for prod cutover |

---

## 1. Starting / Stopping / Restarting the API

### Current production layout
```text
Code releases:   C:/Users/andre/Bortlesboat/releases/bitcoin-api-<timestamp>-<sha>
Stable pointer:  C:/Users/andre/Bortlesboat/releases/bitcoin-api-current
Launcher shim:   C:/Users/andre/Bortlesboat/bitcoin-api/start-api.bat
Prod launcher:   C:/Users/andre/Bortlesboat/ops/bitcoinsapi/start-prod.bat
```

The promoted release uses links back to the shared local state in `C:/Users/andre/Bortlesboat/bitcoin-api/` for `.env`, `data/`, and `logs/`. Do not point production directly at a dirty working tree again.

### Start (if not running)
```bash
cmd.exe /c C:/Users/andre/Bortlesboat/bitcoin-api/start-api.bat
# or
schtasks /Run /TN SatoshiAPI
```

### Check if running
```bash
curl http://localhost:9332/api/v1/health
```
If you get `{"data":{"status":"ok",...}}`, it's running.

### Find the process
```bash
# From bash (Claude Code)
wmic process where "name='python3.12.exe'" get ProcessId,CommandLine | grep 9332
```
Look for the line with `--port 9332`. Note the PID number at the end.

### Restart (kill + start)
```bash
cmd.exe /c C:/Users/andre/Bortlesboat/bitcoin-api/start-api.bat
# or
schtasks /Run /TN SatoshiAPI
```
The launcher shim kills anything already listening on `9332`, then starts the promoted release from `releases/bitcoin-api-current`. Downtime is typically a few seconds; Cloudflare may show a brief 502.

### Why restart?
You need to restart after changing `.env` (the API reads env vars at startup, not live).

---

## 2. Configuration (.env)

The API reads its config from `~/Bortlesboat/bitcoin-api/.env`. Current settings:

```ini
BITCOIN_RPC_HOST=127.0.0.1        # Your Bitcoin Core node
BITCOIN_RPC_PORT=8332              # Bitcoin Core RPC port
BITCOIN_DATADIR=E:/                # Bitcoin data directory (for cookie auth)
API_HOST=0.0.0.0                   # Listen on all interfaces
API_PORT=9332                      # API port
CORS_ORIGINS=http://localhost:3000,http://localhost:9332,https://bitcoinsapi.com
ADMIN_API_KEY=<your-key>           # Required for /api/v1/analytics/* endpoints
```

### Adding/changing a setting
1. Edit `~/Bortlesboat/bitcoin-api/.env`
2. Restart the API (see Section 1)

### Available settings (from `.env.example`)
- `BITCOIN_RPC_USER` / `BITCOIN_RPC_PASSWORD` -- RPC auth (alternative to cookie auth)
- `RPC_TIMEOUT=10` -- RPC call timeout in seconds (fails fast into stale cache)
- `RATE_LIMIT_ANONYMOUS=30` -- requests/min for anonymous users
- `RATE_LIMIT_FREE=100` -- requests/min for free API key users
- `RATE_LIMIT_PRO=500` -- requests/min for pro users
- `RATE_LIMIT_EXEMPT_KEYS` -- comma-separated key hashes that bypass all rate limits (e.g. internal bots)
- `ADMIN_API_KEY` -- key for admin analytics endpoints
- `ADMIN_NOTIFICATION_EMAIL` -- receives alerts on new API key registrations
- `ENABLE_PRICES_ROUTER=true` -- toggle CoinGecko price endpoint
- `ENABLE_ADDRESS_ROUTER=true` -- toggle address lookup endpoints
- `ENABLE_EXCHANGE_COMPARE=true` -- toggle exchange comparison endpoint
- `ENABLE_SUPPLY_ROUTER=true` -- toggle supply endpoint
- `ENABLE_STATS_ROUTER=true` -- toggle statistics endpoints (utxo-set, segwit, op-returns)

### Indexer Configuration

The blockchain indexer provides address transaction history and enriched transaction lookups. It requires PostgreSQL.

**Enable:**
```bash
# In .env:
ENABLE_INDEXER=true
INDEXER_POSTGRES_DSN=postgresql://satoshi:satoshi@localhost:5432/satoshi_index
INDEXER_ZMQ_ENDPOINT=tcp://127.0.0.1:28332  # optional, falls back to 10s polling
INDEXER_BATCH_SIZE=50
```

**Start PostgreSQL:**
```bash
docker compose up -d postgres-indexer
```

**Monitor sync progress:**
```bash
curl http://localhost:9332/api/v1/indexed/status
```

The indexer starts automatically when the API boots with `ENABLE_INDEXER=true`. Initial sync takes several days (940K+ blocks). Address queries return partial results during sync.

**Endpoints (4):**
- `GET /api/v1/indexed/address/{addr}/balance` — balance, tx count, first/last seen
- `GET /api/v1/indexed/address/{addr}/txs` — paginated tx history
- `GET /api/v1/indexed/tx/{txid}` — enriched tx with resolved inputs + spent status
- `GET /api/v1/indexed/status` — sync progress, ETA, blocks/sec

### Fee Observatory (optional)

The observatory reads the Fee Observatory's SQLite DB (read-only) to expose multi-source fee estimator comparison data.

```ini
ENABLE_OBSERVATORY=true                                    # default: true
OBSERVATORY_DB=~/.bitcoin-fee-observatory/observatory.db   # default path
```

Requires the Fee Observatory to be collecting data (`bitcoin-fee-observatory` repo). Endpoints return 503 if the DB doesn't exist.

**Endpoints (3):**
- `GET /api/v1/fees/observatory/scoreboard` — per-source accuracy ranking
- `GET /api/v1/fees/observatory/block-stats` — per-block fee percentiles
- `GET /api/v1/fees/observatory/estimates` — multi-source fee estimate time series

**Dashboard:** `GET /fee-observatory` — branded page with iframe to Streamlit dashboard (port 8505).

### x402 Stablecoin Micropayments (optional)

Enables pay-per-call via the x402 protocol (USDC on Base). Requires the `bitcoin-api-x402` package.

```ini
ENABLE_X402=true                          # default: false
X402_PAY_TO_ADDRESS=0xYourEVMWallet...    # EVM wallet address for USDC receipts
```

**Enable:** Set both env vars in `.env` and restart. Install the extension: `pip install -e ../bitcoin-api-x402`.

**Disable:** Set `ENABLE_X402=false` (or remove it) and restart. All paid endpoints revert to free.

**Dashboard:** Visit `/x402` for live payment analytics (challenges, payments, revenue, conversion rate).

**Endpoints:**
- `GET /api/v1/x402-info` -- payment info and paid endpoint listing
- `GET /api/v1/x402-demo` -- sandbox endpoint to test the 402 flow (no real payment)
- `GET /api/v1/x402-stats` -- aggregated payment analytics (JSON)
- `GET /x402` -- visual analytics dashboard

**Data retention:** x402 payment records auto-pruned after 180 days at startup.

### Stripe Billing (optional)
```ini
STRIPE_SECRET_KEY=sk_live_...       # Stripe API secret key
STRIPE_WEBHOOK_SECRET=whsec_...     # Stripe webhook signing secret
STRIPE_PRICE_ID=price_...           # Stripe Price ID for Pro tier
STRIPE_SUCCESS_URL=https://bitcoinsapi.com/billing/success
STRIPE_CANCEL_URL=https://bitcoinsapi.com/billing/cancel
```

If these are not set, billing endpoints return **503 Service Unavailable** with a message that billing is not configured. The rest of the API is unaffected.

---

## 3. Prometheus Metrics

The `/metrics` endpoint exposes Prometheus-format metrics. Requires `X-Admin-Key` header.

```bash
curl -H "X-Admin-Key: $ADMIN_API_KEY" http://localhost:9332/metrics
```

Returns standard Prometheus text format with counters, histograms, and gauges for request latency, error rates, cache hit rates, and active connections. Point your Prometheus scraper at this endpoint.

---

## 4. WebSocket Subscriptions

Connect to `/api/v1/ws` for real-time push notifications (blocks, fees, mempool changes). Requires an API key.

### SSE Streams

SSE streams (`/api/v1/stream/blocks`, `/api/v1/stream/fees`, `/api/v1/stream/whale-txs`) have the following limits:
- **Max duration:** 1 hour per connection (auto-disconnects, clients should reconnect)
- **Connection caps:** 50 concurrent block streams, 50 fee streams, 20 whale streams
- Connections beyond the cap receive a 429 response

```python
import websockets, json

async with websockets.connect(
    "wss://bitcoinsapi.com/api/v1/ws",
    extra_headers={"X-API-Key": "YOUR_KEY"}
) as ws:
    # Subscribe to topics
    await ws.send(json.dumps({"subscribe": ["blocks", "fees"]}))
    async for msg in ws:
        print(json.loads(msg))
```

**Topics:** `blocks`, `fees`, `mempool`. The server pushes events via an in-process pub/sub hub (`pubsub.py`).

---

## 5. Stripe Billing

Four billing endpoints under `/api/v1/billing/`. All return **503** if Stripe env vars are not configured.

### Stripe Setup

1. **Create product + price in Stripe Dashboard:**
   - Go to Products -> Add Product
   - Create "Satoshi API Pro" with a recurring monthly price
   - Copy the price ID (starts with `price_...`)

2. **Set environment variables** in `.env`:
   ```ini
   STRIPE_SECRET_KEY=sk_live_...       # From Stripe Dashboard -> Developers -> API Keys
   STRIPE_WEBHOOK_SECRET=whsec_...     # Generated when creating webhook endpoint
   STRIPE_PRICE_ID=price_...           # From step 1
   ```
   All three are required. If `STRIPE_SECRET_KEY` or `STRIPE_PRICE_ID` is missing, billing endpoints return 503.

3. **Test locally** with Stripe CLI:
   ```bash
   stripe listen --forward-to localhost:9332/api/v1/billing/webhook
   ```
   This prints a webhook signing secret (`whsec_...`) for local testing.

4. **Verify the flow:**
   ```bash
   # Create checkout session (requires API key)
   curl -X POST -H "X-API-Key: YOUR_KEY" http://localhost:9332/api/v1/billing/checkout
   # -> Returns checkout_url, open in browser to complete payment
   # -> Stripe sends webhook -> tier upgrades to "pro"

   # Check subscription status
   curl -H "X-API-Key: YOUR_KEY" http://localhost:9332/api/v1/billing/status

   # Cancel subscription
   curl -X POST -H "X-API-Key: YOUR_KEY" http://localhost:9332/api/v1/billing/cancel
   ```

5. **Production webhook:** Configure in Stripe Dashboard -> Developers -> Webhooks:
   - URL: `https://bitcoinsapi.com/api/v1/billing/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`

Subscription data is stored in the `subscriptions` table (created by `migrations/004_add_subscriptions.sql`), with `stripe_customer_id` linked to the API key.

---

## 6. External Services (all optional)

All three services default to disabled. The API functions fully without them.

### Resend (Transactional Email)

Sends a welcome email with API key + curl quickstart on registration. Fire-and-forget (never blocks registration).

```ini
RESEND_API_KEY=re_...            # From https://resend.com/api-keys
RESEND_FROM_EMAIL=Satoshi API <noreply@bitcoinsapi.com>
RESEND_ENABLED=true              # Set to false to disable (default)
```

**Verify:** Register a new API key and check the email arrives. Check API logs for `Welcome email sent` or `Welcome email failed`.

**Disable:** Set `RESEND_ENABLED=false` in `.env` and restart. Registration still works; key is shown in the response.

### Upstash Redis (Rate Limiting Backend)

Replaces in-memory sliding window with Redis sorted sets. Rate limits persist across restarts and work across multiple workers.

```ini
UPSTASH_REDIS_URL=https://....upstash.io   # From https://console.upstash.com
UPSTASH_REDIS_TOKEN=AX...                   # REST API token
RATE_LIMIT_BACKEND=redis                    # "redis" or "memory" (default)
```

**Verify:** Check startup logs for `Rate limit backend: redis`. If Redis is unreachable, it falls back to in-memory automatically.

**Disable:** Set `RATE_LIMIT_BACKEND=memory` in `.env` and restart. In-memory works fine for single-instance deployments.

### PostHog (Landing Page Analytics)

Privacy-first analytics on landing page and SEO comparison pages. Server-side registration event tracking. No autocapture, no session recording, IP anonymized.

```ini
POSTHOG_API_KEY=phc_...          # From https://us.posthog.com/settings/project-api-key
POSTHOG_HOST=https://us.i.posthog.com
POSTHOG_ENABLED=true             # Set to false to disable (default)
```

**Verify:** Visit the landing page and check PostHog dashboard for page views. Register an API key and check for `api_key_registered` event.

**Disable:** Set `POSTHOG_ENABLED=false` in `.env` and restart. The JS snippet on HTML pages checks the flag server-side and is not injected when disabled.

---

## 7. Analytics Dashboard (Admin Only)

15 endpoints + a visual dashboard that show how people use your API. All require the admin key (except `/analytics/public`).

### Visual Dashboard

Open in browser: `http://localhost:9332/admin/dashboard?key=YOUR_KEY`

**Authentication methods (any one works):**
- Query parameter: `?key=YOUR_KEY` (original, convenient for bookmarks)
- Header: `X-Admin-Key: YOUR_KEY` (for programmatic access)
- Cookie: `admin_token=YOUR_KEY` (set automatically after first query-param login, persists across refreshes)

Auto-refreshes every 60 seconds. Shows KPI cards, charts (requests over time, top endpoints, latency percentiles), per-key usage table, and retention metrics.

### How to query
```bash
# Overview (requests, error rate, avg latency)
curl -H "X-Admin-Key: YOUR_KEY" http://localhost:9332/api/v1/analytics/overview

# Request log (recent requests with details)
curl -H "X-Admin-Key: YOUR_KEY" http://localhost:9332/api/v1/analytics/requests

# Most popular endpoints
curl -H "X-Admin-Key: YOUR_KEY" http://localhost:9332/api/v1/analytics/endpoints

# Error breakdown
curl -H "X-Admin-Key: YOUR_KEY" http://localhost:9332/api/v1/analytics/errors

# Who's using it (user-agent strings)
curl -H "X-Admin-Key: YOUR_KEY" http://localhost:9332/api/v1/analytics/user-agents

# Response time stats
curl -H "X-Admin-Key: YOUR_KEY" http://localhost:9332/api/v1/analytics/latency

# Per-key usage breakdown (hits, latency, error rate per API key)
curl -H "X-Admin-Key: YOUR_KEY" http://localhost:9332/api/v1/analytics/keys

# Day-over-day and week-over-week growth
curl -H "X-Admin-Key: YOUR_KEY" http://localhost:9332/api/v1/analytics/growth

# Slowest endpoints by p95 latency
curl -H "X-Admin-Key: YOUR_KEY" http://localhost:9332/api/v1/analytics/slow-endpoints

# Key retention (active keys in 24h/7d/30d vs total)
curl -H "X-Admin-Key: YOUR_KEY" http://localhost:9332/api/v1/analytics/retention

# Client type breakdown (ai-agent, sdk, browser, bitcoin-mcp)
curl -H "X-Admin-Key: YOUR_KEY" http://localhost:9332/api/v1/analytics/client-types

# MCP-specific funnel
curl -H "X-Admin-Key: YOUR_KEY" http://localhost:9332/api/v1/analytics/mcp-funnel

# Top traffic referrers (where visitors come from)
curl -H "X-Admin-Key: YOUR_KEY" http://localhost:9332/api/v1/analytics/referrers

# Conversion funnel (registered -> activated -> engaged, with UTM source attribution)
curl -H "X-Admin-Key: YOUR_KEY" http://localhost:9332/api/v1/analytics/funnel

# List all registered API key users
curl -H "X-Admin-Key: YOUR_KEY" http://localhost:9332/api/v1/analytics/users
```

Replace `YOUR_KEY` with the value from your `.env` `ADMIN_API_KEY`.

### Auto-Pruning

The background fee collector thread automatically prunes old data once per 24 hours:
- Usage logs older than 90 days are deleted
- Fee history older than 30 days is downsampled to hourly averages
- Fee history older than 365 days is deleted
- Research data (block_confirmations, fee_estimates_log) older than 365 days is deleted

The fee collector also logs multi-source fee estimates every 5 minutes (Core 8 targets, mempool.space 4 targets, local mempool 1 target) and captures block confirmation feerate percentiles on each new block.

Check API logs for `Auto-prune:` messages to confirm it's running.

### Where is the admin key?
In `~/Bortlesboat/bitcoin-api/.env`, the `ADMIN_API_KEY` line.

---

## 8. API Keys (for users)

### Create a new API key
```bash
cd ~/Bortlesboat/bitcoin-api
python scripts/create_api_key.py
```
This generates a key and stores its SHA256 hash in the database.

### How users self-register
Users can POST to `/api/v1/register` with `agreed_to_terms: true` to get a free API key. No admin action needed.

---

## 9. SEO & Marketing Toolkit

### Run SEO metrics check
```bash
cd ~/Bortlesboat/bitcoin-api
python scripts/seo_metrics.py
```
Shows: page accessibility (all 16 pages), GitHub stars, PyPI downloads, PR merge status, Bing indexing, search mentions, API usage stats. Saves data to `data/seo_metrics.db`.

### Daily analytics digest
```bash
# Print to stdout (test mode)
SATOSHI_ADMIN_KEY=<key> python scripts/analytics_digest.py

# Send via email
SATOSHI_ADMIN_KEY=<key> python scripts/analytics_digest.py --email

# Override recipient
SATOSHI_ADMIN_KEY=<key> python scripts/analytics_digest.py --email --to you@example.com
```
Reports: requests/growth/latency/errors/client types/retention/referrers/conversion funnel. Reads admin key from env or `.env`. Designed for daily cron on GMKtec.

### Submit pages to search engines (IndexNow)
```bash
bash scripts/submit_indexnow.sh
```
Auto-runs after every successful deploy via `deploy-api.sh`. Submits all 11 SEO pages to Bing/Yandex.

### Publishing the `/ibit` tool page

The public `https://bitcoinsapi.com/ibit` page is built in the standalone repo at `C:/Users/andre/ibit-weekend-calculator`.

Refresh and export it with:

```powershell
cd C:/Users/andre/ibit-weekend-calculator
npm run refresh:snapshot
npm run build
npm run export:bitcoinsapi
```

Default export target: `C:/Users/andre/bitcoin-api/static/ibit.html`

If you are working from an isolated `bitcoin-api` worktree, also copy `dist/index.html` into that worktree's `static/ibit.html` before running pytest or opening a PR. Then update `static/sitemap.xml` and `static/llms.txt` if the page slug or positioning changes.

### Marketing drafts location
All ready-to-post drafts are in `docs/marketing/drafts/` (gitignored, local-only):
- `reddit-bitcoindev.md` -- r/BitcoinDev (question format, post first)
- `reddit-selfhosted.md` -- r/selfhosted
- `reddit-bitcoin.md` -- r/Bitcoin
- `reddit-python.md` -- r/Python
- `hackernews-show-hn.md` -- Hacker News Show HN
- `stacker-news.md` -- Stacker News

> **Note:** Marketing drafts and strategy docs are gitignored. They exist locally
> but are never committed to the public repo. Source of truth: `bitcoin-api-internal` (private).

### Keeping marketing materials accurate
When endpoints, tests, or features change, run:
```
/marketing-sync
```
This Claude Code skill audits all marketing files against the actual codebase and fixes stale facts.

### Other marketing files (gitignored, local-only)
- `docs/marketing/launch-plan.md` -- Master tracker (what's posted, what's pending)
- `docs/marketing/distribution-channels.md` -- Full channel strategy
- `docs/marketing/brand-strategy.md` -- Voice, positioning, visual identity
- `docs/marketing/umbrel-submission-guide.md` -- App store submission guide

---

## 10. Running Tests

```bash
cd ~/Bortlesboat/bitcoin-api

# Unit tests (no node needed, ~18s)
python -m pytest tests/test_api.py -q

# E2E tests (requires running API + node)
python -m pytest tests/test_e2e.py -m e2e

# Load test (requires running API)
locust -f tests/locustfile.py --host http://localhost:9332

# Security check (requires running API + API key)
SATOSHI_API_KEY=<your-key> bash scripts/security_check.sh

# Legal audit (checks license, ToS, privacy policy consistency)
python scripts/legal_audit.py

# Security audit (10 automated checks)
python scripts/security_audit.py

# Privacy check (pre-commit hook, also runnable standalone)
python scripts/privacy_check.py --all

# Trigger advisory (shows which agents to run for changed files)
python scripts/trigger_check.py

# Quick diagnostic (checks every silo: node, tunnel, API, cache, DB, git)
bash scripts/diagnose.sh

# Diagnose single silo
bash scripts/diagnose.sh --silo node
bash scripts/diagnose.sh --silo api,db

# Machine-readable diagnostic (for scripts/monitoring)
bash scripts/diagnose.sh --json

# With deep health (circuit breaker, uptime, cache stats)
ADMIN_API_KEY=<key> bash scripts/diagnose.sh
```

### Version Management

```bash
# Show current version state
bash scripts/release.sh status

# List all tagged releases
bash scripts/release.sh list

# Tag current HEAD as release (reads version from pyproject.toml)
bash scripts/release.sh tag

# Show what changed since a version
bash scripts/release.sh diff v0.3.2

# Safely revert to a tagged version (creates backup branch first)
bash scripts/release.sh revert v0.3.2
```

### Automated Monitoring

```bash
# Watchdog — auto-restarts dead/zombie API (runs every 5 min via Task Scheduler)
# Detects: port not listening, health check failure, zombie process
# Logs to: logs/watchdog.log (auto-trims at 10K lines)
bash scripts/watchdog-api.sh

# Smoke test — 5-point external health check (cron-friendly)
# Checks: /health, /fees/recommended, /docs, /openapi.json, /redoc
bash scripts/smoke-test-api.sh          # verbose output
bash scripts/smoke-test-api.sh --quiet  # only logs failures (for cron)

# Pre-deploy staging — starts temp server on :9333, runs 8 validation checks
# Checks: health, security headers, CSP, fees endpoint, docs (no CSP), redoc, openapi.json, landing page
bash scripts/staging-check.sh
```

---

## 11. Interactive API Guide

The `/api/v1/guide` endpoint returns curated code examples and use-case walkthroughs. No auth required.

```bash
# Full guide (all use cases, default language)
curl https://bitcoinsapi.com/api/v1/guide

# Filter by use case and language
curl "https://bitcoinsapi.com/api/v1/guide?use_case=fees&lang=python"
curl "https://bitcoinsapi.com/api/v1/guide?use_case=transactions&lang=curl"
```

---

## 12. Agent Employees (12 Agents — Claude Code Skills)

The project has 12 specialized agents (flat org, all report to CEO) you can run as slash commands:

| Command | Role | What it does |
|---------|------|-------------|
| `/pm-review` | Product Manager | Feature strategy, competitive gaps, pricing, 90-day roadmap |
| `/ux-review` | UX/Design Lead | Customer journey, landing page, registration flow, docs UX, error messages |
| `/finance-review` | CFO | Cost analysis, unit economics, revenue projections |
| `/legal-review` | Legal | Checks ToS, privacy policy, disclaimers against actual code behavior |
| `/marketing-sync` | Marketing | Fixes stale endpoint counts, license refs, test counts across all marketing files |
| `/security-review` | Security | Audits security headers, auth, rate limits, CSP, secrets |
| `/architecture-review` | Architect | SCOPE_OF_WORK currency, CLAUDE.md, code quality, module coupling |
| `/qa-review` | QA Lead | Test coverage, test-to-SOW sync, regression scanning |
| `/analytics-review` | Analytics | Audits data collection, logging, analytics endpoints |
| `/agent-advocate` | Agent/Token Advocate | Agent consumer experience, token efficiency, response design, MCP compatibility |
| `/ops-review` | Chief of Staff | Data lifecycle, metrics, process automation, standards, org maintenance |
| `/admin-assistant` | Admin Assistant | Endpoint count stamping, doc consistency, guide catalog sync, cross-file reference audits |
| `/all-hands` | Orchestrator | Runs ALL 12 agents, consolidated dashboard, conflict detection, CEO action items |

**Deprecated wrappers** (backward compat — run successor agents):
| `/code-review` | → `/qa-review` + `/architecture-review` |
| `/product-review` | → `/pm-review` + `/ux-review` |

After any code change, Claude will check the trigger matrix in `docs/AGENT_ROLES.md` to see which agents should run. See that file for the full trigger matrix, cross-reference table, conflict resolution protocol, and performance tracking.

---

## 13. Building & Publishing

### Build the PyPI package locally
```bash
cd ~/Bortlesboat/bitcoin-api
python -m build
```
Creates `dist/satoshi_api-X.Y.Z.tar.gz` and `.whl`.

### Publish to PyPI (automated)
1. Go to github.com/Bortlesboat/bitcoin-api/releases/new
2. Create a tag like `v0.3.2`
3. GitHub Actions `.github/workflows/publish.yml` auto-publishes to PyPI

### Manual publish (if needed)
```bash
python -m twine upload dist/satoshi_api-*.whl dist/satoshi_api-*.tar.gz
```

---

## 14. Domain & HTTPS (Cloudflare)

- **Domain:** bitcoinsapi.com (Cloudflare Registrar)
- **Tunnel:** `cloudflared` runs via Registry Run key (`HKCU\...\Run\CloudflaredTunnel`) as user, routes `bitcoinsapi.com` -> `localhost:9332`
- **All three services auto-start on logon:** Bitcoin Knots (Registry Run), cloudflared tunnel (Registry Run), API (Scheduled Task)
- **If the site goes down but API is running locally:** check `cloudflared tunnel info satoshi-api` for active connections. The old Windows service (`sc query cloudflared`) is broken — ignore it.
- **If API returns 502:** Bitcoin Knots is not running. Check `netstat -ano | grep 8332`. The API will serve stale cached data for most endpoints until the node comes back.

### Cloudflare Dashboard locations
- **DNS:** dash.cloudflare.com -> bitcoinsapi.com -> DNS
- **Tunnel:** dash.cloudflare.com -> Zero Trust -> Tunnels
- **Web Analytics:** dash.cloudflare.com -> Analytics & Logs -> Web Analytics

### Cloudflare Analytics — REVISED (2026-03-07)
The manual JS beacon (`beacon.min.js`) was **removed** from all HTML pages (Sprint 25 — replaced by PostHog). Only the automatic RUM setup (Speed > RUM) remains active. Cloudflare auto-injects at the edge for performance metrics (load time, TTFB). PostHog handles page-level analytics.

---

## 15. Backups & Log Rotation

### Database Backups

Run `scripts/backup-db.sh` to create a WAL-safe backup of `data/satoshi_api.db`:

```bash
bash scripts/backup-db.sh
```

- Uses `sqlite3 .backup` (WAL-safe), falls back to `cp`
- Stores backups in `data/backups/`, retains last 7
- **Scheduled daily** via Windows Task Scheduler (`SatoshiAPIBackup`, 3:00 AM)

### Disaster Recovery

1. Stop the API: `taskkill /F /IM python.exe` (or let watchdog handle restart)
2. Restore: `cp data/backups/satoshi_api_YYYYMMDD_HHMMSS.db data/satoshi_api.db`
3. Restart: `bash scripts/deploy-api.sh` or wait for watchdog (5 min)

### Log Rotation

- **watchdog.log**: Auto-trimmed at 10,000 lines (down to 5,000) by watchdog script
- **api.log**: Auto-trimmed at 50,000 lines (down to 25,000) by watchdog script
- Both run every 5 minutes when the watchdog Task Scheduler entry is active

### Data Retention

| Data | Retention | Mechanism |
|------|-----------|-----------|
| Usage logs | 90 days | Auto-pruned by background job |
| Fee history | 30 days | Auto-pruned by background job |
| x402 payment records | 180 days | Auto-pruned at startup |
| DB backups | Last 7 | Auto-pruned by backup script |
| Watchdog log | ~5,000 lines | Auto-trimmed by watchdog |
| API log | ~25,000 lines | Auto-trimmed by watchdog |

## 16. Pending Setup (Manual Browser Actions)

### Bing Webmaster Tools — DONE (2026-03-07)
Verified via HTML meta tag (`06E6BDEDE1F4866F7945A8918FBBFACA`). Sitemap submitted: `https://bitcoinsapi.com/sitemap.xml`. Token is in `static/index.html`.

### GitHub Social Preview
1. Go to github.com/Bortlesboat/bitcoin-api/settings
2. Scroll to "Social Preview"
3. Upload `static/social-preview.png`

---

## 17. File Map

| Location | What's there |
|----------|-------------|
| `src/bitcoin_api/` | All source code (17 modules + 22 router files (21 REST + mcp_server sub-app) + 3 indexer routers + 6 services) |
| `tests/` | Unit tests, e2e tests, load test, helpers |
| `static/` | Landing page, SEO pages, utility/tool pages, legal pages, robots/sitemap |
| `docs/` | SOW, self-hosting guide, marketing, legal |
| `scripts/` | API key creation, SEO metrics, security checks |
| `data/` | SQLite databases (auto-created, gitignored) |
| `.env` | Your local config (gitignored, never committed) |
| `.env.example` | Template showing all available settings |
| `CHANGELOG.md` | Version history |
| `CLAUDE.md` | Instructions for AI-assisted development |
