# Satoshi API Python SDK

Typed Python client for the [Satoshi API](https://bitcoinsapi.com) — Bitcoin node data for developers.

**Zero dependencies.** Uses only Python stdlib. Works with Python 3.10+.

## Install

```bash
pip install satoshi-api
```

## Quick Start

```python
from satoshi_api import SatoshiAPI

api = SatoshiAPI()  # anonymous tier (30 req/min)

# Get current fees
fees = api.fees()
print(fees.data)

# Get a block
block = api.block(840000)
print(f"Block {block.data['height']}: {block.data['tx_count']} transactions")

# Check mempool
mempool = api.mempool()
print(f"Mempool: {mempool.data['size']} transactions")

# Fee recommendation
landscape = api.fee_landscape()
print(landscape.data["recommendation"])
```

## Authentication

```python
# Register for a free API key at https://bitcoinsapi.com/docs
api = SatoshiAPI(api_key="your-api-key")  # 100 req/min

# Or point at your own node
api = SatoshiAPI(base_url="http://localhost:9332")
```

## Error Handling

```python
from satoshi_api import SatoshiAPI, APIError, RateLimitError

api = SatoshiAPI()

try:
    tx = api.transaction("abc123invalid")
except RateLimitError as e:
    print(f"Rate limited. Retry in {e.retry_after}s")
except APIError as e:
    print(f"API error [{e.status}]: {e.detail}")
except ConnectionError:
    print("Cannot reach API")
```

Rate limiting is handled automatically — the SDK reads the `Retry-After` header and retries up to 3 times.

## Response Object

Every method returns a `Response` with:

```python
resp = api.fees()
resp.data          # The response payload (dict)
resp.meta          # Metadata (timestamp, node_height, chain)
resp.height        # Shortcut for meta.node_height
resp.chain         # Shortcut for meta.chain
resp.cached        # Whether response was served from cache
resp.request_id    # Request ID for support/debugging
```

## All Methods

### Status & Health
- `api.health()` — Node health check
- `api.health_deep()` — Deep health (DB, jobs, caches, circuit breaker)
- `api.status()` — Full node status

### Blocks
- `api.block(height_or_hash)` — Block analysis
- `api.block_latest()` — Latest block
- `api.block_stats(height)` — Raw block statistics
- `api.block_header(hash)` — Block header
- `api.block_txids(hash)` — Transaction IDs in block
- `api.block_txs(hash, start, limit)` — Paginated transactions
- `api.tip_height()` / `api.tip_hash()` — Chain tip

### Transactions
- `api.transaction(txid)` — Decoded transaction
- `api.transaction_hex(txid)` — Raw hex
- `api.transaction_status(txid)` — Confirmation status
- `api.transaction_outspends(txid)` — Output spending status
- `api.broadcast(hex)` — Broadcast signed tx (requires key)
- `api.decode(hex)` — Decode without broadcasting (requires key)
- `api.utxo(txid, vout)` — Check UTXO existence

### Fees
- `api.fees()` — All fee estimates
- `api.fee_target(target)` — Specific confirmation target
- `api.fee_recommended()` — Fast/medium/slow
- `api.fee_landscape()` — Full analysis with recommendation
- `api.fee_mempool_blocks()` — Projected mempool blocks
- `api.fee_estimate_tx(inputs, outputs)` — Estimate for specific tx
- `api.fee_history(hours, interval)` — Historical data

### Mempool
- `api.mempool()` — Analysis (size, congestion, buckets)
- `api.mempool_info()` — Raw mempool info
- `api.mempool_txids()` — All mempool txids
- `api.mempool_recent()` — Recently added transactions
- `api.mempool_tx(txid)` — Specific mempool entry

### Mining & Network
- `api.mining()` — Difficulty, hashrate, retarget
- `api.mining_nextblock()` — Next block prediction
- `api.network()` — Connections, version, relay fee
- `api.network_difficulty()` — Difficulty adjustment
- `api.network_forks()` — Chain tips
- `api.validate_address(addr)` — Address validation

### Prices & Tools
- `api.prices()` — BTC price (USD, EUR, GBP, etc.)
- `api.exchange_compare(amount_usd)` — Exchange fee comparison

## Self-Hosted

Point the SDK at your own Satoshi API instance:

```python
api = SatoshiAPI(base_url="http://my-node:9332")
```

## License

MIT
