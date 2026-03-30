# Impact Metrics — Satoshi API + bitcoin-mcp Ecosystem

*Last updated: March 18, 2026*

---

## Code & Quality

| Metric | Satoshi API | bitcoin-mcp | BAIP-1 | Total |
|--------|------------|-------------|--------|-------|
| **Tests** | 725 (704 unit + 21 e2e) | 116 | 61 | **902** |
| **Endpoints / Tools** | ~115 endpoints, 28 routers | 49 tools, 6 prompts, 7 resources | 4 operations | — |
| **Commits** | 146 | 35 | 7 | **188** |
| **Lines of Code** | ~12,000+ | ~3,000+ | ~1,000+ | **16,000+** |
| **CI/CD** | GitHub Actions (test + publish) | GitHub Actions (test, 3 Python versions) | GitHub Actions (test, 3 Python versions) | All green |
| **License** | Apache 2.0 | MIT | MIT | OSI-approved |
| **PyPI Published** | Yes (satoshi-api) | Yes (bitcoin-mcp) | No (SDK only) | 2 packages |
| **PyPI Downloads** | 483/month, 42/week | 900/month, 353/week | — | **1,383/month** |

## Production Readiness

| Signal | Status |
|--------|--------|
| **Live production service** | bitcoinsapi.com (24/7) |
| **Security audit** | Completed (threat model, pentest log, CSP, rate limiting) |
| **Operations runbook** | 25KB ops guide (deployment, monitoring, troubleshooting) |
| **Self-hosting guide** | Complete (Docker, Cloudflare tunnel, bare metal) |
| **API documentation** | Interactive Swagger/OpenAPI at /docs |
| **Monitoring** | Prometheus metrics, health endpoints, circuit breaker |
| **Rate limiting** | Sliding window + daily caps (in-memory or Redis) |

## Bitcoin Ecosystem Contributions

| Contribution | Detail |
|-------------|--------|
| **Bitcoin Core reviews** | 19+ code reviews on bitcoin/bitcoin |
| **Review targets** | achow101, stickies-v, theStack, kevkevinpal (established maintainers) |
| **Ecosystem PRs** | ~165 PRs across 30 repos, 33 merged |
| **MCP Registry** | First Bitcoin MCP server on official Anthropic MCP Registry |
| **Protocol spec** | BAIP-1: Bitcoin Agent Identity Protocol (novel research) |
| **Open source tools** | Fee Observatory, Discord bot, Python SDK |

## Architecture & Documentation

| Document | Size | Purpose |
|----------|------|---------|
| SCOPE_OF_WORK.md | 53 KB | Living design document — 32 sprints documented |
| OPERATIONS.md | 25 KB | Production runbook |
| ARCHITECTURE.md | 3.7 KB | Design patterns and module responsibilities |
| CONTRIBUTING.md | Present | DCO requirement, development setup, PR guidelines |
| SECURITY.md | Present | Responsible disclosure, 48-hour response SLA |
| CODE_OF_CONDUCT.md | Present | Contributor Covenant 2.1 |

## Unique Value

1. **No competing Bitcoin MCP server exists** with this scope (49 tools vs. basic RPC wrappers)
2. **Fee intelligence saves real money** — not just raw data, but actionable "send now or wait" recommendations
3. **Zero-config for AI agents** — `pip install bitcoin-mcp` works immediately with hosted fallback
4. **Self-hostable** — full sovereignty, connect your own Bitcoin Core node
5. **BAIP-1** — first protocol spec for verifiable AI agent identities on Bitcoin

## Sustainability Model

- **Free tier:** Self-hosted (forever free, Apache 2.0)
- **Hosted free:** 5,000 requests/day (anonymous), 25,000/day (registered)
- **Pro tier:** Higher limits for commercial use
- **Grant funding:** Enables dedicated development time and infrastructure costs
