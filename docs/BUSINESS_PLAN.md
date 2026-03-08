# Satoshi API — Business Plan

**Version:** 2.0
**Date:** March 2026
**Status:** Live — https://bitcoinsapi.com
**Release:** v0.3.2 on PyPI (`pip install satoshi-api`)
**License:** Apache-2.0

---

## Executive Summary

Satoshi API is an open-source REST API that turns any Bitcoin Core node into a developer-friendly data service. Where existing tools give developers raw RPC dumps, Satoshi API provides analyzed, structured data — fee recommendations, mempool congestion scores, block analysis — in a standard REST format with OpenAPI docs.

The product is built and production-hardened: 356 tests (335 unit + 21 e2e), 10 automated security checks with a completed penetration test, and a green CI pipeline. It runs on commodity hardware with ~$3/month operating cost. The business model is open-core: free self-hosted product drives adoption and credibility, optional hosted tiers generate recurring revenue, and the project serves as a consulting funnel for custom Bitcoin infrastructure work.

**What exists today:**
- 73 REST endpoints across 20 routers (blocks, transactions, fees, mempool, mining, network, prices, supply, stats, billing, metrics, WebSocket, and more)
- 4-tier API key auth (anonymous, free, pro, enterprise), rate limiting, caching, security hardening
- Stripe billing integration (checkout, webhooks, status, cancel)
- WebSocket + SSE real-time streaming, Prometheus metrics, circuit breaker for RPC reliability
- Docker deployment, Cloudflare Tunnel for HTTPS, SQLite (WAL mode)
- Landing page with competitor comparison pages (vs-mempool, vs-blockcypher), blog post, self-hosting guide
- Three-layer product suite: bitcoinlib-rpc (library) -> Satoshi API (REST) -> bitcoin-mcp (AI agents)
- bitcoin-mcp listed on the Anthropic MCP Registry (35 tools, 6 prompts, 7 resources)

---

## 1. Problem

Developers building Bitcoin applications face a tooling gap:

| Approach | Problem |
|----------|---------|
| **Raw RPC** | Clunky auth, inconsistent responses, no validation, no caching. Fine for scripts, painful for apps. |
| **Third-party APIs** (BlockCypher, GetBlock, QuickNode) | Rate limits, monthly fees ($49-100+), privacy concerns (they see your queries), vendor lock-in |
| **Block explorers** (mempool.space, Esplora) | Built for browsing, not building. Undocumented limits, no SLA, not designed as dev infrastructure |
| **Run your own explorer** | Overkill. Electrs/Fulcrum adds complexity, disk, and maintenance for features most apps don't need |

The gap: there's no **simple, self-hosted REST API** that gives developers analyzed Bitcoin data from their own node with zero vendor dependency.

---

## 2. Solution

**One command to go from a Bitcoin node to a production API:**

```bash
pip install satoshi-api && bitcoin-api
```

What makes Satoshi API different:

1. **Analyzed data, not raw dumps.** Fee recommendations with human-readable text, mempool congestion scoring, block analysis with median fee rates — not raw RPC output that developers have to parse themselves.

2. **AI-agent ready.** The bitcoin-mcp layer (35 tools, 6 prompts, 7 resources) lets Claude, GPT, and other AI agents query Bitcoin data via MCP tool calls. Listed on the Anthropic MCP Registry. No other Bitcoin API has this.

3. **Self-hosted by default.** Your node, your data. No third-party sees your queries. No rate limit anxiety. No monthly bill.

4. **Production-grade out of the box.** 4-tier API key auth, rate limiting with block caps, caching, input validation, structured errors with request IDs, Prometheus metrics, WebSocket streaming, Stripe billing, OpenAPI docs — all included, not bolted on.

---

## 3. Market

### 3.1 Target Segments

| Segment | Size Estimate | Need | How We Reach Them |
|---------|--------------|------|-------------------|
| **Bitcoin node operators** | ~70,000 reachable nodes globally | Clean API on their node | PyPI, r/Bitcoin, HN |
| **Bitcoin app developers** | Thousands (growing with ordinals, L2s) | Fast prototyping without running infrastructure | dev.to, r/BitcoinDev, Nostr |
| **AI agent builders** | Early but fast-growing (MCP ecosystem) | Bitcoin data for AI tools | Anthropic MCP Registry, Claude community |
| **Companies needing Bitcoin data** | Hundreds (exchanges, wallets, analytics) | Reliable, low-cost data | Direct outreach, SEO |
| **Freelance/consulting clients** | Open-ended | Custom Bitcoin tooling | "I built this, I can build for you" |

### 3.2 Market Timing

Three tailwinds make this the right time:

1. **AI agent explosion.** MCP (Model Context Protocol) is creating demand for structured data APIs that AI can consume. Bitcoin is underserved here. bitcoin-mcp is already on the Anthropic MCP Registry.
2. **Self-sovereignty movement.** Post-FTX, post-Tornado Cash — more developers want self-hosted infrastructure. "Not your node, not your data."
3. **Ordinals/inscriptions.** New developer interest in Bitcoin-native applications is at a multi-year high. These developers need APIs.

---

## 4. Product Suite

Three repositories, each independently useful, together forming a full stack:

```
bitcoinlib-rpc          Satoshi API            bitcoin-mcp
(Python library)   ->   (REST API)        ->   (AI agent interface)

pip install             pip install             pip install
bitcoinlib-rpc          satoshi-api             bitcoin-mcp

Use in scripts          Use in web apps         Use in AI agents
```

| Product | What It Does | Status |
|---------|-------------|--------|
| **bitcoinlib-rpc** | Typed Python wrapper for Bitcoin Core RPC + 6 analysis tools | v0.3.1, stable |
| **Satoshi API** | REST API with auth, caching, rate limiting, 73 endpoints across 20 routers | v0.3.2, production, live at bitcoinsapi.com |
| **bitcoin-mcp** | MCP server exposing 35 tools, 6 prompts, 7 resources for AI agents | v0.3.0, on Anthropic MCP Registry |

### 4.1 API Surface (73 endpoints across 20 routers)

| Category | Endpoints | What Developers Get |
|----------|-----------|-------------------|
| **Fees** | 3 | Fee estimates for 1-144 block targets, human-readable recommendations |
| **Mempool** | 3 | Congestion level, fee buckets, next-block minimum fee |
| **Blocks** | 3 | Block analysis (median fee rate, total fees, weight), raw stats |
| **Transactions** | 5 | Tx analysis (fees, SegWit/Taproot detection, inscriptions), decode, broadcast |
| **Mining** | 2 | Hashrate, difficulty, retarget estimate, next block template |
| **Network** | 2 | Node info, chain fork detection |
| **Status** | 2 | Health check, sync progress |
| **Supply** | 1 | Circulating supply, halving schedule, inflation rate |
| **Stats** | 3+ | UTXO set stats, SegWit adoption, OP_RETURN analysis |
| **Prices** | 3+ | Multi-exchange price data, historical rates |
| **Billing** | 4 | Stripe checkout, webhook, subscription status, cancel |
| **Metrics** | 1 | Prometheus metrics endpoint |
| **WebSocket** | 1 | Real-time subscriptions (mempool, blocks, fees) |
| **Auth/Keys** | 3+ | API key management, registration |
| **Other** | Remaining | Feature flags, decision pages, static routes |

---

## 5. Business Model

### 5.1 Revenue Streams

| Stream | Description | Status |
|--------|-------------|--------|
| **Open source adoption** | Free forever. Builds community, credibility, and SEO. | Live |
| **Hosted API subscriptions** | Managed API at bitcoinsapi.com for devs who don't want to run a node. | Live (Stripe integrated) |
| **Consulting/freelance** | Custom Bitcoin tooling, built on this stack. | Available (via Upwork, direct) |
| **Enterprise contracts** | Dedicated instances, SLA, custom endpoints. | Available on request |

### 5.2 Pricing (Hosted Tiers)

| Tier | Price | Rate Limits | Block Cap | Target |
|------|-------|-------------|-----------|--------|
| **Self-Hosted** | Free | Unlimited | Unlimited | Run on your own node |
| **Hosted Free** | $0/mo | 1,000 req/day | 144 blocks | Try before you buy |
| **Pro** | $19/mo | 100,000 req/day | 1,008 blocks | Production apps |
| **Enterprise** | Custom | Custom | 2,016 blocks | Contact us |

Stripe billing is fully integrated: checkout sessions, webhook processing, subscription status queries, and cancellation. 4-tier auth system (anonymous, free, pro, enterprise) with per-tier block caps enforced at the middleware level.

### 5.3 Unit Economics

**Cost to serve (self-hosted on existing hardware):**

| Item | Monthly |
|------|---------|
| Electricity (marginal ~15-20W) | $2 |
| Domain (bitcoinsapi.com on Cloudflare) | ~$1 |
| Cloudflare Tunnel | $0 |
| Internet (existing) | $0 |
| **Total** | **~$3/mo** |

**Break-even:** 1 Pro customer ($19/mo) covers all infrastructure costs with margin.

**At scale (cloud-hosted, if needed):**

| Item | Monthly |
|------|---------|
| VPS (4 vCPU, 8GB RAM) | $20-40 |
| Bitcoin Core node (500GB+ disk) | $20-40 |
| Domain + Cloudflare | $1 |
| **Total** | **~$50-80/mo** |

Break-even at scale: 3-4 Pro customers.

---

## 6. Competitive Landscape

| Competitor | Free Tier | Paid Entry | Self-Hostable | Our Advantage |
|-----------|-----------|------------|---------------|---------------|
| **mempool.space** | Yes (undocumented) | Enterprise (call sales) | Yes | We have analyzed data + AI integration + Stripe billing |
| **Blockstream Esplora** | Yes (~50 rps) | N/A | Yes | We have auth, rate limiting, caching, Prometheus metrics built in |
| **BlockCypher** | 1K req/day | $100/mo | No | We're self-hostable and 10x cheaper |
| **GetBlock** | 50K CU/day | $49/mo | No | We're Bitcoin-focused with better DX |
| **QuickNode** | 10M credits | $49/mo | No | We're open source, no vendor lock-in |
| **Alchemy** | 30M CU | $5/mo PAYG | No | We're Bitcoin-native (they're EVM-focused) |

**Our edge:** No one else combines all four:
1. Analyzed Bitcoin data (not raw RPC)
2. AI agent integration (MCP, on Anthropic Registry)
3. Self-hosted with one command (`pip install satoshi-api`)
4. Real-time streaming (WebSocket + SSE) with Prometheus observability

Landing pages at bitcoinsapi.com include dedicated comparison pages (vs-mempool, vs-blockcypher) for SEO and conversion.

---

## 7. Go-to-Market

### 7.1 Phase 1: Launch — COMPLETE

| Channel | Action | Status |
|---------|--------|--------|
| **PyPI** | Published `satoshi-api` + `bitcoinlib-rpc` + `bitcoin-mcp` | Done |
| **Anthropic MCP Registry** | bitcoin-mcp listed | Done |
| **Landing page** | Live at bitcoinsapi.com with comparison pages | Done |
| **Hacker News** | "Show HN: REST API for your Bitcoin node" | Pending |
| **dev.to** | Full blog post (architecture deep dive) | Pending |
| **r/BitcoinDev** | Technical announcement with examples | Pending |
| **r/Bitcoin** | Brief announcement | Pending |
| **Nostr** | Thread with curl examples | Pending |

### 7.2 Phase 2: Community (Months 1-3)

- Respond to every issue and PR
- Write "How to build X with Satoshi API" tutorials
- Monitor Bitcoin dev forums for people asking about APIs
- Iterate based on feedback (new endpoints, better docs)

### 7.3 Phase 3: Revenue (Months 3-6)

- If adoption hits 100+ GitHub stars / 50+ PyPI installs/week:
  - Promote hosted tiers (Stripe billing already integrated)
  - Add premium endpoints (historical data, webhooks)
- If consulting inquiries come in:
  - Take projects that build on this stack
  - Use delivered work to improve the open-source product

### 7.4 Phase 4: Scale (Months 6-12)

- If revenue justifies it:
  - Move to cloud-hosted Bitcoin node (dedicated)
  - Enterprise features (SLA, dedicated instances)
  - Hire part-time contributor for maintenance

---

## 8. Product Roadmap

### v0.3.2 — CURRENT RELEASE (COMPLETE)

- 73 REST endpoints across 20 routers
- 4-tier API key auth (anonymous, free, pro, enterprise) with block caps (144/1008/2016)
- Rate limiting (in-memory + Upstash Redis), TTL caching with reorg-safe depth awareness
- Stripe billing integration (checkout, webhooks, status, cancel)
- WebSocket + SSE real-time streaming
- Prometheus /metrics endpoint
- Circuit breaker for RPC reliability
- Database migrations (SQL-based runner with rollback and status)
- Docker deployment, CI/CD, Cloudflare Tunnel
- 335 unit tests + 21 e2e tests (356 total)
- 10 automated security checks, penetration test completed
- Landing page with competitor comparison pages (vs-mempool, vs-blockcypher)
- CAN-SPAM compliant, GDPR privacy policy, Terms of Service
- Published to PyPI as `satoshi-api`
- Apache-2.0 license

### v0.4 — Premium Features (Next)

- Historical fee data (time series API)
- Address watching / transaction monitoring
- Smart fee estimation (probability-based)
- Webhook subscriptions for new blocks and mempool events
- Enhanced analytics dashboard

### v0.5 — Scale & Reliability

- PostgreSQL backend option (in addition to SQLite)
- Multi-node load balancing
- Admin dashboard for hosted tier management
- Connection pooling and query optimization

### v1.0 — Enterprise

- SLA-backed enterprise tier
- Dedicated instance provisioning
- Custom endpoint development
- White-label API option

---

## 9. Growth Opportunities

Highest-potential adjacencies if the core product gains traction:

| Opportunity | Market Size | Difficulty | Fit |
|-------------|------------|------------|-----|
| **Smart fee estimation** | Large (every wallet needs this) | High | Direct extension of fee endpoints |
| **Transaction monitoring** | Large (compliance, alerts) | Medium | WebSocket infrastructure already built |
| **Mempool intelligence** | Medium (traders, miners) | Medium | Real-time data pipeline already built |
| **Ordinals/inscriptions API** | Medium (growing fast) | Medium | Aligns with prior experience |
| **Lightning Network integration** | Large (payments) | High | Separate node required |
| **AI agent marketplace** | Growing fast | Medium | bitcoin-mcp already on Anthropic Registry |

---

## 10. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Low adoption / no demand | Medium | Product stays a portfolio piece | Low cost to maintain (~$3/mo). Still valuable for consulting funnel. |
| Competitor launches similar product | Low | Reduced differentiation | First-mover in analyzed-data + MCP niche. Open source = hard to displace. |
| Bitcoin Core API changes | Very Low | Breaking changes | Pinned to stable RPC interface. bitcoinlib-rpc abstracts changes. |
| Infrastructure reliability | Low | Downtime hurts reputation | Circuit breaker + Cloudflare + Docker auto-restart + monitoring |
| Regulatory / compliance | Low | May need KYC for hosted tier | Cross that bridge when revenue justifies it. Privacy policy and ToS already in place. |
| Scaling beyond single node | Medium | Performance ceiling | v0.5 roadmap addresses this (PostgreSQL, multi-node) |

---

## 11. Current State & What's Next

### Already built and operational:
- Domain: bitcoinsapi.com (~$10/yr on Cloudflare)
- PyPI: `pip install satoshi-api` (v0.3.2)
- Stripe billing: fully integrated
- Legal: Terms of Service, Privacy Policy, CAN-SPAM compliance
- Security: 10 automated checks, pentest completed, all findings fixed
- Monitoring: Prometheus metrics, structured access logging
- MCP Registry: bitcoin-mcp listed on Anthropic MCP Registry

### To grow (next 90 days):
- Community launch (HN, dev.to, Reddit, Nostr)
- Community engagement (respond to issues, write tutorials)
- Feedback loops with early adopters
- First paying customer

### To scale (if demand warrants):
- Cloud infrastructure ($50-80/mo)
- Part-time contributor for maintenance
- Enterprise outreach

---

## 12. Key Metrics to Track

| Metric | Tool | Target (90 days) |
|--------|------|-------------------|
| GitHub stars | GitHub | 100+ |
| PyPI downloads/week | PyPI stats | 50+ |
| API requests/day (hosted) | Prometheus metrics | 1,000+ |
| Unique API key signups | SQLite DB | 20+ |
| Consulting inquiries | Email (api@bitcoinsapi.com) | 3+ |
| MRR | Stripe dashboard | $19+ (first Pro customer) |

---

## 13. Team

**Current:** Solo developer/operator.

- FP&A Analyst with Python development skills
- Bitcoin protocol knowledge (contributed to bitcoin/bitcoin, rust-bitcoin, bitcoinbook)
- Production engineering experience (Docker, CI/CD, security hardening, Stripe integration)
- Full product suite built, tested, and deployed (356 tests, 10 security checks, pentest)
- 10 automated agent "employees" for code review, security, marketing, legal, QA, and ops

**What a partner/associate could bring:**
- DevRel / community building (respond to issues, write tutorials, conference talks)
- Sales / business development (enterprise outreach, partnerships)
- Infrastructure (dedicated hosting, SLA management)
- Frontend (dashboard, developer portal, billing UI)

---

## Appendix A: Technical Architecture

```
Internet
    |
Cloudflare (HTTPS, DDoS protection, IP hiding)
    |
cloudflared tunnel (localhost relay)
    |
Satoshi API (FastAPI, port 9332)
    |-- Auth middleware (4-tier: anonymous/free/pro/enterprise)
    |-- Rate limiter (sliding window, in-memory or Upstash Redis + daily DB-backed)
    |-- Block cap enforcement (anon/free=144, pro=1008, enterprise=2016)
    |-- TTL cache (reorg-safe, per-cache locks, bounded LRU)
    |-- Circuit breaker (RPC reliability)
    |-- Prometheus metrics (counters, histograms, gauges)
    |-- WebSocket + SSE (real-time streaming via pub/sub hub)
    |-- Stripe billing (checkout, webhooks, status, cancel)
    |-- Structured access logging + usage buffer (batch writes)
    |-- Transactional email (Resend, optional)
    |-- Analytics events (PostHog, optional)
    |
SQLite (WAL mode) — API keys, usage logs, fee history, subscriptions
    |
Bitcoin Core RPC (port 8332, localhost only)
    |-- rpcwhitelist restricts to safe commands
    |-- txindex=1 for full transaction lookups
```

**Optional services (all default disabled, API fully functional without them):**
- Upstash Redis — rate limit persistence across restarts
- Resend — transactional email (key registration, notifications)
- PostHog — landing page analytics
- Stripe — subscription billing

## Appendix B: Links

- **Live API:** https://bitcoinsapi.com
- **Contact:** api@bitcoinsapi.com
- **GitHub:** github.com/Bortlesboat/bitcoin-api
- **PyPI:** pypi.org/project/satoshi-api/
- **Product Suite:**
  - bitcoinlib-rpc: github.com/Bortlesboat/bitcoinlib-rpc
  - bitcoin-mcp: github.com/Bortlesboat/bitcoin-mcp (Anthropic MCP Registry)
  - Protocol Guide: bortlesboat.github.io/bitcoin-protocol-guide

---

*This document is for internal planning. Do not share publicly without review.*
