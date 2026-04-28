# Satoshi API Copilot Instructions

Satoshi API is Bitcoin fee intelligence for agents and developers. Lead with outcomes: save money on fees, know when to send, and stop watching block explorers. Avoid selling the product by endpoint counts.

## Project Shape

- FastAPI app in `src/bitcoin_api/`; routers are thin HTTP wrappers and business logic belongs in `src/bitcoin_api/services/`.
- Canonical public API paths use `/api/v1`. Keep generated clients on `/api/v1`.
- The only versionless paid aliases are the x402 hero paths: `/fees/landscape`, `/mining/nextblock`, `/fees/observatory/scoreboard`, `/ai/fees/advice`, and `/ai/explain/transaction/{txid}`. They must stay hidden from OpenAPI and priced by the same x402 rules as their canonical endpoints.
- `bitcoin-mcp` uses `/api/v1/rpc` for hosted fallback. Do not break anonymous read-only RPC fallback without updating the MCP docs and tests.

## x402 Buyer Path

- First paid-call page: `https://bitcoinsapi.com/x402/start`.
- General quickstart: `https://bitcoinsapi.com/quickstart`.
- Discovery: `https://bitcoinsapi.com/.well-known/x402` and `https://bitcoinsapi.com/openapi.json`.
- Payment headers: unpaid responses return `PAYMENT-REQUIRED`; paid retries should use `PAYMENT-SIGNATURE`; successful paid responses include `PAYMENT-RESPONSE`.
- x402 uses USDC on Base. Runtime wiring lives in the `bitcoin-api-x402` extension package.
- Runnable buyer examples live in `examples/x402-paid-call/paid_call.py` and `examples/x402-paid-call/paid-call.ts`.

## Agent/MCP Integration

Use `docs/AGENT_INTEGRATION.md` when adding Satoshi API to another repository's agent instructions. Minimal MCP config:

```json
{
  "mcpServers": {
    "bitcoin": {
      "command": "bitcoin-mcp"
    }
  }
}
```

Set `SATOSHI_API_URL=https://bitcoinsapi.com` only when a client needs an explicit hosted fallback URL.

## Required Maintenance

- If changing behavior, update `docs/SCOPE_OF_WORK.md`.
- If changing operations, monitoring, x402, or deployment behavior, update `docs/OPERATIONS.md`.
- If changing buyer onboarding, keep `/x402/start`, `examples/x402-paid-call/`, `static/llms.txt`, and `static/llms-full.txt` aligned.
- If adding an endpoint, add focused tests and register the router in `src/bitcoin_api/main.py`.

## Useful Verification

```bash
python -m pytest tests/test_api_simplicity.py tests/test_public_discovery_paths.py tests/test_x402_stats.py -q
python -m pytest tests/test_mcp_server.py tests/test_middleware_unit.py -q
```
