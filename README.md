<div align="center">

![Satoshi API](static/satoshi-api-logo.png)

# Satoshi API

**Stop overpaying Bitcoin fees. Know when to send.**

[![CI](https://github.com/Bortlesboat/bitcoin-api/actions/workflows/ci.yml/badge.svg)](https://github.com/Bortlesboat/bitcoin-api/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/satoshi-api?color=orange)](https://pypi.org/project/satoshi-api/)
[![Downloads](https://img.shields.io/pypi/dm/satoshi-api)](https://pypi.org/project/satoshi-api/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Live API](https://img.shields.io/badge/live-bitcoinsapi.com-f7931a)](https://bitcoinsapi.com)
[![OpenSats](https://img.shields.io/badge/Support-OpenSats-f7931a)](https://opensats.org)

[Live Playground](https://bitcoinsapi.com/docs) &middot; [Landing Page](https://bitcoinsapi.com) &middot; [PyPI](https://pypi.org/project/satoshi-api/) &middot; [MCP Server](https://github.com/Bortlesboat/bitcoin-mcp) &middot; [Discord Bot](https://github.com/Bortlesboat/satoshi-discord-bot)

</div>

---

<div align="center">

**Live at [bitcoinsapi.com](https://bitcoinsapi.com)** &middot; **MCP-ready** &middot; **x402 pay-per-call** &middot; **Apache 2.0**

</div>

---

Bad fee timing burns sats on every Bitcoin transaction. Satoshi API tells you when to send, what to pay, and whether to wait — combining multiple `estimatesmartfee` targets with real-time mempool state. Instead of just "4 sat/vB", you get "Fees are low. Good time to send." One `pip install`, self-hostable, open source.

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

| Category | Example paths | Highlights |
|----------|---------------|------------|
| **Fees** | `/api/v1/fees/recommended`, `/api/v1/fees/plan` | Recommendations, landscape ("send now or wait?"), history, mempool-blocks |
| **Transactions** | `/api/v1/tx/{txid}`, `/api/v1/broadcast` | Decoded analysis, status, outspends, UTXO lookup, broadcast |
| **Mempool** | `/api/v1/mempool`, `/api/v1/mempool/recent` | Congestion score, fee buckets, recent entries |
| **Blocks** | `/api/v1/blocks/latest`, `/api/v1/blocks/{height_or_hash}` | Latest block, by height/hash, stats, txids, header |
| **Mining** | `/api/v1/mining`, `/api/v1/mining/nextblock` | Hashrate, difficulty, next block template |
| **Network** | `/api/v1/network`, `/api/v1/network/difficulty` | Peers, forks, difficulty, address validation |
| **Streams** | `/api/v1/stream/blocks`, `/api/v1/stream/fees` | Real-time blocks & fees via SSE |

...and more (prices, address lookups, exchange comparison). [Full interactive docs at `/docs`](https://bitcoinsapi.com/docs).

## For AI Agents

**[bitcoin-mcp](https://github.com/Bortlesboat/bitcoin-mcp)** — the first Bitcoin MCP server on the official Anthropic MCP Registry — lets AI agents check fees, verify payments, and monitor addresses without human babysitting. Saves developer time: no custom Bitcoin plumbing needed.

```bash
# Install and point at your Satoshi API instance
pip install bitcoin-mcp
SATOSHI_API_URL=https://bitcoinsapi.com bitcoin-mcp
```

Or connect to a local node directly:

```json
{
  "mcpServers": {
    "bitcoin": { "command": "bitcoin-mcp" }
  }
}
```

For repo-native agent instructions, use [docs/AGENT_INTEGRATION.md](docs/AGENT_INTEGRATION.md). It includes copy-paste snippets for `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, Cursor/Windsurf rules, MCP config, and x402 paid calls.

For keyless premium calls, start at [bitcoinsapi.com/x402/start](https://bitcoinsapi.com/x402/start). The paid flow is: discover `/.well-known/x402`, request a paid `/api/v1` endpoint, read `PAYMENT-REQUIRED`, then retry with `PAYMENT-SIGNATURE`.

## Self-Hosting

```bash
pip install satoshi-api
satoshi-api  # runs on :9332

# Expose publicly (free HTTPS + DDoS protection)
cloudflared tunnel --url http://localhost:9332
```

See [self-hosting guide](docs/self-hosting.md) for full production setup.

## Research Export

For offline fee-forecasting work, the repo now includes a local JSONL export path that emits the same merged row shape used by the companion benchmark importer.

```powershell
$env:PYTHONPATH='src'
python scripts/export_fee_forecast_benchmark.py data/fee-forecast-benchmark.jsonl --hours 168 --interval-minutes 10
```

The export joins local `fee_history` observations to the next `1-6` confirmed blocks from the research tables in `data/bitcoin_api.db`. After migration `012_add_research_tables.sql`, the background fee collector also fills `block_confirmations` on each detected new block and logs fee estimates every cycle, so a normal local API run can build this export without extra manual seeding. Very recent observations without six future block outcomes are skipped automatically.

## Contributing

Issues and PRs welcome. Run the test suite before submitting:

```bash
pip install -e ".[dev]"
pytest
```

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for the 12-month development plan — indexer expansion, multi-network support, fee prediction, SDKs, and more.

## Support This Project

Satoshi API is free, open-source Bitcoin infrastructure. If you find it useful, consider supporting development through [OpenSats](https://opensats.org).

## Related Projects

- [bitcoin-mcp](https://github.com/Bortlesboat/bitcoin-mcp) — MCP server with 49 Bitcoin tools for AI agents
- [ChainPulse](https://github.com/Bortlesboat/chainpulse) — AI-powered Bitcoin network intelligence CLI
- [BAIP-1](https://github.com/Bortlesboat/baip-python) — Bitcoin Agent Identity Protocol

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

<div align="center">

**[Live API](https://bitcoinsapi.com/docs)** &middot; **[Website](https://bitcoinsapi.com)** &middot; **[PyPI](https://pypi.org/project/satoshi-api/)** &middot; **[MCP Server](https://github.com/Bortlesboat/bitcoin-mcp)** &middot; **[Roadmap](docs/ROADMAP.md)**

Built by a [Bitcoin Core contributor](https://github.com/Bortlesboat). Run `python -m pytest --collect-only -q` for the current test inventory.

</div>
