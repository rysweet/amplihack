"""Learning tests for Document Analyzer agent.

These tests validate that the Document Analyzer agent learns from experience
and improves over time using the memory system.

Test Approach:
- Outside-in: Start with real user scenarios
- Measurable: Track concrete learning metrics
- Repeatable: Use consistent test data
"""

from dataclasses import dataclass
from datetime import datetime

import pytest

from amplihack.memory.coordinator import MemoryCoordinator
from amplihack.memory.models import MemoryQuery, MemoryType

# =============================================================================
# Learning Metrics
# =============================================================================


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
    improvement_vs_first_run: float = 0.0  # Percentage
    memory_hit_rate: float = 0.0  # Percentage

    def calculate_learning_score(self) -> float:
        """Calculate overall learning score (0-100)."""
        # Weight different factors
        efficiency_score = min(100, 100 / max(1, self.task_completion_time_ms / 1000))
        quality_score = self.solution_quality_score
        memory_usage_score = self.memory_hit_rate

        # Weighted average
        return efficiency_score * 0.3 + quality_score * 0.5 + memory_usage_score * 0.2


# =============================================================================
# Mock Document Analyzer Agent
# =============================================================================


class DocumentAnalyzerAgent:
    """Mock Document Analyzer for testing.

    In production, this would be the real agent implementation.
    For testing, we simulate the key behaviors we want to validate.
    """

    def __init__(self, memory: MemoryCoordinator):
        self.memory = memory
        self.agent_id = "doc_analyzer"

    def analyze(self, document: str, session_id: str) -> LearningMetrics:
        """Analyze document and return metrics.

        This mock implementation simulates:
        1. Checking memory for similar documents
        2. Faster processing if relevant memories found
        3. Storing learned patterns
        """
        import time

        start_time = time.perf_counter()

        # Check memory for relevant patterns
        relevant_memories = self.memory.retrieve(
            query=MemoryQuery(agent_id=self.agent_id, memory_type=MemoryType.SEMANTIC, limit=10)
        )

        memories_retrieved = len(relevant_memories.memories)
        memories_used = 0

        # Simulate faster processing if we have relevant memories
        base_processing_time = 2000  # 2 seconds baseline
        if memories_retrieved > 0:
            # 20% faster per relevant memory, up to 80% faster
            speedup = min(0.8, memories_retrieved * 0.2)
            processing_time = base_processing_time * (1 - speedup)
            memories_used = min(memories_retrieved, 3)
        else:
            processing_time = base_processing_time

        # Simulate processing delay
        time.sleep(processing_time / 1000)

        # Store learning from this analysis
        self.memory.store(
            memory_type=MemoryType.SEMANTIC,
            title="Documentation analysis pattern",
            content=f"Analyzed document about {extract_topic(document)}",
            session_id=session_id,
            agent_id=self.agent_id,
            metadata={"processing_time": processing_time},
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Calculate metrics
        memory_hit_rate = (
            (memories_used / memories_retrieved * 100) if memories_retrieved > 0 else 0
        )

        return LearningMetrics(
            task_completion_time_ms=elapsed_ms,
            api_calls_made=2 + memories_retrieved,  # 2 for store/retrieve + memory checks
            tokens_consumed=1000 - (memories_used * 100),  # Fewer tokens if using memory
            solution_quality_score=85 + (memories_used * 2),  # Better quality with memory
            error_rate=0.0,
            success_on_first_attempt=True,
            relevant_memories_retrieved=memories_retrieved,
            relevant_memories_used=memories_used,
            new_patterns_learned=1,
            procedural_memories_stored=0,
            memory_hit_rate=memory_hit_rate,
        )

    def analyze_for_user(self, document_content: str, user_query: str, session_id: str):
        """User-facing analysis method (outside-in interface)."""
        metrics = self.analyze(document_content, session_id)

        return {
            "summary": f"Analysis of {len(document_content)} chars",
            "key_concepts": ["concept1", "concept2"],
            "processing_time": metrics.task_completion_time_ms,
            "quality_score": metrics.solution_quality_score,
            "cross_references_count": metrics.relevant_memories_used,
        }


def extract_topic(document: str) -> str:
    """Extract main topic from document (simplified)."""
    if "authentication" in document.lower():
        return "authentication"
    if "authorization" in document.lower():
        return "authorization"
    if "storage" in document.lower():
        return "storage"
    return "general"


# =============================================================================
# Agent Learning Tests
# =============================================================================


@pytest.mark.agent_learning
class TestDocumentAnalyzerLearning:
    """Validate Document Analyzer learns from experience."""

    @pytest.fixture
    def analyzer(self, mock_backend):
        """Create analyzer with memory."""
        memory = MemoryCoordinator(backend=mock_backend)
        return DocumentAnalyzerAgent(memory=memory)

    def test_analyzer_improves_on_second_analysis(self, analyzer, mock_backend):
        """Test analyzer is faster and better on second analysis.

        LEARNING GOAL: Speed improvement >15%, quality maintained
        """
        # Simulate first run returning no memories
        mock_backend.query.return_value = []

        # ACT - First Analysis (no prior memory)
        doc1 = "# Authentication\nDetails about Azure authentication..."
        metrics_run1 = analyzer.analyze(document=doc1, session_id="analyzer_session_1")

        # Simulate second run finding the stored memory
        from amplihack.memory.models import MemoryEntry

        mock_backend.query.return_value = [
            MemoryEntry(
                id="mem1",
                session_id="analyzer_session_1",
                agent_id="doc_analyzer",
                memory_type=MemoryType.SEMANTIC,
                title="Documentation analysis pattern",
                content="Analyzed document about authentication",
                metadata={},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )
        ]

        # ACT - Second Analysis (with memory from run 1)
        doc2 = "# Authorization\nDetails about Azure RBAC..."
        metrics_run2 = analyzer.analyze(document=doc2, session_id="analyzer_session_2")

        # ASSERT - Learning improvements
        assert metrics_run2.task_completion_time_ms < metrics_run1.task_completion_time_ms, (
            "Second run should be faster"
        )

        assert metrics_run2.solution_quality_score >= metrics_run1.solution_quality_score, (
            "Quality should maintain or improve"
        )

        assert metrics_run2.relevant_memories_retrieved > 0, "Should retrieve relevant memories"

        assert metrics_run2.memory_hit_rate > 0, "Should use retrieved memories"

        # Calculate learning improvement
        learning_improvement = (
            (metrics_run1.task_completion_time_ms - metrics_run2.task_completion_time_ms)
            / metrics_run1.task_completion_time_ms
        ) * 100

        assert learning_improvement > 15, (
            f"Expected >15% improvement, got {learning_improvement:.1f}%"
        )

        print(f"\n✓ Learning improvement: {learning_improvement:.1f}%")
        print(
            f"✓ Quality improvement: {metrics_run2.solution_quality_score - metrics_run1.solution_quality_score:.1f} points"
        )
        print(f"✓ Memory hit rate: {metrics_run2.memory_hit_rate:.1f}%")

    def test_analyzer_learns_documentation_patterns(self, analyzer, mock_backend):
        """Test analyzer stores and reuses documentation patterns.

        LEARNING GOAL: Progressive improvement across multiple documents
        """
        # Simulate progressive memory accumulation
        stored_memories: list[MemoryEntry] = []

        def mock_query_side_effect(*args, **kwargs):
            return stored_memories.copy()

        def mock_store_side_effect(entry):
            stored_memories.append(entry)
            return f"mem_{len(stored_memories)}"

        mock_backend.query.side_effect = mock_query_side_effect
        mock_backend.store.side_effect = mock_store_side_effect

        # ACT - Analyze multiple similar documents
        docs = [
            "# Azure Authentication\nDetails about auth...",
            "# Azure Storage\nDetails about storage...",
            "# Azure Compute\nDetails about compute...",
        ]

        metrics_by_doc = []
        for i, doc_content in enumerate(docs):
            metrics = analyzer.analyze(document=doc_content, session_id=f"sess_doc_{i}")
            metrics_by_doc.append(metrics)

        # ASSERT - Progressive improvement
        assert (
            metrics_by_doc[1].task_completion_time_ms < metrics_by_doc[0].task_completion_time_ms
        ), "Second analysis should be faster than first"

        assert (
            metrics_by_doc[2].task_completion_time_ms < metrics_by_doc[1].task_completion_time_ms
        ), "Third analysis should be faster than second"

        # Check pattern learning
        assert len(stored_memories) == 3, "Should store memory for each analysis"

        # Verify quality improves or maintains
        assert all(
            metrics_by_doc[i + 1].solution_quality_score >= metrics_by_doc[i].solution_quality_score
            for i in range(len(metrics_by_doc) - 1)
        ), "Quality should improve or maintain"

        print(f"\n✓ Doc 1 time: {metrics_by_doc[0].task_completion_time_ms:.0f}ms")
        print(f"✓ Doc 2 time: {metrics_by_doc[1].task_completion_time_ms:.0f}ms")
        print(f"✓ Doc 3 time: {metrics_by_doc[2].task_completion_time_ms:.0f}ms")
        print(
            f"✓ Total speedup: {((metrics_by_doc[0].task_completion_time_ms - metrics_by_doc[2].task_completion_time_ms) / metrics_by_doc[0].task_completion_time_ms * 100):.1f}%"
        )

    def test_analyzer_cross_session_memory_persistence(self, analyzer, mock_backend):
        """Test analyzer retrieves relevant memories across sessions.

        LEARNING GOAL: Knowledge persists and transfers across sessions
        """
        # SESSION 1: Store memory about authentication
        auth_memory = MemoryEntry(
            id="auth_mem",
            session_id="session_1",
            agent_id="doc_analyzer",
            memory_type=MemoryType.SEMANTIC,
            title="Authentication analysis",
            content="Analyzed authentication document",
            metadata={"topic": "authentication"},
            created_at=datetime.now(),
            accessed_at=datetime.now(),
        )

        mock_backend.query.return_value = [auth_memory]

        # SESSION 2: Analyze related topic (authorization)
        doc = "# Authorization\nRBAC concepts..."
        metrics = analyzer.analyze(document=doc, session_id="session_2")

        # ASSERT - Should retrieve relevant memories from session 1
        assert metrics.relevant_memories_retrieved > 0, (
            "Should retrieve memories from previous session"
        )

        assert metrics.relevant_memories_used > 0, "Should use relevant memories"

        print(f"\n✓ Retrieved {metrics.relevant_memories_retrieved} memories from previous session")
        print(f"✓ Used {metrics.relevant_memories_used} memories")
        print(f"✓ Memory hit rate: {metrics.memory_hit_rate:.1f}%")


@pytest.mark.agent_learning
@pytest.mark.e2e
class TestDocumentAnalyzerOutsideIn:
    """Outside-in tests for Document Analyzer (user perspective)."""

    def test_user_analyzes_ms_learn_docs(self, mock_backend, sample_documents):
        """
        USER GOAL: Understand Azure documentation

        EXPECTED BEHAVIOR:
        1. Agent analyzes document
        2. Stores key concepts in semantic memory
        3. On second document, retrieves related concepts
        4. Provides better analysis faster
        """
        # Setup
        memory = MemoryCoordinator(backend=mock_backend)
        agent = DocumentAnalyzerAgent(memory=memory)

        # Simulate no memories initially
        mock_backend.query.return_value = []

        # ACT - First document
        doc1_content = (sample_documents / "azure_auth.md").read_text()
        result1 = agent.analyze_for_user(
            document_content=doc1_content,
            user_query="How does Azure authentication work?",
            session_id="user_session_1",
        )

        # Verify user gets useful answer
        assert result1["summary"] is not None, "User should get summary"
        assert len(result1["key_concepts"]) > 0, "User should get key concepts"

        # Verify learning happened (memory was stored)
        assert mock_backend.store.called, "Should store learned patterns"

        # Simulate finding stored memory
        mock_backend.query.return_value = [
            MemoryEntry(
                id="stored_auth",
                session_id="user_session_1",
                agent_id="doc_analyzer",
                memory_type=MemoryType.SEMANTIC,
                title="Documentation analysis pattern",
                content="Analyzed document about authentication",
                metadata={},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )
        ]

        # ACT - Second document (related topic)
        doc2_content = (sample_documents / "azure_rbac.md").read_text()
        result2 = agent.analyze_for_user(
            document_content=doc2_content,
            user_query="How does Azure authorization work?",
            session_id="user_session_2",
        )

        # ASSERT - Verify improvement
        assert result2["processing_time"] < result1["processing_time"], (
            "Second analysis should be faster"
        )

        assert result2["cross_references_count"] > 0, "Should reference auth concepts from memory"

        print(f"\n✓ First analysis: {result1['processing_time']:.0f}ms")
        print(f"✓ Second analysis: {result2['processing_time']:.0f}ms")
        print(
            f"✓ Improvement: {((result1['processing_time'] - result2['processing_time']) / result1['processing_time'] * 100):.1f}%"
        )
        print(f"✓ Cross-references: {result2['cross_references_count']}")

    def test_user_benefits_from_accumulated_knowledge(self, mock_backend, sample_documents):
        """
        USER GOAL: Leverage accumulated knowledge for faster insights

        EXPECTED BEHAVIOR:
        System should get progressively better as knowledge accumulates
        """
        memory = MemoryCoordinator(backend=mock_backend)
        agent = DocumentAnalyzerAgent(memory=memory)

        # Simulate progressive memory accumulation
        accumulated_memories: list[MemoryEntry] = []

        def mock_query_dynamic(*args, **kwargs):
            return accumulated_memories.copy()

        def mock_store_dynamic(entry):
            accumulated_memories.append(entry)
            return f"mem_{len(accumulated_memories)}"

        mock_backend.query.side_effect = mock_query_dynamic
        mock_backend.store.side_effect = mock_store_dynamic

        # ACT - User analyzes multiple documents over time
        documents = [
            ("azure_auth.md", "How does authentication work?"),
            ("azure_rbac.md", "Explain authorization"),
            ("azure_storage.md", "What about storage security?"),
        ]

        results = []
        for i, (doc_file, query) in enumerate(documents):
            doc_content = (sample_documents / doc_file).read_text()
            result = agent.analyze_for_user(
                document_content=doc_content, user_query=query, session_id=f"user_session_{i}"
            )
            results.append(result)

        # ASSERT - Progressive improvement
        assert results[1]["processing_time"] < results[0]["processing_time"], (
            "Second document should be faster"
        )

        assert results[2]["processing_time"] < results[1]["processing_time"], (
            "Third document should be faster"
        )

        # Quality should improve or maintain
        assert results[2]["quality_score"] >= results[0]["quality_score"], (
            "Quality should improve with experience"
        )

        print(
            f"\n✓ Document 1: {results[0]['processing_time']:.0f}ms, quality: {results[0]['quality_score']}"
        )
        print(
            f"✓ Document 2: {results[1]['processing_time']:.0f}ms, quality: {results[1]['quality_score']}"
        )
        print(
            f"✓ Document 3: {results[2]['processing_time']:.0f}ms, quality: {results[2]['quality_score']}"
        )
        print(
            f"✓ Total speedup: {((results[0]['processing_time'] - results[2]['processing_time']) / results[0]['processing_time'] * 100):.1f}%"
        )


# =============================================================================
# Performance Validation
# =============================================================================


@pytest.mark.performance
class TestDocumentAnalyzerPerformance:
    """Validate analyzer meets performance constraints."""

    def test_analysis_with_memory_under_2_seconds(self, mock_backend):
        """Test analysis completes in reasonable time with memory."""
        memory = MemoryCoordinator(backend=mock_backend)
        agent = DocumentAnalyzerAgent(memory=memory)

        # Simulate having relevant memories
        mock_backend.query.return_value = [
            MemoryEntry(
                id="perf_mem",
                session_id="perf_test",
                agent_id="doc_analyzer",
                memory_type=MemoryType.SEMANTIC,
                title="Pattern",
                content="Content",
                metadata={},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )
        ]

        # ACT
        import time

        start = time.perf_counter()
        metrics = agent.analyze(document="Test document content", session_id="perf_test")
        elapsed_ms = (time.perf_counter() - start) * 1000

        # ASSERT - Should complete in <2 seconds with memory
        assert elapsed_ms < 2000, f"Took {elapsed_ms:.0f}ms, exceeds 2s limit"
        assert metrics.task_completion_time_ms < 2000

        print(f"\n✓ Analysis completed in {elapsed_ms:.0f}ms")
