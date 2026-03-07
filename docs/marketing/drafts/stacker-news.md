# Platform: stacker.news

**Suggested Title:** Your full node already has the data -- you just need a better interface

---

Running a full node is sovereign. Querying someone else's API to read your own blockchain data is not.

I kept building small tools on top of Bitcoin Core and hitting the same friction: fee estimates with no context, mempool data scattered across multiple RPC calls, caching that breaks near the tip because of reorgs. So I built Satoshi API -- an open-source REST layer that sits on top of your node and handles the annoying parts.

`pip install satoshi-api` and you have 60 endpoints wrapping your node in structured JSON. Apache-2.0 licensed. Everything stays local.

**What's actually useful about it:**

- Fee recommendations with plain-English context ("send now" vs "wait 2 blocks"), not just raw sat/vB
- Mempool congestion scoring so you know if now is a good time to transact
- Real-time SSE streams for new blocks and fee changes -- no polling
- Address lookups via `scantxoutset` (no Electrs/Esplora dependency)

**What it's NOT:** Not an address indexer. If you need full address history at scale, you still want Electrs or Esplora. This is for querying what your node already knows, with a clean interface and depth-aware caching.

**Self-hosting is the entire point.** Docker supported. Rate limiting and API keys built in if you want to share on your LAN or expose through a tunnel. There's a free hosted version at bitcoinsapi.com for trying it, but the real use case is your node, your API, your data.

- **GitHub:** https://github.com/Bortlesboat/bitcoin-api
- **Install:** `pip install satoshi-api`

What else would you want from a self-hosted API layer on your node? I'm prioritizing based on what people actually need.
