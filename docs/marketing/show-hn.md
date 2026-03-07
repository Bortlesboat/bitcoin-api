# Show HN Post Draft

## Title

Show HN: Satoshi API -- Self-hosted REST API for Bitcoin Core nodes

## Body

I run a Bitcoin full node. I wanted to build apps on top of it, but Bitcoin Core's JSON-RPC is painful: raw hex blobs, no caching, no REST conventions. The alternatives require 64GB RAM to self-host (Esplora) or cost $100+/mo (BlockCypher, GetBlock).

So I built Satoshi API:

    pip install satoshi-api && satoshi-api

That gives you 50 REST endpoints wrapping your node with analyzed, structured JSON. Fee estimates come with "send now or wait?" recommendations. Transactions come decoded with input/output analysis. The mempool gets a congestion score and fee buckets.

Stack: FastAPI + SQLite (WAL mode), runs on the same box as your node.

What makes it different:

- **Self-hosted by default.** Python package, runs wherever your node runs. The SQLite of Bitcoin APIs.
- **Analyzed data.** Fee landscape with trend analysis, mempool congestion scores, block weight utilization -- stuff you'd otherwise compute yourself from 5 RPC calls.
- **MCP integration.** Ships with bitcoin-mcp so AI agents (Claude, GPT) can query your node directly via tool calls. I haven't seen another Bitcoin API with this, but I'd love to be wrong.
- **Real-time streams.** SSE endpoints for new blocks and fee updates. No polling.

What it's NOT: not an address indexer (that's Electrum/Esplora), not multi-chain, not trying to replace block explorers. It's a clean interface to YOUR node's data.

Honest limitation: address balance lookups use `scantxoutset` which can be slow (~30s on first call for busy addresses). Results are cached, but if you need instant address lookups at scale, you still want a dedicated indexer.

Also available hosted free at bitcoinsapi.com if you want to try without a node.

- GitHub: https://github.com/Bortlesboat/bitcoin-api
- PyPI: https://pypi.org/project/satoshi-api/
- Live API: https://bitcoinsapi.com
- Docs: https://bitcoinsapi.com/docs

Happy to answer questions about the architecture, Bitcoin Core RPC quirks, or the MCP integration.
