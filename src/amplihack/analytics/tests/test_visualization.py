"""
Tests for visualization module.

Tests tree building, ASCII rendering, and pattern detection.
"""

import pytest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from amplihack.analytics.metrics_reader import SubagentExecution, MetricsReader
from amplihack.analytics.visualization import (
    AgentNode,
    ExecutionTreeBuilder,
    AsciiTreeRenderer,
    PatternDetector,
    ReportGenerator,
    Pattern,
)


class TestAgentNode:
    """Tests for AgentNode class."""

    def test_create_node(self):
        """Test creating an agent node."""
        node = AgentNode(
            name="architect",
            parent="orchestrator",
            invocation_count=2,
            total_duration_ms=45000.0,
            children=[]
        )

        assert node.name == "architect"
        assert node.parent == "orchestrator"
        assert node.invocation_count == 2
        assert node.total_duration_seconds() == 45.0

    def test_add_child(self):
        """Test adding child nodes."""
        parent = AgentNode("parent", None, 1, 1000.0, [])
        child = AgentNode("child", "parent", 1, 500.0, [])

        parent.add_child(child)

        assert len(parent.children) == 1
        assert parent.children[0] == child


class TestExecutionTreeBuilder:
    """Tests for ExecutionTreeBuilder class."""

    def test_build_simple_tree(self):
        """Test building a simple execution tree."""
        executions = [
            SubagentExecution(
                agent_name="architect",
                session_id="test",
                parent_agent=None,
                execution_id="exec_001",
                start_time=datetime.now(),
                end_time=None,
                duration_ms=45000.0,
                metadata={}
            ),
            SubagentExecution(
                agent_name="builder",
                session_id="test",
                parent_agent="architect",
                execution_id="exec_002",
                start_time=datetime.now(),
                end_time=None,
                duration_ms=120000.0,
                metadata={}
            )
        ]

        builder = ExecutionTreeBuilder(executions)
        tree = builder.build()

        # Should have one root (architect)
        assert len(tree) == 1
        assert "architect" in tree

        # Architect should have builder as child
        architect_node = tree["architect"]
        assert architect_node.invocation_count == 1
        assert len(architect_node.children) == 1
        assert architect_node.children[0].name == "builder"

    def test_build_multiple_invocations(self):
        """Test building tree with multiple invocations of same agent."""
        executions = [
            SubagentExecution(
                agent_name="builder",
                session_id="test",
                parent_agent="orchestrator",
                execution_id="exec_001",
                start_time=datetime.now(),
                end_time=None,
                duration_ms=60000.0,
                metadata={}
            ),
            SubagentExecution(
                agent_name="builder",
                session_id="test",
                parent_agent="orchestrator",
                execution_id="exec_002",
                start_time=datetime.now(),
                end_time=None,
                duration_ms=70000.0,
                metadata={}
            )
        ]

        builder = ExecutionTreeBuilder(executions)
        tree = builder.build()

        assert "builder" in tree
        builder_node = tree["builder"]
        assert builder_node.invocation_count == 2
        assert builder_node.total_duration_ms == 130000.0


class TestAsciiTreeRenderer:
    """Tests for AsciiTreeRenderer class."""

    def test_render_single_node(self):
        """Test rendering a single node."""
        node = AgentNode("architect", None, 1, 45000.0, [])
        tree = {"architect": node}

        renderer = AsciiTreeRenderer()
        output = renderer.render(tree)

        assert "architect" in output
        assert "1 invocations" in output
        assert "45.0s" in output

    def test_render_tree_with_children(self):
        """Test rendering a tree with children."""
        parent = AgentNode("architect", None, 1, 45000.0, [])
        child1 = AgentNode("builder", "architect", 1, 30000.0, [])
        child2 = AgentNode("reviewer", "architect", 1, 15000.0, [])

        parent.add_child(child1)
        parent.add_child(child2)

        tree = {"architect": parent}

        renderer = AsciiTreeRenderer()
        output = renderer.render(tree)

        # Should contain tree structure
        assert "architect" in output
        assert "builder" in output
        assert "reviewer" in output
        # Should have tree connectors
        assert "├─" in output or "└─" in output


class TestPatternDetector:
    """Tests for PatternDetector class."""

    def test_detect_correlations(self):
        """Test detecting agent correlations."""
        executions = [
            SubagentExecution(
                agent_name="analyzer",
                session_id="test",
                parent_agent="architect",
                execution_id=f"exec_{i}",
                start_time=datetime.now(),
                end_time=None,
                duration_ms=10000.0,
                metadata={}
            )
            for i in range(3)
        ]

        detector = PatternDetector(executions)
        patterns = detector._detect_correlations()

        # Should detect architect -> analyzer correlation
        assert len(patterns) >= 1
        correlation_pattern = patterns[0]
        assert correlation_pattern.pattern_type == "correlation"
        assert "architect" in correlation_pattern.agents
        assert "analyzer" in correlation_pattern.agents

    def test_detect_bottlenecks(self):
        """Test detecting bottlenecks."""
        executions = [
            SubagentExecution(
                agent_name="fast_agent",
                session_id="test",
                parent_agent=None,
                execution_id="exec_001",
                start_time=datetime.now(),
                end_time=None,
                duration_ms=5000.0,
                metadata={}
            ),
            SubagentExecution(
                agent_name="slow_agent",
                session_id="test",
                parent_agent=None,
                execution_id="exec_002",
                start_time=datetime.now(),
                end_time=None,
                duration_ms=50000.0,
                metadata={}
            ),
            SubagentExecution(
                agent_name="slow_agent",
                session_id="test",
                parent_agent=None,
                execution_id="exec_003",
                start_time=datetime.now(),
                end_time=None,
                duration_ms=60000.0,
                metadata={}
            )
        ]

        detector = PatternDetector(executions)
        patterns = detector._detect_bottlenecks()

        # Should detect slow_agent as bottleneck
        assert len(patterns) >= 1
        bottleneck = patterns[0]
        assert bottleneck.pattern_type == "bottleneck"
        assert "slow_agent" in bottleneck.agents

    def test_detect_all_patterns(self):
        """Test detecting all patterns."""
        executions = [
            SubagentExecution(
                agent_name="architect",
                session_id="test",
                parent_agent=None,
                execution_id="exec_001",
                start_time=datetime.now(),
                end_time=None,
                duration_ms=10000.0,
                metadata={}
            )
        ]

        detector = PatternDetector(executions)
        patterns = detector.detect_all()

        # Should return a list (may be empty for simple cases)
        assert isinstance(patterns, list)


class TestReportGenerator:
    """Tests for ReportGenerator class."""

    @pytest.fixture
    def temp_metrics_with_data(self):
        """Create temporary metrics directory with test data."""
        with TemporaryDirectory() as tmpdir:
            metrics_path = Path(tmpdir)

            # Create test JSONL files
            start_events = [
                {
                    "event": "start",
                    "agent_name": "architect",
                    "session_id": "session_001",
                    "timestamp": "2025-11-02T14:30:00.000Z",
                    "parent_agent": None,
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

    def test_generate_text_report(self, temp_metrics_with_data):
        """Test generating text report."""
        reader = MetricsReader(metrics_dir=temp_metrics_with_data)
        generator = ReportGenerator(reader)

        report = generator.generate_text_report(session_id="session_001")

        assert "Subagent Execution Map" in report
        assert "session_001" in report
        assert "architect" in report
        assert "Performance Summary" in report

    def test_generate_json_report(self, temp_metrics_with_data):
        """Test generating JSON report."""
        reader = MetricsReader(metrics_dir=temp_metrics_with_data)
        generator = ReportGenerator(reader)

        report = generator.generate_json_report(session_id="session_001")

        assert "session_id" in report
        assert report["session_id"] == "session_001"
        assert "executions" in report
        assert "tree" in report
        assert "stats" in report
        assert "patterns" in report
