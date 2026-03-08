# Satoshi API -- Project Instructions

## Scope of Work (MANDATORY)

**`docs/SCOPE_OF_WORK.md` is the canonical project document. It MUST be updated with every change.**

After any code change, documentation update, or architectural decision:
1. Update the relevant section(s) in `docs/SCOPE_OF_WORK.md`
2. If adding/removing endpoints: update Section 3 (API Surface)
3. If adding/removing files: update Section 6 (Deliverables)
4. If fixing bugs or addressing review findings: update Section 5.2 (Critical Issues Fixed)
5. If changing security controls: update Section 4 (Security Model)
6. If test count changes: update Section 6.1 (sprint table totals)
7. If adding known limitations: update Section 5.3
8. If deployment steps change: update Section 7

The SOW is the single source of truth for what this project is, what it does, and what state it's in. Treat it like a living design doc, not a one-time artifact.

## Architecture

- **Stack:** FastAPI + bitcoinlib-rpc + SQLite (WAL mode)
- **Entry point:** `src/bitcoin_api/main.py`
- **Config:** Pydantic Settings from env vars (`config.py`), RPC password is `SecretStr`
- **Auth:** API key via `X-API-Key` header, tier-based (anonymous/free/pro/enterprise). Anonymous: lightweight GET only. Free+: expensive GET (mining/stats/whale-stream). Block caps: anon/free=144, pro=1008, enterprise=2016. Helpers: `require_api_key()`, `cap_blocks_param()` in `auth.py`.
- **Rate limiting:** Sliding window (in-memory or Upstash Redis) + daily (DB-backed)
- **Caching:** Per-cache locks, reorg-safe depth awareness, bounded LRU for hash mappings
- **External services (all optional, default disabled):** Upstash Redis (rate limit persistence), Resend (transactional email), PostHog (landing page analytics). API functions fully without any of them.

## Testing

- Run tests: `python -m pytest tests/test_api.py -q`
- E2E (requires running API): `python -m pytest tests/test_e2e.py -m e2e`
- Load test: `locust -f tests/locustfile.py --host http://localhost:9332`
- Security check: `SATOSHI_API_KEY=<key> bash scripts/security_check.sh`
- `authed_client` fixture for POST endpoints + gated GET endpoints (requires API key in DB)
- `client` fixture is anonymous -- use for lightweight GET tests and auth rejection tests

## Conventions

- Response envelope: `{ data, meta }` on success, `{ error }` on failure
- All errors include `request_id` for tracing
- POST endpoints require `free` tier or above (403 for anonymous)
- Node version info redacted for anonymous users on `/network`
- Secrets: never log, never commit. RPC password uses `SecretStr`.

## Operations (MANDATORY READ for deployment/config changes)

**`docs/OPERATIONS.md` is the human-facing operations guide.** It covers how to start/stop/restart the API, configure `.env`, use analytics, run agents, publish to PyPI, and complete pending setup (Cloudflare, Bing, social preview). **Any agent making deployment, config, or operational changes MUST update OPERATIONS.md to match.**

## Key Files

| File | Purpose |
|------|---------|
| `docs/SCOPE_OF_WORK.md` | Living project document (KEEP UPDATED) |
| `docs/OPERATIONS.md` | How to run, restart, configure, use analytics, run agents |
| `src/bitcoin_api/main.py` | App creation, lifespan, router registration (~89 lines) |
| `src/bitcoin_api/middleware.py` | Security headers, CORS, auth + rate limiting, gzip compression |
| `src/bitcoin_api/exceptions.py` | All exception handlers |
| `src/bitcoin_api/jobs.py` | Background fee collector thread |
| `src/bitcoin_api/static_routes.py` | Landing page, robots.txt, sitemap, decision pages, favicon |
| `src/bitcoin_api/config.py` | Settings from env vars + feature_flags property |
| `src/bitcoin_api/auth.py` | API key auth |
| `src/bitcoin_api/rate_limit.py` | Rate limiting (in-memory or Upstash Redis) |
| `src/bitcoin_api/notifications.py` | Transactional email (Resend) + analytics events (PostHog) |
| `src/bitcoin_api/cache.py` | TTL + LRU caching with registry + factory |
| `src/bitcoin_api/usage_buffer.py` | Batch usage logging (50 rows / 30s flush) |
| `src/bitcoin_api/db.py` | SQLite (WAL), key storage, fee history |
| `src/bitcoin_api/metrics.py` | Prometheus metric definitions (counters, histograms, gauges) |
| `src/bitcoin_api/pubsub.py` | In-process pub/sub hub for WebSocket push |
| `src/bitcoin_api/stripe_client.py` | Stripe checkout session creation + webhook helpers |
| `src/bitcoin_api/routers/metrics.py` | GET /metrics (Prometheus text format) |
| `src/bitcoin_api/routers/websocket.py` | WS /api/v1/ws (real-time subscriptions) |
| `src/bitcoin_api/routers/billing.py` | Stripe billing: checkout, webhook, status, cancel |
| `src/bitcoin_api/routers/supply.py` | Supply endpoint: circulating supply, halving, inflation |
| `src/bitcoin_api/routers/stats.py` | Statistics: UTXO set, SegWit adoption, OP_RETURN stats |
| `src/bitcoin_api/services/` | Business logic (fees, transactions, exchanges, mining, stats, serializers) |
| `src/bitcoin_api/services/mining.py` | Pool identification, hashrate calculation |
| `src/bitcoin_api/services/stats.py` | Output type classification, OP_RETURN parsing |
| `src/bitcoin_api/migrations/` | SQL migrations + enhanced runner (rollback, status, validation) |
| `src/bitcoin_api/migrations/004_add_subscriptions.sql` | subscriptions table + stripe_customer_id column |
| `static/visualizer.html` | ECharts live visualization dashboard |
| `tests/test_api.py` | Unit + integration tests (235). Total: 335 unit + 21 e2e = 356 tests |
| `tests/test_notifications.py` | Resend + PostHog notification tests (9) |
| `tests/test_rate_limit_redis.py` | Redis rate limiting + fallback tests (6) |
| `tests/test_e2e.py` | E2E tests (21) |
| `tests/helpers.py` | Isolated router test client factory |
| `docs/AGENT_ROLES.md` | Agent employee coordination & trigger matrix |
| `scripts/security_audit.py` | Automated security audit (10 checks) |
| `scripts/privacy_check.py` | Pre-commit privacy enforcer (blocks secrets/PII) |
| `scripts/trigger_check.py` | Pre-commit advisory (reports which agents to run) |
| `scripts/install-hooks.sh` | Installs pre-commit hooks (privacy blocking + trigger advisory) |

## Agent Employees

Satoshi API has 11 agent "employees" in a flat org. After any change, check the trigger matrix in `docs/AGENT_ROLES.md` to see if other agents should run.

### All 11 Agents (report directly to CEO)
| Role | Skill | Responsibility |
|------|-------|---------------|
| **Product Manager** | `/pm-review` | Feature strategy, competitive gaps, pricing, 90-day roadmap |
| **UX/Design Lead** | `/ux-review` | Customer journey, landing page, registration, docs UX, error messages |
| **CFO / Finance** | `/finance-review` | Cost analysis, unit economics, pricing validation, revenue projections |
| **Legal** | `/legal-review` | ToS, privacy policy, disclaimers, compliance |
| **Marketing** | `/marketing-sync` | Landing page, SEO, endpoint counts, feature claims |
| **Security** | `/security-review` | Headers, auth, rate limits, CSP, threat model |
| **Architect** | `/architecture-review` | SCOPE_OF_WORK, CLAUDE.md, code quality, module coupling, architecture |
| **QA Lead** | `/qa-review` | Tests, coverage gaps, regressions, test-to-docs sync |
| **Analytics** | `/analytics-review` | Data collection changes, logging, metrics |
| **Chief of Staff** | `/ops-review` | Data lifecycle, metrics, process automation, standards, org maintenance, headcount |
| **Admin Assistant** | `/admin-assistant` | Endpoint count stamping, doc consistency, guide catalog sync, cross-file reference audits |

**Orchestration:** `/all-hands` runs all 11 agents with consolidated dashboard.
**Deprecated wrappers:** `/code-review` (→ qa + architecture), `/product-review` (→ pm + ux).

Each agent reads the trigger matrix, does its work, then reports which other agents should run next. No auto-execution — user stays in control.
