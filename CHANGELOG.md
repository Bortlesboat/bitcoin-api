# Changelog

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
