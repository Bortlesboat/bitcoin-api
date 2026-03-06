#!/usr/bin/env bash
# Security verification script for Satoshi API
# Usage: ./scripts/security_check.sh [BASE_URL]

BASE_URL="${1:-http://localhost:9332}"
API="/api/v1"
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
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$API/blocks/1;DROP TABLE blocks")
check "SQLi in block height" "422" "$code"

# 2. Oversized payload
echo "[2] Oversized payload"
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL$API/decode" \
    -H "Content-Type: application/json" \
    -d "{\"raw_tx\": \"$(python3 -c 'print("aa" * 600000)')\"}")
check "1.2MB payload rejected" "422" "$code"

# 3. Rate limit exhaustion
echo "[3] Rate limit exhaustion"
for i in $(seq 1 35); do
    curl -s -o /dev/null "$BASE_URL$API/health" &
done
wait
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$API/health")
check "Rate limited after burst" "429" "$code"

# 4. Invalid API key
echo "[4] Invalid API key"
code=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "X-API-Key: definitely-not-a-valid-key" "$BASE_URL$API/health")
check "Invalid key → 401" "401" "$code"

# 5. Path traversal
echo "[5] Path traversal"
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$API/tx/../../etc/passwd")
check "Path traversal rejected" "422" "$code"

# 6. CORS from evil origin
echo "[6] CORS check"
acao=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Origin: https://evil.example.com" "$BASE_URL$API/health" \
    -D - 2>/dev/null | grep -i "access-control-allow-origin" | grep "evil" | wc -l)
check "Evil origin not reflected" "0" "$acao"

# 7. Node version not leaked
echo "[7] Node version redaction"
body=$(curl -s "$BASE_URL$API/network")
leaked=$(echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin).get('data',{}); print(1 if d.get('subversion') and d['subversion'] != '[redacted]' else 0)" 2>/dev/null)
check "Anonymous: node version redacted" "0" "$leaked"

# 8. POST without API key
echo "[8] POST auth requirement"
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL$API/broadcast" \
    -H "Content-Type: application/json" -d '{"raw_tx": "0200000001"}')
check "Anonymous broadcast rejected" "403" "$code"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
