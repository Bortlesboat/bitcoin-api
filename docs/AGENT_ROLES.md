# Agent Employee Coordination — Satoshi API

This document defines the 12 agent "employees" that maintain Satoshi API, their responsibilities, and the trigger matrix that coordinates their work.

## Company Status (Quick Reference)

**All agents: read this block first. It has the volatile facts that change every release.**

| Fact | Value | Updated |
|------|-------|---------|
| **Version** | 0.3.3 | 2026-03-08 |
| **Endpoints** | 86 total (82 core + 4 indexer) | 2026-03-09 |
| **Tests** | 400 unit + 21 e2e = 421 total | 2026-03-08 |
| **Routers** | 20 core + 3 indexer = 23 | 2026-03-08 |
| **Live URL** | https://bitcoinsapi.com | — |
| **Infra cost** | ~$3/mo | 2026-03-08 |
| **Revenue** | Pre-revenue (Stripe wired, Pro tier hidden) | 2026-03-08 |
| **Latest release** | v0.3.4 — RPC proxy endpoint for bitcoin-mcp zero-config, 428 tests, 83 endpoints, 24 routers | 2026-03-09 |
| **MCP tools** | 43 tools, 6 prompts, 7 resources (bitcoin-mcp) | 2026-03-09 |
| **Launch status** | **LAUNCH SPRINT ACTIVE** — content pipeline loaded, T-0 = Show HN Tuesday | 2026-03-09 |
| **Open issues** | None critical — ToS §7 stale-data addressed by /disclaimer page | 2026-03-09 |
| **Awesome-list PRs** | 6 open (awesome-bitcoin, crypto-api, lopp.net, public-apis, awesome-mcp-servers, awesome-fastapi) | 2026-03-09 |

**When you find a fact here is wrong, update it immediately and note the date.**

### The Any-Limit Filter (MANDATORY — applied to ALL decisions)

Every feature, endpoint, marketing claim, and roadmap item must pass this test:

> **Does it make money, save money, or save time/effort in a substantial way?**

If the answer is "not really" — it's infrastructure, not product. Don't lead with it, don't prioritize it, don't brag about it.

**What passes the filter:**
- Fee intelligence ("send now or wait") — **saves money** on every Bitcoin transaction
- Payment confirmation monitoring — **saves time** (stop watching block explorers)
- MCP/AI agent layer — **saves time** (devs skip building Bitcoin plumbing)
- Exchange fee comparison — **saves money** (find cheapest on-ramp)

**What does NOT pass (still useful, but never lead with it):**
- Endpoint count (nobody cares about 80 endpoints)
- Thin RPC wrappers (raw block/tx data available everywhere)
- Self-hosting pitch (secondary, not primary value prop)
- Internal architecture sophistication (circuit breakers, caching — invisible to users)

**Product positioning (Mar 8 pivot):**
- FROM: "Bitcoin API with 80 endpoints"
- TO: "Bitcoin fee intelligence that saves you money on every transaction"

Source: Reddit feedback from u/Any-Limit-7282, adopted as company strategy.

### Current Sprint: Launch Campaign (Mar 9-22)

**Context:** External agency-agents consult (61 specialized AI agents) reviewed Satoshi API on Mar 9. Unanimous finding: **distribution problem, not product problem.** Full report: `memory/satoshi-api/agency-consult.md`.

**Key insight adopted:** Launch is a 30-day campaign, not a single event. "First Bitcoin MCP server" positioning window is 3-6 months before competitors ship MCP tooling.

**Content pipeline (ALL READY — in `docs/marketing/`):**

| Asset | File | Status | Owner |
|-------|------|--------|-------|
| Show HN post | `show-hn.md` | READY — post Tuesday morning | Marketing |
| dev.to article | `devto-article.md` | READY — publish same day as HN | Marketing |
| 5 X/Twitter threads | `twitter-threads.md` | READY — Thread 1 on launch day | Marketing |
| Fee dashboard tutorial | `tutorial-fee-dashboard.md` + `examples/fee_dashboard.py` | READY + code verified | Agent Advocate |
| Python SDK client | `examples/satoshi_client.py` (46 methods) | READY — single-file drop-in | Agent Advocate, Architect |
| Directory submission guide | `directory-submissions.md` | READY — 6 directories, copy-paste | Marketing, Admin |
| Submission kit | `LAUNCH_SUBMISSION_KIT.md` | READY — one-liners, descriptions, tags | Marketing |
| Fee commentary playbook | `fee-commentary-playbook.md` | READY — recurring X content | Marketing |

**Launch week actions (each agent's role):**

| Agent | Action Required | When |
|-------|----------------|------|
| **Marketing** | Verify all content passes Any-Limit Filter before publish. Track HN/Reddit/directory performance. | T-0 through T+7 |
| **PM** | Define activation metric (suggested: registered + 3 API calls in 24h). Run Mar 15 signal check. | Before T-0, T+5 |
| **UX** | Monitor first-user experience. Flag any onboarding friction from HN/Reddit feedback. | T+1 through T+7 |
| **Finance** | Baseline pre-launch metrics. Track CAC by channel after launch. | T-1, T+7 |
| **Agent Advocate** | Verify SDK client works against live API. Monitor MCP directory acceptance. | Before T-0, ongoing |
| **Admin Assistant** | Stamp all content with correct counts (43 MCP tools, 83 endpoints, 428 tests). Verify cross-doc consistency. | Before T-0 |
| **QA** | Run full test suite pre-launch. Verify examples/ code runs. | Before T-0 |
| **Security** | Monitor for abuse after HN traffic spike. | T+0 through T+3 |
| **Analytics** | Set up PostHog funnel: visit → register → first call → 3+ calls. | Before T-0 |
| **Architect** | Review SDK client (`satoshi_client.py`) for API path accuracy. | Before T-0 |
| **Ops** | Ensure api.log rotation is set up before traffic spike. DB backup before launch. | Before T-0 |
| **Legal** | No action unless new claims are added to marketing materials. | On-call |

**Awesome-list PRs to monitor (6 open):**
1. `igorbarinov/awesome-bitcoin` #142 — waiting
2. `CoinQuanta/awesome-crypto-api` #11 — waiting
3. `jlopp/lopp.net` #1191 — waiting
4. `public-apis/public-apis` #5403 — waiting
5. `punkpeye/awesome-mcp-servers` #2980 — submitted Mar 9
6. `mjhea0/awesome-fastapi` #236 — updated Mar 9

---

## The 12 Employees

All 12 agents report directly to the CEO. Fully flat org — no intermediate management layers.

### Strategic
| Role | Skill | Responsibility |
|------|-------|---------------|
| **Product Manager** | `/pm-review` | Feature strategy, competitive gaps, prioritization, pricing, 90-day roadmap |
| **UX/Design Lead** | `/ux-review` | Customer journey, landing page, registration flow, docs UX, error messages |
| **CFO / Finance** | `/finance-review` | Cost analysis, unit economics, pricing validation, revenue projections, infra cost optimization |
| **Agent/Token Advocate** | `/agent-advocate` | Ensure every decision accounts for agent consumers and token efficiency — voice of the machine at the table |

### Operations
| Role | Skill | Script | Responsibility |
|------|-------|--------|---------------|
| **Legal** | `/legal-review` | `scripts/legal_audit.py` | ToS, privacy policy, disclaimers, compliance |
| **Marketing** | `/marketing-sync` | `scripts/marketing_sync.py` | Landing page, SEO, endpoint counts, feature claims |
| **Security** | `/security-review` | `scripts/security_audit.py` | Headers, auth, rate limits, CSP, threat model |
| **Architect** | `/architecture-review` | N/A (agent-only) | SCOPE_OF_WORK currency, CLAUDE.md, code quality, module coupling, architecture |
| **QA Lead** | `/qa-review` | N/A (agent-only) | Tests, coverage gaps, regressions, test-to-docs sync |
| **Analytics** | `/analytics-review` | N/A (agent-only) | Data collection changes, logging, metrics |
| **Chief of Staff** | `/ops-review` | N/A (agent-only) | Data lifecycle, metrics design, process automation, standards enforcement, org maintenance, headcount planning |
| **Admin Assistant** | `/admin-assistant` | `scripts/stamp_endpoint_count.py` | Endpoint count stamping, doc consistency, guide catalog sync, cross-file reference audits |

### Deprecated Wrappers (backward compat)
| Old Skill | Replacement | Notes |
|-----------|-------------|-------|
| `/code-review` | `/qa-review` + `/architecture-review` | Runs both in sequence |
| `/product-review` | `/pm-review` + `/ux-review` | Runs both in sequence |

### Collaboration Pairs
These are NOT reporting lines — they're documented so agents know who to consult:
- **PM + UX** — feature specs, customer journey
- **Architect + QA** — code quality, test strategy
- **Marketing + UX** — landing page, docs UX
- **CFO + PM** — pricing, roadmap economics
- **Legal + Security** — compliance, data protection
- **Analytics + PM** — usage data, feature decisions
- **Analytics + CFO** — revenue metrics, cost tracking
- **Agent Advocate + PM** — feature design from agent consumer perspective
- **Agent Advocate + Architect** — response structure, token efficiency, API ergonomics
- **Agent Advocate + UX** — agent onboarding, error self-correction, discoverability
- **Agent Advocate + Marketing** — agent-first positioning, MCP/tool compatibility claims
- **Chief of Staff + ALL** — org health, process gaps, standards enforcement, data lifecycle

## Design Rationale

Based on research into multi-agent patterns (Cursor's Planner/Worker/Judge hierarchy, VoltAgent's 127 agents, Claude Code swarm orchestration with TeammateTool), we chose **human-in-the-loop trigger matrix** over autonomous swarms:

- **Swarm pattern** (parallel workers, inbox messaging, task claiming) is for 5-10 concurrent agents on massive codebases. Overkill for a single developer.
- **Trigger matrix** = each agent reports what OTHER agents should review. Human decides when/whether to run them.
- **Slash commands** are the interface. Each agent reads this file, does its job, logs its run, and reports triggers.

Key insight from Mike Mason's 2026 analysis: "Orchestrated agents on bounded tasks with human oversight produce value. Autonomous agents don't work reliably." Google's DORA Report confirms: 90% AI adoption increase → 9% bug rate climb when agents run unsupervised.

**Why flat at 12:** At 12 agents with 1 human, hierarchy demotes key functions (Security under Product? Legal under Finance? No). The trigger matrix already coordinates cross-agent work. Real startups at this size are flat.

## Agent Run Protocol

Every agent follows this protocol:

1. **Read this trigger matrix** before starting work
2. **Do your job** — run audit script, review code, fix issues
3. **Log your run** — update the Audit Trail table with date, result, and downstream triggers
4. **Report triggers** — list which other agents should run next (do NOT auto-invoke them)
5. **Update performance tracking** — record checks/fixed/outstanding in the Performance Tracking table

## Standardized Output Format

All agents emit this header:

```
### [Agent Name] Report — YYYY-MM-DD
- **Status:** PASS / PASS WITH WARNINGS / FAIL
- **Checks:** X passed, Y warnings, Z errors
- **Items Fixed:** [list or "None"]
- **Outstanding:** [list or "None"]
- **Downstream Triggers:**
  - [ ] /skill-name — reason
  - [x] /skill-name — No trigger
```

Finance and PM add detailed tables BELOW the standard header.

## Trigger Matrix

When a change of the given type occurs, the listed agents should be triggered for review.

| Change Type | Triggers |
|-------------|----------|
| New endpoint added | Marketing, Security, QA Lead, Architect, PM, Ops, **Admin Assistant**, **Agent Advocate** |
| New data collection (PII) | Legal, Security |
| New third-party integration | Legal, Security |
| Pricing/tier change | Legal, Marketing, PM, Finance |
| License change | Legal, Marketing, Architect |
| New marketing claim | Legal |
| Auth/rate-limit change | Security, Marketing, **Agent Advocate** |
| Test count change | Marketing, QA Lead, Admin Assistant |
| New static page | Marketing (sitemap), Architect (CSP whitelist), Admin Assistant (sitemap audit) |
| DB schema change | Security, Architect |
| Config/env var change | Architect, Security, Admin Assistant (env doc sync), **update OPERATIONS.md** |
| Deployment/process change | Architect, **update OPERATIONS.md** |
| Customer journey change | PM, UX, Marketing, **Agent Advocate** |
| Infrastructure cost change | Finance, Architect |
| Competitive landscape shift | PM, Marketing |
| Revenue/usage milestone | Finance, PM |
| Service layer change | Security, Architect |
| Logging/observability change | Analytics, Security, Architect |
| Landing page / docs UX change | UX, Marketing |
| Response schema change | Agent Advocate, Architect, QA Lead |
| Error message change | UX, QA Lead, **Agent Advocate** |
| Agent added/removed/split | Ops (update AGENT_ROLES.md, all downstream docs), Admin Assistant (count sync) |
| Data retention policy change | Ops, Legal, Analytics |
| Process/automation change | Ops, Architect |
| Cross-doc inconsistency found | Ops (sync all references), Admin Assistant (full audit) |
| Version bump | Admin Assistant (version refs), Marketing (claims) |
| Pre-deploy gate | Admin Assistant (full consistency sweep) |

## Cross-Reference: Who Cares About What

| File/Area | PM | UX | Finance | Legal | Marketing | Security | Architect | QA | Analytics | Ops | Admin | Agent |
|-----------|----|----|---------|-------|-----------|----------|-----------|-----|-----------|-----|-------|-------|
| `static/terms.html` | - | - | - | Owner | - | - | - | - | - | - | - | - |
| `static/privacy.html` | - | - | - | Owner | - | Reads | - | - | Reads | Reads | - | - |
| `static/index.html` | Reads | Owner | - | Reads | Owner | Reads | - | - | - | - | Counts | Reads |
| `middleware.py` | - | - | - | Reads | - | Owner | Reads | - | - | - | - | Reads |
| `config.py` (pricing/tiers) | Reads | - | Reads | - | - | Reads | Owner | - | - | - | Flags | Reads |
| `routers/*.py` | Reads | Reads | - | Reads | Reads | Reads | Owner | Reads | Reads | - | Catalog | **Owner** |
| `services/*.py` | - | - | - | - | Reads | Reads | Owner | - | - | - | - | Reads |
| `db.py` / migrations | - | - | - | - | - | Reads | Owner | - | Owner | Reads | - | - |
| `docs/SCOPE_OF_WORK.md` | Reads | - | Reads | Reads | Reads | Reads | Owner | Reads | - | Reads | Counts | Reads |
| `docs/AGENT_ROLES.md` | - | - | - | - | - | - | - | - | - | Owner | Counts | - |
| `docs/OPERATIONS.md` | - | - | - | - | - | - | Reads | - | - | Owner | - | - |
| `CLAUDE.md` | - | - | - | - | - | - | Owner | - | - | - | KeyFiles | - |
| `tests/` | - | - | - | - | Reads | - | - | Owner | - | - | Count | - |
| SEO pages (`static/*.html`) | Reads | Reads | - | - | Owner | Reads | - | - | - | - | Counts | - |
| Competitor pages (`vs-*.html`) | Owner | - | Reads | - | Reads | - | - | - | - | - | - | Reads |
| `scripts/security_check.sh` | - | - | - | - | - | Owner | - | - | - | - | - | - |
| Error messages (HTTPException) | - | Owner | - | - | - | - | - | Reads | - | - | - | **Owner** |
| `.env.example` | - | - | - | - | - | - | - | - | - | - | EnvSync | - |
| `static/sitemap.xml` | - | - | - | - | Reads | - | - | - | - | - | URLs | - |
| `pyproject.toml` (version) | - | - | - | - | - | - | - | - | - | - | Version | - |
| Guide endpoints (`/guide/*`) | - | - | - | - | - | - | - | - | - | - | - | **Owner** |
| OpenAPI/schema | - | - | - | - | - | - | Reads | - | - | - | - | **Owner** |

## Audit Trail

Track the last run of each agent for staleness detection.

| Agent | Last Run | Result | Triggered By | Downstream Triggers |
|-------|----------|--------|-------------|-------------------|
| PM | 2026-03-09 | WARN (5): zero distribution, Pro hidden, FastAPI desc stale | All-Hands | Marketing, Finance, UX, Admin |
| UX | 2026-03-09 | WARN (6): mobile grid, ToS checkbox, dim contrast — ALL FIXED | All-Hands | Legal, Marketing, Admin, QA |
| Finance | 2026-03-09 | PASS WITH ADVISORIES (3): capacity plan, revenue tracking | All-Hands | PM, Marketing |
| Legal | 2026-03-09 | WARN (4): registration_ip removed from privacy, ToS checkbox FIXED | All-Hands | UX, Security, Admin |
| Marketing | 2026-03-09 | **UPDATED**: Content pipeline fully loaded (7 assets). MCP tool count fixed 40→43 across all drafts. 2 new awesome-list PRs submitted. Launch sprint briefing added. | Agency Consult + CEO | Admin, PM, Agent Advocate |
| Security | 2026-03-09 | WARN (8): CSP unsafe-inline, no pip audit — no critical issues | All-Hands | Architect, QA |
| Architect | 2026-03-09 | WARN (5): 8/10 quality, workers=2 rate limit bypass noted | All-Hands | QA, Ops, Admin |
| QA | 2026-03-09 | PASS: 400/400 tests (2 failover env leak tests FIXED) | All-Hands | Architect, Admin |
| Analytics | 2026-03-09 | WARN (5): WS_MESSAGES_DROPPED verified OK, registration gauge OK. **ACTION: Define activation funnel in PostHog before T-0.** | All-Hands | QA, Architecture |
| Ops | 2026-03-09 | WARN (7): no DB backup schedule, unbounded api.log. **ACTION: Fix log rotation + DB backup before launch traffic.** | All-Hands | Admin, Architect |
| Agent Advocate | 2026-03-09 | **UPDATED**: Python SDK client created (`examples/satoshi_client.py`, 46 methods). Fee dashboard tutorial created + verified. DX audit framework adopted from agency-agents Developer Advocate consult. | Agency Consult + CEO | Architecture, PM, QA |
| Admin Assistant | 2026-03-09 | **ACTION: Stamp 43 MCP tools across all docs.** Verify `LAUNCH_SUBMISSION_KIT.md` counts match live state. Pre-launch consistency sweep needed. | Agency Consult | Marketing, Architect |

## Performance Tracking

| Agent | Last 5 Runs | Issues Found | Fixed | Trigger Count | Latest Result |
|-------|-------------|-------------|-------|---------------|---------------|
| PM | 2026-03-07, 2026-03-08, 2026-03-08 | 5 | 0 | 4 | WARN (11/18 checks, triggers: Marketing, UX, Finance, Architect) |
| UX | 2026-03-07, 2026-03-08, 2026-03-08 | 5 | 0 | 4 | WARN (2 P0 bugs found, triggers: Marketing, QA, Admin, Agent Advocate) |
| Finance | 2026-03-07, 2026-03-08, 2026-03-08, 2026-03-08 | 3 | 0 | 3 | PASS (8/8 controls, triggers: PM, Marketing) |
| Legal | 2026-03-07, 2026-03-08, 2026-03-08 | 2 | 0 | 2 | WARN (agent terms missing, triggers: Agent Advocate, UX, Security, Marketing, Admin, Architect) |
| Marketing | 2026-03-07, 2026-03-08, 2026-03-08 | 4 | 0 | 4 | WARN (dirs not submitted, triggers: UX, Admin, Agent Advocate, PM) |
| Security | 2026-03-07, 2026-03-07, 2026-03-07, 2026-03-08, 2026-03-08 | 4 | 0 | 3 | WARN (2 critical gaps, triggers: Architect, Agent Advocate, QA, Legal, PM) |
| Architect | 2026-03-07, 2026-03-08, 2026-03-08 | 6 | 0 | 3 | WARN (3 scale concerns, triggers: QA, Agent Advocate, Security, PM) |
| QA | 2026-03-07, 2026-03-08, 2026-03-08 | 5 | 0 | 3 | WARN (422 actual vs 415 documented, triggers: Agent Advocate, Architect, Admin, Security) |
| Analytics | 2026-03-07, 2026-03-08, 2026-03-08 | 5 | 0 | 4 | WARN (can't slice by MCP, triggers: Architect, QA, PM, Agent Advocate) |
| Ops | 2026-03-07, 2026-03-08 | — | — | — | WARN (single-worker, triggers: Security, PM, Architect, Finance) |
| Agent Advocate | 2026-03-08, 2026-03-08 | — | — | — | WARN (token waste, triggers: Architect, QA, PM, Marketing, Admin) |
| Admin Assistant | 2026-03-07, 2026-03-08 | 5 | 5 | 2 | PASS (6/9 clean, triggers: Marketing, Architect) |

## Conflict Resolution Protocol

When two agents disagree, apply this priority order (highest wins):

1. **Legal** — Compliance is non-negotiable
2. **Security** — Safety overrides convenience
3. **Finance** — Business viability overrides growth aspirations
4. **PM** — Product direction overrides operational preferences
5. **Architect** — Technical feasibility overrides feature requests
6. **All others** — Escalate to CEO

### Common Conflict Patterns

| Conflict | Resolution |
|----------|-----------|
| Security wants restrictions that hurt UX | Security wins — find a UX workaround |
| PM wants feature that Architect says is too complex | Architect proposes simpler alternative, PM decides |
| Any agent proposes change that hurts agent experience | Agent Advocate flags it, proposing agent gets to counter, CEO decides |
| Marketing claims something Legal hasn't approved | Legal wins — pull the claim until approved |
| Finance says pricing is too low, PM disagrees | Model both scenarios, CEO decides |
| QA finds bug in Architect-approved code | QA wins — fix before deploy |

### Escalation Rules
- If two agents at the same priority level disagree → escalate to CEO
- If resolution requires code changes → QA must re-run after
- If resolution changes public-facing content → Marketing must sync

## Future Hire List

| Role | Signal to Hire | Current State |
|------|---------------|---------------|
| DevOps/SRE | Deploy fails 2+/month OR multi-server OR uptime <99% | Single server, manual deploy works |
| Customer Success | First Pro user OR 3+ support emails/week | Zero paying users |
| Data Engineer | 3+ schema changes/month OR usage_log >1M rows | Single SQLite table |
| Growth/Sales | MRR >$500 OR 5+ enterprise inquiries | Pre-revenue |
| Technical Writer | 3+ doc complaints OR >100 endpoints AND >10 paying users | 83 endpoints, self-documented |
| Compliance Officer | Regulated jurisdiction OR user funds OR PII >10K records | Minimal PII |

---

## Org Chart

```
                                           CEO
       ________________________________________________________________________
      |     |      |      |       |     |      |      |     |     |         |      |
     PM    UX    CFO   Agent    Legal  Mktg  Security Arch   QA  Analytics  Ops  Admin
                       Advocate
```

All agents are peers. Collaboration pairs (documented above) handle cross-functional coordination. The trigger matrix handles change propagation. No intermediate management needed at this scale.

*This file is read by all 12 agent skills at the start of every run. Update it when adding new change types, agents, or cross-references.*
