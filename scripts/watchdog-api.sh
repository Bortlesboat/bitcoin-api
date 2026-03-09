#!/usr/bin/env bash
# Satoshi API Watchdog
# Checks if the API is running on port 9332 and restarts it if not.
# Designed to run every 5 minutes via Windows Task Scheduler.

set -euo pipefail

API_PORT=9332
API_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$API_DIR/logs"
WATCHDOG_LOG="$LOG_DIR/watchdog.log"
API_LOG="$LOG_DIR/api.log"
HEALTH_URL="http://localhost:$API_PORT/api/v1/health"
HEALTH_TIMEOUT=10
STARTUP_WAIT=5

# Ensure logs directory exists
mkdir -p "$LOG_DIR"

timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

log() {
    echo "[$(timestamp)] $1" >> "$WATCHDOG_LOG"
}

# Trim watchdog log if it exceeds 10000 lines
if [[ -f "$WATCHDOG_LOG" ]] && (( $(wc -l < "$WATCHDOG_LOG") > 10000 )); then
    tail -5000 "$WATCHDOG_LOG" > "$WATCHDOG_LOG.tmp" && mv "$WATCHDOG_LOG.tmp" "$WATCHDOG_LOG"
    log "Trimmed watchdog log to last 5000 lines"
fi

# Step 1: Check if anything is listening on the port
port_listening() {
    netstat -ano 2>/dev/null | grep -qE ":${API_PORT}\s.*LISTEN"
}

# Step 2: Health check - verify it's actually responding
health_check() {
    local status
    status=$(curl -s -o /dev/null -w '%{http_code}' --max-time "$HEALTH_TIMEOUT" "$HEALTH_URL" 2>/dev/null) || return 1
    [[ "$status" == "200" ]]
}

# Get PID of process on port (for killing zombies)
get_pid_on_port() {
    netstat -ano 2>/dev/null | grep -E ":${API_PORT}\s.*LISTEN" | awk '{print $NF}' | head -1
}

# Start the API
start_api() {
    log "Starting Satoshi API..."
    cd "$API_DIR"
    PYTHONPATH=src nohup python -m uvicorn bitcoin_api.main:app --host 0.0.0.0 --port "$API_PORT" --workers 2 >> "$API_LOG" 2>&1 &
    local new_pid=$!
    log "Launched uvicorn with PID $new_pid, waiting ${STARTUP_WAIT}s..."
    sleep "$STARTUP_WAIT"

    if port_listening; then
        if health_check; then
            log "SUCCESS: API is up and healthy (PID $new_pid)"
            return 0
        else
            log "WARNING: Port is listening but health check failed (PID $new_pid)"
            return 1
        fi
    else
        log "FAILURE: API did not start - port $API_PORT not listening after ${STARTUP_WAIT}s"
        log "Last 10 lines of api.log:"
        tail -10 "$API_LOG" 2>/dev/null >> "$WATCHDOG_LOG" || true
        return 1
    fi
}

# Main logic
if port_listening; then
    # Something is on the port - verify it's healthy
    if health_check; then
        # All good, silent exit
        exit 0
    else
        # Zombie process - kill it and restart
        zombie_pid=$(get_pid_on_port)
        log "ZOMBIE DETECTED: Port $API_PORT listening but health check failed (PID $zombie_pid)"
        if [[ -n "$zombie_pid" ]]; then
            log "Killing zombie process $zombie_pid..."
            taskkill //PID "$zombie_pid" //F > /dev/null 2>&1 || true
            sleep 2
        fi
        start_api
    fi
else
    # Nothing on the port - start fresh
    log "API not running on port $API_PORT"
    start_api
fi
