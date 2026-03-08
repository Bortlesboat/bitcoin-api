#!/usr/bin/env bash
# deploy-api.sh — Pull, test, restart Satoshi API (bitcoinsapi.com)
# Runs in bash on Windows. Cloudflare Tunnel is a separate Windows service.
set -euo pipefail

API_DIR="$HOME/Bortlesboat/bitcoin-api"
PORT=9332
LOG_DIR="$API_DIR/logs"
LOG_FILE="$LOG_DIR/api.log"

cd "$API_DIR"
echo "=== Satoshi API Deployment ==="
echo "$(date '+%Y-%m-%d %H:%M:%S') — Starting deploy"

# 1. Pull latest code
echo ""
echo "[1/6] Pulling latest from git..."
git pull --ff-only || { echo "FATAL: git pull failed (merge conflict?)"; exit 1; }

# 1.5. Install/update dependencies
echo ""
echo "[1.5/6] Installing dependencies..."
pip install -e . --quiet || { echo "FATAL: pip install failed"; exit 1; }

# 2. Run tests
echo ""
echo "[2/6] Running marketing sync check..."
python scripts/marketing_sync.py || { echo "WARNING: Marketing materials have stale endpoint counts. Run: python scripts/marketing_sync.py --fix"; }

echo ""
echo "[3/6] Running tests..."
PYTHONPATH=src python -m pytest tests/ -q --ignore=tests/test_e2e.py --ignore=tests/locustfile.py || { echo "FATAL: Tests failed — aborting deploy"; exit 1; }
echo "Tests passed."

# 3. Find and kill existing uvicorn process on port 9332
echo ""
echo "[4/6] Stopping current uvicorn (port $PORT)..."
PIDS=$(netstat -ano 2>/dev/null | grep ":${PORT}" | grep "LISTENING" | awk '{print $NF}' | sort -u || true)

if [ -n "$PIDS" ]; then
    for PID in $PIDS; do
        echo "  Killing PID $PID (SIGTERM)..."
        taskkill //PID "$PID" 2>/dev/null || true
        sleep 5
        # Force kill if still alive
        taskkill //PID "$PID" //F 2>/dev/null || true
    done
    echo "  Process(es) stopped."
else
    echo "  No existing process on port $PORT — clean start."
fi

# 4. Start new uvicorn
echo ""
echo "[5/6] Starting uvicorn..."
mkdir -p "$LOG_DIR"
cd "$API_DIR"
PYTHONPATH=src nohup python -m uvicorn bitcoin_api.main:app --host 0.0.0.0 --port "$PORT" >> "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "  Started uvicorn (PID $NEW_PID), logging to $LOG_FILE"

# 5. Health check
echo ""
echo "[6/6] Health check (waiting 5s)..."
sleep 5

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}/api/v1/health" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo ""
    echo "=== DEPLOY SUCCESS ==="
    echo "Health check: 200 OK"
    echo "PID: $NEW_PID"
    echo "URL: https://bitcoinsapi.com"
    echo "$(date '+%Y-%m-%d %H:%M:%S') — Deploy complete"

    # Auto-tag release if not already tagged
    echo ""
    echo "[Post-deploy] Checking release tag..."
    VERSION=$(grep -m1 'version' pyproject.toml | sed 's/.*"\(.*\)".*/\1/')
    if ! git rev-parse "v$VERSION" >/dev/null 2>&1; then
        if [[ $(git status --porcelain | wc -l | tr -d ' ') -eq 0 ]]; then
            git tag -a "v$VERSION" -m "Release v$VERSION — $(date '+%Y-%m-%d')"
            echo "  Tagged v$VERSION"
        else
            echo "  Skipping tag (uncommitted changes)"
        fi
    else
        echo "  Already tagged v$VERSION"
    fi

    # Submit updated pages to search engines via IndexNow
    echo ""
    echo "[Post-deploy] Submitting pages to IndexNow..."
    bash "$API_DIR/scripts/submit_indexnow.sh" 2>/dev/null && echo "  IndexNow submitted." || echo "  IndexNow submission failed (non-blocking)."
else
    echo ""
    echo "=== DEPLOY FAILED ==="
    echo "Health check returned HTTP $HTTP_CODE"
    echo "Check logs: $LOG_FILE"
    tail -20 "$LOG_FILE" 2>/dev/null || true
    exit 1
fi
