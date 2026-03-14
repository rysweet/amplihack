#!/bin/bash
# Pre-push hook: Prevent direct pushes to main branch.
# Install: cp this file to .git/hooks/pre-push && chmod +x .git/hooks/pre-push
#
# This is a LOCAL safety net. GitHub's enforce_admins setting is the
# server-side enforcement. This hook catches mistakes before they
# even leave the machine.

PROTECTED_BRANCH="main"

while read local_ref local_sha remote_ref remote_sha; do
    if echo "$remote_ref" | grep -q "refs/heads/${PROTECTED_BRANCH}$"; then
        echo ""
        echo "🚫 BLOCKED: Direct push to '${PROTECTED_BRANCH}' is not allowed."
        echo ""
        echo "   You must create a branch and open a pull request."
        echo ""
        echo "   Quick fix:"
        echo "     git checkout -b feat/my-change"
        echo "     git push -u origin feat/my-change"
        echo "     gh pr create"
        echo ""
        exit 1
    fi
done

exit 0
