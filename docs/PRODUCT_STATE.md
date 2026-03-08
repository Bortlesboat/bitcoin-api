# Satoshi API -- Product State Document

**Prepared by:** Product Manager (Agent)
**Date:** 2026-03-07
**Version:** 1.0
**Status:** Board-Ready

---

## STAGE 1: CURRENT -- Launch Ready

Everything below is built, tested, deployed, and live at https://bitcoinsapi.com.

### 1.1 Core API Endpoints (76 total across 20 routers)

| Category | Count | Key Endpoints | Auth Required |
|----------|-------|---------------|---------------|
| **Status & Health** | 4 | `/health`, `/health/deep`, `/status`, `/healthz` | deep = free+ |
| **Blocks** | 9 | `/blocks/latest`, `/blocks/{height_or_hash}`, `/blocks/{hash}/txids`, `/blocks/{hash}/txs`, `/blocks/{hash}/header`, `/blocks/{hash}/raw`, `/blocks/{height}/stats`, `/blocks/tip/height`, `/blocks/tip/hash` | No |
| **Transactions** | 9 | `/tx/{txid}`, `/tx/{txid}/raw`, `/tx/{txid}/hex`, `/tx/{txid}/status`, `/tx/{txid}/outspends`, `/tx/{txid}/merkle-proof`, `/utxo/{txid}/{vout}`, `/decode` (POST), `/broadcast` (POST) | POST = free+ |
| **Fees** | 7 | `/fees`, `/fees/recommended`, `/fees/mempool-blocks`, `/fees/landscape`, `/fees/estimate-tx`, `/fees/history`, `/fees/{target}` | No |
| **Mempool** | 5 | `/mempool`, `/mempool/info`, `/mempool/tx/{txid}`, `/mempool/txids`, `/mempool/recent` | No |
| **Mining** | 7 | `/mining`, `/mining/nextblock`, `/mining/hashrate/history`, `/mining/revenue`, `/mining/pools`, `/mining/difficulty/history`, `/mining/revenue/history` | No |
| **Network** | 4 | `/network`, `/network/forks`, `/network/difficulty`, `/network/validate-address/{addr}` | No (version redacted for anon) |
| **Prices** | 1 | `/prices` (CoinGecko-sourced, attributed) | No |
| **Address** | 2 | `/address/{address}`, `/address/{address}/utxos` (via scantxoutset) | No |
| **Supply** | 1 | `/supply` (circulating, halving schedule, inflation rate) | No |
| **Statistics** | 3 | `/stats/utxo-set`, `/stats/segwit-adoption`, `/stats/op-returns` | No |
| **Streams (SSE)** | 3 | `/stream/blocks`, `/stream/fees`, `/stream/whale-txs` | No |
| **Tools** | 1 | `/tools/exchange-compare` | No |
| **WebSocket** | 1 | `/ws` (pub/sub, public + premium channels) | free+ |
| **Registration** | 1 | `/register` (self-serve API key with ToS acceptance) | No |
| **Billing** | 4 | `/billing/checkout`, `/billing/webhook`, `/billing/status`, `/billing/cancel` (Stripe) | free+ / Stripe sig |
| **Analytics** | 12 | overview, requests, endpoints, errors, user-agents, latency, keys, growth, slow-endpoints, retention, client-types, mcp-funnel | Admin only |
| **Guide** | 1 | `/guide` (interactive, multi-language, use-case filtered) | No |
| **Metrics** | 1 | `/metrics` (Prometheus text format) | Admin only |
| **Admin UI** | 1 | `/admin/dashboard` (Chart.js visual dashboard) | Admin only |

**Extended routers** (prices, address, exchanges, supply, stats) are feature-flagged -- all default ON, toggleable per-deployment via `.env`.

**Tier gating applied to 7 expensive endpoints** (mining/nextblock, stats/*, stream/whale-txs) requiring free+ key. Block-walking caps: anon/free = 144 blocks, pro = 1,008, enterprise = 2,016.

### 1.2 Security & Auth

| Capability | Detail |
|-----------|--------|
| **Transport** | HTTPS via Cloudflare Tunnel -- no home IP exposed, TLS at edge, DDoS absorbed |
| **Authentication** | API key via `X-API-Key` header, SHA256-hashed storage, `secrets.compare_digest()` constant-time comparison |
| **Authorization** | 4-tier system: anonymous (read-only GET), free (POST + expensive GET), pro ($19/mo), enterprise |
| **Rate limiting** | Per-minute sliding window (in-memory) + daily DB-backed counts. `X-RateLimit-*` headers. `Retry-After` on 429 |
| **Registration protection** | 5 registrations/hour/IP, 3 keys/email hard cap, email length 254 chars, label 100 chars |
| **Input validation** | Pydantic + regex (64-hex txid, non-negative heights, hex-only bodies, 2MB body limit) |
| **Node protection** | RPC whitelist (21 safe commands), localhost-only binding, `scantxoutset` semaphore (max 1 concurrent, 30s timeout) |
| **Security headers** | CSP, X-Frame-Options DENY, HSTS, X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy, X-XSS-Protection |
| **Circuit breaker** | 3 failures = OPEN (503 + Retry-After), 30s cooldown, HALF_OPEN probe, auto-recovery |
| **Error handling** | RFC 7807 `type` URIs (12 defined), JSON envelopes on all `/api/*` paths, `help_url` on every error |
| **Privacy** | Pre-commit hook blocks tracking code (GA, Mixpanel, fingerprinting). No analytics beacons. |
| **Secrets management** | Pydantic `SecretStr` for RPC password. No API keys in scripts (GitGuardian-flagged key rotated). |
| **Penetration test** | Completed 2026-03-07 -- full API surface. 3 findings (metrics exposure, email length, registration rate limit). All fixed, deployed, verified. |

### 1.3 Developer Experience

| Asset | Status |
|-------|--------|
| **Python SDK** | `sdk/satoshi_api/` -- zero-dependency, typed, auto-retry on 429, supports self-hosted + hosted. `register()` bug fixed (was sending empty body). Link on landing page. |
| **3 example projects** | `examples/block-tracker/`, `examples/fee-monitor/`, `examples/mempool-monitor/` -- each with README, requirements.txt, runnable script |
| **Interactive guide** | `/api/v1/guide` -- use-case filtering, multi-language code examples (Python, curl, JS), covers all 76 endpoints |
| **OpenAPI / Swagger** | `/docs` (Swagger UI) + `/redoc` (ReDoc) -- auto-generated, metadata includes contact, license, terms, servers |
| **Self-hosting guide** | `docs/self-hosting.md` + `docs/bitcoin-conf-example.conf` -- complete setup from zero |
| **Blog post** | `blog-post.md` -- architecture deep-dive, ready for dev.to |
| **Standard response envelope** | `{ data, meta }` on success, `{ error }` on failure, `request_id` on everything |
| **Deprecation headers** | Sunset headers on deprecated query-param auth |
| **Show HN draft** | Written, ready to submit |
| **MCP integration** | bitcoin-mcp (separate repo) -- 35 tools, 6 prompts, 7 resources, AI agent interface for the API |

### 1.4 Monitoring & Observability

| Capability | Detail |
|-----------|--------|
| **Prometheus metrics** | `/metrics` (admin-gated): cache hit/miss counters across all cache paths, WebSocket active connections gauge, registered API keys gauge (initialized from DB), request latency histograms, fee collector metrics |
| **Admin analytics** | 12 endpoints: overview, requests, endpoints, errors, user-agents, latency, keys, growth, slow-endpoints, retention, client-types, mcp-funnel |
| **Admin dashboard** | `static/admin-dashboard.html` -- Chart.js, dark theme, auto-refresh, visual analytics |
| **Visualizer** | `static/visualizer.html` -- ECharts live visualization |
| **Structured logging** | JSON logging (opt-in via config), access logs with IP, method, path, status, tier, request_id, latency |
| **Usage buffer** | Batch writes (50 rows or 30s flush) -- prevents write contention |
| **Auto-pruning** | Fee history data auto-pruned in background collector |
| **UptimeRobot** | External health monitoring every 5 minutes |
| **Deep health** | `/health/deep` -- DB connectivity, background jobs status, cache state, circuit breaker state, migration status |

### 1.5 Legal & Compliance

| Document | Location | Coverage |
|----------|----------|----------|
| **Terms of Service** | `static/terms.html`, `/terms` | Acceptable use, liability limitation, financial disclaimer, FL governing law, WebSocket/SSE terms, Stripe billing terms |
| **Privacy Policy** | `static/privacy.html`, `/privacy` | Data collection transparency, retention periods, third-party services (Stripe, CoinGecko), no tracking |
| **Financial disclaimer** | `X-Data-Disclaimer` header on all responses | Not financial advice |
| **CoinGecko attribution** | `attribution` field in `/prices` response + footer | Required by CoinGecko ToS |
| **ToS acceptance** | `/register` requires `agreed_to_terms: true` | Consent on record |
| **License** | Apache 2.0 | Open source |
| **DCO** | Developer Certificate of Origin | Contribution compliance |
| **Legal audit script** | `scripts/legal_audit.py` (10 areas) | Automated compliance checking |
| **LLC prep** | `docs/LLC_PREP.md` | Checklist ready, deferred until paying customers |

### 1.6 Marketing & Distribution Assets

| Asset | Detail |
|-------|--------|
| **Landing page** | `static/index.html` -- "Free Bitcoin API for Developers", "No node required" above fold, JSON-LD structured data, SEO meta, OG/Twitter cards |
| **7 SEO pages** | vs-mempool, vs-blockcypher, best-bitcoin-api-for-developers, bitcoin-api-for-ai-agents, self-hosted-bitcoin-api, bitcoin-fee-api, bitcoin-mempool-api |
| **MCP setup guide** | `static/bitcoin-mcp-setup-guide.html` |
| **Sitemap** | `static/sitemap.xml` (12 URLs) |
| **robots.txt** | Welcomes AI crawlers |
| **Google verification** | Site verified |
| **Domain** | bitcoinsapi.com (Cloudflare Registrar, ~$10/yr) |
| **Contact** | api@bitcoinsapi.com |
| **PyPI** | `pip install satoshi-api` |
| **Pricing** | 2 visible tiers (Self-Hosted free + Hosted free), Pro ($19/mo) hidden until demand. Reconciled across all 19 doc files. |

### 1.7 Infrastructure & Deployment

| Component | Detail |
|-----------|--------|
| **Runtime** | FastAPI + uvicorn on Main PC, port 9332 |
| **Database** | SQLite (WAL mode), 5 migrations, parameterized queries |
| **Auto-start** | Windows Scheduled Task "SatoshiAPI" on logon |
| **HTTPS** | Cloudflare Tunnel (`cloudflared` Windows service), named tunnel `satoshi-api` |
| **Docker** | `Dockerfile` (non-root), `docker-compose.yml`, `docker-compose.prod.yml`, health checks, graceful shutdown (30s) |
| **CI/CD** | GitHub Actions: tests + lint on push, PyPI publish on release |
| **Pre-commit hooks** | Privacy enforcer (blocking) + agent trigger advisory (non-blocking) |
| **Operating cost** | ~$3/month (electricity + domain) |

### 1.8 Test Coverage

| Type | Count | Detail |
|------|-------|--------|
| **Unit tests** | 335 | `tests/test_api.py` (235) + `test_notifications.py` (9) + `test_rate_limit_redis.py` (6) + indexer tests (85) -- all passing |
| **E2E tests** | 21 | `tests/test_e2e.py` -- against live node |
| **Load test** | 1 | `tests/locustfile.py` -- 8 weighted endpoints, 50 users, 0 errors, p95 < 500ms (4ms median) |
| **Security script** | 1 | `scripts/security_check.sh` -- 9 checks, all passing |
| **Legal audit** | 1 | `scripts/legal_audit.py` -- 10 areas |
| **Staging check** | 1 | `scripts/staging-check.sh` -- pre-deploy validation (CSP, headers, docs, endpoints) |
| **Total** | **356 tests + 3 audit scripts** | |

---

## STAGE 2: Post-Launch (30-60 Days)

Focus: validate demand, gather feedback, optimize what's built.

### Trigger Conditions

| Signal | Threshold | Action |
|--------|-----------|--------|
| API key registrations | > 20 keys | Prioritize DX improvements based on usage patterns |
| API key registrations | > 50 keys | Publish JS/TypeScript SDK |
| PyPI downloads/week | > 50 | Write "How to build X" tutorial series |
| GitHub stars | > 100 | Submit to more MCP directories, consider Product Hunt |
| Hosted requests/day | > 1,000 | Evaluate SQLite write performance, consider batch optimizations |
| Pro tier inquiries | > 3 | Activate visible Pro pricing on landing page |
| Support emails | Any pattern | Build FAQ / troubleshooting page |

### Planned Work

| Item | Effort | Trigger |
|------|--------|---------|
| **JS/TypeScript SDK** | 2-3 days | Deferred from sprint, ship when >50 keys |
| **Show HN submission** | 1 hour | Immediate -- draft is ready |
| **dev.to blog post** | 1 hour | Immediate -- blog-post.md is ready |
| **r/BitcoinDev + r/Bitcoin posts** | 1 hour | Immediate |
| **Nostr announcement** | 1 hour | Immediate |
| **MCP directory submissions** | 2 hours | Immediate (modelcontextprotocol/servers PR, Smithery, MCP Hub) |
| **Tutorial: "Build a fee alert bot"** | 4 hours | When >20 keys |
| **Tutorial: "Bitcoin data in Claude"** | 4 hours | When MCP directory listings go live |
| **API key rotation endpoint** | 1 day | When any key compromise reported |
| **`security.txt`** | 1 hour | Should ship within 30 days |
| **CSP nonce-based script loading** | 1 day | Remove `unsafe-inline` from script-src |
| **SRI for external scripts** | 2 hours | Harden CDN dependencies |
| **Idempotency keys for POST** | 1 day | When broadcast volume > 10/day |
| **Community engagement** | Ongoing | Respond to every issue and PR within 24 hours |

### Analytics to Watch

- Which endpoints get the most traffic (optimize caching for those)
- Client-type distribution (browser vs. SDK vs. MCP vs. curl)
- Registration-to-active-usage conversion rate
- Error rate by endpoint (find pain points)
- Geographic distribution (via Cloudflare analytics)

---

## STAGE 3: Validated Demand (60-90 Days)

Focus: features that require proven user demand before investing.

### Trigger Conditions

| Signal | Threshold | Action |
|--------|-----------|--------|
| Pro subscribers | > 5 | Invest in premium-only features |
| Address endpoint usage | > 100 req/day | Evaluate Electrs sidecar for `/address/{addr}/txs` |
| WebSocket connections | > 10 concurrent | Build premium real-time channels |
| Consulting inquiries | > 3 | Formalize consulting offering, link from API |
| Enterprise inquiries | > 1 | Build SLA framework, dedicated instance playbook |

### Planned Work

| Item | Effort | Dependency |
|------|--------|------------|
| **Electrs sidecar (optional)** | 3-5 days | Only if address history demand is validated. Adds `/address/{addr}/txs`. Board decision: no custom Postgres indexer. |
| **Premium WebSocket channels** | 2-3 days | Auth infrastructure already in place. Premium channels for whale alerts, large mempool events. |
| **SSE connection authentication** | 1 day | Rate limit SSE by tier |
| **Transaction monitoring webhooks** | 3-5 days | "Notify me when txid confirms" -- requires background poller |
| **Smart fee estimation v2** | 3-5 days | Probability-based confirmation estimates, not just sat/vB |
| **Historical fee time-series API** | 2 days | Already collecting data via fee collector. Expose as queryable endpoint. |
| **SDK: Go client** | 3 days | If Go developers show up in user-agent data |
| **Hosted tier marketing page** | 1 day | When Pro has > 5 subscribers |
| **Stripe billing portal** | 1 day | Customer self-service for plan changes |

---

## STAGE 4: Platform Expansion (90+ Days)

Focus: long-term vision, only pursued if Stages 1-3 validate the market.

### Planned Work

| Item | Effort | Dependency |
|------|--------|------------|
| **Multi-node load balancing** | 1-2 weeks | Only if single-node performance ceiling is hit |
| **PostgreSQL backend option** | 1-2 weeks | Only if SQLite write contention becomes real at >1K req/s |
| **Ordinals/inscriptions API** | 2-3 weeks | Aligns with prior Rune Emilio experience. Requires ord indexer. |
| **Lightning Network integration** | 2-3 weeks | Separate LN node required. L402 extension package already exists. |
| **Mempool intelligence** | 2 weeks | Real-time congestion maps, miner template prediction |
| **Enterprise features** | Ongoing | SLA, dedicated instances, custom endpoints, compliance docs |
| **Cloud-hosted option** | Ongoing | Move to VPS ($50-80/mo) if demand justifies |
| **LLC formation** | 1 day | When monthly revenue > $100 (checklist ready in `docs/LLC_PREP.md`) |
| **Admin billing dashboard** | 1 week | Revenue tracking, churn analysis, MRR charts |
| **Developer portal** | 2 weeks | Unified docs site with API explorer, SDKs, tutorials |

### Long-Term Product Vision

The three-layer stack (bitcoinlib-rpc -> Satoshi API -> bitcoin-mcp) positions us as the full-stack Bitcoin data infrastructure for developers and AI agents. The endgame is not competing with QuickNode or Alchemy on hosted infrastructure scale -- it is owning the "analyzed Bitcoin data" category:

1. **Self-hosted default** -- the `pip install` experience is the moat
2. **AI-native** -- MCP integration is 12-18 months ahead of any competitor
3. **Consulting funnel** -- every user is a potential custom development client
4. **Open-core economics** -- free drives adoption, hosted/pro drives revenue, enterprise drives margin

---

## PM ASSESSMENT

### What Are We Strongest At?

**Developer experience and product completeness.** 76 endpoints, 356 tests, Python SDK, interactive guide, 3 example projects, OpenAPI docs, self-hosting guide, SEO pages, legal compliance -- this is an absurdly well-built v0.3 product. The ratio of "things built" to "users acquired" is extremely high, which is both a strength (launch confidence) and a warning (see risks below).

The security posture is genuinely impressive for a solo project. Penetration test completed and all findings resolved. Pre-commit privacy hooks. RFC 7807 errors. Constant-time auth comparison. Circuit breaker. This is production-grade infrastructure.

The AI/MCP angle is a legitimate first-mover advantage. No other Bitcoin API has a native MCP integration layer. As the agent ecosystem grows, this becomes more valuable.

### What Is Our Biggest Risk?

**Over-engineering, under-marketing.** We have spent 25 sprints building. We have spent zero sprints acquiring users. The product is battle-tested against automated tests and security scripts, but it has not been battle-tested against real developers with real use cases.

Specific risks in priority order:

1. **Zero distribution.** Show HN not submitted. Blog post not published. Reddit not posted. MCP directories not submitted. PyPI listing exists but nobody knows about it. Every day without distribution is a day the product sits idle.

2. **Single-machine infrastructure.** The entire API runs on one PC behind a residential internet connection. Power outage = total downtime. This is fine for launch but becomes a credibility problem if paying customers appear.

3. **BUSINESS_PLAN.md is stale.** It still says "77 endpoints" in the product suite table (should be 74), lists an outdated roadmap (v0.2 items already completed), and the launch channels section references actions not yet taken. The document should either be updated or retired in favor of this Product State document.

4. **Pricing uncertainty.** $19/mo Pro tier is set but unvalidated. We do not know if developers will pay for a Bitcoin API when mempool.space is free. The self-hosted angle sidesteps this, but hosted revenue is the stated business model.

5. **Address history gap.** `/address/{addr}/txs` (transaction history by address) is the most-requested feature in every Bitcoin API. We deliberately skip it (requires Electrs), which is the right architectural call, but it limits appeal for wallet developers.

### What Would I Do Differently?

1. **Launch first, build second.** If I were PM from sprint 1, I would have shipped after sprint 6 (core API + auth + caching + security), submitted Show HN, and let user feedback drive sprints 7-25. We built the admin dashboard, billing integration, interactive guide, and example projects before having a single external user. That is backwards.

2. **Track one metric obsessively.** Right now we track nothing externally. I would instrument "API keys registered" as the north star metric and review it daily. Everything else (stars, downloads, revenue) follows from that.

3. **Kill the BUSINESS_PLAN.md.** It is a planning artifact from before the product was built. This Product State document supersedes it. Keep the SCOPE_OF_WORK as the technical source of truth and this document as the strategic source of truth.

4. **Set a launch deadline and hold it.** "Launch is the #1 priority" has been the stated goal, but we keep adding features. Set a hard date (e.g., March 10, 2026) and submit Show HN regardless of what is or is not polished.

### Are We Ready to Launch?

**Yes. Unequivocally.** The product has been ready to launch since sprint 13 (simplify for launch). Everything since then has been polish. We are past the point of diminishing returns on pre-launch work.

The go-live checklist is 100% complete. All 335 unit tests pass. Security audit clean. Legal docs in place. Landing page live. Domain configured. HTTPS working. Auto-start configured. Monitoring active.

There is no technical, legal, or product reason to delay. The only blocker is pressing "submit" on Hacker News and clicking "publish" on dev.to.

### The Single Most Important Thing Post-Launch

**Distribution.** Specifically, submit Show HN within 48 hours of reading this document. Then publish the dev.to blog post. Then post to r/BitcoinDev. Then submit to MCP directories.

After that, the single most important activity is **responding to every piece of feedback within 24 hours**. The first 20 users will define the product roadmap for the next 6 months. Their questions will reveal what documentation is missing, their errors will reveal what validation is incomplete, and their feature requests will tell us whether Stage 3 investments are worth making.

Do not build anything new until 20 people have used what already exists.

---

*This document is the definitive product state assessment for Satoshi API as of 2026-03-07. It supersedes the phased roadmap in BUSINESS_PLAN.md and the competitive gap analysis in COMPETITIVE_ANALYSIS.md for strategic planning purposes. The SCOPE_OF_WORK.md remains the canonical technical reference.*
