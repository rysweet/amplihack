"""
End-to-End Learning Tests - Validate all four agents demonstrate learning.

Tests use gadugi-agentic-test framework for real-world validation.

All tests written to FAIL initially (TDD approach).
"""

import json

import pytest

pytestmark = pytest.mark.e2e  # Mark all tests as E2E


class TestDocumentationAnalyzerE2E:
    """E2E tests for documentation analyzer learning."""

    @pytest.fixture
    def real_docs(self, tmp_path):
        """Create realistic documentation set."""
        docs = tmp_path / "docs"
        docs.mkdir()

        # Mix of good and bad documentation
        files = {
            "tutorial_good.md": """
# Python Tutorial

Learn Python basics with examples.

## Hello World

```python
print("Hello, World!")
```

This prints a greeting message.
            """,
            "tutorial_bad_1.md": """
# Advanced Topics

Learn advanced concepts.

## Decorators

Decorators are useful.

## Context Managers

Context managers handle resources.
            """,
            "tutorial_bad_2.md": """
# API Guide

Use the API for integration.

## Authentication

Authenticate your requests.

## Making Calls

Call the endpoints.
            """,
            "reference.md": """
# API Reference

## function process(data)

Processes data and returns result.

### Parameters

- data: Input data

### Returns

Processed result
            """,
        }

        for filename, content in files.items():
            (docs / filename).write_text(content)

        return docs

    def test_learns_over_five_runs(self, real_docs):
        """Agent demonstrates learning over 5 consecutive runs."""
        from doc_analyzer import DocumentationAnalyzer

        agent = DocumentationAnalyzer(enable_memory=True)
        agent.memory.clear()

        results = []

        # Run agent 5 times on same docs
        for run_num in range(5):
            result = agent.execute(target=real_docs)
            results.append(
                {
                    "run": run_num + 1,
                    "runtime": result.runtime_seconds,
                    "issues_found": result.issues_found,
                    "patterns_applied": result.metadata.get("patterns_applied", 0),
                    "experiences_stored": len(agent.memory.retrieve_experiences()),
                }
            )

        # Validate learning progression
        assert results[4]["runtime"] < results[0]["runtime"], "Runtime should decrease over runs"

        assert results[4]["patterns_applied"] > 0, "Should apply patterns by run 5"

        assert results[4]["experiences_stored"] > results[0]["experiences_stored"], (
            "Should accumulate experiences"
        )

        # Calculate improvement
        improvement = (results[0]["runtime"] - results[4]["runtime"]) / results[0]["runtime"]
        assert improvement > 0.20, f"Expected >20% improvement, got {improvement * 100:.1f}%"

    def test_performance_requirements_met(self, real_docs):
        """Agent meets p50 <100ms memory operation requirement."""
        import time

        from doc_analyzer import DocumentationAnalyzer

        agent = DocumentationAnalyzer(enable_memory=True)

        # Warm up (build patterns)
        for _ in range(3):
            agent.execute(target=real_docs)

        # Measure memory operations
        operation_times = []

        for _ in range(100):
            start = time.time()
            agent.memory.retrieve_relevant(current_context="documentation quality check", top_k=10)
            elapsed_ms = (time.time() - start) * 1000
            operation_times.append(elapsed_ms)

        # Calculate p50
        operation_times.sort()
        p50 = operation_times[len(operation_times) // 2]

        assert p50 < 100, f"p50 should be <100ms, got {p50:.1f}ms"


class TestAllAgentsLearning:
    """E2E tests validating all four agents demonstrate learning."""

    @pytest.fixture
    def test_data(self, tmp_path):
        """Create test data for all agents."""
        data = {
            "docs": tmp_path / "docs",
            "code": tmp_path / "src",
        }

        # Create documentation
        data["docs"].mkdir()
        for i in range(10):
            (data["docs"] / f"doc_{i}.md").write_text(f"# Document {i}\nContent here.")

        # Create code
        data["code"].mkdir()
        for i in range(10):
            (data["code"] / f"module_{i}.py").write_text(f"""
def function_{i}(data):
    try:
        return process(data)
    except Exception as e:
        print(f"Error: {{e}}")
        return None
            """)

        return data

    def test_all_four_agents_show_learning(self, test_data):
        """All four agents demonstrate measurable learning."""
        agents = [
            ("doc-analyzer", "DocumentationAnalyzer", test_data["docs"]),
            ("pattern-recognizer", "CodePatternRecognizer", test_data["code"]),
            ("bug-predictor", "BugPredictor", test_data["code"]),
            ("performance-optimizer", "PerformanceOptimizer", test_data["code"]),
        ]

        learning_results = {}

        for agent_name, agent_class_name, target in agents:
            # Import agent dynamically
            module = __import__(agent_name.replace("-", "_"), fromlist=[agent_class_name])
            AgentClass = getattr(module, agent_class_name)

            agent = AgentClass(enable_memory=True)
            agent.memory.clear()

            # Run twice to measure improvement
            result1 = agent.execute(target=target)
            result2 = agent.execute(target=target)

            improvement = (
                result1.runtime_seconds - result2.runtime_seconds
            ) / result1.runtime_seconds

            learning_results[agent_name] = {
                "improvement": improvement,
                "patterns_learned": len(
                    agent.memory.retrieve_experiences(experience_type=ExperienceType.PATTERN)
                ),
            }

        # All agents should show improvement
        for agent_name, results in learning_results.items():
            assert results["improvement"] > 0, f"{agent_name} should show improvement"

            assert results["patterns_learned"] > 0, f"{agent_name} should learn patterns"

    def test_cross_agent_comparison(self, test_data):
        """Compare learning rates across agents."""
        from doc_analyzer import DocumentationAnalyzer
        from pattern_recognizer import CodePatternRecognizer

        # Doc analyzer on docs
        doc_agent = DocumentationAnalyzer(enable_memory=True)
        doc_agent.memory.clear()

        doc_results = []
        for _ in range(3):
            result = doc_agent.execute(target=test_data["docs"])
            doc_results.append(result.runtime_seconds)

        doc_improvement = (doc_results[0] - doc_results[2]) / doc_results[0]

        # Pattern recognizer on code
        pattern_agent = CodePatternRecognizer(enable_memory=True)
        pattern_agent.memory.clear()

        pattern_results = []
        for _ in range(3):
            result = pattern_agent.execute(target=test_data["code"])
            pattern_results.append(result.runtime_seconds)

        pattern_improvement = (pattern_results[0] - pattern_results[2]) / pattern_results[0]

        # Both should show meaningful improvement
        assert doc_improvement > 0.15
        assert pattern_improvement > 0.15


class TestGadugiAgenticTestIntegration:
    """Test gadugi-agentic-test scenario execution."""

    def test_scenario_yaml_execution(self, tmp_path):
        """Execute gadugi-agentic-test scenario from YAML."""
        from gadugi_agentic_test import ScenarioRunner

        # Create scenario definition
        scenario = {
            "scenario": {
                "name": "Documentation Analyzer Learning",
                "description": "Validate doc analyzer learns patterns",
                "steps": [
                    {
                        "name": "First Run",
                        "action": "run_agent",
                        "agent": "doc-analyzer",
                        "target": str(tmp_path / "docs"),
                        "metrics": ["runtime", "issues_found", "experiences_stored"],
                    },
                    {
                        "name": "Second Run",
                        "action": "run_agent",
                        "agent": "doc-analyzer",
                        "target": str(tmp_path / "docs"),
                        "metrics": ["runtime", "issues_found", "patterns_applied"],
                    },
                    {
                        "name": "Validate Learning",
                        "action": "assert_improvement",
                        "metrics": {
                            "runtime_improvement": ">20%",
                            "patterns_recognized": ">0",
                            "issues_found": ">=first_run",
                        },
                    },
                ],
            }
        }

        # Create test docs
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "test.md").write_text("# Test\nNo examples.")

        # Write scenario file
        scenario_file = tmp_path / "scenario.yaml"
        import yaml

        with open(scenario_file, "w") as f:
            yaml.dump(scenario, f)

        # Run scenario
        runner = ScenarioRunner()
        result = runner.execute_scenario(scenario_file)

        assert result.success is True
        assert all(step.passed for step in result.steps)

    def test_evidence_collection(self, tmp_path):
        """gadugi-agentic-test collects evidence of learning."""
        from doc_analyzer import DocumentationAnalyzer
        from gadugi_agentic_test import EvidenceCollector

        collector = EvidenceCollector(output_dir=tmp_path / "evidence")

        agent = DocumentationAnalyzer(enable_memory=True)
        agent.memory.clear()

        # Create test docs
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "doc.md").write_text("# Doc\nContent.")

        # Run with evidence collection
        with collector.collect("doc-analyzer-run-1"):
            _ = agent.execute(target=docs)

        with collector.collect("doc-analyzer-run-2"):
            _ = agent.execute(target=docs)

        # Check evidence was collected
        evidence_files = list((tmp_path / "evidence").glob("*.json"))
        assert len(evidence_files) >= 2

        # Evidence should show learning
        with open(evidence_files[0]) as f:
            evidence1 = json.load(f)

        with open(evidence_files[1]) as f:
            evidence2 = json.load(f)

        assert evidence2["runtime"] < evidence1["runtime"]


class TestLearningPlateauDetection:
    """Test detection of learning plateaus."""

    def test_detects_learning_plateau(self, tmp_path):
        """System detects when agent stops improving (plateau)."""
        from doc_analyzer import DocumentationAnalyzer
        from doc_analyzer.metrics import LearningMetrics

        agent = DocumentationAnalyzer(enable_memory=True)
        agent.memory.clear()

        metrics = LearningMetrics(agent.memory)

        # Create simple docs
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "simple.md").write_text("# Simple Doc\nJust text.")

        # Run until plateau (typically 10-15 runs)
        runtimes = []
        for run in range(20):
            result = agent.execute(target=docs)
            runtimes.append(result.runtime_seconds)

            # Check for plateau after 10 runs
            if run >= 10:
                # Calculate improvement rate in last 5 runs
                recent_improvement = (runtimes[-5] - runtimes[-1]) / runtimes[-5]

                if recent_improvement < 0.05:  # <5% improvement
                    # Plateau detected
                    assert metrics.has_plateaued(), "Metrics should detect plateau"
                    break


class TestMemoryPersistenceE2E:
    """Test memory persistence across agent restarts."""

    def test_knowledge_survives_restart(self, tmp_path):
        """Agent knowledge persists across process restarts."""
        from doc_analyzer import DocumentationAnalyzer

        memory_path = tmp_path / "persistent_memory"

        # First session
        agent1 = DocumentationAnalyzer(enable_memory=True, memory_path=memory_path)
        agent1.memory.clear()

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "doc.md").write_text("# Doc\nNo examples.")

        # Run to learn patterns
        for _ in range(3):
            agent1.execute(target=docs)

        # Get pattern count
        patterns1 = agent1.memory.retrieve_experiences(experience_type=ExperienceType.PATTERN)
        pattern_count1 = len(patterns1)

        # Simulate restart - create new agent instance
        agent2 = DocumentationAnalyzer(enable_memory=True, memory_path=memory_path)

        # Should load previous patterns
        patterns2 = agent2.memory.retrieve_experiences(experience_type=ExperienceType.PATTERN)

        assert len(patterns2) == pattern_count1, "Patterns should persist across restart"

    def test_no_memory_leaks_over_extended_runs(self, tmp_path):
        """No memory leaks over 100 runs."""
        import os

        import psutil
        from doc_analyzer import DocumentationAnalyzer

        process = psutil.Process(os.getpid())

        agent = DocumentationAnalyzer(enable_memory=True)
        agent.memory.clear()

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "doc.md").write_text("# Doc\nContent.")

        # Measure initial memory
        initial_memory_mb = process.memory_info().rss / 1024 / 1024

        # Run 100 times
        for _ in range(100):
            agent.execute(target=docs)

        # Measure final memory
        final_memory_mb = process.memory_info().rss / 1024 / 1024

        # Should not grow significantly (allow 50MB growth)
        memory_growth = final_memory_mb - initial_memory_mb

        assert memory_growth < 50, f"Memory grew by {memory_growth:.1f}MB over 100 runs"
