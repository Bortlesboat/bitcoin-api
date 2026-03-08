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
- [x] **Deploy** updated code to production (Mar 8, 2026)
- [x] **IndexNow** auto-runs on every deploy via deploy-api.sh (Mar 8)
- [x] **Google Search Console** verified (meta tag, Mar 7)
- [x] **Bing Webmaster Tools** verified + sitemap submitted (Mar 8)
- [x] Weekly SEO metrics cron (Windows Scheduled Task `SatoshiSEO`, Sundays 9:07am)
- [x] Daily analytics digest email (Windows Scheduled Task `SatoshiDigest`, 8:07am daily)
- [x] UTM tracking on registration (utm_source/medium/campaign captured in api_keys)
- [x] Referrer tracking endpoint (`/analytics/referrers`)
- [x] Conversion funnel endpoint (`/analytics/funnel`)

## Manual Actions Still Required

### Priority 1: MCP Web Directories
- [ ] mcpmarket.com — web form (GitHub login)
- [ ] mcpservers.org — web form (free tier)
- [ ] mcpserverslist.com — web form
- [ ] GitHub MCP Registry — add server.json to bitcoin-mcp repo

### Priority 2: Content & Backlinks
- [ ] Publish dev.to article (paste docs/dev-to-article.md into dev.to/new)
- [ ] Cross-post to Medium (Bitcoin tag)
- [ ] Post on r/bitcoindev (pending mod approval)
- [ ] Bitcoin Talk forum announcement
- [ ] Hacker News "Show HN" post (targeting Mon/Tue for visibility)

### Priority 3: Additional List Submissions
- [ ] Submit to awesome-python lists (API/web section)
- [ ] Submit to awesome-self-hosted lists
- [ ] RapidAPI — list the hosted API (free tier)
- [ ] ProgrammableWeb — submit API listing

### Optional
- [ ] Cloudflare Web Analytics token (beacon already deployed, needs CF dashboard token in .env)

## Metrics & Monitoring

### How to Check
```bash
python scripts/seo_metrics.py              # Full check, saves to DB
python scripts/seo_metrics.py --report     # Latest snapshot
python scripts/seo_metrics.py --history    # Trend over time
python scripts/analytics_digest.py         # Full analytics digest (stdout)
python scripts/analytics_digest.py --email # Send digest via email
```

### Baseline (Mar 7, 2026 — Day 0)
| Metric | Value | Target (30 days) |
|--------|-------|-----------------|
| Pages live | 10/10 | 10/10 |
| GitHub stars | 0 | 10+ |
| PyPI downloads | 74 total | 500+ |
| PRs merged | 0/5 | 3/5 |
| Bing indexed pages | 1 | 9+ |
| Search query mentions | 1/6 | 3/6 |
| AI recommendation | Not mentioned | Mentioned by 1+ AI |
| API key registrations | 10 | 50+ |

### When to Expect Results
- **Week 1:** Pages indexed by Bing/Google (IndexNow submitted, sitemaps submitted)
- **Week 2-3:** Awesome-list PRs start getting reviewed/merged
- **Week 3-4:** Search mentions should start appearing for direct queries
- **Month 2-3:** AI models update their indexes; may start recommending
- **Ongoing:** Each merged awesome-list PR increases AI recommendation probability

### Schedule
- **Daily 8:07am:** Analytics digest email (traffic, funnel, errors, referrers)
- **Weekly Sunday 9:07am:** SEO metrics snapshot to `data/seo_metrics.db`
- **On every deploy:** IndexNow auto-submits all pages to Bing/Yandex
