#!/usr/bin/env python3
"""
Unit tests for Ultra-Think performance metrics system.
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add hooks to path for testing
import sys

sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / ".claude" / "tools" / "amplihack" / "hooks")
)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "tools" / "amplihack"))

from post_tool_use import PostToolUseHook
from performance_report import PerformanceReporter


class TestPostToolUseHook:
    """Test TodoWrite metrics capture in post_tool_use hook."""

    def test_process_todowrite_metrics(self):
        """Test that TodoWrite transitions are captured correctly."""
        hook = PostToolUseHook()

        tool_use = {
            "name": "TodoWrite",
            "parameters": {
                "todos": [
                    {
                        "content": "Test task 1",
                        "status": "in_progress",
                        "activeForm": "Testing task 1",
                    },
                    {
                        "content": "Test task 2",
                        "status": "pending",
                        "activeForm": "Testing task 2",
                    },
                ]
            },
        }

        conversation_context = {"messageNumber": 42}

        # Mock save_metric to capture calls
        saved_metrics = []

        def mock_save_metric(metric_name, value, metadata):
            saved_metrics.append({"metric": metric_name, "value": value, "metadata": metadata})

        hook.save_metric = mock_save_metric

        # Process the metrics
        hook.process_todowrite_metrics(tool_use, conversation_context)

        # Verify only in_progress transition was captured
        assert len(saved_metrics) == 1
        assert saved_metrics[0]["metric"] == "todo_transition"
        assert saved_metrics[0]["value"] == "in_progress"
        assert saved_metrics[0]["metadata"]["task_content"] == "Test task 1"
        assert saved_metrics[0]["metadata"]["message_number"] == 42

    def test_process_todowrite_completed_transition(self):
        """Test that completed transitions are captured."""
        hook = PostToolUseHook()

        tool_use = {
            "name": "TodoWrite",
            "parameters": {
                "todos": [
                    {
                        "content": "Completed task",
                        "status": "completed",
                        "activeForm": "Completing task",
                    },
                ]
            },
        }

        conversation_context = {"messageNumber": 50}

        saved_metrics = []

        def mock_save_metric(metric_name, value, metadata):
            saved_metrics.append({"metric": metric_name, "value": value, "metadata": metadata})

        hook.save_metric = mock_save_metric

        hook.process_todowrite_metrics(tool_use, conversation_context)

        assert len(saved_metrics) == 1
        assert saved_metrics[0]["value"] == "completed"

    def test_process_todowrite_missing_data(self):
        """Test graceful handling of missing data."""
        hook = PostToolUseHook()

        tool_use = {
            "name": "TodoWrite",
            "parameters": {},  # Missing todos
        }

        conversation_context = {}  # Missing messageNumber

        # Should not raise exception
        hook.log = MagicMock()
        hook.save_metric = MagicMock()

        hook.process_todowrite_metrics(tool_use, conversation_context)

        # Should have logged something but not crashed
        hook.save_metric.assert_not_called()


class TestPerformanceReporter:
    """Test performance report generation."""

    def create_sample_metrics(self, temp_dir: Path) -> Path:
        """Create sample metrics file for testing."""
        metrics_file = temp_dir / "post_tool_use_metrics.jsonl"

        base_time = datetime.now()
        session_id = "2025-11-05T10:00:00"

        metrics = [
            # Task 1: in_progress at message 10
            {
                "timestamp": (base_time + timedelta(seconds=0)).isoformat(),
                "metric": "todo_transition",
                "value": "in_progress",
                "hook": "post_tool_use",
                "metadata": {
                    "task_content": "Step 1: Requirements clarification",
                    "task_active_form": "Clarifying requirements",
                    "message_number": 10,
                    "session_timestamp": session_id,
                },
            },
            # Task 1: completed at message 25
            {
                "timestamp": (base_time + timedelta(minutes=5)).isoformat(),
                "metric": "todo_transition",
                "value": "completed",
                "hook": "post_tool_use",
                "metadata": {
                    "task_content": "Step 1: Requirements clarification",
                    "task_active_form": "Clarifying requirements",
                    "message_number": 25,
                    "session_timestamp": session_id,
                },
            },
            # Task 2: in_progress at message 26
            {
                "timestamp": (base_time + timedelta(minutes=5, seconds=10)).isoformat(),
                "metric": "todo_transition",
                "value": "in_progress",
                "hook": "post_tool_use",
                "metadata": {
                    "task_content": "Step 2: Architecture design",
                    "task_active_form": "Designing architecture",
                    "message_number": 26,
                    "session_timestamp": session_id,
                },
            },
            # Task 2: completed at message 45
            {
                "timestamp": (base_time + timedelta(minutes=12)).isoformat(),
                "metric": "todo_transition",
                "value": "completed",
                "hook": "post_tool_use",
                "metadata": {
                    "task_content": "Step 2: Architecture design",
                    "task_active_form": "Designing architecture",
                    "message_number": 45,
                    "session_timestamp": session_id,
                },
            },
        ]

        with open(metrics_file, "w") as f:
            for metric in metrics:
                f.write(json.dumps(metric) + "\n")

        return metrics_file

    def test_load_metrics(self):
        """Test loading metrics from JSONL file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_sample_metrics(temp_path)

            reporter = PerformanceReporter(temp_path)
            metrics = reporter.load_metrics()

            assert len(metrics) == 4
            assert all(m["metric"] == "todo_transition" for m in metrics)

    def test_analyze_tasks(self):
        """Test task analysis and duration calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_sample_metrics(temp_path)

            reporter = PerformanceReporter(temp_path)
            metrics = reporter.load_metrics()
            tasks = reporter.analyze_tasks(metrics)

            assert len(tasks) == 2

            # Check Task 1
            task1 = next(t for t in tasks if "Requirements" in t["task"])
            assert task1["messages"] == 15  # 25 - 10
            assert task1["duration_minutes"] == pytest.approx(5.0, rel=0.1)
            assert task1["status"] == "completed"

            # Check Task 2
            task2 = next(t for t in tasks if "Architecture" in t["task"])
            assert task2["messages"] == 19  # 45 - 26
            assert task2["duration_minutes"] == pytest.approx(6.83, rel=0.1)
            assert task2["status"] == "completed"

    def test_generate_report(self):
        """Test report generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_sample_metrics(temp_path)

            reporter = PerformanceReporter(temp_path)
            report = reporter.generate_report()

            assert "Ultra-Think Performance Summary" in report
            assert "Requirements clarification" in report
            assert "Architecture design" in report
            assert "Total:" in report
            assert "34 msgs" in report  # 15 + 19

    def test_categorize_task_type(self):
        """Test task type categorization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            reporter = PerformanceReporter(temp_path)

            # Test investigation
            tasks = [{"task": "Investigate bug causes"}]
            assert reporter.categorize_task_type(tasks) == "investigation"

            # Test debugging
            tasks = [{"task": "Fix memory leak"}]
            assert reporter.categorize_task_type(tasks) == "debugging"

            # Test refactoring
            tasks = [{"task": "Refactor authentication module"}]
            assert reporter.categorize_task_type(tasks) == "refactoring"

            # Test development (default)
            tasks = [{"task": "Implement new feature"}]
            assert reporter.categorize_task_type(tasks) == "development"

    def test_baseline_management(self):
        """Test baseline creation and updates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_sample_metrics(temp_path)

            reporter = PerformanceReporter(temp_path)

            # Initially no baselines
            baselines = reporter.load_baselines()
            assert len(baselines) == 0

            # Update baselines
            reporter.update_baselines()

            # Now should have baselines
            baselines = reporter.load_baselines()
            assert "development" in baselines
            assert baselines["development"]["sample_count"] == 1
            assert baselines["development"]["avg_messages"] == 34  # 15 + 19

            # Update again
            reporter.update_baselines()

            # Sample count should increase
            baselines = reporter.load_baselines()
            assert baselines["development"]["sample_count"] == 2

    def test_empty_metrics(self):
        """Test handling of empty metrics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            reporter = PerformanceReporter(temp_path)
            report = reporter.generate_report()

            assert "No TodoWrite metrics found" in report


class TestIntegration:
    """Integration tests for the full system."""

    def test_end_to_end_workflow(self):
        """Test complete workflow from hook to report."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a mock hook with temp directory
            hook = PostToolUseHook()

            # Override metrics directory
            metrics_dir = temp_path
            metrics_file = metrics_dir / "post_tool_use_metrics.jsonl"

            def mock_save_metric(metric_name, value, metadata):
                metric = {
                    "timestamp": datetime.now().isoformat(),
                    "metric": metric_name,
                    "value": value,
                    "hook": "post_tool_use",
                    "metadata": metadata,
                }

                with open(metrics_file, "a") as f:
                    f.write(json.dumps(metric) + "\n")

            hook.save_metric = mock_save_metric
            hook.log = MagicMock()

            # Simulate TodoWrite calls
            tool_use1 = {
                "name": "TodoWrite",
                "parameters": {
                    "todos": [
                        {
                            "content": "Test task",
                            "status": "in_progress",
                            "activeForm": "Testing",
                        }
                    ]
                },
            }

            context1 = {"messageNumber": 10}
            hook.process_todowrite_metrics(tool_use1, context1)

            tool_use2 = {
                "name": "TodoWrite",
                "parameters": {
                    "todos": [
                        {
                            "content": "Test task",
                            "status": "completed",
                            "activeForm": "Testing",
                        }
                    ]
                },
            }

            context2 = {"messageNumber": 20}
            hook.process_todowrite_metrics(tool_use2, context2)

            # Generate report
            reporter = PerformanceReporter(temp_path)
            report = reporter.generate_report()

            assert "Test task" in report
            assert "10 msgs" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
