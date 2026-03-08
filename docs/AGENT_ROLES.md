# Agent Employee Coordination — Satoshi API

This document defines the 12 agent "employees" that maintain Satoshi API, their responsibilities, and the trigger matrix that coordinates their work.

## Company Status (Quick Reference)

**All agents: read this block first. It has the volatile facts that change every release.**

| Fact | Value | Updated |
|------|-------|---------|
| **Version** | 0.3.3 | 2026-03-08 |
| **Endpoints** | 78 core (+ 4 indexer = 82 when enabled) | 2026-03-08 |
| **Tests** | 359 unit + 21 e2e = 380 total | 2026-03-08 |
| **Routers** | 20 core + 3 indexer = 23 | 2026-03-08 |
| **Live URL** | https://bitcoinsapi.com | — |
| **Infra cost** | ~$3/mo | 2026-03-08 |
| **Revenue** | Pre-revenue (Stripe wired, Pro tier hidden) | 2026-03-08 |
| **Latest release** | v0.3.3 — Stale-while-error cache fallback, auto-start on reboot, sanitized error messages | 2026-03-08 |
| **Launch status** | Feature-complete, awaiting distribution (Show HN, Reddit, PyPI) | 2026-03-08 |
| **Open issues** | None critical — ToS §7 stale-data disclosure pending, /health/deep sanitized | 2026-03-08 |

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

---

## The 12 Employees

All 12 agents report directly to the CEO (Andy). Fully flat org — no intermediate management layers.

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
| PM | 2026-03-08 | PASS WITH WARNINGS | All-Hands | Marketing, Finance, UX, Admin |
| UX | 2026-03-08 | PASS WITH WARNINGS | All-Hands | Legal, Marketing, Admin, QA |
| Finance | 2026-03-08 | PASS WITH ADVISORIES (3) | Manual | PM, Marketing |
| Legal | 2026-03-08 | PASS WITH WARNINGS | All-Hands | UX, PM |
| Marketing | 2026-03-08 | WARN (version stamps stale) | All-Hands | Admin, UX, Architect |
| Security | 2026-03-08 | WARN (4 items) | All-Hands | QA, Architect, Admin |
| Architect | 2026-03-08 | PASS WITH WARNINGS (4) | All-Hands | QA, Admin, Security |
| QA | 2026-03-08 | WARN (0 stale cache tests) | All-Hands | Architect, Security, Admin |
| Analytics | 2026-03-08 | WARN (no stale Prometheus metric) | All-Hands | QA, Architect, Security, Admin |
| Ops | 2026-03-07 | — (created) | All-Hands | — |
| Agent Advocate | 2026-03-08 | — (created) | — | — |
| Admin Assistant | 2026-03-07 | PASS (76 endpoints stamped, 26 files, 5 stale refs fixed) | Manual | Architect, Marketing |

## Performance Tracking

| Agent | Last 5 Runs | Issues Found | Fixed | Trigger Count |
|-------|-------------|-------------|-------|---------------|
| PM | 2026-03-07, 2026-03-08 | 5 | 0 | 4 |
| UX | 2026-03-07, 2026-03-08 | 5 | 0 | 4 |
| Finance | 2026-03-07, 2026-03-08, 2026-03-08 | 3 | 0 | 3 |
| Legal | 2026-03-07, 2026-03-08 | 2 | 0 | 2 |
| Marketing | 2026-03-07, 2026-03-08 | 4 | 0 | 4 |
| Security | 2026-03-07, 2026-03-07, 2026-03-07, 2026-03-08 | 4 | 0 | 3 |
| Architect | 2026-03-07, 2026-03-08 | 6 | 0 | 3 |
| QA | 2026-03-07, 2026-03-08 | 5 | 0 | 3 |
| Analytics | 2026-03-07, 2026-03-08 | 5 | 0 | 4 |
| Ops | 2026-03-07 | — | — | — |
| Agent Advocate | 2026-03-08 | — | — | — |
| Admin Assistant | 2026-03-07 | 5 | 5 | 2 |

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
| Technical Writer | 3+ doc complaints OR >76 endpoints | 76 endpoints, self-documented |
| Compliance Officer | Regulated jurisdiction OR user funds OR PII >10K records | Minimal PII |

---

## Org Chart

```
                                         CEO (Andy)
       ________________________________________________________________________
      |     |      |      |       |     |      |      |     |     |         |      |
     PM    UX    CFO   Agent    Legal  Mktg  Security Arch   QA  Analytics  Ops  Admin
                       Advocate
```

All agents are peers. Collaboration pairs (documented above) handle cross-functional coordination. The trigger matrix handles change propagation. No intermediate management needed at this scale.

*This file is read by all 12 agent skills at the start of every run. Update it when adding new change types, agents, or cross-references.*
