# Changelog

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
- Cloudflare Web Analytics beacon + Bing Webmaster verification placeholders
- SEO metrics API usage tracker in `scripts/seo_metrics.py`
- `ADMIN_API_KEY` env var for analytics endpoint authentication
- 3-tier codebase refactor: split main.py (555→89 lines), cache factory+registry, batch usage logging, migration system

### Fixed
- 404 on `/api/v1/*` routes now returns JSON error envelope instead of HTML
- `/api/v1/register` now subject to rate limiting (removed from skip set)

### Changed
- Total endpoints: 42 → 48
- Unit tests: 118 → 129 (150 total with 21 e2e)

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
- OG image updated to reflect 40 endpoints

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
- Competitive analysis document (vs mempool.space — 161 endpoints mapped)
- 12 new unit tests + 6 new e2e tests (71 unit + 15 e2e total)

### Changed
- RPC whitelist: added `getrawmempool` (now 17 commands)
- Total endpoints: 19 → 27

## [0.1.0] - 2026-03-05

### Added
- REST API with 19 endpoints across 7 categories (blocks, transactions, fees, mempool, mining, network, status)
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
