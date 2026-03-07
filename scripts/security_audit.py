#!/usr/bin/env python3
"""Security auditor for Satoshi API.

Checks security headers, CSP policy, rate limiting, auth enforcement,
hardcoded secrets, CORS configuration, and RPC whitelist.

Run: python scripts/security_audit.py
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
# 1. Security headers present and correct
# ---------------------------------------------------------------------------
def check_security_headers():
    print("\n[1] Security Headers")
    middleware = (SRC / "middleware.py").read_text(encoding="utf-8")

    required_headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": None,  # just check presence
        "X-XSS-Protection": "1; mode=block",
        "Content-Security-Policy": None,
        "Strict-Transport-Security": None,
    }

    for header, expected_value in required_headers.items():
        if header in middleware:
            if expected_value and expected_value in middleware:
                note(f"{header} = {expected_value}")
            elif expected_value:
                warn(f"{header} present but value may differ from expected '{expected_value}'")
            else:
                note(f"{header} is set")
        else:
            error(f"{header} MISSING from middleware")


# ---------------------------------------------------------------------------
# 2. CSP covers all static pages
# ---------------------------------------------------------------------------
def check_csp_coverage():
    print("\n[2] CSP Coverage")
    middleware = (SRC / "middleware.py").read_text(encoding="utf-8")

    # Check CSP is not applied to docs paths (Swagger needs inline scripts)
    if "_DOCS_PATHS" in middleware and "not in _DOCS_PATHS" in middleware:
        note("CSP correctly skipped for docs/Swagger paths")
    else:
        warn("CSP may be applied to docs paths — Swagger UI needs inline scripts")

    # Check CSP directives
    csp_directives = ["default-src", "script-src", "style-src", "img-src",
                      "connect-src", "frame-ancestors", "base-uri", "form-action"]
    for directive in csp_directives:
        if directive in middleware:
            note(f"CSP has {directive}")
        else:
            warn(f"CSP missing {directive} directive")

    # Verify static pages exist and would be served with CSP
    static_pages = list(STATIC.glob("*.html"))
    note(f"{len(static_pages)} static HTML pages found — all get CSP headers")


# ---------------------------------------------------------------------------
# 3. Rate limit skip set matches served pages
# ---------------------------------------------------------------------------
def check_rate_limit_skip():
    print("\n[3] Rate Limit Skip Set")
    middleware = (SRC / "middleware.py").read_text(encoding="utf-8")

    if "_RATE_LIMIT_SKIP" not in middleware:
        error("No _RATE_LIMIT_SKIP set found — all requests are rate-limited")
        return

    # Extract the skip set
    skip_match = re.search(r'_RATE_LIMIT_SKIP\s*=\s*\{([^}]+)\}', middleware, re.DOTALL)
    if not skip_match:
        warn("Could not parse _RATE_LIMIT_SKIP set")
        return

    skip_block = skip_match.group(1)
    skip_paths = set(re.findall(r'"([^"]+)"', skip_block))
    note(f"Rate limit skip set has {len(skip_paths)} paths")

    # Check that legal pages are skipped
    for legal_page in ("/terms", "/privacy"):
        if legal_page in skip_paths:
            note(f"{legal_page} in skip set (good — legal pages shouldn't be rate-limited)")
        else:
            warn(f"{legal_page} NOT in skip set — legal pages will be rate-limited")

    # Check that static SEO pages match skip set
    for html_file in STATIC.glob("*.html"):
        slug = "/" + html_file.stem
        if slug in ("/index",):
            slug = "/"
        if slug not in skip_paths and slug not in ("/terms", "/privacy"):
            # SEO pages should ideally be in skip set
            if html_file.stem not in ("index", "terms", "privacy"):
                if f"/{html_file.stem}" not in skip_paths:
                    warn(f"Static page {html_file.name} (/{html_file.stem}) not in rate limit skip set")


# ---------------------------------------------------------------------------
# 4. Auth enforcement on POST endpoints
# ---------------------------------------------------------------------------
def check_auth_enforcement():
    print("\n[4] Auth Enforcement on POST Endpoints")
    middleware = (SRC / "middleware.py").read_text(encoding="utf-8")

    # Check that auth middleware exists
    if "authenticate" in middleware:
        note("Auth middleware calls authenticate()")
    else:
        error("No authenticate() call in middleware")

    # Check POST endpoints require auth (tier check)
    for router_file in (SRC / "routers").glob("*.py"):
        if router_file.name == "__init__.py":
            continue
        content = router_file.read_text(encoding="utf-8")
        post_routes = re.findall(r'@router\.post\([^)]*\)', content)
        if post_routes:
            # Check that the router has tier checking
            if "tier" in content.lower() or "anonymous" in content.lower():
                note(f"{router_file.name}: POST endpoints have tier checks")
            else:
                warn(f"{router_file.name}: has POST endpoints but no visible tier/auth checks")


# ---------------------------------------------------------------------------
# 5. Hardcoded secrets check
# ---------------------------------------------------------------------------
def check_hardcoded_secrets():
    print("\n[5] Hardcoded Secrets")

    secret_patterns = [
        (r'password\s*=\s*["\'][^"\']+["\']', "hardcoded password"),
        (r'secret\s*=\s*["\'][^"\']+["\']', "hardcoded secret"),
        (r'api[_-]?key\s*=\s*["\'][a-zA-Z0-9]{16,}["\']', "hardcoded API key"),
        (r'token\s*=\s*["\'][a-zA-Z0-9]{16,}["\']', "hardcoded token"),
        (r'Bearer\s+[a-zA-Z0-9._-]{20,}', "hardcoded bearer token"),
    ]

    # Scan all Python files
    py_files = list(SRC.rglob("*.py")) + list((ROOT / "scripts").glob("*.py"))
    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8")
        rel = py_file.relative_to(ROOT)
        for pattern, desc in secret_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Skip common false positives
                if any(fp in match.lower() for fp in ("example", "test", "placeholder",
                                                       "your_", "xxx", "changeme",
                                                       "secretstr", "secret_str")):
                    continue
                error(f"{rel}: possible {desc} — {match[:50]}...")

    # Check .env is gitignored
    gitignore = ROOT / ".gitignore"
    if gitignore.exists():
        gi_content = gitignore.read_text(encoding="utf-8")
        if ".env" in gi_content:
            note(".env is in .gitignore")
        else:
            error(".env is NOT in .gitignore — secrets may be committed")
    else:
        warn("No .gitignore found")

    # Check config uses SecretStr for sensitive fields
    config = (SRC / "config.py").read_text(encoding="utf-8")
    if "SecretStr" in config:
        note("Config uses SecretStr for sensitive fields")
    else:
        warn("Config does not use SecretStr — passwords may be logged")


# ---------------------------------------------------------------------------
# 6. CORS configuration
# ---------------------------------------------------------------------------
def check_cors():
    print("\n[6] CORS Configuration")
    middleware = (SRC / "middleware.py").read_text(encoding="utf-8")

    if "CORSMiddleware" in middleware:
        note("CORS middleware is configured")
    else:
        error("No CORS middleware found")

    # Check for wildcard origins warning
    if '"*"' in middleware and "cors" in middleware.lower():
        warn("CORS allows wildcard '*' origins — restrict in production")
    elif "cors_origins" in middleware:
        note("CORS uses configurable origins from settings")

    # Check allowed methods
    methods_match = re.search(r'allow_methods\s*=\s*\[([^\]]+)\]', middleware)
    if methods_match:
        methods = methods_match.group(1)
        note(f"CORS allowed methods: {methods}")
        if "DELETE" in methods or "PUT" in methods:
            warn("CORS allows DELETE/PUT — verify these are needed")


# ---------------------------------------------------------------------------
# 7. RPC whitelist
# ---------------------------------------------------------------------------
def check_rpc_whitelist():
    print("\n[7] RPC Whitelist")

    # Check if there's RPC method restriction in the codebase
    rpc_calls = set()
    for router_file in (SRC / "routers").glob("*.py"):
        content = router_file.read_text(encoding="utf-8")
        # Find RPC method calls like rpc.getblockcount(), rpc.call("getblockcount")
        methods = re.findall(r'rpc\.(\w+)\(', content)
        methods += re.findall(r'rpc\.call\(["\'](\w+)', content)
        for m in methods:
            if m not in ("__init__", "close", "connect"):
                rpc_calls.add(m)

    if rpc_calls:
        note(f"RPC methods used: {', '.join(sorted(rpc_calls))}")
        # Check SCOPE_OF_WORK documents them
        sow = ROOT / "docs" / "SCOPE_OF_WORK.md"
        if sow.exists():
            sow_text = sow.read_text(encoding="utf-8").lower()
            undocumented = [m for m in rpc_calls if m.lower() not in sow_text]
            if undocumented:
                warn(f"RPC methods not mentioned in SCOPE_OF_WORK: {', '.join(undocumented)}")
            else:
                note("All RPC methods documented in SCOPE_OF_WORK")
    else:
        note("No direct RPC calls found (may use abstraction layer)")


# ---------------------------------------------------------------------------
# 8. Database security
# ---------------------------------------------------------------------------
def check_db_security():
    print("\n[8] Database Security")
    db_py = (SRC / "db.py").read_text(encoding="utf-8")

    # Check for parameterized queries (no f-string SQL)
    fstring_sql = re.findall(r'f["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*["\']', db_py, re.IGNORECASE)
    if fstring_sql:
        error(f"Possible SQL injection: {len(fstring_sql)} f-string SQL queries in db.py")
    else:
        note("No f-string SQL detected in db.py (good)")

    # Check WAL mode
    if "wal" in db_py.lower():
        note("SQLite WAL mode enabled")
    else:
        warn("SQLite WAL mode not detected — concurrent access may cause issues")

    # Check for raw string concatenation in SQL across all files
    for py_file in SRC.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        rel = py_file.relative_to(ROOT)
        # Look for string concatenation near SQL keywords
        concat_sql = re.findall(r'(?:SELECT|INSERT|UPDATE|DELETE).*\+\s*(?:str\(|f"|request)', content, re.IGNORECASE)
        if concat_sql:
            error(f"{rel}: possible SQL injection via string concatenation")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  SATOSHI API — SECURITY AUDIT")
    print("=" * 60)

    check_security_headers()
    check_csp_coverage()
    check_rate_limit_skip()
    check_auth_enforcement()
    check_hardcoded_secrets()
    check_cors()
    check_rpc_whitelist()
    check_db_security()

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
