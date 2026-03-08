# Bitcoin Mempool Monitor

A simple Python script that polls Bitcoin mempool stats every 30 seconds.

Powered by [bitcoinsapi.com](https://bitcoinsapi.com) — Free Bitcoin API for developers.

## Setup

```bash
pip install requests
python mempool_monitor.py
```

## Sample Output

```
Monitoring Bitcoin mempool...
Powered by bitcoinsapi.com

Mempool | Size: 12.4 MB | Transactions: 8923
Mempool | Size: 11.8 MB | Transactions: 8651
```

## How It Works

The script polls the bitcoinsapi.com mempool endpoint every 30 seconds and prints the current mempool size and transaction count. Useful for monitoring network congestion.

## API Reference

- **Endpoint:** `GET /api/v1/mempool`
- **Auth:** None required (free tier)
- **Docs:** [bitcoinsapi.com](https://bitcoinsapi.com)
