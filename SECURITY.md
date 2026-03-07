# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest (PyPI) | Yes |
| Development (master) | Best effort |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Email **api@bitcoinsapi.com** with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Response Timeline

- **Initial response:** within 48 hours
- **Assessment:** within 1 week
- **Fix + disclosure:** coordinated with reporter

## Scope

Security issues in scope:
- Authentication bypass
- Rate limit circumvention
- RPC command injection
- Information disclosure (node version, internal state)
- Denial of service via crafted input
- Dependency vulnerabilities

Out of scope:
- Issues requiring physical access to the host
- Social engineering
- Bitcoin Core vulnerabilities (report to bitcoin-core-dev)
