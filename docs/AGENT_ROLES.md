# Agent Employee Coordination — Satoshi API

This document defines the 10 agent "employees" that maintain Satoshi API, their responsibilities, and the trigger matrix that coordinates their work.

## The 10 Employees

All 10 agents report directly to the CEO (Andy). Fully flat org — no intermediate management layers.

### Strategic
| Role | Skill | Responsibility |
|------|-------|---------------|
| **Product Manager** | `/pm-review` | Feature strategy, competitive gaps, prioritization, pricing, 90-day roadmap |
| **UX/Design Lead** | `/ux-review` | Customer journey, landing page, registration flow, docs UX, error messages |
| **CFO / Finance** | `/finance-review` | Cost analysis, unit economics, pricing validation, revenue projections, infra cost optimization |

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
- **Chief of Staff + ALL** — org health, process gaps, standards enforcement, data lifecycle

## Design Rationale

Based on research into multi-agent patterns (Cursor's Planner/Worker/Judge hierarchy, VoltAgent's 127 agents, Claude Code swarm orchestration with TeammateTool), we chose **human-in-the-loop trigger matrix** over autonomous swarms:

- **Swarm pattern** (parallel workers, inbox messaging, task claiming) is for 5-10 concurrent agents on massive codebases. Overkill for a single developer.
- **Trigger matrix** = each agent reports what OTHER agents should review. Human decides when/whether to run them.
- **Slash commands** are the interface. Each agent reads this file, does its job, logs its run, and reports triggers.

Key insight from Mike Mason's 2026 analysis: "Orchestrated agents on bounded tasks with human oversight produce value. Autonomous agents don't work reliably." Google's DORA Report confirms: 90% AI adoption increase → 9% bug rate climb when agents run unsupervised.

**Why flat at 10:** At 10 agents with 1 human, hierarchy demotes key functions (Security under Product? Legal under Finance? No). The trigger matrix already coordinates cross-agent work. Real startups at this size are flat.

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
| New endpoint added | Marketing, Security, QA Lead, Architect, PM, Ops |
| New data collection (PII) | Legal, Security |
| New third-party integration | Legal, Security |
| Pricing/tier change | Legal, Marketing, PM, Finance |
| License change | Legal, Marketing, Architect |
| New marketing claim | Legal |
| Auth/rate-limit change | Security, Marketing |
| Test count change | Marketing, QA Lead |
| New static page | Marketing (sitemap), Architect (CSP whitelist) |
| DB schema change | Security, Architect |
| Config/env var change | Architect, Security, **update OPERATIONS.md** |
| Deployment/process change | Architect, **update OPERATIONS.md** |
| Customer journey change | PM, UX, Marketing |
| Infrastructure cost change | Finance, Architect |
| Competitive landscape shift | PM, Marketing |
| Revenue/usage milestone | Finance, PM |
| Service layer change | Security, Architect |
| Logging/observability change | Analytics, Security, Architect |
| Landing page / docs UX change | UX, Marketing |
| Error message change | UX, QA Lead |
| Agent added/removed/split | Ops (update AGENT_ROLES.md, all downstream docs) |
| Data retention policy change | Ops, Legal, Analytics |
| Process/automation change | Ops, Architect |
| Cross-doc inconsistency found | Ops (sync all references) |

## Cross-Reference: Who Cares About What

| File/Area | PM | UX | Finance | Legal | Marketing | Security | Architect | QA | Analytics | Ops |
|-----------|----|----|---------|-------|-----------|----------|-----------|-----|-----------|-----|
| `static/terms.html` | - | - | - | Owner | - | - | - | - | - | - |
| `static/privacy.html` | - | - | - | Owner | - | Reads | - | - | Reads | Reads |
| `static/index.html` | Reads | Owner | - | Reads | Owner | Reads | - | - | - | - |
| `middleware.py` | - | - | - | Reads | - | Owner | Reads | - | - | - |
| `config.py` (pricing/tiers) | Reads | - | Reads | - | - | Reads | Owner | - | - | - |
| `routers/*.py` | Reads | Reads | - | Reads | Reads | Reads | Owner | Reads | Reads | - |
| `services/*.py` | - | - | - | - | Reads | Reads | Owner | - | - | - |
| `db.py` / migrations | - | - | - | - | - | Reads | Owner | - | Owner | Reads |
| `docs/SCOPE_OF_WORK.md` | Reads | - | Reads | Reads | Reads | Reads | Owner | Reads | - | Reads |
| `docs/AGENT_ROLES.md` | - | - | - | - | - | - | - | - | - | Owner |
| `docs/OPERATIONS.md` | - | - | - | - | - | - | Reads | - | - | Owner |
| `tests/` | - | - | - | - | Reads | - | - | Owner | - | - |
| SEO pages (`static/*.html`) | Reads | Reads | - | - | Owner | Reads | - | - | - | - |
| Competitor pages (`vs-*.html`) | Owner | - | Reads | - | Reads | - | - | - | - | - |
| `scripts/security_check.sh` | - | - | - | - | - | Owner | - | - | - | - |
| Error messages (HTTPException) | - | Owner | - | - | - | - | - | Reads | - | - |

## Audit Trail

Track the last run of each agent for staleness detection.

| Agent | Last Run | Result | Triggered By | Downstream Triggers |
|-------|----------|--------|-------------|-------------------|
| PM | 2026-03-07 | PASS WITH WARNINGS | All-Hands | UX, Finance, Marketing |
| UX | 2026-03-07 | PASS WITH WARNINGS | All-Hands | Marketing |
| Finance | 2026-03-07 | PASS | All-Hands | PM |
| Legal | 2026-03-07 | PASS WITH WARNINGS | All-Hands | Security, Marketing |
| Marketing | 2026-03-07 | PASS WITH WARNINGS | All-Hands | — |
| Security | 2026-03-07 | PASS (pentest: 3 fixed, 0 outstanding) | /security-review + pentest | — |
| Architect | 2026-03-07 | PASS (207/207 tests) | All-Hands | QA, Marketing |
| QA | 2026-03-07 | PASS WITH WARNINGS | All-Hands | Architect |
| Analytics | 2026-03-07 | PASS WITH WARNINGS | All-Hands | Legal, Security |
| Ops | 2026-03-07 | — (created) | All-Hands | — |

## Performance Tracking

| Agent | Last 5 Runs | Issues Found | Fixed | Trigger Count |
|-------|-------------|-------------|-------|---------------|
| PM | 2026-03-07 | 4 | 0 | 3 |
| UX | 2026-03-07 | 3 | 0 | 1 |
| Finance | 2026-03-07 | 0 | 0 | 1 |
| Legal | 2026-03-07 | 2 | 2 | 2 |
| Marketing | 2026-03-07 | 7 | 7 | 0 |
| Security | 2026-03-07, 2026-03-07, 2026-03-07 | 8 | 8 | 2 |
| Architect | 2026-03-07 | 1 | 1 | 2 |
| QA | 2026-03-07 | 2 | 2 | 1 |
| Analytics | 2026-03-07 | 2 | 0 | 2 |
| Ops | 2026-03-07 | — | — | — |

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
| Technical Writer | 3+ doc complaints OR >100 endpoints | 73 endpoints, self-documented |
| Compliance Officer | Regulated jurisdiction OR user funds OR PII >10K records | Minimal PII |

---

## Org Chart

```
                                    CEO (Andy)
       _____________________________________________________________
      |     |      |      |     |      |      |     |     |         |
     PM    UX    CFO   Legal  Mktg  Security Arch   QA  Analytics  Ops
```

All agents are peers. Collaboration pairs (documented above) handle cross-functional coordination. The trigger matrix handles change propagation. No intermediate management needed at this scale.

*This file is read by all 10 agent skills at the start of every run. Update it when adding new change types, agents, or cross-references.*
