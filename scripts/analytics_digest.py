#!/usr/bin/env python3
"""Daily analytics digest — queries Satoshi API admin endpoints and emails a summary.

Usage:
    python scripts/analytics_digest.py                    # Print to stdout
    python scripts/analytics_digest.py --email            # Send via Resend
    python scripts/analytics_digest.py --email --to X     # Override recipient

Designed to run as a daily cron job on Main PC (Windows Scheduled Task).
Requires: ADMIN_API_KEY in .env or SATOSHI_ADMIN_KEY env var.
"""

import argparse
import html as html_lib
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

# Known bot/scanner patterns in endpoints — not real API usage
BOT_ENDPOINTS = {
    "/wordpress/", "/wp-admin/", "/wp-login", "/.env", "/xmlrpc",
    "/actuator", "/config.", "/admin/", "/phpmyadmin",
}


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


def _fmt_pct(val):
    """Format a percentage value, handling None and edge cases."""
    if val is None:
        return "n/a"
    return f"{val:+.1f}%" if val != 0 else "0%"


def _fmt_num(val):
    """Format a number with comma separators."""
    if val is None or val == "?":
        return "?"
    return f"{val:,}" if isinstance(val, (int, float)) else str(val)


def _is_bot_endpoint(endpoint: str) -> bool:
    """Check if an endpoint is a known bot/scanner target."""
    ep_lower = endpoint.lower()
    return any(pat in ep_lower for pat in BOT_ENDPOINTS)


def gather_metrics() -> dict:
    """Fetch all analytics endpoints and assemble a digest."""
    metrics = {}

    for key, path in [
        ("overview", "/analytics/overview"),
        ("growth", "/analytics/growth"),
        ("top_endpoints", "/analytics/endpoints?period=24h&limit=20"),
        ("errors", "/analytics/errors?period=24h"),
        ("client_types", "/analytics/client-types?period=24h"),
        ("latency", "/analytics/latency?period=24h"),
        ("retention", "/analytics/retention"),
        ("referrers", "/analytics/referrers?period=24h&limit=10"),
        ("funnel", "/analytics/funnel?period=7d"),
    ]:
        data = _api(path)
        if data and "data" in data:
            metrics[key] = data["data"]

    return metrics


def _analyze(metrics: dict) -> dict:
    """Derive insights from raw metrics."""
    insights = {}
    ov = metrics.get("overview", {})
    gr = metrics.get("growth", {})
    eps = metrics.get("top_endpoints", [])
    errs = metrics.get("errors", {})

    # Separate bot vs real endpoints
    real_endpoints = [e for e in eps if not _is_bot_endpoint(e["endpoint"])]
    bot_endpoints = [e for e in eps if _is_bot_endpoint(e["endpoint"])]
    bot_hits = sum(e["hits"] for e in bot_endpoints)
    total_hits = sum(e["hits"] for e in eps)
    insights["real_endpoints"] = real_endpoints[:10]
    insights["bot_hits"] = bot_hits
    insights["bot_pct"] = round(bot_hits / total_hits * 100, 1) if total_hits > 0 else 0

    # Categorize errors by severity
    by_status = errs.get("by_status", [])
    err_404 = sum(e["count"] for e in by_status if e["status"] == 404)
    err_405 = sum(e["count"] for e in by_status if e["status"] == 405)  # Bots sending wrong method
    err_429 = sum(e["count"] for e in by_status if e["status"] == 429)  # Rate limiting = working
    err_noise = err_404 + err_405 + err_429  # Not real problems
    err_server = sum(e["count"] for e in by_status if e["status"] >= 500)  # Actual problems
    err_client = sum(e["count"] for e in by_status if 400 <= e["status"] < 500) - err_noise
    insights["errors_404"] = err_404
    insights["errors_noise"] = err_noise
    insights["errors_server"] = err_server
    insights["errors_client"] = max(0, err_client)
    insights["errors_real"] = err_server + max(0, err_client)

    # Real error rate = only server errors + legitimate client errors (not bots, not rate limits)
    req_24h = ov.get("requests_24h", 0)
    insights["real_error_rate"] = round(insights["errors_real"] / req_24h * 100, 1) if req_24h > 0 else 0
    insights["server_error_rate"] = round(err_server / req_24h * 100, 1) if req_24h > 0 else 0

    # Health status — based on server errors only (5xx), not bot noise
    lat_p95 = metrics.get("latency", {}).get("p95")
    if req_24h == 0:
        insights["health"] = "DOWN"
        insights["health_note"] = "No requests in 24h"
    elif err_server > 0 and insights["server_error_rate"] > 5:
        insights["health"] = "DEGRADED"
        insights["health_note"] = f"{err_server} server errors ({insights['server_error_rate']}%)"
    elif lat_p95 and lat_p95 > 1000:
        insights["health"] = "SLOW"
        insights["health_note"] = f"p95 latency {lat_p95}ms"
    else:
        insights["health"] = "HEALTHY"
        insights["health_note"] = f"{_fmt_num(req_24h)} req/24h, p95 {lat_p95 or '?'}ms"

    return insights


def format_text(metrics: dict) -> str:
    """Format metrics as plain-text digest."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    insights = _analyze(metrics)
    ov = metrics.get("overview", {})
    gr = metrics.get("growth", {})
    lat = metrics.get("latency", {})
    ret = metrics.get("retention", {})
    ct = metrics.get("client_types", {})
    funnel = metrics.get("funnel", {})
    refs = metrics.get("referrers", [])
    errs = metrics.get("errors", {})

    lines = []
    lines.append(f"SATOSHI API DIGEST -- {now}")
    lines.append(f"Status: {insights['health']} -- {insights['health_note']}")
    lines.append("")

    # --- Traffic ---
    lines.append("TRAFFIC")
    lines.append(f"  Requests:  24h {_fmt_num(ov.get('requests_24h'))}  |  7d {_fmt_num(ov.get('requests_7d'))}  |  30d {_fmt_num(ov.get('requests_30d'))}")
    dod = gr.get("requests_dod_pct")
    wow = gr.get("requests_wow_pct")
    lines.append(f"  Growth:    day-over-day {_fmt_pct(dod)}  |  week-over-week {_fmt_pct(wow)}")
    lines.append(f"  Bot noise: {_fmt_num(insights['bot_hits'])} hits ({insights['bot_pct']}% of top endpoints)")
    lines.append("")

    # --- Performance ---
    lines.append("PERFORMANCE")
    avg = ov.get("avg_latency_ms_24h")
    lines.append(f"  Avg: {round(avg, 1) if avg else '?'}ms  |  p50: {lat.get('p50', '?')}ms  |  p95: {lat.get('p95', '?')}ms  |  p99: {lat.get('p99', '?')}ms")
    lines.append("")

    # --- Users ---
    lines.append("USERS")
    total_keys = ret.get("total_registered_keys", 0)
    lines.append(f"  Registered API keys: {_fmt_num(total_keys)}")
    # Note: "active" from retention endpoint counts unique key_hashes in usage_log,
    # which includes anonymous (null hash) traffic. Only meaningful when > total_keys.
    active_7d = ret.get("active_7d", 0)
    if active_7d > total_keys:
        lines.append(f"  Authenticated key activity (7d): {_fmt_num(active_7d)} unique hashes (includes anonymous)")
    else:
        lines.append(f"  Active keys (7d): {_fmt_num(active_7d)} of {_fmt_num(total_keys)} registered")
    lines.append("")

    # --- Funnel ---
    if funnel:
        reg = funnel.get("registered", 0)
        act = funnel.get("made_api_call", 0)
        eng = funnel.get("engaged_10plus_calls", 0)
        lines.append("CONVERSION FUNNEL (7d)")
        lines.append(f"  Registered:    {reg}")
        lines.append(f"  -> Activated:  {act} ({funnel.get('activation_rate_pct', 0)}% made at least 1 API call)")
        lines.append(f"  -> Engaged:    {eng} ({funnel.get('engagement_rate_pct', 0)}% made 10+ calls)")
        sources = funnel.get("top_sources", [])
        if sources:
            lines.append(f"  Sources:       {', '.join(s['source'] + '(' + str(s['count']) + ')' for s in sources)}")
        lines.append("")

    # --- Client Types ---
    if ct.get("breakdown"):
        lines.append("CLIENT TYPES (24h)")
        for b in ct["breakdown"]:
            bar = "#" * max(1, int(b["pct"] / 5))
            lines.append(f"  {b['client_type']:<12} {b['count']:>5}  {b['pct']:>5.1f}%  {bar}")
        lines.append("")

    # --- Top Real Endpoints ---
    real_eps = insights.get("real_endpoints", [])
    if real_eps:
        lines.append("TOP ENDPOINTS (24h, excluding bots)")
        for ep in real_eps[:8]:
            avg_ms = ep.get("avg_latency_ms")
            avg_str = f"{avg_ms:>6.0f}ms" if avg_ms else "    ?ms"
            lines.append(f"  {ep['hits']:>5} hits  {avg_str}  {ep['endpoint']}")
        lines.append("")

    # --- Referrers ---
    # Filter out self-referrals
    ext_refs = [r for r in refs if "bitcoinsapi.com" not in r.get("referrer", "")]
    if ext_refs:
        lines.append("EXTERNAL REFERRERS (24h)")
        for r in ext_refs[:5]:
            lines.append(f"  {r['hits']:>5} hits  {r['unique_keys']} keys  {r['referrer']}")
        lines.append("")

    # --- Errors ---
    lines.append("ERRORS (24h)")
    lines.append(f"  Server errors (5xx):   {_fmt_num(insights['errors_server'])} ({insights['server_error_rate']}% of requests)")
    lines.append(f"  Client errors (real):  {_fmt_num(insights['errors_client'])}")
    lines.append(f"  Noise (bots+limits):   {_fmt_num(insights['errors_noise'])} (404={insights['errors_404']}, 405/429=expected)")
    by_status = errs.get("by_status", [])
    for e in by_status:
        label = {404: "Not Found (bot probes)", 405: "Method Not Allowed (bots)",
                 429: "Rate Limited (working as intended)",
                 502: "Bad Gateway (node down)", 503: "Service Unavailable (circuit breaker)",
                 422: "Validation Error", 403: "Forbidden"}.get(e["status"], f"HTTP {e['status']}")
        marker = " **" if e["status"] >= 500 else ""
        lines.append(f"    {e['count']:>4}  {label}{marker}")
    lines.append("")

    return "\n".join(lines)


def format_html(metrics: dict) -> str:
    """Format metrics as a proper HTML email."""
    now = datetime.now(timezone.utc).strftime("%A, %B %d %Y at %H:%M UTC")
    insights = _analyze(metrics)
    ov = metrics.get("overview", {})
    gr = metrics.get("growth", {})
    lat = metrics.get("latency", {})
    ret = metrics.get("retention", {})
    ct = metrics.get("client_types", {})
    funnel = metrics.get("funnel", {})
    refs = metrics.get("referrers", [])
    errs = metrics.get("errors", {})

    # Health badge color
    health_colors = {"HEALTHY": "#3fb950", "DEGRADED": "#d29922", "SLOW": "#d29922", "DOWN": "#f85149"}
    health_color = health_colors.get(insights["health"], "#8b949e")

    # Build HTML sections
    sections = []

    # --- Hero / Health ---
    sections.append(f"""
    <div style="background: {health_color}20; border-left: 4px solid {health_color}; padding: 12px 16px; border-radius: 4px; margin-bottom: 20px;">
      <span style="color: {health_color}; font-weight: 700; font-size: 16px;">{insights['health']}</span>
      <span style="color: #8b949e; margin-left: 8px;">{html_lib.escape(insights['health_note'])}</span>
    </div>""")

    # --- Traffic KPIs ---
    dod = gr.get("requests_dod_pct")
    wow = gr.get("requests_wow_pct")
    sections.append(f"""
    <h3 style="color: #f7931a; margin: 20px 0 8px;">Traffic</h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
      <tr>
        <td style="padding: 6px 12px; border: 1px solid #30363d; color: #8b949e;">24h</td>
        <td style="padding: 6px 12px; border: 1px solid #30363d; font-weight: 600;">{_fmt_num(ov.get('requests_24h'))}</td>
        <td style="padding: 6px 12px; border: 1px solid #30363d; color: #8b949e;">7d</td>
        <td style="padding: 6px 12px; border: 1px solid #30363d; font-weight: 600;">{_fmt_num(ov.get('requests_7d'))}</td>
        <td style="padding: 6px 12px; border: 1px solid #30363d; color: #8b949e;">30d</td>
        <td style="padding: 6px 12px; border: 1px solid #30363d; font-weight: 600;">{_fmt_num(ov.get('requests_30d'))}</td>
      </tr>
      <tr>
        <td style="padding: 6px 12px; border: 1px solid #30363d; color: #8b949e;">DoD</td>
        <td style="padding: 6px 12px; border: 1px solid #30363d;">{_fmt_pct(dod)}</td>
        <td style="padding: 6px 12px; border: 1px solid #30363d; color: #8b949e;">WoW</td>
        <td style="padding: 6px 12px; border: 1px solid #30363d;">{_fmt_pct(wow)}</td>
        <td style="padding: 6px 12px; border: 1px solid #30363d; color: #8b949e;">Bot noise</td>
        <td style="padding: 6px 12px; border: 1px solid #30363d;">{insights['bot_pct']}%</td>
      </tr>
    </table>""")

    # --- Performance ---
    avg = ov.get("avg_latency_ms_24h")
    sections.append(f"""
    <h3 style="color: #f7931a; margin: 20px 0 8px;">Performance</h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
      <tr>
        <td style="padding: 6px 12px; border: 1px solid #30363d; color: #8b949e;">Avg</td>
        <td style="padding: 6px 12px; border: 1px solid #30363d;">{round(avg, 1) if avg else '?'}ms</td>
        <td style="padding: 6px 12px; border: 1px solid #30363d; color: #8b949e;">p50</td>
        <td style="padding: 6px 12px; border: 1px solid #30363d;">{lat.get('p50', '?')}ms</td>
        <td style="padding: 6px 12px; border: 1px solid #30363d; color: #8b949e;">p95</td>
        <td style="padding: 6px 12px; border: 1px solid #30363d;">{lat.get('p95', '?')}ms</td>
        <td style="padding: 6px 12px; border: 1px solid #30363d; color: #8b949e;">p99</td>
        <td style="padding: 6px 12px; border: 1px solid #30363d;">{lat.get('p99', '?')}ms</td>
      </tr>
    </table>""")

    # --- Funnel ---
    if funnel:
        reg = funnel.get("registered", 0)
        act = funnel.get("made_api_call", 0)
        eng = funnel.get("engaged_10plus_calls", 0)
        act_pct = funnel.get("activation_rate_pct", 0)
        eng_pct = funnel.get("engagement_rate_pct", 0)
        # Bar widths (proportional)
        reg_w = 100
        act_w = max(5, int(act_pct)) if reg > 0 else 0
        eng_w = max(5, int(eng_pct)) if reg > 0 else 0
        sections.append(f"""
    <h3 style="color: #f7931a; margin: 20px 0 8px;">Conversion Funnel (7d)</h3>
    <div style="font-size: 14px;">
      <div style="margin-bottom: 6px;">
        <div style="background: #f7931a; height: 24px; width: {reg_w}%; border-radius: 3px; display: flex; align-items: center; padding-left: 8px; font-weight: 600; color: #0d1117;">{reg} registered</div>
      </div>
      <div style="margin-bottom: 6px;">
        <div style="background: #3fb950; height: 24px; width: {act_w}%; border-radius: 3px; display: flex; align-items: center; padding-left: 8px; font-weight: 600; color: #0d1117;">{act} activated ({act_pct}%)</div>
      </div>
      <div>
        <div style="background: #58a6ff; height: 24px; width: {eng_w}%; min-width: 40px; border-radius: 3px; display: flex; align-items: center; padding-left: 8px; font-weight: 600; color: #0d1117;">{eng} engaged ({eng_pct}%)</div>
      </div>
    </div>""")

    # --- Top Endpoints ---
    real_eps = insights.get("real_endpoints", [])
    if real_eps:
        rows = ""
        for ep in real_eps[:8]:
            avg_ms = ep.get("avg_latency_ms")
            avg_str = f"{avg_ms:.0f}ms" if avg_ms else "?"
            rows += f"""
        <tr>
          <td style="padding: 4px 8px; border: 1px solid #30363d; text-align: right;">{ep['hits']}</td>
          <td style="padding: 4px 8px; border: 1px solid #30363d; text-align: right;">{avg_str}</td>
          <td style="padding: 4px 8px; border: 1px solid #30363d; font-family: monospace; font-size: 12px;">{html_lib.escape(ep['endpoint'])}</td>
        </tr>"""
        sections.append(f"""
    <h3 style="color: #f7931a; margin: 20px 0 8px;">Top Endpoints (24h, bots filtered)</h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
      <tr style="color: #8b949e;">
        <th style="padding: 4px 8px; border: 1px solid #30363d; text-align: right;">Hits</th>
        <th style="padding: 4px 8px; border: 1px solid #30363d; text-align: right;">Avg</th>
        <th style="padding: 4px 8px; border: 1px solid #30363d; text-align: left;">Endpoint</th>
      </tr>{rows}
    </table>""")

    # --- External Referrers ---
    ext_refs = [r for r in refs if "bitcoinsapi.com" not in r.get("referrer", "")]
    if ext_refs:
        ref_rows = ""
        for r in ext_refs[:5]:
            ref_rows += f"""
        <tr>
          <td style="padding: 4px 8px; border: 1px solid #30363d; text-align: right;">{r['hits']}</td>
          <td style="padding: 4px 8px; border: 1px solid #30363d; text-align: right;">{r['unique_keys']}</td>
          <td style="padding: 4px 8px; border: 1px solid #30363d; font-size: 12px;">{html_lib.escape(r['referrer'])}</td>
        </tr>"""
        sections.append(f"""
    <h3 style="color: #f7931a; margin: 20px 0 8px;">External Referrers (24h)</h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
      <tr style="color: #8b949e;">
        <th style="padding: 4px 8px; border: 1px solid #30363d; text-align: right;">Hits</th>
        <th style="padding: 4px 8px; border: 1px solid #30363d; text-align: right;">Keys</th>
        <th style="padding: 4px 8px; border: 1px solid #30363d; text-align: left;">Referrer</th>
      </tr>{ref_rows}
    </table>""")

    # --- Errors ---
    by_status = errs.get("by_status", [])
    non_404 = [e for e in by_status if e["status"] != 404]
    error_detail = ""
    if non_404:
        for e in non_404:
            label = {405: "Method Not Allowed (bots)", 429: "Rate Limited (working as intended)",
                     502: "Bad Gateway (node down)", 503: "Service Unavailable (circuit breaker)",
                     422: "Validation Error", 403: "Forbidden"}.get(e["status"], f"HTTP {e['status']}")
            color = "#f85149" if e["status"] in (502, 503) else "#8b949e"
            error_detail += f'<div style="margin: 2px 0;"><span style="color: {color};">{e["count"]}</span> {label}</div>'

    sections.append(f"""
    <h3 style="color: #f7931a; margin: 20px 0 8px;">Errors (24h)</h3>
    <div style="font-size: 13px;">
      <div>Server errors (5xx): <strong style="color: {'#f85149' if insights['errors_server'] > 0 else '#3fb950'};">{_fmt_num(insights['errors_server'])}</strong> ({insights['server_error_rate']}%)</div>
      <div>Client errors (real): {_fmt_num(insights['errors_client'])}</div>
      <div style="color: #8b949e;">Noise (bots + rate limits): {_fmt_num(insights['errors_noise'])}</div>
      {error_detail}
    </div>""")

    # --- Assemble ---
    body = "\n".join(sections)
    return f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 700px; margin: 0 auto; background: #0d1117; color: #c9d1d9;
            padding: 28px; border-radius: 8px;">
  <div style="display: flex; align-items: center; margin-bottom: 16px;">
    <h1 style="color: #f7931a; font-size: 22px; margin: 0; flex: 1;">Satoshi API Daily Digest</h1>
  </div>
  <p style="color: #8b949e; font-size: 12px; margin: 0 0 20px;">{now}</p>
  {body}
  <hr style="border: 1px solid #30363d; margin: 24px 0 16px;">
  <p style="font-size: 11px; color: #8b949e;">
    <a href="{API_BASE}" style="color: #f7931a;">bitcoinsapi.com</a> |
    <a href="{API_BASE}/docs" style="color: #f7931a;">API Docs</a> |
    <a href="https://github.com/Bortlesboat/bitcoin-api" style="color: #f7931a;">GitHub</a>
  </p>
</div>
"""


def send_email(html_body: str, to: str) -> bool:
    """Send digest email via Resend."""
    resend_key = os.getenv("RESEND_API_KEY", "")
    if not resend_key:
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.strip().startswith("RESEND_API_KEY="):
                    resend_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not resend_key:
        print("ERROR: No RESEND_API_KEY found. Cannot send email.", file=sys.stderr)
        return False

    now = datetime.now(timezone.utc)
    payload = json.dumps({
        "from": "Satoshi API <noreply@bitcoinsapi.com>",
        "to": [to],
        "subject": f"Satoshi API Digest -- {now.strftime('%b %d')}",
        "html": html_body,
    }).encode()

    req = Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {resend_key}",
            "Content-Type": "application/json",
            "User-Agent": "SatoshiDigest/1.0",
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
            print(format_text(metrics))
            sys.exit(1)
    else:
        print(format_text(metrics))


if __name__ == "__main__":
    main()
