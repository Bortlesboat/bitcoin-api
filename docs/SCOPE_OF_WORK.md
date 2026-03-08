# Satoshi API -- Scope of Work

**Version:** 0.3.3
**Date:** 2026-03-08
**Author:** Bortlesboat
**Status:** Live -- https://bitcoinsapi.com

---

## 1. Project Overview

**Satoshi API** is a Bitcoin fee intelligence service that tells you when to send, what to pay, and whether to wait — saving money on every transaction. It sits in a three-layer stack: **bitcoinlib-rpc** (Python RPC client) -> **Satoshi API** (REST layer) -> **bitcoin-mcp** (AI agent interface).

**Target users:** Anyone sending Bitcoin who wants to stop overpaying fees. Developers building wallets/payment apps. AI agents that need to check fees and verify payments autonomously.

**Value proposition:** Fee intelligence that saves money (send now vs wait), payment monitoring that saves time (stop watching block explorers), and AI agent integration that saves developer effort (MCP support on Anthropic Registry). One `pip install`, self-hostable, open source.

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
    |-- Optional: Upstash Redis (persistent rate limit state)
    |-- Optional: Resend (transactional email on registration)
    |-- Optional: PostHog (landing page + registration analytics)
    |-- TTL cache (reorg-safe, per-cache locks)
    |-- Structured access logging
    |
Bitcoin Core RPC (port 8332, localhost only)
    |-- rpcwhitelist restricts to 21 safe commands
    |-- txindex=1 for full transaction lookups
```

### 2.2 Component Responsibilities

| Component | Responsibility | Design Pattern |
|-----------|---------------|----------------|
| `main.py` | App creation, lifespan, router registration (~89 lines) | Composition root |
| `middleware.py` | Security headers, CORS, auth + rate limiting middleware, gzip compression | Middleware chain |
| `exceptions.py` | RPC, validation, HTTP, and generic exception handlers; RFC 7807 `type` URIs | Exception handler registry |
| `jobs.py` | Background fee collector thread lifecycle | Background worker |
| `static_routes.py` | Landing page, robots.txt, sitemap, decision pages | Static file serving |
| `usage_buffer.py` | Batch usage logging (flush at 50 rows or 30s) | Write-behind buffer |
| `migrations/` | SQL migration files + runner, tracked in `schema_migrations` | Sequential migrations |
| `auth.py` | API key validation, tier resolution | Strategy (tier-based) |
| `rate_limit.py` | Per-minute sliding window (in-memory or Upstash Redis) + daily limits | Token bucket / sliding window |
| `notifications.py` | Transactional email (Resend) + analytics events (PostHog) | Fire-and-forget side effects |
| `cache.py` | TTL caching with reorg-safe depth awareness, stale fallback for graceful degradation, `get_cached_node_info()` helper for non-RPC contexts | Cache-aside with lock-per-cache + stale-while-error |
| `db.py` | SQLite (WAL mode), usage logging, key storage | Repository pattern |
| `config.py` | 12-factor env var config via Pydantic | Settings singleton |
| `dependencies.py` | Lazy singleton RPC connection | Dependency injection |
| `models.py` | Response envelope, typed data models | DTO / envelope pattern |
| `services/` | Business logic: fee analysis, tx broadcast, exchange comparison, serializers | Service layer (pure functions) |
| `routers/` | 20 thin HTTP routers — parameter validation, auth, response envelope | RESTful resource routing |

### 2.3 Design Principles Applied

- **Single Responsibility:** Each module owns one concern. Routers are thin HTTP wrappers; business logic lives in `services/`. Cache doesn't know about HTTP.
- **Dependency Inversion:** Routers depend on `get_rpc()` abstraction, not concrete RPC. Testable via DI override.
- **Open/Closed:** New endpoints = new router file. No modification of middleware needed.
- **12-Factor App:** Config from env vars, stateless processes, explicit dependencies, dev/prod parity.
- **Defense in Depth:** Auth -> rate limit -> input validation -> RPC whitelist -> localhost binding.

---

## 3. API Surface

### 3.1 Endpoints (78 total)

| Category | Endpoint | Method | Auth Required |
|----------|----------|--------|---------------|
| **Status** | `/api/v1/health` | GET | No |
| | `/api/v1/health/deep` | GET | Yes (free+) |
| | `/api/v1/status` | GET | No |
| | `/healthz` | GET | No |
| **Blocks** | `/api/v1/blocks/latest` | GET | No |
| | `/api/v1/blocks/tip/height` | GET | No |
| | `/api/v1/blocks/tip/hash` | GET | No |
| | `/api/v1/blocks/{height_or_hash}` | GET | No |
| | `/api/v1/blocks/{height}/stats` | GET | No |
| | `/api/v1/blocks/{hash}/txids` | GET | No |
| | `/api/v1/blocks/{hash}/txs` | GET | No |
| | `/api/v1/blocks/{hash}/header` | GET | No |
| | `/api/v1/blocks/{hash}/raw` | GET | No |
| **Transactions** | `/api/v1/tx/{txid}` | GET | No |
| | `/api/v1/tx/{txid}/raw` | GET | No |
| | `/api/v1/tx/{txid}/hex` | GET | No |
| | `/api/v1/tx/{txid}/status` | GET | No |
| | `/api/v1/tx/{txid}/outspends` | GET | No |
| | `/api/v1/tx/{txid}/merkle-proof` | GET | No |
| | `/api/v1/utxo/{txid}/{vout}` | GET | No |
| | `/api/v1/decode` | POST | Yes (free+) |
| | `/api/v1/broadcast` | POST | Yes (free+) |
| **Fees** | `/api/v1/fees` | GET | No |
| | `/api/v1/fees/recommended` | GET | No |
| | `/api/v1/fees/mempool-blocks` | GET | No |
| | `/api/v1/fees/landscape` | GET | No |
| | `/api/v1/fees/estimate-tx` | GET | No |
| | `/api/v1/fees/history` | GET | No |
| | `/api/v1/fees/{target}` | GET | No |
| **Mempool** | `/api/v1/mempool` | GET | No |
| | `/api/v1/mempool/info` | GET | No |
| | `/api/v1/mempool/tx/{txid}` | GET | No |
| | `/api/v1/mempool/txids` | GET | No |
| | `/api/v1/mempool/recent` | GET | No |
| **Mining** | `/api/v1/mining` | GET | No |
| | `/api/v1/mining/nextblock` | GET | No |
| | `/api/v1/mining/hashrate/history` | GET | No |
| | `/api/v1/mining/revenue` | GET | No |
| | `/api/v1/mining/pools` | GET | No |
| | `/api/v1/mining/difficulty/history` | GET | No |
| | `/api/v1/mining/revenue/history` | GET | No |
| **Network** | `/api/v1/network` | GET | No (redacted) |
| | `/api/v1/network/forks` | GET | No |
| | `/api/v1/network/difficulty` | GET | No |
| | `/api/v1/network/validate-address/{addr}` | GET | No |
| **Prices** | `/api/v1/prices` | GET | No |
| **Address** | `/api/v1/address/{address}` | GET | No |
| | `/api/v1/address/{address}/utxos` | GET | No |
| **Supply** | `/api/v1/supply` | GET | No |
| **Statistics** | `/api/v1/stats/utxo-set` | GET | No |
| | `/api/v1/stats/segwit-adoption` | GET | No |
| | `/api/v1/stats/op-returns` | GET | No |
| **Streams** | `/api/v1/stream/blocks` | GET (SSE) | No |
| | `/api/v1/stream/fees` | GET (SSE) | No |
| | `/api/v1/stream/whale-txs` | GET (SSE) | No |
| **Tools** | `/api/v1/tools/exchange-compare` | GET | No |
| **Keys** | `/api/v1/register` | POST | No |
| **Analytics** | `/api/v1/analytics/public` | GET | No |
| | `/api/v1/analytics/overview` | GET | Admin key |
| | `/api/v1/analytics/requests` | GET | Admin key |
| | `/api/v1/analytics/endpoints` | GET | Admin key |
| | `/api/v1/analytics/errors` | GET | Admin key |
| | `/api/v1/analytics/user-agents` | GET | Admin key |
| | `/api/v1/analytics/latency` | GET | Admin key |
| | `/api/v1/analytics/keys` | GET | Admin key |
| | `/api/v1/analytics/growth` | GET | Admin key |
| | `/api/v1/analytics/slow-endpoints` | GET | Admin key |
| | `/api/v1/analytics/retention` | GET | Admin key |
| | `/api/v1/analytics/client-types` | GET | Admin key |
| | `/api/v1/analytics/mcp-funnel` | GET | Admin key |
| | `/api/v1/analytics/referrers` | GET | Admin key |
| | `/api/v1/analytics/funnel` | GET | Admin key |
| **Guide** | `/api/v1/guide` | GET | No |
| **Metrics** | `/metrics` | GET | No |
| **WebSocket** | `/api/v1/ws` | WS | Yes (free+) |
| **Billing** | `/api/v1/billing/checkout` | POST | Yes (free+) |
| | `/api/v1/billing/webhook` | POST | No (Stripe signature) |
| | `/api/v1/billing/status` | GET | Yes (free+) |
| | `/api/v1/billing/cancel` | POST | Yes (free+) |
| **Admin UI** | `/admin/dashboard` | GET | Admin key (query param) |
| **Indexed** | `/api/v1/indexed/address/{addr}/balance` | GET | Yes (free+) |
| | `/api/v1/indexed/address/{addr}/txs` | GET | Yes (free+) |
| | `/api/v1/indexed/tx/{txid}` | GET | Yes (free+) |
| | `/api/v1/indexed/status` | GET | No |

### 3.2 Endpoint Tiers

Endpoints are grouped into Core (always on) and Extended (toggleable via feature flags):

| Tier | Routers | Feature Flag |
|------|---------|-------------|
| **Core** | status, blocks, transactions, fees, mempool, mining, network, stream, keys, metrics, websocket, billing | Always enabled |
| **Extended** | prices | `ENABLE_PRICES_ROUTER` (default: true) |
| **Extended** | address | `ENABLE_ADDRESS_ROUTER` (default: true) |
| **Extended** | exchanges | `ENABLE_EXCHANGE_COMPARE` (default: true) |
| **Extended** | supply | `ENABLE_SUPPLY_ROUTER` (default: true) |
| **Extended** | stats | `ENABLE_STATS_ROUTER` (default: true) |
| **Indexer** | indexed address, indexed tx, indexer status | `ENABLE_INDEXER` (default: false) |

All flags default to `true` so tests pass unchanged and Swagger `/docs` shows everything. Production `.env` controls what's actually exposed.

### 3.3 Rate Limits

| Tier | Price | Rate Limit | Daily Limit | POST Access |
|------|-------|-----------|-------------|-------------|
| **Self-Hosted** | Free forever | Unlimited | Unlimited | Yes |
| **Hosted (anonymous)** | Free | 30/min | 1,000/day | No |
| **Hosted (API key)** | Free | 100/min | 10,000/day | Yes |
| **Pro** | $19/mo | 500/min | 100,000/day | Yes |

Landing page presents 2 tiers (Self-Hosted + Hosted). Pro is preserved but hidden until demand materializes.

### 3.4 Data Integrity Features

| Feature | Implementation | Details |
|---------|---------------|---------|
| **IBD/Sync Warning** | `Meta.syncing: bool` field | Auto-detected via `verificationprogress < 0.9999`. `X-Node-Syncing: true` header added to all responses when node is syncing. |
| **Stale Data Indicators** | `Meta.cached: bool`, `Meta.cache_age_seconds: int \| None` | Auto-populated from blockchain info cache state. Lets clients know data freshness. |
| **Broadcast Pre-Validation** | `decoderawtransaction` before `sendrawtransaction` | `/broadcast` catches malformed hex early. RPC error codes mapped to human-readable HTTP responses (see Section 4). |

### 3.5 Response Format

All responses use a standard envelope:

```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2026-03-06T12:00:00+00:00",
    "request_id": "uuid",
    "node_height": 939462,
    "chain": "main",
    "syncing": false,
    "cached": true,
    "cache_age_seconds": 12
  }
}
```

Errors follow the same structure:

```json
{
  "error": {
    "type": "https://bitcoinsapi.com/errors/not-found",
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
| **Authorization** | Tier-based access | Anonymous: read-only GET. Free+: POST + expensive GET (mining/stats). Block-walking caps per tier (anon/free: 144, pro: 1008, enterprise: 2016) |
| **Rate Limiting** | Per-minute + daily | Sliding window (in-memory or Upstash Redis) + DB-backed daily counts |
| **Input Validation** | Regex + Pydantic | 64-hex txid, non-negative heights, hex-only bodies |
| **Body Size** | 2MB limit | Pydantic `Field(max_length=2_000_000)` on hex inputs |
| **Node Protection** | RPC whitelist | Only 21 safe commands allowed via `rpcwhitelist` |
| **Network** | Localhost-only RPC | `rpcbind=127.0.0.1`, `rpcallowip=127.0.0.1` |
| **Broadcast Validation** | Decode-before-send | `decoderawtransaction` pre-check; RPC -25 → 409, -26 → 422, -27 → 409 |
| **Information Hiding** | Version redaction | Node version/subversion hidden from anonymous users |
| **Secrets** | SecretStr for RPC password | Pydantic SecretStr prevents accidental logging |
| **Access Logging** | Structured logs | IP, method, path, status, tier, request_id |
| **CORS** | Allowlist-based | Configured origins, not wildcard in production |
| **Security Headers** | Middleware-injected | CSP, X-Frame-Options DENY, HSTS, X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy, X-XSS-Protection, X-Data-Disclaimer |
| **Terms of Service** | `/terms` static page | Acceptable use, liability limitation, financial disclaimer, FL governing law |
| **Privacy Policy** | `/privacy` static page | Data collection transparency, retention periods, third-party services |
| **ToS Acceptance** | `/register` endpoint | `agreed_to_terms: true` required for API key registration |
| **CoinGecko Attribution** | Prices response + footer | Required by CoinGecko ToS; `attribution` field in /prices response |
| **RFC 7807 Errors** | `type` URI on all error responses | 12 error type URIs at `https://bitcoinsapi.com/errors/*`, default `about:blank` |
| **Retry-After** | Header on 429 responses | Per-minute: calculated from window reset; daily: 3600s |
| **Gzip Compression** | GzipMiddleware | Responses ≥1000 bytes compressed automatically |
| **HSTS** | Conditional on HTTPS | `max-age=31536000; includeSubDomains` when behind TLS |
| **CSP** | Strict policy (skipped on docs) | `default-src 'self'`, allowlists for inline styles (landing page), GitHub images. Skipped on `/docs`, `/redoc`, `/openapi.json` so Swagger UI / ReDoc can load CDN assets. |
| **Clickjacking** | Frame denial | `X-Frame-Options: DENY` + CSP `frame-ancestors 'none'` |
| **Circuit Breaker** | RPC fast-fail | 3 failures → OPEN (503 + Retry-After), 30s cooldown → HALF_OPEN probe, success → CLOSED. Non-RPC endpoints unaffected. |
| **Metrics Auth** | Admin-only `/metrics` | Requires `X-Admin-Key` header with `secrets.compare_digest()` constant-time comparison |
| **Registration Rate Limit** | Per-IP sliding window | 5 registrations/hour/IP + 3 keys/email hard cap |
| **Input Length Limits** | Pydantic Field constraints | Email `max_length=254`, label `max_length=100` on registration |
| **Privacy Enforcement** | Pre-commit hook | `scripts/privacy_check.py` blocks tracking code (GA, Mixpanel, fingerprinting) from being committed |
| **Agent Trigger Advisory** | Pre-commit hook | `scripts/trigger_check.py` shows which agent reviews are needed for changed files |

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
| XSS via landing page | CSP blocks inline scripts (except landing page), nosniff header | Very low |
| Clickjacking | X-Frame-Options DENY + CSP frame-ancestors 'none' | Very low |
| Tab-napping via external links | All external links use `rel="noopener noreferrer"` | Very low |
| Timing attack on auth | `secrets.compare_digest()` on all key comparisons | Very low |
| Registration abuse | Per-IP rate limit (5/hr) + per-email cap (3 keys) + field length validation | Very low |
| Metrics data exposure | `/metrics` gated behind `X-Admin-Key` admin auth | Very low |
| Tracking code injection | Pre-commit hook blocks analytics/tracking patterns | Very low |

### 4.3 Penetration Test Log

| Date | Scope | Findings | Status |
|------|-------|----------|--------|
| 2026-03-07 | Full API surface (live site) | 3 findings: metrics public (HIGH), no email length limit (HIGH), no registration rate limit (MEDIUM) | All fixed, deployed, verified |

**Pentest methodology:** Header injection, path traversal, SQL injection, XSS in user-agent, IDOR, timing attacks, input fuzzing, `.env` exposure, CORS misconfiguration, host header injection. Cloudflare Tunnel blocks most network-layer attacks.

---

## 5. Production Architecture Review

### 5.1 Grades by Principle

| Principle | Grade | Key Finding |
|-----------|-------|-------------|
| SOLID | B | Clean SRP, good DI. Rate limit strategies could use protocol abstraction. |
| Separation of Concerns | A- | Layers are clean. Minor: middleware does both auth + rate limit + logging. |
| Error Handling | B+ | Comprehensive handlers. Fixed: now logs exceptions server-side. |
| Security | A- | Defense in depth. Security headers (CSP, HSTS, X-Frame-Options). SecretStr for passwords. |
| Scalability | B | Thread-safe caching + rate limiting. SQLite is bottleneck at >1K req/s. |
| Observability | A | Structured JSON logging (opt-in), access logs + request IDs + admin analytics (78 endpoints + visual dashboard), auto-pruning, Prometheus `/metrics` endpoint, WebSocket pub/sub. |
| Configuration | A- | 12-factor compliant. Sensible defaults. |
| Testing | A- | 359 unit tests + 21 e2e + load test + security script. |
| Dependencies | A- | Minimal, intentional. Could pin tighter. |
| API Design | A- | Versioned, enveloped, deprecation headers. No idempotency keys yet. |
| Data Integrity | A- | WAL mode, parameterized queries, sync detection, stale data indicators, broadcast pre-validation. Enhanced migration runner with rollback + validation. |
| Deployment | A- | Non-root Docker, health checks, graceful shutdown, stale-while-error fallback, auto-start on reboot. |

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

**v0.3.1 Hardening (Mar 7):**
19. **No RPC timeout** -- Added configurable `RPC_TIMEOUT` (default 30s) via Settings, wired to BitcoinRPC constructor
20. **Address scan can hang** -- Wrapped `scantxoutset` in timeout guard, returns 504 on `ReadTimeout`
21. **No Cache-Control headers** -- Added middleware: fee/mempool→10s, deep blocks→1hr, health→no-cache, register→no-store
22. **404 returns HTML on API routes** -- `http_exception_handler` now returns JSON envelope for `/api/*` paths
23. **Registration not rate-limited** -- Removed `/api/v1/register` from rate limit skip set
24. **Raw mempool fetched repeatedly** -- Added `cached_raw_mempool` with 5s TTL for mempool/recent and fees/mempool-blocks
25. **Timing attack on API key comparison** -- Auth now uses `secrets.compare_digest()` for constant-time comparison
26. **Registration email enumeration** -- `/register` no longer reveals whether an email is already registered
27. **Cloudflare Insights tracking removed** -- Removed CF beacon from all HTML pages, CSP, and legal_audit checks

**Pentest Hardening (Mar 7):**
28. **Metrics endpoint publicly exposed** -- Added `X-Admin-Key` auth with `secrets.compare_digest()` on `/metrics` endpoint
29. **No per-IP registration rate limit** -- Added sliding window (5 registrations/hour/IP) with `threading.Lock` + `time.monotonic()`
30. **Unbounded email/label input** -- Added Pydantic `Field(max_length=254)` on email, `Field(max_length=100)` on label

### 5.3 Known Limitations (Acceptable for v0.1)

| Limitation | Impact | When to Address |
|------------|--------|-----------------|
| SQLite write bottleneck | >1K req/s will see contention | v0.2 -- batch writes or PostgreSQL |
| ~~No Prometheus metrics~~ | ~~Can't monitor cache hit rates, latency~~ | **RESOLVED** -- `/metrics` endpoint (prometheus-client) |
| No idempotency keys | POST retries could double-broadcast | v0.2 -- add `Idempotency-Key` header |
| ~~No schema migrations~~ | ~~Manual ALTER TABLE for DB changes~~ | **RESOLVED** -- SQL migration runner in `migrations/` |
| Daily limit COUNT(*) | O(n) per request at scale | v0.2 -- cache count in memory |
| ~~No webhook support~~ | ~~Clients must poll~~ | **RESOLVED** -- WebSocket `/api/v1/ws` with pub/sub |
| No address transaction history | Cannot provide `/address/{addr}/txs` | Deliberate -- Bitcoin Core RPC has no `getaddresshistory`. Requires external indexer (Electrs, Fulcrum). We offer `scantxoutset` via POST `/address/utxos` for UTXO lookup by address. Adding Electrs increases deployment complexity significantly. |
| Email delivery depends on Resend | Welcome email fails silently if Resend is down | Graceful degradation -- registration succeeds regardless, key always returned in response |

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
| 8 | v0.77 endpoints: mempool txids/recent, block txids/txs, tip height/hash, tx status, difficulty | 12 |
| 9 | L402 Lightning payments | Moved to separate extension package (bitcoin-api-l402) |
| 10 | Launch features: fee landscape, tx estimator, SSE streams, fee history | 9 |
| 11 | Security hardening (headers, CSP, HSTS), exchange compare tool, SEO comparison pages, robots.txt, sitemap.xml | 6 |
| 12 | Production hardening: RPC timeout, Cache-Control, 404 JSON, address timeout guard, cached raw mempool | 3 |
| 13 | Simplify for launch: feature flags for extended routers, 2-tier pricing presentation, README trim, Show HN draft | 0 |
| 14 | Legal infrastructure: ToS, Privacy Policy, financial disclaimer header, CoinGecko attribution, ToS acceptance on /register, Apache 2.0 license, DCO | 0 |
| 15 | Analytics & web metrics: enhanced request logging (method, latency, user-agent), 6 admin analytics endpoints, CF beacon, Bing verification, SEO metrics API usage tracker | 11 |
| 16 | 3-tier codebase refactor: split main.py (555→89 lines), cache factory+registry, batch usage logging, migration system, deep health endpoint, feature flags dict, test helpers | 0 (existing 129 all pass) |
| 17 | Service layer extraction (~300 lines from routers→services), enhanced migration runner (rollback, status, validation), structured JSON logging, migration status in /health/deep | 0 (existing 129 all pass) |
| 18 | Industry Standards: RFC 7807 type URIs, Retry-After on 429s, OpenAPI metadata (contact/license/terms/servers), GzipMiddleware, favicon route | 0 (existing 129 all pass) |
| 19 | Analytics infrastructure expansion: 4 new analytics endpoints (keys, growth, slow-endpoints, retention), auto-pruning in fee collector, admin dashboard (Chart.js), CSP + rate-limit skip updates | 10 |
| 20 | Interactive API guide: `/api/v1/guide` endpoint with use-case filtering and multi-language code examples | 9 |
| 21 | Prometheus `/metrics`, WebSocket `/api/v1/ws` pub/sub, Stripe billing (checkout/webhook/status/cancel), subscriptions migration | 27 |
| 22 | Supply, stats, mining expansion, raw block, merkle proof, whale SSE, visualizer page | 32 |
| 23 | Consistency pass: complete guide catalog (all 78 endpoints), `help_url` on all error handlers, path prefix mapping for 8 new categories, docs sync | 0 |
| 24 | Phase 3 analytics: client classification (`classify_client`), MCP funnel analytics endpoints (client-types, mcp-funnel), migration 005, User-Agent tracking in bitcoin-mcp L402 client | 12 |
| 25 | Tier gating (7 expensive endpoints), block-walking caps per tier, Stripe price_id guard, Electrs limitation docs | 12 |
| 26 | Resend email integration, Upstash Redis rate limiting, PostHog analytics, 19 new tests (notifications, Redis rate limit, integration) | 19 |
| 27 | Blockchain indexer Phase 1: PostgreSQL-backed address history, tx lookup, sync worker with ZMQ/polling, reorg handling, address_summary denormalization. Siloed under `indexer/` with `ENABLE_INDEXER=false` default. Optional deps: asyncpg, pyzmq. | 50 |
| 28 | Analytics automation: referrer tracking endpoint, conversion funnel endpoint, UTM param capture on registration (migration 009), IndexNow auto-submit on deploy, daily analytics digest script, static route fix for IndexNow key file | 5 |
| **Total** | **78 endpoints, 20 core routers (+ 3 indexer = 23 when enabled)** | **359 unit + 21 e2e** |

### 6.2 Files Delivered

**Source (50 files):**
- `src/bitcoin_api/` -- main, auth, cache, circuit_breaker, config, db, dependencies, exceptions, jobs, metrics, middleware, models, notifications, pubsub, rate_limit, static_routes, stripe_client, usage_buffer
- `src/bitcoin_api/services/` -- fees, transactions, exchanges, serializers, mining, stats
- `src/bitcoin_api/routers/` -- address, analytics, billing, blocks, exchanges, fees, guide, health_deep, keys, mempool, metrics, mining, network, prices, status, stream, supply, stats, transactions, websocket
- `src/bitcoin_api/migrations/` -- runner.py, 001_initial_schema.sql, 002_add_migrations_table.sql, 003_add_schema_migrations_index.sql, 004_add_subscriptions.sql, 005_add_client_type.sql, 006_add_referrer.sql, 007_add_client_ip.sql, 008_add_error_type.sql
- `src/bitcoin_api/indexer/` -- config, db, parser, worker, reorg, models
- `src/bitcoin_api/indexer/services/` -- address, transaction
- `src/bitcoin_api/indexer/routers/` -- indexed_address, indexed_tx, indexer_status
- `src/bitcoin_api/indexer/migrations/` -- 001_initial_schema.sql

**Tests (21 test files + 2 support files):**
- `tests/test_health.py` -- 11 tests (health, root, status, healthz, docs, visualizer)
- `tests/test_blocks.py` -- 18 tests (block-related endpoints)
- `tests/test_fees.py` -- 16 tests (fee endpoints)
- `tests/test_transactions.py` -- 27 tests (transaction endpoints)
- `tests/test_mempool.py` -- 7 tests (mempool endpoints)
- `tests/test_mining.py` -- 21 tests (mining endpoint + service)
- `tests/test_network.py` -- 26 tests (network, rate limit, error handling)
- `tests/test_keys.py` -- 12 tests (API key registration & auth)
- `tests/test_billing.py` -- 12 tests (Stripe billing)
- `tests/test_guide.py` -- 8 tests (guide endpoints)
- `tests/test_admin.py` -- 30 tests (admin dashboard, analytics, metrics)
- `tests/test_misc.py` -- 51 tests (supply, stats, prices, exchanges, address, streams, websocket, classify_client, migrations)
- `tests/test_stale_cache.py` -- 19 tests (stale store, _cached_rpc fallback, MAX_STALE_AGE, Prometheus counter)
- `tests/test_notifications.py` -- 9 tests (Resend email + PostHog analytics)
- `tests/test_rate_limit_redis.py` -- 6 tests (Redis rate limiting + fallback)
- `tests/test_indexer_parser.py` -- 25 tests (block parser, satoshi conversion, hex helpers)
- `tests/test_indexer_reorg.py` -- 15 tests (reorg detection, fork point with RPC, rollback logic)
- `tests/test_indexer_routers.py` -- 14 tests (indexed endpoints, auth, validation)
- `tests/test_indexer_worker.py` -- 19 tests (RPC retry, sync_blocks, _index_block, version check)
- `tests/test_indexer_services.py` -- 12 tests (address balance/history, transaction detail)
- `tests/test_e2e.py` -- 21 e2e tests (against live node)
- `tests/locustfile.py` -- Load test (8 weighted endpoints)
- `tests/helpers.py` -- Isolated router test client factory

**Deployment (6 files):**
- `Dockerfile`, `docker-compose.yml`, `docker-compose.prod.yml`
- `.env.example`, `.env.production.example`
- `cloudflared-config.yml.example`

**Documentation (6 files):**
- `README.md`, `CHANGELOG.md`, `blog-post.md`
- `docs/self-hosting.md`, `docs/bitcoin-conf-example.conf`
- `docs/OPERATIONS.md` -- How to run, restart, configure, use analytics, run agents

**CI/CD (2 active files):**
- `.github/workflows/ci.yml` -- Tests + lint on push
- `.github/workflows/publish.yml` -- PyPI publish on release
- ~~`.github/workflows/pages.yml`~~ -- Removed (static pages served by FastAPI, not GitHub Pages)

**Project config (1 file):**
- `CLAUDE.md` -- Project instructions for AI-assisted development

**Scripts (14 files):**
- `scripts/create_api_key.py`, `scripts/seed_db.py`
- `scripts/security_check.sh` (requires `SATOSHI_API_KEY` env var for POST tests)
- `scripts/security_audit.py` (10 automated security checks)
- `scripts/staging-check.sh` (pre-deploy validation: starts staging server, checks CSP/headers/docs/endpoints)
- `scripts/legal_audit.py` (10-area legal compliance checker: ToS, privacy, disclaimers, attribution, license)
- `scripts/privacy_check.py` (pre-commit privacy enforcer — blocks commits with secrets/PII)
- `scripts/trigger_check.py` (pre-commit advisory — reports which agents should review based on changed files)
- `scripts/install-hooks.sh` (installs pre-commit hooks: privacy enforcer blocking + trigger advisory non-blocking)
- `scripts/deploy-api.sh` (pull, test, kill, restart, health check, auto-tag on success)
- `scripts/diagnose.sh` (silo-by-silo diagnostic: node, tunnel, API, cache, DB, version, tests; supports --json and --silo filters)
- `scripts/release.sh` (version management: tag, list, diff, revert with backup branches)
- `scripts/watchdog-api.sh` (auto-restart zombie API; runs every 5 min via Task Scheduler)
- `scripts/smoke-test-api.sh` (5-point health check for cron monitoring; supports --quiet)
- `scripts/doc_consistency.py` (CI-enforced doc consistency checks)

**Legal (3 files):**
- `static/terms.html` -- Terms of Service (FL governing law, liability limitation, acceptable use)
- `static/privacy.html` -- Privacy Policy (data collection, retention, third-party services)
- `docs/LLC_PREP.md` -- LLC formation checklist (deferred until paying customers)

**Website (14 files):**
- `static/index.html` -- Landing page with JSON-LD structured data, security headers, SEO meta tags
- `static/vs-mempool.html` -- SEO comparison page: Satoshi API vs mempool.space
- `static/vs-blockcypher.html` -- SEO comparison page: Satoshi API vs BlockCypher
- `static/best-bitcoin-api-for-developers.html` -- SEO decision page: developer guide
- `static/bitcoin-api-for-ai-agents.html` -- SEO decision page: AI/MCP angle
- `static/self-hosted-bitcoin-api.html` -- SEO decision page: self-hosting
- `static/bitcoin-fee-api.html` -- SEO feature page: fee estimation endpoints
- `static/bitcoin-mempool-api.html` -- SEO feature page: mempool analysis endpoints
- `static/bitcoin-mcp-setup-guide.html` -- SEO guide: MCP setup for AI agents
- `static/robots.txt` -- Search engine crawl directives (welcomes AI crawlers)
- `static/terms.html` -- Terms of Service page
- `static/privacy.html` -- Privacy Policy page
- `static/sitemap.xml` -- XML sitemap for search engines (12 URLs)
- `static/admin-dashboard.html` -- Admin analytics dashboard (Chart.js, dark theme, auto-refresh)
- `static/visualizer.html` -- ECharts live visualization dashboard

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

### 7.2 External Services (all optional)

| Service | Purpose | Cost | Fallback if disabled |
|---------|---------|------|---------------------|
| **Upstash Redis** | Persistent, distributed rate limit state (sorted sets) | Free tier sufficient | In-memory sliding window (resets on restart) |
| **Resend** | Welcome email with API key on registration, usage alerts | Free tier (100 emails/day) | Key shown once in registration response only |
| **PostHog** | Landing page analytics, CTA tracking, registration funnel | Free tier (1M events/mo) | No landing page visitor visibility (API metrics unaffected) |

All three default to disabled. Enable via `.env` flags (`RESEND_ENABLED`, `POSTHOG_ENABLED`, `RATE_LIMIT_BACKEND=redis`). The API functions fully without any of them.

### 7.3 Deployment Steps

1. Buy domain, add to Cloudflare
2. Install `cloudflared`, create tunnel
3. Configure Bitcoin Core with `rpcwhitelist` (see `docs/bitcoin-conf-example.conf`)
4. `docker compose -f docker-compose.prod.yml up -d`
5. Configure `cloudflared` tunnel to `localhost:9332`
6. Set up UptimeRobot on `https://api.domain.dev/healthz`
7. Create initial API keys via `scripts/create_api_key.py`

### 7.4 Go-Live Checklist

- [x] All 359 unit tests pass
- [x] Security check script passes all 9 checks
- [x] E2E tests pass against live node
- [x] Load test: 50 users, 0 errors, p95 < 500ms (4ms median)
- [x] Quick tunnel HTTPS verified via Cloudflare
- [x] Permanent domain `bitcoinsapi.com` + named Cloudflare Tunnel `satoshi-api`
- [x] Anonymous POST /broadcast returns 403
- [x] Anonymous GET /network redacts version
- [x] UptimeRobot monitors /api/v1/health (5-min interval)
- [x] cloudflared Windows service auto-starts tunnel
- [x] SatoshiAPI scheduled task auto-starts API on logon
- [x] API key created for personal use
- [x] Bitcoin Core RPC whitelist configured (17 commands)

---

## 8. Product Strategy & Pricing

### 8.1 What We're Selling

Satoshi API serves three strategic purposes:

1. **Open source product** -- `pip install satoshi-api` is the fastest path from a Bitcoin node to a REST API. Value = convenience + developer experience.
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

| Tier | Price | Rate Limit | Daily Limit | POST Access | Target |
|------|-------|-----------|-------------|-------------|--------|
| **Self-Hosted** | Free forever | Unlimited | Unlimited | Yes | Node runners |
| **Anonymous (Hosted)** | Free | 30/min | 1,000/day | No | Try it, no signup |
| **Developer (Hosted)** | Free (with key) | 100/min | 10,000/day | Yes | Build & ship |
| **Pro** | $19/mo | 500/min | 100,000/day | Yes | Production apps |

**Launch strategy:** Free tiers at launch, Pro tier via Stripe when demand materializes. L402 Lightning payments available as optional extension (feature, not primary monetization). API keys are free — request via api@bitcoinsapi.com or self-serve `/api/v1/register` endpoint.

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
| **Satoshi API** | **Unlimited (self-host)** | **$0 (free hosted)** | **Yes** | **Fee intelligence, MCP/AI-ready, pip install** |

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
| PyPI | `pip install satoshi-api` | High |
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

### v0.3 (Launch Features — COMPLETE)
- `GET /fees/landscape` — "Should I send now?" decision engine with trend analysis
- `GET /fees/estimate-tx` — transaction size/fee estimator (pure math, no RPC)
- `GET /fees/history` — historical fee tracker (SQLite-backed, auto-pruning)
- `GET /stream/blocks` — SSE real-time block events
- `GET /stream/fees` — SSE fee rate updates every 30s
- Background fee collector (5-min snapshots for trend + history)

### v0.3.1 (Security Hardening — COMPLETE)
- Timing attack fix (`secrets.compare_digest`)
- Registration email enumeration fix
- Cloudflare Insights removed (privacy improvement)
- Service layer extraction (exchanges, fees, transactions, serializers)
- Migration rollback support
- JSON logging option (`log_format` config)
- Admin dashboard page (`static/admin-dashboard.html`)
- Pre-commit hooks: privacy enforcer (blocking) + trigger advisory (non-blocking)
- Unit tests expanded (139 → 207 across sprints 19-22)

### v0.3.2 (External Integrations — COMPLETE)
- Resend transactional email (welcome email on registration, usage alerts)
- Upstash Redis as optional rate limiting backend (persistent, distributed)
- PostHog analytics on landing page + server-side registration tracking
- Privacy-first PostHog config: no autocapture, no session recording, IP anonymized

### v0.3.3 (Resilience & Error Handling — COMPLETE)
- Stale-while-error cache fallback — when node is down, API serves last-known-good cached data instead of 502 errors
- Auto-start for Bitcoin Knots and cloudflared tunnel via Registry Run keys (API already had auto-start)
- Sanitized error messages — external-facing errors now say "Temporarily Unavailable" instead of exposing internal details
- Unit tests expanded (340 → 359)

### v0.3.4 (Security Hardening — Next)
- CSP nonce-based script loading (remove `'unsafe-inline'` from script-src)
- Subresource Integrity (SRI) for any external scripts
- API key rotation endpoint (issue new key, deprecate old)
- SSE connection authentication (optional API key for stream endpoints)
- Rate limiting for SSE connections (connection count per tier)
- `Expect-CT` header for certificate transparency monitoring
- Security.txt (`/.well-known/security.txt`) with disclosure policy

### v0.4 (Medium Effort)
- ~~Prometheus `/metrics` endpoint~~ **RESOLVED** -- Sprint 21
- Idempotency key support for POST
- ~~Alembic schema migrations~~ **RESOLVED** -- Enhanced native runner with rollback, status, validation (Sprint 17)
- ~~Batch usage log writes~~ **RESOLVED** -- Usage buffer (Sprint 16)

### L402 Lightning Payments (Extension Package)
- Separated into `bitcoin-api-l402` package for clean base product
- Layers on via `enable_l402(app, ...)` — no code in core API
- Includes: macaroon minting/verification, Lightning client (Alby Hub + mock), endpoint pricing, FastAPI middleware
- Repository: github.com/Bortlesboat/bitcoin-api-l402

### v0.5 (Address Lookups — PARTIAL)
- [x] `GET /address/{address}` — address balance and UTXO summary via `scantxoutset` (no Electrs needed)
- [x] `GET /address/{address}/utxos` — list UTXOs for address via `scantxoutset` (sorted by value, paginated)
- [ ] `GET /address/{addr}/txs` — address transaction history (requires Electrs/Fulcrum)
- [ ] PostgreSQL backend option

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
