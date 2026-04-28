# Satoshi API — Bitcoin REST API (bitcoinsapi.com)

## What this is
Production FastAPI application for Bitcoin fee intelligence, MCP-powered agents, and x402 pay-per-call Bitcoin data. Live at https://bitcoinsapi.com. Revenue-generating product — treat production changes carefully and verify before promoting.

## Architecture
- `src/bitcoin_api/routers/` — HTTP endpoint definitions, one file per category (27 routers)
- `src/bitcoin_api/services/` — Business logic layer (HTTP-agnostic, testable in isolation)
- `src/bitcoin_api/indexer/` — Address + transaction indexer (separate worker process)
- `src/bitcoin_api/main.py` — App entrypoint, middleware, router registration, startup events
- `src/bitcoin_api/models.py` — Pydantic request/response models (shared across routers)
- `src/bitcoin_api/config.py` — Settings via pydantic-settings / env vars
- `src/bitcoin_api/auth.py` — API key authentication
- `src/bitcoin_api/rate_limit.py` — Free tier rate limiting
- `.github/copilot-instructions.md` — GitHub Copilot/Coding Agent instructions for this repo
- `docs/AGENT_INTEGRATION.md` — Copy-paste kit for adding Satoshi API to other agent-aware repos

## Active workflows (run these, don't skip)
- `./diagnose.sh` — silo checks; run before any significant structural change
- `./release.sh` — tag + changelog + deploy; run for all releases
- `./deploy-api.sh` — auto-tags and deploys to production

## Key rules
- **Tag before major changes**: `git tag v{version} && git push --tags`
- **Run diagnose after structural changes**: catches silo leaks and import errors
- All new endpoints need unit tests in `tests/`
- New routers MUST be registered in `main.py` — this is the #1 missed step
- Live API with real users — no debugging in production. Test locally first.
- `/api/v1/rpc` endpoint is used by bitcoin-mcp zero-config — don't break it

## Content pages (not just API)
- `/history` — Bitcoin History Explorer
- `/guide` — Bitcoin Protocol Guide
- `/mcp-setup` — MCP setup instructions
- `/bitcoin-mcp` — Bitcoin MCP guide
- `/bitcoin-fee-intelligence` — fee intelligence guide
- `/quickstart` — full x402 quickstart
- `/x402/start` — shortest first-paid-call x402 buyer path
- `/docs` — OpenAPI docs (`/api-docs` redirects here for legacy links)

## Discoverability priority
- Glama and AI search rank by documentation completeness — keep OpenAPI descriptions current
- bitcoin-mcp points here as its fallback API; keep fee/mempool endpoints fast and reliable
- GitHub/Copilot agents read `.github/copilot-instructions.md`; keep it aligned with `AGENTS.md`, `CLAUDE.md`, `static/llms.txt`, and `docs/AGENT_INTEGRATION.md`
- For paid x402 onboarding, `/api/v1` stays canonical; versionless aliases are only hidden buyer shortcuts for the five hero endpoints
