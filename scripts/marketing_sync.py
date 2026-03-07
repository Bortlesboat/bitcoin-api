#!/usr/bin/env python3
"""Marketing Sync Checker — ensures all marketing materials match product state.

Reads the canonical product facts from code/config, then scans all marketing
materials for stale numbers, outdated claims, or missing mentions.

Usage:
    python scripts/marketing_sync.py              # Full audit
    python scripts/marketing_sync.py --fix        # Auto-fix endpoint counts
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

    # Endpoint count from router files (count @router.get/post/etc decorators)
    endpoint_count = 0
    router_dir = ROOT / "src" / "bitcoin_api" / "routers"
    if router_dir.exists():
        for py_file in router_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            content = py_file.read_text()
            routes = re.findall(r'@(?:app|router)\.(get|post|put|delete|patch)\(', content)
            internal = len(re.findall(r'include_in_schema\s*=\s*False', content))
            endpoint_count += len(routes) - internal
    state["endpoint_count"] = endpoint_count

    # Router count
    if router_dir.exists():
        router_files = [f for f in router_dir.glob("*.py") if f.name != "__init__.py"]
        state["router_count"] = len(router_files)

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
    ("README.md", "GitHub README"),
    ("blog-post.md", "Blog post"),
    ("static/vs-mempool.html", "SEO: vs Mempool"),
    ("static/vs-blockcypher.html", "SEO: vs BlockCypher"),
    ("static/best-bitcoin-api-for-developers.html", "SEO: Best Bitcoin API"),
    ("static/bitcoin-api-for-ai-agents.html", "SEO: AI Agents"),
    ("static/self-hosted-bitcoin-api.html", "SEO: Self-hosted"),
    ("static/bitcoin-fee-api.html", "SEO: Fee API"),
    ("static/bitcoin-mempool-api.html", "SEO: Mempool API"),
    ("static/og-image.svg", "OG image"),
    ("docs/marketing/drafts/reddit-bitcoindev.md", "Draft: r/BitcoinDev"),
    ("docs/marketing/drafts/reddit-selfhosted.md", "Draft: r/selfhosted"),
    ("docs/marketing/drafts/reddit-bitcoin.md", "Draft: r/Bitcoin"),
    ("docs/marketing/drafts/reddit-python.md", "Draft: r/Python"),
    ("docs/marketing/drafts/stacker-news.md", "Draft: Stacker News"),
    ("docs/marketing/drafts/hackernews-show-hn.md", "Draft: Hacker News"),
    ("docs/marketing/show-hn.md", "Show HN draft"),
    ("docs/marketing/devto-article.md", "Dev.to article"),
    ("docs/marketing/launch-plan.md", "Launch plan"),
    ("docs/marketing/brand-strategy.md", "Brand strategy"),
    ("docs/marketing/distribution-channels.md", "Distribution channels"),
    ("docs/BUSINESS_PLAN.md", "Business plan"),
    ("umbrel/umbrel-app.yml", "Umbrel app manifest"),
    ("static/bitcoin-mcp-setup-guide.html", "SEO: MCP Setup Guide"),
]

# Files where endpoint counts should NOT be auto-fixed (historical references)
NO_FIX_FILES = {"CHANGELOG.md", "docs/SCOPE_OF_WORK.md", "docs/BUSINESS_PLAN.md"}


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
    for m in re.finditer(r'(\d+)\+?\s*endpoints', content, re.IGNORECASE):
        mentioned = int(m.group(1))
        if mentioned < 15:  # Skip small counts like "5 endpoints" in feature descriptions
            continue
        if mentioned != endpoint_count:
            issues.append({
                "file": rel, "desc": description, "severity": "error",
                "issue": f"Says '{m.group(0)}' but code has {endpoint_count} endpoints",
                "line_approx": content[:m.start()].count('\n') + 1,
                "old": m.group(0),
                "new": f"{endpoint_count} endpoints",
                "fixable": True,
            })

    # Also catch "NN Endpoints" (capitalized, as in headings like "48 Endpoints")
    for m in re.finditer(r'(\d+)\s+Endpoints', content):
        mentioned = int(m.group(1))
        if mentioned < 15:
            continue
        if mentioned != endpoint_count:
            issues.append({
                "file": rel, "desc": description, "severity": "error",
                "issue": f"Says '{m.group(0)}' but code has {endpoint_count}",
                "line_approx": content[:m.start()].count('\n') + 1,
                "old": m.group(0),
                "new": f"{endpoint_count} Endpoints",
                "fixable": True,
            })

    # Check version mentions (look for x.y.z patterns near "version" or "v")
    version = state.get("version", "")
    if version and filepath.suffix in (".md", ".html", ".txt"):
        for m in re.finditer(r'(?:version|v)[\s:]*(\d+\.\d+\.\d+)', content, re.IGNORECASE):
            mentioned_ver = m.group(1)
            if mentioned_ver != version and mentioned_ver not in ("0.0.1", "2.1"):
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
# 4. Auto-fix endpoint counts
# ---------------------------------------------------------------------------

def fix_endpoint_counts(state: dict, issues: list[dict], dry_run: bool = False) -> int:
    """Replace stale endpoint counts in marketing files. Returns count of files fixed."""
    endpoint_count = state["endpoint_count"]
    files_fixed = set()

    for issue in issues:
        if not issue.get("fixable"):
            continue
        rel = issue["file"]
        if rel in NO_FIX_FILES:
            continue

        filepath = ROOT / rel
        if not filepath.exists():
            continue

        content = filepath.read_text(encoding="utf-8", errors="ignore")

        # Replace all endpoint count patterns (e.g., "48 endpoints" -> "50 endpoints")
        def replace_count(m):
            num = int(m.group(1))
            if num < 15:
                return m.group(0)
            rest = m.group(0)[len(m.group(1)):]  # everything after the number
            return f"{endpoint_count}{rest}"

        new_content = re.sub(r'(\d+)(\+?\s*[Ee]ndpoints)', replace_count, content)

        if new_content != content:
            if dry_run:
                print(f"  Would fix: {rel}")
            else:
                filepath.write_text(new_content, encoding="utf-8")
                print(f"  Fixed: {rel}")
            files_fixed.add(rel)

    return len(files_fixed)


# ---------------------------------------------------------------------------
# 5. Output
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
    parser.add_argument("--fix", action="store_true", help="Auto-fix endpoint counts in all marketing files")
    parser.add_argument("--dry-run", action="store_true", help="Show what --fix would change without writing")
    args = parser.parse_args()

    state = get_product_state()
    issues = run_audit(state)

    if args.fix or args.dry_run:
        n = fix_endpoint_counts(state, issues, dry_run=args.dry_run)
        if not args.dry_run and n > 0:
            # Re-audit after fix
            issues = run_audit(state)
            print(f"\nFixed {n} files. Re-running audit...\n")

    if args.json:
        print(json.dumps({"state": state, "issues": issues}, indent=2))
    else:
        print_report(state, issues)

    sys.exit(1 if any(i["severity"] == "error" for i in issues) else 0)


if __name__ == "__main__":
    main()
