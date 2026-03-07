# SEO & AI Search Optimization Checklist

## Completed

- [x] robots.txt with AI crawler directives (GPTBot, ClaudeBot, CCBot, PerplexityBot)
- [x] sitemap.xml with 9 URLs
- [x] JSON-LD structured data on landing page (SoftwareApplication, WebAPI, Organization, FAQPage)
- [x] Improved meta tags (wiki-voice description, keywords)
- [x] 7 SEO decision/feature pages with JSON-LD FAQPage schemas
- [x] Internal cross-linking between all pages
- [x] FastAPI routes for all static pages + IndexNow key
- [x] dev.to article draft (docs/dev-to-article.md)
- [x] PR: igorbarinov/awesome-bitcoin #141 (73.8K stars)
- [x] PR: public-apis/public-apis #5397
- [x] PR: CoinQuanta/awesome-crypto-api #9
- [x] PR: punkpeye/awesome-mcp-servers #2847 (82.4K stars)
- [x] PR: appcypher/awesome-mcp-servers #516
- [x] Issue: APIs-guru/openapi-directory #1611
- [x] Email: b10c fee API list (blog@b10c.me)
- [x] SEO metrics tracker script (scripts/seo_metrics.py)
- [x] IndexNow submission script (scripts/submit_indexnow.sh)

## Manual Actions Still Required

### Priority 1: Deploy New Code
- [ ] **Deploy** updated code to production (new pages, routes, robots.txt, sitemap)
- [ ] **Run IndexNow:** `bash scripts/submit_indexnow.sh` (after deploy)

### Priority 2: Search Engine Consoles
- [ ] **Bing Webmaster Tools** (ChatGPT uses Bing's index)
  1. Go to https://www.bing.com/webmasters
  2. Sign in with Microsoft account
  3. Add site: bitcoinsapi.com
  4. Verify via DNS TXT record or CNAME in Cloudflare
  5. Submit sitemap: https://bitcoinsapi.com/sitemap.xml
  6. Request indexing for all 9 URLs

- [ ] **Google Search Console**
  1. Go to https://search.google.com/search-console
  2. Add property: bitcoinsapi.com
  3. Verify via DNS TXT in Cloudflare
  4. Submit sitemap
  5. Request indexing

### Priority 3: MCP Web Directories
- [ ] mcpmarket.com — web form (GitHub login)
- [ ] mcpservers.org — web form (free tier)
- [ ] mcpserverslist.com — web form
- [ ] GitHub MCP Registry — add server.json to bitcoin-mcp repo

### Priority 4: Content & Backlinks
- [ ] Publish dev.to article (paste docs/dev-to-article.md into dev.to/new)
- [ ] Cross-post to Medium (Bitcoin tag)
- [ ] Post on r/Bitcoin, r/bitcoindev (when appropriate)
- [ ] Bitcoin Talk forum announcement
- [ ] Hacker News "Show HN" post (targeting Mon/Tue for visibility)

### Priority 5: Additional List Submissions
- [ ] Submit to awesome-python lists (API/web section)
- [ ] Submit to awesome-self-hosted lists
- [ ] RapidAPI — list the hosted API (free tier)
- [ ] ProgrammableWeb — submit API listing

## Metrics & Monitoring

### How to Check
```bash
python scripts/seo_metrics.py              # Full check, saves to DB
python scripts/seo_metrics.py --report     # Latest snapshot
python scripts/seo_metrics.py --history    # Trend over time
```

### Baseline (Mar 7, 2026 — Day 0)
| Metric | Value | Target (30 days) |
|--------|-------|-----------------|
| Pages live | 0/10 (not deployed) | 10/10 |
| GitHub stars | 0 | 10+ |
| PyPI downloads | 74 total | 500+ |
| PRs merged | 0/5 | 3/5 |
| Bing indexed pages | 1 | 9+ |
| Search query mentions | 1/6 | 3/6 |
| AI recommendation | Not mentioned | Mentioned by 1+ AI |

### When to Expect Results
- **Week 1:** Pages indexed by Bing/Google after deployment + IndexNow
- **Week 2-3:** Awesome-list PRs start getting reviewed/merged
- **Week 3-4:** Search mentions should start appearing for direct queries
- **Month 2-3:** AI models update their indexes; may start recommending
- **Ongoing:** Each merged awesome-list PR increases AI recommendation probability

### Schedule
Run `python scripts/seo_metrics.py` weekly (Sundays). Compare against baseline.
Candidate for GMKtec cron: `7 9 * * 0` (Sundays 9:07am)
