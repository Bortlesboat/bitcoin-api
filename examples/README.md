# Satoshi API — Example Projects

Simple, runnable examples for the [Satoshi API](https://bitcoinsapi.com) — a free Bitcoin API for developers.

## Examples

| Example | Description | Method |
|---------|-------------|--------|
| [block-tracker](block-tracker/) | Stream new Bitcoin blocks in real time | SSE |
| [fee-monitor](fee-monitor/) | Stream real-time fee estimates | SSE |
| [mempool-monitor](mempool-monitor/) | Poll mempool congestion stats | REST |

## Quick Start

Each example requires only `requests`:

```bash
pip install requests
cd block-tracker && python block_tracker.py
```

## About

All examples are powered by [bitcoinsapi.com](https://bitcoinsapi.com) — a free, open Bitcoin API with 73 endpoints covering blocks, transactions, fees, mempool, mining, network stats, and more.

No API key required for the free tier.
