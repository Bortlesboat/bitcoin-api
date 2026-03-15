# Satoshi API — Bitcoin REST API (bitcoinsapi.com)

## What this is
Production FastAPI application serving ~103 Bitcoin API endpoints. Live at https://bitcoinsapi.com. v0.3.4. 568 unit + 21 e2e = 589 tests. Revenue-generating product — treat production changes carefully.

## Architecture
- `src/bitcoin_api/routers/` — HTTP endpoint definitions, one file per category (27 routers)
- `src/bitcoin_api/services/` — Business logic layer (HTTP-agnostic, testable in isolation)
- `src/bitcoin_api/indexer/` — Address + transaction indexer (separate worker process)
- `src/bitcoin_api/main.py` — App entrypoint, middleware, router registration, startup events
- `src/bitcoin_api/models.py` — Pydantic request/response models (shared across routers)
- `src/bitcoin_api/config.py` — Settings via pydantic-settings / env vars
- `src/bitcoin_api/auth.py` — API key authentication
- `src/bitcoin_api/rate_limit.py` — Free tier rate limiting

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
- `/api-docs` — OpenAPI docs

## Discoverability priority
- Glama and AI search rank by documentation completeness — keep OpenAPI descriptions current
- bitcoin-mcp points here as its fallback API; keep fee/mempool endpoints fast and reliable
