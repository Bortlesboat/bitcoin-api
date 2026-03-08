# Launch Day Playbook

**Date:** Monday, March 10, 2026
**Goal:** Get Satoshi API in front of developers across 8+ channels in 48 hours.

---

## Pre-Flight Checklist (do before posting anything)

```bash
# 1. Verify API is up
curl -s https://bitcoinsapi.com/api/v1/health | python -m json.tool

# 2. Verify PyPI is current
pip index versions satoshi-api  # should show 0.3.1

# 3. Run tests
cd ~/Bortlesboat/bitcoin-api && python -m pytest tests/test_api.py -q --tb=no

# 4. Check landing page loads
curl -s -o /dev/null -w "%{http_code}" https://bitcoinsapi.com  # should be 200

# 5. Test key registration works
curl -s -X POST https://bitcoinsapi.com/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","agreed_to_terms":true}' | python -m json.tool

# 6. Baseline metrics (record these numbers)
curl -s -H "X-API-Key: YOUR_ADMIN_KEY" https://bitcoinsapi.com/api/v1/analytics/overview
```

---

## Posting Schedule

### Monday Morning: Primary Channels

| Order | Channel | Title | Draft File |
|-------|---------|-------|------------|
| 1 | **Hacker News** | "Show HN: I built a free Bitcoin API so devs don't have to run a node" | `docs/marketing/drafts/hackernews-show-hn.md` |
| 2 | **r/BitcoinDev** | "What would you want from a REST wrapper around Bitcoin Core RPC?" | `docs/marketing/drafts/reddit-bitcoindev.md` |
| 3 | **Stacker News** | "Your full node already has the data -- you just need a better interface" | `docs/marketing/drafts/stacker-news.md` |

### Monday Afternoon: Secondary Channels

| Order | Channel | Title | Draft File |
|-------|---------|-------|------------|
| 4 | **r/Bitcoin** | "I built an open-source REST API for Bitcoin Core -- here's what it does" | `docs/marketing/drafts/reddit-bitcoin.md` |
| 5 | **r/selfhosted** | "Self-hosted Bitcoin REST API -- query your own node with 73 endpoints" | `docs/marketing/drafts/reddit-selfhosted.md` |

### Tuesday: Technical Channels

| Order | Channel | Title | Draft File |
|-------|---------|-------|------------|
| 6 | **r/Python** | "Built a FastAPI app that wraps Bitcoin Core RPC -- lessons on caching..." | `docs/marketing/drafts/reddit-python.md` |
| 7 | **dev.to** | "Why I built a REST API for Bitcoin Core (and why raw RPC sucks)" | `docs/marketing/devto-article.md` |
| 8 | **Nostr** | Short post with curl example + GitHub link | Write fresh (see template below) |

### Wednesday: Directory Submissions

| Order | Channel | Action |
|-------|---------|--------|
| 9 | awesome-selfhosted | Submit PR |
| 10 | awesome-fastapi | Submit PR |
| 11 | awesome-bitcoin | PR already submitted (#141) — check status |
| 12 | public-apis | PR already submitted (#5397) — check status |

---

## Nostr Post Template

```
I built a free Bitcoin API so developers don't have to run a node.

73 endpoints. pip install. Self-hosted or hosted free tier.

Try it now:
curl https://bitcoinsapi.com/api/v1/fees/recommended

GitHub: github.com/Bortlesboat/bitcoin-api
Docs: bitcoinsapi.com/docs

Apache-2.0. Solo project. Feedback welcome.

#bitcoin #dev #opensource #api
```

---

## HN Title Options (pick the one that feels right)

1. "Show HN: I built a free Bitcoin API so developers don't have to run a node"
2. "Show HN: Satoshi API -- Open-source REST API for Bitcoin Core (Python/FastAPI)"
3. "Show HN: 73-endpoint REST API for your Bitcoin node (pip install, self-hosted)"

Option 1 tells a story (best for clicks).
Option 2 is descriptive (best for credibility).
Option 3 leads with the number (best for curiosity).

**Recommendation: Option 1.** People click stories.

---

## Day-Of Monitoring

After each post, check every 30 minutes for the first 2 hours:

- **HN:** Reply to every comment within 1 hour. Be technical, honest, humble.
- **Reddit:** Reply to every comment. Upvote helpful feedback.
- **Stacker News:** Engage with zaps and replies.
- **Email:** Check api@bitcoinsapi.com for signups or questions.

### What to say if someone asks about missing features:

- **"Why no address history?"** → "I use scantxoutset for balance/UTXOs. Full address history needs an indexer like Electrs — it's on the roadmap if there's demand."
- **"Why not just use mempool.space?"** → "mempool.space is great for browsing. This is for building — structured JSON, API keys, rate limiting, self-hosted on your own node."
- **"How is this different from Esplora?"** → "Esplora needs Docker + Electrs + 64GB RAM. This is pip install and you're running."
- **"Why Python?"** → "FastAPI gives us OpenAPI docs for free, async support, and pip install simplicity. The API returns JSON — your client can be any language."

---

## Evening Check-In

```bash
# Check how many new API keys registered
curl -s -H "X-API-Key: YOUR_ADMIN_KEY" \
  https://bitcoinsapi.com/api/v1/analytics/growth

# Check request volume
curl -s -H "X-API-Key: YOUR_ADMIN_KEY" \
  https://bitcoinsapi.com/api/v1/analytics/overview

# Check which endpoints are popular
curl -s -H "X-API-Key: YOUR_ADMIN_KEY" \
  https://bitcoinsapi.com/api/v1/analytics/endpoints
```

Record these numbers. Compare daily for the first week.

---

## Success Metrics (Week 1)

| Metric | Good | Great | Amazing |
|--------|------|-------|---------|
| API keys registered | 5+ | 20+ | 50+ |
| GitHub stars | 10+ | 50+ | 100+ |
| HN points | 5+ | 30+ | 100+ |
| Requests/day | 100+ | 1,000+ | 5,000+ |
| PyPI downloads/week | 10+ | 50+ | 200+ |

---

## If Nothing Happens (and that's OK)

Most developer tools don't blow up on day 1. If HN gets 3 upvotes and Reddit gets 12 views:

1. Don't panic. This is normal.
2. Wait a week. Post again with a different angle.
3. Try: "I added X to my Bitcoin API" (update posts get more traction than launch posts).
4. Find a Bitcoin Discord or Telegram group and share there.
5. Write a tutorial ("Build a fee alert bot in 50 lines of Python") and post THAT.

The goal is not virality. The goal is 1 developer who builds something with your API.
