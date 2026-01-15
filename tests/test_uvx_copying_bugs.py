"""Tests for UVX file copying bug fixes (Issue #1940).

This module tests two critical bugs in the UVX file copying system:
1. Bug #1: Missing should_proceed check when user cancels
2. Bug #2: Silent failure when copytree_manifest returns empty list

Following TDD approach - these tests FAIL before fixes are implemented.
Target test ratio: 3:1 to 5:1 (54-90 lines for 18 lines of implementation).
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestBug1ShouldProceedCheck:
    """Test Bug #1: Missing should_proceed check.

    When user responds 'n' to conflict prompt, should_proceed=False
    but code continues to copy files anyway. Should exit immediately.
    """

    def test_user_cancels_with_n_response_exits_immediately(self):
        """Unit test: User responds 'n' → should_proceed=False → sys.exit(0)."""
        # ARRANGE: Mock SafeCopyStrategy to return should_proceed=False
        mock_strategy = MagicMock()
        mock_strategy.target_dir = Path("/fake/path/.claude")
        mock_strategy.should_proceed = False

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create minimal environment for UVX mode
            os.environ["UV_PYTHON"] = "/fake/uv/python"
            os.environ["AMPLIHACK_ORIGINAL_CWD"] = temp_dir

            with patch("amplihack.cli.is_uvx_deployment", return_value=True):
                with patch("amplihack.safety.SafeCopyStrategy") as mock_strategy_class:
                    mock_strategy_manager = MagicMock()
                    mock_strategy_manager.determine_target.return_value = mock_strategy
                    mock_strategy_class.return_value = mock_strategy_manager

                    with patch("amplihack.safety.GitConflictDetector") as mock_detector:
                        mock_detector_instance = MagicMock()
                        mock_detector_instance.detect_conflicts.return_value = MagicMock(
                            has_conflicts=True, conflicting_files=[".claude/context/test.md"]
                        )
                        mock_detector.return_value = mock_detector_instance

                        # ACT & ASSERT: Should exit with code 0 (user cancel)
                        from amplihack.cli import main

                        with pytest.raises(SystemExit) as exc_info:
                            with patch.object(sys, "argv", ["amplihack"]):
                                main()

                        assert exc_info.value.code == 0

    def test_user_cancels_message_shown(self, capsys):
        """Unit test: Verify cancellation message is shown to user."""
        # ARRANGE: Mock SafeCopyStrategy to return should_proceed=False
        mock_strategy = MagicMock()
        mock_strategy.target_dir = Path("/fake/path/.claude")
        mock_strategy.should_proceed = False

        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["UV_PYTHON"] = "/fake/uv/python"
            os.environ["AMPLIHACK_ORIGINAL_CWD"] = temp_dir

            with patch("amplihack.cli.is_uvx_deployment", return_value=True):
                with patch("amplihack.safety.SafeCopyStrategy") as mock_strategy_class:
                    mock_strategy_manager = MagicMock()
                    mock_strategy_manager.determine_target.return_value = mock_strategy
                    mock_strategy_class.return_value = mock_strategy_manager

                    with patch("amplihack.safety.GitConflictDetector") as mock_detector:
                        mock_detector_instance = MagicMock()
                        mock_detector_instance.detect_conflicts.return_value = MagicMock(
                            has_conflicts=True, conflicting_files=[".claude/context/test.md"]
                        )
                        mock_detector.return_value = mock_detector_instance

                        # ACT: Trigger main() and catch exit
                        from amplihack.cli import main

                        with pytest.raises(SystemExit):
                            with patch.object(sys, "argv", ["amplihack"]):
                                main()

                        # ASSERT: Cancellation message shown
                        captured = capsys.readouterr()
                        assert (
                            "cancelled" in captured.out.lower() or "exiting" in captured.out.lower()
                        )


class TestBug2EmptyCopyHandling:
    """Test Bug #2: Silent failure on empty copy.

    When copytree_manifest returns empty list (no files copied),
    code silently continues. Should show error and exit(1).
    """

    def test_empty_copy_result_exits_with_error(self):
        """Unit test: Empty copy (copied=[]) → error message → sys.exit(1)."""
        # ARRANGE: Mock copytree_manifest to return empty list
        mock_strategy = MagicMock()
        mock_strategy.target_dir = Path("/fake/path/.claude")
        mock_strategy.should_proceed = True

        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["UV_PYTHON"] = "/fake/uv/python"
            os.environ["AMPLIHACK_ORIGINAL_CWD"] = temp_dir

            with patch("amplihack.cli.is_uvx_deployment", return_value=True):
                with patch("amplihack.safety.SafeCopyStrategy") as mock_strategy_class:
                    mock_strategy_manager = MagicMock()
                    mock_strategy_manager.determine_target.return_value = mock_strategy
                    mock_strategy_class.return_value = mock_strategy_manager

                    with patch("amplihack.safety.GitConflictDetector") as mock_detector:
                        mock_detector_instance = MagicMock()
                        mock_detector_instance.detect_conflicts.return_value = MagicMock(
                            has_conflicts=False, conflicting_files=[]
                        )
                        mock_detector.return_value = mock_detector_instance

                        with patch("amplihack.cli.copytree_manifest") as mock_copy:
                            # Return empty list (no files copied)
                            mock_copy.return_value = []

                            # ACT & ASSERT: Should exit with code 1 (error)
                            from amplihack.cli import main

                            with pytest.raises(SystemExit) as exc_info:
                                with patch.object(sys, "argv", ["amplihack"]):
                                    main()

                            assert exc_info.value.code == 1

    def test_empty_copy_error_message_shown(self, capsys):
        """Unit test: Verify error message is shown when copy fails."""
        # ARRANGE: Mock copytree_manifest to return empty list
        mock_strategy = MagicMock()
        mock_strategy.target_dir = Path("/fake/path/.claude")
        mock_strategy.should_proceed = True

        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["UV_PYTHON"] = "/fake/uv/python"
            os.environ["AMPLIHACK_ORIGINAL_CWD"] = temp_dir

            with patch("amplihack.cli.is_uvx_deployment", return_value=True):
                with patch("amplihack.safety.SafeCopyStrategy") as mock_strategy_class:
                    mock_strategy_manager = MagicMock()
                    mock_strategy_manager.determine_target.return_value = mock_strategy
                    mock_strategy_class.return_value = mock_strategy_manager

                    with patch("amplihack.safety.GitConflictDetector") as mock_detector:
                        mock_detector_instance = MagicMock()
                        mock_detector_instance.detect_conflicts.return_value = MagicMock(
                            has_conflicts=False, conflicting_files=[]
                        )
                        mock_detector.return_value = mock_detector_instance

                        with patch("amplihack.cli.copytree_manifest") as mock_copy:
                            mock_copy.return_value = []

                            # ACT: Trigger main() and catch exit
                            from amplihack.cli import main

                            with pytest.raises(SystemExit):
                                with patch.object(sys, "argv", ["amplihack"]):
                                    main()

                            # ASSERT: Error message shown
                            captured = capsys.readouterr()
                            assert (
                                "error" in captured.out.lower() or "failed" in captured.out.lower()
                            )
                            assert ".claude" in captured.out.lower()
