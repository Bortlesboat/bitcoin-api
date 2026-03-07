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
- **Auth:** API key via `X-API-Key` header, tier-based (anonymous/free/pro/enterprise)
- **Rate limiting:** Sliding window (in-memory) + daily (DB-backed)
- **Caching:** Per-cache locks, reorg-safe depth awareness, bounded LRU for hash mappings

## Testing

- Run tests: `python -m pytest tests/test_api.py -q`
- E2E (requires running API): `python -m pytest tests/test_e2e.py -m e2e`
- Load test: `locust -f tests/locustfile.py --host http://localhost:9332`
- Security check: `SATOSHI_API_KEY=<key> bash scripts/security_check.sh`
- `authed_client` fixture for POST endpoint tests (requires API key in DB)
- `client` fixture is anonymous -- use for GET tests and auth rejection tests

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
| `src/bitcoin_api/middleware.py` | Security headers, CORS, auth + rate limiting |
| `src/bitcoin_api/exceptions.py` | All exception handlers |
| `src/bitcoin_api/jobs.py` | Background fee collector thread |
| `src/bitcoin_api/static_routes.py` | Landing page, robots.txt, sitemap, decision pages |
| `src/bitcoin_api/config.py` | Settings from env vars + feature_flags property |
| `src/bitcoin_api/auth.py` | API key auth |
| `src/bitcoin_api/rate_limit.py` | Rate limiting |
| `src/bitcoin_api/cache.py` | TTL + LRU caching with registry + factory |
| `src/bitcoin_api/usage_buffer.py` | Batch usage logging (50 rows / 30s flush) |
| `src/bitcoin_api/db.py` | SQLite (WAL), key storage, fee history |
| `src/bitcoin_api/migrations/` | SQL migrations + runner |
| `tests/test_api.py` | Unit tests (129) |
| `tests/test_e2e.py` | E2E tests (21) |
| `tests/helpers.py` | Isolated router test client factory |
| `docs/AGENT_ROLES.md` | Agent employee coordination & trigger matrix |
| `scripts/security_audit.py` | Automated security audit (8 checks) |

## Agent Employees

Satoshi API has 7 agent "employees" organized in a hierarchy. After any change, check the trigger matrix in `docs/AGENT_ROLES.md` to see if other agents should run.

### Leadership (report to CEO)
| Role | Skill | Responsibility |
|------|-------|---------------|
| **Head of Product** | `/product-review` | Product vision, customer journey, pricing, roadmap, competitive positioning |
| **CFO / Finance** | `/finance-review` | Cost analysis, unit economics, pricing validation, revenue projections |

### Operations
| Role | Skill | Responsibility |
|------|-------|---------------|
| **Legal** | `/legal-review` | ToS, privacy policy, disclaimers, compliance |
| **Marketing** | `/marketing-sync` | Landing page, SEO, endpoint counts, feature claims |
| **Security** | `/security-review` | Headers, auth, rate limits, CSP, threat model |
| **CTO / Coder** | `/code-review` | Tests pass, code quality, SCOPE_OF_WORK updated, architecture |
| **Analytics** | `/analytics-review` | Data collection changes, logging, metrics |

Each agent reads the trigger matrix, does its work, then reports which other agents should run next. No auto-execution — user stays in control.
