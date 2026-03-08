# Bitcoin Block Tracker

A simple Python script that streams new Bitcoin blocks in real time using Server-Sent Events (SSE).

Powered by [bitcoinsapi.com](https://bitcoinsapi.com) — Free Bitcoin API for developers.

## Setup

```bash
pip install requests
python block_tracker.py
```

## Sample Output

```
Watching for new Bitcoin blocks...
Powered by bitcoinsapi.com

New Block #884210 | Hash: 00000000000000... | Txs: 3421
New Block #884211 | Hash: 00000000000000... | Txs: 2876
```

## How It Works

The script connects to the bitcoinsapi.com SSE stream endpoint and prints each new block as it's mined (~every 10 minutes on average).

## API Reference

- **Endpoint:** `GET /api/v1/stream/blocks`
- **Auth:** None required (free tier)
- **Docs:** [bitcoinsapi.com](https://bitcoinsapi.com)
