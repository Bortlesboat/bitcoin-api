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

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
