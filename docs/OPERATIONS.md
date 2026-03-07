# Satoshi API -- Operations Guide

Everything you need to run, maintain, and market Satoshi API. This is the "how do I..." doc.

---

## Quick Reference

| What | How |
|------|-----|
| **API is running at** | `http://localhost:9332` (local) / `https://bitcoinsapi.com` (public) |
| **Interactive docs** | `http://localhost:9332/docs` |
| **Process** | `python -m uvicorn bitcoin_api.main:app --host 0.0.0.0 --port 9332` |
| **Config** | `.env` in repo root (loaded automatically by Pydantic Settings) |
| **Database** | `data/bitcoin_api.db` (SQLite, auto-created) |
| **Auto-start** | Windows Scheduled Task "SatoshiAPI" runs on logon |
| **HTTPS** | Cloudflare Tunnel (`cloudflared` Windows service) routes bitcoinsapi.com -> localhost:9332 |
| **Monitoring** | UptimeRobot checks `/api/v1/health` every 5 min |

---

## 1. Starting / Stopping / Restarting the API

### Start (if not running)
```bash
cd ~/Bortlesboat/bitcoin-api
python -m uvicorn bitcoin_api.main:app --host 0.0.0.0 --port 9332 &
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
# Replace XXXXX with the actual PID from above
taskkill.exe //PID XXXXX //F
sleep 1
cd ~/Bortlesboat/bitcoin-api
python -m uvicorn bitcoin_api.main:app --host 0.0.0.0 --port 9332 &
```
Downtime: ~2 seconds. Cloudflare will show a 502 briefly.

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
- `RATE_LIMIT_ANONYMOUS=30` -- requests/min for anonymous users
- `RATE_LIMIT_FREE=100` -- requests/min for free API key users
- `RATE_LIMIT_PRO=500` -- requests/min for pro users
- `ADMIN_API_KEY` -- key for admin analytics endpoints
- `ENABLE_PRICES_ROUTER=true` -- toggle CoinGecko price endpoint
- `ENABLE_ADDRESS_ROUTER=true` -- toggle address lookup endpoints
- `ENABLE_EXCHANGE_COMPARE=true` -- toggle exchange comparison endpoint

---

## 3. Analytics Dashboard (Admin Only)

Six endpoints that show how people use your API. All require the admin key header.

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
```

Replace `YOUR_KEY` with the value from your `.env` `ADMIN_API_KEY`.

### Where is the admin key?
In `~/Bortlesboat/bitcoin-api/.env`, the `ADMIN_API_KEY` line.

---

## 4. API Keys (for users)

### Create a new API key
```bash
cd ~/Bortlesboat/bitcoin-api
python scripts/create_api_key.py
```
This generates a key and stores its SHA256 hash in the database.

### How users self-register
Users can POST to `/api/v1/register` with `agreed_to_terms: true` to get a free API key. No admin action needed.

---

## 5. SEO & Marketing Toolkit

### Run SEO metrics check
```bash
cd ~/Bortlesboat/bitcoin-api
python scripts/seo_metrics.py
```
Shows: page accessibility (all 10 pages), GitHub stars, PyPI downloads, PR merge status, Bing indexing, search mentions, API usage stats. Saves data to `data/seo_metrics.db`.

### Marketing drafts location
All ready-to-post drafts are in `docs/marketing/drafts/`:
- `reddit-bitcoindev.md` -- r/BitcoinDev (question format, post first)
- `reddit-selfhosted.md` -- r/selfhosted
- `reddit-bitcoin.md` -- r/Bitcoin
- `reddit-python.md` -- r/Python
- `hackernews-show-hn.md` -- Hacker News Show HN
- `stacker-news.md` -- Stacker News

### Keeping marketing materials accurate
When endpoints, tests, or features change, run:
```
/marketing-sync
```
This Claude Code skill audits all marketing files against the actual codebase and fixes stale facts.

### Other marketing files
- `docs/marketing/launch-plan.md` -- Master tracker (what's posted, what's pending)
- `docs/marketing/distribution-channels.md` -- Full channel strategy
- `docs/marketing/brand-strategy.md` -- Voice, positioning, visual identity
- `docs/marketing/umbrel-submission-guide.md` -- App store submission guide

---

## 6. Running Tests

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

# Security audit (8 automated checks)
python scripts/security_audit.py
```

---

## 7. Agent Employees (Claude Code Skills)

The project has specialized agents you can run as slash commands:

| Command | What it does |
|---------|-------------|
| `/code-review` | Runs tests, checks code quality, verifies SCOPE_OF_WORK is current |
| `/marketing-sync` | Fixes stale endpoint counts, license refs, test counts across all marketing files |
| `/security-review` | Audits security headers, auth, rate limits, CSP, secrets |
| `/legal-review` | Checks ToS, privacy policy, disclaimers against actual code behavior |
| `/analytics-review` | Audits data collection, logging, analytics endpoints |
| `/product-review` | Product vision, customer journey, pricing, competitive positioning |
| `/finance-review` | Cost analysis, unit economics, revenue projections |
| `/architecture-review` | SCOPE_OF_WORK currency, module coupling, architecture |
| `/qa-review` | Test coverage, test-to-SOW sync, regression scanning |
| `/ux-review` | Landing page, registration flow, docs UX, error messages |
| `/all-hands` | Runs ALL agents, produces consolidated dashboard |

After any code change, Claude will check the trigger matrix in `docs/AGENT_ROLES.md` to see which agents should run.

---

## 8. Building & Publishing

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

## 9. Domain & HTTPS (Cloudflare)

- **Domain:** bitcoinsapi.com (Cloudflare Registrar)
- **Tunnel:** `cloudflared` Windows service routes `bitcoinsapi.com` -> `localhost:9332`
- **The tunnel auto-starts** with Windows (runs as a service)
- **If the site goes down but API is running locally**, check: `sc query cloudflared` in PowerShell

### Cloudflare Dashboard locations
- **DNS:** dash.cloudflare.com -> bitcoinsapi.com -> DNS
- **Tunnel:** dash.cloudflare.com -> Zero Trust -> Tunnels
- **Analytics (pending):** dash.cloudflare.com -> Analytics & Logs -> Web Analytics

---

## 10. Pending Setup (Manual Browser Actions)

### Cloudflare Web Analytics
1. Go to dash.cloudflare.com -> Analytics & Logs -> Web Analytics
2. Click "Add a site" -> enter `bitcoinsapi.com`
3. Copy the token
4. Tell Claude: "replace REPLACE_WITH_CF_TOKEN in all HTML files with [your token]"

### Bing Webmaster Tools
1. Go to bing.com/webmasters
2. Add site: `bitcoinsapi.com`
3. Choose "HTML Meta Tag" verification
4. Copy the content value from the meta tag
5. Tell Claude: "replace REPLACE_WITH_BING_TOKEN in index.html with [your token]"
6. After verification, submit sitemap: `https://bitcoinsapi.com/sitemap.xml`

### GitHub Social Preview
1. Go to github.com/Bortlesboat/bitcoin-api/settings
2. Scroll to "Social Preview"
3. Upload `static/social-preview.png`

---

## 11. File Map

| Location | What's there |
|----------|-------------|
| `src/bitcoin_api/` | All source code (13 modules + 14 routers) |
| `tests/` | Unit tests, e2e tests, load test, helpers |
| `static/` | Landing page, SEO pages, legal pages, robots/sitemap |
| `docs/` | SOW, self-hosting guide, marketing, legal |
| `scripts/` | API key creation, SEO metrics, security checks |
| `data/` | SQLite databases (auto-created, gitignored) |
| `.env` | Your local config (gitignored, never committed) |
| `.env.example` | Template showing all available settings |
| `CHANGELOG.md` | Version history |
| `CLAUDE.md` | Instructions for AI-assisted development |
