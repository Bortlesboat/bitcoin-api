#!/usr/bin/env python3
"""Documentation & Brand Consistency Checker.

Validates that all static HTML pages meet brand standards and that
key documentation files don't contradict each other.

Usage:
    python scripts/doc_consistency.py          # Full check
    python scripts/doc_consistency.py --json   # JSON output for agents

Exit code 1 if any errors found, 0 if clean.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

# Pages that should have full brand treatment (fonts, analytics, nav)
BRAND_PAGES = [
    "index.html",
    "vs-mempool.html",
    "vs-blockcypher.html",
    "best-bitcoin-api-for-developers.html",
    "bitcoin-api-for-ai-agents.html",
    "self-hosted-bitcoin-api.html",
    "bitcoin-fee-api.html",
    "bitcoin-mempool-api.html",
    "bitcoin-mcp-setup-guide.html",
    "privacy.html",
    "terms.html",
    "404.html",
]


def check_html_brand(filename: str, content: str) -> list[dict]:
    """Check a single HTML file for brand standard compliance."""
    issues = []
    rel = f"static/{filename}"

    if "fonts.googleapis.com" not in content:
        issues.append({"file": rel, "severity": "error",
                       "issue": "Missing Google Fonts import (Inter + JetBrains Mono)"})
    elif "Inter" not in content:
        issues.append({"file": rel, "severity": "error",
                       "issue": "Google Fonts loaded but 'Inter' not in CSS"})

    if "__POSTHOG_API_KEY__" not in content:
        issues.append({"file": rel, "severity": "error",
                       "issue": "Missing PostHog analytics (__POSTHOG_API_KEY__ placeholder)"})

    if re.search(r"phc_[a-zA-Z0-9]+", content):
        issues.append({"file": rel, "severity": "error",
                       "issue": "Hardcoded PostHog key found — use __POSTHOG_API_KEY__"})

    if "<nav" not in content.lower():
        issues.append({"file": rel, "severity": "warning",
                       "issue": "No <nav> element — page is a dead end"})

    if "#0d1117" not in content.lower() and "#0D1117" not in content:
        issues.append({"file": rel, "severity": "warning",
                       "issue": "Missing brand background color (#0d1117)"})

    if "#f7931a" not in content.lower():
        issues.append({"file": rel, "severity": "warning",
                       "issue": "Missing brand accent color (#f7931a)"})

    if "favicon" not in content.lower():
        issues.append({"file": rel, "severity": "warning",
                       "issue": "No favicon reference"})

    return issues


def check_version_consistency() -> list[dict]:
    """Ensure version is consistent across key files."""
    issues = []
    pyproject = ROOT / "pyproject.toml"
    canonical = None
    if pyproject.exists():
        m = re.search(r'version\s*=\s*"([^"]+)"', pyproject.read_text(encoding="utf-8"))
        if m:
            canonical = m.group(1)
    if not canonical:
        return [{"file": "pyproject.toml", "severity": "error",
                 "issue": "Cannot read version"}]

    init_py = ROOT / "src" / "bitcoin_api" / "__init__.py"
    if init_py.exists():
        content = init_py.read_text(encoding="utf-8")
        m = re.search(r'__version__\s*=\s*"([^"]+)"', content)
        if m and m.group(1) != canonical:
            issues.append({"file": "src/bitcoin_api/__init__.py", "severity": "error",
                           "issue": f"__version__ '{m.group(1)}' != pyproject '{canonical}'"})

    sow = ROOT / "docs" / "SCOPE_OF_WORK.md"
    if sow.exists():
        head = sow.read_text(encoding="utf-8")[:500]
        m = re.search(r'[Vv]ersion[:\s]+(\d+\.\d+\.\d+)', head)
        if m and m.group(1) != canonical:
            issues.append({"file": "docs/SCOPE_OF_WORK.md", "severity": "warning",
                           "issue": f"Header version '{m.group(1)}' != '{canonical}'"})
    return issues


def check_posthog_templating() -> list[dict]:
    """Ensure pages with PostHog are in the allowed set in static_routes.py."""
    issues = []
    routes_file = ROOT / "src" / "bitcoin_api" / "static_routes.py"
    if not routes_file.exists():
        return issues

    routes_content = routes_file.read_text(encoding="utf-8")
    m = re.search(r'allowed\s*=\s*\{([^}]+)\}', routes_content)
    if not m:
        return issues

    allowed = set(re.findall(r'"([^"]+)"', m.group(1)))

    for html_file in STATIC.glob("*.html"):
        content = html_file.read_text(encoding="utf-8", errors="ignore")
        if "__POSTHOG_API_KEY__" not in content:
            continue
        page_name = html_file.stem
        if page_name in ("index", "404", "admin-dashboard"):
            continue
        if page_name not in allowed:
            issues.append({"file": f"static/{html_file.name}", "severity": "error",
                           "issue": f"Has __POSTHOG_API_KEY__ but '{page_name}' not in static_routes.py allowed set"})
    return issues


def main():
    parser = argparse.ArgumentParser(description="Brand & doc consistency checker")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    all_issues = []

    for filename in BRAND_PAGES:
        filepath = STATIC / filename
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            all_issues.extend(check_html_brand(filename, content))
        else:
            all_issues.append({"file": f"static/{filename}", "severity": "warning",
                               "issue": "Brand page not found"})

    all_issues.extend(check_version_consistency())
    all_issues.extend(check_posthog_templating())

    errors = [i for i in all_issues if i["severity"] == "error"]
    warnings = [i for i in all_issues if i["severity"] == "warning"]

    if args.json:
        print(json.dumps({"issues": all_issues}, indent=2))
    else:
        print("=" * 60)
        print("BRAND & DOCUMENTATION CONSISTENCY CHECK")
        print("=" * 60)
        print()
        if not all_issues:
            print("ALL CLEAR — brand standards and docs are consistent.")
        else:
            if errors:
                print(f"ERRORS ({len(errors)}):")
                for i in errors:
                    print(f"  [{i['file']}] {i['issue']}")
                print()
            if warnings:
                print(f"WARNINGS ({len(warnings)}):")
                for i in warnings:
                    print(f"  [{i['file']}] {i['issue']}")
                print()
            print(f"Total: {len(errors)} errors, {len(warnings)} warnings")
            print(f"Checked: {len(BRAND_PAGES)} HTML pages + cross-doc consistency")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
