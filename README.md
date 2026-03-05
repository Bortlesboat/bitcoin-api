# Bitcoin API

Developer-friendly REST API for Bitcoin node data. Powered by [bitcoinlib-rpc](https://github.com/Bortlesboat/bitcoinlib-rpc) -- analyzed data, not raw RPC dumps.

## Why?

- **Mempool.space** is free but rate-limited and not self-hostable
- **BlockCypher** jumps to $100/mo for serious use
- **Bitcoin API** gives you a clean REST interface to your own node with generous rate limits

## Quickstart

```bash
# Install
pip install bitcoin-api

# Point at your node (or use .env file)
export BITCOIN_RPC_USER=your_user
export BITCOIN_RPC_PASSWORD=your_password

# Run
bitcoin-api
# -> http://localhost:8333/docs
```

### Docker

```bash
cp .env.example .env
# Edit .env with your node credentials
docker compose up -d
```

## Endpoints

All endpoints are under `/api/v1/`. Full OpenAPI docs at `/docs`.

### Free Tier (no key required for anonymous, 30 req/min)

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Node ping |
| `GET /status` | Sync progress, peers, disk |
| `GET /network` | Version, connections, relay fee |
| `GET /blocks/latest` | Latest block analysis |
| `GET /blocks/{height_or_hash}` | Block by height or hash |
| `GET /blocks/{height}/stats` | Raw block statistics |
| `GET /tx/{txid}` | Transaction analysis (fees, SegWit, inscriptions) |
| `GET /tx/{txid}/raw` | Raw decoded transaction |
| `GET /utxo/{txid}/{vout}` | UTXO spent check |
| `GET /mempool` | Mempool analysis (fee buckets, congestion) |
| `GET /mempool/info` | Raw mempool stats |
| `GET /mempool/tx/{txid}` | Mempool entry for a transaction |
| `GET /fees` | Fee estimates (1, 3, 6, 25, 144 blocks) |
| `GET /fees/recommended` | Human-readable fee recommendation |
| `GET /fees/{target}` | Fee estimate for specific block target |

## Examples

```bash
# Health check
curl http://localhost:8333/api/v1/health

# Fee estimates
curl http://localhost:8333/api/v1/fees

# Analyze a transaction
curl http://localhost:8333/api/v1/tx/abc123...

# Latest block
curl http://localhost:8333/api/v1/blocks/latest

# With API key
curl -H "X-API-Key: btc_your_key_here" http://localhost:8333/api/v1/mempool
```

## API Keys

```bash
# Create a free-tier key (100 req/min)
python scripts/create_api_key.py --tier free --label "my-app"

# Create a pro key (500 req/min)
python scripts/create_api_key.py --tier pro --label "production"
```

## Rate Limits

| Tier | Req/min | Req/day | Price |
|------|---------|---------|-------|
| Anonymous | 30 | 1,000 | Free |
| Free (API key) | 100 | 10,000 | Free |
| Pro | 500 | 100,000 | $9/mo |
| Enterprise | 2,000 | Unlimited | $29/mo |

Rate limit info is included in response headers:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`

## Response Format

All endpoints return a standard envelope:

```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2026-03-05T12:00:00+00:00",
    "node_height": 880000,
    "chain": "main"
  }
}
```

Errors follow RFC 7807:

```json
{
  "error": {
    "status": 404,
    "title": "Not Found",
    "detail": "Transaction not found"
  }
}
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
