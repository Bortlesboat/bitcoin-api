# Platform: Hacker News (Show HN)

**Suggested Title:** Show HN: Satoshi API -- "Should I send Bitcoin now or wait?" as a REST endpoint

---

**First comment (the "Show HN" comment):**

Most Bitcoin fee APIs give you a number in sat/vB. I wanted one that tells me what to actually do.

Satoshi API combines `estimatesmartfee` at multiple confirmation targets with real-time mempool state to produce a recommendation: "Fees are low. Good time to send." or "Mempool is congested. Consider waiting." Try it:

    curl https://bitcoinsapi.com/api/v1/fees/recommended

That is the core use case. There are 78 endpoints total (blocks, transactions, mempool, mining stats, address lookups, real-time SSE streams), but the fee intelligence is what is actually differentiated.

A few technical decisions that might be interesting to HN:

- **Caching is depth-aware.** Blocks with 6+ confirmations cache for an hour. Recent blocks cache for 30 seconds. Fee data refreshes every 10 seconds. This prevents stale data during reorgs without unnecessary RPC calls.
- **Rate limiting is hybrid.** Per-minute limits use an in-memory sliding window (fast, no I/O). Daily limits use SQLite (survives restarts). Both are per-API-key with tier-based thresholds.
- **RPC surface is 21 commands.** Read-only except `sendrawtransaction` behind auth. No wallet, no debug, no admin RPCs.

I also built an MCP server ([bitcoin-mcp](https://github.com/Bortlesboat/bitcoin-mcp)) so AI agents can query Bitcoin data directly. It is on the Anthropic MCP Registry and PyPI -- the first Bitcoin MCP server that talks to your local node instead of third-party APIs.

The hosted version at bitcoinsapi.com works with no signup for GET endpoints. Self-hosting is `pip install satoshi-api` -- your node, your data, no third-party dependencies.

Solo project. 335 unit tests, 21 e2e tests. Apache-2.0 license. Feedback welcome.

- GitHub: https://github.com/Bortlesboat/bitcoin-api
- Live docs: https://bitcoinsapi.com/docs
- PyPI: https://pypi.org/project/satoshi-api/
