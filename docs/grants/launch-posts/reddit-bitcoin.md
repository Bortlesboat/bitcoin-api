# r/Bitcoin Post

**Title:** I built an open-source Bitcoin fee intelligence API — tells you when to send, not just what to pay

**Subreddit:** r/Bitcoin

---

**Body:**

I've been building Satoshi API — an open-source Bitcoin API focused on fee intelligence. Instead of raw fee estimates, it gives you actionable recommendations: "Fees are low. Good time to send."

**What it does:**

- Fee recommendations that combine multiple estimatesmartfee targets with real-time mempool analysis
- 108 endpoints covering blocks, transactions, mempool, mining, network, and more
- Real-time SSE streams for new blocks and fee changes
- PSBT security analysis (catches common ordinals listing scams)
- Address balance and UTXO queries via built-in indexer

**How to use it:**

```
pip install satoshi-api
satoshi-api
# API running at http://localhost:9332
```

Or use the hosted version free at bitcoinsapi.com (1,000 req/day anonymous, 10,000 with free API key).

**For AI agents:**

I also built bitcoin-mcp — the first Bitcoin MCP server on the Anthropic Registry. It lets AI assistants (Claude, GPT, etc.) natively check fees, verify payments, and monitor addresses. 49 tools, zero config.

```
pip install bitcoin-mcp
```

**The numbers:**

- 725 tests (704 unit + 21 e2e)
- 108 endpoints across 27 routers
- Apache 2.0 licensed, self-hostable, connects to your own node
- Live production service at bitcoinsapi.com
- I also review Bitcoin Core PRs (19+ reviews)

I'm applying for an OpenSats grant to work on this more seriously — expanding the indexer, adding fee prediction, Signet support, and more SDKs.

GitHub: https://github.com/Bortlesboat/bitcoin-api
MCP Server: https://github.com/Bortlesboat/bitcoin-mcp
Live API docs: https://bitcoinsapi.com/docs

Happy to answer any questions or take feedback.
