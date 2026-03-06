# Satoshi API

[![CI](https://github.com/Bortlesboat/bitcoin-api/actions/workflows/ci.yml/badge.svg)](https://github.com/Bortlesboat/bitcoin-api/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

The thinnest REST layer over your Bitcoin node. One `pip install`, instant API.

Powered by [bitcoinlib-rpc](https://github.com/Bortlesboat/bitcoinlib-rpc) for analyzed data (fees, mempool congestion, block stats) rather than raw RPC dumps. Part of the AI agent pipeline: **bitcoinlib-rpc** -> **satoshi-api** -> [bitcoin-mcp](https://github.com/Bortlesboat/bitcoin-mcp).

## Prerequisites

- **Bitcoin Core** running with `server=1` in `bitcoin.conf` (RPC enabled)
- Python 3.10+

**Node configuration notes:**
- Transaction lookups (`/tx/{txid}`, `/tx/{txid}/raw`) for confirmed transactions require `txindex=1`
- Block template (`/mining/nextblock`) requires at least one connected peer on mainnet
- Block stats (`/blocks/{height}/stats`) is unavailable for pruned blocks below the prune height

## Quick Start

```bash
pip install bitcoin-api  # or: pip install -e . for local dev

# Point at your node
export BITCOIN_RPC_USER=your_user
export BITCOIN_RPC_PASSWORD=your_password
# For testnet: export BITCOIN_RPC_PORT=18332
# For signet:  export BITCOIN_RPC_PORT=38332

# Run
bitcoin-api  # or: satoshi-api
# -> http://localhost:9332/docs
```

### Docker

```bash
# Create .env with your node credentials
echo "BITCOIN_RPC_USER=your_user" > .env
echo "BITCOIN_RPC_PASSWORD=your_password" >> .env

docker compose up -d
```

## Endpoints

All endpoints are under `/api/v1/`. Interactive docs at `/docs`.

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Node ping (no auth required) |
| `GET /status` | Sync progress, peers, disk usage |
| `GET /network` | Version, connections, relay fee |
| `GET /network/forks` | Chain tips / fork detection |
| `GET /blocks/latest` | Latest block analysis |
| `GET /blocks/{height_or_hash}` | Block by height or hash |
| `GET /blocks/{height}/stats` | Raw block statistics |
| `GET /tx/{txid}` | Transaction analysis (fees, SegWit, Taproot, inscriptions) |
| `GET /tx/{txid}/raw` | Raw decoded transaction |
| `GET /utxo/{txid}/{vout}` | UTXO lookup |
| `GET /mempool` | Mempool analysis (fee buckets, congestion) |
| `GET /mempool/info` | Raw mempool stats |
| `GET /mempool/tx/{txid}` | Mempool entry for a transaction |
| `GET /fees` | Fee estimates (1, 3, 6, 25, 144 blocks) |
| `GET /fees/recommended` | Human-readable fee recommendation |
| `GET /fees/{target}` | Fee estimate for specific block target |
| `GET /mining` | Hashrate, difficulty, retarget estimate |
| `GET /mining/nextblock` | Block template analysis |
| `POST /decode` | Decode raw transaction hex |
| `POST /broadcast` | Broadcast signed transaction |

## Examples

```bash
# Health check
curl http://localhost:9332/api/v1/health

# Fee recommendation
curl http://localhost:9332/api/v1/fees/recommended

# Analyze a transaction
curl http://localhost:9332/api/v1/tx/a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d

# Latest block
curl http://localhost:9332/api/v1/blocks/latest

# With API key (higher rate limits)
curl -H "X-API-Key: your_key_here" http://localhost:9332/api/v1/mempool
```

## API Keys

Anonymous access works out of the box. For higher rate limits, create a key:

```bash
python scripts/create_api_key.py --tier free --label "my-app"
python scripts/create_api_key.py --tier pro --label "production"
```

Pass the key via `X-API-Key` header. Query parameter `?api_key=` is deprecated (sunset: 2026-09-01).

## Rate Limits

| Tier | Req/min | Req/day |
|------|---------|---------|
| Anonymous | 30 | 1,000 |
| Free (API key) | 100 | 10,000 |
| Pro | 500 | 100,000 |
| Enterprise | 2,000 | Unlimited |

Rate limit info in response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `X-RateLimit-Daily-Limit`, `X-RateLimit-Daily-Remaining`.

Every response includes `X-Request-ID` (UUID) and `X-Auth-Tier` headers.

## Response Format

Standard envelope on all endpoints:

```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2026-03-05T12:00:00+00:00",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "node_height": 880000,
    "chain": "main"
  }
}
```

Errors:

```json
{
  "error": {
    "status": 404,
    "title": "Not Found",
    "detail": "Transaction not found",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

## Input Validation

- Transaction IDs and block hashes must be exactly 64 hex characters
- Invalid formats return 422 immediately (no wasted RPC calls)
- Invalid API keys return 401 (not silent downgrade to anonymous)

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
