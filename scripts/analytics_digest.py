#!/usr/bin/env python3
"""Daily analytics digest — queries Satoshi API admin endpoints and emails a summary.

Usage:
    python scripts/analytics_digest.py                    # Print to stdout
    python scripts/analytics_digest.py --email            # Send via Resend
    python scripts/analytics_digest.py --email --to X     # Override recipient

Designed to run as a daily cron job on GMKtec or Main PC.
Requires: SATOSHI_ADMIN_KEY env var (or reads from .env in repo root).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

API_BASE = os.getenv("SATOSHI_API_URL", "https://bitcoinsapi.com")
ADMIN_KEY = os.getenv("SATOSHI_ADMIN_KEY", "") or os.getenv("ADMIN_API_KEY", "")
DEFAULT_TO = "andrew.jaguars@gmail.com"


def _load_env():
    """Try loading .env from repo root if ADMIN_KEY not set."""
    global ADMIN_KEY
    if ADMIN_KEY:
        return
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("ADMIN_API_KEY="):
                ADMIN_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                break


def _api(path: str, timeout: int = 15) -> dict | None:
    """GET an admin analytics endpoint. Returns parsed JSON or None on error."""
    url = f"{API_BASE}/api/v1{path}"
    headers = {"X-Admin-Key": ADMIN_KEY, "User-Agent": "SatoshiDigest/1.0"}
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except (URLError, json.JSONDecodeError, OSError) as e:
        print(f"  WARN: {path} failed: {e}", file=sys.stderr)
        return None


def gather_metrics() -> dict:
    """Fetch all analytics endpoints and assemble a digest."""
    metrics = {}

    # Overview
    data = _api("/analytics/overview")
    if data and "data" in data:
        metrics["overview"] = data["data"]

    # Growth
    data = _api("/analytics/growth")
    if data and "data" in data:
        metrics["growth"] = data["data"]

    # Top endpoints (24h)
    data = _api("/analytics/endpoints?period=24h&limit=10")
    if data and "data" in data:
        metrics["top_endpoints"] = data["data"]

    # Errors
    data = _api("/analytics/errors?period=24h")
    if data and "data" in data:
        metrics["errors"] = data["data"]

    # Client types
    data = _api("/analytics/client-types?period=24h")
    if data and "data" in data:
        metrics["client_types"] = data["data"]

    # Latency
    data = _api("/analytics/latency?period=24h")
    if data and "data" in data:
        metrics["latency"] = data["data"]

    # Retention
    data = _api("/analytics/retention")
    if data and "data" in data:
        metrics["retention"] = data["data"]

    # Referrers
    data = _api("/analytics/referrers?period=24h&limit=10")
    if data and "data" in data:
        metrics["referrers"] = data["data"]

    # Funnel
    data = _api("/analytics/funnel?period=7d")
    if data and "data" in data:
        metrics["funnel"] = data["data"]

    return metrics


def format_text(metrics: dict) -> str:
    """Format metrics as plain-text digest."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"=== Satoshi API Daily Digest — {now} ===", ""]

    ov = metrics.get("overview", {})
    lines.append(f"Requests: 24h={ov.get('requests_24h', '?')}  7d={ov.get('requests_7d', '?')}  30d={ov.get('requests_30d', '?')}")
    lines.append(f"Unique keys (24h): {ov.get('unique_keys_24h', '?')}")
    lines.append(f"Error rate (24h): {ov.get('error_rate_24h', '?')}")
    lines.append(f"Avg latency (24h): {ov.get('avg_latency_ms_24h', '?')}ms")
    lines.append("")

    gr = metrics.get("growth", {})
    lines.append(f"Growth: DoD {gr.get('requests_dod_pct', '?')}%  WoW {gr.get('requests_wow_pct', '?')}%")
    lines.append(f"Keys: today={gr.get('keys_today', '?')}  yesterday={gr.get('keys_yesterday', '?')}  DoD {gr.get('keys_dod_pct', '?')}%")
    lines.append("")

    lat = metrics.get("latency", {})
    lines.append(f"Latency: p50={lat.get('p50', '?')}ms  p95={lat.get('p95', '?')}ms  p99={lat.get('p99', '?')}ms")
    lines.append("")

    ct = metrics.get("client_types", {})
    if ct.get("breakdown"):
        lines.append("Client Types:")
        for b in ct["breakdown"]:
            lines.append(f"  {b['client_type']}: {b['count']} ({b['pct']}%)")
        lines.append("")

    ret = metrics.get("retention", {})
    lines.append(f"Retention: 24h={ret.get('retention_24h_pct', '?')}%  7d={ret.get('retention_7d_pct', '?')}%  30d={ret.get('retention_30d_pct', '?')}%")
    lines.append(f"  Active: 24h={ret.get('active_24h', '?')}  7d={ret.get('active_7d', '?')}  30d={ret.get('active_30d', '?')}  total={ret.get('total_registered_keys', '?')}")
    lines.append("")

    eps = metrics.get("top_endpoints", [])
    if eps:
        lines.append("Top Endpoints (24h):")
        for ep in eps[:10]:
            lines.append(f"  {ep['hits']:>5}  {ep.get('avg_latency_ms', '?'):>7}ms  {ep['endpoint']}")
        lines.append("")

    refs = metrics.get("referrers", [])
    if refs:
        lines.append("Top Referrers (24h):")
        for r in refs[:10]:
            lines.append(f"  {r['hits']:>5} hits  {r['unique_keys']} keys  {r['referrer']}")
        lines.append("")

    funnel = metrics.get("funnel", {})
    if funnel:
        lines.append(f"Funnel (7d): {funnel.get('registered', 0)} registered -> {funnel.get('made_api_call', 0)} activated ({funnel.get('activation_rate_pct', 0)}%) -> {funnel.get('engaged_10plus_calls', 0)} engaged ({funnel.get('engagement_rate_pct', 0)}%)")
        sources = funnel.get("top_sources", [])
        if sources:
            lines.append("  Sources: " + ", ".join(f"{s['source']}({s['count']})" for s in sources))
        lines.append("")

    errs = metrics.get("errors", {})
    by_status = errs.get("by_status", [])
    if by_status:
        lines.append("Errors (24h):")
        for e in by_status:
            lines.append(f"  HTTP {e['status']}: {e['count']}")
        lines.append("")

    return "\n".join(lines)


def format_html(metrics: dict) -> str:
    """Format metrics as HTML email body."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    text = format_text(metrics)
    # Wrap in a preformatted dark-theme email body
    return f"""
<div style="font-family: 'Courier New', monospace; max-width: 700px; margin: 0 auto;
            background: #0d1117; color: #c9d1d9; padding: 24px; border-radius: 8px;">
  <h2 style="color: #f7931a; margin-top: 0;">Satoshi API Daily Digest</h2>
  <p style="color: #8b949e; font-size: 12px;">{now}</p>
  <pre style="white-space: pre-wrap; font-size: 13px; line-height: 1.5;">{text}</pre>
  <hr style="border: 1px solid #30363d;">
  <p style="font-size: 11px; color: #8b949e;">
    <a href="{API_BASE}" style="color: #f7931a;">bitcoinsapi.com</a> |
    <a href="{API_BASE}/admin/dashboard" style="color: #f7931a;">Admin Dashboard</a>
  </p>
</div>
"""


def send_email(html_body: str, to: str) -> bool:
    """Send digest email via Resend."""
    resend_key = os.getenv("RESEND_API_KEY", "")
    if not resend_key:
        # Try .env
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.strip().startswith("RESEND_API_KEY="):
                    resend_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not resend_key:
        print("ERROR: No RESEND_API_KEY found. Cannot send email.", file=sys.stderr)
        return False

    payload = json.dumps({
        "from": "Satoshi API <noreply@bitcoinsapi.com>",
        "to": [to],
        "subject": f"Satoshi API Digest — {datetime.now(timezone.utc).strftime('%b %d')}",
        "html": html_body,
    }).encode()

    req = Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {resend_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            print(f"Email sent: {result.get('id', 'ok')}")
            return True
    except Exception as e:
        print(f"ERROR sending email: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Satoshi API daily analytics digest")
    parser.add_argument("--email", action="store_true", help="Send digest via email")
    parser.add_argument("--to", default=DEFAULT_TO, help="Email recipient")
    args = parser.parse_args()

    _load_env()
    if not ADMIN_KEY:
        print("ERROR: Set SATOSHI_ADMIN_KEY or ADMIN_API_KEY env var, or add ADMIN_API_KEY to .env", file=sys.stderr)
        sys.exit(1)

    print("Gathering metrics...", file=sys.stderr)
    metrics = gather_metrics()

    if args.email:
        html = format_html(metrics)
        ok = send_email(html, args.to)
        if not ok:
            # Fallback: print to stdout
            print(format_text(metrics))
            sys.exit(1)
    else:
        print(format_text(metrics))


if __name__ == "__main__":
    main()
