# Satoshi API — Launch Plan & Marketing Tracker

## Pre-Post Checklist (run EVERY TIME before posting a draft)

1. Run `/marketing-sync` — fixes all stale facts across drafts, SEO pages, landing page
2. Re-read the specific draft you're about to post
3. Verify links work: `curl -s -o /dev/null -w "%{http_code}" https://bitcoinsapi.com/docs`
4. Confirm PyPI version matches: `pip index versions satoshi-api`

If any product change happened since drafts were written (new endpoint, feature, pricing change),
`/marketing-sync` will catch it and update all materials automatically.

## Product State (as of 2026-03-07)

| Fact | Value | Source of Truth |
|------|-------|-----------------|
| Version (live) | v0.3.1 | CHANGELOG.md |
| Version (PyPI) | 0.3.1 — NEEDS UPDATE | pypi.org/project/satoshi-api |
| Endpoints | 48 | docs/SCOPE_OF_WORK.md |
| Tests | 129 unit + 21 e2e (150 total) | tests/ |
| Install command | `pip install satoshi-api` | pypi |
| Live URL | https://bitcoinsapi.com | Cloudflare Tunnel |
| GitHub stars | 0 | github.com/Bortlesboat/bitcoin-api |
| PyPI downloads | 252 | pypistats.org |

## Pre-Launch Checklist (before any marketing push)

- [x] All SEO pages live (7 decision + 2 feature pages)
- [x] robots.txt + sitemap.xml deployed
- [x] JSON-LD structured data on all pages
- [x] Google Search Console verified
- [x] IndexNow submitted to Bing/Yandex
- [x] GitHub: 15 topics, description, homepage set
- [x] GitHub: issue templates, PR template, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT
- [x] GitHub: v0.3.1 release created
- [x] Dev.to article published
- [ ] PyPI: publish v0.3.1 (BLOCKER — marketing says "pip install" but PyPI is stale). Build verified locally.
- [ ] GitHub social preview image uploaded (og-image.svg ready in static/)
- [ ] Bing Webmaster Tools setup
- [x] All marketing drafts synced to 48 endpoints + Apache-2.0 license
- [x] SEO metrics baseline captured (2026-03-07): 10/10 pages live, 6287 req/24h, 74 PyPI downloads
- [x] CHANGELOG updated with Sprint 15+16 entries
- [x] ADMIN_API_KEY added to .env templates

## Marketing Channels — Execution Tracker

### TIER 1: Do Now (Mar 7-8)

| Channel | Status | Draft Ready | Posted | Link |
|---------|--------|-------------|--------|------|
| Reddit r/BitcoinDev | TODO | See drafts below | | |
| Reddit r/selfhosted | TODO | See drafts below | | |
| Reddit r/Bitcoin | TODO | See drafts below | | |
| Stacker News | TODO | See drafts below | | |
| PyPI v0.3.1 publish | TODO | N/A | | |
| awesome-selfhosted PR | TODO | N/A | | |
| awesome-fastapi PR | TODO | N/A | | |

### TIER 1.5: This Weekend (Mar 8-9)

| Channel | Status | Draft Ready | Posted | Link |
|---------|--------|-------------|--------|------|
| Hacker News Show HN | TODO | See drafts below | | |
| Nostr long-form | TODO | | | |

### TIER 2: Next Week (Mar 10-14)

| Channel | Status | Draft Ready | Posted | Link |
|---------|--------|-------------|--------|------|
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
| awesome-bitcoin PR | Mar 7 | Open | #141 |
| public-apis PR | Mar 7 | Open | #5403 |
| mcpmarket.com | Mar 7 | Submitted | |
| mcpservers.org | Mar 7 | Submitted | |
| Dev.to article | Mar 7 | Published | dev.to/bortlesboat/... |
| Google Search Console | Mar 7 | Verified | |
| IndexNow (Bing/Yandex) | Mar 7 | Submitted | |

## Content Consistency Rules

When the product changes, these materials MUST be updated:

| If this changes... | Update these... |
|-------------------|-----------------|
| Endpoint count | Landing page, README, all SEO pages, PyPI description, all drafts |
| Version number | PyPI, CHANGELOG, GitHub Release, landing page |
| Install command | README, all SEO pages, all marketing drafts |
| Pricing/tiers | Landing page, SEO pages, Reddit/HN drafts |
| MCP integration | AI agents page, marketing drafts mentioning MCP |
| New feature | CHANGELOG, landing page, relevant SEO pages |

## Key Messages (use consistently across all channels)

1. **Primary:** Self-hosted REST API for Bitcoin Core. 48 endpoints. `pip install satoshi-api`.
2. **Differentiator:** Only Bitcoin API with native AI agent support (MCP).
3. **Privacy angle:** Your node, your data. Queries never leave your network.
4. **Developer angle:** Analyzed data, not raw RPC. Fees in sat/vB, congestion levels, human-readable recommendations.
5. **Simplicity:** Three lines to start. pip install, set env vars, run.

## Post Timing Strategy

- Reddit: Stagger posts 4-6 hours apart to avoid looking spammy
- r/BitcoinDev first (most targeted), then r/selfhosted, then r/Bitcoin
- HN Show HN: Sunday 11AM ET or Monday 6-8AM ET
- Product Hunt: Tuesday 12:01AM PT
- Never post all channels same day — spread over 3-5 days
