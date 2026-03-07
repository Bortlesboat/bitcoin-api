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

## Key Files

| File | Purpose |
|------|---------|
| `docs/SCOPE_OF_WORK.md` | Living project document (KEEP UPDATED) |
| `src/bitcoin_api/main.py` | App, middleware, exception handlers |
| `src/bitcoin_api/config.py` | Settings from env vars |
| `src/bitcoin_api/auth.py` | API key auth |
| `src/bitcoin_api/rate_limit.py` | Rate limiting |
| `src/bitcoin_api/cache.py` | TTL + LRU caching |
| `tests/test_api.py` | Unit tests (115) |
| `tests/test_e2e.py` | E2E tests (21) |
