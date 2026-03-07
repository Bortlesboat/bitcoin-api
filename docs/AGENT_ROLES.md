# Agent Employee Coordination — Satoshi API

This document defines the 7 agent "employees" that maintain Satoshi API, their responsibilities, and the trigger matrix that coordinates their work.

## The 7 Employees

### Leadership (report to CEO)
| Role | Skill | Responsibility |
|------|-------|---------------|
| **Head of Product** | `/product-review` | Product vision, customer journey, pricing strategy, roadmap, competitive positioning |
| **CFO / Finance** | `/finance-review` | Cost analysis, unit economics, pricing validation, revenue projections, infra cost optimization |

### Operations
| Role | Skill | Script | Responsibility |
|------|-------|--------|---------------|
| **Legal** | `/legal-review` | `scripts/legal_audit.py` | ToS, privacy policy, disclaimers, compliance |
| **Marketing** | `/marketing-sync` | `scripts/marketing_sync.py` | Landing page, SEO, endpoint counts, feature claims |
| **Security** | `/security-review` | `scripts/security_audit.py` | Headers, auth, rate limits, CSP, threat model |
| **CTO / Coder** | `/code-review` | N/A (agent-only) | Tests pass, code quality, SCOPE_OF_WORK updated, architecture |
| **Analytics** | `/analytics-review` | N/A (agent-only) | Data collection changes, logging, metrics |

## Design Rationale

Based on research into multi-agent patterns (Cursor's Planner/Worker/Judge hierarchy, VoltAgent's 127 agents, Claude Code swarm orchestration with TeammateTool), we chose **human-in-the-loop trigger matrix** over autonomous swarms:

- **Swarm pattern** (parallel workers, inbox messaging, task claiming) is for 5-10 concurrent agents on massive codebases. Overkill for a single developer.
- **Trigger matrix** = each agent reports what OTHER agents should review. Human decides when/whether to run them.
- **Slash commands** are the interface. Each agent reads this file, does its job, logs its run, and reports triggers.

Key insight from Mike Mason's 2026 analysis: "Orchestrated agents on bounded tasks with human oversight produce value. Autonomous agents don't work reliably." Google's DORA Report confirms: 90% AI adoption increase → 9% bug rate climb when agents run unsupervised.

## Agent Run Protocol

Every agent follows this protocol:

1. **Read this trigger matrix** before starting work
2. **Do your job** — run audit script, review code, fix issues
3. **Log your run** — update the Audit Trail table with date, result, and downstream triggers
4. **Report triggers** — list which other agents should run next (do NOT auto-invoke them)

## Trigger Matrix

When a change of the given type occurs, the listed agents should be triggered for review.

| Change Type | Triggers |
|-------------|----------|
| New endpoint added | Marketing, Security, Coder, Product |
| New data collection (PII) | Legal, Security |
| New third-party integration | Legal, Security |
| Pricing/tier change | Legal, Marketing, Product, Finance |
| License change | Legal, Marketing, Coder |
| New marketing claim | Legal |
| Auth/rate-limit change | Security, Marketing |
| Test count change | Marketing, Coder |
| New static page | Marketing (sitemap), Coder (CSP whitelist) |
| DB schema change | Security, Coder |
| Config/env var change | Coder, Security |
| Customer journey change | Product, Marketing |
| Infrastructure cost change | Finance, Coder |
| Competitive landscape shift | Product, Marketing |
| Revenue/usage milestone | Finance, Product |

## Cross-Reference: Who Cares About What

| File/Area | Product | Finance | Legal | Marketing | Security | Coder | Analytics |
|-----------|---------|---------|-------|-----------|----------|-------|-----------|
| `static/terms.html` | - | - | Owner | - | - | - | - |
| `static/privacy.html` | - | - | Owner | - | Reads | - | Reads |
| `static/index.html` | Reads | - | Reads | Owner | Reads | - | - |
| `middleware.py` | - | - | Reads | - | Owner | Reads | - |
| `config.py` (pricing/tiers) | Reads | Reads | - | - | Reads | Owner | - |
| `routers/*.py` | Reads | - | Reads | Reads | Reads | Owner | Reads |
| `db.py` / migrations | - | - | Reads | - | Reads | Owner | Owner |
| `docs/SCOPE_OF_WORK.md` | Reads | Reads | Reads | Reads | Reads | Owner | - |
| `tests/` | - | - | - | Reads | - | Owner | - |
| SEO pages (`static/*.html`) | Reads | - | - | Owner | Reads | - | - |
| Competitor pages (`vs-*.html`) | Owner | Reads | - | Reads | - | - | - |
| `scripts/security_check.sh` | - | - | - | - | Owner | - | - |

## Audit Trail

Track the last run of each agent for staleness detection.

| Agent | Last Run | Result | Triggered By | Downstream Triggers |
|-------|----------|--------|-------------|-------------------|
| Product | - | - | - | - |
| Finance | - | - | - | - |
| Legal | - | - | - | - |
| Marketing | - | - | - | - |
| Security | - | - | - | - |
| Coder | 2026-03-07 | PASS (129/129 tests) | Manual — 3-tier refactor + architecture audit | Marketing (+1 endpoint), Security (new /health/deep, middleware extracted) |
| Analytics | - | - | - | - |

---

## Org Chart

```
        CEO (Andy)
        /       \
   Product    Finance (CFO)
      |
  -------------------------
  |     |      |     |    |
Legal  Mktg  Security CTO Analytics
```

Product and Finance are strategic leadership — they set direction.
The other 5 are operational — they execute and maintain.

*This file is read by all 7 agent skills at the start of every run. Update it when adding new change types, agents, or cross-references.*
