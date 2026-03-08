#!/usr/bin/env python3
"""Legal compliance auditor for Satoshi API.

Checks that legal documents (ToS, Privacy Policy, disclaimers) are consistent
with the actual codebase state: endpoints, data sources, data collection,
third-party integrations, and marketing claims.

Run: python scripts/legal_audit.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "bitcoin_api"
STATIC = ROOT / "static"

errors: list[str] = []
warnings: list[str] = []
info: list[str] = []


def error(msg: str) -> None:
    errors.append(f"  ERROR: {msg}")


def warn(msg: str) -> None:
    warnings.append(f"  WARN:  {msg}")


def note(msg: str) -> None:
    info.append(f"  INFO:  {msg}")


# ---------------------------------------------------------------------------
# 1. Legal pages exist and are served
# ---------------------------------------------------------------------------
def check_legal_pages_exist():
    print("\n[1] Legal Pages Exist")
    for page in ("terms.html", "privacy.html"):
        p = STATIC / page
        if p.exists():
            size = p.stat().st_size
            note(f"{page} exists ({size:,} bytes)")
        else:
            error(f"{page} MISSING — create static/{page}")

    # Check they're in the static page whitelist in static_routes.py
    static_routes_py = (SRC / "static_routes.py").read_text(encoding="utf-8")
    for slug in ("terms", "privacy"):
        if f'"{slug}"' in static_routes_py:
            note(f"/{slug} is in static page whitelist")
        else:
            error(f"/{slug} NOT in static page whitelist — won't be served")

    # Check rate limit skip
    main_py = (SRC / "main.py").read_text(encoding="utf-8")
    if '"terms"' in main_py and '"/terms"' in main_py.split("_RATE_LIMIT_SKIP")[1].split("}")[0] if "_RATE_LIMIT_SKIP" in main_py else False:
        note("/terms in rate limit skip set")
    elif "_RATE_LIMIT_SKIP" in main_py:
        skip_block = main_py.split("_RATE_LIMIT_SKIP")[1].split("}")[0]
        for slug in ("terms", "privacy"):
            if f'"/{slug}"' in skip_block:
                note(f"/{slug} in rate limit skip set")
            else:
                warn(f"/{slug} NOT in rate limit skip — legal pages will be rate-limited")


# ---------------------------------------------------------------------------
# 2. ToS acceptance on registration
# ---------------------------------------------------------------------------
def check_tos_acceptance():
    print("\n[2] ToS Acceptance on Registration")
    keys_py = (SRC / "routers" / "keys.py").read_text(encoding="utf-8")
    if "agreed_to_terms" in keys_py:
        note("agreed_to_terms field exists in RegisterRequest")
    else:
        error("RegisterRequest missing agreed_to_terms field — users can register without accepting ToS")

    if "agreed_to_terms" in keys_py and "not body.agreed_to_terms" in keys_py:
        note("ToS acceptance is enforced (422 if false)")
    elif "agreed_to_terms" in keys_py:
        warn("agreed_to_terms field exists but enforcement check not found")

    # Check landing page sends agreed_to_terms
    index = (STATIC / "index.html").read_text(encoding="utf-8")
    if "agreed_to_terms" in index:
        note("Landing page sends agreed_to_terms in registration")
    else:
        error("Landing page registration form does NOT send agreed_to_terms — will get 422")


# ---------------------------------------------------------------------------
# 3. Financial data disclaimer
# ---------------------------------------------------------------------------
def check_disclaimer():
    print("\n[3] Financial Data Disclaimer")
    middleware_py = (SRC / "middleware.py").read_text(encoding="utf-8")
    if "X-Data-Disclaimer" in middleware_py:
        note("X-Data-Disclaimer header is set in middleware")
    else:
        error("X-Data-Disclaimer header MISSING from middleware — API responses lack financial disclaimer")

    # Check ToS has financial disclaimer section
    terms = STATIC / "terms.html"
    if terms.exists():
        content = terms.read_text(encoding="utf-8")
        if "financial" in content.lower() and "not financial advice" in content.lower():
            note("ToS contains financial disclaimer language")
        else:
            error("ToS missing financial disclaimer section")

    # Check landing page footer
    index = (STATIC / "index.html").read_text(encoding="utf-8")
    if "informational purposes" in index.lower() or "not financial advice" in index.lower():
        note("Landing page has financial disclaimer in footer")
    else:
        warn("Landing page missing financial disclaimer text")


# ---------------------------------------------------------------------------
# 4. Third-party data attribution
# ---------------------------------------------------------------------------
def check_attribution():
    print("\n[4] Third-Party Data Attribution")

    # CoinGecko in prices router
    prices_py = (SRC / "routers" / "prices.py").read_text(encoding="utf-8")
    if "coingecko" in prices_py.lower():
        note("Prices router references CoinGecko")
    else:
        error("Prices router has NO CoinGecko reference — attribution required by their ToS")

    if "attribution" in prices_py:
        note("Prices response includes attribution field")
    else:
        warn("Prices response missing attribution field")

    # CoinGecko in ToS
    terms = STATIC / "terms.html"
    if terms.exists():
        content = terms.read_text(encoding="utf-8")
        if "coingecko" in content.lower():
            note("ToS mentions CoinGecko data ownership")
        else:
            error("ToS does NOT mention CoinGecko — required by their ToS")

    # CoinGecko in privacy policy
    privacy = STATIC / "privacy.html"
    if privacy.exists():
        content = privacy.read_text(encoding="utf-8")
        if "coingecko" in content.lower():
            note("Privacy policy mentions CoinGecko")
        else:
            warn("Privacy policy should mention CoinGecko as third-party data source")

    # CoinGecko in landing page
    index = (STATIC / "index.html").read_text(encoding="utf-8")
    if "coingecko" in index.lower():
        note("Landing page has CoinGecko attribution")
    else:
        warn("Landing page missing CoinGecko attribution in footer")


# ---------------------------------------------------------------------------
# 5. Privacy policy vs actual data collection
# ---------------------------------------------------------------------------
def check_privacy_accuracy():
    print("\n[5] Privacy Policy vs Actual Data Collection")

    privacy = STATIC / "privacy.html"
    if not privacy.exists():
        error("Privacy policy does not exist — cannot audit")
        return

    privacy_text = privacy.read_text(encoding="utf-8").lower()

    # Check: do we collect email?
    keys_py = (SRC / "routers" / "keys.py").read_text(encoding="utf-8")
    if "email" in keys_py:
        if "email" in privacy_text:
            note("Email collection documented in privacy policy")
        else:
            error("Code collects email at registration but privacy policy doesn't mention it")

    # Check: do we log IPs?
    main_py = (SRC / "main.py").read_text(encoding="utf-8")
    if "client.host" in main_py or "client_ip" in main_py:
        if "ip address" in privacy_text:
            note("IP logging documented in privacy policy")
        else:
            error("Code logs IP addresses but privacy policy doesn't mention it")

    # Check: do we use cookies?
    if "cookie" in main_py.lower():
        if "cookie" in privacy_text:
            note("Cookie usage documented")
        else:
            error("Code uses cookies but privacy policy says we don't")
    else:
        if "do not use cookies" in privacy_text:
            note("Correctly states no cookies")

    # Check: usage logging
    db_py = (SRC / "db.py").read_text(encoding="utf-8")
    if "usage_log" in db_py:
        if "usage" in privacy_text or "request path" in privacy_text or "access log" in privacy_text:
            note("Usage/access logging documented")
        else:
            warn("Code has usage_log table — ensure privacy policy covers request logging")

    # Check: Cloudflare mentioned
    if "cloudflare" in privacy_text:
        note("Cloudflare documented as third-party service")
    else:
        warn("Cloudflare processes all traffic but not mentioned in privacy policy")

    # Check for new data collection patterns
    for router_file in (SRC / "routers").glob("*.py"):
        content = router_file.read_text(encoding="utf-8")
        # Check for any new PII collection
        if "user_agent" in content and router_file.name != "__init__.py":
            if "user" not in privacy_text or "agent" not in privacy_text:
                warn(f"{router_file.name} accesses user_agent — verify privacy policy coverage")


# ---------------------------------------------------------------------------
# 6. License consistency
# ---------------------------------------------------------------------------
def check_license():
    print("\n[6] License Consistency")

    license_file = (ROOT / "LICENSE").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    index = (STATIC / "index.html").read_text(encoding="utf-8")

    # Detect which license
    if "Apache License" in license_file:
        license_type = "Apache-2.0"
    elif "MIT License" in license_file:
        license_type = "MIT"
    else:
        license_type = "Unknown"

    note(f"LICENSE file is: {license_type}")

    # Check pyproject.toml
    if license_type == "Apache-2.0":
        if "Apache" in pyproject:
            note("pyproject.toml license field matches")
        else:
            error(f"pyproject.toml license doesn't match LICENSE file ({license_type})")

        if "Apache" in readme:
            note("README license reference matches")
        else:
            error("README still references old license")

        if "MIT" in index and "Apache" not in index:
            error("Landing page still says MIT — should say Apache 2.0")
        elif "Apache" in index:
            note("Landing page license reference matches")

    elif license_type == "MIT":
        if "MIT" in pyproject:
            note("pyproject.toml license field matches")
        else:
            error(f"pyproject.toml license doesn't match LICENSE file ({license_type})")

    # Check ToS references correct license
    terms = STATIC / "terms.html"
    if terms.exists():
        terms_text = terms.read_text(encoding="utf-8")
        if license_type.lower().replace("-", " ") in terms_text.lower() or license_type in terms_text:
            note("ToS references correct license")
        else:
            warn(f"ToS should reference {license_type} license")

    # Check CONTRIBUTING.md
    contributing = ROOT / "CONTRIBUTING.md"
    if contributing.exists():
        contrib_text = contributing.read_text(encoding="utf-8")
        if license_type == "Apache-2.0" and "apache" in contrib_text.lower():
            note("CONTRIBUTING.md references correct license")
        elif license_type == "MIT" and "mit" in contrib_text.lower():
            note("CONTRIBUTING.md references correct license")
        else:
            error(f"CONTRIBUTING.md doesn't reference {license_type}")


# ---------------------------------------------------------------------------
# 7. Sitemap includes legal pages
# ---------------------------------------------------------------------------
def check_sitemap():
    print("\n[7] Sitemap & SEO")
    sitemap = STATIC / "sitemap.xml"
    if not sitemap.exists():
        warn("No sitemap.xml found")
        return

    content = sitemap.read_text(encoding="utf-8")
    for page in ("terms", "privacy"):
        if page in content:
            note(f"/{page} in sitemap.xml")
        else:
            warn(f"/{page} NOT in sitemap.xml")


# ---------------------------------------------------------------------------
# 8. Implied warranties / marketing claims
# ---------------------------------------------------------------------------
def check_marketing_claims():
    print("\n[8] Marketing Claims & Implied Warranties")

    index = (STATIC / "index.html").read_text(encoding="utf-8")

    # Check for uptime guarantees
    uptime_matches = re.findall(r'(\d+\.?\d*%\s*uptime)', index, re.IGNORECASE)
    for match in uptime_matches:
        warn(f'Landing page claims "{match}" — ensure ToS disclaims uptime guarantees')

    # Check for accuracy guarantees
    if "guaranteed" in index.lower() or "100% accurate" in index.lower():
        error("Landing page makes guarantee claims — ToS must disclaim or remove")

    # Check ToS has warranty disclaimer
    terms = STATIC / "terms.html"
    if terms.exists():
        terms_text = terms.read_text(encoding="utf-8")
        if '"as is"' in terms_text.lower():
            note('ToS has "AS IS" warranty disclaimer')
        else:
            error("ToS missing warranty disclaimer")

        if "limitation of liability" in terms_text.lower():
            note("ToS has limitation of liability section")
        else:
            error("ToS missing limitation of liability")


# ---------------------------------------------------------------------------
# 9. Governing law & contact info
# ---------------------------------------------------------------------------
def check_governing_law():
    print("\n[9] Governing Law & Contact")
    terms = STATIC / "terms.html"
    if not terms.exists():
        error("No ToS — cannot check governing law")
        return

    content = terms.read_text(encoding="utf-8")
    if "florida" in content.lower():
        note("ToS specifies Florida governing law")
    else:
        warn("ToS missing governing law clause")

    if "api@bitcoinsapi.com" in content:
        note("ToS includes contact email")
    else:
        warn("ToS missing contact information")

    privacy = STATIC / "privacy.html"
    if privacy.exists():
        pcontent = privacy.read_text(encoding="utf-8")
        if "api@bitcoinsapi.com" in pcontent:
            note("Privacy policy includes contact email")
        else:
            warn("Privacy policy missing contact email")


# ---------------------------------------------------------------------------
# 10. New data sources / integrations not covered
# ---------------------------------------------------------------------------
def check_new_integrations():
    print("\n[10] Uncovered Integrations & Data Sources")

    # Scan all router files for HTTP calls to external services
    external_domains = set()
    for router_file in (SRC / "routers").glob("*.py"):
        content = router_file.read_text(encoding="utf-8")
        urls = re.findall(r'https?://([a-zA-Z0-9.-]+)', content)
        for url in urls:
            if url not in ("bitcoinsapi.com", "localhost", "127.0.0.1"):
                external_domains.add((router_file.name, url))

    # Also check main app
    main_content = (SRC / "main.py").read_text(encoding="utf-8")
    urls = re.findall(r'https?://([a-zA-Z0-9.-]+)', main_content)
    for url in urls:
        if url not in ("bitcoinsapi.com", "localhost", "127.0.0.1"):
            external_domains.add(("main.py", url))

    if external_domains:
        # Check each is mentioned in privacy policy
        privacy = STATIC / "privacy.html"
        privacy_text = privacy.read_text(encoding="utf-8").lower() if privacy.exists() else ""

        for source_file, domain in sorted(external_domains):
            domain_short = domain.split(".")[-2] if "." in domain else domain
            if domain_short.lower() in privacy_text:
                note(f"{domain} ({source_file}) — documented in privacy policy")
            else:
                if domain in ("raw.githubusercontent.com",
                              "cdn.jsdelivr.net", "schema.org", "www.coingecko.com"):
                    pass  # Infrastructure, not data collection
                else:
                    warn(f"{domain} ({source_file}) — NOT mentioned in privacy policy. Review if it processes user data.")
    else:
        note("No external API calls found outside of known services")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  SATOSHI API — LEGAL COMPLIANCE AUDIT")
    print("=" * 60)

    check_legal_pages_exist()
    check_tos_acceptance()
    check_disclaimer()
    check_attribution()
    check_privacy_accuracy()
    check_license()
    check_sitemap()
    check_marketing_claims()
    check_governing_law()
    check_new_integrations()

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)

    for line in info:
        print(f"  {line}")

    if warnings:
        print(f"\n  {len(warnings)} WARNING(S):")
        for line in warnings:
            print(f"  {line}")

    if errors:
        print(f"\n  {len(errors)} ERROR(S):")
        for line in errors:
            print(f"  {line}")

    if errors:
        print(f"\n  RESULT: FAIL — {len(errors)} error(s), {len(warnings)} warning(s)")
        sys.exit(1)
    elif warnings:
        print(f"\n  RESULT: PASS WITH WARNINGS — {len(warnings)} warning(s)")
        sys.exit(0)
    else:
        print("\n  RESULT: ALL CLEAR")
        sys.exit(0)


if __name__ == "__main__":
    main()
