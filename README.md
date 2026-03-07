<div align="center">

# Satoshi API

**REST API for your Bitcoin node. One `pip install`, 40 endpoints.**

[![CI](https://github.com/Bortlesboat/bitcoin-api/actions/workflows/ci.yml/badge.svg)](https://github.com/Bortlesboat/bitcoin-api/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/satoshi-api?color=orange)](https://pypi.org/project/satoshi-api/)
[![Downloads](https://img.shields.io/pypi/dm/satoshi-api)](https://pypi.org/project/satoshi-api/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Live API](https://img.shields.io/badge/live-bitcoinsapi.com-f7931a)](https://bitcoinsapi.com)

[Live Playground](https://bitcoinsapi.com/docs) &middot; [Landing Page](https://bitcoinsapi.com) &middot; [PyPI](https://pypi.org/project/satoshi-api/) &middot; [MCP Server](https://github.com/Bortlesboat/bitcoin-mcp)

</div>

---

Satoshi API wraps Bitcoin Core's JSON-RPC in a clean REST interface with analyzed data, smart caching, and tiered rate limiting. Instead of calling `estimatesmartfee` five times and doing math, you get fee recommendations in sat/vB. Instead of raw `getmempoolinfo`, you get congestion scores and fee buckets.

```
Your App  -->  Satoshi API (REST)  -->  Bitcoin Core (RPC)  -->  Blockchain
                     |
              bitcoin-mcp (MCP)  -->  AI Agents (Claude, GPT)
```

## Quick Start

```bash
pip install satoshi-api

export BITCOIN_RPC_USER=your_user
export BITCOIN_RPC_PASSWORD=your_password

satoshi-api
# API:  http://localhost:9332
# Docs: http://localhost:9332/docs
```

Or try the live API right now — no install needed:

```bash
curl https://bitcoinsapi.com/api/v1/fees/recommended | jq
```

<details>
<summary>Docker</summary>

```bash
echo "BITCOIN_RPC_USER=your_user" > .env
echo "BITCOIN_RPC_PASSWORD=your_password" >> .env

docker compose up -d
```

</details>

## Why Not Just Use RPC Directly?

| Feature | Satoshi API | Raw RPC | Hosted APIs |
|---------|-------------|---------|-------------|
| Setup | 3 lines | Already there | Sign up + API key |
| Self-hosted | Yes | Yes | No |
| Privacy | Your node, your data | Your node | They see your queries |
| Analyzed data | Fee recs, congestion scores | Raw values only | Varies |
| Caching | Reorg-aware TTL | None | Varies |
| Rate limiting | Built-in, tiered | None | Yes (their limits) |
| Input validation | Before RPC call | None | Yes |
| Cost at scale | $0 (self-host) | $0 | $50-500+/mo |
| AI agent support | MCP ready | No | No |

## Endpoints

40 endpoints across 8 categories. All prefixed with `/api/v1/`. [Full interactive docs at `/docs`](https://bitcoinsapi.com/docs).

<details>
<summary><strong>Blocks</strong> — 8 endpoints</summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/blocks/latest` | Latest block analysis |
| GET | `/blocks/tip/height` | Current chain height |
| GET | `/blocks/tip/hash` | Current tip block hash |
| GET | `/blocks/{height_or_hash}` | Block by height or hash |
| GET | `/blocks/{height}/stats` | Detailed block statistics |
| GET | `/blocks/{hash}/txids` | Transaction IDs in a block |
| GET | `/blocks/{hash}/txs` | Full transactions in a block |
| GET | `/blocks/{hash}/header` | Raw block header |

</details>

<details>
<summary><strong>Transactions</strong> — 7 endpoints</summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tx/{txid}` | Transaction analysis (fees, SegWit, Taproot) |
| GET | `/tx/{txid}/raw` | Raw decoded transaction |
| GET | `/tx/{txid}/hex` | Transaction as hex string |
| GET | `/tx/{txid}/status` | Confirmation status |
| GET | `/tx/{txid}/outspends` | Spending status of each output |
| GET | `/utxo/{txid}/{vout}` | UTXO lookup (spent/unspent) |
| POST | `/broadcast` | Broadcast signed transaction |

</details>

<details>
<summary><strong>Fees</strong> — 7 endpoints</summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/fees` | Fee estimates (all targets) |
| GET | `/fees/recommended` | Human-readable high/medium/low |
| GET | `/fees/{target}` | Fee for specific confirmation target |
| GET | `/fees/landscape` | Should I send now or wait? |
| GET | `/fees/estimate-tx` | Transaction size & fee cost estimator |
| GET | `/fees/history` | Historical fee rates & cheapest hour |
| GET | `/fees/mempool-blocks` | Fee distribution by projected blocks |

</details>

<details>
<summary><strong>Mempool</strong> — 5 endpoints</summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/mempool` | Congestion analysis (fee buckets, score) |
| GET | `/mempool/info` | Raw mempool info |
| GET | `/mempool/tx/{txid}` | Single mempool entry |
| GET | `/mempool/txids` | All mempool transaction IDs |
| GET | `/mempool/recent` | Recently added entries |

</details>

<details>
<summary><strong>Mining, Network, Prices, Streams</strong> — 13 endpoints</summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/mining` | Hashrate, difficulty, retarget |
| GET | `/mining/nextblock` | Next block template analysis |
| GET | `/network` | Connections, relay fee, version |
| GET | `/network/forks` | Chain tips and fork detection |
| GET | `/network/difficulty` | Difficulty and retarget info |
| GET | `/network/validate-address/{addr}` | Validate a Bitcoin address |
| GET | `/prices` | BTC price in 6 fiat currencies |
| GET | `/stream/blocks` | Real-time new block events (SSE) |
| GET | `/stream/fees` | Live fee rate updates (SSE) |
| POST | `/decode` | Decode raw transaction hex |
| POST | `/register` | Self-serve API key registration |
| GET | `/health` | Node reachability check |
| GET | `/status` | Full node status |

</details>

## Examples

```bash
# Fee recommendation — what should I pay right now?
curl https://bitcoinsapi.com/api/v1/fees/recommended
# {
#   "data": {
#     "recommendation": "Fees are low. Good time to send.",
#     "estimates": { "high": 4, "medium": 2, "low": 1 }
#   }
# }

# Should I send now or wait?
curl https://bitcoinsapi.com/api/v1/fees/landscape

# Mempool congestion
curl https://bitcoinsapi.com/api/v1/mempool

# Latest block analysis
curl https://bitcoinsapi.com/api/v1/blocks/latest

# Transaction analysis — Satoshi's first transaction
curl https://bitcoinsapi.com/api/v1/tx/f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16
```

## AI Agent Integration (MCP)

Satoshi API pairs with [bitcoin-mcp](https://github.com/Bortlesboat/bitcoin-mcp) to give AI assistants direct access to your Bitcoin node via [Model Context Protocol](https://modelcontextprotocol.io/).

```json
// Claude Desktop config
{
  "mcpServers": {
    "bitcoin": {
      "command": "bitcoin-mcp",
      "args": ["--api-url", "http://localhost:9332"]
    }
  }
}
```

Ask Claude: *"What are current Bitcoin fees?"* *"Should I send a transaction now or wait?"* *"Analyze the latest block."*

No other Bitcoin API has native MCP integration.

## API Keys & Rate Limits

Anonymous access works out of the box. For higher limits:

```bash
# Self-serve registration
curl -X POST https://bitcoinsapi.com/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "label": "my-app"}'
```

| Tier | Req/min | Req/day | POST Access |
|------|---------|---------|-------------|
| Anonymous | 30 | 1,000 | No |
| Free (API key) | 100 | 10,000 | Yes |
| Pro ($19/mo) | 500 | 100,000 | Yes |
| Enterprise | 2,000 | Unlimited | Yes |

Self-hosted = unlimited requests, no tiers needed.

## Architecture

- **Stack:** FastAPI + [bitcoinlib-rpc](https://github.com/Bortlesboat/bitcoinlib-rpc) + SQLite (WAL mode)
- **Caching:** Reorg-aware TTL — deep blocks cached 1hr, tip blocks 30s, fees 10s
- **Security:** API key auth (SHA256 hashed), input validation before RPC, CSP/HSTS headers, rpcwhitelist
- **Testing:** 110 unit tests + 21 e2e tests + load test + security check script
- **Deployment:** pip, Docker, or Cloudflare Tunnel for public access

## Self-Hosting

```bash
# Production deployment with Cloudflare Tunnel (free HTTPS, DDoS protection)
pip install satoshi-api
satoshi-api  # runs on :9332

# Expose publicly
cloudflared tunnel --url http://localhost:9332
```

See [self-hosting guide](docs/self-hosting.md) for full production setup.

## Contributing

Issues and PRs welcome. Run the test suite before submitting:

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT

---

<div align="center">

**[Live API](https://bitcoinsapi.com/docs)** &middot; **[Website](https://bitcoinsapi.com)** &middot; **[PyPI](https://pypi.org/project/satoshi-api/)** &middot; **[MCP Server](https://github.com/Bortlesboat/bitcoin-mcp)**

Built by a [Bitcoin Core contributor](https://github.com/Bortlesboat).

</div>
