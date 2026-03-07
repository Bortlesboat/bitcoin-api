# Platform: r/Python

**Suggested Title:** Built a FastAPI app that wraps Bitcoin Core RPC -- lessons on caching, rate limiting, and API design

---

I built [Satoshi API](https://github.com/Bortlesboat/bitcoin-api), a REST API that wraps Bitcoin Core's JSON-RPC in 49 endpoints. Wanted to share some of the Python/FastAPI patterns I landed on, since a few of them took real iteration to get right.

**Depth-aware TTL caching.** The naive approach -- cache everything for N seconds -- does not work when your data source is a blockchain. A block with 100 confirmations will never change, but a block with 1 confirmation might disappear in a reorg. I built a cache layer where TTL scales with confirmation depth: recent blocks get 30s, deep blocks get 1 hour, fee estimates get 10s. Each cache key gets its own asyncio lock to prevent thundering herd on cold starts. Implemented as a simple dict with expiry timestamps -- no Redis needed for a single-instance API.

**Sliding window rate limiter.** I went with an in-memory sliding window for per-minute limits (deque of timestamps, prune expired on each check) and SQLite for daily limits. The daily counter uses a simple `COUNT(*)` on the usage log table, which is O(n) and will not scale past ~1K req/s, but for a self-hosted API it is fine. The alternative was maintaining an in-memory counter with periodic flush, but that loses counts on restart.

**Pydantic Settings with SecretStr.** Config is a Pydantic `BaseSettings` singleton that reads from env vars. The RPC password field is `SecretStr`, which prevents it from showing up in logs, repr, or Swagger docs. Small thing, but it caught a real bug during development where I was logging the full config object.

**Response envelope pattern.** Every endpoint returns `{ data, meta }` where `meta` includes timestamp, request_id (UUID), node_height, chain, syncing status, and cache age. Errors return `{ error: { status, title, detail, request_id } }`. This makes client code predictable and debugging straightforward.

**FastAPI middleware ordering matters.** My middleware stack is: security headers, CORS, auth, rate limiting, access logging. Getting auth before rate limiting was important -- you want to know the user's tier before deciding their rate limit. Logging comes last so it can read `request.state.tier` set by auth.

The whole thing is ~15 source files, 118 unit tests, 21 e2e tests. FastAPI + httpx + SQLite, no heavy dependencies.

- **GitHub:** https://github.com/Bortlesboat/bitcoin-api
- **PyPI:** `pip install satoshi-api`
- **Live docs (Swagger):** https://bitcoinsapi.com/docs
