# Satoshi API -- Scope of Work

**Version:** 0.1.0
**Date:** 2026-03-06
**Author:** Andy Barnes
**Status:** In Progress -- Security Hardening & Production Deployment

---

## 1. Project Overview

**Satoshi API** is a developer-friendly REST API that wraps a Bitcoin Core node with analyzed, structured data. It sits in a three-layer stack: **bitcoinlib-rpc** (Python RPC client) -> **Satoshi API** (REST layer) -> **bitcoin-mcp** (AI agent interface).

**Target users:** Developers building Bitcoin applications, AI agents querying blockchain data, hobbyist node operators wanting a clean API.

**Value proposition:** One `pip install`, instant REST API over your Bitcoin node. Analyzed data (fee recommendations, mempool congestion scores, block analysis) rather than raw RPC dumps.

---

## 2. Architecture

### 2.1 System Diagram

```
Internet
    |
Cloudflare (HTTPS, DDoS protection, IP hiding)
    |
cloudflared tunnel (localhost relay)
    |
Satoshi API (FastAPI, port 9332)
    |-- Auth middleware (API key via X-API-Key header)
    |-- Rate limiter (sliding window per-minute + daily DB-backed)
    |-- TTL cache (reorg-safe, per-cache locks)
    |-- Structured access logging
    |
Bitcoin Core RPC (port 8332, localhost only)
    |-- rpcwhitelist restricts to 16 safe commands
    |-- txindex=1 for full transaction lookups
```

### 2.2 Component Responsibilities

| Component | Responsibility | Design Pattern |
|-----------|---------------|----------------|
| `main.py` | App lifecycle, middleware stack, exception handlers | Middleware chain |
| `auth.py` | API key validation, tier resolution | Strategy (tier-based) |
| `rate_limit.py` | Per-minute sliding window + daily limits | Token bucket / sliding window |
| `cache.py` | TTL caching with reorg-safe depth awareness | Cache-aside with lock-per-cache |
| `db.py` | SQLite (WAL mode), usage logging, key storage | Repository pattern |
| `config.py` | 12-factor env var config via Pydantic | Settings singleton |
| `dependencies.py` | Lazy singleton RPC connection | Dependency injection |
| `models.py` | Response envelope, typed data models | DTO / envelope pattern |
| `routers/` | 7 domain routers (blocks, tx, fees, mempool, mining, network, status) | RESTful resource routing |

### 2.3 Design Principles Applied

- **Single Responsibility:** Each module owns one concern. Routers don't touch DB. Cache doesn't know about HTTP.
- **Dependency Inversion:** Routers depend on `get_rpc()` abstraction, not concrete RPC. Testable via DI override.
- **Open/Closed:** New endpoints = new router file. No modification of middleware needed.
- **12-Factor App:** Config from env vars, stateless processes, explicit dependencies, dev/prod parity.
- **Defense in Depth:** Auth -> rate limit -> input validation -> RPC whitelist -> localhost binding.

---

## 3. API Surface

### 3.1 Endpoints (27 total)

| Category | Endpoint | Method | Auth Required |
|----------|----------|--------|---------------|
| **Status** | `/api/v1/health` | GET | No |
| | `/api/v1/status` | GET | No |
| **Blocks** | `/api/v1/blocks/latest` | GET | No |
| | `/api/v1/blocks/tip/height` | GET | No |
| | `/api/v1/blocks/tip/hash` | GET | No |
| | `/api/v1/blocks/{height_or_hash}` | GET | No |
| | `/api/v1/blocks/{height}/stats` | GET | No |
| | `/api/v1/blocks/{hash}/txids` | GET | No |
| | `/api/v1/blocks/{hash}/txs` | GET | No |
| **Transactions** | `/api/v1/tx/{txid}` | GET | No |
| | `/api/v1/tx/{txid}/raw` | GET | No |
| | `/api/v1/tx/{txid}/status` | GET | No |
| | `/api/v1/utxo/{txid}/{vout}` | GET | No |
| | `/api/v1/decode` | POST | Yes (free+) |
| | `/api/v1/broadcast` | POST | Yes (free+) |
| **Fees** | `/api/v1/fees` | GET | No |
| | `/api/v1/fees/recommended` | GET | No |
| | `/api/v1/fees/{target}` | GET | No |
| **Mempool** | `/api/v1/mempool` | GET | No |
| | `/api/v1/mempool/info` | GET | No |
| | `/api/v1/mempool/tx/{txid}` | GET | No |
| | `/api/v1/mempool/txids` | GET | No |
| | `/api/v1/mempool/recent` | GET | No |
| **Mining** | `/api/v1/mining` | GET | No |
| | `/api/v1/mining/nextblock` | GET | No |
| **Network** | `/api/v1/network` | GET | No (redacted) |
| | `/api/v1/network/forks` | GET | No |
| | `/api/v1/network/difficulty` | GET | No |

### 3.2 Rate Limits

| Tier | Per Minute | Per Day | POST Access |
|------|-----------|---------|-------------|
| Anonymous | 30 | 1,000 | No |
| Free | 100 | 10,000 | Yes |
| Pro | 500 | 100,000 | Yes |
| Enterprise | 2,000 | Unlimited | Yes |

### 3.3 Response Format

All responses use a standard envelope:

```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2026-03-06T12:00:00+00:00",
    "request_id": "uuid",
    "node_height": 939462,
    "chain": "main"
  }
}
```

Errors follow the same structure:

```json
{
  "error": {
    "status": 404,
    "title": "Not Found",
    "detail": "Transaction not found",
    "request_id": "uuid"
  }
}
```

---

## 4. Security Model

### 4.1 Implemented Controls

| Layer | Control | Implementation |
|-------|---------|----------------|
| **Transport** | HTTPS via Cloudflare Tunnel | TLS termination at edge, no home IP exposed |
| **Authentication** | API key (SHA256 hashed) | X-API-Key header, deprecated query param with sunset |
| **Authorization** | Tier-based access | Anonymous: read-only. Free+: POST endpoints |
| **Rate Limiting** | Per-minute + daily | Sliding window (memory) + DB-backed daily counts |
| **Input Validation** | Regex + Pydantic | 64-hex txid, non-negative heights, hex-only bodies |
| **Body Size** | 2MB limit | Pydantic `Field(max_length=2_000_000)` on hex inputs |
| **Node Protection** | RPC whitelist | Only 17 safe commands allowed via `rpcwhitelist` |
| **Network** | Localhost-only RPC | `rpcbind=127.0.0.1`, `rpcallowip=127.0.0.1` |
| **Information Hiding** | Version redaction | Node version/subversion hidden from anonymous users |
| **Secrets** | SecretStr for RPC password | Pydantic SecretStr prevents accidental logging |
| **Access Logging** | Structured logs | IP, method, path, status, tier, request_id |
| **CORS** | Allowlist-based | Configured origins, not wildcard in production |

### 4.2 Threat Model

| Threat | Mitigation | Residual Risk |
|--------|------------|---------------|
| DDoS | Cloudflare + rate limiting | Low -- Cloudflare absorbs L3/L4 |
| Broadcast spam | API key required for POST | Low -- free key = auditable |
| Node fingerprinting | Version redaction for anon | Low -- authenticated users see it |
| RPC command injection | Whitelist + parameterized calls | Very low |
| SQL injection | Parameterized SQLite queries | Very low |
| API key theft | SHA256 hashing, no plaintext storage, no keys in scripts | Medium -- rotate on compromise |
| Database leak | Keys are hashed, not reversible | Low |

---

## 5. Production Architecture Review

### 5.1 Grades by Principle

| Principle | Grade | Key Finding |
|-----------|-------|-------------|
| SOLID | B | Clean SRP, good DI. Rate limit strategies could use protocol abstraction. |
| Separation of Concerns | A- | Layers are clean. Minor: middleware does both auth + rate limit + logging. |
| Error Handling | B+ | Comprehensive handlers. Fixed: now logs exceptions server-side. |
| Security | B+ | Defense in depth. Fixed: SecretStr for passwords, body limits in Docker. |
| Scalability | B | Thread-safe caching + rate limiting. SQLite is bottleneck at >1K req/s. |
| Observability | B- | Access logs + request IDs. Missing: Prometheus metrics. |
| Configuration | A- | 12-factor compliant. Sensible defaults. |
| Testing | B+ | 59 unit tests + e2e + load test + security script. |
| Dependencies | A- | Minimal, intentional. Could pin tighter. |
| API Design | A- | Versioned, enveloped, deprecation headers. No idempotency keys yet. |
| Data Integrity | B | WAL mode, parameterized queries. No schema migrations framework. |
| Deployment | B+ | Non-root Docker, health checks. Fixed: graceful shutdown. |

### 5.2 Critical Issues Fixed

**Sprint 6:**
1. **Exception swallowing** -- Middleware now logs full tracebacks via `logger.exception()`
2. **Secret leakage risk** -- RPC password changed to Pydantic `SecretStr`
3. **No graceful shutdown** -- Added 30s timeout to CLI and Dockerfile
4. **Unbounded memory** -- `_hash_to_height` dict replaced with `LRUCache(maxsize=256)`
5. **E2E test assertion bug** -- Fixed `"healthy"` -> `"ok"` to match actual status
6. **Missing `request.state.tier`** -- Middleware now sets tier for downstream handlers

**Sprint 7 (Architecture Review):**
7. **RPC singleton never recovers** -- Added `reset_rpc()` called on `ConnectionError` to allow reconnection
8. **POST 403 missing request_id** -- Changed from inline `JSONResponse` to `raise HTTPException`, uses standard error handler
9. **Prod healthcheck uses curl** -- Docker compose prod healthcheck now uses Python urllib (matches Dockerfile)
10. **Duplicate fee field** -- Removed `fee_sat`, kept `fee_sats` (Bitcoin convention)
11. **Rate limit header wrong epoch** -- Changed `time.monotonic()` to `time.time()` for correct unix timestamps
12. **Data leak via extra=allow** -- Changed to `extra="ignore"` on response models
13. **CORS wildcard warning** -- Log WARNING at startup if `*` in origins
14. **Block/mempool null fields** -- Fixed field name mapping: `fee_rate_median`→`median_fee_rate`, `total_fee_btc`→`total_fee`, `total_bytes`→`bytes`, `buckets`→`fee_buckets`
15. **Block hash cache miss** -- `cached_block_by_hash` now checks both `_block_cache` and `_recent_block_cache`
16. **E2E fee test no-op** -- Test checked for "high"/"medium"/"low" keys that don't exist; now validates actual integer-keyed estimates
17. **Dockerfile invalid flag** -- Removed `--limit-max-request-size` (not a valid uvicorn CLI/API param); body limits enforced by Pydantic model validation

**Post-launch (Mar 6):**
18. **Hardcoded API key in security_check.sh** -- Flagged by GitGuardian. Replaced with `$SATOSHI_API_KEY` env var. Exposed key deactivated, new key generated. Committed key is in git history but was for local use only (no third-party exposure).

### 5.3 Known Limitations (Acceptable for v0.1)

| Limitation | Impact | When to Address |
|------------|--------|-----------------|
| SQLite write bottleneck | >1K req/s will see contention | v0.2 -- batch writes or PostgreSQL |
| No Prometheus metrics | Can't monitor cache hit rates, latency | v0.2 -- add `/metrics` endpoint |
| No idempotency keys | POST retries could double-broadcast | v0.2 -- add `Idempotency-Key` header |
| No schema migrations | Manual ALTER TABLE for DB changes | v0.2 -- add Alembic |
| Daily limit COUNT(*) | O(n) per request at scale | v0.2 -- cache count in memory |
| No webhook support | Clients must poll | v0.3 -- WebSocket/webhook subscriptions |

---

## 6. Deliverables

### 6.1 Completed (Sprints 1-6)

| Sprint | Deliverable | Tests |
|--------|-------------|-------|
| 1 | Core API: health, blocks, transactions, fees, mempool | 15 |
| 2 | Rate limiting (per-minute + daily), API key auth | 8 |
| 3 | Caching (TTL, reorg-safe), mining endpoints, network | 10 |
| 4 | Input validation, error unification, deprecation headers | 12 |
| 5 | Thread safety, usage logging, Docker, CI | 10 |
| 6 | Security hardening, production deployment, docs | 4 |
| 7 | Architecture review: 11 fixes (3 critical, 4 high, 4 medium) | 0 |
| 8 | v0.2 endpoints: mempool txids/recent, block txids/txs, tip height/hash, tx status, difficulty | 12 |
| **Total** | **27 endpoints, 7 routers** | **71 unit + 9 e2e** |

### 6.2 Files Delivered

**Source (11 files):**
- `src/bitcoin_api/` -- main, auth, cache, config, db, dependencies, models, rate_limit
- `src/bitcoin_api/routers/` -- blocks, fees, mempool, mining, network, status, transactions

**Tests (3 files):**
- `tests/test_api.py` -- 59 unit tests
- `tests/test_e2e.py` -- 9 e2e tests (against live node)
- `tests/locustfile.py` -- Load test (8 weighted endpoints)

**Deployment (6 files):**
- `Dockerfile`, `docker-compose.yml`, `docker-compose.prod.yml`
- `.env.example`, `.env.production.example`
- `cloudflared-config.yml.example`

**Documentation (5 files):**
- `README.md`, `CHANGELOG.md`, `blog-post.md`
- `docs/self-hosting.md`, `docs/bitcoin-conf-example.conf`

**CI/CD (3 files):**
- `.github/workflows/ci.yml` -- Tests + lint on push
- `.github/workflows/publish.yml` -- PyPI publish on release
- `.github/workflows/pages.yml` -- GitHub Pages deployment for landing page

**Project config (1 file):**
- `CLAUDE.md` -- Project instructions for AI-assisted development

**Scripts (3 files):**
- `scripts/create_api_key.py`, `scripts/seed_db.py`
- `scripts/security_check.sh` (requires `SATOSHI_API_KEY` env var for POST tests)

**Website (1 file):**
- `docs/website/index.html` -- Landing page with product info, use cases, endpoints, pricing, comparison table

---

## 7. Deployment Plan

### 7.1 Infrastructure

| Component | Provider | Cost |
|-----------|----------|------|
| Bitcoin Core node | Main PC (existing) | $0 |
| Satoshi API | Main PC Docker | $0 |
| Domain | Cloudflare Registrar | ~$10/yr |
| HTTPS + DDoS | Cloudflare Tunnel (free) | $0 |
| Monitoring | UptimeRobot (free tier) | $0 |

### 7.2 Deployment Steps

1. Buy domain, add to Cloudflare
2. Install `cloudflared`, create tunnel
3. Configure Bitcoin Core with `rpcwhitelist` (see `docs/bitcoin-conf-example.conf`)
4. `docker compose -f docker-compose.prod.yml up -d`
5. Configure `cloudflared` tunnel to `localhost:9332`
6. Set up UptimeRobot on `https://api.domain.dev/healthz`
7. Create initial API keys via `scripts/create_api_key.py`

### 7.3 Go-Live Checklist

- [x] All 59 unit tests pass
- [x] Security check script passes all 9 checks
- [x] E2E tests pass against live node
- [x] Load test: 50 users, 0 errors, p95 < 500ms (4ms median)
- [x] Quick tunnel HTTPS verified via Cloudflare
- [ ] Permanent domain + named Cloudflare Tunnel
- [x] Anonymous POST /broadcast returns 403
- [x] Anonymous GET /network redacts version
- [ ] UptimeRobot confirms /healthz reachable
- [x] API key created for personal use
- [x] Bitcoin Core RPC whitelist configured (17 commands)

---

## 8. Product Strategy & Pricing

### 8.1 What We're Selling

Satoshi API serves three strategic purposes:

1. **Open source product** -- `pip install bitcoin-api` is the fastest path from a Bitcoin node to a REST API. Value = convenience + developer experience.
2. **Portfolio/credibility piece** -- Demonstrates Bitcoin protocol + Python + production engineering competence. Signals to Upwork clients, employers, and the Bitcoin dev community.
3. **Consulting funnel** -- "I built this, I can build custom Bitcoin tooling for you." Leads to paid work.

A hosted API is a secondary revenue opportunity, not the primary business.

### 8.2 Target Users

| User Segment | What They Need | Revenue Potential |
|-------------|---------------|-------------------|
| Node operators wanting a clean API | `pip install`, done | Free (self-host) |
| Wallet/app devs in prototype stage | Quick API, avoid running a node | $0-20/mo |
| AI agent builders (MCP users) | Bitcoin data for Claude/GPT | Free (use MCP layer) |
| Companies needing uptime + SLA | Hosted, dedicated, compliant | $50-500/mo |
| Upwork/freelance clients | Custom Bitcoin tooling | Hourly rate |

### 8.3 Pricing Model

| Tier | Price | Limits | Target |
|------|-------|--------|--------|
| Open Source | Free forever | Self-hosted, unlimited | Node runners |
| Free (Hosted) | $0/mo | 1,000 req/day, 30/min, read-only | Devs trying it out |
| Builder | $9/mo | 10,000 req/day, 100/min, POST | Side projects |
| Pro | $29/mo | 100,000 req/day, 500/min, priority | Small apps |
| Enterprise | Custom | Unlimited, SLA, dedicated | Contact |

**Launch strategy:** Free + open source only. Add paid tiers when demand materializes. Don't build Stripe integration for zero customers.

### 8.4 Infrastructure Cost

| Item | Monthly Cost |
|------|-------------|
| Electricity (marginal ~15-20W over always-on PC) | $2 |
| Domain (.dev) | $1 |
| Cloudflare Tunnel | $0 |
| Internet (already have) | $0 |
| **Total operating cost** | **~$3/month** |

One-time: 2TB SSD ~$150-200 (already have).

**Break-even:** 1 customer at $9/mo.

### 8.5 Competitive Landscape

| Competitor | Free Tier | Paid Entry | Self-Hostable | Differentiator |
|-----------|-----------|------------|---------------|----------------|
| mempool.space | Yes (undocumented limits) | Enterprise (call sales) | Yes (Docker) | De facto standard explorer |
| Blockstream Esplora | Yes (~50 rps) | N/A (free) | Yes | Most complete open-source REST API |
| BlockCypher | 1K req/day | $100/mo | No | Payment forwarding, multi-chain |
| GetBlock | 50K CU/day | $49/mo | No | 50+ chains |
| QuickNode | 10M credits | $49/mo | No | Best DX, 25+ chains |
| Alchemy | 30M CU | $5/mo PAYG | No | Dominant in EVM |
| **Satoshi API** | **Unlimited (self-host)** | **$0 (free hosted)** | **Yes** | **Analyzed data, MCP/AI-ready, pip install** |

**Our edge:** Nobody else offers analyzed Bitcoin data (fee recommendations, congestion scores, block analysis) + AI agent integration (MCP) + one-line install. We're not competing on hosted infrastructure -- we're competing on developer experience for the self-hosted niche.

### 8.6 Growth Opportunities (from ChatGPT analysis)

Highest-potential adjacencies if the product gains traction:
1. **Smart fee estimation API** -- probability-based confirmation estimates (largest market)
2. **Transaction monitoring** -- webhook-based tx/address watching (lowest difficulty)
3. **Mempool intelligence** -- real-time congestion maps, miner template prediction
4. **Ordinals API** -- inscription indexing, sat tracking (aligns with prior experience)

These would be v1.0+ features, not v0.1 scope.

---

## 9. Distribution Plan

### 9.1 Launch Channels

| Channel | Content | Priority |
|---------|---------|----------|
| Hacker News | "Show HN: Satoshi API -- REST API for your Bitcoin node" | Primary |
| dev.to | Full blog post (architecture deep dive) | High |
| r/BitcoinDev | Technical announcement | High |
| r/Bitcoin | Brief announcement | Medium |
| Nostr | Thread with examples | Medium |
| PyPI | `pip install bitcoin-api` | High |
| MCP directories | modelcontextprotocol/servers PR, Smithery, MCP Hub | Medium |

### 9.2 PyPI Publishing

```bash
# Build
python -m build

# Upload (or use GitHub Actions publish workflow on release)
twine upload dist/*
```

---

## 10. Future Roadmap

### v0.2 (Feature Parity — COMPLETE)
- Mempool: `/mempool/txids`, `/mempool/recent`
- Blocks: `/blocks/tip/height`, `/blocks/tip/hash`, `/blocks/{hash}/txids`, `/blocks/{hash}/txs`
- Transactions: `/tx/{txid}/status`
- Network: `/network/difficulty`
- RPC whitelist: added `getrawmempool`

### v0.3 (Medium Effort — Next)
- `GET /fees/mempool-blocks` — projected mempool blocks (simulate block filling)
- `GET /tx/{txid}/outspends` — output spending status
- Historical mempool statistics (background collector + time-series storage)
- `GET /prices` — BTC price (cached from CoinGecko/Coinbase)
- Prometheus `/metrics` endpoint
- Idempotency key support for POST

### v0.4 (Real-Time + Infrastructure)
- WebSocket endpoint for mempool fee updates
- Webhook subscriptions for new blocks
- Server-Sent Events for chain tip changes
- Alembic schema migrations
- Batch usage log writes

### v0.5 (Address Lookups — Requires Electrs/Fulcrum)
- `GET /address/{addr}` — address summary
- `GET /address/{addr}/txs` — address transaction history
- `GET /address/{addr}/utxo` — address UTXOs
- PostgreSQL backend option

---

## 11. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Bitcoin Core node goes down | Medium | API returns 502 | UptimeRobot alert, auto-restart via Docker |
| Home power/internet outage | Low | API offline | Cloudflare shows maintenance page |
| RPC password leaked | Low | Node compromise | SecretStr, env-only config, no git commits |
| Rate limit bypass | Low | Resource exhaustion | Cloudflare WAF + application rate limits |
| SQLite corruption | Very Low | API keys lost | WAL mode, periodic backups |
| Dependency vulnerability | Low | Supply chain risk | Minimal deps, pin versions, `pip audit` in CI |

---

*This document is the canonical scope of work for the Satoshi API project. Update it as the project evolves.*
