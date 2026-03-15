# Satoshi API — Routers (HTTP Layer)

## What this directory is
One file per API category. Each router defines HTTP endpoints and delegates to `../services/`. Keep routers thin — no business logic here.

## Router inventory
| File | Category | Notes |
|------|----------|-------|
| `fees.py` | Fee estimation + recommendations | Most-used endpoints; fee intelligence is the core value prop |
| `mempool.py` | Mempool analysis, entry lookup, ancestor chains | |
| `blocks.py` | Block stats, analysis, comparison | |
| `transactions.py` | Transaction decode, analysis, search, inscription detection | |
| `address.py` | Address balance, history, UTXOs | Uses indexer — requires indexer to be running |
| `mining.py` | Mining info, difficulty, pool rankings, halving countdown | |
| `network.py` | Network info, blockchain state, peers, chain tips | |
| `supply.py` | Circulating supply, UTXO set, chain tx stats | |
| `prices.py` | BTC price feeds, market sentiment | |
| `psbt.py` | PSBT security analysis | |
| `history.py` | Historical Bitcoin data explorer | |
| `keys.py` | Key generation, script explanation | |
| `rpc_proxy.py` | JSON-RPC proxy (`/api/v1/rpc`) | Used by bitcoin-mcp zero-config — critical, don't break |
| `mcp_server.py` | MCP server endpoint | Serves MCP protocol directly from the API |
| `analytics.py` | Usage analytics | Internal only |
| `billing.py` | Stripe billing + subscriptions | |
| `health_deep.py` | Deep health checks | |

## Rules
- New endpoint → register in this router file AND add to router list in `../../main.py`
- Response models go in `../models.py` (not inline in routers)
- Business logic goes in `../services/`, not here
- Always add an OpenAPI `description=` string to new endpoints (shown in /api-docs and to AI agents)
- Path params go in route decorator; query params as function args with type hints
