"""
Tests for subagent_mapper CLI module.

Tests command-line interface and argument parsing.
"""

import pytest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from io import StringIO
import sys

from amplihack.analytics.subagent_mapper import (
    parse_args,
    main,
    list_sessions,
    show_stats,
    generate_report,
)
from amplihack.analytics.metrics_reader import MetricsReader
from amplihack.analytics.visualization import ReportGenerator


class TestParseArgs:
    """Tests for argument parsing."""

    def test_default_args(self):
        """Test parsing with no arguments."""
        args = parse_args([])

        assert args.session_id is None
        assert args.agent is None
        assert args.output == "text"
        assert args.stats is False
        assert args.list_sessions is False

    def test_session_id_arg(self):
        """Test parsing with session ID."""
        args = parse_args(["--session-id", "session_001"])

        assert args.session_id == "session_001"

    def test_agent_filter_arg(self):
        """Test parsing with agent filter."""
        args = parse_args(["--agent", "architect"])

        assert args.agent == "architect"

    def test_output_format_text(self):
        """Test parsing with text output format."""
        args = parse_args(["--output", "text"])

        assert args.output == "text"

    def test_output_format_json(self):
        """Test parsing with JSON output format."""
        args = parse_args(["--output", "json"])

        assert args.output == "json"

    def test_stats_flag(self):
        """Test parsing with stats flag."""
        args = parse_args(["--stats"])

        assert args.stats is True

    def test_list_sessions_flag(self):
        """Test parsing with list-sessions flag."""
        args = parse_args(["--list-sessions"])

        assert args.list_sessions is True

    def test_metrics_dir_arg(self):
        """Test parsing with custom metrics directory."""
        args = parse_args(["--metrics-dir", "/custom/path"])

        assert args.metrics_dir == Path("/custom/path")

    def test_combined_args(self):
        """Test parsing with multiple arguments."""
        args = parse_args([
            "--session-id", "session_001",
            "--agent", "architect",
            "--output", "json"
        ])

        assert args.session_id == "session_001"
        assert args.agent == "architect"
        assert args.output == "json"


class TestListSessions:
    """Tests for list_sessions function."""

    @pytest.fixture
    def temp_metrics_with_sessions(self):
        """Create temporary metrics with multiple sessions."""
        with TemporaryDirectory() as tmpdir:
            metrics_path = Path(tmpdir)

            # Create test data with multiple sessions
            events = []
            for i in range(3):
                events.append({
                    "event": "start",
                    "agent_name": "test",
                    "session_id": f"session_{i:03d}",
                    "timestamp": f"2025-11-0{i+1}T14:30:00.000Z",
                    "execution_id": f"exec_{i}"
                })

            with open(metrics_path / "subagent_start.jsonl", "w") as f:
                for event in events:
                    f.write(json.dumps(event) + "\n")

            yield metrics_path

    def test_list_sessions_with_data(self, temp_metrics_with_sessions, capsys):
        """Test listing sessions with data."""
        reader = MetricsReader(metrics_dir=temp_metrics_with_sessions)
        exit_code = list_sessions(reader)

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Available Sessions:" in captured.out
        assert "session_000" in captured.out
        assert "session_001" in captured.out
        assert "session_002" in captured.out

    def test_list_sessions_empty(self, capsys):
        """Test listing sessions with no data."""
        with TemporaryDirectory() as tmpdir:
            reader = MetricsReader(metrics_dir=Path(tmpdir))
            exit_code = list_sessions(reader)

            assert exit_code == 0

            captured = capsys.readouterr()
            assert "No sessions found" in captured.out


class TestShowStats:
    """Tests for show_stats function."""

    @pytest.fixture
    def temp_metrics_with_stats(self):
        """Create temporary metrics with stats data."""
        with TemporaryDirectory() as tmpdir:
            metrics_path = Path(tmpdir)

            start_events = [
                {
                    "event": "start",
                    "agent_name": "architect",
                    "session_id": "session_001",
                    "timestamp": "2025-11-02T14:30:00.000Z",
                    "execution_id": "exec_001"
                },
                {
                    "event": "start",
                    "agent_name": "builder",
                    "session_id": "session_001",
                    "timestamp": "2025-11-02T14:31:00.000Z",
                    "execution_id": "exec_002"
                }
            ]

            stop_events = [
                {
                    "event": "stop",
                    "agent_name": "architect",
                    "session_id": "session_001",
                    "timestamp": "2025-11-02T14:30:45.000Z",
                    "execution_id": "exec_001",
                    "duration_ms": 45000.0
                },
                {
                    "event": "stop",
                    "agent_name": "builder",
                    "session_id": "session_001",
                    "timestamp": "2025-11-02T14:33:00.000Z",
                    "execution_id": "exec_002",
                    "duration_ms": 120000.0
                }
            ]

            with open(metrics_path / "subagent_start.jsonl", "w") as f:
                for event in start_events:
                    f.write(json.dumps(event) + "\n")

            with open(metrics_path / "subagent_stop.jsonl", "w") as f:
                for event in stop_events:
                    f.write(json.dumps(event) + "\n")

            yield metrics_path

    def test_show_stats_with_data(self, temp_metrics_with_stats, capsys):
        """Test showing stats with data."""
        reader = MetricsReader(metrics_dir=temp_metrics_with_stats)
        exit_code = show_stats(reader, "session_001", None)

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Performance Statistics" in captured.out
        assert "Total Executions:" in captured.out
        assert "architect" in captured.out
        assert "builder" in captured.out

    def test_show_stats_no_session(self):
        """Test showing stats with no session."""
        with TemporaryDirectory() as tmpdir:
            reader = MetricsReader(metrics_dir=Path(tmpdir))
            exit_code = show_stats(reader, None, None)

            assert exit_code == 1


class TestGenerateReport:
    """Tests for generate_report function."""

    @pytest.fixture
    def temp_metrics_for_report(self):
        """Create temporary metrics for report generation."""
        with TemporaryDirectory() as tmpdir:
            metrics_path = Path(tmpdir)

            start_events = [
                {
                    "event": "start",
                    "agent_name": "architect",
                    "session_id": "session_001",
                    "timestamp": "2025-11-02T14:30:00.000Z",
                    "execution_id": "exec_001"
                }
            ]

            stop_events = [
                {
                    "event": "stop",
                    "agent_name": "architect",
                    "session_id": "session_001",
                    "timestamp": "2025-11-02T14:30:45.000Z",
                    "execution_id": "exec_001",
                    "duration_ms": 45000.0
                }
            ]

            with open(metrics_path / "subagent_start.jsonl", "w") as f:
                for event in start_events:
                    f.write(json.dumps(event) + "\n")

            with open(metrics_path / "subagent_stop.jsonl", "w") as f:
                for event in stop_events:
                    f.write(json.dumps(event) + "\n")

            yield metrics_path

    def test_generate_text_report(self, temp_metrics_for_report, capsys):
        """Test generating text report."""
        reader = MetricsReader(metrics_dir=temp_metrics_for_report)
        generator = ReportGenerator(reader)

        exit_code = generate_report(
            reader,
            generator,
            "session_001",
            None,
            "text"
        )

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Subagent Execution Map" in captured.out
        assert "architect" in captured.out

    def test_generate_json_report(self, temp_metrics_for_report, capsys):
        """Test generating JSON report."""
        reader = MetricsReader(metrics_dir=temp_metrics_for_report)
        generator = ReportGenerator(reader)

        exit_code = generate_report(
            reader,
            generator,
            "session_001",
            None,
            "json"
        )

        assert exit_code == 0

        captured = capsys.readouterr()
        report_data = json.loads(captured.out)
        assert report_data["session_id"] == "session_001"
        assert "executions" in report_data


class TestMainFunction:
    """Tests for main CLI function."""

    @pytest.fixture
    def temp_metrics_for_main(self):
        """Create temporary metrics for main function tests."""
        with TemporaryDirectory() as tmpdir:
            metrics_path = Path(tmpdir)

            start_events = [
                {
                    "event": "start",
                    "agent_name": "test_agent",
                    "session_id": "test_session",
                    "timestamp": "2025-11-02T14:30:00.000Z",
                    "execution_id": "exec_001"
                }
            ]

            stop_events = [
                {
                    "event": "stop",
                    "agent_name": "test_agent",
                    "session_id": "test_session",
                    "timestamp": "2025-11-02T14:30:10.000Z",
                    "execution_id": "exec_001",
                    "duration_ms": 10000.0
                }
            ]

            with open(metrics_path / "subagent_start.jsonl", "w") as f:
                for event in start_events:
                    f.write(json.dumps(event) + "\n")

            with open(metrics_path / "subagent_stop.jsonl", "w") as f:
                for event in stop_events:
                    f.write(json.dumps(event) + "\n")

            yield metrics_path

    def test_main_with_list_sessions(self, temp_metrics_for_main, capsys):
        """Test main with --list-sessions."""
        args = [
            "--list-sessions",
            "--metrics-dir", str(temp_metrics_for_main)
        ]

        exit_code = main(args)

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Available Sessions:" in captured.out

    def test_main_with_stats(self, temp_metrics_for_main, capsys):
        """Test main with --stats."""
        args = [
            "--stats",
            "--metrics-dir", str(temp_metrics_for_main)
        ]

        exit_code = main(args)

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Performance Statistics" in captured.out

    def test_main_generate_report(self, temp_metrics_for_main, capsys):
        """Test main generating default report."""
        args = [
            "--metrics-dir", str(temp_metrics_for_main)
        ]

        exit_code = main(args)

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Subagent Execution Map" in captured.out

    def test_main_with_json_output(self, temp_metrics_for_main, capsys):
        """Test main with JSON output."""
        args = [
            "--output", "json",
            "--metrics-dir", str(temp_metrics_for_main)
        ]

        exit_code = main(args)

        assert exit_code == 0

        captured = capsys.readouterr()
        report_data = json.loads(captured.out)
        assert "session_id" in report_data
