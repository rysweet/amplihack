#!/usr/bin/env python3
"""Phase 3 manual test script.

Tests:
1. Multiple concurrent workstreams (up to 5)
2. Capacity management
3. Coordination analysis
4. Stall detection
5. Multi-project dashboard

Run from project root:
    python .claude/tools/amplihack/pm/test_phase3.py
"""

import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Add module to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pm.state import PMStateManager, BacklogItem, WorkstreamState
from pm.workstream import WorkstreamManager, WorkstreamMonitor
from pm.cli import cmd_init, cmd_add, cmd_coordinate, cmd_status


def test_multiple_workstreams():
    """Test 1: Multiple concurrent workstreams."""
    print("=" * 60)
    print("TEST 1: Multiple Concurrent Workstreams")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Initialize PM
        manager = PMStateManager(project_root)
        manager.initialize(
            project_name="test-project",
            project_type="cli-tool",
            primary_goals=["Test Phase 3"],
            quality_bar="balanced",
        )

        # Add 6 backlog items
        for i in range(1, 7):
            manager.add_backlog_item(
                title=f"Task {i}",
                priority="HIGH" if i <= 3 else "MEDIUM",
                description=f"Description for task {i}",
                tags=["test", f"task-{i}"],
            )

        # Create 3 workstreams (should succeed)
        for i in range(1, 4):
            ws = manager.create_workstream(f"BL-{i:03d}", agent="builder")
            print(f"✓ Created workstream {ws.id} for {ws.title}")

        # Check capacity
        active = manager.get_active_workstreams()
        print(f"\n✓ Active workstreams: {len(active)}/5")
        assert len(active) == 3, "Should have 3 active workstreams"

        # Try to create 2 more (should succeed - total 5)
        for i in range(4, 6):
            ws = manager.create_workstream(f"BL-{i:03d}", agent="builder")
            print(f"✓ Created workstream {ws.id} for {ws.title}")

        # Check at capacity
        active = manager.get_active_workstreams()
        print(f"\n✓ Active workstreams: {len(active)}/5 (AT CAPACITY)")
        assert len(active) == 5, "Should have 5 active workstreams"

        # Try to create 6th (should fail)
        can_start, reason = manager.can_start_workstream()
        print(f"\n✓ Cannot start 6th workstream: {reason}")
        assert not can_start, "Should not be able to start 6th workstream"

        print("\n✅ TEST 1 PASSED: Multiple workstreams working correctly")


def test_capacity_management():
    """Test 2: Capacity management."""
    print("\n" + "=" * 60)
    print("TEST 2: Capacity Management")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        manager = PMStateManager(project_root)
        manager.initialize(
            project_name="capacity-test",
            project_type="library",
            primary_goals=["Test capacity"],
            quality_bar="strict",
        )

        # Add items
        for i in range(1, 6):
            manager.add_backlog_item(title=f"Item {i}")

        # Check counts
        counts = manager.get_workstream_count()
        print(f"✓ Initial counts: {counts}")
        assert counts["RUNNING"] == 0

        # Create 3 workstreams
        for i in range(1, 4):
            manager.create_workstream(f"BL-{i:03d}")

        counts = manager.get_workstream_count()
        print(f"✓ After creating 3: {counts}")
        assert counts["RUNNING"] == 3

        # Complete one
        manager.complete_workstream("ws-001", success=True)
        counts = manager.get_workstream_count()
        print(f"✓ After completing 1: {counts}")
        assert counts["RUNNING"] == 2
        assert counts["COMPLETED"] == 1

        # Can start another now
        can_start, reason = manager.can_start_workstream()
        print(f"✓ Can start again: {can_start} - {reason}")
        assert can_start

        print("\n✅ TEST 2 PASSED: Capacity management working")


def test_coordination_analysis():
    """Test 3: Coordination analysis."""
    print("\n" + "=" * 60)
    print("TEST 3: Coordination Analysis")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        manager = PMStateManager(project_root)
        manager.initialize(
            project_name="coordination-test",
            project_type="web-service",
            primary_goals=["Test coordination"],
            quality_bar="balanced",
        )

        # Add items with dependencies and overlapping tags
        bl1 = manager.add_backlog_item(
            title="Foundation work",
            tags=["backend", "api"],
        )
        bl2 = manager.add_backlog_item(
            title="Dependent work",
            tags=["backend", "tests"],
        )
        bl3 = manager.add_backlog_item(
            title="Conflicting work",
            tags=["backend", "api"],  # Same tags as bl1
        )

        # Create workstreams
        ws1 = manager.create_workstream("BL-001")
        ws2 = manager.create_workstream("BL-002")
        ws3 = manager.create_workstream("BL-003")

        # Add dependency: ws2 depends on ws1
        manager.update_workstream("ws-002", dependencies=["BL-001"])

        # Run coordination analysis
        monitor = WorkstreamMonitor(manager)
        analysis = monitor.analyze_coordination()

        print(f"✓ Active workstreams: {len(analysis.active_workstreams)}")
        print(f"✓ Dependencies detected: {len(analysis.dependencies)}")
        print(f"✓ Conflicts detected: {len(analysis.conflicts)}")
        print(f"✓ Execution order: {analysis.execution_order}")
        print(f"✓ Recommendations: {len(analysis.recommendations)}")

        assert len(analysis.active_workstreams) == 3
        assert len(analysis.dependencies) >= 1, "Should detect dependency"
        assert len(analysis.conflicts) >= 1, "Should detect conflict"

        print("\n✅ TEST 3 PASSED: Coordination analysis working")


def test_stall_detection():
    """Test 4: Stall detection."""
    print("\n" + "=" * 60)
    print("TEST 4: Stall Detection")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        manager = PMStateManager(project_root)
        manager.initialize(
            project_name="stall-test",
            project_type="cli-tool",
            primary_goals=["Test stalls"],
            quality_bar="relaxed",
        )

        # Add item and create workstream
        manager.add_backlog_item(title="Task 1")
        ws = manager.create_workstream("BL-001")

        # Simulate old last_activity (stalled)
        old_time = (datetime.utcnow() - timedelta(minutes=45)).isoformat() + "Z"
        manager.update_workstream("ws-001", last_activity=old_time)

        # Detect stalls
        monitor = WorkstreamMonitor(manager)
        stalled = monitor.detect_stalls()

        print(f"✓ Stalled workstreams: {len(stalled)}")
        if stalled:
            print(f"  - {stalled[0].id}: {stalled[0].title}")

        assert len(stalled) == 1, "Should detect 1 stalled workstream"

        # Check health
        health = monitor.get_workstream_health("ws-001")
        print(f"✓ Health status: {health['status']}")
        print(f"✓ Issues: {health['issues']}")

        assert health["status"] == "STALLED"

        print("\n✅ TEST 4 PASSED: Stall detection working")


def test_multi_project_dashboard():
    """Test 5: Multi-project dashboard."""
    print("\n" + "=" * 60)
    print("TEST 5: Multi-Project Dashboard")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create 3 projects
        for i in range(1, 4):
            project_dir = root / f"project-{i}"
            project_dir.mkdir()

            manager = PMStateManager(project_dir)
            manager.initialize(
                project_name=f"Project {i}",
                project_type="cli-tool",
                primary_goals=[f"Goal {i}"],
                quality_bar="balanced",
            )

            # Add some items
            for j in range(1, 3):
                manager.add_backlog_item(title=f"Task {j}")

            # Create workstream for first 2 projects
            if i <= 2:
                manager.create_workstream("BL-001")

        # Check multi-project view works
        from pm.cli import format_multi_project_dashboard

        dashboard = format_multi_project_dashboard(root)
        print(dashboard)

        assert "Project 1" in dashboard
        assert "Project 2" in dashboard
        assert "Project 3" in dashboard

        print("\n✅ TEST 5 PASSED: Multi-project dashboard working")


def run_all_tests():
    """Run all Phase 3 tests."""
    print("\n" + "=" * 60)
    print("PM ARCHITECT PHASE 3 TEST SUITE")
    print("=" * 60 + "\n")

    try:
        test_multiple_workstreams()
        test_capacity_management()
        test_coordination_analysis()
        test_stall_detection()
        test_multi_project_dashboard()

        print("\n" + "=" * 60)
        print("🎉 ALL PHASE 3 TESTS PASSED")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
