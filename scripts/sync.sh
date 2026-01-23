#!/bin/bash
set -e

cd "$CLAUDE_PROJECT_DIR" 2>/dev/null || cd "$(dirname "$0")/../.."

echo "=== SYNCING VAULT ==="

# 1. Git pull
echo ""
echo "--- Git Status ---"
git pull origin main 2>&1 || echo "Warning: git pull failed (offline?)"
git status --short

# 2. Read key files and extract @Claude todos
echo ""
echo "--- README ---"
cat README.md 2>/dev/null || echo "(no README.md found)"

echo ""
echo "--- USER ---"
cat USER.md 2>/dev/null || echo "(no USER.md found)"

echo ""
echo "--- IDEAS ---"
cat IDEAS.md 2>/dev/null || echo "(no IDEAS.md found)"

# 3. Check for @Claude mentions
echo ""
echo "=== @CLAUDE TODOS ==="
TODOS=$(grep -n "@Claude" README.md USER.md IDEAS.md 2>/dev/null || true)
if [ -n "$TODOS" ]; then
    echo "$TODOS"
    echo ""
    echo "ACTION REQUIRED: Complete the @Claude tasks above before proceeding."
else
    echo "(No @Claude todos found)"
fi
