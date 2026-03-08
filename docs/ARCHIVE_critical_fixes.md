# Critical Issues Fixed — Archive

Moved from `SCOPE_OF_WORK.md` Section 5.2 for token efficiency. Full history preserved here.

**Sprint 6:**
1. **Exception swallowing** -- Middleware now logs full tracebacks via `logger.exception()`
2. **Secret leakage risk** -- RPC password changed to Pydantic `SecretStr`
3. **No graceful shutdown** -- Added 30s timeout to CLI and Dockerfile
4. **Unbounded memory** -- `_hash_to_height` dict replaced with `LRUCache(maxsize=256)`
5. **E2E test assertion bug** -- Fixed `"healthy"` -> `"ok"` to match actual status
6. **Missing `request.state.tier`** -- Middleware now sets tier for downstream handlers

**Sprint 7 (Architecture Review):**
7. **RPC singleton never recovers** -- Added `reset_rpc()` called on `ConnectionError` to allow reconnection
8. **POST 403 missing request_id** -- Changed from inline `JSONResponse` to `raise HTTPException`, uses standard error handler
9. **Prod healthcheck uses curl** -- Docker compose prod healthcheck now uses Python urllib (matches Dockerfile)
10. **Duplicate fee field** -- Removed `fee_sat`, kept `fee_sats` (Bitcoin convention)
11. **Rate limit header wrong epoch** -- Changed `time.monotonic()` to `time.time()` for correct unix timestamps
12. **Data leak via extra=allow** -- Changed to `extra="ignore"` on response models
13. **CORS wildcard warning** -- Log WARNING at startup if `*` in origins
14. **Block/mempool null fields** -- Fixed field name mapping: `fee_rate_median`→`median_fee_rate`, `total_fee_btc`→`total_fee`, `total_bytes`→`bytes`, `buckets`→`fee_buckets`
15. **Block hash cache miss** -- `cached_block_by_hash` now checks both `_block_cache` and `_recent_block_cache`
16. **E2E fee test no-op** -- Test checked for "high"/"medium"/"low" keys that don't exist; now validates actual integer-keyed estimates
17. **Dockerfile invalid flag** -- Removed `--limit-max-request-size` (not a valid uvicorn CLI/API param); body limits enforced by Pydantic model validation

**Post-launch (Mar 6):**
18. **Hardcoded API key in security_check.sh** -- Flagged by GitGuardian. Replaced with `$SATOSHI_API_KEY` env var. Exposed key deactivated, new key generated.

**v0.3.1 Hardening (Mar 7):**
19. **No RPC timeout** -- Added configurable `RPC_TIMEOUT` (default 30s) via Settings
20. **Address scan can hang** -- Wrapped `scantxoutset` in timeout guard, returns 504 on `ReadTimeout`
21. **No Cache-Control headers** -- Added middleware: fee/mempool→10s, deep blocks→1hr, health→no-cache, register→no-store
22. **404 returns HTML on API routes** -- `http_exception_handler` now returns JSON envelope for `/api/*` paths
23. **Registration not rate-limited** -- Removed `/api/v1/register` from rate limit skip set
24. **Raw mempool fetched repeatedly** -- Added `cached_raw_mempool` with 5s TTL
25. **Timing attack on API key comparison** -- Auth now uses `secrets.compare_digest()`
26. **Registration email enumeration** -- `/register` no longer reveals whether an email is already registered
27. **Cloudflare Insights tracking removed** -- Removed CF beacon from all HTML pages

**Pentest Hardening (Mar 7):**
28. **Metrics endpoint publicly exposed** -- Added `X-Admin-Key` auth with `secrets.compare_digest()`
29. **No per-IP registration rate limit** -- Added sliding window (5 registrations/hour/IP)
30. **Unbounded email/label input** -- Added Pydantic `Field(max_length=254)` on email, `Field(max_length=100)` on label
