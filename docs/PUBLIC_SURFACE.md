# Public Surface Inventory

Last updated: 2026-03-29

This file is the operator-facing inventory of the live public product surface for `bitcoinsapi.com`.

## Surface snapshot

Production discovery snapshot from `https://bitcoinsapi.com/openapi.json` on 2026-03-29:
- 109 public paths
- 110 public operations
- Largest route groups: Analytics (17), Blocks (9), Fees (9), Transactions (9), Mining (7), History Explorer (7), Alerts (6)

Current branch app schema snapshot during the API trial pass:
- 101 local paths
- 102 local operations
- The delta versus production is expected because some live-only/public deployment surfaces are not enabled in the local branch runtime

## Current hosted trial policy

- Anonymous: 200 req/min, 5,000/day, lightweight GET endpoints
- Free API key: 500 req/min, 25,000/day, all standard endpoints
- Pro: 2,000 req/min, 250,000/day
- Enterprise: 5,000 req/min, custom daily policy

## Public website pages

Primary hubs:
- `/` - homepage and API key registration
- `/fees` - live fee tracker and send-or-wait wedge
- `/mcp-setup` - MCP setup guide
- `/bitcoin-api-for-ai-agents` - AI agent landing page
- `/x402` - x402 explainer plus live activity
- `/pricing` - pricing and packaging
- `/guide` - protocol guide
- `/history` - history explorer hub

Comparison and search pages:
- `/vs-mempool`
- `/vs-blockcypher`
- `/best-bitcoin-api-for-developers`
- `/self-hosted-bitcoin-api`
- `/bitcoin-fee-api`
- `/bitcoin-mempool-api`
- `/bitcoin-mcp-setup-guide`
- `/bitcoin-transaction-fee-calculator`
- `/best-time-to-send-bitcoin`
- `/bitcoin-fee-estimator`
- `/bitcoin-api-for-trading-bots`
- `/how-to-reduce-bitcoin-transaction-fees`

Public utility and policy pages:
- `/about`
- `/terms`
- `/privacy`
- `/disclaimer`

Noindex utility pages:
- `/ai`
- `/visualizer`
- `/docs`
- `/redoc`
- `/openapi.json`
- `/history/block`
- `/history/tx`
- `/history/address`

Redirects:
- `/api-docs` -> `/docs`
- `/fee-observatory` -> `/fees`

## Discovery assets for agents and crawlers

- `/robots.txt`
- `/sitemap.xml`
- `/llms.txt`
- `/llms-full.txt`
- `/.well-known/mcp/server-card.json`
- `/openapi.json`

These should stay:
- anonymously accessible
- free of rate limiting
- logged for discovery analytics

## API surface by access mode

Anonymous public endpoints:
- `/api/v1/health`
- `/api/v1/status`
- `/api/v1/fees*`
- `/api/v1/mempool*`
- `/api/v1/blocks/latest`
- `/api/v1/blocks/tip/*`
- `/api/v1/blocks/{height_or_hash}`
- `/api/v1/blocks/{height}/stats`
- `/api/v1/tx/{txid}*`
- `/api/v1/utxo/{txid}/{vout}`
- `/api/v1/mining`
- `/api/v1/mining/difficulty/history`
- `/api/v1/network*`
- `/api/v1/prices`
- `/api/v1/market-data`
- `/api/v1/supply`
- `/api/v1/history/*`
- `/api/v1/indexed/status`
- `/api/v1/analytics/public`
- `/api/v1/x402-info`
- `/api/v1/x402-stats`

API key required:
- `/api/v1/health/deep`
- `/api/v1/mining/pools`
- `/api/v1/mining/revenue`
- `/api/v1/mining/hashrate/history`
- `/api/v1/stats/*`
- `/api/v1/address/*`
- `/api/v1/indexed/address/*`

x402 premium lane:
- `/api/v1/ai/*`
- `/api/v1/mining/nextblock`
- `/api/v1/fees/landscape`
- `/api/v1/fees/observatory/*`
- transaction broadcast route(s)

Admin only:
- `/api/v1/analytics/overview`
- `/api/v1/analytics/founder`
- `/admin/dashboard`
- `/admin/founder`

Streaming:
- `/api/v1/stream/blocks`
- `/api/v1/stream/fees`
- `/api/v1/stream/whale-txs`

## Smoke checks

Core lightweight smoke test:
- `scripts/smoke-test-api.sh`

Comprehensive route validation during the API trial pass:
- `python -m pytest tests/test_admin.py tests/test_ai.py tests/test_alerts.py tests/test_billing.py tests/test_blocks.py tests/test_fees.py tests/test_guide.py tests/test_health.py tests/test_history.py tests/test_indexer_routers.py tests/test_keys.py tests/test_mcp_server.py tests/test_mempool.py tests/test_mining.py tests/test_misc.py tests/test_network.py tests/test_observatory.py tests/test_psbt.py tests/test_rpc_proxy.py tests/test_transactions.py tests/test_x402_stats.py -q`
- Result on 2026-03-29: `524 passed, 3 skipped`

What it covers:
- homepage
- fee tracker
- llms discovery file
- x402 landing page
- docs and OpenAPI
- server card
- public health, fee, mempool, difficulty, analytics
- x402 demo and x402 info

## Operating notes

- Public static pages and discovery assets should never consume anonymous API rate budget.
- AI crawler visibility depends on both `robots.txt` and the crawlability of `/llms.txt`, `/openapi.json`, and the MCP server card.
- The discovery docs (`/llms.txt`, `/llms-full.txt`, `/api/v1/guide`, and the MCP server card) must stay aligned with the real auth and x402 access model or agent adoption trust erodes quickly.
- x402 should be treated as a premium lane inside the broader fee-intelligence product, not as a standalone business line.
- The clearest acquisition wedge remains: "should I send now or wait?" for wallets, bots, and AI agents. x402 fits best as the pay-per-call lane for premium one-shot answers, not the homepage headline.
