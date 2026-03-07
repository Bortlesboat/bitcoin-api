#!/usr/bin/env bash
# Security verification script for Satoshi API
# Usage: ./scripts/security_check.sh [BASE_URL]

BASE_URL="${1:-http://localhost:9332}"
API="/api/v1"
API_KEY="${SATOSHI_API_KEY:-}"
if [ -z "$API_KEY" ]; then
    echo "WARNING: SATOSHI_API_KEY not set. Test 2 (oversized payload) will fail."
fi
PASS=0
FAIL=0

check() {
    local desc="$1" expected="$2" actual="$3"
    if [ "$actual" = "$expected" ]; then
        echo "  PASS: $desc (got $actual)"
        ((PASS++))
    else
        echo "  FAIL: $desc (expected $expected, got $actual)"
        ((FAIL++))
    fi
}

echo "=== Satoshi API Security Check ==="
echo "Target: $BASE_URL"
echo ""

# 1. SQL injection on path params
echo "[1] SQL injection attempts"
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$API/tx/1'OR'1'='1")
check "SQLi in txid" "422" "$code"
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$API/blocks/abc'OR'1")
check "SQLi in block hash" "422" "$code"

# 2. Oversized payload
echo "[2] Oversized payload"
tmpfile=$(mktemp)
python3 -c "import json; print(json.dumps({'hex': 'aa' * 1100000}))" > "$tmpfile"
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL$API/decode" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: ${API_KEY}" \
    -d @"$tmpfile")
rm -f "$tmpfile"
check "2.2MB payload rejected" "422" "$code"

# 3. Invalid API key
echo "[3] Invalid API key"
code=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "X-API-Key: definitely-not-a-valid-key" "$BASE_URL$API/fees")
check "Invalid key -> 401" "401" "$code"

# 4. Path traversal
echo "[4] Path traversal"
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$API/blocks/..%2F..%2Fetc%2Fpasswd")
# 404 or 422 both mean the traversal was blocked (404 = router rejected, 422 = validation rejected)
if [ "$code" = "422" ] || [ "$code" = "404" ]; then
    echo "  PASS: Path traversal rejected (got $code)"
    ((PASS++))
else
    echo "  FAIL: Path traversal rejected (expected 404 or 422, got $code)"
    ((FAIL++))
fi

# 5. CORS from evil origin
echo "[5] CORS check"
acao=$(curl -s -D - -o /dev/null \
    -H "Origin: https://evil.example.com" "$BASE_URL$API/fees" 2>/dev/null \
    | grep -ci "access-control-allow-origin.*evil")
check "Evil origin not reflected" "0" "$acao"

# 6. Node version not leaked
echo "[6] Node version redaction"
body=$(curl -s "$BASE_URL$API/network")
leaked=$(echo "$body" | python3 -c "
import sys, json
d = json.load(sys.stdin).get('data', {})
print(1 if d.get('subversion') and d['subversion'] != '[redacted]' else 0)
" 2>/dev/null)
check "Anonymous: node version redacted" "0" "$leaked"

# 7. POST without API key
echo "[7] POST auth requirement"
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL$API/broadcast" \
    -H "Content-Type: application/json" -d '{"hex": "0200000001"}')
check "Anonymous broadcast rejected" "403" "$code"

# 8. Rate limit exhaustion (LAST — exhausts the window)
echo "[8] Rate limit exhaustion"
for i in $(seq 1 35); do
    curl -s -o /dev/null "$BASE_URL$API/fees" &
done
wait
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$API/fees")
check "Rate limited after burst" "429" "$code"

# 9. Security headers present
echo "[9] Security headers"
hdrs=$(curl -s -D - -o /dev/null "$BASE_URL$API/fees" 2>/dev/null)
for h in "x-content-type-options" "x-frame-options" "content-security-policy" "referrer-policy" "permissions-policy"; do
    present=$(echo "$hdrs" | grep -ci "$h")
    if [ "$present" -ge 1 ]; then
        echo "  PASS: $h header present"
        ((PASS++))
    else
        echo "  FAIL: $h header missing"
        ((FAIL++))
    fi
done

# 10. HTTP method confusion (DELETE should be 405)
echo "[10] HTTP method confusion"
code=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE_URL$API/fees")
check "DELETE /fees -> 405" "405" "$code"
code=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$BASE_URL$API/fees")
check "PUT /fees -> 405" "405" "$code"

# 11. JSON content-type enforcement on POST
echo "[11] Content-type enforcement"
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL$API/decode" \
    -H "X-API-Key: ${API_KEY}" \
    -H "Content-Type: text/plain" \
    -d 'not json at all')
check "POST with text/plain rejected" "422" "$code"

# 12. Error response envelope consistency (no raw tracebacks)
echo "[12] Error envelope consistency"
body=$(curl -s "$BASE_URL$API/tx/0000000000000000000000000000000000000000000000000000000000000000")
has_error=$(echo "$body" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(1 if 'error' in d and 'status' in d['error'] else 0)
except: print(0)
" 2>/dev/null)
check "404 has {error} envelope" "1" "$has_error"

# 13. No stack trace in error responses
echo "[13] No stack trace leakage"
body=$(curl -s "$BASE_URL$API/tx/ZZZZ")
leaked=$(echo "$body" | grep -ci "traceback\|\.py\|File \"")
check "No traceback in 422 response" "0" "$leaked"

# 14. Malformed hex to /decode
echo "[14] Malformed Bitcoin hex"
if [ -n "$API_KEY" ]; then
    code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL$API/decode" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: ${API_KEY}" \
        -d '{"hex": "ZZZZ_not_hex"}')
    # Should get 422 (validation) or 400 (bad request), NOT 500
    if [ "$code" = "422" ] || [ "$code" = "400" ]; then
        echo "  PASS: Malformed hex rejected cleanly (got $code)"
        ((PASS++))
    else
        echo "  FAIL: Malformed hex (expected 400 or 422, got $code)"
        ((FAIL++))
    fi
else
    echo "  SKIP: Needs API key"
fi

# 15. Node version not in error messages
echo "[15] RPC info not leaked in errors"
body=$(curl -s "$BASE_URL$API/tx/0000000000000000000000000000000000000000000000000000000000000000")
leaked=$(echo "$body" | grep -ci "rpc\|8332\|bitcoin-cli\|cookie")
check "No RPC details in error body" "0" "$leaked"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
