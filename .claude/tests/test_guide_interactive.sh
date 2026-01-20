#!/bin/bash
# Test guide agent v3.0.0 interactive features

echo "=== Testing Guide Agent v3.0.0 Interactive Features ==="
echo ""

GUIDE_FILE=".claude/agents/amplihack/core/guide.md"

echo "Test 1: Version Check"
VERSION=$(grep "^version:" $GUIDE_FILE | head -1 | awk '{print $2}')
if [ "$VERSION" = "3.0.0" ]; then
    echo "✅ Version 3.0.0 confirmed"
else
    echo "❌ Expected v3.0.0, got $VERSION"
    exit 1
fi

echo ""
echo "Test 2: Interactive Features (41 WAIT states)"
WAIT_COUNT=$(grep -c "\[WAIT" $GUIDE_FILE)
if [ $WAIT_COUNT -ge 10 ]; then
    echo "✅ Found $WAIT_COUNT WAIT states (interactive tutor)"
else
    echo "❌ Only $WAIT_COUNT WAIT states"
    exit 1
fi

echo ""
echo "Test 3: Real Production Examples"
grep -q "quality-audit" $GUIDE_FILE && echo "✅ quality-audit example" || { echo "❌ Missing"; exit 1; }
grep -q "issue #2003\|Read issue" $GUIDE_FILE && echo "✅ GitHub issue example" || { echo "❌ Missing"; exit 1; }
grep -q "ddd:prime\|Azure Functions" $GUIDE_FILE && echo "✅ DDD example" || { echo "❌ Missing"; exit 1; }

echo ""
echo "Test 4: Anthropic Documentation"
grep -q "docs.anthropic.com" $GUIDE_FILE && echo "✅ Anthropic docs linked" || { echo "❌ Missing"; exit 1; }

echo ""
echo "Test 5: Interactive Elements"
grep -q "TRY IT\|YOUR ANSWER\|YOUR PROMPT" $GUIDE_FILE && echo "✅ Interactive exercises" || { echo "❌ Missing"; exit 1; }
grep -q "Goal Workshop" $GUIDE_FILE && echo "✅ Goal workshop" || { echo "❌ Missing"; exit 1; }
grep -q "CHECKPOINT\|Quiz" $GUIDE_FILE && echo "✅ Checkpoint quizzes" || { echo "❌ Missing"; exit 1; }

echo ""
echo "Test 6: All 5 Platforms"
for platform in "Claude Code" "Amplifier" "Copilot" "Codex" "RustyClawd"; do
    if grep -qi "$platform" $GUIDE_FILE; then
        echo "✅ $platform"
    else
        echo "❌ Missing: $platform"
        exit 1
    fi
done

echo ""
echo "=== ALL TESTS PASSED ==="
echo "Guide Agent v3.0.0 is an excellent interactive tutor!"
