# Competitive Analysis: Satoshi API vs mempool.space

## Summary

Satoshi API currently exposes **77 endpoints** (v0.2.1). mempool.space exposes **~77 endpoints**.

However, most of mempool.space's surface area falls outside our scope:

| Category | mempool.space Endpoints | In Our Scope? |
|---|---|---|
| Core Bitcoin (blocks, txs, mempool, fees, mining) | ~50 | Yes |
| Lightning Network | 24 | No |
| Liquid Network | 20 | No |
| Accelerator | 12 | No |
| Mining pool history/tracking | 22 | No |
| About/Meta/Internal | 11 | No |
| Wallet/Treasury tracking | ~10 | No |
| RBF/CPFP/Audit | ~12 | No |

**The real comparison is 25 vs ~50 core Bitcoin endpoints.** We cover the most important ones and have unique features they lack.

---

## Feature Parity Table

| # | Satoshi API Endpoint | mempool.space Equivalent | Status |
|---|---|---|---|
| 1 | `GET /block/latest` | `GET /api/blocks/tip/hash` + `GET /api/block/{hash}` | **Parity** — same data, we combine into one call |
| 2 | `GET /block/{hash}` | `GET /api/block/{hash}` | **Parity** |
| 3 | `GET /block/height/{height}` | `GET /api/block-height/{height}` | **Parity** |
| 4 | `GET /blocks` | `GET /api/v1/blocks/{startHeight}` | **Parity** |
| 5 | `GET /tx/{txid}` | `GET /api/tx/{txid}` | **Parity** |
| 6 | `POST /tx/broadcast` | `POST /api/tx` | **Parity** |
| 7 | `POST /decode` | *None* | **Ahead** — unique to Satoshi API |
| 8 | `GET /fees` | `GET /api/v1/fees/recommended` | **Ahead** — we add per-target flexibility, text recommendations |
| 9 | `GET /fees/estimates` | `GET /api/v1/fees/recommended` | **Parity** |
| 10 | `GET /mempool` | `GET /api/mempool` | **Parity** — we add congestion score |
| 11 | `GET /mempool/fees` | `GET /api/mempool` (embedded) | **Parity** |
| 12 | `GET /mining/hashrate` | `GET /api/v1/mining/hashrate/{timePeriod}` | **Behind** — they have historical timeseries |
| 13 | `GET /mining/difficulty` | `GET /api/v1/difficulty-adjustment` | **Parity** |
| 14 | `GET /mining/nextblock` | *None* | **Ahead** — block template analysis is unique |
| 15 | `GET /network/info` | `GET /api/v1/lightning/statistics/latest` (partial) | **Parity** — different data shape |
| 16 | `GET /utxo/{txid}/{vout}` | `GET /api/tx/{txid}/outspend/{vout}` (partial) | **Ahead** — direct UTXO lookup vs outspend check |
| 17 | `GET /health` | *None (internal)* | **Parity** — standard ops endpoint |
| 18 | `GET /info` | *None* | **Ahead** — API metadata |
| 19 | `GET /` | *None* | **Parity** — root/welcome |

**Score: 5 Ahead, 13 Parity, 1 Behind**

---

## Gaps We Should Close (v0.2-v0.3)

### Low Effort (v0.2 — wrappers around existing Bitcoin Core RPCs)

| Endpoint | mempool.space Equivalent | Notes |
|---|---|---|
| `GET /mempool/txids` | `GET /api/mempool/txids` | `getrawmempool` RPC |
| `GET /mempool/recent` | `GET /api/mempool/recent` | `getrawmempool` + sort by time |
| `GET /block/{hash}/txids` | `GET /api/block/{hash}/txids` | `getblock` verbosity=1 |
| `GET /block/{hash}/txs` | `GET /api/block/{hash}/txs/{startIndex}` | `getblock` verbosity=2, paginated |
| `GET /tx/{txid}/status` | `GET /api/tx/{txid}/status` | `gettxout` + `getrawtransaction` |
| `GET /chain/tip/height` | `GET /api/blocks/tip/height` | `getblockcount` |
| `GET /chain/tip/hash` | `GET /api/blocks/tip/hash` | `getbestblockhash` |
| `GET /difficulty-adjustment` | `GET /api/v1/difficulty-adjustment` | Compute from `getblockchaininfo` |

**Estimated effort:** 1-2 days. All data available from Bitcoin Core with no additional infrastructure.

### Medium Effort (v0.2-v0.3)

| Endpoint | mempool.space Equivalent | Notes |
|---|---|---|
| `GET /mempool/blocks` | `GET /api/v1/fees/mempool-blocks` | Projected blocks from mempool — requires fee bucketing logic |
| `GET /tx/{txid}/outspends` | `GET /api/tx/{txid}/outspends` | Check if each output is spent — needs UTXO set scanning |
| `GET /mempool/stats` | `GET /api/v1/statistics/{timePeriod}` | Historical mempool size/fee stats — requires periodic snapshots |
| `GET /price` | `GET /api/v1/prices` | BTC price — needs external API (CoinGecko, etc.) |

**Estimated effort:** 3-5 days. Some require background jobs or external data sources.

### High Effort (v0.3+)

| Endpoint | mempool.space Equivalent | Notes |
|---|---|---|
| `GET /address/{address}` | `GET /api/address/{address}` | Address balance, tx count, UTXO list |
| `GET /address/{address}/txs` | `GET /api/address/{address}/txs` | Transaction history for address |
| `GET /address/{address}/utxo` | `GET /api/address/{address}/utxo` | Unspent outputs for address |
| `GET /scripthash/{hash}` | `GET /api/scripthash/{hash}` | Script hash lookups |

**Estimated effort:** 1-2 weeks. Requires an address index (Electrs, Fulcrum, or similar). Bitcoin Core alone cannot efficiently look up transactions by address. This is the single biggest architectural decision for v0.3.

---

## Gaps We Intentionally Skip

| Feature Area | mempool.space Endpoints | Why We Skip |
|---|---|---|
| **Lightning Network** | 77 endpoints (nodes, channels, stats, liquidity rankings) | Requires a separate LN node (LND/CLN). Completely different infrastructure. Could be a separate project. |
| **Liquid Network** | 77 endpoints (L-BTC, assets, pegs, federation) | Sidechain with niche usage. Elements node required. Not core Bitcoin. |
| **Accelerator** | 77 endpoints (bid, estimate, history) | Paid transaction acceleration service. Requires mining pool partnerships and business relationships. |
| **Mining pool tracking** | 77 endpoints (pool rankings, hashrates, block counts, rewards) | Requires a database of pool identifiers + coinbase transaction parsing + historical data collection. Large ongoing data effort. |
| **Wallet/Treasury tracking** | ~77 endpoints (known wallets, balances) | Manual address curation and labeling. Editorial, not API. |
| **RBF tracking** | ~77 endpoints (replacements, full-RBF history) | Requires continuous mempool monitoring and replacement event tracking. High memory/storage cost. |
| **CPFP analysis** | ~77 endpoints (effective fee rates, package analysis) | Complex parent/child fee calculation across transaction graphs. Specialized mempool analysis. |
| **Block audit/template prediction** | ~77 endpoints (audit scores, predicted blocks) | Requires their block template prediction system and post-hoc comparison. Proprietary methodology. |
| **Address prefix search** | `GET /api/address-prefix/{prefix}` | Explorer UI feature. Requires full address index. Low API value. |
| **Block raw/header hex** | `GET /api/block/{hash}/raw`, `/header` | Raw hex dumps. Niche use case. Available directly from Bitcoin Core RPC for anyone self-hosting. |

---

## Our Unique Advantages

Things Satoshi API offers that mempool.space does not:

### 1. `POST /decode` — Transaction Decode Without Broadcast
Decode a raw transaction hex to inspect inputs, outputs, scripts, and fees without broadcasting. mempool.space has no equivalent — you either broadcast or get nothing.

### 2. `GET /mining/nextblock` — Block Template Analysis
Real-time view of what the next block would look like if mined now: transaction count, total fees, weight, fee range. Built on `getblocktemplate` RPC. mempool.space projects mempool into blocks but doesn't expose actual template data.

### 3. `GET /utxo/{txid}/{vout}` — Point UTXO Lookup
Direct lookup of a specific UTXO by txid and output index. Returns value, scriptPubKey, confirmation status. mempool.space only has outspend checks (is it spent?), not UTXO state queries.

### 4. `GET /fees` — Per-Target Flexibility with Human-Readable Text
Fee estimates with configurable confirmation targets and human-readable recommendations ("High priority: 25 sat/vB for ~1 block confirmation"). mempool.space returns fixed buckets (fastest, halfHour, hour, economy, minimum) without explanatory text.

### 5. Congestion Scoring on `/mempool`
Mempool endpoint includes a congestion score (low/medium/high/critical) based on size and fee pressure. mempool.space returns raw stats without interpretation.

### 6. API Key Authentication with Tiers
Built-in API key system with configurable rate limit tiers (free, pro, enterprise). mempool.space's public API has no auth — just IP-based rate limiting with no guaranteed SLA.

### 7. Rate Limiting with Headers
Standard `X-RateLimit-*` headers on every response so clients can manage their usage. mempool.space returns 429s without rate limit metadata.

### 8. MCP / AI Agent Integration Layer
First-class Model Context Protocol (MCP) server for AI agent integration. Claude, GPT, and other LLM agents can query Bitcoin data natively. No equivalent exists for mempool.space.

### 9. `pip install` One-Liner
`pip install satoshi-api` and you have a running Bitcoin API server. mempool.space requires Docker, a full Electrs index, MariaDB, and significant configuration.

### 10. Self-Hosted by Default
Designed to run against your own Bitcoin Core node. Your node, your data, your rules. mempool.space is primarily a hosted service — self-hosting is possible but heavyweight.

---

## Roadmap Impact

### v0.2 — Core Completeness (Target: +8-77 endpoints)

**New endpoints from gap analysis:**
- `GET /mempool/txids` — list all mempool transaction IDs
- `GET /mempool/recent` — recently broadcast transactions
- `GET /block/{hash}/txids` — transaction IDs in a block
- `GET /block/{hash}/txs` — full transactions in a block (paginated)
- `GET /tx/{txid}/status` — confirmation status of a transaction
- `GET /chain/tip/height` — current block height
- `GET /chain/tip/hash` — current best block hash
- `GET /difficulty-adjustment` — difficulty epoch progress and estimates

**Also in v0.2:**
- WebSocket support for new blocks and mempool events
- Batch RPC connection pooling
- Response caching layer

### v0.3 — Extended Data (Target: +4-77 endpoints)

**New endpoints from gap analysis:**
- `GET /mempool/blocks` — projected next blocks from mempool
- `GET /tx/{txid}/outspends` — spent status of transaction outputs
- `GET /price` — BTC price from external feeds
- `GET /mempool/stats` — historical mempool statistics (requires snapshot storage)

**Also in v0.3:**
- Address lookups (requires Electrs/Fulcrum integration decision)
  - `GET /address/{address}` — balance and tx count
  - `GET /address/{address}/txs` — transaction history
  - `GET /address/{address}/utxo` — unspent outputs
- Optional Electrs backend configuration

### v0.4 — Production Hardening

- Prometheus metrics and Grafana dashboards
- Multi-node failover
- Docker Compose with optional Electrs
- SDK clients (Python, TypeScript)
- Hosted tier (if demand warrants)

---

*Last updated: 2026-03-06*
