#!/bin/bash
set -e

vault_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$vault_root"

echo "=== SYNCING VAULT ==="

# 1. Git pull
echo ""
echo "--- Git Status ---"
if ! git pull --ff-only; then
    echo "Vault sync failed. Resolve the Git error above before processing tasks." >&2
    exit 1
fi
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
TODOS=$(grep -En '^[[:space:]]*[-*][[:space:]]+\[ \].*@Claude' USER.md IDEAS.md 2>/dev/null || true)
if [ -n "$TODOS" ]; then
    echo "$TODOS"
    echo ""
    echo "ACTION REQUIRED: Complete the @Claude tasks above before proceeding."
else
    echo "(No @Claude todos found)"
fi
