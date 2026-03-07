#!/usr/bin/env bash
# Install git hooks for Satoshi API
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

# Pre-commit: privacy check + trigger matrix advisory
cat > "$HOOKS_DIR/pre-commit" << 'HOOK'
#!/usr/bin/env bash
# Satoshi API pre-commit: privacy enforcer + agent trigger advisory

REPO_ROOT="$(git rev-parse --show-toplevel)"

# 1. Privacy check (blocking)
python "$REPO_ROOT/scripts/privacy_check.py" --hook
if [ $? -ne 0 ]; then
    exit 1
fi

# 2. Agent trigger advisory (non-blocking)
python "$REPO_ROOT/scripts/trigger_check.py" 2>/dev/null || true
HOOK

chmod +x "$HOOKS_DIR/pre-commit"
echo "Installed pre-commit hook."
echo "  - Privacy Promise Enforcer (blocking)"
echo "  - Agent Trigger Advisory (non-blocking)"
