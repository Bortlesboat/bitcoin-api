# GitHub Agent Integration Targets

Last refreshed: 2026-04-28

This tracker keeps Satoshi API submissions focused on places where agents already look for Bitcoin, MCP, x402, or repository instruction examples. Use `docs/AGENT_INTEGRATION.md` as the source snippet and keep every submission tied to live, verifiable surfaces.

## First-Party

| Target | Status | Next action |
|--------|--------|-------------|
| `Bortlesboat/bitcoin-api` | In progress | Add Copilot instructions, reusable agent integration guide, issue template, and discovery-doc links |
| `Bortlesboat/bitcoin-api-x402` | Local docs patched | Added `AGENTS.md`, `.github/copilot-instructions.md`, and README links to `/x402/start` plus the integration guide |
| `Bortlesboat/lemonade-bitcoin-agent` | Local docs patched | Added `AGENTS.md`, `.github/copilot-instructions.md`, and README links back to the Satoshi API integration kit |
| `Bortlesboat/bitcoin-mcp` | Local docs patched | Added `.github/copilot-instructions.md`; README and AGENTS now link the Satoshi API integration kit |

## x402 Ecosystem

| Target | Why it matters | Submission shape |
|--------|----------------|------------------|
| `xpaysh/awesome-x402` | Curated x402 discovery list | Add Satoshi API as a seller/API and Satoshi Facilitator as infrastructure, with live `/.well-known/x402` and `/x402/start` links |
| `google-agentic-commerce/a2a-x402` | Agent-to-agent commerce examples | Propose Satoshi API as a Bitcoin fee-intelligence paid resource example |
| `dabit3/a2a-x402-typescript` | TypeScript a2a/x402 examples | Add or reference a minimal paid call using `/api/v1/fees/landscape` |
| `qntx/x402-openai-python` | Python agent/x402 bridge | Add Satoshi API as a small paid resource smoke target |
| `ethanniser/x402-mcp` | MCP + x402 surface | Add Satoshi API as an x402 resource usable from MCP clients |
| `microchipgnu/MCPay` | Payment-enabled MCP examples | Add Satoshi API as a Base USDC paid API example |

## GitHub/Copilot Agent Lists

| Target | Why it matters | Submission shape |
|--------|----------------|------------------|
| `github/awesome-copilot` | GitHub-maintained Copilot examples | Submit a concise example of `.github/copilot-instructions.md` for an API/MCP/x402 repo if accepted category fits |
| `luongnv89/agents-dot-md` | AGENTS.md pattern discovery | Add Satoshi API as an example of API + MCP + x402 agent instructions |
| `luisalbertogh/awesome-copilot-custom-agents` | Custom Copilot agent examples | Submit the Satoshi API integration snippet if repo accepts external examples |
| `attentiondotnet/awesome-copilot-agents` | Copilot agent resource list | Submit after first-party instructions are merged |

## Submission Evidence To Reuse

- Website: https://bitcoinsapi.com
- API docs: https://bitcoinsapi.com/docs
- Agent overview: https://bitcoinsapi.com/llms.txt
- Full agent reference: https://bitcoinsapi.com/llms-full.txt
- x402 first paid call: https://bitcoinsapi.com/x402/start
- x402 discovery: https://bitcoinsapi.com/.well-known/x402
- Paid-only OpenAPI: https://bitcoinsapi.com/openapi.json
- MCP setup: https://bitcoinsapi.com/mcp-setup
- MCP server card: https://bitcoinsapi.com/.well-known/mcp/server-card.json
- GitHub integration guide: `docs/AGENT_INTEGRATION.md`

## Submission Rules

- Use `/api/v1` paths in code examples.
- Lead with fee intelligence that saves money or time, not endpoint counts.
- Mention synthetic smoke tests only as uptime evidence, not organic demand.
- Include one live proof URL per submission.
