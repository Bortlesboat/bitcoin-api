# Bitcoin Fee Monitor

A simple Python script that streams real-time Bitcoin fee estimates using Server-Sent Events (SSE).

Powered by [bitcoinsapi.com](https://bitcoinsapi.com) — Free Bitcoin API for developers.

## Setup

```bash
pip install requests
python fee_monitor.py
```

## Sample Output

```
Monitoring Bitcoin fee estimates...
Powered by bitcoinsapi.com

Fees (sat/vB) | Fast: 42 | Medium: 18 | Economy: 6
Fees (sat/vB) | Fast: 40 | Medium: 17 | Economy: 5
```

## How It Works

The script connects to the bitcoinsapi.com SSE fee stream and prints updated fee estimates as they change. Useful for wallets, exchanges, or anyone timing transactions.

## API Reference

- **Endpoint:** `GET /api/v1/stream/fees`
- **Auth:** None required (free tier)
- **Docs:** [bitcoinsapi.com](https://bitcoinsapi.com)
