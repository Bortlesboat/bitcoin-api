# Competitive Analysis: Satoshi API v0.3.3

## Overview

Satoshi API is a **Bitcoin fee intelligence service** that saves money on every transaction. It tells you when to send, what to pay, and whether to wait — then lets AI agents act on that data autonomously.

**bitcoinlib-rpc** (Python RPC client) → **Satoshi API** (REST/WS/SSE) → **bitcoin-mcp** (MCP for AI agents)

Live at [bitcoinsapi.com](https://bitcoinsapi.com). Free, no signup needed. Self-hostable via `pip install satoshi-api`.

**Competitive framing:** We don't compete on endpoint count. We compete on: **Does using this save you money or time?**

---

## Competitor Overview

| Provider | Model | Auth | Endpoints | Address Index | Self-Hostable | AI Integration |
|---|---|---|---|---|---|---|
| **Satoshi API** | Open-source (Apache-2.0) | API key (4 tiers) | 73 | Optional (asyncpg+zmq) | Yes (primary mode) | MCP server (bitcoin-mcp) |
| **mempool.space** | Open-source (AGPL) | None (IP rate limit) | ~140+ | Electrs required | Yes (heavyweight) | None |
| **BlockCypher** | Hosted SaaS | API token | ~40 | Hosted only | No | None |
| **Esplora** (Blockstream) | Open-source (MIT) | None | ~30 | Electrs-based | Yes | None |
| **GetBlock** | Hosted SaaS | API key | RPC passthrough | Hosted only | No | None |
| **QuickNode** | Hosted SaaS | API key | RPC passthrough | Hosted only | No | None |

---

## Detailed Comparisons

### vs mempool.space

mempool.space is the closest competitor in scope. Most of their ~140+ endpoints cover areas outside Satoshi API's focus:

| mempool.space Category | Approx. Endpoints | In Our Scope? |
|---|---|---|
| Core Bitcoin (blocks, txs, mempool, fees, mining) | ~50 | Yes — covered |
| Lightning Network | ~24 | No |
| Liquid Network | ~20 | No |
| Accelerator | ~12 | No |
| Mining pool history/tracking | ~22 | No |
| Wallet/Treasury tracking | ~10 | No |
| RBF/CPFP/Audit | ~12 | No |

Within core Bitcoin, Satoshi API has full parity or leads on blocks, transactions, mempool, fees, mining, and network data. Areas where Satoshi API goes beyond mempool.space:

- **API key auth with 4 tiers** (anon/free/pro/enterprise) vs no auth
- **Rate limit headers** (`X-RateLimit-*`) on every response vs opaque 429s
- **WebSocket real-time subscriptions** (new blocks, mempool events) with topic-based channels
- **SSE streaming** (whale transactions, new blocks) via `/stream`
- **Supply/halving tracking** with live inflation rate and countdown
- **Exchange price comparison** endpoints
- **Analytics endpoints** (network-level statistics, UTXO set composition, SegWit adoption)
- **Block template analysis** (`/mining/nextblock`) from actual `getblocktemplate` RPC
- **Transaction decode without broadcast** (`POST /decode`)
- **Prometheus metrics** endpoint for operational monitoring
- **Circuit breaker** for RPC resilience
- **MCP integration** via bitcoin-mcp for AI agent workflows
- **One-liner install** (`pip install satoshi-api`) vs Docker + Electrs + MariaDB

mempool.space leads in: Lightning Network data, Liquid Network, mining pool historical tracking, RBF/CPFP analysis, transaction acceleration, and raw hex endpoints.

### vs BlockCypher

BlockCypher is a hosted-only SaaS with ~40 endpoints focused on multi-chain support (BTC, ETH, LTC, DOGE). Comparison:

| Dimension | Satoshi API | BlockCypher |
|---|---|---|
| Self-hosting | Yes (primary) | No |
| Open source | Yes (Apache-2.0) | No |
| Bitcoin depth | Deep (78 endpoints, mining, mempool, supply, analytics) | Moderate (~15 BTC-specific) |
| Address lookups | Yes (optional indexer) | Yes (hosted) |
| WebHooks/streaming | WebSocket + SSE | WebHooks (push to your URL) |
| Pricing | Free self-hosted; hosted free tier | Free tier (3 req/sec), paid plans |
| Multi-chain | Bitcoin only | BTC, ETH, LTC, DOGE |

BlockCypher's advantage is zero setup (hosted) and multi-chain. Satoshi API's advantage is depth of Bitcoin-specific data, self-sovereignty, and the full product suite (RPC client + REST API + MCP).

### vs Esplora (Blockstream)

Esplora is Blockstream's open-source block explorer API, powering blockstream.info.

| Dimension | Satoshi API | Esplora |
|---|---|---|
| Install | `pip install satoshi-api` | Rust binary + Electrs |
| Endpoints | 73 | ~30 |
| Auth/tiers | API key with 4 tiers | None |
| Rate limiting | In-memory + Upstash Redis, per-tier | IP-based only |
| Streaming | WebSocket + SSE | None |
| Caching | TTL with reorg-safe depth awareness | None built-in |
| Metrics | Prometheus endpoint | None |
| AI integration | MCP server | None |

Esplora is lightweight and reliable for basic block/tx/address queries. Satoshi API offers a richer feature set (streaming, auth, caching, metrics, AI integration) with an easier install path.

### vs GetBlock / QuickNode

Both are hosted RPC-passthrough services — they proxy your JSON-RPC calls to their managed nodes.

| Dimension | Satoshi API | GetBlock / QuickNode |
|---|---|---|
| Abstraction | REST API with structured responses | Raw JSON-RPC passthrough |
| Self-hosting | Yes | No |
| Price | Free (self-hosted) | $0-$500+/mo depending on usage |
| Response format | Structured JSON with `{ data, meta }` envelope | Raw Bitcoin Core RPC responses |
| Streaming | WebSocket + SSE | WebSocket (limited) |
| Auth | Built-in tier system | API key (single tier) |
| Value-add | Fee recommendations, congestion scoring, supply tracking, analytics | Node management only |

These services solve a different problem (managed node access). Satoshi API adds a structured data layer on top of the node, with features that don't exist in raw RPC.

---

## Satoshi API Unique Advantages

### Architecture & Operations
1. **One-liner install** — `pip install satoshi-api` gets you a running API server. No Docker, no database prerequisites, no multi-service orchestration.
2. **Self-hosted by default** — Your node, your data, no third-party dependency. Hosted free tier available for those who don't run a node.
3. **Apache-2.0 license** — Permissive. Fork it, embed it, build on it commercially.
4. **Circuit breaker for RPC** — Automatic failover and recovery when Bitcoin Core is temporarily unavailable.
5. **TTL caching with reorg-safe depth** — Cache invalidation accounts for chain reorganizations. Bounded LRU for hash mappings.
6. **Prometheus metrics** — `/metrics` endpoint for Grafana dashboards, alerting, and operational visibility.

### Security & Auth
7. **4-tier API key system** — Anonymous, Free, Pro, Enterprise with distinct rate limits and endpoint access.
8. **Tier-gated endpoints** — 7 expensive endpoints (mining/stats/analytics) require Free+ API key. Block count caps per tier (anon/free: 144, pro: 1008, enterprise: 2016).
9. **Rate limiting with headers** — Sliding window (in-memory or Upstash Redis) + daily caps. Standard `X-RateLimit-*` headers on every response.
10. **SecretStr for all secrets** — RPC passwords and API keys never appear in logs or error messages.
11. **CAN-SPAM compliant emails** — Transactional email via Resend with proper unsubscribe handling.
12. **GDPR privacy policy** — Published and enforced.

### Data & Endpoints
13. **20 routers** — status, blocks, tx, fees, mempool, mining, network, stream, keys, supply, stats, prices, address, exchanges, analytics, admin, cache, billing, metrics, websocket.
14. **SSE streaming** — Real-time whale transaction alerts and new block notifications via `/stream`.
15. **WebSocket subscriptions** — Topic-based real-time data push (`/api/v1/ws`).
16. **Supply and halving tracking** — Circulating supply, inflation rate, halving countdown, subsidy schedule.
17. **Exchange price comparison** — Cross-exchange BTC price data.
18. **Block template analysis** — `/mining/nextblock` exposes actual `getblocktemplate` data (fee range, weight, tx count).
19. **Transaction decode without broadcast** — `POST /decode` inspects raw transactions without submitting them.
20. **Address lookups** — Optional asyncpg+zmq indexer for address balance, transaction history, and UTXO queries.
21. **Network analytics** — UTXO set composition, SegWit adoption rates, OP_RETURN statistics.
22. **Congestion scoring** — Mempool endpoint includes human-readable congestion level (low/medium/high/critical).
23. **Fee recommendations** — Per-target estimates with human-readable text ("High priority: 25 sat/vB for ~1 block confirmation").

### AI & Developer Experience
24. **Three-layer product suite** — bitcoinlib-rpc (library) → Satoshi API (REST) → bitcoin-mcp (MCP). Developers pick the abstraction level they need.
25. **MCP integration** — bitcoin-mcp provides 35 tools for AI agents (Claude, GPT, etc.) to query Bitcoin data natively. No other Bitcoin API has this.
26. **Swagger UI** — Interactive API documentation at `/docs` with try-it-out for every endpoint.
27. **Structured responses** — Consistent `{ data, meta }` envelope with `request_id` tracing on all responses.

### Testing & Quality
28. **380 tests** — 359 unit + 21 end-to-end. Comprehensive coverage across all routers and edge cases.

---

## Gaps We Intentionally Skip

| Feature Area | Why |
|---|---|
| **Lightning Network** | Requires separate LN node infrastructure. Different protocol entirely. |
| **Liquid Network** | Sidechain with niche adoption. Requires Elements node. |
| **Transaction acceleration** | Requires mining pool business partnerships. |
| **Mining pool historical tracking** | Requires ongoing coinbase parsing and pool identification database. |
| **RBF/CPFP analysis** | Requires continuous mempool monitoring with high memory/storage cost. |
| **Multi-chain support** | Bitcoin-only focus is a feature, not a limitation. |

---

## What's Next

Near-term priorities for Satoshi API:

- **SDK clients** — Python and TypeScript client libraries for typed API access
- **Docker Compose** — One-command deployment with optional Electrs address indexer
- **Historical mempool statistics** — Periodic snapshots for trend analysis
- **Multi-node failover** — Automatic fallback across multiple Bitcoin Core instances
- **Webhook push notifications** — Configurable alerts for address activity, large transactions, new blocks

---

*Last updated: 2026-03-07 — Satoshi API v0.3.3 (78 endpoints, 380 tests, 20 routers)*
