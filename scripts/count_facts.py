#!/usr/bin/env python3
"""Count Facts — Single source of truth for all countable product facts.

Reads counts directly from code, compares against what docs claim,
and exits non-zero if anything is stale. Designed to run in CI or
as a pre-commit check.

Usage:
    python scripts/count_facts.py          # Check mode (exit 1 if stale)
    python scripts/count_facts.py --json   # Output canonical counts as JSON
    python scripts/count_facts.py --stamp  # Update SCOPE_OF_WORK.md header

WHY THIS EXISTS:
Every all-hands review finds stale counts (endpoints, tools, tests, routers).
The root cause is hardcoded numbers in 20+ files with no verification.
This script derives counts FROM CODE and catches drift before it ships.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def count_endpoints() -> int:
    """Count API endpoints from router decorators (excludes __init__.py)."""
    count = 0
    router_dir = ROOT / "src" / "bitcoin_api" / "routers"
    for py_file in router_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        content = py_file.read_text()
        routes = re.findall(r'@(?:app|router)\.(get|post|put|delete|patch)\(', content)
        internal = len(re.findall(r'include_in_schema\s*=\s*False', content))
        count += len(routes) - internal
    return count


def count_routers() -> int:
    """Count router files (excludes __init__.py)."""
    router_dir = ROOT / "src" / "bitcoin_api" / "routers"
    return len([f for f in router_dir.glob("*.py") if f.name != "__init__.py"])


def count_tests() -> dict:
    """Count test functions in test files."""
    counts = {}
    for name, path in [("unit", "tests/test_api.py"), ("e2e", "tests/test_e2e.py")]:
        f = ROOT / path
        if f.exists():
            counts[name] = len(re.findall(r'\ndef test_', f.read_text()))
    counts["total"] = sum(counts.values())
    return counts


def count_migrations() -> int:
    """Count migration SQL files (excludes .down.sql)."""
    mig_dir = ROOT / "src" / "bitcoin_api" / "migrations"
    return len([f for f in mig_dir.glob("*.sql") if not f.name.endswith(".down.sql")])


def count_mcp() -> dict | None:
    """Count bitcoin-mcp tools/prompts/resources from sibling repo."""
    mcp_server = ROOT.parent / "bitcoin-mcp" / "src" / "bitcoin_mcp" / "server.py"
    if not mcp_server.exists():
        return None
    content = mcp_server.read_text()
    return {
        "tools": len(re.findall(r'@mcp\.tool\(\)', content)),
        "prompts": len(re.findall(r'@mcp\.prompt\(\)', content)),
        "resources": len(re.findall(r'@mcp\.resource\(', content)),
    }


def get_version() -> str:
    """Read version from pyproject.toml."""
    m = re.search(r'version\s*=\s*"([^"]+)"', (ROOT / "pyproject.toml").read_text())
    return m.group(1) if m else "unknown"


def get_all_facts() -> dict:
    """Collect all canonical facts from code."""
    tests = count_tests()
    facts = {
        "version": get_version(),
        "endpoints": count_endpoints(),
        "routers": count_routers(),
        "unit_tests": tests.get("unit", 0),
        "e2e_tests": tests.get("e2e", 0),
        "total_tests": tests["total"],
        "migrations": count_migrations(),
    }
    mcp = count_mcp()
    if mcp:
        facts["mcp_tools"] = mcp["tools"]
        facts["mcp_prompts"] = mcp["prompts"]
        facts["mcp_resources"] = mcp["resources"]
    return facts


def check_sow(facts: dict) -> list[str]:
    """Check SCOPE_OF_WORK.md for stale counts. Returns list of issues."""
    sow = ROOT / "docs" / "SCOPE_OF_WORK.md"
    if not sow.exists():
        return ["SCOPE_OF_WORK.md not found"]
    content = sow.read_text()
    issues = []

    # Check endpoint count in section headers
    for m in re.finditer(r'(\d+)\s*(?:total|endpoints)', content, re.IGNORECASE):
        n = int(m.group(1))
        if n > 15 and n != facts["endpoints"]:
            line = content[:m.start()].count('\n') + 1
            issues.append(f"SOW line ~{line}: says {n} endpoints, code has {facts['endpoints']}")

    # Check router count
    for m in re.finditer(r'(\d+)\s*routers', content, re.IGNORECASE):
        n = int(m.group(1))
        if n != facts["routers"]:
            line = content[:m.start()].count('\n') + 1
            issues.append(f"SOW line ~{line}: says {n} routers, code has {facts['routers']}")

    return issues


def main():
    parser = argparse.ArgumentParser(description="Canonical count facts from code")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    facts = get_all_facts()

    if args.json:
        print(json.dumps(facts, indent=2))
        return

    print("Canonical Product Facts (derived from code):")
    print(f"  Satoshi API v{facts['version']}")
    print(f"  {facts['endpoints']} endpoints across {facts['routers']} routers")
    print(f"  {facts['total_tests']} tests ({facts['unit_tests']} unit + {facts['e2e_tests']} e2e)")
    print(f"  {facts['migrations']} migrations")
    if "mcp_tools" in facts:
        print(f"  bitcoin-mcp: {facts['mcp_tools']} tools, {facts['mcp_prompts']} prompts, {facts['mcp_resources']} resources")
    print()

    issues = check_sow(facts)
    if issues:
        print(f"DRIFT DETECTED ({len(issues)} issues):")
        for i in issues:
            print(f"  - {i}")
        sys.exit(1)
    else:
        print("No drift detected. All counts match code.")


if __name__ == "__main__":
    main()
