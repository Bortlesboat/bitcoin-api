# Platform: Hacker News (Show HN)

**Suggested Title:** Show HN: Satoshi API -- Open-source REST API for Bitcoin Core (Python/FastAPI)

---

**First comment (the "Show HN" comment):**

Satoshi API wraps Bitcoin Core's JSON-RPC in a REST interface with 54 endpoints. `pip install satoshi-api`, set your RPC credentials, and you have a local API on port 9332.

I built this because every Bitcoin app I worked on ended up reimplementing the same layer: fee estimation with human-readable context, mempool congestion analysis, block lookups that handle both height and hash, reorg-aware caching. This packages all of that into a single install.

A few technical decisions that might be interesting:

- **Caching is depth-aware.** Blocks with 6+ confirmations cache for an hour. Recent blocks cache for 30 seconds. Fee data refreshes every 10 seconds. This prevents stale data during reorgs without unnecessary RPC calls.
- **Rate limiting is hybrid.** Per-minute limits use an in-memory sliding window (fast, no I/O). Daily limits use SQLite (survives restarts). Both are per-API-key with tier-based thresholds.
- **RPC surface is whitelisted.** The API only calls 17 read-only RPC commands (plus `sendrawtransaction` behind auth). No wallet, no debug, no admin RPCs.

I also built an MCP server ([bitcoin-mcp](https://github.com/Bortlesboat/bitcoin-mcp)) so AI agents can query Bitcoin data via Model Context Protocol. This is probably niche, but I have not seen another Bitcoin API that supports it.

The hosted version at bitcoinsapi.com has a free tier (no signup for GET endpoints). But the main use case is self-hosting -- your node, your data, no third-party dependencies.

Solo project. 129 unit tests, 21 e2e tests. Apache-2.0 license. Feedback appreciated.

- GitHub: https://github.com/Bortlesboat/bitcoin-api
- Live docs: https://bitcoinsapi.com/docs
- PyPI: https://pypi.org/project/satoshi-api/
