#!/bin/bash

echo "=== Gang of Four Design Patterns Skill Verification ==="
echo ""

# Check main skill file
echo "1. Checking SKILL.md..."
if [ -f ".claude/skills/design-patterns-expert/SKILL.md" ]; then
    lines=$(wc -l < .claude/skills/design-patterns-expert/SKILL.md)
    echo "   ✓ SKILL.md exists ($lines lines)"
else
    echo "   ✗ SKILL.md missing"
    exit 1
fi

# Check README
echo "2. Checking README.md..."
if [ -f ".claude/skills/design-patterns-expert/README.md" ]; then
    lines=$(wc -l < .claude/skills/design-patterns-expert/README.md)
    echo "   ✓ README.md exists ($lines lines)"
else
    echo "   ✗ README.md missing"
    exit 1
fi

# Check examples
echo "3. Checking examples directory..."
example_count=$(find .claude/skills/design-patterns-expert/examples -name "*.md" | wc -l)
if [ "$example_count" -ge 5 ]; then
    echo "   ✓ Found $example_count example files (required: ≥5)"
else
    echo "   ✗ Only $example_count examples found (required: ≥5)"
    exit 1
fi

# Check pattern coverage
echo "4. Checking pattern coverage..."
pattern_count=$(grep -c "^#### " .claude/skills/design-patterns-expert/SKILL.md)
if [ "$pattern_count" -ge 23 ]; then
    echo "   ✓ Found $pattern_count pattern entries (required: 23)"
else
    echo "   ✗ Only $pattern_count patterns found (required: 23)"
    exit 1
fi

# Check activation triggers
echo "5. Checking activation triggers..."
trigger_count=$(grep -A 60 "^activation_triggers:" .claude/skills/design-patterns-expert/SKILL.md | grep -c '  - "')
if [ "$trigger_count" -ge 40 ]; then
    echo "   ✓ Found $trigger_count activation triggers"
else
    echo "   ✗ Only $trigger_count triggers found"
    exit 1
fi

# Check for TODOs or placeholders
echo "6. Checking for placeholders/TODOs..."
todo_count=$(grep -i "TODO\|PLACEHOLDER\|FIXME\|XXX" .claude/skills/design-patterns-expert/SKILL.md | wc -l)
if [ "$todo_count" -eq 0 ]; then
    echo "   ✓ No TODOs or placeholders found"
else
    echo "   ⚠ Found $todo_count TODOs/placeholders"
fi

# Check YAML frontmatter
echo "7. Checking YAML frontmatter..."
if head -1 .claude/skills/design-patterns-expert/SKILL.md | grep -q "^---$"; then
    echo "   ✓ YAML frontmatter present"
else
    echo "   ✗ YAML frontmatter missing"
    exit 1
fi

echo ""
echo "=== Verification Complete ==="
echo "All checks passed! The skill is ready for use."
