#!/usr/bin/env python3
"""Cross-Agent Trigger Detector — advisory output for which agents to run.

Analyzes staged git changes against the trigger matrix from AGENT_ROLES.md
and prints which agent reviews are recommended.

Usage:
  python scripts/trigger_check.py          # Check staged files
  python scripts/trigger_check.py --diff   # Check uncommitted changes
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Trigger rules: (file pattern, list of triggered agents)
TRIGGER_RULES = [
    # Code changes
    ("src/bitcoin_api/routers/", ["Marketing", "Security", "QA", "Architect"]),
    ("src/bitcoin_api/middleware.py", ["Security (owner)", "Architect"]),
    ("src/bitcoin_api/auth.py", ["Security (owner)", "Architect"]),
    ("src/bitcoin_api/rate_limit.py", ["Security", "Architect"]),
    ("src/bitcoin_api/config.py", ["Architect", "Security", "OPERATIONS.md"]),
    ("src/bitcoin_api/db.py", ["Security", "Architect"]),
    ("src/bitcoin_api/migrations/", ["Security", "Architect"]),
    ("src/bitcoin_api/services/", ["QA", "Architect"]),
    # Static / marketing
    ("static/", ["Marketing (sitemap)", "Security (CSP review)"]),
    ("static/privacy.html", ["Legal (owner)", "Security"]),
    ("static/terms.html", ["Legal (owner)"]),
    # Docs
    ("docs/SCOPE_OF_WORK.md", ["Architect (owner)"]),
    ("docs/BUSINESS_PLAN.md", ["Finance", "Product"]),
    ("docs/AGENT_ROLES.md", ["All agents"]),
    ("docs/OPERATIONS.md", ["Architect"]),
    ("docs/marketing/", ["Marketing (owner)"]),
    # Tests
    ("tests/", ["QA", "Marketing (test counts)"]),
    # Config / deploy
    ("pyproject.toml", ["Marketing (version)", "Architect"]),
    ("scripts/deploy", ["Architect", "Security", "OPERATIONS.md"]),
    (".github/", ["Architect", "Security"]),
    ("Dockerfile", ["Architect", "Security"]),
]


def get_changed_files(diff_mode: bool = False) -> list[str]:
    cmd = ["git", "diff", "--name-only"] if diff_mode else ["git", "diff", "--cached", "--name-only"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]


def main():
    diff_mode = "--diff" in sys.argv
    files = get_changed_files(diff_mode)

    if not files:
        return

    triggered = {}  # agent -> set of reasons
    for fname in files:
        for pattern, agents in TRIGGER_RULES:
            if fname.startswith(pattern) or f"/{pattern}" in f"/{fname}":
                for agent in agents:
                    triggered.setdefault(agent, set()).add(fname)

    if not triggered:
        return

    print(f"\n{'-'*50}")
    print("AGENT TRIGGER ADVISORY")
    print(f"{'-'*50}")
    for agent, reasons in sorted(triggered.items()):
        short_reasons = ", ".join(sorted(reasons)[:3])
        if len(reasons) > 3:
            short_reasons += f" (+{len(reasons)-3} more)"
        print(f"  -> {agent}: {short_reasons}")
    print(f"{'-'*50}\n")


if __name__ == "__main__":
    main()
