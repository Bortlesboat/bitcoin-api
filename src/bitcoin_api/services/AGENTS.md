# Satoshi API — Services (Business Logic Layer)

## What this directory is
Business logic, data fetching, and computation. Called by routers, calls Bitcoin Core RPC or external APIs. HTTP-agnostic — no Request/Response objects here.

## Service inventory
| File | Responsibility |
|------|---------------|
| `fees.py` | Fee estimation algorithms, smart fee calculations, mempool-based recommendations |
| `mining.py` | Mining stats, difficulty adjustment calc, pool rankings |
| `transactions.py` | Transaction parsing, inscription detection, PSBT analysis |
| `analytics.py` | Usage event recording and aggregation |
| `exchanges.py` | Exchange rate fetching from external sources |
| `price.py` | Price aggregation from multiple sources |
| `stats.py` | Blockchain statistics computation |
| `serializers.py` | Shared serialization helpers |

## Rules
- Services must be independently testable (mock the RPC client, not the service)
- All external API calls must handle rate limits and timeouts gracefully
- Bitcoin RPC calls go through `../dependencies.py` (provides the injected RPC client)
- Cache aggressively where appropriate — use `../cache.py`
- Service functions return Python objects (dicts/models), not HTTP responses
- If a service function grows beyond ~100 lines, consider splitting it
