# Changelog

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
