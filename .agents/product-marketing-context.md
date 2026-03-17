# Product Marketing Context

*Last updated: 2026-03-17*

## Product Overview
**One-liner:** Bitcoin fee intelligence that saves money on every transaction.
**What it does:** Satoshi API tells apps and AI agents *when* to send Bitcoin to minimize fees. It adds congestion scoring, send-or-wait verdicts, and historical fee context on top of raw blockchain data — turning "8 sat/vB" into "wait 2 hours, save 46%." Also serves as the first AI-native Bitcoin data layer with 49 MCP tools for Claude/ChatGPT.
**Product category:** Bitcoin API / Developer tools / AI agent infrastructure
**Product type:** Developer API (SaaS + self-hostable)
**Business model:** Freemium. Anonymous access (free, lightweight GET) → Free tier ($0, 10K req/day) → Pro ($19/mo, 100K req/day) → Enterprise (custom). Infrastructure cost ~$3/mo.

## Target Audience
**Target companies:** Solo developers, AI agent builders, Bitcoin wallet teams, trading bot shops, fintech startups
**Decision-makers:** Individual developers (self-serve), CTOs at small Bitcoin companies, AI/ML engineers building agent tooling
**Primary use case:** Know the cheapest time to send Bitcoin — save money on transaction fees through timing intelligence
**Jobs to be done:**
- "Tell me if I should send Bitcoin now or wait" (fee intelligence)
- "Give my AI agent real Bitcoin data" (MCP/agent infrastructure)
- "Replace my expensive hosted API with something free and self-hostable" (cost savings)
**Use cases:**
- Wallet apps showing "send now for $2.50 or wait for $1.35"
- Trading bots optimizing withdrawal/rebalancing timing
- AI agents answering "should I send Bitcoin right now?" with real data
- Node operators who want a production REST API on top of their node
- Researchers/analysts querying historical fee and block data

## Personas
| Persona | Cares about | Challenge | Value we promise |
|---------|-------------|-----------|------------------|
| AI Agent Builder | Easy integration, token efficiency, reliable data | No good Bitcoin data source for LLMs. Current options are raw RPC or expensive APIs. | `pip install bitcoin-mcp` — 49 tools, zero config, real-time Bitcoin data in your agent's context |
| Bitcoin Wallet Dev | Fee accuracy, UX simplicity, reliability | Users overpay on fees because wallets show raw sat/vB with no context | Send-or-wait verdicts your users actually understand. "Wait 2 hours, save 46%." |
| Trading Bot Dev | Low latency, high rate limits, cost | Existing APIs charge $49-100/mo for the rate limits they need | $19/mo for 100K req/day. Or self-host for $0. Fee intelligence optimizes every transaction. |
| Node Operator | Sovereignty, self-hosting, no third-party dependency | Raw RPC is powerful but not production-ready (no rate limiting, auth, caching) | `git clone && docker-compose up` — your node, your API, your rules |

## Problems & Pain Points
**Core problem:** Bitcoin users and apps overpay on transaction fees because they lack timing intelligence. Raw fee rates (sat/vB) don't tell you whether to send now or wait.
**Why alternatives fall short:**
- **Raw Bitcoin Core RPC:** Gives fee estimates but no context (congestion scoring, historical comparison, send-or-wait). Not REST, no auth, no rate limiting.
- **Mempool.space:** Excellent block explorer, but fee API gives rates without verdicts. No MCP interface. Not self-hostable as an API.
- **BlockCypher/Blockchain.com:** General multi-chain APIs. Shallow Bitcoin coverage, no fee intelligence. $49-100/mo for comparable rate limits.
- **Building it yourself:** Weeks of work to stand up fee analysis, caching, auth, rate limiting, monitoring.
**What it costs them:** Overpaying 20-60% on Bitcoin fees. For businesses processing transactions, this adds up to thousands per year.
**Emotional tension:** "I know I'm overpaying but I don't know when is cheaper." For developers: "I just want Bitcoin data in my agent/app without building infrastructure."

## Competitive Landscape
**Direct:** Mempool.space API — great explorer, but fee data without verdicts. No AI/MCP interface. Not positioned as developer API.
**Direct:** BlockCypher — legacy multi-chain API. Shallow Bitcoin, expensive ($49-100/mo), no fee intelligence.
**Secondary:** Running your own Bitcoin Core RPC — powerful but raw. No REST, no auth, no caching, no fee intelligence layer.
**Indirect:** Not checking fees at all — just sending whenever and accepting whatever fee the wallet suggests.

## Differentiation
**Key differentiators:**
- **Fee intelligence, not just fee rates:** Congestion scoring, send-or-wait verdicts, historical context, cost estimation with savings projections. "Wait 2 hours, save 46%."
- **First AI-native Bitcoin API:** 49 MCP tools vs competitors' ~7. Works with Claude, ChatGPT, any MCP-compatible LLM. Zero config — falls back to hosted API automatically.
- **Self-hostable at $0:** Full API on your own node. Competitors charge $49-100/mo. Our hosted version is also free for most use cases.
- **Full vertical stack:** bitcoinlib-rpc → Satoshi API → bitcoin-mcp → Python SDK → Discord bot. One ecosystem, everything integrated.
**How we do it differently:** We treat fee data as a decision problem, not a display problem. Every fee endpoint answers "what should I do?" not just "what are the numbers?"
**Why that's better:** Developers ship better UX. Users save money. AI agents give useful answers instead of raw data dumps.
**Why customers choose us:** Free, self-hostable, AI-native, and the only API that actually tells you when to send.

## Objections
| Objection | Response |
|-----------|----------|
| "Why not just use mempool.space?" | Mempool shows fees. We tell you what to do about them. Plus: MCP interface, self-hostable API, programmatic access designed for apps not browsers. |
| "This is just a wrapper around Bitcoin Core RPC" | Started there, grew beyond. Fee intelligence (congestion scoring, send-or-wait, historical analysis), MCP tools, WebSocket subscriptions, content pages — none of this exists in RPC. |
| "Why would I pay when the free tier exists?" | Most people won't need to. Pro is for trading bots and apps hitting 10K+ req/day. At $19/mo, one fee-optimized transaction per month pays for itself. |
| "Single-operator project — what about reliability?" | Simple stack = fewer failure modes. Monitored by UptimeRobot. Self-hosting option means zero dependency on us. |
| "Why Bitcoin-only?" | Bitcoin's fee auction model creates real savings opportunities through timing. Ethereum's EIP-1559 is more predictable. We're deep on Bitcoin, not shallow on everything. |

**Anti-persona:** Enterprise teams needing multi-chain coverage, SLA guarantees, and 24/7 support. Developers who need Ethereum/Solana/etc. Users who just want a block explorer UI (use mempool.space).

## Switching Dynamics
**Push:** Overpaying on fees with no visibility. Expensive hosted APIs ($49-100/mo). No good Bitcoin data source for AI agents. Raw RPC is too low-level for production apps.
**Pull:** Free tier covers most needs. Self-hostable = sovereignty. Fee intelligence = real money saved. MCP = AI agents work out of the box. 103 endpoints = comprehensive.
**Habit:** "I've always just used mempool.space" or "My wallet picks the fee for me." Developers: "I built my own RPC wrapper and it works fine."
**Anxiety:** "Is this maintained?" "Will it be around next year?" "Is it actually accurate?" "Single operator = single point of failure."

## Customer Language
**How they describe the problem:**
- "I never know if I'm overpaying on Bitcoin fees"
- "I just want my AI agent to know about Bitcoin"
- "Every Bitcoin API charges way too much for what you get"
- "Setting up Bitcoin Core RPC for a web app is painful"
**How they describe us:**
- "It actually tells you when to send" (vs just showing numbers)
- "The MCP thing just works — pip install and done"
- "Free and I can self-host it? What's the catch?"
**Words to use:** fee intelligence, save money, send-or-wait, AI-native, self-hostable, free, sovereignty, your node, real data, actionable
**Words to avoid:** wrapper, endpoint count (in headlines), production-grade, analyzed data, enterprise-grade, revolutionary, game-changing, cutting-edge
**Glossary:**
| Term | Meaning |
|------|---------|
| Fee intelligence | Congestion scoring + send-or-wait verdicts + savings projections (not just sat/vB) |
| MCP | Model Context Protocol — lets AI agents call tools. Our 49 tools = Bitcoin data for Claude/ChatGPT |
| Send-or-wait | The core decision: should you broadcast your transaction now or wait for lower fees? |
| Congestion score | 0-1 measure of how busy the mempool is. Higher = wait. Lower = send. |
| bitcoin-mcp | Our MCP server package on PyPI. `pip install bitcoin-mcp` — zero config. |
| Self-hostable | Run the full API on your own hardware connected to your own Bitcoin node. $0. |

## Brand Voice
**Tone:** Technical but accessible. Confident without being arrogant. Direct — say what it does, not what it aspires to be.
**Style:** Short sentences. Lead with outcomes. Show code, not slides. Prove claims with data (46.8% savings). No marketing fluff.
**Personality:** Pragmatic, builder-minded, Bitcoin-native, quietly excellent. Like a senior engineer explaining something clearly — not a sales deck.

## Proof Points
**Metrics:**
- 46.8% average fee savings through timing optimization (from real mempool data analysis)
- 103 endpoints across core API, history, content, and indexer
- 616 tests (595 unit + 21 e2e)
- 49 MCP tools (most comprehensive Bitcoin MCP server)
- ~$3/mo infrastructure cost (self-sustaining)
- 256 bitcoin-mcp PyPI downloads/month (organic, zero promotion)
**Customers:** ~100 API key registrations (pre-launch, zero marketing spend)
**Testimonials:** None yet (pre-revenue). First testimonial is a launch priority.
**Value themes:**
| Theme | Proof |
|-------|-------|
| Saves money | 46.8% average fee savings. Send-or-wait verdicts based on real congestion data. |
| AI-native | 49 MCP tools. Zero-config fallback to hosted API. Works with Claude out of the box. |
| Free & sovereign | Self-hostable at $0. Hosted free tier: 10K req/day. No vendor lock-in. |
| Deep, not broad | Bitcoin-only. Fee intelligence layer that no other API has. 103 endpoints of Bitcoin depth. |

## Goals
**Business goal:** First paying customer by April 8, 2026 (30-day decision gate). Path to $950/mo recurring revenue by month 12.
**Conversion action:** Register for free API key → use the API → hit rate limit → upgrade to Pro ($19/mo)
**Current metrics:** ~100 registrations, 0 paid, 256 bitcoin-mcp downloads/mo, 0 marketing spend
