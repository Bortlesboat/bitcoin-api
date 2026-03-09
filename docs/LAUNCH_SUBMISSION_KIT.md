# Satoshi API — Launch Directory Submission Kit

Use this for: DevHunt, BetaList, Peerlist, Indie Hackers, AlternativeTo, SaaSHub, awesome-lists.

---

## One-Liner (under 80 chars)

> Bitcoin fee intelligence API — know when to send, save money every time.

---

## Short Description (2-3 sentences)

Satoshi API is the first Bitcoin MCP server on the Anthropic Registry. It gives AI agents and developers fee intelligence that saves money on every Bitcoin transaction — not just fee rates, but "send now or wait?" recommendations with mempool context. Free, open source, self-hostable.

---

## Long Description (1 paragraph)

Bad fee timing burns sats on every Bitcoin transaction. Satoshi API combines multiple fee estimation targets with real-time mempool state to tell you exactly when to send and what to pay. Instead of calling `estimatesmartfee` five times and doing math, you get a single endpoint that says "Fees are low. Good time to send." — saving money on every transaction. It's the first Bitcoin API on the Anthropic MCP Registry, meaning AI agents like Claude and ChatGPT can check fees, verify payments, and monitor addresses without human intervention. Install with `pip install satoshi-api`, point it at your Bitcoin Core node, and you're running in 60 seconds. Self-hostable at $0/month, or use the free hosted tier at bitcoinsapi.com with no signup required. Apache-2.0 licensed, 421 tests, built by a Bitcoin Core contributor.

---

## Key Features (5 bullets — each saves money, saves time, or makes money)

1. **Fee intelligence that saves money** — "Send now or wait?" recommendations with mempool context. Every time you wait instead of overpaying = sats saved.
2. **AI-native via MCP** — First Bitcoin MCP server on the Anthropic Registry. Your AI agents check fees, verify payments, and broadcast transactions — no human babysitting.
3. **Self-hostable at $0/month** — Your node, your data, your API. Competitors charge $49-100/mo. Apache-2.0 licensed, no vendor lock-in.
4. **60-second setup** — `pip install satoshi-api && satoshi-api`. One command install, one command run. Saves hours of Bitcoin RPC plumbing.
5. **Real-time streaming** — SSE + WebSocket feeds for fees and new blocks. Build alerting, dashboards, or trading signals without polling.

---

## Categories / Tags

**Primary categories:** Developer Tools, API, Cryptocurrency, Bitcoin, Open Source
**Secondary categories:** AI/ML Tools, Infrastructure, Fintech, DevOps
**Tags:** bitcoin, api, mcp, ai-agents, fee-estimation, open-source, self-hosted, python, fastapi, mempool, blockchain, developer-tools, rest-api, cryptocurrency

---

## URLs

| Resource | URL |
|----------|-----|
| Website | https://bitcoinsapi.com |
| GitHub | https://github.com/Bortlesboat/bitcoin-api |
| Interactive Docs (Swagger) | https://bitcoinsapi.com/docs |
| PyPI | https://pypi.org/project/satoshi-api/ |
| MCP Server (companion) | https://github.com/Bortlesboat/bitcoin-mcp |
| Discord Bot | https://github.com/Bortlesboat/satoshi-discord-bot |
| Status Page | https://stats.uptimerobot.com/satoshi-api |
| Discord Community | https://discord.gg/EB6Jd66EsF |

---

## Pricing

| Tier | Price | Details |
|------|-------|---------|
| **Self-Hosted** | Free forever | Full API, unlimited requests, your own node. Apache-2.0. |
| **Hosted Free** | $0/mo | 1,000 requests/day, all GET endpoints, no signup needed. |
| **Pro** | $19/mo | 100,000 requests/day, 500 req/min, POST access, priority support. |

---

## Screenshot Descriptions (what to capture)

1. **Hero + live fee data** — Landing page hero section showing the live fee response JSON updating in real time. Captures the "ask Claude about Bitcoin" conversation mockup. Best for primary listing image.

2. **Swagger docs** — `/docs` page showing the interactive API documentation with endpoint categories expanded (fees, blocks, transactions). Shows the developer experience.

3. **Fee recommendation response** — Terminal/curl output of `GET /api/v1/fees/recommended` showing the `"recommendation": "Fees are low. Good time to send."` JSON response. The money shot.

4. **MCP in action** — Claude Desktop with bitcoin-mcp installed, showing a natural language query like "Should I send Bitcoin now?" with Claude's fee-informed response. Demonstrates the AI agent use case.

5. **Pricing section** — Landing page pricing cards showing Free / Pro tiers. Clean, simple, shows the value prop of self-hosting at $0.

---

## Platform-Specific Notes

**DevHunt:** Lead with "First Bitcoin MCP server on the Anthropic Registry" — the AI angle is novel here.

**BetaList:** Emphasize the free tier and open source nature. BetaList audience loves trying things without commitment.

**Peerlist:** Developer-focused. Highlight the `pip install` simplicity and 421 test count. Link to GitHub prominently.

**Indie Hackers:** Solo builder story — built by a Bitcoin Core contributor and FP&A analyst. Self-hosted = $0 infra cost narrative resonates.

**AlternativeTo:** Position as alternative to mempool.space API (block explorer) and BlockCypher (paid API). Differentiator: fee intelligence + AI agent support + self-hostable.

**SaaSHub:** Compare against: mempool.space, BlockCypher, Blockchain.com API, Bitcore. Category: Cryptocurrency API.

**awesome-lists:** Target `awesome-bitcoin`, `awesome-mcp-servers`, `awesome-fastapi`, `awesome-selfhosted`. Keep description to one line.

---

## Version Info

- Current version: v0.3.3
- Python: 3.10+
- License: Apache-2.0
- Tests: 421 (400 unit + 21 e2e)
