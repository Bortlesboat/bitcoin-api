# Show HN Post

**Title:** Show HN: Satoshi API – Open-source Bitcoin fee intelligence API (~115 endpoints, self-hostable)

---

**Body:**

Hi HN, I built Satoshi API — an open-source REST API that wraps Bitcoin Core with fee intelligence.

Instead of raw fee estimates ("4 sat/vB"), it tells you: "Fees are low. Good time to send. You'd save 50% waiting 3 blocks."

**Quick start:**
```
pip install satoshi-api
satoshi-api  # runs on :9332, connects to your Bitcoin Core node
```

Or use the hosted version free: https://bitcoinsapi.com/docs

**What makes it different from mempool.space or Blockstream's API:**

- Fee *recommendations*, not just estimates — combines multiple `estimatesmartfee` targets with real-time mempool depth
- Self-hostable with one `pip install` — no Docker, no config files
- First Bitcoin MCP server on the Anthropic Registry — AI agents can natively check fees, verify payments, monitor addresses (49 tools, zero config: `pip install bitcoin-mcp`)
- 725 tests, Apache 2.0

**Tech stack:** Python, FastAPI, SQLite (WAL), Bitcoin Core RPC. Optional: Redis, Stripe, Resend. Circuit breaker for RPC failover, per-cache locking, sliding window rate limiting.

**Numbers:** ~115 endpoints, 28 routers, 725 tests, 900+ PyPI downloads/month across both packages. Live at bitcoinsapi.com.

I'm a Bitcoin Core reviewer (19+ reviews) and FP&A analyst by day. Built this evenings/weekends. Applying for an OpenSats grant to go deeper — indexer expansion, fee prediction, more SDKs.

Source: https://github.com/Bortlesboat/bitcoin-api
MCP server: https://github.com/Bortlesboat/bitcoin-mcp

Happy to discuss the architecture, fee algorithm, or anything else.
