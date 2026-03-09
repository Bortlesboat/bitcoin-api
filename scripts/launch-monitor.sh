#!/usr/bin/env bash
# =============================================================================
# Satoshi API — Launch Day Monitor
# Usage: bash scripts/launch-monitor.sh
# Auto-refresh: watch -n 60 bash scripts/launch-monitor.sh
# =============================================================================

set -uo pipefail

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

API_URL="https://bitcoinsapi.com"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_PATH="$(cd "$SCRIPT_DIR/.." && pwd)/data/bitcoin_api.db"

# --- Header ---
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${CYAN}║         SATOSHI API — LAUNCH DAY MONITOR             ║${RESET}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════╝${RESET}"
echo -e "${DIM}  $(date '+%Y-%m-%d %H:%M:%S %Z')${RESET}"
echo ""

# =============================================================================
# 1. API Health
# =============================================================================
echo -e "${BOLD}━━━ 1. API HEALTH ━━━${RESET}"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" --max-time 10 "${API_URL}/api/v1/health" 2>/dev/null) || HEALTH_RESPONSE=$'\n000'
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -1)
BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "  Status: ${GREEN}● HEALTHY${RESET} (HTTP $HTTP_CODE)"
    echo "$BODY" | python -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
    data = d.get('data', d)
    if isinstance(data, dict):
        for k in ['version', 'uptime', 'node_connected']:
            if k in data:
                print(f'  {k}: {data[k]}')
except: pass
" 2>/dev/null || true
else
    echo -e "  Status: ${RED}● DOWN${RESET} (HTTP $HTTP_CODE)"
    if [ -n "$BODY" ]; then
        echo -e "  Response: ${DIM}${BODY:0:200}${RESET}"
    fi
fi
echo ""

# =============================================================================
# 2. API Key Count
# =============================================================================
echo -e "${BOLD}━━━ 2. API KEYS ━━━${RESET}"
if [ -f "$DB_PATH" ]; then
    python - "$DB_PATH" <<'PYEOF'
import sqlite3, sys
db = sys.argv[1]
try:
    conn = sqlite3.connect(db)
    total = conn.execute('SELECT COUNT(*) FROM api_keys').fetchone()[0]
    active = conn.execute('SELECT COUNT(*) FROM api_keys WHERE active = 1').fetchone()[0]
    tiers = conn.execute('SELECT tier, COUNT(*) FROM api_keys GROUP BY tier ORDER BY COUNT(*) DESC').fetchall()
    print(f'  Total keys:  {total}')
    print(f'  Active keys: {active}')
    tier_str = ', '.join(f'{t}: {c}' for t, c in tiers)
    print(f'  By tier:     {tier_str}')
    conn.close()
except Exception as e:
    print(f'  Error querying DB: {e}', file=sys.stderr)
PYEOF
else
    echo -e "  ${YELLOW}⚠ DB not found at ${DB_PATH}${RESET}"
    echo "  Trying admin endpoint..."
    curl -s --max-time 10 "${API_URL}/api/v1/admin/analytics" 2>/dev/null | head -c 300 || echo "  (unreachable)"
fi
echo ""

# =============================================================================
# 3. Recent Registrations (last 24h)
# =============================================================================
echo -e "${BOLD}━━━ 3. REGISTRATIONS (Last 24h) ━━━${RESET}"
if [ -f "$DB_PATH" ]; then
    python - "$DB_PATH" <<'PYEOF'
import sqlite3, sys
db = sys.argv[1]
conn = sqlite3.connect(db)
rows = conn.execute('''
    SELECT created_at, email, label, utm_source, tier
    FROM api_keys
    WHERE created_at >= datetime('now', '-24 hours')
    ORDER BY created_at DESC
''').fetchall()
if not rows:
    print('  (none)')
else:
    print(f'  {len(rows)} new registration(s):')
    print()
    for r in rows:
        ts, email, label, utm, tier = r
        email_display = email or '(no email)'
        label_display = label or '(no label)'
        utm_display = utm if utm else '-'
        print(f'  {ts}  {email_display:<30} {label_display:<20} utm={utm_display}  [{tier}]')
conn.close()
PYEOF
else
    echo -e "  ${YELLOW}⚠ DB not found${RESET}"
fi
echo ""

# =============================================================================
# 4. Hacker News Check
# =============================================================================
echo -e "${BOLD}━━━ 4. HACKER NEWS ━━━${RESET}"
HN_RESP=$(curl -s --max-time 10 "https://hn.algolia.com/api/v1/search?query=satoshi+api&tags=show_hn" 2>/dev/null) || HN_RESP=""
if [ -n "$HN_RESP" ]; then
    echo "$HN_RESP" | python -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
    hits = d.get('hits', [])
    relevant = [h for h in hits if 'satoshi' in h.get('title','').lower() or 'bitcoinsapi' in h.get('url','').lower()]
    if relevant:
        for h in relevant[:3]:
            title = h.get('title', '?')
            points = h.get('points', 0)
            comments = h.get('num_comments', 0)
            oid = h.get('objectID', '')
            print(f'  \033[0;32m● FOUND:\033[0m {title}')
            print(f'    Points: {points}  Comments: {comments}')
            print(f'    https://news.ycombinator.com/item?id={oid}')
    else:
        print('  (no Show HN post found yet)')
except Exception as e:
    print(f'  Error: {e}', file=sys.stderr)
" 2>/dev/null || echo -e "  ${YELLOW}⚠ Parse error${RESET}"
else
    echo -e "  ${YELLOW}⚠ Could not reach HN API${RESET}"
fi

# Broader HN search
HN_BROAD=$(curl -s --max-time 10 "https://hn.algolia.com/api/v1/search?query=bitcoinsapi" 2>/dev/null) || HN_BROAD=""
if [ -n "$HN_BROAD" ]; then
    echo "$HN_BROAD" | python -c "
import json, sys
d = json.loads(sys.stdin.read())
hits = d.get('hits', [])
mentions = [h for h in hits if 'bitcoinsapi' in json.dumps(h).lower() or 'satoshi api' in h.get('title','').lower()]
if mentions:
    print(f'  + {len(mentions)} mention(s) across all HN')
" 2>/dev/null || true
fi
echo ""

# =============================================================================
# 5. Reddit Inbox
# =============================================================================
echo -e "${BOLD}━━━ 5. REDDIT ━━━${RESET}"
echo -e "  ${YELLOW}→ Check manually:${RESET} https://www.reddit.com/message/inbox/"
echo -e "  ${YELLOW}→ Search:${RESET} https://www.reddit.com/search/?q=bitcoinsapi"
echo -e "  ${DIM}  (OAuth required — cannot automate from CLI)${RESET}"
echo ""

# =============================================================================
# 6. Today's Request Count
# =============================================================================
echo -e "${BOLD}━━━ 6. TODAY'S TRAFFIC ━━━${RESET}"
if [ -f "$DB_PATH" ]; then
    python - "$DB_PATH" <<'PYEOF'
import sqlite3, sys
db = sys.argv[1]
conn = sqlite3.connect(db)

today_total = conn.execute(
    "SELECT COUNT(*) FROM usage_log WHERE ts >= date('now')"
).fetchone()[0]

by_status = conn.execute(
    "SELECT status, COUNT(*) FROM usage_log WHERE ts >= date('now') GROUP BY status ORDER BY COUNT(*) DESC"
).fetchall()

unique_ips = conn.execute(
    "SELECT COUNT(DISTINCT client_ip) FROM usage_log WHERE ts >= date('now') AND client_ip != ''"
).fetchone()[0]

top_endpoints = conn.execute(
    "SELECT endpoint, COUNT(*) FROM usage_log WHERE ts >= date('now') GROUP BY endpoint ORDER BY COUNT(*) DESC LIMIT 5"
).fetchall()

unique_keys = conn.execute(
    "SELECT COUNT(DISTINCT key_hash) FROM usage_log WHERE ts >= date('now') AND key_hash IS NOT NULL AND key_hash != ''"
).fetchone()[0]

errors = conn.execute(
    "SELECT COUNT(*) FROM usage_log WHERE ts >= date('now') AND status >= 400"
).fetchone()[0]

print(f'  Total requests today: {today_total}')
print(f'  Unique IPs:           {unique_ips}')
print(f'  Unique API keys:      {unique_keys}')
print(f'  Errors (4xx/5xx):     {errors}')
print()
if by_status:
    status_str = ', '.join(f'{s}: {c}' for s, c in by_status[:6])
    print(f'  By status: {status_str}')
if top_endpoints:
    print('  Top endpoints:')
    for ep, cnt in top_endpoints:
        print(f'    {cnt:>5}x  {ep}')

conn.close()
PYEOF
else
    echo -e "  ${YELLOW}⚠ DB not found${RESET}"
fi
echo ""

# =============================================================================
# Footer
# =============================================================================
echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${DIM}  Auto-refresh: watch -n 60 bash scripts/launch-monitor.sh${RESET}"
echo -e "${DIM}  DB: ${DB_PATH}${RESET}"
echo ""
