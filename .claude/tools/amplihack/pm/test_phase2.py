#!/usr/bin/env python3
"""Quick test script for PM Architect Phase 2 commands.

Tests:
- intelligence module imports
- cmd_suggest basic functionality
- cmd_prepare basic functionality
"""

import sys
from pathlib import Path
import tempfile
import shutil

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pm.state import PMStateManager
from pm.cli import cmd_init, cmd_add, cmd_suggest, cmd_prepare


def test_phase2():
    """Test Phase 2 commands end-to-end."""
    # Create temp directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        print(f"Testing in: {project_root}")

        # Initialize PM
        print("\n1. Testing /pm:init...")
        # Mock user input for initialization
        import io
        old_stdin = sys.stdin
        sys.stdin = io.StringIO("\n1\nGoal 1\nGoal 2\n\n2\n")

        try:
            result = cmd_init(project_root)
            assert result == 0, "pm:init failed"
            print("✅ /pm:init passed")
        finally:
            sys.stdin = old_stdin

        # Add some backlog items
        print("\n2. Testing /pm:add...")
        manager = PMStateManager(project_root)

        # Add HIGH priority feature
        result = cmd_add(
            title="Add authentication API",
            priority="HIGH",
            description="Implement JWT-based auth with login/logout endpoints",
            estimated_hours=4,
            tags=["api", "auth"],
            project_root=project_root,
        )
        assert result == 0, "pm:add failed"
        print("✅ Added BL-001: High priority feature")

        # Add MEDIUM priority bug
        result = cmd_add(
            title="Fix login validation bug",
            priority="MEDIUM",
            description="Login accepts empty passwords",
            estimated_hours=1,
            tags=["bug"],
            project_root=project_root,
        )
        assert result == 0, "pm:add failed"
        print("✅ Added BL-002: Medium priority bug")

        # Add LOW priority refactor
        result = cmd_add(
            title="Refactor user service",
            priority="LOW",
            description="Clean up user service code",
            estimated_hours=3,
            tags=["refactor"],
            project_root=project_root,
        )
        assert result == 0, "pm:add failed"
        print("✅ Added BL-003: Low priority refactor")

        # Test /pm:suggest
        print("\n3. Testing /pm:suggest...")
        result = cmd_suggest(project_root=project_root)
        assert result == 0, "pm:suggest failed"
        print("✅ /pm:suggest passed")

        # Test /pm:prepare
        print("\n4. Testing /pm:prepare...")
        result = cmd_prepare(
            backlog_id="BL-001",
            agent="builder",
            project_root=project_root,
        )
        assert result == 0, "pm:prepare failed"
        print("✅ /pm:prepare passed")

        print("\n" + "=" * 60)
        print("✅ ALL PHASE 2 TESTS PASSED")
        print("=" * 60)


if __name__ == "__main__":
    try:
        test_phase2()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
