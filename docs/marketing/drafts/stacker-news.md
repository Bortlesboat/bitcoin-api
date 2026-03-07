# Platform: stacker.news

**Suggested Title:** Satoshi API: REST API for your Bitcoin node with AI agent support

---

I built an open-source REST API that wraps your Bitcoin Core node in 42 clean endpoints. It is called Satoshi API. MIT licensed, self-hosted, no third parties.

**Why it exists:** Running a full node is sovereign. Querying someone else's API to read your own blockchain data is not. Satoshi API keeps everything local -- install it, point it at your node, and you have a full REST API without any data leaving your machine.

**What it does:**

- Fee recommendations with plain-English context, not just raw sat/vB numbers
- Mempool congestion scoring so you know if now is a good time to send
- Block and transaction analysis with structured JSON responses
- Real-time SSE streams for new blocks and fee changes
- Address balance lookups via `scantxoutset` (no Electrs dependency)
- Transaction broadcast with pre-validation

**Self-hosting is the primary use case.** `pip install satoshi-api` and you are live. Docker also supported. Rate limiting and API keys are built in if you want to share it on your LAN or expose it through a Cloudflare Tunnel.

**AI agent support (MCP).** I also built a companion MCP server ([bitcoin-mcp](https://github.com/Bortlesboat/bitcoin-mcp)) that lets AI assistants query your node through Model Context Protocol. This means Claude, GPT, or any MCP-compatible agent can look up blocks, check fees, and analyze transactions on your sovereign node. As far as I know, this is the only Bitcoin API with MCP integration.

The hosted version at bitcoinsapi.com is free to try (no signup for read endpoints), but the real point is self-hosting. Your node, your API, your data.

Built by a Bitcoin Core contributor. Feedback welcome.

- **GitHub:** https://github.com/Bortlesboat/bitcoin-api
- **Live demo:** https://bitcoinsapi.com/docs
- **Install:** `pip install satoshi-api`
- **Contact:** api@bitcoinsapi.com
