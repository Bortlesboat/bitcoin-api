#!/usr/bin/env python3
"""Marketing Sync Checker — ensures all marketing materials match product state.

Reads the canonical product facts from code/config, then scans all marketing
materials for stale numbers, outdated claims, or missing mentions.

Usage:
    python scripts/marketing_sync.py              # Full audit
    python scripts/marketing_sync.py --fix        # Show suggested fixes
    python scripts/marketing_sync.py --json       # JSON output for agents
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# 1. Extract canonical product facts from code
# ---------------------------------------------------------------------------

def get_product_state() -> dict:
    """Read canonical product facts from source files."""
    state = {}

    # Version from pyproject.toml
    pyproject = ROOT / "pyproject.toml"
    if pyproject.exists():
        m = re.search(r'version\s*=\s*"([^"]+)"', pyproject.read_text())
        if m:
            state["version"] = m.group(1)

    # Endpoint count from main.py (count @app.get/@app.post/@router.get etc.)
    main_py = ROOT / "src" / "bitcoin_api" / "main.py"
    endpoint_count = 0
    router_dir = ROOT / "src" / "bitcoin_api" / "routers"
    for py_file in [main_py] + list(router_dir.glob("*.py")) if router_dir.exists() else [main_py]:
        if py_file.exists():
            content = py_file.read_text()
            # Count route decorators (exclude include_in_schema=False which are internal)
            routes = re.findall(r'@(?:app|router)\.(get|post|put|delete|patch)\(', content)
            internal = len(re.findall(r'include_in_schema\s*=\s*False', content))
            endpoint_count += len(routes) - internal
    state["endpoint_count"] = endpoint_count

    # Test count from test files
    test_file = ROOT / "tests" / "test_api.py"
    if test_file.exists():
        content = test_file.read_text()
        unit_tests = len(re.findall(r'\ndef test_', content))
        state["unit_tests"] = unit_tests

    e2e_file = ROOT / "tests" / "test_e2e.py"
    if e2e_file.exists():
        content = e2e_file.read_text()
        e2e_tests = len(re.findall(r'\ndef test_', content))
        state["e2e_tests"] = e2e_tests

    # Install command (always satoshi-api for now)
    state["install_cmd"] = "pip install satoshi-api"
    state["live_url"] = "https://bitcoinsapi.com"
    state["github_url"] = "https://github.com/Bortlesboat/bitcoin-api"

    return state


# ---------------------------------------------------------------------------
# 2. Define marketing materials to scan
# ---------------------------------------------------------------------------

MARKETING_FILES = [
    # (path relative to ROOT, description)
    ("static/index.html", "Landing page"),
    ("docs/website/index.html", "Landing page (docs copy)"),
    ("README.md", "GitHub README"),
    ("static/vs-mempool.html", "SEO: vs Mempool"),
    ("static/vs-blockcypher.html", "SEO: vs BlockCypher"),
    ("static/best-bitcoin-api-for-developers.html", "SEO: Best Bitcoin API"),
    ("static/bitcoin-api-for-ai-agents.html", "SEO: AI Agents"),
    ("static/self-hosted-bitcoin-api.html", "SEO: Self-hosted"),
    ("static/bitcoin-fee-api.html", "SEO: Fee API"),
    ("static/bitcoin-mempool-api.html", "SEO: Mempool API"),
    ("docs/marketing/drafts/reddit-bitcoindev.md", "Draft: r/BitcoinDev"),
    ("docs/marketing/drafts/reddit-selfhosted.md", "Draft: r/selfhosted"),
    ("docs/marketing/drafts/reddit-bitcoin.md", "Draft: r/Bitcoin"),
    ("docs/marketing/drafts/reddit-python.md", "Draft: r/Python"),
    ("docs/marketing/drafts/stacker-news.md", "Draft: Stacker News"),
    ("docs/marketing/drafts/hackernews-show-hn.md", "Draft: Hacker News"),
    ("docs/marketing/launch-plan.md", "Launch plan"),
    ("docs/dev-to-article.md", "Dev.to article"),
    ("static/og-image.svg", "OG image"),
    ("CHANGELOG.md", "Changelog"),
    ("docs/SCOPE_OF_WORK.md", "Scope of Work"),
]


# ---------------------------------------------------------------------------
# 3. Check each file for stale facts
# ---------------------------------------------------------------------------

def check_file(filepath: Path, description: str, state: dict) -> list[dict]:
    """Check a single file for stale product facts. Returns list of issues."""
    if not filepath.exists():
        return [{"file": str(filepath.relative_to(ROOT)), "desc": description,
                 "severity": "warning", "issue": "File not found"}]

    content = filepath.read_text(encoding="utf-8", errors="ignore")
    issues = []
    rel = str(filepath.relative_to(ROOT))

    # Check endpoint count mentions
    endpoint_count = state.get("endpoint_count", 0)
    # Find patterns like "40+ endpoints", "40 endpoints", "33 endpoints" etc.
    # Skip changelogs (they intentionally list old counts) and small numbers (<10)
    is_changelog = "CHANGELOG" in rel.upper()
    is_sow = "SCOPE_OF_WORK" in rel.upper()
    for m in re.finditer(r'(\d+)\+?\s*endpoints', content, re.IGNORECASE):
        mentioned = int(m.group(1))
        if mentioned < 15:  # Skip small counts like "5 endpoints" in feature descriptions
            continue
        if is_changelog or is_sow:  # Historical docs list old counts intentionally
            continue
        if mentioned != endpoint_count and abs(mentioned - endpoint_count) > 2:
            issues.append({
                "file": rel, "desc": description, "severity": "error",
                "issue": f"Says '{m.group(0)}' but code has {endpoint_count} endpoints",
                "line_approx": content[:m.start()].count('\n') + 1,
                "old": m.group(0),
                "new": f"{endpoint_count} endpoints",
            })

    # Check version mentions (look for x.y.z patterns near "version" or "v")
    version = state.get("version", "")
    if version and filepath.suffix in (".md", ".html", ".txt"):
        for m in re.finditer(r'(?:version|v)[\s:]*(\d+\.\d+\.\d+)', content, re.IGNORECASE):
            mentioned_ver = m.group(1)
            if mentioned_ver != version and mentioned_ver not in ("0.0.1", "2.1"):
                # Skip changelog entries (they list old versions intentionally)
                if "CHANGELOG" not in rel.upper():
                    issues.append({
                        "file": rel, "desc": description, "severity": "warning",
                        "issue": f"Mentions version {mentioned_ver}, current is {version}",
                        "line_approx": content[:m.start()].count('\n') + 1,
                    })

    # Check test count mentions
    unit = state.get("unit_tests", 0)
    e2e = state.get("e2e_tests", 0)
    total = unit + e2e
    for m in re.finditer(r'(\d+)\s*(?:unit\s*)?tests', content, re.IGNORECASE):
        mentioned = int(m.group(1))
        # Only flag if it's clearly a total test count and significantly off
        if mentioned > 20 and abs(mentioned - total) > 10 and abs(mentioned - unit) > 10:
            issues.append({
                "file": rel, "desc": description, "severity": "warning",
                "issue": f"Says '{m.group(0)}' but current count is {unit} unit + {e2e} e2e = {total} total",
                "line_approx": content[:m.start()].count('\n') + 1,
            })

    return issues


def run_audit(state: dict) -> list[dict]:
    """Run full audit across all marketing materials."""
    all_issues = []
    for rel_path, desc in MARKETING_FILES:
        filepath = ROOT / rel_path
        issues = check_file(filepath, desc, state)
        all_issues.extend(issues)
    return all_issues


# ---------------------------------------------------------------------------
# 4. Output
# ---------------------------------------------------------------------------

def print_report(state: dict, issues: list[dict]):
    """Print human-readable audit report."""
    print("=" * 60)
    print("MARKETING SYNC AUDIT")
    print("=" * 60)
    print()
    print("Product State (from code):")
    for k, v in state.items():
        print(f"  {k}: {v}")
    print()

    if not issues:
        print("ALL CLEAR — no stale facts found in marketing materials.")
        return

    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for i in errors:
            line = f" (line ~{i['line_approx']})" if "line_approx" in i else ""
            print(f"  [{i['desc']}] {i['file']}{line}")
            print(f"    {i['issue']}")
            if "old" in i:
                print(f"    Fix: '{i['old']}' -> '{i['new']}'")
        print()

    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for i in warnings:
            line = f" (line ~{i['line_approx']})" if "line_approx" in i else ""
            print(f"  [{i['desc']}] {i['file']}{line}")
            print(f"    {i['issue']}")
        print()

    print(f"Total: {len(errors)} errors, {len(warnings)} warnings across {len(MARKETING_FILES)} files")


def main():
    parser = argparse.ArgumentParser(description="Marketing material sync checker")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--fix", action="store_true", help="Show fix suggestions")
    args = parser.parse_args()

    state = get_product_state()
    issues = run_audit(state)

    if args.json:
        print(json.dumps({"state": state, "issues": issues}, indent=2))
    else:
        print_report(state, issues)

    # Exit code: 1 if errors found
    sys.exit(1 if any(i["severity"] == "error" for i in issues) else 0)


if __name__ == "__main__":
    main()
