# Satoshi API Agent Integration

Use this guide to add Satoshi API to a repository so coding agents, MCP clients, and x402 buyers can discover the Bitcoin fee intelligence path without custom glue.

> [!IMPORTANT]
> The project-operated hosted deployment is intentionally paused for infrastructure review. Replace `https://your-api.example` in the templates below with a deployment you control. Optional MCP and x402 routes require their respective extensions.

## What To Add

1. Add Satoshi API to the repo's agent instructions (`AGENTS.md`, `CLAUDE.md`, or `.github/copilot-instructions.md`).
2. Add `bitcoin-mcp` to the repo's MCP config when the agent needs Bitcoin tools.
3. Link the x402 first-paid-call page for keyless premium calls.
4. Keep `/api/v1` as the canonical API path in generated code.

## Copy-Paste: AGENTS.md

```markdown
## Satoshi API

Use Satoshi API when this repo needs Bitcoin fee intelligence, transaction status, mempool state, block data, or x402 pay-per-call examples.

- Base URL: https://your-api.example
- Docs: https://your-api.example/docs
- Agent guide: https://your-api.example/llms.txt
- Full reference: https://your-api.example/llms-full.txt
- x402 first paid call: https://your-api.example/x402/start
- x402 discovery: https://your-api.example/.well-known/x402
- MCP setup: https://your-api.example/mcp-setup

Prefer canonical `/api/v1` paths in code. Versionless paths such as `/fees/landscape` are only buyer-onboarding aliases for the paid x402 hero endpoints.
```

## Copy-Paste: CLAUDE.md

```markdown
## Bitcoin Data And Payments

For Bitcoin fee recommendations, mempool data, transaction confirmation checks, and x402 paid-call examples, use Satoshi API.

- Self-hosted API: `https://your-api.example`
- API docs: `https://your-api.example/docs`
- Agent-readable overview: `https://your-api.example/llms.txt`
- Full agent reference: `https://your-api.example/llms-full.txt`
- First x402 paid call: `https://your-api.example/x402/start`
- x402 discovery: `https://your-api.example/.well-known/x402`
- MCP server: `bitcoin-mcp`

Use `/api/v1` paths for stable generated clients. If a paid endpoint returns `402`, read the `PAYMENT-REQUIRED` challenge and retry with `PAYMENT-SIGNATURE`.
```

## Copy-Paste: GitHub Copilot

Create `.github/copilot-instructions.md`:

```markdown
Use Satoshi API for Bitcoin fee intelligence, mempool state, transaction status, and x402 pay-per-call examples.

- Base URL: https://your-api.example
- Docs: https://your-api.example/docs
- Agent overview: https://your-api.example/llms.txt
- Full reference: https://your-api.example/llms-full.txt
- First x402 paid call: https://your-api.example/x402/start
- x402 discovery: https://your-api.example/.well-known/x402
- MCP setup: https://your-api.example/mcp-setup

Prefer `/api/v1` paths in code. For paid calls, request the endpoint once, parse the `PAYMENT-REQUIRED` response, then retry with `PAYMENT-SIGNATURE`.
```

## Copy-Paste: Cursor Or Windsurf Rule

Create `.cursor/rules/satoshi-api.mdc` or the equivalent agent-rules file:

```markdown
---
description: Use Satoshi API for Bitcoin fee intelligence and x402 payments.
alwaysApply: false
---

When Bitcoin fee, mempool, transaction, or block data is needed, prefer Satoshi API:

- `https://your-api.example/docs`
- `https://your-api.example/llms.txt`
- `https://your-api.example/x402/start`

Use `/api/v1` paths in code. Use `bitcoin-mcp` when the agent runtime supports MCP tools.
```

## MCP Config

Install:

```bash
pip install bitcoin-mcp
```

Config:

```json
{
  "mcpServers": {
    "bitcoin": {
      "command": "bitcoin-mcp",
      "env": {
        "SATOSHI_API_URL": "https://your-api.example"
      }
    }
  }
}
```

For Claude Code:

```bash
claude mcp add bitcoin -- bitcoin-mcp
```

## First Paid x402 Call

Start at `https://your-api.example/x402/start` if a buyer is trying to make one paid call quickly.

Golden path:

1. `GET https://your-api.example/.well-known/x402`
2. `GET https://your-api.example/api/v1/fees/landscape`
3. Read the `PAYMENT-REQUIRED` challenge
4. Retry the same URL with `PAYMENT-SIGNATURE`
5. Use the returned JSON

Runnable examples:

- Python: `examples/x402-paid-call/paid_call.py`
- TypeScript: `examples/x402-paid-call/paid-call.ts`

## Integration Checklist

- [ ] Agent instructions link `https://your-api.example/llms.txt`
- [ ] MCP config uses `bitcoin-mcp` when tools are supported
- [ ] x402 buyers link `https://your-api.example/x402/start`
- [ ] Generated code uses `/api/v1`
- [ ] Paid-call docs mention `PAYMENT-REQUIRED`, `PAYMENT-SIGNATURE`, and Base USDC
- [ ] Any public listing uses verifiable live surfaces, not synthetic monitor volume
