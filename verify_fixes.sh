#!/bin/bash
# Verify all 50 fix branches exist and have commits

echo "Verifying 50 Fix Branches"
echo "=========================="
echo ""

MISSING=0
SUCCESS=0

for i in {1..50}; do
    BRANCH="origin/fix/specific-$i"
    if git branch -r | grep -q "$BRANCH"; then
        echo "✓ Fix $i: Branch exists"
        SUCCESS=$((SUCCESS + 1))
    else
        echo "✗ Fix $i: Branch MISSING"
        MISSING=$((MISSING + 1))
    fi
done

echo ""
echo "=========================="
echo "Summary"
echo "=========================="
echo "Total Expected: 50"
echo "Found: $SUCCESS"
echo "Missing: $MISSING"
echo ""

if [ $MISSING -eq 0 ]; then
    echo "✓ ALL 50 FIXES VERIFIED!"
    exit 0
else
    echo "✗ Some fixes are missing"
    exit 1
fi
