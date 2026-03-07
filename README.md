<div align="center">

# Satoshi API

**REST API for your Bitcoin node. One `pip install`, 71 endpoints.**

[![CI](https://github.com/Bortlesboat/bitcoin-api/actions/workflows/ci.yml/badge.svg)](https://github.com/Bortlesboat/bitcoin-api/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/satoshi-api?color=orange)](https://pypi.org/project/satoshi-api/)
[![Downloads](https://img.shields.io/pypi/dm/satoshi-api)](https://pypi.org/project/satoshi-api/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Live API](https://img.shields.io/badge/live-bitcoinsapi.com-f7931a)](https://bitcoinsapi.com)

[Live Playground](https://bitcoinsapi.com/docs) &middot; [Landing Page](https://bitcoinsapi.com) &middot; [PyPI](https://pypi.org/project/satoshi-api/) &middot; [MCP Server](https://github.com/Bortlesboat/bitcoin-mcp)

</div>

---

Wraps Bitcoin Core's JSON-RPC in a clean REST interface with analyzed data, smart caching, and tiered rate limiting.

## Install & Run

```bash
pip install satoshi-api
export BITCOIN_RPC_USER=your_user BITCOIN_RPC_PASSWORD=your_password
satoshi-api
# API:  http://localhost:9332
# Docs: http://localhost:9332/docs
```

## Example

```bash
curl http://localhost:9332/api/v1/fees/recommended | jq
```

```json
{
  "data": {
    "recommendation": "Fees are low. Good time to send.",
    "estimates": { "high": 4, "medium": 2, "low": 1 }
  },
  "meta": { "timestamp": "...", "node_height": 939462, "chain": "main" }
}
```

## Core Endpoints

| Category | Endpoints | Highlights |
|----------|-----------|------------|
| **Blocks** | 8 | Latest block, by height/hash, stats, txids, header |
| **Transactions** | 7 | Decoded analysis, status, outspends, UTXO lookup, broadcast |
| **Fees** | 7 | Recommendations, landscape ("send now or wait?"), history, mempool-blocks |
| **Mempool** | 5 | Congestion score, fee buckets, recent entries |
| **Mining** | 2 | Hashrate, difficulty, next block template |
| **Network** | 4 | Peers, forks, difficulty, address validation |
| **Streams** | 2 | Real-time blocks & fees via SSE |

...and more (prices, address lookups, exchange comparison). [Full interactive docs at `/docs`](https://bitcoinsapi.com/docs).

## AI Agent Integration (MCP)

Pairs with [bitcoin-mcp](https://github.com/Bortlesboat/bitcoin-mcp) to give AI assistants direct access to your Bitcoin node via [Model Context Protocol](https://modelcontextprotocol.io/).

```json
{
  "mcpServers": {
    "bitcoin": {
      "command": "bitcoin-mcp",
      "args": ["--api-url", "http://localhost:9332"]
    }
  }
}
```

## Self-Hosting

```bash
pip install satoshi-api
satoshi-api  # runs on :9332

# Expose publicly (free HTTPS + DDoS protection)
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

Apache 2.0 — see [LICENSE](LICENSE).

---

<div align="center">

**[Live API](https://bitcoinsapi.com/docs)** &middot; **[Website](https://bitcoinsapi.com)** &middot; **[PyPI](https://pypi.org/project/satoshi-api/)** &middot; **[MCP Server](https://github.com/Bortlesboat/bitcoin-mcp)**

Built by a [Bitcoin Core contributor](https://github.com/Bortlesboat).

</div>
