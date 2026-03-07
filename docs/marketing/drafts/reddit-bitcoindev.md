# Platform: r/BitcoinDev

**Suggested Title:** Satoshi API: open-source REST wrapper for Bitcoin Core RPC (42 endpoints, pip install)

---

I built a REST API layer over Bitcoin Core's JSON-RPC and wanted to share it with this community for feedback.

**The problem:** Bitcoin Core's RPC is powerful but rough for application development. Fee estimates come back as raw sat/vB numbers with no context. Mempool data requires multiple calls to piece together. Block data needs hash-to-height lookups you have to manage yourself. Every app I built ended up reimplementing the same translation layer.

**What Satoshi API does:** It wraps 17 whitelisted RPC commands into 42 REST endpoints that return analyzed, structured data. A few things I think are worth discussing:

- **Depth-aware caching.** Blocks deeper than 6 confirmations get long TTLs. Recent blocks get short TTLs. Fee and mempool data refresh every 10-30 seconds. This avoids stale data during reorgs without hammering the node.
- **Fee landscape endpoint.** `/fees/landscape` combines `estimatesmartfee` at multiple targets with mempool size and recent block fullness to give a "send now or wait?" recommendation. Opinionated, but useful for wallets.
- **Reorg safety.** Every response includes `meta.node_height` and `meta.syncing` (triggered when `verificationprogress < 0.9999`), so clients know if they are looking at IBD data.
- **RPC whitelist.** The API only calls 17 read-only commands (plus `sendrawtransaction` behind auth). No wallet RPCs, no debug RPCs.

The stack is Python/FastAPI with sliding-window rate limiting and SQLite for usage logging. Runs on port 9332 alongside your node.

I also built an MCP server ([bitcoin-mcp](https://github.com/Bortlesboat/bitcoin-mcp)) so AI agents can query the API directly via Model Context Protocol. This is probably the part I am least sure about in terms of demand -- would appreciate thoughts on whether agent-accessible Bitcoin data is something people actually want.

This is a new project and I am a single developer. I would genuinely appreciate feedback on the API design, the caching strategy, or anything that looks wrong.

- **GitHub:** https://github.com/Bortlesboat/bitcoin-api
- **Live interactive docs:** https://bitcoinsapi.com/docs
- **Install:** `pip install satoshi-api`
- **License:** MIT
