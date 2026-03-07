# Satoshi API — Legal Obligations Tracker

**Last audited:** 2026-03-07
**Audit tool:** `python scripts/legal_audit.py`
**Skill command:** `/legal-review`

---

## 1. Active Legal Documents

| Document | Location | Last Updated | Status |
|----------|----------|--------------|--------|
| Terms of Service | `static/terms.html` | 2026-03-07 | Active |
| Privacy Policy | `static/privacy.html` | 2026-03-07 | Active |
| Apache 2.0 License | `LICENSE` | 2026-03-07 | Active |
| DCO (CONTRIBUTING.md) | `CONTRIBUTING.md` | 2026-03-07 | Active |
| LLC Prep Checklist | `docs/LLC_PREP.md` | 2026-03-07 | Deferred |

## 2. Compliance Obligations

### 2.1 Third-Party Data

| Provider | Data Used | Attribution Required | Where Attributed | Compliance |
|----------|-----------|---------------------|-----------------|------------|
| CoinGecko | BTC price data | Yes (their ToS) | `/prices` response, landing page footer, ToS Section 7 | Compliant |
| Cloudflare | DDoS/CDN (processes IPs) | Privacy policy mention | Privacy Policy Section 3 | Compliant |
| Bitcoin Core | Blockchain data | No (open protocol) | N/A | N/A |

### 2.2 Data Collection

| Data Point | Where Collected | Privacy Policy Reference | Retention |
|------------|----------------|------------------------|-----------|
| Email address | `/register` endpoint | Section 1, row 1 | Until key deletion |
| API key hash | `/register` endpoint | Section 1, row 2 | Until key deletion |
| IP address | Every request (middleware) | Section 1, row 3 | 30 days |
| Request path/method | Every request (usage_log) | Section 1, row 4 | 30 days |
| HTTP status code | Every request (usage_log) | Section 1, row 5 | 30 days |
| User-Agent | Every request (usage_log) | Pending coverage | 30 days |
| Response time | Every request (usage_log) | Not PII, no coverage needed | 30 days |

### 2.3 User Rights

| Right | Mechanism | Status |
|-------|-----------|--------|
| Data deletion | Email api@bitcoinsapi.com | Manual process |
| Data access | Email api@bitcoinsapi.com | Manual process |
| ToS acceptance | `agreed_to_terms` field on `/register` | Enforced (422 if false) |

### 2.4 Financial Disclaimers

| Disclaimer | Location | Status |
|------------|----------|--------|
| "Not financial advice" | `X-Data-Disclaimer` header (all API responses) | Active |
| Fee estimate disclaimer | ToS Section 6 | Active |
| Price data disclaimer | ToS Section 6 | Active |
| Broadcast disclaimer | ToS Section 6 | Active |
| Landing page disclaimer | Footer text | Active |

### 2.5 License Compliance

| File | Expected License | Status |
|------|-----------------|--------|
| `LICENSE` | Apache-2.0 | Correct |
| `pyproject.toml` | Apache-2.0 | Correct |
| `README.md` | Apache-2.0 badge | Correct |
| `CONTRIBUTING.md` | Apache-2.0 reference | Correct |
| `static/index.html` | Apache 2.0 text | Correct |
| `static/terms.html` | Apache 2.0 reference | Correct |

## 3. Legal Risk Register

| Risk | Severity | Mitigation | Status |
|------|----------|------------|--------|
| No LLC — personal liability | Medium | LLC prep checklist ready, file when revenue starts | Deferred |
| User relies on fee estimates, loses money | Medium | Financial disclaimer in ToS, API header, landing page | Mitigated |
| CoinGecko attribution violation | Low | Attribution in response, footer, and ToS | Mitigated |
| GDPR applicability (EU users) | Low | Minimal data collection, no cookies, deletion on request | Partially mitigated |
| Broadcast of illegal transactions | Low | ToS acceptable use clause, API key required for POST | Mitigated |
| Marketing implies uptime guarantee | Low | ToS Section 8 disclaims uptime guarantees | Monitor |
| Data breach of email addresses | Low | Only emails stored, hashed keys, no passwords | Acceptable risk |

## 4. Trigger Events (When to Update Legal Docs)

These events MUST trigger a `/legal-review`:

| Event | What to Check |
|-------|--------------|
| New third-party API integration | Privacy policy + ToS attribution |
| New data collection (any PII field) | Privacy policy Section 1 |
| New endpoint handling user data | Privacy policy + ToS |
| Pricing/tier changes | ToS Section 5 |
| License change | All files in Section 2.5 |
| New marketing claims | ToS warranty disclaimer |
| First paying customer | File LLC (docs/LLC_PREP.md) |
| Geographic expansion (non-US) | GDPR, international privacy laws |
| User data request received | Process per Section 2.3 |

## 5. Audit History

| Date | Tool | Result | Issues Found | Issues Fixed |
|------|------|--------|-------------|--------------|
| 2026-03-07 | Initial setup | N/A | All documents created from scratch | N/A |

---

*This tracker is maintained by the `/legal-review` skill. Run it after any code change that touches data collection, third-party integrations, marketing claims, or user-facing terms.*
