#!/usr/bin/env python3
"""Privacy Promise Enforcer — detects tracking/analytics additions in staged files.

Usage:
  python scripts/privacy_check.py              # Check staged git changes
  python scripts/privacy_check.py --all        # Scan entire codebase
  python scripts/privacy_check.py --hook       # Exit 1 on violations (for pre-commit)

Maintains an approved external domains list. Any new external domain
in CSP, <script src=>, or fetch/requests calls gets flagged.
"""

import re
import subprocess
import sys
from pathlib import Path

# --- Configuration ---

TRACKING_PATTERNS = [
    # Analytics services
    r"google-analytics", r"googletagmanager", r"gtag\(", r"ga\(",
    r"mixpanel", r"hotjar", r"heap\.io", r"amplitude",
    r"segment\.io", r"segment\.com", r"rudderstack",
    r"plausible\.io", r"fathom\.io", r"matomo", r"piwik",
    r"cloudflareinsights", r"cf-beacon",
    # Ad/pixel trackers
    r"facebook.*pixel", r"fbevents", r"doubleclick",
    r"googlesyndication", r"adsbygoogle",
    # Fingerprinting
    r"canvas\.toDataURL", r"navigator\.plugins", r"AudioContext",
    r"fingerprintjs", r"clientjs",
    # Cookie tracking (but not cookie-based auth which we don't use)
    r"document\.cookie\s*=", r"setCookie\(",
]

APPROVED_EXTERNAL_DOMAINS = {
    "bitcoinsapi.com",
    "raw.githubusercontent.com",
    "schema.org",
    "www.coingecko.com",
    "api.coingecko.com",
    "cdn.jsdelivr.net",
    "us.i.posthog.com",
    "us-assets.i.posthog.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
}

SECRET_PATTERNS = [
    r"sk_live_[a-zA-Z0-9]+",           # Stripe live key
    r"sk_test_[a-zA-Z0-9]+",           # Stripe test key
    r"re_[a-zA-Z0-9]{20,}",            # Resend API key
    r"whsec_[a-zA-Z0-9]+",             # Stripe webhook secret
    r"UPSTASH_[A-Z_]*=\S+",            # Upstash credentials in assignment
    r"phc_[a-zA-Z0-9]{30,}",           # PostHog project key (flag if in .py files)
    r"btc_[0-9a-f]{32}",               # Satoshi API key
]

# Files where PostHog project key is expected (client-side, public by design)
SECRET_ALLOWLIST = {
    "static/index.html", "static\\index.html",
    "static/vs-mempool.html", "static\\vs-mempool.html",
    "static/vs-blockcypher.html", "static\\vs-blockcypher.html",
}

SCAN_EXTENSIONS = {".py", ".html", ".js", ".ts", ".css"}

# Files that define tracking patterns (self-references, not violations)
SELF_EXCLUDE = {"scripts/privacy_check.py", "scripts\\privacy_check.py"}

ROOT = Path(__file__).resolve().parent.parent


def get_staged_diff() -> list[tuple[str, str]]:
    """Return list of (filename, diff_content) for staged files."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True, cwd=ROOT,
    )
    files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]

    diffs = []
    for fname in files:
        if not any(fname.endswith(ext) for ext in SCAN_EXTENSIONS):
            continue
        diff_result = subprocess.run(
            ["git", "diff", "--cached", "--", fname],
            capture_output=True, cwd=ROOT,
        )
        try:
            stdout = diff_result.stdout.decode("utf-8", errors="replace")
        except Exception:
            continue
        # Only check added lines (lines starting with +)
        added = "\n".join(
            line[1:] for line in stdout.split("\n")
            if line.startswith("+") and not line.startswith("+++")
        )
        if added:
            diffs.append((fname, added))
    return diffs


def scan_file(filepath: Path) -> list[tuple[int, str, str]]:
    """Scan a file for tracking patterns. Returns [(line_num, line, pattern)]."""
    violations = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeDecodeError):
        return violations

    for i, line in enumerate(content.split("\n"), 1):
        for pattern in TRACKING_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                violations.append((i, line.strip(), pattern))
                break  # one match per line is enough
    return violations


def scan_text(text: str, source: str) -> list[tuple[str, str, str]]:
    """Scan text content for tracking patterns. Returns [(source, line, pattern)]."""
    violations = []
    for line in text.split("\n"):
        for pattern in TRACKING_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                violations.append((source, line.strip(), pattern))
                break
    return violations


def check_csp_domains(filepath: Path) -> list[str]:
    """Extract external domains from CSP directives and flag unapproved ones."""
    warnings = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeDecodeError):
        return warnings

    # Find CSP string in middleware
    csp_matches = re.findall(r"https?://([a-zA-Z0-9._-]+)", content)
    for domain in set(csp_matches):
        if domain not in APPROVED_EXTERNAL_DOMAINS:
            warnings.append(f"Unapproved external domain in CSP: {domain}")
    return warnings


def check_html_external_scripts(html_dir: Path) -> list[str]:
    """Scan HTML files for external <script> tags not in approved list."""
    warnings = []
    for html_file in html_dir.glob("*.html"):
        try:
            content = html_file.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        # Match <script src="https://..."> or <script defer src='https://...'>
        for match in re.finditer(r"<script[^>]+src=['\"]https?://([^/'\"]+)", content):
            domain = match.group(1)
            if domain not in APPROVED_EXTERNAL_DOMAINS:
                warnings.append(f"{html_file.name}: external script from unapproved domain: {domain}")
    return warnings


def main():
    hook_mode = "--hook" in sys.argv
    scan_all = "--all" in sys.argv

    violations = []
    warnings = []

    if scan_all:
        # Full codebase scan
        for ext in SCAN_EXTENSIONS:
            for filepath in ROOT.rglob(f"*{ext}"):
                if ".git" in filepath.parts or "node_modules" in filepath.parts:
                    continue
                rel = str(filepath.relative_to(ROOT))
                if rel in SELF_EXCLUDE or rel.replace("/", "\\") in SELF_EXCLUDE:
                    continue
                file_violations = scan_file(filepath)
                for line_num, line, pattern in file_violations:
                    violations.append((rel, line_num, line, pattern))
    else:
        # Staged changes only
        diffs = get_staged_diff()
        for fname, content in diffs:
            if fname in SELF_EXCLUDE or fname.replace("/", "\\") in SELF_EXCLUDE:
                continue
            text_violations = scan_text(content, fname)
            for source, line, pattern in text_violations:
                violations.append((source, 0, line, pattern))

    # Secret/credential scanning
    if scan_all:
        for ext in SCAN_EXTENSIONS:
            for filepath in ROOT.rglob(f"*{ext}"):
                if ".git" in filepath.parts or "node_modules" in filepath.parts:
                    continue
                rel = str(filepath.relative_to(ROOT))
                if rel in SELF_EXCLUDE or rel.replace("/", "\\") in SELF_EXCLUDE:
                    continue
                try:
                    content = filepath.read_text(encoding="utf-8", errors="ignore")
                except (OSError, UnicodeDecodeError):
                    continue
                for i, line in enumerate(content.split("\n"), 1):
                    for pattern in SECRET_PATTERNS:
                        if re.search(pattern, line):
                            # Allow PostHog public key in HTML files
                            if "phc_" in pattern and (rel in SECRET_ALLOWLIST or rel.replace("/", "\\") in SECRET_ALLOWLIST):
                                continue
                            warnings.append(f"{rel}:{i} — possible secret: matched '{pattern}'")
                            break
    else:
        for fname, content in (diffs if not scan_all else []):
            if fname in SELF_EXCLUDE or fname.replace("/", "\\") in SELF_EXCLUDE:
                continue
            for line in content.split("\n"):
                for pattern in SECRET_PATTERNS:
                    if re.search(pattern, line):
                        if "phc_" in pattern and (fname in SECRET_ALLOWLIST or fname.replace("/", "\\") in SECRET_ALLOWLIST):
                            continue
                        warnings.append(f"{fname} — possible secret in staged change: matched '{pattern}'")
                        break

    # Always check CSP and static HTML
    middleware = ROOT / "src" / "bitcoin_api" / "middleware.py"
    if middleware.exists():
        warnings.extend(check_csp_domains(middleware))

    for static_dir in [ROOT / "static", ROOT / "docs" / "website"]:
        if static_dir.exists():
            warnings.extend(check_html_external_scripts(static_dir))

    # Report
    if violations:
        print(f"\n{'='*60}")
        print("PRIVACY PROMISE VIOLATIONS DETECTED")
        print(f"{'='*60}\n")
        for source, line_num, line, pattern in violations:
            loc = f"{source}:{line_num}" if line_num else source
            print(f"  [{loc}] matched '{pattern}'")
            print(f"    {line[:120]}\n")
        print(f"Total: {len(violations)} violation(s)")
        print("Review with /security-review before committing.\n")

    if warnings:
        print(f"\n{'='*60}")
        print("EXTERNAL DOMAIN WARNINGS")
        print(f"{'='*60}\n")
        for w in warnings:
            print(f"  {w}")
        print(f"\nTotal: {len(warnings)} warning(s)")
        print(f"Approved domains: {', '.join(sorted(APPROVED_EXTERNAL_DOMAINS))}\n")

    if not violations and not warnings:
        print("Privacy check passed. No tracking patterns or unapproved domains found.")

    if hook_mode and (violations or warnings):
        print("BLOCKED: Fix violations before committing, or use --no-verify to bypass.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
