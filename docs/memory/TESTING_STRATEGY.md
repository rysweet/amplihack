# Comprehensive Testing Strategy for Memory-Enabled Goal-Seeking Agents

## Executive Summary

This document defines the comprehensive testing strategy for memory-enabled goal-seeking agents. The strategy follows the testing pyramid (60% unit, 30% integration, 10% E2E), applies outside-in testing methodology, and integrates with the gadugi-agentic-test framework for agent learning validation.

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Pyramid Architecture](#test-pyramid-architecture)
3. [Memory Library Core Tests](#memory-library-core-tests)
4. [Agent Learning Tests](#agent-learning-tests)
5. [Outside-In Testing Scenarios](#outside-in-testing-scenarios)
6. [gadugi-agentic-test Integration](#gadugi-agentic-test-integration)
7. [Performance Benchmarks](#performance-benchmarks)
8. [Security Tests](#security-tests)
9. [Test Automation Strategy](#test-automation-strategy)

---

## Testing Philosophy

### Core Principles

1. **Strategic Coverage Over 100% Coverage**: Focus on critical paths, error handling, and boundaries
2. **Fast Tests**: Unit tests <100ms, integration tests <1s, E2E tests <30s
3. **Isolated Tests**: No cross-test dependencies, repeatable results
4. **Measurable Learning**: Every agent test must measure learning metrics
5. **Outside-In Approach**: Start with real user scenarios, derive implementation tests

### Anti-Patterns to Avoid

- ❌ Testing implementation details instead of behavior
- ❌ Flaky or time-dependent tests
- ❌ Tests that don't validate learning improvement
- ❌ Over-reliance on mocks for memory operations
- ❌ Missing error case and boundary tests

---

## Test Pyramid Architecture

```
        ┌─────────────────┐
        │   E2E Tests     │  10% - Full agent execution with memory
        │   (~20 tests)   │  Validate real-world learning scenarios
        └─────────────────┘
              ▲
              │
        ┌─────────────────────┐
        │ Integration Tests   │  30% - Real Kùzu database operations
        │    (~60 tests)      │  Memory pipelines + agent interactions
        └─────────────────────┘
              ▲
              │
        ┌───────────────────────────┐
        │    Unit Tests             │  60% - Components in isolation
        │    (~120 tests)           │  Core classes, validators, queries
        └───────────────────────────┘

Total: ~200 tests targeting >80% coverage
```

### Coverage Targets

| Layer       | Tests   | Coverage            | Execution Time |
| ----------- | ------- | ------------------- | -------------- |
| Unit        | 120     | Core logic 90%+     | <10s total     |
| Integration | 60      | Pipelines 85%+      | <60s total     |
| E2E         | 20      | Critical paths 70%+ | <10min total   |
| **Total**   | **200** | **>80% overall**    | **<12min**     |

---

## Memory Library Core Tests

### 1. Unit Tests (60% - ~72 tests)

#### 1.1 MemoryCoordinator Tests

**File**: `tests/memory/unit/test_memory_coordinator.py`

```python
"""Unit tests for MemoryCoordinator - the main memory interface."""

import pytest
from datetime import datetime, timedelta
from amplihack.memory.coordinator import MemoryCoordinator
from amplihack.memory.models import MemoryEntry, MemoryType, MemoryQuery


class TestMemoryCoordinatorStore:
    """Test memory storage operations (<100ms)."""

    def test_store_episodic_memory_creates_entry(self, mock_backend):
        """Test storing episodic memory creates valid entry."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)

        # ACT
        result = coordinator.store(
            memory_type=MemoryType.EPISODIC,
            title="User asked about authentication",
            content="Discussion about JWT vs session-based auth",
            session_id="sess_123",
            agent_id="architect",
            metadata={"topic": "security"}
        )

        # ASSERT
        assert result.success is True
        assert result.memory_id is not None
        assert result.execution_time_ms < 500
        mock_backend.store.assert_called_once()

    def test_store_with_importance_scoring(self, mock_backend):
        """Test importance is correctly calculated during storage."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend, use_review=True)

        # ACT
        result = coordinator.store(
            memory_type=MemoryType.SEMANTIC,
            title="Critical security vulnerability found",
            content="SQL injection vulnerability in login endpoint",
            session_id="sess_456",
            agent_id="security",
            metadata={"severity": "critical"}
        )

        # ASSERT - High importance for critical findings
        stored_entry = mock_backend.store.call_args[0][0]
        assert stored_entry.importance >= 8
        assert result.execution_time_ms < 500

    def test_store_procedural_with_steps(self, mock_backend):
        """Test storing procedural memory with execution steps."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)

        # ACT
        result = coordinator.store(
            memory_type=MemoryType.PROCEDURAL,
            title="How to fix import errors",
            content="1. Check dependencies\n2. Verify PYTHONPATH\n3. Restart IDE",
            session_id="sess_789",
            agent_id="builder",
            metadata={"success_rate": 0.95}
        )

        # ASSERT
        assert result.success is True
        stored_entry = mock_backend.store.call_args[0][0]
        assert "1." in stored_entry.content
        assert stored_entry.memory_type == MemoryType.PROCEDURAL

    def test_store_fails_gracefully_on_invalid_input(self, mock_backend):
        """Test error handling for invalid memory entries."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)

        # ACT
        result = coordinator.store(
            memory_type=MemoryType.EPISODIC,
            title="",  # Invalid: empty title
            content="Some content",
            session_id="sess_999",
            agent_id="test"
        )

        # ASSERT
        assert result.success is False
        assert "title" in result.error.lower()
        mock_backend.store.assert_not_called()


class TestMemoryCoordinatorRetrieve:
    """Test memory retrieval operations (<50ms without review)."""

    def test_retrieve_by_session_id(self, mock_backend):
        """Test retrieving all memories for a session."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        mock_backend.query.return_value = [
            create_mock_memory("mem_1", "sess_100"),
            create_mock_memory("mem_2", "sess_100"),
        ]

        # ACT
        result = coordinator.retrieve(
            query=MemoryQuery(session_id="sess_100")
        )

        # ASSERT
        assert len(result.memories) == 2
        assert result.execution_time_ms < 50
        assert all(m.session_id == "sess_100" for m in result.memories)

    def test_retrieve_by_memory_type(self, mock_backend):
        """Test filtering by memory type."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        mock_backend.query.return_value = [
            create_mock_memory("mem_3", "sess_200", MemoryType.SEMANTIC),
        ]

        # ACT
        result = coordinator.retrieve(
            query=MemoryQuery(memory_type=MemoryType.SEMANTIC)
        )

        # ASSERT
        assert len(result.memories) == 1
        assert result.memories[0].memory_type == MemoryType.SEMANTIC

    def test_retrieve_with_content_search(self, mock_backend):
        """Test full-text search functionality."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        mock_backend.query.return_value = [
            create_mock_memory("mem_4", "sess_300", content="authentication flow"),
        ]

        # ACT
        result = coordinator.retrieve(
            query=MemoryQuery(content_search="authentication")
        )

        # ASSERT
        assert len(result.memories) == 1
        assert "authentication" in result.memories[0].content.lower()

    def test_retrieve_with_importance_threshold(self, mock_backend):
        """Test filtering by importance score."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        mock_backend.query.return_value = [
            create_mock_memory("mem_5", "sess_400", importance=9),
            create_mock_memory("mem_6", "sess_400", importance=8),
        ]

        # ACT
        result = coordinator.retrieve(
            query=MemoryQuery(min_importance=8)
        )

        # ASSERT
        assert len(result.memories) == 2
        assert all(m.importance >= 8 for m in result.memories)

    def test_retrieve_empty_results(self, mock_backend):
        """Test handling of no matching memories."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        mock_backend.query.return_value = []

        # ACT
        result = coordinator.retrieve(
            query=MemoryQuery(session_id="nonexistent")
        )

        # ASSERT
        assert len(result.memories) == 0
        assert result.success is True


class TestMemoryCoordinatorWorkingMemory:
    """Test working memory operations (temporary context)."""

    def test_clear_working_memory_for_session(self, mock_backend):
        """Test clearing working memory at session boundaries."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)

        # ACT
        result = coordinator.clear_working_memory(session_id="sess_500")

        # ASSERT
        assert result.success is True
        mock_backend.delete_by_query.assert_called_once()

    def test_working_memory_auto_expires(self, mock_backend):
        """Test working memory expires after timeout."""
        # ARRANGE
        coordinator = MemoryCoordinator(backend=mock_backend)
        past_time = datetime.now() - timedelta(hours=2)

        # Store working memory with expiration
        coordinator.store(
            memory_type=MemoryType.WORKING,
            title="Temporary context",
            content="Active task state",
            session_id="sess_600",
            agent_id="builder",
            expires_at=past_time
        )

        # ACT - Query should exclude expired memories
        result = coordinator.retrieve(
            query=MemoryQuery(
                session_id="sess_600",
                memory_type=MemoryType.WORKING,
                include_expired=False
            )
        )

        # ASSERT
        assert len(result.memories) == 0


# Additional unit test classes:
# - TestStoragePipeline (12 tests)
# - TestRetrievalPipeline (12 tests)
# - TestMemoryQuery (8 tests)
# - TestMemoryEntry (8 tests)
# - TestKuzuBackend (12 tests)
# - TestSQLiteBackend (12 tests)

# Total: 72 unit tests
```

**Test Fixtures** (`conftest.py`):

```python
"""Shared test fixtures for memory system tests."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock
from amplihack.memory.models import MemoryEntry, MemoryType


@pytest.fixture
def mock_backend():
    """Mock memory backend for unit tests."""
    backend = MagicMock()
    backend.store.return_value = "mock_memory_id"
    backend.query.return_value = []
    backend.delete.return_value = True
    return backend


@pytest.fixture
def sample_memory_entry():
    """Sample memory entry for testing."""
    return MemoryEntry(
        id="mem_test_001",
        session_id="sess_test",
        agent_id="test_agent",
        memory_type=MemoryType.EPISODIC,
        title="Test Memory",
        content="Sample content for testing",
        metadata={"test": True},
        created_at=datetime.now(),
        accessed_at=datetime.now(),
        importance=5
    )


def create_mock_memory(
    memory_id: str,
    session_id: str,
    memory_type: MemoryType = MemoryType.EPISODIC,
    importance: int = 5,
    content: str = "Test content"
) -> MemoryEntry:
    """Helper to create mock memory entries."""
    return MemoryEntry(
        id=memory_id,
        session_id=session_id,
        agent_id="test_agent",
        memory_type=memory_type,
        title="Test Memory",
        content=content,
        metadata={},
        created_at=datetime.now(),
        accessed_at=datetime.now(),
        importance=importance
    )
```

#### 1.2 Security Capability Tests

**File**: `tests/memory/unit/test_security_capabilities.py`

```python
"""Security tests for memory system capabilities."""

import pytest
from amplihack.memory.models import MemoryQuery


class TestSecurityEnforcement:
    """Test capability-based security enforcement."""

    def test_query_injection_prevention(self):
        """Test SQL injection prevention in queries."""
        # ARRANGE - Malicious input
        malicious_session_id = "sess_1'; DROP TABLE memory_entries; --"

        # ACT & ASSERT - Should raise validation error
        with pytest.raises(ValueError, match="invalid characters"):
            MemoryQuery(session_id=malicious_session_id)

    def test_limit_boundary_enforcement(self):
        """Test query limit boundaries prevent DOS."""
        # ACT & ASSERT - Should reject excessive limits
        with pytest.raises(ValueError, match="limit must be"):
            MemoryQuery(limit=100000)

        with pytest.raises(ValueError, match="limit must be"):
            MemoryQuery(limit=-1)

    def test_agent_id_isolation(self, mock_backend):
        """Test agents can only access their own memories."""
        # ARRANGE
        from amplihack.memory.coordinator import MemoryCoordinator
        coordinator = MemoryCoordinator(backend=mock_backend)

        # ACT - Try to access another agent's memories
        result = coordinator.retrieve(
            query=MemoryQuery(agent_id="other_agent"),
            requesting_agent_id="current_agent",
            enforce_isolation=True
        )

        # ASSERT - Should be blocked
        assert result.success is False
        assert "permission denied" in result.error.lower()

    def test_session_boundary_enforcement(self, mock_backend):
        """Test memories don't leak across sessions."""
        # Implementation validates session boundaries
        pass
```

---

### 2. Integration Tests (30% - ~60 tests)

#### 2.1 Real Kùzu Database Tests

**File**: `tests/memory/integration/test_kuzu_integration.py`

```python
"""Integration tests with real Kùzu database."""

import pytest
from pathlib import Path
from amplihack.memory.backends.kuzu_backend import KuzuBackend
from amplihack.memory.coordinator import MemoryCoordinator
from amplihack.memory.models import MemoryType, MemoryQuery


@pytest.mark.integration
class TestKuzuBackendIntegration:
    """Test MemoryCoordinator with real Kùzu backend."""

    @pytest.fixture
    def kuzu_coordinator(self, tmp_path):
        """Create coordinator with real Kùzu database."""
        db_path = tmp_path / "test_kuzu_db"
        backend = KuzuBackend(database_path=str(db_path))
        backend.initialize()
        return MemoryCoordinator(backend=backend)

    def test_store_and_retrieve_roundtrip(self, kuzu_coordinator):
        """Test storing and retrieving from real database."""
        # ARRANGE & ACT - Store
        store_result = kuzu_coordinator.store(
            memory_type=MemoryType.EPISODIC,
            title="Integration test memory",
            content="Testing with real Kùzu database",
            session_id="integration_sess_1",
            agent_id="test_agent",
            metadata={"test_type": "integration"}
        )

        # ACT - Retrieve
        retrieve_result = kuzu_coordinator.retrieve(
            query=MemoryQuery(session_id="integration_sess_1")
        )

        # ASSERT
        assert store_result.success is True
        assert len(retrieve_result.memories) == 1
        assert retrieve_result.memories[0].title == "Integration test memory"

    def test_concurrent_writes_consistency(self, kuzu_coordinator):
        """Test multiple concurrent writes maintain consistency."""
        # ARRANGE - Multiple agents writing simultaneously
        import threading

        results = []
        def store_memory(agent_num):
            result = kuzu_coordinator.store(
                memory_type=MemoryType.SEMANTIC,
                title=f"Memory from agent {agent_num}",
                content=f"Content {agent_num}",
                session_id="concurrent_sess",
                agent_id=f"agent_{agent_num}"
            )
            results.append(result)

        # ACT - Concurrent writes
        threads = [threading.Thread(target=store_memory, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # ASSERT - All writes successful
        assert all(r.success for r in results)

        # Verify all memories stored
        retrieve_result = kuzu_coordinator.retrieve(
            query=MemoryQuery(session_id="concurrent_sess")
        )
        assert len(retrieve_result.memories) == 5

    def test_full_text_search_with_kuzu(self, kuzu_coordinator):
        """Test full-text search capabilities."""
        # ARRANGE - Store multiple memories
        topics = ["authentication", "authorization", "encryption"]
        for topic in topics:
            kuzu_coordinator.store(
                memory_type=MemoryType.SEMANTIC,
                title=f"Security: {topic}",
                content=f"Discussion about {topic} implementation",
                session_id="search_sess",
                agent_id="security"
            )

        # ACT - Search for specific topic
        result = kuzu_coordinator.retrieve(
            query=MemoryQuery(content_search="authentication")
        )

        # ASSERT
        assert len(result.memories) >= 1
        assert any("authentication" in m.content.lower() for m in result.memories)


@pytest.mark.integration
class TestMemoryPipelineIntegration:
    """Test complete memory pipelines with real database."""

    def test_storage_pipeline_with_agent_review(self, kuzu_coordinator):
        """Test storage pipeline including agent review."""
        # This would test the full storage pipeline with:
        # 1. Input validation
        # 2. Agent review for importance scoring
        # 3. Database storage
        # 4. Verification query
        pass

    def test_retrieval_pipeline_with_relevance_scoring(self, kuzu_coordinator):
        """Test retrieval with agent-based relevance scoring."""
        # This would test the full retrieval pipeline with:
        # 1. Initial query
        # 2. Agent review for relevance
        # 3. Ranked results
        pass


# Additional integration test classes:
# - TestCrossSessionMemoryAccess (8 tests)
# - TestMemoryMaintenance (8 tests)
# - TestBackupAndRestore (6 tests)
# - TestMigrationScenarios (6 tests)

# Total: 60 integration tests
```

#### 2.2 Performance Benchmarks

**File**: `tests/memory/integration/test_performance.py`

```python
"""Performance benchmark tests for memory system (NFR1: <50ms retrieval)."""

import pytest
import time
from amplihack.memory.models import MemoryQuery


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Benchmark critical memory operations."""

    def test_retrieve_without_review_under_50ms(self, kuzu_coordinator):
        """Test retrieval completes in <50ms (NFR1)."""
        # ARRANGE - Pre-populate with 100 memories
        for i in range(100):
            kuzu_coordinator.store(
                memory_type=MemoryType.EPISODIC,
                title=f"Memory {i}",
                content=f"Content for memory {i}",
                session_id="perf_sess",
                agent_id="test_agent"
            )

        # ACT - Time retrieval
        start = time.perf_counter()
        result = kuzu_coordinator.retrieve(
            query=MemoryQuery(session_id="perf_sess", limit=10)
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        # ASSERT - Must complete in <50ms
        assert elapsed_ms < 50, f"Retrieval took {elapsed_ms:.2f}ms, exceeds 50ms limit"
        assert len(result.memories) == 10

    def test_store_with_review_under_500ms(self, kuzu_coordinator):
        """Test storage with agent review completes in <500ms."""
        # ACT - Time storage with review
        start = time.perf_counter()
        result = kuzu_coordinator.store(
            memory_type=MemoryType.SEMANTIC,
            title="Performance test",
            content="Testing storage with agent review",
            session_id="perf_sess_2",
            agent_id="test_agent",
            use_review=True
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        # ASSERT
        assert elapsed_ms < 500, f"Storage took {elapsed_ms:.2f}ms, exceeds 500ms limit"
        assert result.success is True

    def test_query_performance_scales_linearly(self, kuzu_coordinator):
        """Test query performance scales with dataset size."""
        # Test with 100, 1000, 10000 records
        # Verify O(log n) or better performance
        pass
```

---

### 3. E2E Tests (10% - ~20 tests)

**File**: `tests/memory/e2e/test_agent_memory_workflows.py`

```python
"""End-to-end tests for agent memory workflows."""

import pytest
from pathlib import Path


@pytest.mark.e2e
class TestAgentMemoryWorkflows:
    """Test complete agent workflows with memory."""

    def test_multi_session_learning_workflow(self, kuzu_coordinator):
        """Test agent learns across multiple sessions."""
        # SESSION 1: Agent encounters problem
        kuzu_coordinator.store(
            memory_type=MemoryType.EPISODIC,
            title="Import error encountered",
            content="Failed to import module 'foo' due to missing dependency",
            session_id="session_1",
            agent_id="builder",
            metadata={"error_type": "ImportError"}
        )

        # SESSION 1: Agent finds solution
        kuzu_coordinator.store(
            memory_type=MemoryType.PROCEDURAL,
            title="Fix for import errors",
            content="1. Check requirements.txt\n2. Run pip install\n3. Verify import",
            session_id="session_1",
            agent_id="builder",
            metadata={"success": True}
        )

        # SESSION 2: Agent encounters similar problem
        # Should retrieve procedural memory from session 1
        relevant_memories = kuzu_coordinator.retrieve(
            query=MemoryQuery(
                agent_id="builder",
                memory_type=MemoryType.PROCEDURAL,
                content_search="import error"
            )
        )

        # ASSERT - Agent has learned
        assert len(relevant_memories.memories) >= 1
        assert "pip install" in relevant_memories.memories[0].content

    def test_cross_agent_knowledge_sharing(self, kuzu_coordinator):
        """Test agents share knowledge through semantic memory."""
        # Architect stores design decision
        kuzu_coordinator.store(
            memory_type=MemoryType.SEMANTIC,
            title="Authentication design: JWT tokens",
            content="Decided to use JWT tokens for stateless authentication",
            session_id="session_design",
            agent_id="architect",
            metadata={"decision": True}
        )

        # Builder queries for authentication approach
        relevant = kuzu_coordinator.retrieve(
            query=MemoryQuery(
                content_search="authentication",
                memory_type=MemoryType.SEMANTIC
            )
        )

        # ASSERT - Knowledge transferred
        assert len(relevant.memories) >= 1
        assert "JWT" in relevant.memories[0].content

# Additional E2E test classes:
# - TestHookIntegration (6 tests)
# - TestFullAgentExecution (4 tests)

# Total: 20 E2E tests
```

---

## Agent Learning Tests

### Learning Metrics Definition

```python
"""Dataclass for measuring agent learning metrics."""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class LearningMetrics:
    """Metrics for measuring agent learning improvement."""

    # Efficiency Metrics
    task_completion_time_ms: float
    api_calls_made: int
    tokens_consumed: int

    # Quality Metrics
    solution_quality_score: float  # 0-100
    error_rate: float  # Percentage
    success_on_first_attempt: bool

    # Learning Indicators
    relevant_memories_retrieved: int
    relevant_memories_used: int
    new_patterns_learned: int
    procedural_memories_stored: int

    # Comparison Metrics
    improvement_vs_first_run: float  # Percentage
    memory_hit_rate: float  # Percentage

    def calculate_learning_score(self) -> float:
        """Calculate overall learning score (0-100)."""
        # Weight different factors
        efficiency_score = min(100, 100 / (self.task_completion_time_ms / 1000))
        quality_score = self.solution_quality_score
        memory_usage_score = (self.memory_hit_rate / 100) * 100

        # Weighted average
        return (
            efficiency_score * 0.3 +
            quality_score * 0.5 +
            memory_usage_score * 0.2
        )
```

### Agent 1: Document Analyzer

**Learning Goal**: Improve documentation analysis quality and speed over time.

**File**: `tests/agents/test_doc_analyzer_learning.py`

```python
"""Learning tests for Document Analyzer agent."""

import pytest
from amplihack.memory.coordinator import MemoryCoordinator
from amplihack.agents.doc_analyzer import DocumentAnalyzerAgent


@pytest.mark.agent_learning
class TestDocumentAnalyzerLearning:
    """Validate Document Analyzer learns from experience."""

    def test_analyzer_improves_on_second_analysis(self, kuzu_coordinator):
        """Test analyzer is faster and better on second analysis."""
        # ARRANGE
        agent = DocumentAnalyzerAgent(memory=kuzu_coordinator)
        doc_content = load_sample_doc("ms_learn_authentication.md")

        # ACT - First Analysis (no prior memory)
        metrics_run1 = agent.analyze(
            document=doc_content,
            session_id="analyzer_session_1"
        )

        # ACT - Second Analysis (with memory from run 1)
        metrics_run2 = agent.analyze(
            document=doc_content,
            session_id="analyzer_session_2"
        )

        # ASSERT - Learning improvements
        assert metrics_run2.task_completion_time_ms < metrics_run1.task_completion_time_ms
        assert metrics_run2.solution_quality_score >= metrics_run1.solution_quality_score
        assert metrics_run2.relevant_memories_retrieved > 0
        assert metrics_run2.memory_hit_rate > 0

        # Calculate learning score
        learning_improvement = (
            (metrics_run1.task_completion_time_ms - metrics_run2.task_completion_time_ms)
            / metrics_run1.task_completion_time_ms
        ) * 100

        assert learning_improvement > 10, f"Expected >10% improvement, got {learning_improvement:.1f}%"

    def test_analyzer_learns_documentation_patterns(self, kuzu_coordinator):
        """Test analyzer stores and reuses documentation patterns."""
        # ARRANGE
        agent = DocumentAnalyzerAgent(memory=kuzu_coordinator)

        # ACT - Analyze multiple similar documents
        docs = [
            "ms_learn_auth.md",
            "ms_learn_storage.md",
            "ms_learn_compute.md"
        ]

        metrics_by_doc = []
        for doc_file in docs:
            doc_content = load_sample_doc(doc_file)
            metrics = agent.analyze(document=doc_content, session_id=f"sess_{doc_file}")
            metrics_by_doc.append(metrics)

        # ASSERT - Progressive improvement
        assert metrics_by_doc[1].task_completion_time_ms < metrics_by_doc[0].task_completion_time_ms
        assert metrics_by_doc[2].task_completion_time_ms < metrics_by_doc[1].task_completion_time_ms

        # Check pattern learning
        pattern_memories = kuzu_coordinator.retrieve(
            query=MemoryQuery(
                agent_id="doc_analyzer",
                memory_type=MemoryType.SEMANTIC,
                content_search="documentation pattern"
            )
        )
        assert len(pattern_memories.memories) > 0

    def test_analyzer_cross_session_memory_persistence(self, kuzu_coordinator):
        """Test analyzer retrieves relevant memories across sessions."""
        # SESSION 1: Analyze authentication docs
        agent = DocumentAnalyzerAgent(memory=kuzu_coordinator)
        agent.analyze(
            document=load_sample_doc("authentication.md"),
            session_id="session_1"
        )

        # SESSION 2: Analyze authorization docs (related topic)
        metrics = agent.analyze(
            document=load_sample_doc("authorization.md"),
            session_id="session_2"
        )

        # ASSERT - Should retrieve relevant memories from session 1
        assert metrics.relevant_memories_retrieved > 0
        assert metrics.relevant_memories_used > 0
```

### Agent 2: Pattern Recognizer

**Learning Goal**: Recognize patterns faster and more accurately on repeated codebases.

**File**: `tests/agents/test_pattern_recognizer_learning.py`

```python
"""Learning tests for Pattern Recognizer agent."""

import pytest
from amplihack.agents.pattern_recognizer import PatternRecognizerAgent


@pytest.mark.agent_learning
class TestPatternRecognizerLearning:
    """Validate Pattern Recognizer learns from experience."""

    def test_recognizer_identifies_patterns_faster_second_time(self, kuzu_coordinator, tmp_path):
        """Test pattern recognition speed improves on repeated analysis."""
        # ARRANGE
        agent = PatternRecognizerAgent(memory=kuzu_coordinator)
        codebase_path = create_sample_codebase(tmp_path)

        # ACT - First Analysis
        metrics_run1 = agent.analyze_patterns(
            codebase_path=codebase_path,
            session_id="pattern_session_1"
        )

        # ACT - Second Analysis (same codebase)
        metrics_run2 = agent.analyze_patterns(
            codebase_path=codebase_path,
            session_id="pattern_session_2"
        )

        # ASSERT - Speed improvement
        speedup = (
            (metrics_run1.task_completion_time_ms - metrics_run2.task_completion_time_ms)
            / metrics_run1.task_completion_time_ms
        ) * 100

        assert speedup > 20, f"Expected >20% speedup, got {speedup:.1f}%"
        assert metrics_run2.relevant_memories_retrieved > 0

    def test_recognizer_improves_pattern_accuracy(self, kuzu_coordinator, tmp_path):
        """Test pattern recognition accuracy improves with experience."""
        # ARRANGE
        agent = PatternRecognizerAgent(memory=kuzu_coordinator)

        # Train on multiple codebases
        training_codebases = [
            create_codebase_with_singleton_pattern(tmp_path / "cb1"),
            create_codebase_with_factory_pattern(tmp_path / "cb2"),
            create_codebase_with_observer_pattern(tmp_path / "cb3"),
        ]

        for i, codebase in enumerate(training_codebases):
            agent.analyze_patterns(codebase, session_id=f"training_{i}")

        # ACT - Test on new codebase with mixed patterns
        test_codebase = create_codebase_with_mixed_patterns(tmp_path / "test")
        metrics = agent.analyze_patterns(test_codebase, session_id="test")

        # ASSERT - High accuracy due to learned patterns
        assert metrics.solution_quality_score > 85
        assert metrics.relevant_memories_used >= 3  # Used learned patterns
```

### Agent 3: Bug Predictor

**Learning Goal**: Predict bugs more accurately based on historical data.

**File**: `tests/agents/test_bug_predictor_learning.py`

```python
"""Learning tests for Bug Predictor agent."""

import pytest
from amplihack.agents.bug_predictor import BugPredictorAgent


@pytest.mark.agent_learning
class TestBugPredictorLearning:
    """Validate Bug Predictor learns from historical bugs."""

    def test_predictor_learns_from_known_bugs(self, kuzu_coordinator, tmp_path):
        """Test predictor improves accuracy using historical bug data."""
        # ARRANGE
        agent = BugPredictorAgent(memory=kuzu_coordinator)

        # Store historical bug patterns
        historical_bugs = [
            {"pattern": "unvalidated input", "bug_type": "sql_injection", "severity": "critical"},
            {"pattern": "missing null check", "bug_type": "null_pointer", "severity": "high"},
            {"pattern": "race condition", "bug_type": "concurrency", "severity": "high"},
        ]

        for bug in historical_bugs:
            kuzu_coordinator.store(
                memory_type=MemoryType.SEMANTIC,
                title=f"Bug pattern: {bug['pattern']}",
                content=f"Pattern leads to {bug['bug_type']}",
                session_id="bug_training",
                agent_id="bug_predictor",
                metadata=bug
            )

        # ACT - Predict bugs in code with known patterns
        test_code = """
        def process_user_input(user_input):
            query = f"SELECT * FROM users WHERE id = {user_input}"
            db.execute(query)  # SQL injection vulnerability
        """

        predictions = agent.predict_bugs(
            code=test_code,
            session_id="bug_prediction"
        )

        # ASSERT - Should predict SQL injection based on learned pattern
        assert len(predictions.predicted_bugs) > 0
        assert any(bug.bug_type == "sql_injection" for bug in predictions.predicted_bugs)
        assert predictions.relevant_memories_used > 0

    def test_predictor_accuracy_improves_with_feedback(self, kuzu_coordinator):
        """Test predictor learns from prediction feedback."""
        # ARRANGE
        agent = BugPredictorAgent(memory=kuzu_coordinator)

        # Make prediction
        code = "def unsafe_operation(data): return eval(data)"
        predictions = agent.predict_bugs(code, session_id="pred_1")

        # Provide feedback (prediction was correct)
        agent.record_prediction_feedback(
            prediction_id=predictions.prediction_id,
            was_correct=True,
            actual_bug_type="code_injection"
        )

        # ACT - Make similar prediction
        similar_code = "def another_unsafe(input): exec(input)"
        new_predictions = agent.predict_bugs(similar_code, session_id="pred_2")

        # ASSERT - Should have higher confidence due to feedback
        assert new_predictions.solution_quality_score > predictions.solution_quality_score
```

### Agent 4: Performance Optimizer

**Learning Goal**: Apply learned optimization strategies more effectively.

**File**: `tests/agents/test_performance_optimizer_learning.py`

```python
"""Learning tests for Performance Optimizer agent."""

import pytest
from amplihack.agents.performance_optimizer import PerformanceOptimizerAgent


@pytest.mark.agent_learning
class TestPerformanceOptimizerLearning:
    """Validate Performance Optimizer learns effective strategies."""

    def test_optimizer_reuses_successful_strategies(self, kuzu_coordinator):
        """Test optimizer reuses strategies that worked in the past."""
        # ARRANGE
        agent = PerformanceOptimizerAgent(memory=kuzu_coordinator)

        # Store successful optimization
        kuzu_coordinator.store(
            memory_type=MemoryType.PROCEDURAL,
            title="Optimize database queries with indexing",
            content="Added index on user_id column, reduced query time 80%",
            session_id="optimization_1",
            agent_id="optimizer",
            metadata={"success_rate": 0.95, "improvement_pct": 80}
        )

        # ACT - Optimize similar slow query
        slow_code = """
        def get_user_posts(user_id):
            return db.query("SELECT * FROM posts WHERE user_id = ?", user_id)
        """

        optimization = agent.optimize(
            code=slow_code,
            performance_issue="slow database query",
            session_id="optimization_2"
        )

        # ASSERT - Should apply learned indexing strategy
        assert "index" in optimization.suggested_changes.lower()
        assert optimization.relevant_memories_used > 0
        assert optimization.confidence_score > 0.7

    def test_optimizer_learns_optimization_effectiveness(self, kuzu_coordinator):
        """Test optimizer tracks which optimizations work best."""
        # Test multiple optimization attempts, record results
        # Verify optimizer preferences strategies with higher success rates
        pass
```

---

## Outside-In Testing Scenarios

### Scenario Structure

Each scenario follows the outside-in approach:

1. **User Goal**: What the user wants to accomplish
2. **Expected Behavior**: What the agent should do
3. **Learning Validation**: How to measure improvement
4. **Memory Verification**: Check memory operations

### Scenario 1: Document Analysis Flow

```python
"""Outside-in test: User wants to understand MS Learn documentation."""

def test_user_analyzes_ms_learn_docs(kuzu_coordinator):
    """
    USER GOAL: Understand Azure authentication documentation

    EXPECTED BEHAVIOR:
    1. Agent analyzes document
    2. Stores key concepts in semantic memory
    3. On second document, retrieves related concepts
    4. Provides better analysis faster
    """
    # First document
    agent = DocumentAnalyzerAgent(memory=kuzu_coordinator)
    result1 = agent.analyze_for_user(
        document_url="https://learn.microsoft.com/azure/auth",
        user_query="How does Azure authentication work?"
    )

    # Verify user gets useful answer
    assert result1.summary is not None
    assert len(result1.key_concepts) > 0

    # Verify learning happened
    memories = kuzu_coordinator.retrieve(
        query=MemoryQuery(agent_id="doc_analyzer", memory_type=MemoryType.SEMANTIC)
    )
    assert len(memories.memories) > 0

    # Second document (related topic)
    result2 = agent.analyze_for_user(
        document_url="https://learn.microsoft.com/azure/rbac",
        user_query="How does Azure authorization work?"
    )

    # Verify improvement
    assert result2.processing_time < result1.processing_time
    assert result2.cross_references_count > 0  # References auth concepts from memory
```

### Scenario 2: Pattern Recognition Flow

```python
"""Outside-in test: User wants to identify design patterns in codebase."""

def test_user_identifies_design_patterns(kuzu_coordinator, sample_codebase):
    """
    USER GOAL: Find design patterns in large codebase

    EXPECTED BEHAVIOR:
    1. First analysis is thorough but slow
    2. Agent stores pattern signatures
    3. Second analysis on similar codebase is much faster
    4. Accuracy improves with experience
    """
    agent = PatternRecognizerAgent(memory=kuzu_coordinator)

    # First codebase analysis
    result1 = agent.find_patterns_for_user(
        codebase_path=sample_codebase,
        user_query="What design patterns are used here?"
    )

    assert len(result1.patterns_found) > 0
    assert result1.confidence_scores is not None

    # Second codebase (different but similar patterns)
    result2 = agent.find_patterns_for_user(
        codebase_path=create_similar_codebase(),
        user_query="What design patterns are used here?"
    )

    # Verify learning
    assert result2.analysis_time < result1.analysis_time * 0.8  # 20% faster
    assert result2.patterns_found >= result1.patterns_found
```

### Scenario 3: Bug Prediction Flow

```python
"""Outside-in test: User wants to find potential bugs before they occur."""

def test_user_predicts_bugs_in_code(kuzu_coordinator):
    """
    USER GOAL: Identify potential bugs in new code

    EXPECTED BEHAVIOR:
    1. Agent analyzes code for bug patterns
    2. Compares against historical bug database
    3. Provides predictions with confidence scores
    4. Learns from feedback when bugs are confirmed/rejected
    """
    agent = BugPredictorAgent(memory=kuzu_coordinator)

    # User submits code for review
    user_code = load_code_snippet("new_feature.py")
    predictions = agent.predict_bugs_for_user(
        code=user_code,
        context="New authentication endpoint"
    )

    assert len(predictions.potential_bugs) > 0
    assert all(bug.confidence_score is not None for bug in predictions.potential_bugs)

    # User confirms some bugs were real
    agent.receive_user_feedback(
        prediction_id=predictions.id,
        confirmed_bugs=[predictions.potential_bugs[0]],
        false_positives=[predictions.potential_bugs[1]]
    )

    # Next prediction should be more accurate
    result2 = agent.predict_bugs_for_user(
        code=load_code_snippet("another_feature.py"),
        context="Another authentication endpoint"
    )

    assert result2.accuracy_improved is True
```

### Scenario 4: Performance Optimization Flow

```python
"""Outside-in test: User wants to optimize slow code."""

def test_user_optimizes_slow_code(kuzu_coordinator):
    """
    USER GOAL: Make slow code faster

    EXPECTED BEHAVIOR:
    1. Agent analyzes performance bottleneck
    2. Retrieves similar optimization cases from memory
    3. Suggests proven optimization strategies
    4. Tracks effectiveness for future use
    """
    agent = PerformanceOptimizerAgent(memory=kuzu_coordinator)

    # User reports slow code
    slow_code = """
    def process_all_users():
        users = get_all_users()  # Returns 1M users
        for user in users:
            process_user(user)  # Individual DB call
    """

    optimization = agent.optimize_for_user(
        code=slow_code,
        performance_data={"execution_time": 30000, "bottleneck": "database"},
        user_goal="Reduce execution time to < 1 second"
    )

    assert optimization.suggested_changes is not None
    assert optimization.expected_improvement_pct > 50
    assert "batch" in optimization.suggested_changes.lower() or "cache" in optimization.suggested_changes.lower()

    # User implements optimization, reports results
    agent.record_optimization_result(
        optimization_id=optimization.id,
        actual_improvement_pct=85,
        was_successful=True
    )

    # Next similar case should use this successful strategy
    next_optimization = agent.optimize_for_user(
        code=create_similar_slow_code(),
        performance_data={"execution_time": 25000, "bottleneck": "database"},
        user_goal="Make it faster"
    )

    assert next_optimization.confidence_score > optimization.confidence_score
```

---

## gadugi-agentic-test Integration

### Test Scenario Definitions

**File**: `tests/gadugi_scenarios/memory_agent_scenarios.yaml`

```yaml
# Gadugi test scenarios for memory-enabled agents

scenarios:
  - name: "doc_analyzer_learning"
    agent: "document_analyzer"
    category: "learning_validation"
    priority: "high"
    description: "Validate document analyzer improves over multiple sessions"

    setup:
      - create_memory_database: "test_doc_analyzer_db"
      - load_sample_documents:
          - "azure_auth.md"
          - "azure_rbac.md"
          - "azure_storage.md"

    test_steps:
      - name: "Baseline Analysis"
        action: "analyze_document"
        document: "azure_auth.md"
        session_id: "baseline_session"
        collect_metrics: true

      - name: "Second Analysis"
        action: "analyze_document"
        document: "azure_rbac.md"
        session_id: "learning_session"
        collect_metrics: true

      - name: "Verify Learning"
        assertions:
          - metric: "task_completion_time_ms"
            comparison: "less_than"
            baseline: "baseline_session"
            improvement_threshold: 15 # 15% faster

          - metric: "relevant_memories_retrieved"
            comparison: "greater_than"
            value: 0

          - metric: "memory_hit_rate"
            comparison: "greater_than"
            value: 30 # 30% of retrieved memories were used

    success_criteria:
      - "Analysis time improves by >15%"
      - "Agent retrieves and uses relevant memories"
      - "Quality score maintains or improves"

  - name: "pattern_recognizer_accuracy"
    agent: "pattern_recognizer"
    category: "learning_validation"
    priority: "high"
    description: "Validate pattern recognition accuracy improves with training"

    setup:
      - create_memory_database: "test_pattern_db"
      - create_training_codebases:
          - "singleton_examples"
          - "factory_examples"
          - "observer_examples"

    test_steps:
      - name: "Train on Known Patterns"
        action: "analyze_multiple_codebases"
        codebases: ["singleton_examples", "factory_examples", "observer_examples"]
        session_id: "training"

      - name: "Test on Mixed Patterns"
        action: "analyze_codebase"
        codebase: "mixed_patterns_test"
        session_id: "validation"
        collect_metrics: true

      - name: "Verify Accuracy"
        assertions:
          - metric: "solution_quality_score"
            comparison: "greater_than"
            value: 85

          - metric: "relevant_memories_used"
            comparison: "greater_than"
            value: 3

    success_criteria:
      - "Pattern recognition accuracy >85%"
      - "Uses at least 3 learned patterns"

  - name: "bug_predictor_feedback_loop"
    agent: "bug_predictor"
    category: "learning_validation"
    priority: "high"
    description: "Validate bug predictor learns from feedback"

    setup:
      - create_memory_database: "test_bug_db"
      - load_historical_bugs: "bug_database.json"

    test_steps:
      - name: "Make Initial Predictions"
        action: "predict_bugs"
        code_samples: ["sample_1.py", "sample_2.py", "sample_3.py"]
        session_id: "predictions_1"
        collect_metrics: true

      - name: "Provide Feedback"
        action: "record_feedback"
        predictions: "predictions_1"
        actual_bugs: ["sql_injection", "null_pointer"]

      - name: "Make New Predictions"
        action: "predict_bugs"
        code_samples: ["sample_4.py", "sample_5.py"]
        session_id: "predictions_2"
        collect_metrics: true

      - name: "Verify Improvement"
        assertions:
          - metric: "solution_quality_score"
            comparison: "greater_than"
            baseline: "predictions_1"
            improvement_threshold: 10

    success_criteria:
      - "Prediction accuracy improves by >10%"
      - "Confidence scores increase for correct predictions"

  - name: "optimizer_strategy_reuse"
    agent: "performance_optimizer"
    category: "learning_validation"
    priority: "high"
    description: "Validate optimizer reuses successful strategies"

    setup:
      - create_memory_database: "test_optimizer_db"
      - load_optimization_cases: "optimization_history.json"

    test_steps:
      - name: "Optimize Similar Code"
        action: "optimize_code"
        code: "slow_database_query.py"
        session_id: "optimization_1"
        collect_metrics: true

      - name: "Verify Strategy Reuse"
        assertions:
          - metric: "relevant_memories_used"
            comparison: "greater_than"
            value: 1

          - metric: "confidence_score"
            comparison: "greater_than"
            value: 0.7

    success_criteria:
      - "Retrieves at least 1 successful strategy"
      - "Confidence score >70%"
```

### Learning Metric Collection

**File**: `tests/gadugi_scenarios/metric_collectors.py`

```python
"""Metric collection hooks for gadugi-agentic-test integration."""

from typing import Dict, Any
from amplihack.memory.models import LearningMetrics


class GadugiMetricCollector:
    """Collects learning metrics for gadugi test scenarios."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.metrics_by_step: Dict[str, LearningMetrics] = {}

    def collect_metrics(self, step_name: str, agent_result: Any) -> LearningMetrics:
        """Extract metrics from agent execution result."""
        metrics = LearningMetrics(
            task_completion_time_ms=agent_result.execution_time_ms,
            api_calls_made=agent_result.api_calls_count,
            tokens_consumed=agent_result.tokens_used,
            solution_quality_score=agent_result.quality_score,
            error_rate=agent_result.error_rate,
            success_on_first_attempt=agent_result.success,
            relevant_memories_retrieved=agent_result.memories_retrieved,
            relevant_memories_used=agent_result.memories_used,
            new_patterns_learned=agent_result.patterns_stored,
            procedural_memories_stored=agent_result.procedures_stored,
            improvement_vs_first_run=self._calculate_improvement(step_name, agent_result),
            memory_hit_rate=self._calculate_hit_rate(agent_result)
        )

        self.metrics_by_step[step_name] = metrics
        return metrics

    def _calculate_improvement(self, step_name: str, result: Any) -> float:
        """Calculate improvement vs baseline."""
        if "baseline" in self.metrics_by_step:
            baseline = self.metrics_by_step["baseline"]
            return (
                (baseline.task_completion_time_ms - result.execution_time_ms)
                / baseline.task_completion_time_ms
            ) * 100
        return 0.0

    def _calculate_hit_rate(self, result: Any) -> float:
        """Calculate memory hit rate."""
        if result.memories_retrieved > 0:
            return (result.memories_used / result.memories_retrieved) * 100
        return 0.0

    def generate_report(self) -> Dict[str, Any]:
        """Generate learning metrics report for gadugi."""
        return {
            "session_id": self.session_id,
            "total_steps": len(self.metrics_by_step),
            "metrics_by_step": {
                step: {
                    "completion_time_ms": m.task_completion_time_ms,
                    "quality_score": m.solution_quality_score,
                    "memory_hit_rate": m.memory_hit_rate,
                    "learning_score": m.calculate_learning_score()
                }
                for step, m in self.metrics_by_step.items()
            },
            "overall_learning_score": sum(
                m.calculate_learning_score() for m in self.metrics_by_step.values()
            ) / len(self.metrics_by_step)
        }
```

### Test Automation Pipeline

**File**: `.github/workflows/memory_agent_tests.yml`

```yaml
name: Memory Agent Learning Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    paths:
      - "src/amplihack/memory/**"
      - "tests/memory/**"
      - "tests/agents/**"

jobs:
  unit-tests:
    name: Unit Tests (60%)
    runs-on: ubuntu-latest
    timeout-minutes: 5

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install Dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov pytest-benchmark

      - name: Run Unit Tests
        run: |
          pytest tests/memory/unit/ -v --cov=amplihack.memory --cov-report=xml

      - name: Check Coverage
        run: |
          coverage report --fail-under=90

  integration-tests:
    name: Integration Tests (30%)
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install Dependencies
        run: |
          pip install -e .
          pip install pytest

      - name: Run Integration Tests
        run: |
          pytest tests/memory/integration/ -v -m integration

      - name: Run Performance Benchmarks
        run: |
          pytest tests/memory/integration/test_performance.py -v -m performance

  e2e-tests:
    name: E2E Agent Learning Tests (10%)
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install Dependencies
        run: |
          pip install -e .
          pip install pytest

      - name: Run E2E Tests
        run: |
          pytest tests/memory/e2e/ tests/agents/ -v -m e2e

      - name: Collect Learning Metrics
        run: |
          python tests/gadugi_scenarios/collect_metrics.py

      - name: Upload Metrics
        uses: actions/upload-artifact@v3
        with:
          name: learning-metrics
          path: test_results/learning_metrics.json

  gadugi-integration:
    name: Gadugi Agentic Test Integration
    runs-on: ubuntu-latest
    timeout-minutes: 20

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install Dependencies
        run: |
          pip install -e .
          pip install pytest

      - name: Run Gadugi Scenarios
        run: |
          pytest tests/gadugi_scenarios/ -v --gadugi-report=gadugi_results.json

      - name: Validate Learning Improvements
        run: |
          python tests/gadugi_scenarios/validate_learning.py --results gadugi_results.json

      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: gadugi-results
          path: gadugi_results.json
```

---

## Test Execution Guide

### Running All Tests

```bash
# Complete test suite
pytest tests/memory/ tests/agents/ -v

# With coverage report
pytest tests/memory/ tests/agents/ --cov=amplihack.memory --cov-report=html

# Fast tests only (unit)
pytest tests/memory/unit/ -v

# Integration tests
pytest tests/memory/integration/ -v -m integration

# E2E tests
pytest tests/memory/e2e/ tests/agents/ -v -m e2e

# Performance benchmarks
pytest tests/memory/integration/test_performance.py -v -m performance

# Learning validation tests
pytest tests/agents/ -v -m agent_learning

# Gadugi scenarios
pytest tests/gadugi_scenarios/ -v
```

### CI/CD Integration

All tests run automatically on:

- Pull requests to main/develop
- Pushes to main/develop
- Manual workflow dispatch

**Fail Conditions**:

- Unit test coverage <90%
- Any test failure
- Performance benchmarks exceed thresholds
- Learning metrics don't show improvement

---

## Success Criteria Summary

### Coverage Targets (MUST MEET)

- ✅ Overall coverage >80%
- ✅ Core logic (coordinator, pipelines) >90%
- ✅ All 4 agents have learning tests
- ✅ All critical paths have E2E tests

### Performance Targets (MUST MEET)

- ✅ Retrieval without review: <50ms (NFR1)
- ✅ Storage with review: <500ms
- ✅ Agent learning validation: <30s per test

### Learning Targets (MUST DEMONSTRATE)

- ✅ Document Analyzer: >15% speed improvement
- ✅ Pattern Recognizer: >20% speed improvement, >85% accuracy
- ✅ Bug Predictor: >10% accuracy improvement with feedback
- ✅ Performance Optimizer: >70% confidence on strategy reuse

### Test Quality (MUST MAINTAIN)

- ✅ No flaky tests (3 consecutive clean runs required)
- ✅ All tests isolated (no cross-test dependencies)
- ✅ Clear failure messages
- ✅ Repeatable results

---

## Appendix A: Helper Functions

```python
"""Test helper functions."""

from pathlib import Path


def create_sample_codebase(path: Path) -> Path:
    """Create sample codebase for testing."""
    path.mkdir(parents=True, exist_ok=True)

    # Create files with patterns
    (path / "singleton.py").write_text("""
class DatabaseConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
""")

    (path / "factory.py").write_text("""
class ShapeFactory:
    def create_shape(self, shape_type):
        if shape_type == "circle":
            return Circle()
        elif shape_type == "square":
            return Square()
""")

    return path


def load_sample_doc(filename: str) -> str:
    """Load sample documentation for testing."""
    docs_path = Path(__file__).parent / "fixtures" / "documents"
    return (docs_path / filename).read_text()
```

---

## Appendix B: Pytest Configuration

**File**: `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (requires database)
    e2e: End-to-end tests (full system)
    performance: Performance benchmark tests
    agent_learning: Agent learning validation tests
    slow: Tests that take >5 seconds

addopts =
    -v
    --strict-markers
    --tb=short
    --disable-warnings
    --maxfail=5

# Coverage settings
[coverage:run]
source = amplihack.memory
omit =
    */tests/*
    */test_*.py

[coverage:report]
precision = 2
show_missing = True
skip_covered = False
```

---

## Document Control

**Version**: 1.0
**Date**: 2026-02-14
**Author**: Tester Agent (amplihack)
**Status**: Final

**Change Log**:

- 2026-02-14: Initial comprehensive testing strategy
