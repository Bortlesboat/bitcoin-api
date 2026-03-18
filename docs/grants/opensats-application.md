# OpenSats Grant Application — Satoshi API Ecosystem

*Draft prepared March 18, 2026. Submit when applications reopen ~April 1, 2026.*

---

## Project Name

**Satoshi API: Bitcoin Fee Intelligence for Developers and AI Agents**

---

## One-Line Description

Open-source Bitcoin API that saves money on every transaction through fee intelligence — plus the first Bitcoin MCP server giving AI agents native Bitcoin access.

---

## Problem Statement

Bitcoin users overpay fees on virtually every transaction. The default wallet experience is "pick high/medium/low" with no context about mempool conditions, fee trends, or optimal timing. Developers building Bitcoin applications face the same problem at scale — they either run expensive infrastructure or rely on closed-source APIs with vendor lock-in.

Meanwhile, the AI agent ecosystem is exploding, but agents have zero native Bitcoin access. There's no standard way for an AI assistant to check fees, verify payments, or monitor addresses. Every developer who wants AI + Bitcoin has to build custom plumbing from scratch.

---

## Solution

The Satoshi API ecosystem solves both problems:

### 1. Satoshi API — Fee Intelligence That Saves Real Money

Instead of raw fee estimates, Satoshi API tells you *when* to send, *what* to pay, and *whether to wait*. It combines multiple `estimatesmartfee` targets with real-time mempool analysis to produce actionable recommendations like "Fees are low. Good time to send."

- **~115 endpoints** across blocks, transactions, fees, mempool, mining, network, and more
- **725 tests** (704 unit + 21 e2e) with continuous integration
- **Self-hostable** — `pip install satoshi-api` connects to your own Bitcoin Core node
- **Live production service** at bitcoinsapi.com with free tier
- **Apache 2.0** — open source forever

### 2. bitcoin-mcp — AI Agents Meet Bitcoin

The first Bitcoin MCP (Model Context Protocol) server on the official Anthropic Registry. Any AI agent — Claude, GPT, or custom — can instantly access 49 Bitcoin tools:

- Fee intelligence (recommendations, comparisons, cost estimates)
- Block and transaction analysis (with inscription detection)
- Mempool monitoring and congestion scoring
- Mining statistics and difficulty tracking
- Address balance and UTXO queries
- PSBT security analysis

**Zero config:** `pip install bitcoin-mcp` works immediately. No node required — falls back to the hosted Satoshi API. Connect your own node for full sovereignty.

### 3. BAIP-1 — Bitcoin Agent Identity Protocol

A novel protocol spec for verifiable AI agent identities anchored to Bitcoin via ordinal inscriptions. Agents can register, attest, update, and revoke cryptographic identities using Schnorr signatures (BIP-340). Includes a complete Python SDK with 61 tests.

---

## Bitcoin Impact

This project directly increases Bitcoin utility and adoption by:

1. **Saving money** — Fee intelligence helps users and applications pay optimal fees, reducing overpayment
2. **Reducing barriers** — One `pip install` gives developers a complete Bitcoin API; one `pip install` gives AI agents Bitcoin access
3. **Enabling new use cases** — AI agents with native Bitcoin tools unlock applications that don't exist yet: autonomous fee management, payment verification bots, portfolio monitoring agents
4. **Strengthening decentralization** — Self-hostable design means no single point of failure, no vendor lock-in
5. **Advancing protocol research** — BAIP-1 addresses the unsolved problem of AI agent identity on Bitcoin

---

## Open Source Compliance

All code is publicly available under permissive licenses:

| Repository | License | URL |
|-----------|---------|-----|
| Satoshi API | Apache 2.0 | github.com/Bortlesboat/bitcoin-api |
| bitcoin-mcp | MIT | github.com/Bortlesboat/bitcoin-mcp |
| BAIP-1 SDK | MIT | github.com/Bortlesboat/baip-python |
| Fee Observatory | MIT | github.com/Bortlesboat/bitcoin-fee-observatory |

All repositories include CONTRIBUTING.md, CODE_OF_CONDUCT.md, and SECURITY.md. The Satoshi API uses Developer Certificate of Origin (DCO) for all contributions.

---

## Applicant Background

**Andrew Barnes** — FP&A professional and Bitcoin developer.

### Bitcoin Contributions
- **19+ code reviews** on bitcoin/bitcoin targeting established maintainers (achow101, stickies-v, theStack)
- **~165 PRs across 30 repositories**, 33 merged — including bitcoincore.org, bitcoin-book, and major open-source projects
- **Built and shipped** Satoshi API (~115 endpoints, live production), bitcoin-mcp (49 tools, Anthropic MCP Registry), BAIP-1 (novel protocol spec), Fee Observatory
- **902 tests total** across the ecosystem — demonstrating engineering rigor

### Technical Skills
- Python (primary), FastAPI, SQLite, Bitcoin Core RPC, MCP protocol
- 5 years progressive FP&A with enterprise tooling (Tableau, NetSuite, SQL)
- Production deployment experience (Cloudflare, Docker, monitoring, CI/CD)

### Community Engagement
- Active Bitcoin Core reviewer (running changed tests locally in WSL2 before every ACK)
- Open-source contributor across the Bitcoin ecosystem
- Built tools specifically to help other developers and AI agents interact with Bitcoin

---

## Roadmap & Milestones

### Months 1–3: Foundation
- [ ] Full address indexer (mainnet) — complete transaction history for any address
- [ ] Historical fee data API — hourly/daily aggregates going back 1 year
- [ ] Official Python SDK with typed models and async support
- [ ] bitcoin-mcp v1.0 stable release (10+ additional tools)
- [ ] Signet support (full API parity with mainnet)

### Months 4–6: Intelligence
- [ ] Fee prediction model — ML-based forecasts (1hr/6hr/24hr)
- [ ] JavaScript/TypeScript SDK (npm package)
- [ ] PSBT construction and analysis endpoints
- [ ] Multi-sig wallet support
- [ ] 99.9% uptime SLA for hosted service

### Months 7–9: Ecosystem
- [ ] Ordinals/Inscriptions indexing and search
- [ ] Runes protocol support
- [ ] BAIP-1 identity verification endpoints
- [ ] Agent-to-agent payment verification
- [ ] Contributor bounty program

### Months 10–12: Scale
- [ ] Rust and Go SDKs
- [ ] Docker one-click deployment (compose + node + API)
- [ ] Plugin system for community-built endpoints
- [ ] Annual transparency report

---

## Budget

### What Grant Funding Enables

| Category | Monthly | Annual | Notes |
|----------|---------|--------|-------|
| **Developer time** | $3,000 | $36,000 | Dedicated part-time development (~20 hrs/week) |
| **Infrastructure** | $200 | $2,400 | VPS, domain, monitoring, CI/CD minutes |
| **Bitcoin node** | $50 | $600 | Dedicated full node for production API |
| **Community** | $100 | $1,200 | Bounties for contributors, documentation writers |
| **Total** | **$3,350** | **$40,200** | |

### What Has Already Been Built (Without Funding)

All existing code — 902 tests, ~115 endpoints, 49 MCP tools, BAIP-1 spec, live production service — was built without any external funding. Grant support would enable:

1. **Dedicated development time** — Currently built in evenings/weekends alongside full-time employment
2. **Faster iteration** — Roadmap items that would take 12 months could be completed in 6
3. **Community building** — Contributor bounties, documentation, outreach
4. **Infrastructure reliability** — Dedicated hosting for 99.9% uptime

---

## Why This Project Is Not Readily Funded

1. **No VC path** — Open-source Bitcoin infrastructure doesn't generate VC-scale returns
2. **Too niche for general grants** — Requires Bitcoin domain expertise to evaluate
3. **Novel intersection** — AI agents + Bitcoin is too new for established funding categories
4. **Solo developer** — No company entity, no marketing budget, no institutional backing

OpenSats is uniquely positioned to fund this because it understands Bitcoin infrastructure value and supports individual contributors building public goods.

---

## Sustainability Plan

After the grant period, the project sustains through:

1. **Pro tier revenue** — Commercial users with higher rate limits fund ongoing hosting
2. **Self-hosting model** — Core API is free forever; hosting is the paid product
3. **Community contributions** — Plugin system enables community-maintained extensions
4. **Reduced maintenance cost** — Once built, the API requires minimal maintenance (Bitcoin Core RPC is stable)

The goal is for Pro tier revenue to cover infrastructure costs within 12 months, making the project self-sustaining while keeping all code open source.

---

## Links

- **Live API:** https://bitcoinsapi.com
- **API Documentation:** https://bitcoinsapi.com/docs
- **GitHub (Satoshi API):** https://github.com/Bortlesboat/bitcoin-api
- **GitHub (bitcoin-mcp):** https://github.com/Bortlesboat/bitcoin-mcp
- **GitHub (BAIP-1):** https://github.com/Bortlesboat/baip-python
- **PyPI (Satoshi API):** https://pypi.org/project/satoshi-api/
- **PyPI (bitcoin-mcp):** https://pypi.org/project/bitcoin-mcp/
- **MCP Registry:** https://registry.modelcontextprotocol.io (search "bitcoin")
- **Roadmap:** https://github.com/Bortlesboat/bitcoin-api/blob/master/docs/ROADMAP.md
