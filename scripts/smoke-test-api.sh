#!/usr/bin/env bash
# Smoke test for Satoshi API (bitcoinsapi.com)
#
# Cron setup (on GMKtec):
# */15 * * * * wsl -e bash -c "/path/to/smoke-test-api.sh --quiet >> /var/log/satoshi-smoke.log 2>&1 || echo 'SATOSHI API SMOKE FAIL at $(date)' >> /var/log/satoshi-alerts.log"

set -uo pipefail

BASE_URL="${BASE_URL:-https://bitcoinsapi.com}"
TIMEOUT="${TIMEOUT:-10}"
QUIET=false
PASS_COUNT=0
FAIL_COUNT=0

[[ "${1:-}" == "--quiet" ]] && QUIET=true

check() {
    local name="$1"
    local url="$2"
    local pattern="${3:-}"
    local case_insensitive="${4:-false}"
    local expected="${5:-200}"

    local http_code body
    body=$(curl -s --max-time "$TIMEOUT" -H 'User-Agent: Mozilla/5.0' -w '\n%{http_code}' "$url" 2>/dev/null) || {
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "FAIL  $name - curl error (timeout or connection refused)"
        return
    }

    http_code=$(echo "$body" | tail -1)
    body=$(echo "$body" | sed '$d')

    if [[ "$http_code" != "$expected" ]]; then
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "FAIL  $name - HTTP $http_code (expected $expected)"
        return
    fi

    if [[ -n "$pattern" ]]; then
        local grep_flags="-q"
        [[ "$case_insensitive" == "true" ]] && grep_flags="-qi"

        if ! echo "$body" | grep $grep_flags "$pattern"; then
            FAIL_COUNT=$((FAIL_COUNT + 1))
            echo "FAIL  $name - response missing pattern: $pattern"
            return
        fi
    fi

    PASS_COUNT=$((PASS_COUNT + 1))
    [[ "$QUIET" == "false" ]] && echo "PASS  $name"
}

check "home"         "$BASE_URL/"
check "fees-page"    "$BASE_URL/fees"                             "Fee Tracker"                             true
check "llms"         "$BASE_URL/llms.txt"                         "Bitcoin fee intelligence for AI agents" true
check "x402-page"    "$BASE_URL/x402"                             "premium Bitcoin API calls"               true
check "docs"         "$BASE_URL/docs"                             "swagger"                                 true
check "redoc"        "$BASE_URL/redoc"
check "openapi"      "$BASE_URL/openapi.json"                     '"openapi"'
check "server-card"  "$BASE_URL/.well-known/mcp/server-card.json" '"serverInfo"'
check "health"       "$BASE_URL/api/v1/health"                    '"status":"ok"'
check "fees"         "$BASE_URL/api/v1/fees/recommended"          '"recommendation"'
check "mempool"      "$BASE_URL/api/v1/mempool"                   '"congestion"'
check "difficulty"   "$BASE_URL/api/v1/network/difficulty"        '"progress_percent"'
check "analytics"    "$BASE_URL/api/v1/analytics/public"          '"total_keys"'
check "x402-demo"    "$BASE_URL/api/v1/x402-demo"                 '"Payment Required"' false 402
check "x402-info"    "$BASE_URL/api/v1/x402-info"                 '"x402"'

TOTAL=$((PASS_COUNT + FAIL_COUNT))
if [[ "$QUIET" == "false" ]] || [[ "$FAIL_COUNT" -gt 0 ]]; then
    echo "--- $(date -u '+%Y-%m-%d %H:%M:%S UTC') | $PASS_COUNT/$TOTAL passed"
fi

[[ "$FAIL_COUNT" -eq 0 ]] && exit 0 || exit 1
