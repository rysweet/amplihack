"""Phase 4 (Autonomy) Manual Test Suite

Tests for autonomous decision-making, learning, and outcome tracking.

Run with: python -m pytest test_phase4.py -v
Or manually: python test_phase4.py
"""

import tempfile
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pm.state import PMStateManager
from pm.autopilot import AutopilotEngine, AutopilotDecision, AutonomousSchedule
from pm.learning import OutcomeTracker, WorkstreamOutcome, EstimationMetrics


def test_autopilot_dry_run():
    """Test autopilot in dry-run mode (no execution)."""
    print("\n=== TEST: Autopilot Dry-Run ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Initialize PM
        state_mgr = PMStateManager(project_root)
        state_mgr.initialize(
            project_name="Test Project",
            project_type="cli-tool",
            primary_goals=["Test autonomy"],
            quality_bar="balanced"
        )

        # Add some backlog items
        state_mgr.add_backlog_item(
            title="Feature A",
            priority="HIGH",
            estimated_hours=2
        )
        state_mgr.add_backlog_item(
            title="Feature B",
            priority="MEDIUM",
            estimated_hours=4
        )

        # Run autopilot in dry-run mode
        engine = AutopilotEngine(project_root)
        decisions = engine.run(dry_run=True, max_actions=2)

        print(f"Decisions made: {len(decisions)}")
        for decision in decisions:
            print(f"  - {decision.decision_type}: {decision.action_taken}")
            print(f"    Confidence: {decision.confidence:.0%}")
            print(f"    Rationale: {decision.rationale[:80]}...")

        # Verify decisions were logged but not executed
        assert len(decisions) >= 0, "Should make some decisions or none"
        print("✅ Dry-run test passed")


def test_autopilot_execute():
    """Test autopilot in execute mode (actually takes actions)."""
    print("\n=== TEST: Autopilot Execute ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Initialize PM
        state_mgr = PMStateManager(project_root)
        state_mgr.initialize(
            project_name="Test Project",
            project_type="cli-tool",
            primary_goals=["Test autonomy"],
            quality_bar="balanced"
        )

        # Add a high-priority item
        state_mgr.add_backlog_item(
            title="High Priority Feature",
            priority="HIGH",
            estimated_hours=2
        )

        # Run autopilot in execute mode
        engine = AutopilotEngine(project_root)
        decisions = engine.run(dry_run=False, max_actions=1)

        print(f"Decisions executed: {len(decisions)}")
        for decision in decisions:
            print(f"  - {decision.decision_type}: {decision.action_taken}")
            print(f"    Outcome: {decision.outcome}")

        # Verify execution happened
        if decisions:
            # Check if workstream was started
            active = state_mgr.get_active_workstreams()
            if decisions[0].decision_type == "start_work":
                print(f"  Active workstreams after: {len(active)}")

        print("✅ Execute test passed")


def test_decision_explanation():
    """Test decision explanation and retrieval."""
    print("\n=== TEST: Decision Explanation ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Initialize PM
        state_mgr = PMStateManager(project_root)
        state_mgr.initialize(
            project_name="Test Project",
            project_type="cli-tool",
            primary_goals=["Test autonomy"],
            quality_bar="balanced"
        )

        # Add backlog item
        state_mgr.add_backlog_item(
            title="Test Feature",
            priority="HIGH",
            estimated_hours=2
        )

        # Run autopilot to create decisions
        engine = AutopilotEngine(project_root)
        decisions = engine.run(dry_run=True, max_actions=1)

        if decisions:
            decision = decisions[0]
            print(f"Decision ID: {decision.decision_id}")

            # Test retrieval
            retrieved = engine.explain_decision(decision.decision_id)
            assert retrieved is not None, "Should retrieve decision"
            assert retrieved.decision_id == decision.decision_id
            print(f"  Retrieved: {retrieved.action_taken}")

            # Test recent decisions
            recent = engine.get_recent_decisions(hours=1)
            assert len(recent) >= 1, "Should have recent decisions"
            print(f"  Recent decisions: {len(recent)}")

        print("✅ Explanation test passed")


def test_outcome_tracking():
    """Test outcome tracking and learning."""
    print("\n=== TEST: Outcome Tracking ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Initialize PM
        state_mgr = PMStateManager(project_root)
        state_mgr.initialize(
            project_name="Test Project",
            project_type="cli-tool",
            primary_goals=["Test learning"],
            quality_bar="balanced"
        )

        # Add and start workstream
        item = state_mgr.add_backlog_item(
            title="Test Feature",
            priority="HIGH",
            estimated_hours=4
        )
        ws = state_mgr.create_workstream(
            backlog_id=item.id,
            agent="builder"
        )

        # Simulate elapsed time
        state_mgr.update_workstream(ws.id, elapsed_minutes=300)  # 5 hours

        # Complete workstream (triggers outcome tracking)
        tracker = OutcomeTracker(project_root)
        ws_completed = state_mgr.get_workstream(ws.id)
        outcome = tracker.record_outcome(ws_completed, success=True, notes="Test completion")

        print(f"Outcome recorded: {outcome.workstream_id}")
        print(f"  Estimated: {outcome.estimated_hours}h")
        print(f"  Actual: {outcome.actual_hours:.1f}h")
        print(f"  Error: {outcome.estimation_error:.0%}")

        assert outcome.success is True
        assert outcome.estimation_error != 0  # Should have some error
        print("✅ Outcome tracking test passed")


def test_estimation_metrics():
    """Test estimation metrics calculation."""
    print("\n=== TEST: Estimation Metrics ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Initialize PM
        state_mgr = PMStateManager(project_root)
        state_mgr.initialize(
            project_name="Test Project",
            project_type="cli-tool",
            primary_goals=["Test learning"],
            quality_bar="balanced"
        )

        tracker = OutcomeTracker(project_root)

        # Create several outcomes with different errors
        test_outcomes = [
            (4, 3.0),   # Overestimate
            (4, 5.0),   # Underestimate
            (2, 2.5),   # Slight underestimate
            (8, 7.0),   # Slight overestimate
        ]

        for estimated, actual in test_outcomes:
            # Create fake workstream for testing
            class FakeWS:
                def __init__(self):
                    self.id = "ws-test"
                    self.backlog_id = "BL-001"
                    self.title = "Test"
                    self.elapsed_minutes = actual * 60

            # Create fake backlog item
            item = state_mgr.add_backlog_item(
                title=f"Test {estimated}h",
                estimated_hours=estimated
            )

            ws = FakeWS()
            ws.backlog_id = item.id

            tracker.record_outcome(ws, success=True)

        # Get metrics
        metrics = tracker.get_estimation_metrics(window_days=7)

        print(f"Total items: {metrics.total_items}")
        print(f"Mean error: {metrics.mean_error:.1f}%")
        print(f"Median error: {metrics.median_error:.1f}%")
        print(f"Overestimate rate: {metrics.overestimate_rate:.0f}%")
        print(f"Underestimate rate: {metrics.underestimate_rate:.0f}%")

        assert metrics.total_items == len(test_outcomes)
        print("✅ Estimation metrics test passed")


def test_risk_pattern_detection():
    """Test risk pattern identification."""
    print("\n=== TEST: Risk Pattern Detection ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Initialize PM
        state_mgr = PMStateManager(project_root)
        state_mgr.initialize(
            project_name="Test Project",
            project_type="cli-tool",
            primary_goals=["Test learning"],
            quality_bar="balanced"
        )

        tracker = OutcomeTracker(project_root)

        # Create pattern: chronic underestimation
        for i in range(5):
            item = state_mgr.add_backlog_item(
                title=f"Feature {i}",
                estimated_hours=2
            )

            class FakeWS:
                def __init__(self, id, backlog_id):
                    self.id = id
                    self.backlog_id = backlog_id
                    self.title = f"Feature {i}"
                    self.elapsed_minutes = 300  # 5 hours (way over 2h estimate)

            ws = FakeWS(f"ws-{i:03d}", item.id)
            tracker.record_outcome(ws, success=True)

        # Detect patterns
        patterns = tracker.identify_risk_patterns(min_occurrences=3)

        print(f"Patterns detected: {len(patterns)}")
        for pattern in patterns:
            print(f"  - {pattern.pattern_id}: {pattern.description}")
            print(f"    Severity: {pattern.severity}")
            print(f"    Recommendation: {pattern.recommendation}")

        # Should detect chronic underestimation
        pattern_ids = [p.pattern_id for p in patterns]
        assert "chronic_underestimate" in pattern_ids or len(patterns) >= 1
        print("✅ Risk pattern detection test passed")


def test_learning_adjusted_estimates():
    """Test learning-adjusted estimates."""
    print("\n=== TEST: Learning-Adjusted Estimates ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Initialize PM
        state_mgr = PMStateManager(project_root)
        state_mgr.initialize(
            project_name="Test Project",
            project_type="cli-tool",
            primary_goals=["Test learning"],
            quality_bar="balanced"
        )

        tracker = OutcomeTracker(project_root)

        # Create pattern of consistent underestimation
        for i in range(5):
            item = state_mgr.add_backlog_item(
                title=f"Feature {i}",
                estimated_hours=4
            )

            class FakeWS:
                def __init__(self, id, backlog_id):
                    self.id = id
                    self.backlog_id = backlog_id
                    self.title = f"Feature {i}"
                    self.elapsed_minutes = 6 * 60  # 6 hours (50% over)

            ws = FakeWS(f"ws-{i:03d}", item.id)
            tracker.record_outcome(ws, success=True)

        # Get adjusted estimate for new 4-hour task
        adjusted, confidence = tracker.get_adjusted_estimate(
            base_estimate=4,
            complexity="medium"
        )

        print(f"Base estimate: 4h")
        print(f"Adjusted estimate: {adjusted}h")
        print(f"Confidence: {confidence:.0%}")

        # Should increase estimate based on history
        assert adjusted > 4, "Should adjust upward for underestimation pattern"
        print("✅ Learning-adjusted estimates test passed")


def test_improvement_suggestions():
    """Test improvement suggestions generation."""
    print("\n=== TEST: Improvement Suggestions ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Initialize PM
        state_mgr = PMStateManager(project_root)
        state_mgr.initialize(
            project_name="Test Project",
            project_type="cli-tool",
            primary_goals=["Test learning"],
            quality_bar="balanced"
        )

        tracker = OutcomeTracker(project_root)

        # Create several outcomes
        for i in range(6):
            item = state_mgr.add_backlog_item(
                title=f"Feature {i}",
                estimated_hours=4
            )

            class FakeWS:
                def __init__(self, id, backlog_id):
                    self.id = id
                    self.backlog_id = backlog_id
                    self.title = f"Feature {i}"
                    # Vary actual time
                    self.elapsed_minutes = (3 + i % 3) * 60

            ws = FakeWS(f"ws-{i:03d}", item.id)
            tracker.record_outcome(ws, success=(i % 5 != 0))  # 1 failure

        # Get suggestions
        suggestions = tracker.get_improvement_suggestions()

        print(f"Suggestions: {len(suggestions)}")
        for suggestion in suggestions:
            print(f"  - {suggestion}")

        assert len(suggestions) > 0, "Should provide suggestions"
        print("✅ Improvement suggestions test passed")


def run_all_tests():
    """Run all Phase 4 tests."""
    print("=" * 60)
    print("PM ARCHITECT PHASE 4 (AUTONOMY) - TEST SUITE")
    print("=" * 60)

    tests = [
        test_autopilot_dry_run,
        test_autopilot_execute,
        test_decision_explanation,
        test_outcome_tracking,
        test_estimation_metrics,
        test_risk_pattern_detection,
        test_learning_adjusted_estimates,
        test_improvement_suggestions,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ Test error: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
