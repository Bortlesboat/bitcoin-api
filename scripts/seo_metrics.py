#!/usr/bin/env python3
"""
SEO & AI Search Metrics Tracker for Satoshi API.

Tracks: AI search mentions, search engine indexing, GitHub signals,
PyPI downloads, PR merge status, and page accessibility.

Usage:
    python scripts/seo_metrics.py              # Run all checks, save to DB
    python scripts/seo_metrics.py --report     # Print latest report
    python scripts/seo_metrics.py --history    # Show trend over time
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "seo_metrics.db"
SITE = "https://bitcoinsapi.com"
GITHUB_REPO = "Bortlesboat/bitcoin-api"
PYPI_PACKAGE = "satoshi-api"

# Pages we expect to be indexed
SEO_PAGES = [
    "/",
    "/vs-mempool",
    "/vs-blockcypher",
    "/best-bitcoin-api-for-developers",
    "/bitcoin-api-for-ai-agents",
    "/self-hosted-bitcoin-api",
    "/bitcoin-fee-api",
    "/bitcoin-mempool-api",
    "/robots.txt",
    "/sitemap.xml",
]

# Queries to check for AI/search mentions
AI_QUERIES = [
    "best bitcoin api for developers",
    "bitcoin api for ai agents",
    "self-hosted bitcoin api",
    "bitcoin fee estimation api",
    "bitcoin mempool api",
    "satoshi api bitcoin",
]

# PRs we submitted
SUBMITTED_PRS = [
    {"repo": "igorbarinov/awesome-bitcoin", "number": 141},
    {"repo": "public-apis/public-apis", "number": 5397},
    {"repo": "CoinQuanta/awesome-crypto-api", "number": 9},
    {"repo": "punkpeye/awesome-mcp-servers", "number": 2847},
    {"repo": "appcypher/awesome-mcp-servers", "number": 516},
]

SUBMITTED_ISSUES = [
    {"repo": "APIs-guru/openapi-directory", "number": 1611},
]


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            category TEXT NOT NULL,
            metric TEXT NOT NULL,
            value TEXT,
            numeric_value REAL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics(timestamp)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_metrics_cat ON metrics(category, metric)
    """)
    conn.commit()
    return conn


def save_metric(conn, category, metric, value, numeric_value=None):
    ts = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO metrics (timestamp, category, metric, value, numeric_value) VALUES (?, ?, ?, ?, ?)",
        (ts, category, metric, str(value), numeric_value),
    )
    conn.commit()


def check_page_accessibility():
    """Check if all SEO pages are accessible (HTTP 200)."""
    results = {}
    for page in SEO_PAGES:
        url = f"{SITE}{page}"
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "SEO-Metrics-Checker/1.0")
            resp = urllib.request.urlopen(req, timeout=10)
            results[page] = resp.status
        except urllib.error.HTTPError as e:
            results[page] = e.code
        except Exception as e:
            results[page] = str(e)
    return results


def check_github_stats():
    """Get GitHub repo stats: stars, forks, watchers."""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{GITHUB_REPO}", "--jq",
             '{stars: .stargazers_count, forks: .forks_count, watchers: .subscribers_count, open_issues: .open_issues_count}'],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return None


def check_pypi_downloads():
    """Get PyPI download stats for the last month."""
    try:
        url = f"https://pypistats.org/api/packages/{PYPI_PACKAGE}/recent"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "SEO-Metrics-Checker/1.0")
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return data.get("data", {})
    except Exception:
        return None


def check_pr_status():
    """Check merge status of submitted PRs."""
    results = []
    for pr in SUBMITTED_PRS:
        try:
            result = subprocess.run(
                ["gh", "api", f"repos/{pr['repo']}/pulls/{pr['number']}", "--jq",
                 '{state: .state, merged: .merged, title: .title}'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                results.append({
                    "repo": pr["repo"],
                    "number": pr["number"],
                    "state": data.get("state"),
                    "merged": data.get("merged", False),
                })
        except Exception:
            results.append({"repo": pr["repo"], "number": pr["number"], "state": "error"})
    return results


def check_issue_status():
    """Check status of submitted issues."""
    results = []
    for issue in SUBMITTED_ISSUES:
        try:
            result = subprocess.run(
                ["gh", "api", f"repos/{issue['repo']}/issues/{issue['number']}", "--jq",
                 '{state: .state, title: .title}'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                results.append({
                    "repo": issue["repo"],
                    "number": issue["number"],
                    "state": data.get("state"),
                })
        except Exception:
            results.append({"repo": issue["repo"], "number": issue["number"], "state": "error"})
    return results


def check_search_indexing():
    """Check if pages appear in Bing index using site: query."""
    try:
        url = f"https://www.bing.com/search?q=site%3Abitcoinsapi.com"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (compatible; SEO-Metrics/1.0)")
        resp = urllib.request.urlopen(req, timeout=10)
        body = resp.read().decode("utf-8", errors="replace")
        # Count approximate results
        if "No results found" in body or "did not match" in body:
            return 0
        # Try to extract count
        import re
        match = re.search(r'([\d,]+)\s+results', body)
        if match:
            return int(match.group(1).replace(",", ""))
        # If we got content but can't parse count, at least 1
        if "bitcoinsapi.com" in body:
            return 1
        return 0
    except Exception:
        return -1  # error


def check_ai_search_mentions():
    """Check if 'satoshi api' or 'bitcoinsapi' appears in search results for target queries."""
    mentions = {}
    for query in AI_QUERIES:
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://www.bing.com/search?q={encoded}"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Mozilla/5.0 (compatible; SEO-Metrics/1.0)")
            resp = urllib.request.urlopen(req, timeout=10)
            body = resp.read().decode("utf-8", errors="replace").lower()
            found = "satoshi api" in body or "bitcoinsapi" in body or "satoshi-api" in body
            mentions[query] = found
        except Exception:
            mentions[query] = None  # error
    return mentions


def run_all_checks(conn):
    """Run all metrics checks and save to DB."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"Running SEO metrics check at {ts}\n")

    # 1. Page accessibility
    print("Checking page accessibility...")
    pages = check_page_accessibility()
    accessible = sum(1 for v in pages.values() if v == 200)
    total = len(pages)
    save_metric(conn, "pages", "accessible", f"{accessible}/{total}", accessible)
    for page, status in pages.items():
        icon = "+" if status == 200 else "x"
        print(f"  [{icon}] {page} -> {status}")

    # 2. GitHub stats
    print("\nChecking GitHub stats...")
    gh = check_github_stats()
    if gh:
        for key, val in gh.items():
            save_metric(conn, "github", key, val, val)
            print(f"  {key}: {val}")
    else:
        print("  (failed to fetch)")

    # 3. PyPI downloads
    print("\nChecking PyPI downloads...")
    pypi = check_pypi_downloads()
    if pypi:
        for period, count in pypi.items():
            save_metric(conn, "pypi", f"downloads_{period}", count, count)
            print(f"  {period}: {count}")
    else:
        print("  (failed to fetch)")

    # 4. PR status
    print("\nChecking PR merge status...")
    prs = check_pr_status()
    merged_count = 0
    for pr in prs:
        merged = pr.get("merged", False)
        state = pr.get("state", "unknown")
        if merged:
            merged_count += 1
        icon = "M" if merged else ("O" if state == "open" else "C")
        print(f"  [{icon}] {pr['repo']}#{pr['number']} -> {state}" + (" (MERGED)" if merged else ""))
    save_metric(conn, "prs", "merged", f"{merged_count}/{len(prs)}", merged_count)
    save_metric(conn, "prs", "total", len(prs), len(prs))

    # 5. Issue status
    print("\nChecking issue status...")
    issues = check_issue_status()
    for issue in issues:
        state = issue.get("state", "unknown")
        print(f"  {issue['repo']}#{issue['number']} -> {state}")
        save_metric(conn, "issues", f"{issue['repo']}#{issue['number']}", state)

    # 6. Search indexing
    print("\nChecking Bing indexing...")
    indexed = check_search_indexing()
    save_metric(conn, "search", "bing_indexed_pages", indexed, indexed if indexed >= 0 else None)
    if indexed >= 0:
        print(f"  Bing: ~{indexed} pages indexed")
    else:
        print("  Bing: (check failed)")

    # 7. Search mentions
    print("\nChecking search mentions for target queries...")
    mentions = check_ai_search_mentions()
    mention_count = sum(1 for v in mentions.values() if v is True)
    save_metric(conn, "search", "query_mentions", f"{mention_count}/{len(mentions)}", mention_count)
    for query, found in mentions.items():
        icon = "+" if found else ("-" if found is False else "?")
        print(f"  [{icon}] \"{query}\"")

    print(f"\n{'='*50}")
    print(f"Summary: {accessible}/{total} pages live, {merged_count}/{len(prs)} PRs merged, "
          f"{mention_count}/{len(mentions)} search mentions")
    print(f"Data saved to {DB_PATH}")


def show_report(conn):
    """Show the latest metrics."""
    print("Latest SEO Metrics Report")
    print("=" * 50)

    categories = conn.execute(
        "SELECT DISTINCT category FROM metrics ORDER BY category"
    ).fetchall()

    for (cat,) in categories:
        print(f"\n{cat.upper()}")
        rows = conn.execute("""
            SELECT metric, value, numeric_value, timestamp
            FROM metrics
            WHERE category = ?
            AND timestamp = (SELECT MAX(timestamp) FROM metrics WHERE category = ? AND metric = metrics.metric)
            ORDER BY metric
        """, (cat, cat)).fetchall()
        for metric, value, num, ts in rows:
            date = ts[:10] if ts else "?"
            print(f"  {metric}: {value} ({date})")


def show_history(conn):
    """Show metrics trend over time."""
    print("SEO Metrics History")
    print("=" * 50)

    # Get unique dates
    dates = conn.execute("""
        SELECT DISTINCT substr(timestamp, 1, 10) as date FROM metrics ORDER BY date
    """).fetchall()

    if not dates:
        print("No data yet. Run: python scripts/seo_metrics.py")
        return

    key_metrics = [
        ("pages", "accessible"),
        ("github", "stars"),
        ("pypi", "downloads_last_month"),
        ("prs", "merged"),
        ("search", "bing_indexed_pages"),
        ("search", "query_mentions"),
    ]

    # Header
    print(f"{'Date':<12}", end="")
    for cat, metric in key_metrics:
        label = f"{cat}/{metric}"[:18]
        print(f"{label:<20}", end="")
    print()
    print("-" * (12 + 20 * len(key_metrics)))

    for (date,) in dates:
        print(f"{date:<12}", end="")
        for cat, metric in key_metrics:
            row = conn.execute("""
                SELECT value FROM metrics
                WHERE category = ? AND metric = ?
                AND substr(timestamp, 1, 10) = ?
                ORDER BY timestamp DESC LIMIT 1
            """, (cat, metric, date)).fetchone()
            val = row[0] if row else "-"
            print(f"{str(val):<20}", end="")
        print()


def main():
    parser = argparse.ArgumentParser(description="SEO Metrics Tracker")
    parser.add_argument("--report", action="store_true", help="Show latest report")
    parser.add_argument("--history", action="store_true", help="Show trend over time")
    args = parser.parse_args()

    conn = init_db()

    if args.report:
        show_report(conn)
    elif args.history:
        show_history(conn)
    else:
        run_all_checks(conn)

    conn.close()


if __name__ == "__main__":
    main()
