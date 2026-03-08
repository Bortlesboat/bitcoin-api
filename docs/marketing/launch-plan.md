# Satoshi API — Launch Plan & Marketing Tracker

## Pre-Post Checklist (run EVERY TIME before posting a draft)

1. Run `/marketing-sync` — fixes all stale facts across drafts, SEO pages, landing page
2. Re-read the specific draft you're about to post
3. Verify links work: `curl -s -o /dev/null -w "%{http_code}" https://bitcoinsapi.com/docs`
4. Confirm PyPI version matches: `pip index versions satoshi-api`

If any product change happened since drafts were written (new endpoint, feature, pricing change),
`/marketing-sync` will catch it and update all materials automatically.

## Product State (as of 2026-03-08)

| Fact | Value | Source of Truth |
|------|-------|-----------------|
| Version (live) | v0.3.2 | CHANGELOG.md |
| Version (PyPI) | 0.3.2 | pypi.org/project/satoshi-api |
| Endpoints | 74 | router files (marketing_sync.py) |
| Tests | 335 unit + 21 e2e (356 total) | tests/ |
| Install command | `pip install satoshi-api` | pypi |
| Live URL | https://bitcoinsapi.com | Cloudflare Tunnel |
| GitHub stars | 0 | github.com/Bortlesboat/bitcoin-api |
| PyPI downloads | 252 | pypistats.org |
| bitcoin-mcp version | v0.2.2 | pypi.org/project/bitcoin-mcp |
| bitcoin-mcp MCP Registry | **Published** | io.github.Bortlesboat/bitcoin-mcp |
| bitcoin-mcp tools | 35 tools, 6 prompts, 7 resources | bitcoin-mcp README |

## Pre-Launch Checklist (before any marketing push)

- [x] All SEO pages live (7 decision + 2 feature + 1 MCP guide pages)
- [x] robots.txt + sitemap.xml deployed
- [x] JSON-LD structured data on all pages
- [x] Google Search Console verified
- [x] IndexNow submitted to Bing/Yandex
- [x] GitHub: 15 topics, description, homepage set
- [x] GitHub: issue templates, PR template, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT
- [x] GitHub: v0.3.2 release created
- [x] Dev.to article published
- [x] PyPI: publish v0.3.2 — **DONE** (published Mar 8)
- [ ] GitHub social preview image uploaded (og-image.svg ready in static/)
- [ ] Bing Webmaster Tools setup
- [x] All marketing drafts synced to 78 endpoints + Apache-2.0 license
- [x] SEO metrics baseline captured (2026-03-07): 10/10 pages live, 6287 req/24h, 74 PyPI downloads
- [x] CHANGELOG updated with Sprint 15+16 entries
- [x] ADMIN_API_KEY added to .env templates

## Marketing Channels — Execution Tracker

### TIER 1: Reddit Weekend (Sat-Sun Mar 8-9)

| Channel | Status | Draft Ready | Posted | Link |
|---------|--------|-------------|--------|------|
| Reddit r/BitcoinDev | TODO | See drafts below | | |
| Reddit r/selfhosted | TODO | See drafts below | | |
| Reddit r/Bitcoin | TODO | See drafts below | | |
| Stacker News | TODO | See drafts below | | |
| PyPI v0.3.2 publish | **DONE** | N/A | Mar 8 | |
| awesome-selfhosted PR | TODO | N/A | | |
| awesome-fastapi PR | TODO | N/A | | |

### TIER 1.5: Hacker News (Tue Mar 10)

| Channel | Status | Draft Ready | Posted | Link |
|---------|--------|-------------|--------|------|
| Hacker News Show HN | TODO | See drafts below | | |
| Nostr long-form | TODO | | | |

### TIER 2: r/Python + Next Week (Wed Mar 11+)

| Channel | Status | Draft Ready | Posted | Link |
|---------|--------|-------------|--------|------|
| Reddit r/Python | TODO | | | |
| Product Hunt | TODO | | | |
| Bitcointalk | TODO | | | |
| Delving Bitcoin | TODO | | | |
| Umbrel app submission | TODO | | | |
| Start9 app submission | TODO | | | |
| Bitcoin Optech newsletter | TODO | | | |

### TIER 3: Ongoing

| Channel | Status | Notes |
|---------|--------|-------|
| Stack Overflow answers | Ongoing | Answer Bitcoin API questions, link naturally |
| YouTube demo | TODO | 3-min demo video |
| LinkedIn article | TODO | |
| RapidAPI listing | TODO | |
| APIs.guru listing | TODO | |
| AlternativeTo listing | TODO | |

## Already Submitted (tracking)

| Channel | Date | Status | Link |
|---------|------|--------|------|
| awesome-bitcoin PR | Mar 7 | Open | igorbarinov/awesome-bitcoin#141 |
| public-apis PR | Mar 7 | Open | public-apis/public-apis#5403 |
| punkpeye/awesome-mcp-servers PR | Mar 7 | Open | #2847 (82K stars) |
| appcypher/awesome-mcp-servers PR | Mar 7 | Open | #516 (5.2K stars) |
| awesome-selfhosted-data PR | Mar 7 | Open | #2108 |
| mcpmarket.com | Mar 7 | Submitted | |
| mcpservers.org | Mar 7 | Submitted | |
| Dev.to article | Mar 7 | Published | dev.to/bortlesboat/... |
| Google Search Console | Mar 7 | Verified | |
| IndexNow (Bing/Yandex) | Mar 7 | Submitted | |
| MCP Server Finder email | Mar 7 | **Sent** | info@mcpserverfinder.com |
| bitcoin-mcp-setup-guide SEO page | Mar 7 | **Live** | /bitcoin-mcp-setup-guide |
| bitcoin-mcp v0.2.2 on PyPI | Mar 7 | **Published** | https://pypi.org/project/bitcoin-mcp/0.2.2/ |
| MCP Registry (Anthropic official) | Mar 7 | **Published** | io.github.Bortlesboat/bitcoin-mcp |
| All marketing drafts updated with MCP Registry | Mar 7 | **Done** | 6 drafts updated |

## Pending Manual Steps

| Action | Why | Command |
|--------|-----|---------|
| Submit to PulseMCP | Web form — MCP directory | https://www.pulsemcp.com/submit |
| Submit to Smithery | CLI publish — MCP directory | `smithery mcp publish` (needs npm install) |

## MCP Registry Win — Competitive Landscape (Mar 7, 2026)

**bitcoin-mcp is now listed on the official Anthropic MCP Registry.** This is a major distribution milestone.

### Competing Bitcoin MCP Servers (as of Mar 7, 2026)

| Server | Author | Data Source | Local Node? | Registry? | Stars |
|--------|--------|-------------|-------------|-----------|-------|
| **bitcoin-mcp (ours)** | Bortlesboat | Local Bitcoin Core/Knots | **Yes** | **Anthropic Registry + PyPI** | -- |
| bitcoin-mcp | AbdelStark | Third-party APIs | No | npm only | ~50 |
| bitcoin-mcp | JamesANZ | mempool.space API | No | npm only | ~10 |
| bitcoin-mcp | tiero | Third-party APIs | No | No | ~5 |
| bitcoin-mcp-server | nbulian | Mixed (node + APIs) | Partial | No | ~5 |
| bitcoin-mcp | runeape-sats | bitcoin-cli | Yes (CLI) | No | ~2 |
| blockchain-mcp | Tatum | Tatum API (130 chains) | No | No | ~20 |

**Our differentiation is clear:** Only bitcoin-mcp server that (a) talks directly to your local node via RPC, (b) is on PyPI, and (c) is listed in the official Anthropic MCP Registry. Competitors all depend on third-party APIs (mempool.space, Blockstream, etc.) or wrap bitcoin-cli.

### New Action Items from MCP Registry Listing

| Action | Priority | Status |
|--------|----------|--------|
| Submit to awesome-blockchain-mcps (royyannick/awesome-blockchain-mcps) | HIGH | TODO |
| Submit to modelcontextprotocol/servers community list | HIGH | TODO |
| Submit to PulseMCP | HIGH | TODO |
| Submit to Smithery | HIGH | TODO |
| Update all marketing drafts with MCP Registry mention | HIGH | **DONE** |
| Create MCP-specific announcement post (Stacker News / r/LocalLLaMA) | MEDIUM | TODO |
| Add "Listed on the Anthropic MCP Registry" badge to bitcoin-mcp README | MEDIUM | TODO |
| Write SEO page: "best bitcoin mcp server" targeting MCP discovery queries | MEDIUM | TODO |
| Explore bitcoin-mcp landing page at bitcoinsapi.com/mcp | MEDIUM | TODO |

## Content Consistency Rules

When the product changes, these materials MUST be updated:

| If this changes... | Update these... |
|-------------------|-----------------|
| Endpoint count | **Run `python scripts/marketing_sync.py --fix`** (auto-updates all 25+ files) |
| Version number | PyPI, CHANGELOG, GitHub Release, landing page |
| Install command | README, all SEO pages, all marketing drafts |
| Pricing/tiers | Landing page, SEO pages, Reddit/HN drafts |
| MCP integration | AI agents page, marketing drafts mentioning MCP |
| New feature | CHANGELOG, landing page, relevant SEO pages |

## Key Messages (use consistently across all channels)

1. **Primary:** Self-hosted REST API for Bitcoin Core. 78 endpoints. `pip install satoshi-api`.
2. **Differentiator:** Only Bitcoin API with native AI agent support (MCP).
3. **Privacy angle:** Your node, your data. Queries never leave your network.
4. **Developer angle:** Analyzed data, not raw RPC. Fees in sat/vB, congestion levels, human-readable recommendations.
5. **Simplicity:** Three lines to start. pip install, set env vars, run.

## Post Timing Strategy

- Reddit (Sat-Sun Mar 8-9): Stagger posts 4-6 hours apart to avoid looking spammy
- r/BitcoinDev first (most targeted), then r/selfhosted, then r/Bitcoin
- HN Show HN: Tuesday Mar 10, 6-8AM ET (best engagement window)
- r/Python: Wednesday Mar 11
- Product Hunt: Thursday Mar 13 (12:01AM PT)
- Never post all channels same day — spread over 3-5 days
