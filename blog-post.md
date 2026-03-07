# I Built a REST API for My Bitcoin Node in Python

I run a Bitcoin full node. I wanted to query it programmatically -- check fees before broadcasting, monitor mempool congestion, pull block stats into dashboards. The options were: pay for a third-party API with rate limits, run a full block explorer stack (overkill), or just... curl my own node's RPC directly.

RPC works, but it's clunky. Authentication is HTTP basic auth over plaintext. The responses are raw and inconsistent. There's no input validation, no caching, no rate limiting if you want to expose it to other apps on your network. So I built a thin REST layer on top of it.

The result is **Satoshi API** -- 33 endpoints, FastAPI, typed responses, and analyzed data instead of raw RPC dumps. It's [open source](https://github.com/Bortlesboat/bitcoin-api) and on PyPI as `bitcoin-api`.

## What It Does

Point it at your node, get a clean REST API:

```bash
curl http://localhost:9332/api/v1/fees/recommended
```

```json
{
  "data": {
    "recommendation": "Fees are moderate. For next-block confirmation use 25 sat/vB. If you can wait 1 hour, 12 sat/vB should suffice.",
    "estimates": {
      "1": 25.0,
      "3": 18.0,
      "6": 12.0,
      "25": 8.0,
      "144": 5.0
    }
  },
  "meta": {
    "timestamp": "2026-03-05T12:00:00+00:00",
    "node_height": 939462,
    "chain": "main"
  }
}
```

Compare that to calling `estimatesmartfee` five times and doing the math yourself. The API gives you a human-readable recommendation, all targets in one call, and sat/vB conversion already done.

The mempool endpoint is similar -- instead of raw `getmempoolinfo`, you get fee buckets, a congestion level, and the minimum fee rate to get into the next block:

```bash
curl http://localhost:9332/api/v1/mempool
```

```json
{
  "data": {
    "size": 14832,
    "bytes": 7482910,
    "congestion": "medium",
    "next_block_min_fee": 8.2,
    "fee_buckets": [
      {"range": "1-5 sat/vB", "count": 3201, "total_vsize": 1540000},
      {"range": "5-10 sat/vB", "count": 4512, "total_vsize": 2180000},
      {"range": "10-25 sat/vB", "count": 3890, "total_vsize": 1920000},
      {"range": "25-50 sat/vB", "count": 2105, "total_vsize": 1100000},
      {"range": "50+ sat/vB", "count": 1124, "total_vsize": 742910}
    ]
  },
  "meta": {
    "timestamp": "2026-03-05T12:00:00+00:00",
    "node_height": 939462,
    "chain": "main"
  }
}
```

Every response follows the same envelope: `data` + `meta`. Errors follow the same pattern with `error.status`, `error.title`, `error.detail`. No guessing what shape the response will be.

## The Architecture

Satoshi API is the middle layer in a three-part stack:

```
bitcoinlib-rpc  -->  satoshi-api  -->  bitcoin-mcp
(typed RPC)         (REST API)        (AI agent interface)
```

**[bitcoinlib-rpc](https://github.com/Bortlesboat/bitcoinlib-rpc)** is a typed Python wrapper around Bitcoin Core's JSON-RPC. It handles connection management, error mapping, and the analysis functions (fee recommendations, mempool bucketing, block analysis). This is where the logic lives.

**Satoshi API** (this project) wraps that library in FastAPI. It adds HTTP concerns: caching, rate limiting, input validation, API keys, the envelope format. It doesn't contain Bitcoin logic -- it's a thin translation layer.

**[bitcoin-mcp](https://github.com/Bortlesboat/bitcoin-mcp)** is an MCP server that lets AI agents (Claude, GPT, etc.) query Satoshi API with tool calls. Ask Claude "what's the current mempool congestion?" and it hits your node directly. More on this below.

Each layer has a single responsibility. If you just want a Python library, use `bitcoinlib-rpc`. If you want HTTP, add `satoshi-api`. If you want AI agents, add `bitcoin-mcp`.

## Key Design Decisions

### Reorg-Aware Block Cache

Confirmed blocks are immutable... mostly. Within 6 blocks of the tip, a reorg can orphan them. The caching layer handles this with two separate caches:

```python
# Deep blocks (6+ confirmations) -- 1 hour TTL, they're not changing
_block_cache: TTLCache = TTLCache(maxsize=64, ttl=3600)

# Recent blocks near tip -- 30 second TTL, reorg safety
_recent_block_cache: TTLCache = TTLCache(maxsize=8, ttl=30)

REORG_SAFE_DEPTH = 6
```

When you request a block, the cache checks `(tip - height)`. Deep blocks get served from a 1-hour cache. Blocks near the tip use a 30-second cache. Historical block 500,000 gets cached once; the latest block gets re-fetched if it's older than 30 seconds.

Mutable data has even shorter TTLs: fees refresh every 10 seconds, mempool every 5, status every 30.

### Thread Safety

All cache access is behind a `threading.Lock()`. FastAPI runs on uvicorn with a thread pool for sync endpoints, so concurrent requests hitting the same cache need protection. The rate limiter uses a separate lock with the same pattern.

### Rate Limiting

Four tiers, enforced in middleware before the request reaches any endpoint:

| Tier | Req/min | Req/day |
|------|---------|---------|
| Anonymous | 30 | 1,000 |
| Free (API key) | 100 | 10,000 |
| Pro | 500 | 100,000 |
| Enterprise | 2,000 | Unlimited |

Per-minute limits use an in-memory sliding window. Daily limits are backed by SQLite so they survive restarts. Rate limit headers (`X-RateLimit-Remaining`, etc.) are on every response. If you're running this just for yourself, the anonymous tier is more than enough.

### Input Validation

Transaction IDs and block hashes are validated as 64-character hex strings *before* any RPC call. Invalid API keys return 401, not a silent downgrade to anonymous. RPC errors are mapped to appropriate HTTP status codes (-5 "not found" becomes 404, -8 "invalid parameter" becomes 400).

## The AI Agent Angle

This is the part that gets interesting. The third layer, `bitcoin-mcp`, implements the Model Context Protocol. You add it to Claude Desktop or any MCP-compatible client, and your AI assistant can query your node:

> "What are current fee levels?"
> "Analyze the latest block -- how full was it?"
> "Is the mempool congested right now?"

The agent calls your local API, gets structured JSON back, and reasons over it. No third-party API keys, no rate limit anxiety, no privacy concerns about which addresses or transactions you're looking up. Your node, your data.

For anyone building Bitcoin-aware AI agents or chatbots, this stack gives you a clean interface without reinventing the RPC plumbing.

## Getting Started

### pip install

```bash
pip install bitcoin-api

export BITCOIN_RPC_USER=your_user
export BITCOIN_RPC_PASSWORD=your_password

bitcoin-api
# API running at http://localhost:9332
# Interactive docs at http://localhost:9332/docs
```

### Docker

```bash
echo "BITCOIN_RPC_USER=your_user" > .env
echo "BITCOIN_RPC_PASSWORD=your_password" >> .env

docker compose up -d
```

### Create an API Key (Optional)

```bash
python scripts/create_api_key.py --tier pro --label "my-app"
# Pass via header: curl -H "X-API-Key: sk_..." localhost:9332/api/v1/mempool
```

That's it. Three lines to go from a running node to a REST API with docs, caching, and rate limiting.

## What It Isn't

This is not a block explorer. There's no address indexing, no balance lookups, no transaction history by address. Those require `txindex=1` or an external indexer like Electrs. Satoshi API wraps what Bitcoin Core gives you out of the box: blocks, transactions (by txid), mempool, fees, mining stats, network info.

If you need address queries, pair it with Electrs or Fulcrum. Satoshi API is complementary, not a replacement.

## What's Next

- **SSE endpoint for new blocks** -- subscribe to `/blocks/stream` and get push notifications when a block is mined
- **More analysis endpoints** -- UTXO set stats, peer geographic distribution, historical fee trends
- **WebSocket support** -- real-time mempool fee updates

The codebase is 80 tests, CI pipeline, MIT licensed. If you run a node and want a clean API on top of it, give it a try: [github.com/Bortlesboat/bitcoin-api](https://github.com/Bortlesboat/bitcoin-api).

Feedback welcome -- open an issue or find me on Nostr.

---

*Cross-posted to [dev.to](https://dev.to), [r/Bitcoin](https://reddit.com/r/Bitcoin), [r/BitcoinDev](https://reddit.com/r/BitcoinDev), and Nostr.*
