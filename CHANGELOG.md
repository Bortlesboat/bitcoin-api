# Changelog

## [Unreleased]

### Added
- **History Explorer** — 7 new endpoints: `/history/events`, `/history/events/{id}`, `/history/eras`, `/history/eras/{id}`, `/history/concepts`, `/history/concepts/{id}`, `/history/search`
- **MCP streamable-http transport** — MCP server now mounted at `/mcp` using streamable-http (replaces SSE transport at `/mcp/sse`)
- **MCP discovery** — `.well-known/mcp/server-card.json` route for MCP server discovery
- **Smithery listing** — live at smithery.ai/servers/Bortlesboat/bitcoin-mcp

### Changed
- MCP transport upgraded from SSE (`/mcp/sse`) to streamable-http (`/mcp`)
- Endpoints: 87 → 95 (84 core + 7 history + 4 indexer)
- Routers: 24 → 25 (22 core + 3 indexer)
- Unit tests: 407 → 454 (475 total with 21 e2e)
- 429 rate limit responses now include `upgrade` object with next tier info, pricing, and action URL
- Rate limit error messages reworded to be friendlier ("Register for free: 10x more requests, takes 10 seconds")

### Fixed
- **Registration blocked by rate limits** — `/api/v1/register` was subject to per-minute and daily rate limits, so users who hit the anonymous cap couldn't upgrade. Registration endpoint now exempt from both rate limit checks (still has its own per-IP abuse protection).

## [0.3.3] - 2026-03-08

### Added
- **Stale cache fallback** — when Bitcoin node is down, API serves last-known-good cached data instead of 502 errors. Applies to fees, mempool, blocks, status, network, and all `_cached_rpc` endpoints.
- Auto-start for Bitcoin Knots and cloudflared tunnel via Registry Run keys (previously only the API had auto-start)

### Changed
- Error messages sanitized — external-facing errors now say "Temporarily Unavailable" instead of exposing internal details like "Is the node running?" or "Circuit breaker OPEN"
- Cache module uses stale-while-error pattern: fresh data is saved to a secondary store that survives TTL expiry
- Unit tests: 335 → 400 (421 total with 21 e2e)

### Fixed
- **Site down after PC reboot** — Bitcoin Knots and cloudflared tunnel now auto-start on logon. Previously only the API process had auto-start, so reboots left the site returning 530/502.
- **cloudflared Windows service broken** — service ran as SYSTEM but config was in user profile. Replaced with user-level Registry Run key that finds config correctly.

## [0.3.2] - 2026-03-07

### Added
- Resend transactional email integration (welcome email on registration, usage alerts)
- Upstash Redis as optional rate limiting backend (persistent, distributed)
- PostHog analytics on landing page + server-side registration tracking
- Privacy-first PostHog config: no autocapture, no session recording, IP anonymized
- `POST /api/v1/keys/unsubscribe` — CAN-SPAM compliant email opt-out endpoint
- `email_opt_out` column on api_keys table (migration 006)
- Physical mailing address in email footer (CAN-SPAM compliance)
- GDPR section in privacy policy (lawful basis, data portability, supervisory authority)
- Prometheus endpoint normalization — prevents cardinality explosion from dynamic paths
- `total_tx_count` in paginated block transaction responses
- `response_model` annotations on fee endpoints (landscape, estimate-tx, history)
- Age restriction in Terms of Service (must be 13+)
- `.env.production` and `.env.local` in .gitignore

### Fixed
- **Usage buffer lock contention** — DB writes no longer block request threads (drain under lock, write outside)
- **Redis rate limiter unbounded growth** — 2-phase pipeline checks `zcard` before `zadd`
- **SecretStr migration** — all 7 secrets in config.py use Pydantic SecretStr, all call sites use `.get_secret_value()`
- **Migration runner atomicity** — replaced `executescript()` with `BEGIN` + individual `execute()` + `commit()` with rollback
- **Stripe lazy import** — prevents crash when stripe package not installed
- **Analytics SQL epoch fix** — correct bucket calculation using `CAST(strftime('%s', ts) AS INTEGER)`
- **Median fee calculation** — correct median for even-length lists
- **Supply off-by-one** — `remaining = height + 1` for accurate subsidy calculation
- **Sats conversion rounding** — `round(gross_btc * 1e8)` instead of `int()` truncation
- **Cache mutation** — shallow copy price data before adding attribution
- **XSS prevention** — landing page uses `textContent` instead of `innerHTML`
- **Email validation** — regex validation on registration endpoint
- Whale stream: cap 200 txids/poll, evict oldest half instead of `.clear()`
- Exchange price errors return 503 instead of 200 with error body
- Transaction service returns 502 for unmapped RPC errors instead of bare `raise`
- Address router gated behind `require_api_key()`
- Mining hashrate_history gated behind `require_api_key()`
- Mempool recent `count` parameter bounded with `Query(10, ge=1, le=100)`
- Network info uses cached RPC call (30s TTL)
- Slow-endpoints analytics query capped at `LIMIT 100000`
- License in OpenAPI spec corrected to Apache-2.0

### Changed
- Rate limiter now supports dual backend: Redis (primary when configured) with in-memory fallback
- Registration endpoint sends welcome email + fires PostHog event (both fire-and-forget)
- Tests force in-memory backend to avoid external service dependencies
- Stripe, Resend, Upstash Redis, PostHog moved to optional pip extras
- Unit tests: 231 → 335 (356 total with 21 e2e)
- Published to PyPI as `satoshi-api` v0.3.2
- Dockerfile now copies static/ directory
- Landing page: structured data updated (74 endpoints), enterprise CTA added
- Comparison pages (vs-mempool, vs-blockcypher) updated with current feature set

## [0.3.1] - 2026-03-07

### Added
- `GET /address/{address}` — address balance and UTXO summary via UTXO set scan
- `GET /address/{address}/utxos` — list UTXOs for an address (sorted by value, paginated)
- 5 address endpoint tests + 3 hardening tests
- RPC timeout configuration (`RPC_TIMEOUT` env var, default 30s)
- Cache-Control headers middleware (fee/mempool: 10s, blocks: 1hr, health: no-cache, register: no-store)
- Timeout guard on address endpoint `scantxoutset` (returns 504 on timeout)
- Cached raw mempool for mempool/recent and fees/mempool-blocks (5s TTL)
- Analytics & web metrics: enhanced request logging (method, latency, user-agent)
- 6 admin analytics endpoints (`/api/v1/analytics/*`: overview, requests, endpoints, errors, user-agents, latency)
- 4 more analytics endpoints (keys, growth, slow-endpoints, retention)
- Admin dashboard page (`static/admin-dashboard.html`) with Chart.js, dark theme, auto-refresh
- SEO metrics API usage tracker in `scripts/seo_metrics.py`
- `ADMIN_API_KEY` env var for analytics endpoint authentication
- 3-tier codebase refactor: split main.py (555→89 lines), cache factory+registry, batch usage logging, migration system
- Service layer extraction: `services/exchanges.py`, `services/fees.py`, `services/transactions.py`, `services/serializers.py`
- Enhanced migration runner with rollback support and validation
- JSON logging option (`log_format` config setting)
- Pre-commit hooks: `scripts/privacy_check.py` (blocking), `scripts/trigger_check.py` (non-blocking advisory), `scripts/install-hooks.sh`
- `static/bitcoin-mcp-setup-guide.html` — MCP setup guide for AI agents
- RFC 7807 error type URIs, Retry-After on 429s, GzipMiddleware

### Fixed
- 404 on `/api/v1/*` routes now returns JSON error envelope instead of HTML
- `/api/v1/register` now subject to rate limiting (removed from skip set)
- Timing attack on API key comparison — now uses `secrets.compare_digest()`
- Registration email enumeration — `/register` no longer reveals existing emails
- Cloudflare Insights beacon removed from all HTML pages, CSP, and legal_audit

### Removed
- `docs/website/` directory (static pages served by FastAPI directly)
- `.github/workflows/pages.yml` (no longer needed)

### Changed
- Total endpoints: 42 → 50
- Unit tests: 118 → 139 (160 total with 21 e2e)
- Static pages: 12 public pages

## [0.3.0] - 2026-03-07

### Added
- `GET /fees/landscape` — "should I send now or wait?" decision engine
- `GET /fees/estimate-tx` — transaction size and fee cost estimator
- `GET /fees/history` — historical fee rates with cheapest hour
- `GET /stream/blocks` — real-time new block events (Server-Sent Events)
- `GET /stream/fees` — live fee rate updates every 30s (SSE)
- `GET /tools/exchange-compare` — cross-exchange fee comparison (optional)
- `POST /register` — self-serve API key registration
- SEO pages: 7 decision/comparison pages with JSON-LD structured data
- robots.txt, sitemap.xml for search engine indexing
- IndexNow integration for Bing/Yandex indexing
- SEO metrics tracker script (`scripts/seo_metrics.py`)
- Security headers: CSP, HSTS, X-Frame-Options, Permissions-Policy
- CONTRIBUTING.md, SECURITY.md, CODE_OF_CONDUCT.md
- GitHub issue templates, PR template, dependabot config
- 15 GitHub topics for discoverability

### Changed
- Total endpoints: 33 → 40+
- Unit tests: 80 → 110
- README completely overhauled with badges, collapsible sections, live examples
- Landing page updated with JSON-LD structured data and improved meta tags
- Static pages exempt from rate limiting (crawlers can access freely)
- OG image updated to reflect 77 endpoints

## [0.2.1] - 2026-03-06

### Added
- `GET /tx/{txid}/hex` — raw transaction hex string
- `GET /tx/{txid}/outspends` — spending status of each output (spent/unspent via UTXO set)
- `GET /blocks/{hash}/header` — block header as hex string
- `GET /fees/mempool-blocks` — projected next blocks from mempool, grouped by fee rate
- `GET /prices` — BTC price in 6 currencies from CoinGecko (60s cache)
- `GET /network/validate-address/{address}` — validate a Bitcoin address
- 9 new unit tests + 6 new e2e tests (80 unit + 21 e2e total)

### Changed
- RPC whitelist: added `getblockheader`, `validateaddress` (now 19 commands)
- Total endpoints: 27 → 33

## [0.2.0] - 2026-03-06

### Added
- `GET /mempool/txids` — all transaction IDs in the mempool
- `GET /mempool/recent` — most recent mempool entries sorted by time (configurable count, max 100)
- `GET /blocks/tip/height` — chain tip height
- `GET /blocks/tip/hash` — chain tip block hash
- `GET /blocks/{hash}/txids` — transaction IDs in a block
- `GET /blocks/{hash}/txs` — full transactions in a block (paginated, default 25, max 100)
- `GET /tx/{txid}/status` — transaction confirmation status
- `GET /network/difficulty` — difficulty epoch progress, blocks remaining, estimated retarget date
- Competitive analysis document (vs mempool.space — 77 endpoints mapped)
- 12 new unit tests + 6 new e2e tests (71 unit + 15 e2e total)

### Changed
- RPC whitelist: added `getrawmempool` (now 17 commands)
- Total endpoints: 19 → 27

## [0.1.0] - 2026-03-05

### Added
- REST API with 77 endpoints across 7 categories (blocks, transactions, fees, mempool, mining, network, status)
- Tiered API key authentication (anonymous, free, pro, enterprise)
- Sliding-window rate limiting (per-minute in-memory + daily DB-backed)
- TTL caching with reorg-safe depth awareness
- Input validation (txid format, block height range, fee target bounds)
- Structured error responses with request IDs
- Docker support with health checks
- 59 unit tests + 9 e2e tests with full endpoint coverage
- Security hardening: POST auth requirements, node fingerprint redaction, access logging, body size limits
- Production deployment support: Cloudflare Tunnel config, docker-compose.prod, self-hosting docs
- Bitcoin Core RPC whitelist configuration example
