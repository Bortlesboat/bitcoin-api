#!/usr/bin/env bash
# diagnose.sh — Fast silo-by-silo diagnostic for Satoshi API
#
# Usage:
#   bash scripts/diagnose.sh          # full dashboard
#   bash scripts/diagnose.sh --json   # machine-readable output
#   bash scripts/diagnose.sh --silo node    # check single silo
#   bash scripts/diagnose.sh --silo api,db  # check multiple silos
#
# Silos: node, tunnel, api, cache, db, tests
set -uo pipefail

API_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT=9332
LOCAL_URL="http://localhost:$PORT"
PUBLIC_URL="https://bitcoinsapi.com"
DB_PATH="$API_DIR/data/bitcoin_api.db"

# --- Parse args ---
JSON_MODE=false
SILOS_FILTER=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --json) JSON_MODE=true; shift ;;
        --silo) SILOS_FILTER="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# --- Colors (skip in JSON mode) ---
if [[ "$JSON_MODE" == "false" ]]; then
    GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
    CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
else
    GREEN=''; RED=''; YELLOW=''; CYAN=''; BOLD=''; NC=''
fi

PASS_COUNT=0; WARN_COUNT=0; FAIL_COUNT=0
RESULTS=()

status_icon() {
    case "$1" in
        PASS) echo -e "${GREEN}PASS${NC}" ;;
        WARN) echo -e "${YELLOW}WARN${NC}" ;;
        FAIL) echo -e "${RED}FAIL${NC}" ;;
    esac
}

record() {
    local silo="$1" status="$2" detail="$3"
    case "$status" in
        PASS) PASS_COUNT=$((PASS_COUNT + 1)) ;;
        WARN) WARN_COUNT=$((WARN_COUNT + 1)) ;;
        FAIL) FAIL_COUNT=$((FAIL_COUNT + 1)) ;;
    esac
    if [[ "$JSON_MODE" == "true" ]]; then
        RESULTS+=("{\"silo\":\"$silo\",\"status\":\"$status\",\"detail\":\"$detail\"}")
    else
        printf "  %-12s $(status_icon "$status")  %s\n" "$silo" "$detail"
    fi
}

should_check() {
    [[ -z "$SILOS_FILTER" ]] && return 0
    echo ",$SILOS_FILTER," | grep -q ",$1,"
}

# =====================================================================
# SILO 1: Bitcoin Node
# =====================================================================
check_node() {
    [[ "$JSON_MODE" == "false" ]] && echo -e "\n${BOLD}${CYAN}[Node]${NC} Bitcoin Core / Knots"

    # Check if bitcoin-qt or bitcoind is running
    local node_pid
    node_pid=$(tasklist 2>/dev/null | grep -iE "bitcoin-qt|bitcoind" | awk '{print $2}' | head -1)

    if [[ -z "$node_pid" ]]; then
        record "node.process" "FAIL" "No bitcoin-qt or bitcoind process found"
        return
    fi
    record "node.process" "PASS" "Running (PID $node_pid)"

    # Check RPC connectivity via API health endpoint
    local health_body
    health_body=$(curl -s --max-time 5 "$LOCAL_URL/api/v1/health" 2>/dev/null) || {
        record "node.rpc" "WARN" "Cannot check RPC (API not responding)"
        return
    }

    if echo "$health_body" | grep -q '"status":"ok"'; then
        local blocks
        blocks=$(echo "$health_body" | python -c "import sys,json; print(json.load(sys.stdin)['data']['blocks'])" 2>/dev/null || echo "?")
        record "node.rpc" "PASS" "RPC connected, block height $blocks"
    else
        record "node.rpc" "FAIL" "RPC not responding through API"
    fi
}

# =====================================================================
# SILO 2: Cloudflare Tunnel
# =====================================================================
check_tunnel() {
    [[ "$JSON_MODE" == "false" ]] && echo -e "\n${BOLD}${CYAN}[Tunnel]${NC} Cloudflare Tunnel"

    # Check if cloudflared process is running
    local cf_pid
    cf_pid=$(tasklist 2>/dev/null | grep -i "cloudflared" | awk '{print $2}' | head -1)

    if [[ -z "$cf_pid" ]]; then
        record "tunnel.process" "FAIL" "cloudflared not running"
        return
    fi
    record "tunnel.process" "PASS" "Running (PID $cf_pid)"

    # Check public URL reachability
    local pub_code
    pub_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$PUBLIC_URL/api/v1/health" 2>/dev/null) || pub_code="000"

    if [[ "$pub_code" == "200" ]]; then
        record "tunnel.public" "PASS" "Public URL reachable (HTTP $pub_code)"
    elif [[ "$pub_code" == "530" ]]; then
        record "tunnel.public" "FAIL" "HTTP 530 — tunnel has no active connections"
    elif [[ "$pub_code" == "502" ]]; then
        record "tunnel.public" "FAIL" "HTTP 502 — tunnel up but API not responding"
    else
        record "tunnel.public" "WARN" "Public URL returned HTTP $pub_code"
    fi
}

# =====================================================================
# SILO 3: API Process
# =====================================================================
check_api() {
    [[ "$JSON_MODE" == "false" ]] && echo -e "\n${BOLD}${CYAN}[API]${NC} Uvicorn / FastAPI"

    # Check if port is listening
    local listening
    listening=$(netstat -ano 2>/dev/null | grep -E ":${PORT}\s.*LISTEN" | head -1)

    if [[ -z "$listening" ]]; then
        record "api.port" "FAIL" "Nothing listening on port $PORT"
        return
    fi
    local api_pid
    api_pid=$(echo "$listening" | awk '{print $NF}')
    record "api.port" "PASS" "Listening on :$PORT (PID $api_pid)"

    # Health check
    local health_code
    health_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$LOCAL_URL/api/v1/health" 2>/dev/null) || health_code="000"

    if [[ "$health_code" == "200" ]]; then
        record "api.health" "PASS" "/health returns 200"
    else
        record "api.health" "FAIL" "/health returns HTTP $health_code"
        return
    fi

    # Circuit breaker (via /health/deep if we have an admin key)
    if [[ -n "${ADMIN_API_KEY:-}" ]]; then
        local deep_body
        deep_body=$(curl -s --max-time 5 -H "X-API-Key: $ADMIN_API_KEY" "$LOCAL_URL/api/v1/health/deep" 2>/dev/null) || deep_body=""
        if [[ -n "$deep_body" ]]; then
            local cb_state
            cb_state=$(echo "$deep_body" | python -c "import sys,json; print(json.load(sys.stdin)['data']['circuit_breaker']['state'])" 2>/dev/null || echo "unknown")
            if [[ "$cb_state" == "closed" ]]; then
                record "api.circuit" "PASS" "Circuit breaker CLOSED (healthy)"
            elif [[ "$cb_state" == "open" ]]; then
                record "api.circuit" "FAIL" "Circuit breaker OPEN — node failures detected"
            else
                record "api.circuit" "WARN" "Circuit breaker state: $cb_state"
            fi

            # Uptime
            local uptime
            uptime=$(echo "$deep_body" | python -c "
import sys, json
u = json.load(sys.stdin)['data']['uptime_seconds']
h = int(u) // 3600
m = (int(u) % 3600) // 60
print(f'{h}h {m}m')
" 2>/dev/null || echo "?")
            record "api.uptime" "PASS" "Up for $uptime"

            # Background job
            local job_alive
            job_alive=$(echo "$deep_body" | python -c "import sys,json; print(json.load(sys.stdin)['data']['background_job']['thread_alive'])" 2>/dev/null || echo "unknown")
            if [[ "$job_alive" == "True" ]]; then
                record "api.jobs" "PASS" "Fee collector thread alive"
            else
                record "api.jobs" "FAIL" "Fee collector thread DEAD"
            fi
        fi
    else
        record "api.circuit" "WARN" "Set ADMIN_API_KEY to check circuit breaker + deep health"
    fi
}

# =====================================================================
# SILO 4: Cache & Stale Store
# =====================================================================
check_cache() {
    [[ "$JSON_MODE" == "false" ]] && echo -e "\n${BOLD}${CYAN}[Cache]${NC} TTL Cache + Stale Store"

    if [[ -z "${ADMIN_API_KEY:-}" ]]; then
        record "cache" "WARN" "Set ADMIN_API_KEY to inspect cache state"
        return
    fi

    local deep_body
    deep_body=$(curl -s --max-time 5 -H "X-API-Key: $ADMIN_API_KEY" "$LOCAL_URL/api/v1/health/deep" 2>/dev/null) || {
        record "cache" "WARN" "Cannot reach /health/deep"
        return
    }

    local cached age
    cached=$(echo "$deep_body" | python -c "import sys,json; print(json.load(sys.stdin)['data']['blockchain_info_cached'])" 2>/dev/null || echo "unknown")
    age=$(echo "$deep_body" | python -c "import sys,json; print(json.load(sys.stdin)['data'].get('cache_age_seconds', '?'))" 2>/dev/null || echo "?")

    if [[ "$cached" == "True" ]]; then
        record "cache.hot" "PASS" "Blockchain info cached (age: ${age}s)"
    else
        record "cache.hot" "WARN" "Blockchain info NOT cached — first request will be slow"
    fi

    # Check stale store via metrics endpoint
    local metrics
    metrics=$(curl -s --max-time 5 "$LOCAL_URL/metrics" 2>/dev/null) || metrics=""
    if [[ -n "$metrics" ]]; then
        local stale_total
        stale_total=$(echo "$metrics" | grep -E '^stale_cache_served_total' | awk '{sum+=$2} END {printf "%.0f", sum}' || echo "0")
        if [[ "$stale_total" -gt 0 ]]; then
            record "cache.stale" "WARN" "$stale_total stale fallback(s) served since last restart"
        else
            record "cache.stale" "PASS" "Zero stale fallbacks served"
        fi
    fi
}

# =====================================================================
# SILO 5: Database
# =====================================================================
check_db() {
    [[ "$JSON_MODE" == "false" ]] && echo -e "\n${BOLD}${CYAN}[Database]${NC} SQLite (WAL)"

    if [[ ! -f "$DB_PATH" ]]; then
        record "db.file" "FAIL" "Database not found at $DB_PATH"
        return
    fi

    local db_size
    db_size=$(du -sh "$DB_PATH" 2>/dev/null | awk '{print $1}')
    record "db.file" "PASS" "Exists ($db_size)"

    # Check if writable
    if [[ -w "$DB_PATH" ]]; then
        record "db.writable" "PASS" "Writable"
    else
        record "db.writable" "FAIL" "NOT writable — usage logging will fail"
    fi

    # Check WAL file
    if [[ -f "${DB_PATH}-wal" ]]; then
        local wal_size
        wal_size=$(du -sh "${DB_PATH}-wal" 2>/dev/null | awk '{print $1}')
        if [[ $(stat -c%s "${DB_PATH}-wal" 2>/dev/null || echo 0) -gt 104857600 ]]; then
            record "db.wal" "WARN" "WAL file large ($wal_size) — consider checkpoint"
        else
            record "db.wal" "PASS" "WAL file healthy ($wal_size)"
        fi
    fi

    # Migration count
    if [[ -n "${ADMIN_API_KEY:-}" ]]; then
        local deep_body
        deep_body=$(curl -s --max-time 5 -H "X-API-Key: $ADMIN_API_KEY" "$LOCAL_URL/api/v1/health/deep" 2>/dev/null) || deep_body=""
        if [[ -n "$deep_body" ]]; then
            local mig_count
            mig_count=$(echo "$deep_body" | python -c "import sys,json; print(json.load(sys.stdin)['data']['db_migrations_applied'])" 2>/dev/null || echo "?")
            record "db.migrations" "PASS" "$mig_count migrations applied"
        fi
    fi
}

# =====================================================================
# SILO 6: Tests (optional, slower)
# =====================================================================
check_tests() {
    [[ "$JSON_MODE" == "false" ]] && echo -e "\n${BOLD}${CYAN}[Tests]${NC} pytest (fast run)"

    cd "$API_DIR"
    local test_output
    test_output=$(PYTHONPATH=src python -m pytest tests/ -q --tb=no --no-header \
        --ignore=tests/test_e2e.py --ignore=tests/locustfile.py 2>&1) || {
        local failures
        failures=$(echo "$test_output" | tail -1)
        record "tests" "FAIL" "$failures"
        return
    }
    local summary
    summary=$(echo "$test_output" | tail -1)
    record "tests" "PASS" "$summary"
}

# =====================================================================
# SILO 7: Version & Git State
# =====================================================================
check_version() {
    [[ "$JSON_MODE" == "false" ]] && echo -e "\n${BOLD}${CYAN}[Version]${NC} Git & Release State"

    cd "$API_DIR"

    # Current version from pyproject.toml
    local version
    version=$(grep -m1 'version' pyproject.toml | sed 's/.*"\(.*\)".*/\1/' 2>/dev/null || echo "?")
    record "version.current" "PASS" "v$version"

    # Git status
    local dirty
    dirty=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$dirty" -gt 0 ]]; then
        record "version.git" "WARN" "$dirty uncommitted change(s)"
    else
        record "version.git" "PASS" "Working tree clean"
    fi

    # Latest tag
    local latest_tag
    latest_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "none")
    local commits_since
    commits_since=$(git rev-list "$latest_tag"..HEAD --count 2>/dev/null || echo "?")
    if [[ "$latest_tag" == "none" ]]; then
        record "version.tag" "WARN" "No git tags — run: bash scripts/release.sh tag"
    elif [[ "$commits_since" -gt 0 ]]; then
        record "version.tag" "WARN" "$commits_since commit(s) since $latest_tag — consider tagging"
    else
        record "version.tag" "PASS" "HEAD is at $latest_tag"
    fi
}

# =====================================================================
# Run selected silos
# =====================================================================
[[ "$JSON_MODE" == "false" ]] && echo -e "${BOLD}=== Satoshi API Diagnostics ===${NC}"
[[ "$JSON_MODE" == "false" ]] && echo "$(date '+%Y-%m-%d %H:%M:%S')"

should_check "node"    && check_node
should_check "tunnel"  && check_tunnel
should_check "api"     && check_api
should_check "cache"   && check_cache
should_check "db"      && check_db
should_check "version" && check_version
should_check "tests"   && check_tests

# =====================================================================
# Summary
# =====================================================================
TOTAL=$((PASS_COUNT + WARN_COUNT + FAIL_COUNT))

if [[ "$JSON_MODE" == "true" ]]; then
    echo "{\"timestamp\":\"$(date -u '+%Y-%m-%dT%H:%M:%SZ')\",\"pass\":$PASS_COUNT,\"warn\":$WARN_COUNT,\"fail\":$FAIL_COUNT,\"checks\":[$(IFS=,; echo "${RESULTS[*]}")]}"
else
    echo ""
    echo -e "${BOLD}--- Summary ---${NC}"
    echo -e "  ${GREEN}PASS${NC}: $PASS_COUNT  ${YELLOW}WARN${NC}: $WARN_COUNT  ${RED}FAIL${NC}: $FAIL_COUNT  (total: $TOTAL)"

    if [[ $FAIL_COUNT -gt 0 ]]; then
        echo ""
        echo -e "${RED}${BOLD}Action required — see FAIL items above${NC}"
        echo "  Quick fixes:"
        echo "    Node down?    → Start Bitcoin Knots from Start Menu"
        echo "    Tunnel down?  → bash -c 'cloudflared tunnel run satoshi-api &'"
        echo "    API down?     → bash scripts/watchdog-api.sh"
        echo "    Tests fail?   → PYTHONPATH=src python -m pytest tests/ -x"
        echo "    DB issues?    → Check data/ directory permissions"
        exit 1
    elif [[ $WARN_COUNT -gt 0 ]]; then
        echo ""
        echo -e "${YELLOW}Warnings present but system operational${NC}"
        exit 0
    else
        echo ""
        echo -e "${GREEN}${BOLD}All systems healthy${NC}"
        exit 0
    fi
fi
