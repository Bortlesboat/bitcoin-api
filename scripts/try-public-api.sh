#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-https://bitcoinsapi.com}"
TIMEOUT="${TIMEOUT:-10}"
USER_AGENT="${USER_AGENT:-SatoshiAPITryPublic/1.0}"

need() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "Missing required command: $1" >&2
        exit 1
    }
}

need curl
if command -v python.exe >/dev/null 2>&1; then
    PYTHON_BIN="python.exe"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "Missing required command: python.exe, python3, or python" >&2
    exit 1
fi

TMPDIR=".tmp.try-public.$$"
mkdir -p "$TMPDIR"
trap 'rm -rf "$TMPDIR"' EXIT

request() {
    local name="$1"
    local expected="$2"
    local path="$3"
    local out="$TMPDIR/${name}.json"
    local http_code

    http_code="$(curl -sS --max-time "$TIMEOUT" \
        -H "User-Agent: $USER_AGENT" \
        -o "$out" \
        -w "%{http_code}" \
        "$BASE_URL$path")"

    if [[ "$http_code" != "$expected" ]]; then
        echo "FAIL  $name - HTTP $http_code (expected $expected)" >&2
        cat "$out" >&2 || true
        exit 1
    fi

    echo "$out"
}

render() {
    local mode="$1"
    local path="$2"
    local python_path="$path"
    if [[ "$PYTHON_BIN" == *.exe ]] && command -v cygpath >/dev/null 2>&1; then
        python_path="$(cygpath -w "$path")"
    fi
    "$PYTHON_BIN" - "$mode" "$python_path" <<'PY'
import json
import sys

mode, path = sys.argv[1:]
with open(path, encoding="utf-8") as fh:
    body = json.load(fh)

data = body.get("data", {})

if mode == "recommended":
    print(f"Recommendation: {data.get('recommendation', 'n/a')}")
    estimates = data.get("estimates", {})
    if estimates:
        ordered = ", ".join(f"{k} blocks={v} sat/vB" for k, v in estimates.items())
        print(f"Estimates:      {ordered}")

elif mode == "plan":
    print(f"Recommendation: {data.get('recommendation', 'n/a')} ({data.get('recommendation_confidence', 'n/a')} confidence)")
    print(f"Reasoning:      {data.get('reasoning', 'n/a')}")
    env = data.get("fee_environment", {})
    print(f"Environment:    {env.get('level', 'n/a')} - {env.get('message', 'n/a')}")
    tiers = data.get("cost_tiers", {})
    for tier in ("immediate", "standard", "patient", "opportunistic"):
        item = tiers.get(tier)
        if not item:
            continue
        usd = item.get("total_fee_usd")
        usd_text = f" (${usd:.4f})" if isinstance(usd, (int, float)) else ""
        print(
            f"{tier.capitalize():<15}"
            f"{item.get('fee_rate_sat_vb', 'n/a')} sat/vB | "
            f"{item.get('total_fee_sats', 'n/a')} sats{usd_text} | "
            f"{item.get('estimated_time', 'n/a')}"
        )
    trend = data.get("trend", {})
    print(f"Trend:          {trend.get('direction', 'n/a')} ({trend.get('mempool_change_pct', 'n/a')}% mempool change)")

elif mode == "savings":
    savings = data.get("savings_per_tx", {})
    monthly = data.get("monthly_projection", {})
    print(
        "Savings/tx:     "
        f"{savings.get('sats', 'n/a')} sats "
        f"({savings.get('percent', 'n/a')}%)"
    )
    if "usd" in savings:
        print(f"Savings/tx USD: ${savings.get('usd', 0):.4f}")
    print(
        "Monthly (30 tx): "
        f"{monthly.get('total_savings_sats', 'n/a')} sats"
    )
    if "total_savings_usd" in monthly:
        print(f"Monthly USD:    ${monthly.get('total_savings_usd', 0):.4f}")
    fee_range = data.get("fee_range", {})
    print(
        "Observed range: "
        f"{fee_range.get('min', 'n/a')} - {fee_range.get('max', 'n/a')} sat/vB "
        f"(avg {fee_range.get('avg', 'n/a')})"
    )

elif mode == "x402":
    err = body.get("error", {})
    if isinstance(err, str):
        detail = body.get("message", "n/a")
        title = err
    else:
        detail = err.get("detail", "n/a")
        title = err.get("title", "n/a")
    req = body.get("paymentRequirements", {})
    print(f"Challenge:      {title} - {detail}")
    print(
        "Premium call:   "
        f"{req.get('resource', 'n/a')} costs ${req.get('maxAmountRequired', 'n/a')}"
    )

elif mode == "guide":
    print("Quickstart:")
    for step in data.get("quickstart", []):
        curl = step.get("examples", {}).get("curl")
        print(f"  {step.get('step')}. {step.get('action')}")
        if curl:
            print(f"     {curl}")
PY
}

section() {
    printf '\n== %s ==\n' "$1"
}

echo "Satoshi API public trial"
echo "Base URL: $BASE_URL"
echo "This exercises the hosted anonymous fee-intelligence flow plus the x402 demo."

recommended_file="$(request recommended 200 '/api/v1/fees/recommended')"
section "Send-or-wait verdict"
render recommended "$recommended_file"

plan_file="$(request plan 200 '/api/v1/fees/plan?profile=simple_send&currency=usd')"
section "Transaction planner"
render plan "$plan_file"

savings_file="$(request savings 200 '/api/v1/fees/savings?currency=usd')"
section "Savings simulation"
render savings "$savings_file"

x402_file="$(request x402_demo 402 '/api/v1/x402-demo')"
section "Premium lane demo"
render x402 "$x402_file"

guide_file="$(request guide 200 '/api/v1/guide?use_case=fees&lang=curl')"
section "Next curl commands"
render guide "$guide_file"

section "Next steps"
echo "1. Register a free key:"
echo "   curl -X POST $BASE_URL/api/v1/register -H 'Content-Type: application/json' -d '{\"email\":\"you@example.com\",\"label\":\"my-app\",\"agreed_to_terms\":true}'"
echo "2. Retry the planner with your own app flow or transaction shape."
echo "3. Use /api/v1/fees/landscape when you want the premium full-context verdict."
