# r/BitcoinDev Post

**Title:** Open-source Bitcoin API + MCP server for AI agents — feedback welcome

**Subreddit:** r/BitcoinDev (more technical audience)

---

**Body:**

I've been building two complementary tools and would appreciate feedback from other Bitcoin developers:

**1. Satoshi API** — Bitcoin REST API focused on fee intelligence

- Wraps Bitcoin Core RPC with a clean REST interface
- Fee recommendations that combine multiple `estimatesmartfee` targets with mempool depth analysis
- 108 endpoints: blocks, transactions, fees, mempool, mining, network, streams (SSE), address lookups, PSBT analysis
- Built with FastAPI, SQLite (WAL), per-cache locking, circuit breaker for RPC failover
- 725 tests, CI/CD, Apache 2.0
- Self-hostable: `pip install satoshi-api && satoshi-api`

Architecture details: https://github.com/Bortlesboat/bitcoin-api/blob/main/docs/ARCHITECTURE.md

**2. bitcoin-mcp** — MCP server giving AI agents Bitcoin access

- 49 tools covering fee intelligence, block/tx analysis, mempool monitoring, mining stats, address queries
- 6 built-in prompts, 7 resources for context injection
- Zero-config: falls back to hosted Satoshi API when no local node available
- First Bitcoin MCP server on the Anthropic Registry
- 116 tests, MIT licensed
- `pip install bitcoin-mcp`

**What I'm looking for:**

- Missing endpoints that developers actually need
- Feedback on the fee recommendation algorithm (currently combines multiple confirmation targets with mempool pressure scoring)
- Ideas for the indexer — currently supports address balance/history, considering ordinals/runes indexing
- Whether the MCP tool interface makes sense for agent use cases

**Background:** I review Bitcoin Core PRs (19+ reviews, targeting achow101/stickies-v/theStack's work) and built BAIP-1 (Bitcoin Agent Identity Protocol — verifiable agent identities via ordinal inscriptions).

GitHub: https://github.com/Bortlesboat/bitcoin-api
MCP: https://github.com/Bortlesboat/bitcoin-mcp
BAIP-1: https://github.com/Bortlesboat/baip-python
