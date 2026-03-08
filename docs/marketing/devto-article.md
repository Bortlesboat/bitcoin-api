---
title: "Why I built a REST API for Bitcoin Core (and why raw RPC sucks)"
published: false
description: "Bitcoin Core's JSON-RPC is powerful but hostile to developers. Satoshi API wraps it in a clean REST layer with analyzed data, smart caching, and rate limiting. pip install, 3 lines, done."
tags: bitcoin, python, api, opensource
cover_image:
canonical_url: https://bitcoinsapi.com
---

If you've ever pointed `curl` at a Bitcoin Core node, you know the pain. The JSON-RPC interface is powerful -- it exposes everything about the blockchain -- but it was designed for internal use, not for building applications on top of.

I spent a weekend wrapping it in a proper REST API. Then the weekend turned into a month. Here's why raw RPC sucks and what I built instead.

## The problem with Bitcoin Core's RPC

Bitcoin Core exposes ~150 RPC commands over JSON-RPC. In theory, that's everything you need. In practice, there are five problems that make it miserable for app development:

**1. Fees come in BTC/kVB, not sat/vB.** Every wallet, block explorer, and fee estimator on the planet uses sat/vB. Bitcoin Core returns `0.00012345 BTC/kVB`. You have to multiply by 100,000 every single time. Miss a zero and your users overpay by 10x.

**2. No caching.** Every call hits the node. Ask for the same block twice, the node does the same work twice. Ask for fee estimates every second (like a wallet UI might), your node is doing 60 unnecessary `estimatesmartfee` calls per minute.

**3. No rate limiting.** Expose your RPC port and any client can hammer your node. There's `rpcworkqueue` but no per-client throttling, no tiers, no daily limits.

**4. Raw hex dumps.** Want transaction details? You get hex strings and have to decode them yourself. Want to know if a transaction uses SegWit or Taproot? Parse the witness data. The RPC gives you ingredients, not a meal.

**5. No input validation.** Pass a malformed txid? The node tries to look it up, fails, and returns a cryptic error. A proper API should reject `"not-a-txid"` before it ever touches the node.

## The solution: Satoshi API

Satoshi API is a thin REST layer that wraps your Bitcoin Core node. It's a Python package -- install it, point it at your node, get a clean API:

```bash
pip install satoshi-api

export BITCOIN_RPC_USER=your_user
export BITCOIN_RPC_PASSWORD=your_password

bitcoin-api
# -> http://localhost:9332/docs
```

Three lines from node to API. Here's what changes.

### Before: raw RPC fee estimation

```bash
curl -s --user user:pass --data-binary \
  '{"jsonrpc":"1.0","method":"estimatesmartfee","params":[6]}' \
  http://localhost:8332/

# Response:
{"result":{"feerate":0.00012345,"blocks":6},"error":null,"id":null}
```

What unit is `0.00012345`? BTC/kVB. What does that mean for a 140-vbyte transaction? Get your calculator out.

### After: Satoshi API fee recommendation

```bash
curl -s http://localhost:9332/api/v1/fees/recommended

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
    "timestamp": "2026-03-06T12:00:00+00:00",
    "node_height": 939462,
    "chain": "main"
  }
}
```

Human-readable recommendation. All targets at once. Sat/vB. Standard response envelope with metadata. Cached for 10 seconds so your wallet UI isn't grinding your node.

## Architecture: three layers

Satoshi API sits in a simple stack:

```
bitcoinlib-rpc   (Python RPC client, does the analysis)
      |
 Satoshi API     (FastAPI REST layer, adds auth/cache/rate-limit)
      |
  bitcoin-mcp    (MCP server, lets AI agents query Bitcoin)
```

Each layer has one job. `bitcoinlib-rpc` talks to the node and returns structured data. Satoshi API adds production concerns. `bitcoin-mcp` exposes it all to Claude, GPT, and other AI agents via the Model Context Protocol.

## Key features

### Mempool analysis

Not just raw stats -- congestion scoring and fee distribution buckets:

```bash
curl -s http://localhost:9332/api/v1/mempool

{
  "data": {
    "size": 45231,
    "bytes": 28456789,
    "congestion_score": 0.72,
    "fee_buckets": [
      {"range": "1-5 sat/vB", "count": 12450, "percentage": 27.5},
      {"range": "5-10 sat/vB", "count": 18200, "percentage": 40.2},
      ...
    ]
  }
}
```

### Block lookups

Full block analysis with weight utilization, SegWit/Taproot adoption stats:

```bash
curl -s http://localhost:9332/api/v1/blocks/latest
curl -s http://localhost:9332/api/v1/blocks/840000
```

### Transaction broadcast

Decode and broadcast signed transactions. Requires an API key (prevents spam):

```bash
# Decode first to verify
curl -s -X POST http://localhost:9332/api/v1/decode \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{"hex": "0200000001..."}'

# Then broadcast
curl -s -X POST http://localhost:9332/api/v1/broadcast \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{"hex": "0200000001..."}'
```

### Projected mempool blocks

See what the next blocks will look like based on current mempool fee distribution:

```bash
curl -s http://localhost:9332/api/v1/fees/mempool-blocks

{
  "data": [
    {
      "block_index": 0,
      "min_fee_rate": 15.0,
      "max_fee_rate": 250.0,
      "median_fee_rate": 25.0,
      "tx_count": 2800,
      "total_fees_sat": 8500000
    }
  ]
}
```

## Smart caching

Not all data is equal. The caching layer knows the difference:

| Data type | TTL | Why |
|-----------|-----|-----|
| Fee estimates | 10s | Fees change fast |
| Mempool stats | 5s | Volatile by nature |
| Blocks near tip (< 6 deep) | 30s | Reorgs can happen |
| Deep blocks (6+ confirmations) | 1 hour | Immutable for practical purposes |
| Blockchain info | 10s | Sync state changes |

Each cache has its own lock -- no cross-cache contention. Block hash lookups use a bounded LRU (256 entries) so memory doesn't grow unbounded.

## Self-hosting vs hosted

**Self-hosted (free forever):** You run Bitcoin Core, you run Satoshi API. Zero vendor lock-in, no rate limits beyond what you configure, full control. This is the primary use case.

```bash
pip install satoshi-api
satoshi-api  # done
```

**Hosted:** A public instance runs at [bitcoinsapi.com](https://bitcoinsapi.com) with free anonymous access (30 req/min, 1,000/day). Good for prototyping when you don't want to sync a node.

Rate limit tiers:

| Tier | Req/min | Req/day |
|------|---------|---------|
| Anonymous | 30 | 1,000 |
| Free (API key) | 100 | 10,000 |
| Pro | 500 | 100,000 |
| Enterprise | 2,000 | Unlimited |

## The AI angle: MCP integration

This is where it gets interesting. The companion project [bitcoin-mcp](https://github.com/Bortlesboat/bitcoin-mcp) wraps Satoshi API as an MCP (Model Context Protocol) server. That means Claude, GPT, and any MCP-compatible agent can query your Bitcoin node directly.

Ask your AI assistant "What are current Bitcoin fees?" and it calls `/fees/recommended`. Ask "Is the mempool congested?" and it checks `/mempool`. No prompt engineering, no copy-pasting from block explorers -- the agent has direct, structured access to your node.

## L402: Lightning-native API access

There's also optional support for [L402](https://docs.lightning.engineering/the-lightning-network/l402) -- the Lightning Labs protocol for HTTP 402 + Lightning micropayments. Clients can pay per-request with Lightning instead of using API keys. It's available as an extension package and is more of a Bitcoin-native feature than a monetization strategy -- but it's there if you want machine-to-machine payments for API access.

## What's honestly missing

No project is complete, and I'd rather be upfront about the gaps:

- **Address lookups are limited.** Uses `scantxoutset` which shows current UTXOs but not transaction history. Full address indexing needs Electrs/Fulcrum.
- **Single chain.** Bitcoin mainnet, testnet, and signet only. No Liquid, no altchains.
- **Single node.** No clustering, no failover. If your node goes down, the API goes down. Fine for personal use, not for production SLAs.

## Try it

**Install locally:**
```bash
pip install satoshi-api
```

**Use the hosted instance:**
```bash
curl https://bitcoinsapi.com/api/v1/fees/recommended
```

**Browse the source:**
[github.com/Bortlesboat/bitcoin-api](https://github.com/Bortlesboat/bitcoin-api) (Apache-2.0 license)

**PyPI:**
[pypi.org/project/satoshi-api/](https://pypi.org/project/satoshi-api/)

76 endpoints. 356 tests. Zero vendor lock-in. If you're building on Bitcoin and tired of parsing raw hex, give it a look.

---

*Satoshi API is open source under the Apache-2.0 license. PRs, issues, and feedback welcome.*
