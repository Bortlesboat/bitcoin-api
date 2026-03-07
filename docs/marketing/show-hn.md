# Show HN Post Draft

## Title

Show HN: Satoshi API -- one pip install from Bitcoin node to REST API

## Body

I run a Bitcoin full node. I wanted to build things on top of it. The problem: Bitcoin Core's JSON-RPC is painful to work with directly. Raw hex blobs, no analysis, no REST conventions. The alternatives aren't great either -- Esplora needs 16 CPU cores and 64GB RAM to self-host, BlockCypher charges $119/mo, and most hosted APIs rate-limit you into oblivion.

So I built Satoshi API. One command:

    pip install satoshi-api && satoshi-api

That's it. You now have a REST API wrapping your node with 41 endpoints covering blocks, transactions, fees, mempool, mining, network, and price data. It returns analyzed, structured JSON -- not raw RPC output. Fee estimates come with recommendations, transactions come decoded with input/output analysis, blocks come with summary statistics.

What makes it different:

- **Trivial to self-host.** Python package, no infra requirements beyond the node you already run. The SQLite of Bitcoin APIs.
- **MCP integration.** Ships with bitcoin-mcp so AI agents (Claude, GPT, etc.) can query your node directly. This is genuinely useful for building Bitcoin-aware AI tools.
- **L402 Lightning support.** Optional extension for Bitcoin-native pay-per-request via Lightning Network (L402 protocol).
- **Analyzed data.** Decoded transactions, fee percentile breakdowns, mempool visualization data, mining difficulty analysis. Stuff you'd otherwise compute yourself.

What it's NOT: no address indexing (that's what Electrum/Esplora are for), not multi-chain, not trying to replace block explorers. It's a clean interface to YOUR node's data.

Open source, MIT licensed. Also available hosted free at bitcoinsapi.com if you just want to kick the tires.

- GitHub: https://github.com/Bortlesboat/bitcoin-api
- PyPI: https://pypi.org/project/satoshi-api/
- Live API: https://bitcoinsapi.com
- Docs: https://bitcoinsapi.com/docs

Happy to answer questions about the architecture, Bitcoin Core RPC quirks, or the MCP integration.
