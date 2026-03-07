#!/usr/bin/env bash
# Smoke test for Satoshi API (bitcoinsapi.com)
#
# Cron setup (on GMKtec):
# */15 * * * * wsl -e bash -c "/path/to/smoke-test-api.sh --quiet >> /var/log/satoshi-smoke.log 2>&1 || echo 'SATOSHI API SMOKE FAIL at $(date)' >> /var/log/satoshi-alerts.log"

set -uo pipefail

BASE_URL="https://bitcoinsapi.com"
TIMEOUT=10
QUIET=false
PASS_COUNT=0
FAIL_COUNT=0
TOTAL=5

[[ "${1:-}" == "--quiet" ]] && QUIET=true

check() {
    local name="$1"
    local url="$2"
    local pattern="${3:-}"
    local case_insensitive="${4:-false}"

    local http_code body
    body=$(curl -s --max-time "$TIMEOUT" -w '\n%{http_code}' "$url" 2>/dev/null) || {
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "FAIL  $name — curl error (timeout or connection refused)"
        return
    }

    http_code=$(echo "$body" | tail -1)
    body=$(echo "$body" | sed '$d')

    if [[ "$http_code" != "200" ]]; then
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "FAIL  $name — HTTP $http_code (expected 200)"
        return
    fi

    if [[ -n "$pattern" ]]; then
        local grep_flags="-q"
        [[ "$case_insensitive" == "true" ]] && grep_flags="-qi"

        if ! echo "$body" | grep $grep_flags "$pattern"; then
            FAIL_COUNT=$((FAIL_COUNT + 1))
            echo "FAIL  $name — response missing pattern: $pattern"
            return
        fi
    fi

    PASS_COUNT=$((PASS_COUNT + 1))
    [[ "$QUIET" == "false" ]] && echo "PASS  $name"
}

check "health"         "$BASE_URL/api/v1/health"           '"status":"ok"'
check "fees"           "$BASE_URL/api/v1/fees/recommended"  '"recommendation"'
check "docs"           "$BASE_URL/docs"                     "swagger"          true
check "openapi.json"   "$BASE_URL/openapi.json"             '"openapi"'
check "redoc"          "$BASE_URL/redoc"

# Summary
if [[ "$QUIET" == "false" ]] || [[ "$FAIL_COUNT" -gt 0 ]]; then
    echo "--- $(date -u '+%Y-%m-%d %H:%M:%S UTC') | $PASS_COUNT/$TOTAL passed"
fi

[[ "$FAIL_COUNT" -eq 0 ]] && exit 0 || exit 1
