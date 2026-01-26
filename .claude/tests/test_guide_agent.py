"""Test guide agent tutorial system - Simple Python test that actually runs"""

import subprocess
import sys


def test_guide_agent_content():
    """Verify guide agent file has v3.0.0 content with all interactive enhancements"""
    with open(".claude/agents/amplihack/core/guide.md") as f:
        content = f.read()

    # Version check
    assert "version: 3.0.0" in content, "Should be v3.0.0 (interactive tutor version)"

    # Interactive features
    assert "[WAIT" in content, "Should have WAIT states for interactivity"
    assert content.count("[WAIT") >= 10, (
        f"Should have 10+ WAIT states, found {content.count('[WAIT')}"
    )

    # Tutorial sections present (actual section headers from file)
    assert "Workflow Selection" in content, "Should have Workflow Selection section"
    assert "Agent Discovery" in content, "Should have Agent Discovery section"
    assert "Skills Library" in content, "Should have Skills Library section"
    assert "Prompt Engineering" in content, "Should have Prompting section"
    assert "Hook System" in content, "Should have Hooks section"
    assert "Goal Workshop" in content, "Should have Goal Workshop section"
    assert "Continuous Work Mode" in content, "Should have Continuous Work section"

    # Real examples (Gap 3 fixed)
    assert "quality-audit" in content, "Should have quality-audit example"
    assert "issue #2003" in content or "Read issue" in content, "Should have GitHub issue example"
    assert "ddd:prime" in content or "Document-Driven" in content, "Should have DDD example"

    # Anthropic docs (Gap 1 fixed)
    assert "docs.anthropic.com" in content, "Should link to Anthropic docs"
    assert "prompt-engineering" in content or "prompt engineering" in content, (
        "Should reference prompt engineering"
    )

    # Goal workshop (Gap 2 fixed)
    assert "Goal:" in content and "Constraints" in content, "Should have goal template"

    # Platforms
    platforms = ["Claude Code", "Amplifier", "Copilot", "Codex", "RustyClawd"]
    for platform in platforms:
        assert platform in content, f"Should mention {platform}"

    # Zero-BS compliance (exclude TODOs in examples/commands)
    import re

    # Check for TODO/FIXME as standalone items, not in code examples
    todo_pattern = r"^(?!.*```|.*amplihack.*TODO).*\b(TODO|FIXME)\b"
    todo_matches = re.findall(todo_pattern, content, re.MULTILINE | re.IGNORECASE)
    assert len(todo_matches) == 0, f"Should have no TODO placeholders (found {len(todo_matches)})"
    assert "Coming soon" not in content, "Should have no 'Coming soon' placeholders"
    assert "TBD" not in content or "TBD" in "amplihack", "Should have no TBD placeholders"

    print("✅ All content verification tests passed")
    return True


def test_guide_agent_invocation():
    """Test that guide agent can be invoked (requires API key)"""
    # Simple smoke test - just verify amplihack CLI works
    result = subprocess.run(["amplihack", "--version"], capture_output=True, text=True, timeout=5)

    assert result.returncode == 0, "amplihack CLI should work"
    print(f"✅ amplihack CLI works: {result.stdout.strip()}")
    return True


if __name__ == "__main__":
    print("Testing Guide Agent v2.0.0...")
    print()

    try:
        test_guide_agent_content()
        print()
        test_guide_agent_invocation()
        print()
        print("🎉 All tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
