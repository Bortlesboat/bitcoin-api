# Satoshi API — Business Plan

**Version:** 1.0
**Date:** March 2026
**Status:** Live — https://bitcoinsapi.com

---

## Executive Summary

Satoshi API is an open-source REST API that turns any Bitcoin Core node into a developer-friendly data service. Where existing tools give developers raw RPC dumps, Satoshi API provides analyzed, structured data — fee recommendations, mempool congestion scores, block analysis — in a standard REST format with OpenAPI docs.

The product is built and production-hardened (175 unit tests, 21 e2e tests (196 total), 9/9 security checks, CI pipeline green). It runs on commodity hardware with ~$3/month operating cost. The business model is open-core: free self-hosted product drives adoption and credibility, optional hosted tiers generate recurring revenue, and the project serves as a consulting funnel for custom Bitcoin infrastructure work.

**What exists today:**
- 60 REST endpoints across 19 routers (blocks, transactions, fees, mempool, mining, network, prices, status)
- Tiered API key auth, rate limiting, caching, security hardening
- Docker deployment, Cloudflare Tunnel for HTTPS
- Landing page, blog post, self-hosting guide
- Three-layer product suite: bitcoinlib-rpc (library) -> Satoshi API (REST) -> bitcoin-mcp (AI agents)

**What we're asking:** Feedback on go-to-market strategy, potential partnership opportunities, and whether there's appetite to build this into a revenue-generating product vs. keeping it as a portfolio/consulting piece.

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
pip install bitcoin-api && bitcoin-api
```

What makes Satoshi API different:

1. **Analyzed data, not raw dumps.** Fee recommendations with human-readable text, mempool congestion scoring, block analysis with median fee rates — not raw RPC output that developers have to parse themselves.

2. **AI-agent ready.** The bitcoin-mcp layer lets Claude, GPT, and other AI agents query Bitcoin data via MCP tool calls. No other Bitcoin API has this.

3. **Self-hosted by default.** Your node, your data. No third-party sees your queries. No rate limit anxiety. No monthly bill.

4. **Production-grade out of the box.** API key auth, rate limiting, caching, input validation, structured errors with request IDs, OpenAPI docs — all included, not bolted on.

---

## 3. Market

### 3.1 Target Segments

| Segment | Size Estimate | Need | How We Reach Them |
|---------|--------------|------|-------------------|
| **Bitcoin node operators** | ~70,000 reachable nodes globally | Clean API on their node | PyPI, r/Bitcoin, HN |
| **Bitcoin app developers** | Thousands (growing with ordinals, L2s) | Fast prototyping without running infrastructure | dev.to, r/BitcoinDev, Nostr |
| **AI agent builders** | Early but fast-growing (MCP ecosystem) | Bitcoin data for AI tools | MCP directories, Claude community |
| **Companies needing Bitcoin data** | Hundreds (exchanges, wallets, analytics) | Reliable, low-cost data | Direct outreach, SEO |
| **Freelance/consulting clients** | Open-ended | Custom Bitcoin tooling | "I built this, I can build for you" |

### 3.2 Market Timing

Three tailwinds make this the right time:

1. **AI agent explosion.** MCP (Model Context Protocol) is creating demand for structured data APIs that AI can consume. Bitcoin is underserved here.
2. **Self-sovereignty movement.** Post-FTX, post-Tornado Cash — more developers want self-hosted infrastructure. "Not your node, not your data."
3. **Ordinals/inscriptions.** New developer interest in Bitcoin-native applications is at a multi-year high. These developers need APIs.

---

## 4. Product Suite

Three repositories, each independently useful, together forming a full stack:

```
bitcoinlib-rpc          Satoshi API            bitcoin-mcp
(Python library)   ->   (REST API)        ->   (AI agent interface)

pip install             pip install             Add to Claude Desktop
bitcoinlib-rpc          bitcoin-api             config

Use in scripts          Use in web apps         Use in AI agents
```

| Product | What It Does | Status |
|---------|-------------|--------|
| **bitcoinlib-rpc** | Typed Python wrapper for Bitcoin Core RPC + 6 analysis tools | v0.3.1, stable |
| **Satoshi API** | REST API with auth, caching, rate limiting, 60 endpoints | v0.3.1, production-ready |
| **bitcoin-mcp** | MCP server exposing 20 tools for AI agents | v0.3.1, tested |

### 4.1 API Endpoints (19)

| Category | Endpoints | What Developers Get |
|----------|-----------|-------------------|
| **Fees** | 3 | Fee estimates for 1-144 block targets, human-readable recommendations |
| **Mempool** | 3 | Congestion level, fee buckets, next-block minimum fee |
| **Blocks** | 3 | Block analysis (median fee rate, total fees, weight), raw stats |
| **Transactions** | 5 | Tx analysis (fees, SegWit/Taproot detection, inscriptions), decode, broadcast |
| **Mining** | 2 | Hashrate, difficulty, retarget estimate, next block template |
| **Network** | 2 | Node info, chain fork detection |
| **Status** | 2 | Health check, sync progress |

---

## 5. Business Model

### 5.1 Revenue Streams

| Stream | Description | Timeline |
|--------|-------------|----------|
| **Open source adoption** | Free forever. Builds community, credibility, and SEO. | Now |
| **Hosted API subscriptions** | Managed API for devs who don't want to run a node. | When demand appears |
| **Consulting/freelance** | Custom Bitcoin tooling, built on this stack. | Now (via Upwork, direct) |
| **Enterprise contracts** | Dedicated instances, SLA, custom endpoints. | 6-12 months |

### 5.2 Pricing (Hosted Tiers)

| Tier | Price | Limits | Target |
|------|-------|--------|--------|
| Free | $0/mo | 1,000 req/day, read-only | Try before you buy |
| Builder | $9/mo | 10,000 req/day, POST access | Side projects |
| Pro | $29/mo | 100,000 req/day, priority | Production apps |
| Enterprise | Custom | Unlimited, SLA, dedicated | Contact us |

**Launch strategy:** Free + open source only. No Stripe integration until there's actual demand. Don't build billing for zero customers.

### 5.3 Unit Economics

**Cost to serve (self-hosted on existing hardware):**

| Item | Monthly |
|------|---------|
| Electricity (marginal ~15-20W) | $2 |
| Domain (.dev) | $1 |
| Cloudflare Tunnel | $0 |
| Internet (existing) | $0 |
| **Total** | **~$3/mo** |

**Break-even:** 1 Builder customer ($9/mo) covers all infrastructure costs.

**At scale (cloud-hosted, if needed):**

| Item | Monthly |
|------|---------|
| VPS (4 vCPU, 8GB RAM) | $20-40 |
| Bitcoin Core node (500GB+ disk) | $20-40 |
| Domain + Cloudflare | $1 |
| **Total** | **~$50-80/mo** |

Break-even at scale: 2-3 Pro customers or 6-9 Builder customers.

---

## 6. Competitive Landscape

| Competitor | Free Tier | Paid Entry | Self-Hostable | Our Advantage |
|-----------|-----------|------------|---------------|---------------|
| **mempool.space** | Yes (undocumented) | Enterprise (call sales) | Yes | We have analyzed data + AI integration |
| **Blockstream Esplora** | Yes (~50 rps) | N/A | Yes | We have auth, rate limiting, caching built in |
| **BlockCypher** | 1K req/day | $100/mo | No | We're self-hostable and 10x cheaper |
| **GetBlock** | 50K CU/day | $49/mo | No | We're Bitcoin-focused with better DX |
| **QuickNode** | 10M credits | $49/mo | No | We're open source, no vendor lock-in |
| **Alchemy** | 30M CU | $5/mo PAYG | No | We're Bitcoin-native (they're EVM-focused) |

**Our edge:** No one else combines all three:
1. Analyzed Bitcoin data (not raw RPC)
2. AI agent integration (MCP)
3. Self-hosted with one command (`pip install`)

We're not competing on hosted infrastructure scale. We're competing on developer experience for the self-sovereign niche.

---

## 7. Go-to-Market

### 7.1 Phase 1: Launch (Weeks 1-2)

| Channel | Action | Expected Outcome |
|---------|--------|-----------------|
| **PyPI** | Publish `bitcoin-api` + `bitcoinlib-rpc` | Discoverability via pip |
| **Hacker News** | "Show HN: REST API for your Bitcoin node" | 50-200 GitHub stars, early adopter feedback |
| **dev.to** | Full blog post (architecture deep dive) | SEO, developer credibility |
| **r/BitcoinDev** | Technical announcement with examples | Targeted developer audience |
| **r/Bitcoin** | Brief announcement | Broader awareness |
| **Nostr** | Thread with curl examples | Bitcoin-native community |
| **MCP directories** | PR to modelcontextprotocol/servers, Smithery, MCP Hub | AI developer discovery |

### 7.2 Phase 2: Community (Months 1-3)

- Respond to every issue and PR
- Write "How to build X with Satoshi API" tutorials
- Monitor Bitcoin dev forums for people asking about APIs
- Iterate based on feedback (new endpoints, better docs)

### 7.3 Phase 3: Revenue (Months 3-6)

- If adoption hits 100+ GitHub stars / 50+ PyPI installs/week:
  - Launch hosted tier with Stripe
  - Add premium endpoints (historical data, webhooks)
- If consulting inquiries come in:
  - Take projects that build on this stack
  - Use delivered work to improve the open-source product

### 7.4 Phase 4: Scale (Months 6-12)

- If revenue justifies it:
  - Move to cloud-hosted Bitcoin node (dedicated)
  - Add WebSocket/SSE for real-time data
  - Enterprise features (SLA, dedicated instances)
  - Hire part-time contributor for maintenance

---

## 8. Product Roadmap

### v0.3.1 — COMPLETE

- 60 REST endpoints, 19 routers
- API key auth (4 tiers), rate limiting, caching
- Docker, CI/CD, security hardening
- 175 unit tests + 21 e2e tests (196 total)
- Landing page, blog post, self-hosting guide

### v0.2 — Scalability & Observability (Month 1-2)

- Prometheus `/metrics` endpoint
- Batch usage log writes
- Idempotency keys for POST endpoints
- Database migrations (Alembic)

### v0.3 — Real-Time (Month 3-4)

- WebSocket endpoint for mempool fee updates
- Webhook subscriptions for new blocks
- Server-Sent Events for chain tip changes

### v0.4 — Premium Features (Month 5-6)

- Historical fee data (time series)
- Address watching / transaction monitoring
- Smart fee estimation (probability-based)

### v1.0 — Enterprise (Month 6-12)

- PostgreSQL backend option
- Multi-node load balancing
- Admin dashboard
- Stripe billing integration

---

## 9. Growth Opportunities

Highest-potential adjacencies if the core product gains traction:

| Opportunity | Market Size | Difficulty | Fit |
|-------------|------------|------------|-----|
| **Smart fee estimation** | Large (every wallet needs this) | High | Direct extension of fee endpoints |
| **Transaction monitoring** | Large (compliance, alerts) | Medium | Webhook infrastructure needed |
| **Mempool intelligence** | Medium (traders, miners) | Medium | Real-time data pipeline |
| **Ordinals/inscriptions API** | Medium (growing fast) | Medium | Aligns with prior experience |
| **Lightning Network integration** | Large (payments) | High | Separate node required |

---

## 10. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Low adoption / no demand | Medium | Product stays a portfolio piece | Low cost to maintain. Still valuable for consulting funnel. |
| Competitor launches similar product | Low | Reduced differentiation | First-mover in analyzed-data + MCP niche. Open source = hard to displace. |
| Bitcoin Core API changes | Very Low | Breaking changes | Pinned to stable RPC interface. bitcoinlib-rpc abstracts changes. |
| Infrastructure reliability | Medium | Downtime hurts reputation | Cloudflare + Docker auto-restart + UptimeRobot monitoring |
| Regulatory / compliance | Low | May need KYC for hosted tier | Cross that bridge when revenue justifies it |
| Scaling beyond single node | Medium | Performance ceiling | v0.4 roadmap addresses this (PostgreSQL, multi-node) |

---

## 11. What We Need

### To launch (immediate):
- Domain name (~$10/yr)
- PyPI account (free)
- 2 hours to push the button

### To grow (first 90 days):
- Community engagement (respond to issues, write tutorials)
- Feedback loops with early adopters
- Decision: pursue hosted revenue or keep as portfolio/consulting piece?

### To scale (if demand warrants):
- Cloud infrastructure ($50-80/mo)
- Stripe integration for billing
- Part-time contributor for maintenance
- ~~Legal: Terms of service, privacy policy~~ DONE (v0.3.1)

---

## 12. Key Metrics to Track

| Metric | Tool | Target (90 days) |
|--------|------|-------------------|
| GitHub stars | GitHub | 100+ |
| PyPI downloads/week | PyPI stats | 50+ |
| API requests/day (hosted) | Application logs | 1,000+ |
| Unique API key signups | SQLite DB | 20+ |
| Consulting inquiries | Email | 3+ |
| MRR | Stripe (when launched) | $0 (revenue comes later) |

---

## 13. Team

**Current:** Solo developer/operator.

- FP&A Analyst with Python development skills
- Bitcoin protocol knowledge (contributed to bitcoin/bitcoin, rust-bitcoin, bitcoinbook)
- Production engineering experience (Docker, CI/CD, security hardening)
- Full product suite built and tested

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
    |-- Auth middleware (API key via X-API-Key header)
    |-- Rate limiter (sliding window per-minute + daily DB-backed)
    |-- TTL cache (reorg-safe, per-cache locks)
    |-- Structured access logging
    |
Bitcoin Core RPC (port 8332, localhost only)
    |-- rpcwhitelist restricts to 17 safe commands
    |-- txindex=1 for full transaction lookups
```

## Appendix B: Links

- **GitHub:** github.com/Bortlesboat/bitcoin-api
- **Landing Page:** bortlesboat.github.io/bitcoin-api
- **Blog Post:** (to be published on dev.to at launch)
- **Product Suite:**
  - bitcoinlib-rpc: github.com/Bortlesboat/bitcoinlib-rpc
  - bitcoin-mcp: github.com/Bortlesboat/bitcoin-mcp
  - Protocol Guide: bortlesboat.github.io/bitcoin-protocol-guide

---

*This document is for internal discussion. Do not share publicly without review.*
