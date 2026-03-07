# Satoshi API -- Complete Distribution Channel Plan

**Date:** March 7, 2026
**Product:** Satoshi API -- open-source, self-hosted REST API for Bitcoin Core
**Live:** bitcoinsapi.com | GitHub: Bortlesboat/bitcoin-api | PyPI: satoshi-api

---

## TIER 1: HIGH IMPACT (Do These First)

---

### 1. Hacker News -- Show HN

**URL:** https://news.ycombinator.com/submit
**Impact:** HIGH
**Why:** Single highest-leverage launch channel for developer tools. Show HN posts persist on the Show HN page even if they fall off /new, giving extended visibility.

**Best time to post:**
- Data from 23K posts (June 2025 analysis): midnight-1AM PT yields 2x more comments than average (25.7 avg votes vs 18 overall)
- Wednesday has peak traffic (more eyeballs), but weekends are easier to land on front page (less competition)
- Recommendation: **Wednesday 6-8AM ET (3-5AM PT)** for maximum traffic, or **Sunday 11AM-12PM ET** for less competition
- Show HN posts get a second chance via the /shownew page even if they don't hit front page

**Title format:** `Show HN: Satoshi API -- one pip install from Bitcoin node to REST API`

**Post body:** Already drafted at `docs/marketing/show-hn.md` -- ready to go.

**Critical rules:**
- Do NOT ask for upvotes (instant flag/ban)
- Respond to every comment within 1-2 hours
- Keep the post factual, not salesy
- Mention what it's NOT (no address indexing, not a block explorer)

**Expected outcome:** 50-200 GitHub stars, 10-30 comments, 500-2000 unique visitors, potential front page if it catches.

---

### 2. Reddit

**Impact:** HIGH (combined across subreddits)
**Strategy:** Stagger posts across 2-3 days to avoid spam detection. Each post tailored to the subreddit's culture.

#### a) r/Bitcoin (6.5M members)
**URL:** https://reddit.com/r/Bitcoin
**What to write:** Brief, non-technical announcement. Lead with the self-sovereignty angle.
**Draft title:** "I built an open-source REST API for your Bitcoin node -- one pip install, your data stays local"
**Rules:** No direct self-promotion links in post body. Use text post, put links in comments. Emphasize privacy/self-hosted angle.

#### b) r/BitcoinDev (~15K members)
**URL:** https://reddit.com/r/BitcoinDev
**What to write:** Technical deep dive. Code examples, architecture decisions, what RPC calls it wraps.
**Draft title:** "Satoshi API: FastAPI wrapper for Bitcoin Core RPC with analyzed data, MCP integration, and pip install"
**This is the most targeted subreddit.** Small but highly relevant audience.

#### c) r/selfhosted (550K+ members)
**URL:** https://reddit.com/r/selfhosted
**What to write:** Frame as self-hosted infrastructure. Compare to running Esplora (16 CPU/64GB RAM) vs this (pip install on existing node).
**Draft title:** "Self-hosted Bitcoin REST API -- pip install on your existing node, no Docker/Electrs/64GB RAM needed"
**Rules:** r/selfhosted loves lightweight, easy-to-deploy tools. Lead with simplicity.

#### d) r/cryptocurrency (7M+ members)
**URL:** https://reddit.com/r/cryptocurrency
**What to write:** Broader angle -- developer tools, privacy, building on Bitcoin.
**Draft title:** "Built an open-source Bitcoin API that runs on your own node -- free alternative to BlockCypher ($119/mo)"
**Note:** High noise, lower signal. Post here but don't expect deep engagement.

#### e) r/Python (1.3M members)
**URL:** https://reddit.com/r/Python
**What to write:** Focus on the Python/FastAPI implementation. Code quality, typing, testing.
**Draft title:** "I built a production Bitcoin REST API with FastAPI -- 71 endpoints, 228 tests, pip installable"
**Rules:** Must be about the Python aspects, not Bitcoin evangelism.

#### f) r/FastAPI (~30K members)
**URL:** https://reddit.com/r/FastAPI
**What to write:** Architecture showcase. How you structured routers, middleware, auth, caching.
**Draft title:** "FastAPI in production: Bitcoin REST API with tiered auth, rate limiting, caching, and 71 endpoints"

#### g) r/node (~30K members)
**URL:** https://reddit.com/r/node
**Note:** This is for Node.js, not Bitcoin nodes. SKIP unless you add a JS client library.

#### h) Other relevant subreddits:
- **r/programming** (6M) -- for the technical architecture angle
- **r/opensource** (100K+) -- "Apache-2.0-licensed Bitcoin developer tool"
- **r/homelab** (2M+) -- self-hosted infrastructure angle
- **r/LocalLLaMA** (500K+) -- MCP/AI agent integration angle
- **r/MachineLearning** -- only if you write about MCP integration in depth

---

### 3. Stacker News

**URL:** https://stacker.news/
**Impact:** HIGH (for Bitcoin-specific audience)
**What to post:** Link post or text post in the Bitcoin territory.
**Draft title:** "Show SN: Open-source REST API for your Bitcoin node -- pip install, self-hosted, MCP for AI agents"
**How it works:** Post earns sats via upvotes (zaps). Bitcoin-native audience that values self-sovereignty. Very aligned with Satoshi API's positioning.
**Category:** Post to `~bitcoin` territory
**Tips:** Stacker News rewards original content. Include a personal story about why you built it.

---

### 4. MCP Directories (AI Agent Discovery)

**Impact:** HIGH (unique positioning -- only Bitcoin API with MCP)
**This is your differentiated channel.** No competitor has MCP integration.

#### a) Official MCP Registry -- DONE (Mar 7, 2026)
**URL:** https://registry.modelcontextprotocol.io/
**Status:** **PUBLISHED** as `io.github.Bortlesboat/bitcoin-mcp`. Also on PyPI as `bitcoin-mcp` v0.2.2.
**Impact:** Major distribution win. 10,000+ MCP servers in the registry, but we are the only Bitcoin MCP server that queries a local node. Competitors (AbdelStark, JamesANZ, tiero) all use third-party APIs.

#### b) modelcontextprotocol/servers GitHub repo
**URL:** https://github.com/modelcontextprotocol/servers
**Action:** Submit PR to add bitcoin-mcp to the community servers list

#### b2) awesome-blockchain-mcps (NEW)
**URL:** https://github.com/royyannick/awesome-blockchain-mcps
**Action:** Submit PR. Curated list of Blockchain & Crypto MCP servers. Directly targets our audience.
**Status:** TODO

#### c) Smithery
**URL:** https://smithery.ai/
**Action:** Register and list bitcoin-mcp. Smithery provides hosting + discovery for MCP servers. Reach thousands of AI developers.

#### d) PulseMCP
**URL:** https://www.pulsemcp.com/servers
**Action:** Submit listing. 8,590+ servers indexed. Directory is updated daily.

#### e) MCP Server Finder
**URL:** https://www.mcpserverfinder.com/
**Action:** Submit listing.

#### f) Anthropic Community / Claude Discord
**Action:** Share bitcoin-mcp in MCP-related channels. "Here's how to give Claude real-time Bitcoin data."

---

### 5. GitHub Ecosystem

**Impact:** HIGH (long-tail discovery)

#### a) awesome-bitcoin (1.3K stars)
**URL:** https://github.com/igorbarinov/awesome-bitcoin
**Action:** Submit PR to add Satoshi API under "Blockchain API and Web services" section (where mempool.space is listed).
**Line to add:** `* [Satoshi API](https://github.com/Bortlesboat/bitcoin-api) - Self-hosted REST API for Bitcoin Core with analyzed data, MCP integration, and pip install.`

#### b) Other awesome-bitcoin forks (submit to all):
- https://github.com/sr-gi/awesome-bitcoin
- https://github.com/BITVoxy/awesome-bitcoin
- https://github.com/cryptid11/awesome-bitcoin
- https://github.com/JoshuaEstes/awesome-bitcoin

#### c) awesome-selfhosted
**URL:** https://github.com/awesome-selfhosted/awesome-selfhosted
**Action:** Submit PR under "Money, Budgeting & Management" or "Software Development" > API section.

#### d) awesome-fastapi
**URL:** https://github.com/mjhea0/awesome-fastapi
**Action:** Submit PR as a production FastAPI example.

#### e) GitHub Topics
**Action:** Ensure the repo has these topics set: `bitcoin`, `bitcoin-api`, `bitcoin-core`, `rest-api`, `fastapi`, `self-hosted`, `mcp`, `cryptocurrency`, `python`

---

### 6. Dev.to Article

**URL:** https://dev.to/
**Impact:** HIGH (SEO + developer reach)
**Draft:** Already at `docs/marketing/devto-article.md`
**Title ideas:**
- "I Built the SQLite of Bitcoin APIs -- Here's Why"
- "From Bitcoin Node to REST API in 60 Seconds"
- "Why I Built a Self-Hosted Bitcoin API (and Why You Might Want One Too)"
**Tags:** #bitcoin #python #fastapi #api
**Tips:** Cross-post to Hashnode and Medium for additional SEO.

---

## TIER 2: MEDIUM IMPACT (Week 2-4)

---

### 7. Product Hunt

**URL:** https://www.producthunt.com/
**Impact:** MEDIUM-HIGH
**Category:** Developer Tools > APIs
**Best day:** Tuesday-Thursday (or weekend for less competition)
**Launch time:** 12:01 AM Pacific (fixed by PH)

**Preparation checklist:**
- [ ] Tagline (under 60 chars): "Turn your Bitcoin node into a REST API with one command"
- [ ] 5 gallery images showing: (1) pip install terminal, (2) Swagger docs, (3) JSON response example, (4) MCP in Claude Desktop, (5) architecture diagram
- [ ] Maker comment (under 800 chars): Why you built it, what problem it solves, link to try it
- [ ] First comment ready: "AMA -- happy to answer questions about Bitcoin Core RPC, FastAPI architecture, or MCP integration"
- [ ] 10-15 supporters briefed to upvote + comment in first 4 hours
- [ ] Landing page optimized for PH traffic (clear CTA, quick demo)

**Expected outcome:** 50-150 upvotes, badge potential, long-tail SEO from PH listing.

---

### 8. Bitcoin-Specific Forums

#### a) Bitcointalk.org
**URL:** https://bitcointalk.org/index.php?board=6.0 (Development & Technical Discussion)
**Impact:** MEDIUM
**What to write:** [ANN] formatted post with BBCode. Include: what it does, how to install, architecture, links.
**Draft title:** `[ANN] Satoshi API -- Open Source REST API for Bitcoin Core (pip install, self-hosted)`
**Note:** Account rank must be Jr. Member+ for formatted posts. If new account, build some reputation first by posting helpful replies.

#### b) Delving Bitcoin
**URL:** https://delvingbitcoin.org/
**Impact:** MEDIUM (small but influential audience -- core devs read this)
**Category:** "Implementation" (practical implementation techniques)
**What to write:** Technical post about the architecture decisions. Frame as "how I built a REST interface for Bitcoin Core" rather than a product announcement. This audience wants technical substance.
**Caution:** Self-promotion is frowned upon. Lead with technical content, let the project speak for itself.

#### c) Bitcoin Wiki Software List
**URL:** https://en.bitcoin.it/wiki/Software
**Impact:** LOW-MEDIUM (SEO value, permanent listing)
**Action:** Edit the wiki page, add Satoshi API under the appropriate software category.

---

### 9. Nostr

**Impact:** MEDIUM (Bitcoin-native audience, growing)
**How:** Post a long-form note (NIP-23) with the dev.to article content, plus a short-form thread with curl examples showing live API responses.
**Where to post:** Use a Nostr client (Damus, Amethyst, or Primal). Tag with #bitcoin #developer #api #selfhosted.
**Advantage:** No algorithmic suppression. Content lives forever on relays.

---

### 10. Node Distribution Platforms

**Impact:** MEDIUM-HIGH (direct access to node operators)

#### a) Umbrel App Store
**URL:** https://github.com/getumbrel/umbrel-apps
**Action:** Package Satoshi API as an Umbrel app and submit PR. Apps use Docker + YAML manifest. If it already runs on Docker (it does), packaging takes <1 hour.
**This is extremely high-value.** Every Umbrel user already runs a Bitcoin node. One-click install from their app store.

#### b) Start9
**URL:** https://marketplace.start9.com/ (check their developer docs)
**Action:** Package as a Start9 service.

#### c) RaspiBlitz
**URL:** https://github.com/rootzoll/raspiblitz
**Action:** Submit as a community app/plugin.

#### d) myNode
**URL:** https://github.com/mynodebtc/mynode
**Action:** Submit integration.

---

### 11. Twitter/X

**Impact:** MEDIUM
**Strategy:** Thread format showing live API responses. Target Bitcoin Dev Twitter (accounts like @maboroshi_dev, @roasbeef, @aaboronkov).
**Draft thread:**
1. "I built a REST API for Bitcoin Core that you can install with one command. Here's what it does (thread):"
2. Screenshot: `pip install satoshi-api && satoshi-api`
3. Screenshot: curl to /fees/recommended with response
4. Screenshot: curl to /mempool/summary with response
5. "It also has MCP integration so AI agents can query your node directly" + screenshot of Claude using it
6. Links to GitHub, PyPI, live API

**Hashtags:** #Bitcoin #BitcoinDev #OpenSource #API
**Timing:** Post when Bitcoin Dev Twitter is active (weekday mornings ET)

---

### 12. LinkedIn

**Impact:** MEDIUM (for consulting funnel, not direct users)
**Strategy:** Write a post (not article) -- LinkedIn's 2026 algorithm penalizes external links by 60%. Put the link in the first comment instead.

**Draft post:**
```
I built an open-source REST API for Bitcoin Core and shipped it as a pip package.

The problem: Bitcoin Core's JSON-RPC is painful for app developers.
Raw hex blobs, no analysis, no REST conventions.

Alternatives aren't great:
- Esplora needs 16 CPU cores and 64GB RAM to self-host
- BlockCypher charges $119/mo
- Most hosted APIs rate-limit you into oblivion

So I built Satoshi API. One command: pip install satoshi-api

71 endpoints. Analyzed data (fee recommendations, mempool scoring).
AI agent integration via MCP. Self-hosted on your own node.

Open source, Apache-2.0 licensed, free forever for self-hosting.

What's the most painful API integration you've dealt with?

(link in first comment)
```

**Who to tag:** Bitcoin/fintech connections, Python developers, FP&A people who might refer consulting leads.

---

## TIER 3: LOWER IMPACT BUT WORTHWHILE (Month 1-2)

---

### 13. API Directories

#### a) RapidAPI
**URL:** https://rapidapi.com/ (requires account + OpenAPI spec upload)
**Impact:** MEDIUM
**Action:** List the hosted API (bitcoinsapi.com). Upload OpenAPI spec JSON. Set free tier pricing.
**Note:** Good for discovery but most users will self-host.

#### b) APIs.guru
**URL:** https://apis.guru/add-api
**Impact:** LOW-MEDIUM (SEO, machine-readable directory)
**Action:** Submit OpenAPI spec URL. They aggregate definitions, don't host APIs. Need a stable URL to the spec (bitcoinsapi.com/openapi.json).

#### c) Public APIs (GitHub)
**URL:** https://github.com/public-apis/public-apis
**Impact:** MEDIUM (293K stars, massive discovery)
**Action:** Submit PR to add under "Cryptocurrency" category.
**Format:** `| Satoshi API | Bitcoin Core REST API with analyzed data | `apiKey` | Yes | Yes | [Link](https://bitcoinsapi.com/docs) |`

#### d) AlternativeTo
**URL:** https://alternativeto.net/ (click user icon > "Suggest new application")
**Impact:** LOW-MEDIUM
**Action:** Submit Satoshi API. Then search for BlockCypher, mempool.space API, and add Satoshi API as an alternative to each.
**Approval time:** A few days to a week.

---

### 14. Bitcoin Newsletters

#### a) Bitcoin Optech
**URL:** https://bitcoinops.org/
**Impact:** HIGH (if featured -- core devs read this)
**How to get featured:** Optech has a regular "Notable changes to popular Bitcoin software" section. They cover: Bitcoin Core, Core Lightning, Eclair, LDK, LND, libsecp256k1, HWI, Rust Bitcoin, BTCPay Server, BDK.
**Strategy:** You won't get featured as a new project directly. Instead:
1. Make notable releases/changes that show up in Bitcoin ecosystem
2. Get the project mentioned in bitcoin-dev mailing list discussions
3. Email optech@bitcoinops.org with a brief note about the project

#### b) Bitcoin Magazine
**URL:** https://bitcoinmagazine.com/press-releases
**Impact:** MEDIUM
**Action:** Submit a press release. They have a dedicated press release section.
**Cost:** May require payment for sponsored content.

#### c) The Bitcoin Dev Project Newsletter
**URL:** https://bitcoindevs.xyz/
**Impact:** MEDIUM (curated weekly summaries of bitcoin-dev and Delving Bitcoin)
**Action:** If you post on Delving Bitcoin, it may get picked up here.

#### d) Other newsletters to pitch:
- **Marty's Bent** (TFTC) -- Bitcoin-focused, accepts tips
- **Bitcoin Roundtable** -- Weekly Bitcoin news
- **Pomp's newsletter** -- Broader crypto audience

---

### 15. YouTube

**Impact:** MEDIUM (long-tail discovery, builds trust)
**What to create:**

#### a) 3-minute demo video
**Title:** "Bitcoin REST API in 60 Seconds -- pip install satoshi-api"
**Content:** Terminal recording showing: pip install, start server, curl a few endpoints, show Swagger docs. No talking head needed -- screen recording with text overlays.

#### b) 10-minute tutorial
**Title:** "Build a Bitcoin Fee Alert Bot with Python (Satoshi API Tutorial)"
**Content:** Build something useful with the API. Show code, explain the architecture.

#### c) MCP integration demo
**Title:** "Give Claude AI Real-Time Bitcoin Data with MCP"
**Content:** Show bitcoin-mcp in Claude Desktop querying fees, mempool, blocks.

**Channels to target for features/reviews:**
- Bitcoin Audible
- BTC Sessions
- Ministry of Nodes
- 402 Payment Required

---

### 16. Stack Overflow / Bitcoin Stack Exchange

**URL:** https://bitcoin.stackexchange.com/
**Impact:** MEDIUM (long-tail, builds authority)
**Strategy:** Do NOT post promotional answers. Instead:
1. Search for questions about Bitcoin Core RPC, fee estimation APIs, mempool data
2. Answer the question genuinely, then add "Alternatively, if you want a REST wrapper, I built [Satoshi API] that does this"
3. Target questions tagged: `bitcoin-core`, `json-rpc`, `api`, `fee-estimation`, `mempool`

**Example questions to answer:**
- "How to get fee estimates from Bitcoin Core?"
- "REST API for Bitcoin node?"
- "How to decode raw transactions in Python?"
- "Self-hosted Bitcoin API alternatives to BlockCypher?"

---

### 17. Bitcoin Conferences & Meetups

**Impact:** MEDIUM-LOW (networking, credibility)

#### a) Bitcoin++ (developer-focused)
**URL:** https://btcplusplus.dev/
**2026 events:** Floripa (Feb), Las Vegas (Apr), Vienna (May), Nairobi (Jun), Toronto (Jul), Berlin (Nov)
**Action:** Apply to speak at Vienna or Toronto. Topic: "Building Developer Tools on Bitcoin Core" or "MCP: Giving AI Agents Bitcoin Data"

#### b) Bitcoin 2026
**URL:** https://2026.b.tc/
**When:** April 27-29, Las Vegas. Tickets from $199.
**Action:** Attend for networking. Open-source dev track exists. Too late to submit speaker application for April.

#### c) BTC Prague
**URL:** https://btcprague.com/
**When:** June 11-13, 2026
**Action:** Submit speaker application for developer track.

#### d) Local Bitcoin meetups
**URL:** https://www.meetup.com/ (search "Bitcoin" in your area)
**Action:** Offer to demo the API at a local meetup. 5-10 minute lightning talk.

---

### 18. PyPI Optimization

**URL:** https://pypi.org/project/satoshi-api/
**Impact:** MEDIUM (organic discovery by Python developers)
**Action:**
- Ensure description is keyword-rich: "Bitcoin Core REST API", "self-hosted", "MCP", "FastAPI"
- Add classifiers: `Framework :: FastAPI`, `Topic :: Office/Business :: Financial`, `Topic :: Software Development :: Libraries :: Python Modules`
- Add project URLs: Documentation, Source, Changelog, Live Demo
- README should have badges (PyPI version, tests passing, license)

---

### 19. Hashnode / Medium Cross-Posts

**Impact:** LOW-MEDIUM (SEO, broader reach)
**Action:** Cross-post the dev.to article to:
- **Hashnode:** https://hashnode.com/ (use canonical URL pointing to dev.to)
- **Medium:** https://medium.com/ (publish in "Bitcoin" or "Python" publications)
- **Hackernoon:** https://hackernoon.com/ (submit for editorial review)

---

## COMPETITOR MARKETING ANALYSIS

### How mempool.space grew:
1. **Open-source first.** Built the product in the open, let the community adopt it organically.
2. **Umbrel/Start9/RaspiBlitz integration.** One-click install on node distros was their killer distribution channel. Every node runner became a potential user.
3. **Wallet/exchange integrations.** Got mempool.space embedded in wallets, mining pools, and exchanges as the default block explorer.
4. **Direct traffic dominates (72%).** Organic search is only 16%. This means word-of-mouth and bookmarks drive most usage -- not SEO or paid ads.
5. **No paid marketing.** Growth was 100% organic through community adoption and being genuinely useful.
6. **Lesson for Satoshi API:** Get into Umbrel/Start9 ASAP. This is the distribution moat for self-hosted Bitcoin tools.

### How BlockCypher grew:
1. **VC-funded ($3M seed).** Had resources for developer evangelism from day one.
2. **Bitcoin developer meetups.** Founders met investors at SF Bitcoin dev meetups hosted by Foundation Capital.
3. **Multi-chain strategy.** Supported Bitcoin, Ethereum, Litecoin, Dash, Dogecoin -- cast a wide net.
4. **Developer experience focus.** SDKs in multiple languages, Quick Start guides, Postman collections.
5. **Unique technical innovation.** Transaction confidence scoring (99%+ confidence in seconds vs 10-min wait) gave them a talking point.
6. **Lesson for Satoshi API:** The MCP integration is your "transaction confidence score" -- a unique technical innovation that gives you a talking point. Lead with it.

### How Blockstream/Esplora grew:
1. **Blockstream brand.** Already had credibility in Bitcoin space (founded by core devs).
2. **Open-sourced Esplora.** Made it available for anyone to self-host.
3. **Integrated into Liquid/Elements.** Esplora powers blockstream.info, which is a top Bitcoin explorer.
4. **Lesson for Satoshi API:** You don't have Blockstream's brand. Compete on simplicity (pip install vs Docker + Electrs + 64GB RAM).

---

## PRIORITIZED ACTION PLAN

### Week 1: Launch (Days 1-3)
- [ ] **Day 1 (Monday or Wednesday):** Post Show HN (6-8AM ET). Monitor and respond to ALL comments for 12 hours.
- [ ] **Day 1:** Post on Stacker News (~bitcoin territory)
- [ ] **Day 1:** Tweet thread with live API examples
- [ ] **Day 2:** Post on r/BitcoinDev (most targeted audience)
- [ ] **Day 2:** Post on r/selfhosted
- [ ] **Day 2:** Publish dev.to article
- [ ] **Day 3:** Post on r/Bitcoin and r/Python
- [ ] **Day 3:** LinkedIn post (link in first comment)
- [x] **Day 3:** Submit bitcoin-mcp to MCP Registry (**DONE**) + Smithery (TODO) + PulseMCP (TODO)

### Week 2: Ecosystem (Days 4-14)
- [ ] Submit PRs to all awesome-bitcoin lists (5 repos)
- [ ] Submit PR to awesome-selfhosted
- [ ] Submit PR to public-apis/public-apis (293K stars)
- [ ] Submit to AlternativeTo (as alternative to BlockCypher, mempool.space API)
- [ ] Submit to APIs.guru (need OpenAPI spec at stable URL)
- [ ] Post on Nostr (long-form note)
- [ ] Cross-post article to Hashnode and Medium
- [ ] Submit to RapidAPI marketplace
- [ ] Add to Bitcoin Wiki Software page

### Week 3-4: Distribution & Content
- [ ] **Umbrel app submission** (highest-value distribution channel)
- [ ] Start9 service submission
- [ ] RaspiBlitz community app submission
- [ ] Product Hunt launch (pick a Tuesday)
- [ ] Record 3-min demo video for YouTube
- [ ] Post on Bitcointalk Development board
- [ ] Post on Delving Bitcoin (Implementation category, technical framing)
- [ ] Begin answering Stack Overflow / Bitcoin SE questions

### Month 2: Growth
- [ ] Record tutorial video ("Build X with Satoshi API")
- [ ] Record MCP demo video ("Give Claude Bitcoin Data")
- [ ] Email Bitcoin Optech about the project
- [ ] Submit press release to Bitcoin Magazine
- [ ] Submit PR to modelcontextprotocol/servers
- [ ] Apply to speak at Bitcoin++ (Vienna May or Toronto July)
- [ ] Apply to speak at BTC Prague (June)
- [ ] Monitor r/Bitcoin, r/BitcoinDev, Bitcoin SE for API-related questions -- answer with genuine help + mention project

### Month 3: Expand
- [ ] Write "How to build X" tutorials (fee alert bot, portfolio tracker, etc.)
- [ ] Pitch to Bitcoin podcasts (Bitcoin Audible, BTC Sessions)
- [ ] Explore partnerships with wallet projects needing fee data
- [ ] If 100+ stars: submit to Anthropic MCP showcase
- [ ] Post on r/cryptocurrency, r/homelab for broader reach

---

## CHANNELS NOT WORTH PURSUING (YET)

| Channel | Why Skip |
|---------|----------|
| Paid ads (Google/Twitter) | Zero budget, product is free/open-source |
| r/node | Node.js subreddit, not Bitcoin nodes |
| ProductHunt paid promotion | Not worth it for dev tools |
| Bitcoin Magazine sponsored content | Too expensive for current stage |
| Telegram groups | Low signal, high spam, hard to build credibility |
| Facebook groups | Wrong demographic for developer tools |
| Instagram/TikTok | Wrong format entirely |

---

## KEY METRICS TO TRACK PER CHANNEL

| Channel | Metric | Tool |
|---------|--------|------|
| HN | Points, comments, referral traffic | Google Analytics |
| Reddit | Upvotes, comments, click-through | Reddit post analytics |
| Product Hunt | Upvotes, badge, referral traffic | PH dashboard |
| PyPI | Weekly downloads | pypistats.org |
| GitHub | Stars, forks, issues, traffic | GitHub Insights |
| MCP directories | Install count, click-through | Smithery dashboard |
| Dev.to | Views, reactions, bookmarks | Dev.to dashboard |
| Umbrel | App installs | Umbrel metrics (if available) |

---

## DRAFT COPY BANK

### One-liner (for directories/listings):
"Self-hosted REST API for Bitcoin Core with analyzed data, MCP integration, and pip install."

### Two-liner (for awesome-lists):
"Turn your Bitcoin node into a developer-friendly REST API. One command install, 71 endpoints with analyzed data (fee recommendations, mempool scoring), AI agent integration via MCP."

### Elevator pitch (for forums/posts):
"Satoshi API is the SQLite of Bitcoin APIs. One `pip install` gives you a REST API wrapping your Bitcoin Core node with analyzed data -- fee recommendations, mempool congestion scores, decoded transactions -- not raw RPC output. It's the only Bitcoin API with MCP integration for AI agents. Self-hosted, open-source, Apache-2.0 licensed."

### Comparison hook (for Reddit/HN):
"Esplora needs 16 CPU cores and 64GB RAM. BlockCypher charges $119/mo. Satoshi API: `pip install satoshi-api`. Done."
