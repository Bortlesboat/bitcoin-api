#!/usr/bin/env bash
# Install Satoshi API Watchdog as a Windows Scheduled Task
# Run this once to set up auto-restart every 5 minutes.

set -euo pipefail

TASK_NAME="SatoshiAPIWatchdog"
OLD_TASK_NAME="SatoshiAPI"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -W 2>/dev/null || pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
SCRIPT_PATH="${REPO_DIR}\\scripts\\watchdog-api.sh"
# Git Bash path - adjust if bash is elsewhere
BASH_EXE='C:\Program Files\Git\bin\bash.exe'

echo "=== Satoshi API Watchdog Installer ==="
echo ""

# Verify bash exists at expected path
if [[ ! -f "/c/Program Files/Git/bin/bash.exe" ]]; then
    echo "WARNING: Git Bash not found at $BASH_EXE"
    echo "Checking alternatives..."
    if command -v bash &>/dev/null; then
        actual_bash=$(command -v bash)
        echo "  Found bash at: $actual_bash"
        echo "  You may need to update BASH_EXE in this script."
    fi
    echo ""
fi

# Ensure logs directory exists
mkdir -p "$REPO_DIR/logs"

# Step 1: Delete old broken SatoshiAPI task if it exists
echo "[1/3] Checking for old '$OLD_TASK_NAME' task..."
if schtasks.exe //Query //TN "$OLD_TASK_NAME" > /dev/null 2>&1; then
    echo "  Found old task '$OLD_TASK_NAME' - deleting..."
    schtasks.exe //Delete //TN "$OLD_TASK_NAME" //F > /dev/null 2>&1
    echo "  Deleted."
else
    echo "  No old task found."
fi

# Step 2: Delete existing watchdog task if it exists (for clean reinstall)
echo "[2/3] Creating scheduled task '$TASK_NAME'..."
if schtasks.exe //Query //TN "$TASK_NAME" > /dev/null 2>&1; then
    echo "  Existing task found - replacing..."
    schtasks.exe //Delete //TN "$TASK_NAME" //F > /dev/null 2>&1
fi

# Create the task: run every 5 minutes, starting now
# /SC MINUTE /MO 5 = every 5 minutes
# /RL HIGHEST = run with highest privileges (helps with port binding)
schtasks.exe //Create \
    //TN "$TASK_NAME" \
    //TR "\"$BASH_EXE\" \"$SCRIPT_PATH\"" \
    //SC MINUTE \
    //MO 5 \
    //RL HIGHEST \
    //F

echo "  Task created."

# Step 3: Verify
echo "[3/3] Verifying..."
if schtasks.exe //Query //TN "$TASK_NAME" > /dev/null 2>&1; then
    echo "  Task '$TASK_NAME' is registered."
else
    echo "  ERROR: Task creation may have failed. Check manually with:"
    echo "    schtasks /Query /TN $TASK_NAME /V"
    exit 1
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "The watchdog will:"
echo "  - Run every 5 minutes"
echo "  - Check if port 9332 is listening"
echo "  - Hit /api/v1/health to verify the API responds"
echo "  - Auto-restart if down or zombie"
echo "  - Log all restarts to: logs/watchdog.log"
echo "  - API stdout/stderr goes to: logs/api.log"
echo ""
echo "Manual commands:"
echo "  Run watchdog now:   bash scripts/watchdog-api.sh"
echo "  Check task status:  schtasks //Query //TN $TASK_NAME //V"
echo "  Delete task:        schtasks //Delete //TN $TASK_NAME //F"
echo "  View restart log:   tail -20 logs/watchdog.log"
echo ""
echo "NOTE: The task runs as the current user. If you need it to run"
echo "whether logged in or not, open Task Scheduler GUI, find"
echo "'$TASK_NAME', and change the security options manually"
echo "(requires entering your password)."
