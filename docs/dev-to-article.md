---
title: "I Built a REST API for Bitcoin Core — Here's What I Learned"
published: false
description: "Lessons from wrapping Bitcoin Core's JSON-RPC in a developer-friendly REST API with analyzed data, smart caching, and AI agent support."
tags: bitcoin, api, python, opensource
cover_image: https://raw.githubusercontent.com/Bortlesboat/bitcoin-api/main/static/og-image.svg
canonical_url: https://bitcoinsapi.com/best-bitcoin-api-for-developers
---

I run a Bitcoin full node. When I started building apps against it, I hit the same wall everyone hits: Bitcoin Core's JSON-RPC is designed for node operators, not application developers.

The RPC works. It's stable, well-documented, and battle-tested. But if you've ever tried to build a product on top of it, you know the pain points. So I spent a few months wrapping it in a proper REST API, and I learned some things worth sharing.

## The Problem Nobody Talks About

Bitcoin Core's RPC returns fees in BTC/kVB. Every application developer on earth thinks in sat/vB. That's a multiplication, a unit conversion, and a mental model mismatch — on every single call.

`estimatesmartfee` returns one estimate per call. Want fee recommendations for 1, 3, 6, and 144 blocks? That's four RPC round-trips, four response parses, and you still have to write the logic to tell your user "fees are moderate right now, you can wait."

`getmempoolinfo` gives you transaction count and total size. Useful, but what developers actually need is: "How congested is the mempool? What fee rate gets me into the next block? What does the fee distribution look like?"

Raw RPC is a power tool. Most apps need a product.

## What I Built

[Satoshi API](https://bitcoinsapi.com) is a thin REST layer over Bitcoin Core. `pip install`, point at your node, get 40 clean endpoints with analyzed data.

```bash
pip install bitcoin-api
export BITCOIN_RPC_USER=your_user
export BITCOIN_RPC_PASSWORD=your_password
bitcoin-api  # http://localhost:9332/docs
```

That's the entire setup. Here's what the fee endpoint looks like versus calling `estimatesmartfee` five times yourself:

```bash
curl https://bitcoinsapi.com/api/v1/fees/recommended
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

One call. Human-readable recommendation. All targets. Units already in sat/vB. The `meta` envelope tells you exactly which chain and height this came from.

But the interesting part isn't the API itself — it's the design decisions I had to make along the way.

## Lesson 1: Analyzed Data > Raw Data

The biggest ROI came from adding an analysis layer between the RPC and the REST response. Bitcoin Core gives you primitives. Apps need derived insights.

The mempool endpoint is a good example. Raw `getmempoolinfo` tells you there are 14,832 transactions using 7.5 MB. The analyzed endpoint tells you the mempool is at "medium" congestion, the minimum fee to make the next block is 8.2 sat/vB, and breaks down the fee distribution into buckets so you can visualize where your transaction would land.

The transaction analysis endpoint detects SegWit, Taproot, and inscriptions automatically. Block analysis includes weight utilization percentage and a SegWit adoption ratio. None of this is hard to compute, but doing it once in the API layer saves every downstream consumer from reimplementing it.

If you're wrapping any RPC-style backend in a REST API, consider what your consumers actually want to *know*, not just what the backend *returns*.

## Lesson 2: Not All Blocks Are Created Equal

This one bit me early. I added caching (obviously — you don't want to re-fetch block 500,000 every time someone asks for it). But blocks near the chain tip can be orphaned by a reorg. Cache a tip block for an hour and you might serve stale data after a reorg.

The solution is depth-aware caching with two separate stores:

- **Deep blocks** (6+ confirmations): 1-hour TTL. These are effectively immutable.
- **Tip blocks** (< 6 confirmations): 30-second TTL. Short enough to catch reorgs.
- **Mutable data** (fees, mempool): 5-10 second TTL. Always near-fresh.

When a block request comes in, the cache checks `tip_height - block_height` to decide which store to use. Block 100,000 gets cached once and served for an hour. The latest block gets re-validated every 30 seconds. Fees refresh every 10 seconds.

This pattern applies to any blockchain API. If you're caching chain data, you need to think about finality depth, not just time.

## Lesson 3: Rate Limit Your Own Node

This sounds counterintuitive — why would you rate limit yourself? Because Bitcoin Core's RPC server is single-threaded. Flood it with concurrent requests from multiple apps and you'll block your own wallet operations.

Satoshi API has four tiers (Anonymous at 30/min, Free at 100/min, Pro at 500/min, Enterprise at 2,000/min) with per-minute sliding windows in memory and daily limits backed by SQLite so they survive restarts. Even if you're the only user, the rate limiter prevents any single runaway script from starving your node.

The per-minute window is in-memory for speed. Daily counters persist in SQLite (WAL mode, so reads don't block writes). Every response includes `X-RateLimit-Remaining` headers so clients can self-throttle.

## Lesson 4: Response Envelopes Save Everyone's Time

Every successful response returns `{ data, meta }`. Every error returns `{ error: { status, title, detail, request_id } }`. No exceptions.

This seems trivial, but it eliminates an entire category of client-side bugs. You never have to guess whether the response is the data directly or wrapped in an object. You never parse a 200 response that's actually an error message. The `request_id` (UUID on every response via header and body) makes debugging trivial — "this request failed" becomes "request `550e8400-...` returned 404 with detail 'Transaction not found'."

If you're building any API from scratch in 2026, standardize your envelope on day one. Retrofitting it later is painful.

## The AI Agent Angle

This is the part I'm most excited about. The third layer of the stack is [bitcoin-mcp](https://bitcoinsapi.com/bitcoin-api-for-ai-agents), a Model Context Protocol server that lets AI agents query your node directly.

Add this to your Claude Desktop config:

```json
{
  "mcpServers": {
    "bitcoin": {
      "command": "uvx",
      "args": ["bitcoin-mcp"],
      "env": {
        "BITCOIN_API_URL": "http://localhost:9332"
      }
    }
  }
}
```

Now you can ask Claude: "What's the current mempool congestion?" or "Analyze the latest block" and it hits your node, gets structured JSON, and reasons over it. No third-party API. No privacy leakage.

As far as I know, no other Bitcoin API has native AI agent support. The pipeline is three clean layers: `bitcoinlib-rpc` (typed Python library) -> `satoshi-api` (REST) -> `bitcoin-mcp` (AI interface). Each layer has one job.

## Self-Hosting Matters More Than You Think

When you use a hosted Bitcoin API, every address lookup, transaction query, and fee check is correlated with your IP. The API provider builds a profile of which addresses you care about. For a technology built on financial privacy, that's a significant tradeoff most developers don't think about.

Self-hosting Satoshi API means your queries never leave your network. Your node, your data, your privacy. The three-line setup makes this practical, not just aspirational.

There's also a [free hosted tier](https://bitcoinsapi.com) if you want to prototype before running your own node — but for production, self-hosting is the point.

## What's Next

The API currently covers blocks, transactions, mempool, fees, mining, and network info — everything Bitcoin Core exposes via RPC. The roadmap includes:

- **Address lookups** via Electrs/Fulcrum integration
- **Prometheus metrics** endpoint for node monitoring dashboards
- **Webhook notifications** for new blocks and mempool events

## Try It

- **Live API + docs playground**: [bitcoinsapi.com/docs](https://bitcoinsapi.com/docs)
- **GitHub**: [github.com/Bortlesboat/bitcoin-api](https://github.com/Bortlesboat/bitcoin-api)
- **PyPI**: [pypi.org/project/satoshi-api/](https://pypi.org/project/satoshi-api/)
- **Comparison with other Bitcoin APIs**: [bitcoinsapi.com/best-bitcoin-api-for-developers](https://bitcoinsapi.com/best-bitcoin-api-for-developers)

Apache-2.0 licensed, 129 unit tests + 21 E2E tests (150 total), CI pipeline. If you run a node and want a clean API on top of it, I'd love feedback — open an issue or drop a comment below.
