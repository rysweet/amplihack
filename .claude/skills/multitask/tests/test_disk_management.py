#!/usr/bin/env python3
"""Tests for disk management features in multitask orchestrator."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator import ParallelOrchestrator


def test_disk_usage_calculation():
    """Test that disk usage calculation works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create fake workstream directories
        ws1 = tmp_path / "ws-123"
        ws1.mkdir()
        (ws1 / "test.txt").write_text("x" * 1024 * 1024)  # 1MB file

        ws2 = tmp_path / "ws-124"
        ws2.mkdir()
        (ws2 / "test.txt").write_text("x" * 2 * 1024 * 1024)  # 2MB file

        orchestrator = ParallelOrchestrator(
            repo_url="https://github.com/test/repo", tmp_base=str(tmp_path)
        )

        disk_gb, ws_count = orchestrator._calculate_disk_usage()

        assert ws_count == 2, f"Expected 2 workstreams, got {ws_count}"
        assert 0.002 < disk_gb < 0.005, f"Expected ~3MB (0.003GB), got {disk_gb:.4f}GB"

        print(f"✓ Disk usage calculation works: {ws_count} workstreams, {disk_gb:.4f}GB")


def test_cleanup_dry_run():
    """Test that cleanup dry run doesn't delete anything."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create test workstream
        ws_dir = tmp_path / "ws-999"
        ws_dir.mkdir()
        test_file = ws_dir / "test.txt"
        test_file.write_text("test content")

        # Create test config
        config_file = tmp_path / "config.json"
        config_file.write_text(
            json.dumps(
                [{"issue": 999, "branch": "test", "description": "Test", "task": "Test task"}]
            )
        )

        orchestrator = ParallelOrchestrator(
            repo_url="https://github.com/test/repo", tmp_base=str(tmp_path)
        )

        # Run cleanup in dry-run mode (will fail on gh CLI but shouldn't delete)
        try:
            orchestrator.cleanup_merged(str(config_file), dry_run=True)
        except Exception:
            pass  # Expected to fail without gh CLI configured

        # Verify workstream directory still exists
        assert ws_dir.exists(), "Dry run should not delete workstream directory"
        assert test_file.exists(), "Dry run should not delete files"

        print("✓ Dry run doesn't delete files")


def test_cleanup_preserves_resumable_workstream_even_when_pr_is_merged():
    """Merged PR cleanup must skip preserved resumable workstreams."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        ws_dir = tmp_path / "ws-999"
        ws_dir.mkdir()
        test_file = ws_dir / "test.txt"
        test_file.write_text("preserve me")

        state_dir = tmp_path / "state"
        state_dir.mkdir()
        (state_dir / "ws-999.json").write_text(
            json.dumps(
                {
                    "issue": 999,
                    "lifecycle_state": "timed_out_resumable",
                    "cleanup_eligible": False,
                }
            )
        )

        config_file = tmp_path / "config.json"
        config_file.write_text(
            json.dumps(
                [{"issue": 999, "branch": "test", "description": "Test", "task": "Test task"}]
            )
        )

        orchestrator = ParallelOrchestrator(
            repo_url="https://github.com/test/repo", tmp_base=str(tmp_path)
        )

        with patch("orchestrator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='[{"number": 1, "state": "MERGED", "merged": true}]',
            )
            orchestrator.cleanup_merged(str(config_file), dry_run=False)

        assert ws_dir.exists(), "Resumable workstream directory must be preserved"
        assert test_file.exists(), "Cleanup must not delete resumable workstream files"


if __name__ == "__main__":
    test_disk_usage_calculation()
    test_cleanup_dry_run()
    print("\n✅ All disk management tests passed!")
