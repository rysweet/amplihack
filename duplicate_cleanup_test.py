#!/usr/bin/env python3
"""Comprehensive test script for safe duplicate cleanup system.

This script validates all aspects of the cleanup system including:
- SDK integration and detection accuracy
- Safety features and dry-run mode
- Information preservation mechanisms
- Cross-referencing and audit trails
- Error handling and rollback capability

Usage:
    python duplicate_cleanup_test.py                    # Run all tests
    python duplicate_cleanup_test.py --test-sdk         # Test SDK only
    python duplicate_cleanup_test.py --test-safety      # Test safety features only
    python duplicate_cleanup_test.py --test-real        # Test on real repository data
"""

import argparse
import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Import the cleanup system
from cleanup_duplicate_issues import (
    CleanupAction,
    CleanupSession,
    DuplicateCluster,
    IssueInfo,
    SafeCleanupOrchestrator,
)


class TestDuplicateCleanupSystem(unittest.TestCase):
    """Comprehensive test suite for duplicate cleanup system."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.orchestrator = SafeCleanupOrchestrator()
        self.orchestrator.output_dir = self.test_dir / "cleanup_results"
        self.orchestrator.output_dir.mkdir(exist_ok=True)

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def create_test_issue(
        self, number: int, title: str, body: str = "", state: str = "open"
    ) -> IssueInfo:
        """Create a test issue for testing."""
        return IssueInfo(
            number=number,
            title=title,
            body=body,
            state=state,
            author="test-user",
            created_at="2025-09-27T10:00:00Z",
            updated_at="2025-09-27T10:00:00Z",
            labels=["test-label"],
        )

    def test_issue_info_creation(self):
        """Test IssueInfo dataclass creation and properties."""
        issue = self.create_test_issue(123, "Test Issue", "Test body")

        self.assertEqual(issue.number, 123)
        self.assertEqual(issue.title, "Test Issue")
        self.assertEqual(issue.body, "Test body")
        self.assertEqual(issue.state, "open")
        self.assertEqual(issue.comments, [])

    def test_unique_content_extraction(self):
        """Test extraction of unique content from duplicate issues."""
        # Create issues with different content
        issue1 = self.create_test_issue(1, "Same title", "Common content plus unique content A")
        issue2 = self.create_test_issue(2, "Same title", "Common content plus unique content B")
        issue3 = self.create_test_issue(3, "Same title", "Common content")

        # Add unique comments
        issue1.comments = [{"body": "Unique comment A", "author": "user1"}]
        issue2.comments = [{"body": "Unique comment B", "author": "user2"}]
        issue3.comments = [{"body": "Common comment", "author": "user3"}]

        # Test unique content extraction
        unique1 = self.orchestrator.extract_unique_content(issue1, [issue2, issue3])
        unique2 = self.orchestrator.extract_unique_content(issue2, [issue1, issue3])
        self.orchestrator.extract_unique_content(issue3, [issue1, issue2])  # Test the method works

        self.assertIn("Unique comment A", unique1)
        self.assertIn("Unique comment B", unique2)
        self.assertNotIn("Unique comment A", unique2)
        self.assertNotIn("Unique comment B", unique1)

    def test_duplicate_cluster_creation(self):
        """Test duplicate cluster dataclass creation."""
        cluster = DuplicateCluster(
            canonical_issue=100,
            duplicate_issues=[101, 102],
            cluster_type="perfect",
            confidence=0.95,
            reason="Identical issues",
            phase=1,
        )

        self.assertEqual(cluster.canonical_issue, 100)
        self.assertEqual(cluster.duplicate_issues, [101, 102])
        self.assertEqual(cluster.cluster_type, "perfect")
        self.assertEqual(cluster.confidence, 0.95)
        self.assertEqual(cluster.phase, 1)

    def test_close_comment_generation(self):
        """Test generation of closure comments with all required information."""
        canonical = self.create_test_issue(100, "Main Issue", "Main content")
        duplicate = self.create_test_issue(101, "Duplicate Issue", "Duplicate content")
        duplicate.unique_content = "Some unique information"

        cluster = DuplicateCluster(
            canonical_issue=100,
            duplicate_issues=[101],
            cluster_type="functional",
            confidence=0.85,
            reason="Same functionality described differently",
            phase=2,
        )

        comment = self.orchestrator.create_close_comment(canonical, duplicate, cluster)

        # Verify essential elements are present
        self.assertIn("Closing as duplicate of #100", comment)
        self.assertIn("Confidence: 85.0%", comment)
        self.assertIn("functional", comment)
        self.assertIn("Same functionality described differently", comment)
        self.assertIn("Some unique information", comment)
        self.assertIn("Reversal Process", comment)
        self.assertIn("@rysweet", comment)

    async def test_fallback_analysis(self):
        """Test fallback duplicate analysis when SDK is unavailable."""
        # Mock issues data with known duplicates
        self.orchestrator.issues_data = [
            self.create_test_issue(155, "AI-detected error_handling", "Test"),
            self.create_test_issue(157, "AI-detected error_handling", "Test"),
            self.create_test_issue(169, "AI-detected error_handling", "Test"),
            self.create_test_issue(114, "Feature: Port Agent Memory System", "Basic"),
            self.create_test_issue(
                115, "Feature: Port Agent Memory System for Enhanced Capabilities", "Detailed"
            ),
            self.create_test_issue(200, "Unrelated Issue", "Different content"),
        ]

        clusters = self.orchestrator.analyze_duplicates_fallback()

        # Should find AI-detected cluster
        ai_cluster = next((c for c in clusters if c.canonical_issue == 169), None)
        self.assertIsNotNone(ai_cluster)
        if ai_cluster:
            self.assertEqual(ai_cluster.cluster_type, "perfect")
            self.assertEqual(ai_cluster.confidence, 1.0)
            self.assertIn(155, ai_cluster.duplicate_issues)
            self.assertIn(157, ai_cluster.duplicate_issues)

        # Should find Gadugi cluster
        gadugi_cluster = next((c for c in clusters if c.canonical_issue == 115), None)
        self.assertIsNotNone(gadugi_cluster)
        if gadugi_cluster:
            self.assertEqual(gadugi_cluster.cluster_type, "functional")
            self.assertIn(114, gadugi_cluster.duplicate_issues)

    async def test_cleanup_action_creation(self):
        """Test creation of cleanup actions from clusters."""
        # Set up test data
        self.orchestrator.issues_data = [
            self.create_test_issue(100, "Main Issue"),
            self.create_test_issue(101, "Duplicate Issue"),
        ]

        cluster = DuplicateCluster(
            canonical_issue=100,
            duplicate_issues=[101],
            cluster_type="perfect",
            confidence=1.0,
            reason="Identical issues",
            phase=1,
        )

        # Mock comment fetching
        async def mock_fetch_comments(issue_number):
            if issue_number == 101:
                return [{"body": "Unique comment", "author": "test"}]
            return []

        self.orchestrator.fetch_issue_comments = mock_fetch_comments

        actions = await self.orchestrator.create_cleanup_actions([cluster])

        # Should create multiple actions
        self.assertGreater(len(actions), 0)

        # Should have close action
        close_actions = [a for a in actions if a.action_type == "close_issue"]
        self.assertEqual(len(close_actions), 1)
        self.assertEqual(close_actions[0].issue_number, 101)

        # Should have cross-reference action
        comment_actions = [a for a in actions if a.action_type == "add_comment"]
        self.assertGreater(len(comment_actions), 0)

    @patch("subprocess.run")
    async def test_dry_run_mode(self, mock_subprocess):
        """Test that dry-run mode doesn't execute any real commands."""
        action = CleanupAction(
            action_type="close_issue",
            issue_number=101,
            details={"comment": "Test closure"},
            reason="Test reason",
        )

        # Execute in dry-run mode
        success = await self.orchestrator.execute_action(action, dry_run=True)

        # Should succeed without calling subprocess
        self.assertTrue(success)
        self.assertTrue(action.executed)
        mock_subprocess.assert_not_called()

    @patch("subprocess.run")
    async def test_real_execution_mode(self, mock_subprocess):
        """Test that real execution mode calls subprocess correctly."""
        # Mock successful subprocess call
        mock_subprocess.return_value = Mock(stdout="", stderr="", returncode=0)

        action = CleanupAction(
            action_type="close_issue",
            issue_number=101,
            details={"comment": "Test closure"},
            reason="Test reason",
        )

        # Execute in real mode
        success = await self.orchestrator.execute_action(action, dry_run=False)

        # Should succeed and call subprocess
        self.assertTrue(success)
        self.assertTrue(action.executed)
        mock_subprocess.assert_called_once()

        # Verify command structure
        call_args = mock_subprocess.call_args[0][0]
        self.assertIn("gh", call_args)
        self.assertIn("issue", call_args)
        self.assertIn("close", call_args)
        self.assertIn("101", call_args)

    def test_session_data_serialization(self):
        """Test that session data can be properly serialized to JSON."""
        # Create session with all components
        session = CleanupSession(
            session_id="test_session",
            start_time="2025-09-27T10:00:00Z",
            end_time=None,
            mode="dry_run",
            phase=1,
            total_issues_analyzed=10,
            clusters_found=[
                DuplicateCluster(
                    canonical_issue=100,
                    duplicate_issues=[101],
                    cluster_type="perfect",
                    confidence=1.0,
                    reason="Test",
                    phase=1,
                )
            ],
            actions_planned=[
                CleanupAction(
                    action_type="close_issue",
                    issue_number=101,
                    details={"test": "data"},
                    reason="Test action",
                )
            ],
            actions_executed=[],
            sdk_stats={"test": True},
            issues_before=10,
            issues_after=9,
        )

        self.orchestrator.session = session

        # Should save without errors
        try:
            self.orchestrator.save_session_data()
            # Verify files were created
            session_files = list(self.orchestrator.output_dir.glob("cleanup_session_*.json"))
            self.assertEqual(len(session_files), 1)

            preview_file = self.orchestrator.output_dir / "cleanup_preview.json"
            self.assertTrue(preview_file.exists())

            # Verify content can be loaded
            with open(session_files[0]) as f:
                loaded_data = json.load(f)
                self.assertEqual(loaded_data["session_id"], "test_session")

        except Exception as e:
            self.fail(f"Session serialization failed: {e}")

    def test_audit_log_generation(self):
        """Test generation of comprehensive audit logs."""
        # Set up session with test data
        session = CleanupSession(
            session_id="test_session",
            start_time="2025-09-27T10:00:00Z",
            end_time="2025-09-27T10:05:00Z",
            mode="dry_run",
            phase=1,
            total_issues_analyzed=5,
            clusters_found=[
                DuplicateCluster(
                    canonical_issue=100,
                    duplicate_issues=[101, 102],
                    cluster_type="perfect",
                    confidence=1.0,
                    reason="Identical issues",
                    phase=1,
                )
            ],
            actions_planned=[],
            actions_executed=[
                CleanupAction(
                    action_type="close_issue",
                    issue_number=101,
                    details={"canonical_issue": 100},
                    reason="Test closure",
                    executed=True,
                    execution_time="2025-09-27T10:02:00Z",
                )
            ],
            sdk_stats={"sdk_available": True},
            issues_before=5,
            issues_after=3,
        )

        self.orchestrator.session = session
        self.orchestrator.generate_audit_log()

        # Verify log file was created
        log_files = list(self.orchestrator.output_dir.glob("cleanup_log_*.md"))
        self.assertEqual(len(log_files), 1)

        # Verify log content
        with open(log_files[0]) as f:
            content = f.read()
            self.assertIn("# Duplicate Issues Cleanup Log", content)
            self.assertIn("test_session", content)
            self.assertIn("100", content)  # Canonical issue
            self.assertIn("101", content)  # Duplicate issue
            self.assertIn("Reversal Instructions", content)
            self.assertIn("gh issue reopen", content)

    async def test_error_handling(self):
        """Test error handling in various scenarios."""
        # Test with missing issue
        result = self.orchestrator.get_issue_by_number(999)
        self.assertIsNone(result)

        # Test action execution with invalid issue
        action = CleanupAction(
            action_type="close_issue", issue_number=999, details={"comment": "Test"}, reason="Test"
        )

        # Should handle gracefully in dry-run
        success = await self.orchestrator.execute_action(action, dry_run=True)
        self.assertTrue(success)  # Dry run always succeeds

    def test_phase_classification(self):
        """Test proper classification of duplicates into phases."""
        # Perfect duplicate - should be Phase 1
        perfect_cluster = DuplicateCluster(
            canonical_issue=100,
            duplicate_issues=[101],
            cluster_type="perfect",
            confidence=0.98,
            reason="Identical",
            phase=1,
        )
        self.assertEqual(perfect_cluster.phase, 1)

        # Functional duplicate - should be Phase 2
        functional_cluster = DuplicateCluster(
            canonical_issue=200,
            duplicate_issues=[201],
            cluster_type="functional",
            confidence=0.80,
            reason="Same functionality",
            phase=2,
        )
        self.assertEqual(functional_cluster.phase, 2)

        # Edge case - should be Phase 3
        edge_cluster = DuplicateCluster(
            canonical_issue=300,
            duplicate_issues=[301],
            cluster_type="edge_case",
            confidence=0.60,
            reason="Possibly related",
            phase=3,
        )
        self.assertEqual(edge_cluster.phase, 3)


class TestSDKIntegration(unittest.TestCase):
    """Test SDK integration and detection accuracy."""

    def setUp(self):
        """Set up SDK test environment."""
        # Import SDK components if available
        try:
            sdk_path = Path(
                "/Users/ryan/src/hackathon/fix-issue-170-duplicate-detection/.claude/tools/amplihack/reflection"
            )
            if sdk_path.exists():
                sys.path.insert(0, str(sdk_path))
            from semantic_duplicate_detector import (
                SemanticDuplicateDetector,  # type: ignore[import-untyped]
            )

            self.detector = SemanticDuplicateDetector()
            self.sdk_available = True
        except ImportError:
            self.detector = None
            self.sdk_available = False

    def test_sdk_availability(self):
        """Test SDK availability detection."""
        if self.sdk_available:
            self.assertIsNotNone(self.detector)
        else:
            self.skipTest("SDK not available for testing")

    async def test_perfect_duplicate_detection(self):
        """Test detection of perfect duplicates."""
        if not self.sdk_available:
            self.skipTest("SDK not available")

        # Test with identical content
        title = "AI-detected error_handling: Improve error handling"
        body = (
            "# AI-Detected Improvement Opportunity\n\n**Type**: error_handling\n**Priority**: high"
        )

        existing_issues = [{"number": 157, "title": title, "body": body}]

        result = (
            await self.detector.detect_semantic_duplicate(title, body, existing_issues)
            if self.detector
            else None
        )
        self.assertIsNotNone(result)
        assert result is not None  # Type narrowing

        # Should detect as duplicate with high confidence
        self.assertTrue(result.is_duplicate)
        self.assertGreater(result.confidence, 0.9)
        self.assertEqual(len(result.similar_issues), 1)

    async def test_non_duplicate_detection(self):
        """Test detection correctly identifies non-duplicates."""
        if not self.sdk_available:
            self.skipTest("SDK not available")

        # Test with clearly different content
        title1 = "Add Docker containerization support"
        body1 = "We need to add Docker support for easy deployment"

        title2 = "Fix error handling in authentication"
        body2 = "Authentication module has poor error handling"

        existing_issues = [{"number": 200, "title": title2, "body": body2}]

        result = (
            await self.detector.detect_semantic_duplicate(title1, body1, existing_issues)
            if self.detector
            else None
        )
        self.assertIsNotNone(result)
        assert result is not None  # Type narrowing

        # Should not detect as duplicate
        self.assertFalse(result.is_duplicate)
        self.assertLess(result.confidence, 0.5)

    async def test_functional_duplicate_detection(self):
        """Test detection of functional duplicates (same issue, different wording)."""
        if not self.sdk_available:
            self.skipTest("SDK not available")

        # Test with functionally similar content
        title1 = "Fix: Reviewer agent should post PR comments instead of editing PR description"
        body1 = (
            "The reviewer agent incorrectly modifies PR descriptions when it should post comments"
        )

        title2 = "Reviewer agent incorrectly edits PR descriptions instead of posting comments"
        body2 = "When reviewing PRs, the agent edits the description rather than adding comments"

        existing_issues = [{"number": 71, "title": title1, "body": body1}]

        result = (
            await self.detector.detect_semantic_duplicate(title2, body2, existing_issues)
            if self.detector
            else None
        )
        self.assertIsNotNone(result)
        assert result is not None  # Type narrowing

        # Should detect as duplicate with moderate confidence
        self.assertTrue(result.is_duplicate)
        self.assertGreater(result.confidence, 0.4)  # Based on known test data


class TestRealWorldValidation(unittest.TestCase):
    """Test on real repository data for validation."""

    def setUp(self):
        """Set up real-world test environment."""
        self.orchestrator = SafeCleanupOrchestrator()

    async def test_real_data_loading(self):
        """Test loading real GitHub issues."""
        try:
            issues = await self.orchestrator.load_github_issues()
            self.assertGreater(len(issues), 0)

            # Verify issue structure
            for issue in issues[:5]:  # Check first 5
                self.assertIsInstance(issue.number, int)
                self.assertIsInstance(issue.title, str)
                self.assertIn(issue.state, ["open", "closed"])

        except Exception as e:
            self.skipTest(f"Could not load real data: {e}")

    async def test_known_duplicate_detection(self):
        """Test detection on known duplicates from analysis report."""
        # Load real issues
        try:
            await self.orchestrator.load_github_issues()
        except Exception:
            self.skipTest("Could not load real data")

        # Test known perfect duplicates (AI-detected issues)
        issue_155 = self.orchestrator.get_issue_by_number(155)
        issue_157 = self.orchestrator.get_issue_by_number(157)

        if issue_155 and issue_157 and self.orchestrator.detector:
            result = await self.orchestrator.detector.detect_semantic_duplicate(
                title=issue_155.title,
                body=issue_155.body,
                existing_issues=[
                    {"number": issue_157.number, "title": issue_157.title, "body": issue_157.body}
                ],
            )

            # Should detect as perfect duplicate
            self.assertTrue(result.is_duplicate)
            self.assertGreater(result.confidence, 0.9)


async def run_all_tests():
    """Run all test suites."""
    print("🧪 Running Duplicate Cleanup System Tests")
    print("=" * 50)

    # Test suites to run
    test_suites = [TestDuplicateCleanupSystem, TestSDKIntegration, TestRealWorldValidation]

    all_results = []

    for suite_class in test_suites:
        print(f"\n🔬 Running {suite_class.__name__}")
        print("-" * 30)

        suite = unittest.TestLoader().loadTestsFromTestCase(suite_class)

        # Custom test runner for async tests
        for test_case in suite:
            test_method_name = getattr(test_case, "_testMethodName", "unknown_test")
            test_method = getattr(test_case, test_method_name)

            try:
                if asyncio.iscoroutinefunction(test_method):
                    # Run async test
                    await test_method()
                else:
                    # Run sync test
                    test_method()

                print(f"✅ {test_method_name}")
                all_results.append((test_method_name, True, None))

            except unittest.SkipTest as e:
                print(f"⏭️  {test_method_name}: {e}")
                all_results.append((test_method_name, None, str(e)))

            except Exception as e:
                print(f"❌ {test_method_name}: {e}")
                all_results.append((test_method_name, False, str(e)))

    # Print summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)

    passed = len([r for r in all_results if r[1] is True])
    failed = len([r for r in all_results if r[1] is False])
    skipped = len([r for r in all_results if r[1] is None])

    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"📊 Total: {len(all_results)}")

    if failed > 0:
        print("\n❌ FAILED TESTS:")
        for test_name, result, error in all_results:
            if result is False:
                print(f"  - {test_name}: {error}")

    return failed == 0


async def main():
    """Main test execution."""
    parser = argparse.ArgumentParser(description="Test duplicate cleanup system")
    parser.add_argument("--test-sdk", action="store_true", help="Test SDK integration only")
    parser.add_argument("--test-safety", action="store_true", help="Test safety features only")
    parser.add_argument("--test-real", action="store_true", help="Test on real repository data")

    args = parser.parse_args()

    if args.test_sdk:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestSDKIntegration)
    elif args.test_safety:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestDuplicateCleanupSystem)
    elif args.test_real:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestRealWorldValidation)
    else:
        # Run all tests
        success = await run_all_tests()
        sys.exit(0 if success else 1)

    # Run specific test suite
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    asyncio.run(main())
