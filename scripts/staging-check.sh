#!/usr/bin/env bash
# Pre-deploy staging validation for Satoshi API
# Catches deployment-breaking issues (CSP blocking /docs, missing headers,
# broken middleware) that unit tests don't cover.
#
# Usage: bash scripts/staging-check.sh
#
# To use as a git pre-push hook:
# ln -s ../../scripts/staging-check.sh .git/hooks/pre-push
# Or add to .git/hooks/pre-push:
#   bash scripts/staging-check.sh || exit 1

set -uo pipefail

PORT=9333
BASE="http://localhost:$PORT"
TIMEOUT=15
PASS_COUNT=0
FAIL_COUNT=0
TOTAL=0
PID=""

# Resolve project root (script lives in scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Cleanup trap: kill staging server on exit no matter what ---
cleanup() {
    if [[ -n "$PID" ]]; then
        taskkill //PID "$PID" //F //T >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

# --- Start staging server ---
echo "=== Satoshi API Staging Validation ==="
echo "Starting staging server on port $PORT..."

PYTHONPATH="$PROJECT_ROOT/src" python -m uvicorn bitcoin_api.main:app \
    --host 127.0.0.1 --port "$PORT" --log-level warning &
PID=$!

# Poll health endpoint until ready (max TIMEOUT seconds)
elapsed=0
while [[ $elapsed -lt $TIMEOUT ]]; do
    if curl -sf "$BASE/api/v1/health" >/dev/null 2>&1; then
        echo "Server ready after ${elapsed}s."
        break
    fi
    sleep 1
    elapsed=$((elapsed + 1))
done

if [[ $elapsed -ge $TIMEOUT ]]; then
    echo "FATAL: Server failed to start within ${TIMEOUT}s."
    exit 1
fi

echo ""

# --- Check helpers ---
HEADER_FILE=$(mktemp)

get_http_code() {
    # Extract HTTP status code from curl dump headers (works without grep -P)
    awk '/^HTTP\// { code=$2 } END { print code }' "$HEADER_FILE"
}

pass() {
    PASS_COUNT=$((PASS_COUNT + 1))
    TOTAL=$((TOTAL + 1))
    echo "PASS  $1"
}

fail() {
    FAIL_COUNT=$((FAIL_COUNT + 1))
    TOTAL=$((TOTAL + 1))
    echo "FAIL  $1"
}

# --- Checks ---

# 1. Health endpoint returns 200 with status ok
body=$(curl -s -D "$HEADER_FILE" --max-time 10 "$BASE/api/v1/health")
http_code=$(get_http_code)
if [[ "$http_code" == "200" ]] && echo "$body" | grep -q '"status":"ok"'; then
    pass "/api/v1/health returns 200 with status ok"
else
    fail "/api/v1/health — got HTTP $http_code or missing status:ok"
fi

# 2. Security headers present on /api/v1/health
if grep -qi "X-Content-Type-Options" "$HEADER_FILE" && grep -qi "X-Frame-Options" "$HEADER_FILE"; then
    pass "/api/v1/health has security headers (X-Content-Type-Options, X-Frame-Options)"
else
    fail "/api/v1/health missing security headers"
fi

# 3. CSP header present on /api/v1/health (non-docs path should have it)
if grep -qi "Content-Security-Policy" "$HEADER_FILE"; then
    pass "/api/v1/health has Content-Security-Policy header"
else
    fail "/api/v1/health missing Content-Security-Policy header"
fi

# 4. /api/v1/fees/recommended — 200 = ok, 502 = node not connected, 429 = rate limited (shares DB with prod)
fees_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$BASE/api/v1/fees/recommended")
if [[ "$fees_code" == "200" ]] || [[ "$fees_code" == "502" ]] || [[ "$fees_code" == "429" ]]; then
    pass "/api/v1/fees/recommended returns $fees_code (endpoint reachable)"
else
    fail "/api/v1/fees/recommended — got HTTP $fees_code"
fi

# 5. /docs returns 200 and does NOT have CSP header
curl -s -D "$HEADER_FILE" --max-time 10 "$BASE/docs" -o /dev/null
docs_code=$(get_http_code)
if [[ "$docs_code" == "200" ]]; then
    if grep -qi "Content-Security-Policy" "$HEADER_FILE"; then
        fail "/docs has Content-Security-Policy header (CSP blocks Swagger UI)"
    else
        pass "/docs returns 200 with no CSP header (Swagger UI safe)"
    fi
else
    fail "/docs — got HTTP $docs_code (expected 200)"
fi

# 6. /redoc returns 200 and does NOT have CSP header
curl -s -D "$HEADER_FILE" --max-time 10 "$BASE/redoc" -o /dev/null
redoc_code=$(get_http_code)
if [[ "$redoc_code" == "200" ]]; then
    if grep -qi "Content-Security-Policy" "$HEADER_FILE"; then
        fail "/redoc has Content-Security-Policy header (CSP blocks ReDoc)"
    else
        pass "/redoc returns 200 with no CSP header (ReDoc safe)"
    fi
else
    fail "/redoc — got HTTP $redoc_code (expected 200)"
fi

# 7. /openapi.json returns 200 and is valid JSON
openapi_body=$(curl -s -D "$HEADER_FILE" --max-time 10 "$BASE/openapi.json")
openapi_code=$(get_http_code)
if [[ "$openapi_code" == "200" ]] && echo "$openapi_body" | python -m json.tool >/dev/null 2>&1; then
    pass "/openapi.json returns 200 with valid JSON"
else
    fail "/openapi.json — HTTP $openapi_code or invalid JSON"
fi

# 8. Landing page returns 200 and contains site title
landing_body=$(curl -s -D "$HEADER_FILE" --max-time 10 "$BASE/")
landing_code=$(get_http_code)
if [[ "$landing_code" == "200" ]] && echo "$landing_body" | grep -qi "Satoshi API"; then
    pass "/ (landing page) returns 200 with 'Satoshi API' title"
else
    fail "/ (landing page) — HTTP $landing_code or missing title"
fi

# --- Cleanup happens via trap ---
rm -f "$HEADER_FILE"

# --- Summary ---
echo ""
echo "=== Results: $PASS_COUNT/$TOTAL passed ==="
if [[ $FAIL_COUNT -gt 0 ]]; then
    echo "STAGING VALIDATION FAILED — do NOT deploy."
    exit 1
else
    echo "All checks passed — safe to deploy."
    exit 0
fi
