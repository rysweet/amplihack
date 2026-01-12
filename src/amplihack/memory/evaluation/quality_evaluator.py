"""Quality evaluator fer memory retrieval.

Measures how well backends retrieve relevant memories:
- Relevance: How relevant are retrieved memories?
- Precision: What % of retrieved are relevant?
- Recall: What % of relevant were retrieved?
- Ranking: Are most relevant memories ranked first?

Philosophy:
- Ground truth: Test set with known relevant memories
- Comprehensive: Multiple query types and memory types
- Fair: Same test data fer all backends

Public API:
    QualityEvaluator: Main evaluator class
    QualityMetrics: Results dataclass
"""

import logging
from dataclasses import dataclass

from ..coordinator import MemoryCoordinator, RetrievalQuery, StorageRequest
from ..models import MemoryEntry
from ..types import MemoryType

logger = logging.getLogger(__name__)


@dataclass
class QualityMetrics:
    """Quality evaluation results.

    Args:
        relevance_score: Average relevance (0-1)
        precision: % retrieved that are relevant
        recall: % of relevant that were retrieved
        ndcg_score: Ranking quality (0-1, higher is better)
        num_queries: Number of queries evaluated
        backend_name: Name of evaluated backend
    """

    relevance_score: float
    precision: float
    recall: float
    ndcg_score: float
    num_queries: int
    backend_name: str


@dataclass
class QueryTestCase:
    """Test query with ground truth relevant memories.

    Args:
        query_text: Query string
        relevant_memory_ids: IDs of memories that are relevant
        memory_type: Type filter (optional)
    """

    query_text: str
    relevant_memory_ids: list[str]
    memory_type: MemoryType | None = None


class QualityEvaluator:
    """Evaluates memory retrieval quality.

    Measures:
    - Relevance: How relevant are retrieved memories? (0-1)
    - Precision: What % of retrieved are relevant?
    - Recall: What % of relevant were retrieved?
    - NDCG: Normalized Discounted Cumulative Gain (ranking quality)
    """

    def __init__(self, coordinator: MemoryCoordinator):
        """Initialize evaluator.

        Args:
            coordinator: Memory coordinator to evaluate
        """
        self.coordinator = coordinator
        self.backend = coordinator.backend

    async def evaluate(self, test_queries: list[QueryTestCase]) -> QualityMetrics:
        """Evaluate quality using test queries.

        Args:
            test_queries: List of test queries with ground truth

        Returns:
            Quality metrics
        """
        total_relevance = 0.0
        total_precision = 0.0
        total_recall = 0.0
        total_ndcg = 0.0
        num_queries = len(test_queries)

        for test_query in test_queries:
            # Retrieve memories
            query = RetrievalQuery(
                query_text=test_query.query_text,
                memory_types=[test_query.memory_type] if test_query.memory_type else None,
            )
            retrieved_memories = await self.coordinator.retrieve(query)

            # Calculate metrics fer this query
            retrieved_ids = {m.id for m in retrieved_memories}
            relevant_ids = set(test_query.relevant_memory_ids)

            # Precision: % of retrieved that are relevant
            if len(retrieved_ids) > 0:
                precision = len(retrieved_ids & relevant_ids) / len(retrieved_ids)
            else:
                precision = 0.0

            # Recall: % of relevant that were retrieved
            if len(relevant_ids) > 0:
                recall = len(retrieved_ids & relevant_ids) / len(relevant_ids)
            else:
                recall = 0.0

            # Relevance: Average relevance of retrieved memories
            relevance = self._calculate_relevance(retrieved_memories, relevant_ids)

            # NDCG: Ranking quality
            ndcg = self._calculate_ndcg(retrieved_memories, relevant_ids)

            total_relevance += relevance
            total_precision += precision
            total_recall += recall
            total_ndcg += ndcg

        # Average across all queries
        return QualityMetrics(
            relevance_score=total_relevance / num_queries if num_queries > 0 else 0.0,
            precision=total_precision / num_queries if num_queries > 0 else 0.0,
            recall=total_recall / num_queries if num_queries > 0 else 0.0,
            ndcg_score=total_ndcg / num_queries if num_queries > 0 else 0.0,
            num_queries=num_queries,
            backend_name=self.backend.get_capabilities().backend_name,
        )

    def _calculate_relevance(
        self, retrieved_memories: list[MemoryEntry], relevant_ids: set[str]
    ) -> float:
        """Calculate average relevance score.

        Args:
            retrieved_memories: Retrieved memories
            relevant_ids: IDs of relevant memories

        Returns:
            Average relevance (0-1)
        """
        if not retrieved_memories:
            return 0.0

        relevant_count = sum(1 for m in retrieved_memories if m.id in relevant_ids)
        return relevant_count / len(retrieved_memories)

    def _calculate_ndcg(
        self, retrieved_memories: list[MemoryEntry], relevant_ids: set[str]
    ) -> float:
        """Calculate NDCG (Normalized Discounted Cumulative Gain).

        NDCG measures ranking quality - are most relevant memories ranked first?

        Args:
            retrieved_memories: Retrieved memories (in ranked order)
            relevant_ids: IDs of relevant memories

        Returns:
            NDCG score (0-1, higher is better)
        """
        if not retrieved_memories or not relevant_ids:
            return 0.0

        # DCG: Discounted Cumulative Gain
        dcg = 0.0
        for i, memory in enumerate(retrieved_memories):
            if memory.id in relevant_ids:
                # Relevance = 1 fer relevant, 0 fer non-relevant
                relevance = 1.0
                # Discount by position (log2(i+2) because i starts at 0)
                dcg += relevance / (i + 2).bit_length()

        # IDCG: Ideal DCG (if all relevant were ranked first)
        idcg = 0.0
        for i in range(min(len(retrieved_memories), len(relevant_ids))):
            idcg += 1.0 / (i + 2).bit_length()

        # NDCG = DCG / IDCG
        if idcg > 0:
            return dcg / idcg
        return 0.0

    async def create_test_set(self, num_memories: int = 50) -> list[QueryTestCase]:
        """Create a standard test set fer evaluation.

        Creates diverse memories and queries to test retrieval quality.

        Args:
            num_memories: Number of test memories to create

        Returns:
            List of test queries with ground truth
        """
        test_queries = []

        # Store test memories
        memory_ids = []

        # Create episodic memories (conversations)
        for i in range(num_memories // 5):
            request = StorageRequest(
                content=f"User asked about feature {i}, agent explained the implementation details and provided code examples.",
                memory_type=MemoryType.EPISODIC,
                context={"agent_id": "test-agent"},
                metadata={"test_memory": True, "category": "conversation"},
            )
            memory_id = await self.coordinator.store(request)
            if memory_id:
                memory_ids.append(memory_id)

        # Create semantic memories (learnings)
        for i in range(num_memories // 5):
            request = StorageRequest(
                content=f"Pattern learned: When implementing feature {i}, always validate input parameters before processing.",
                memory_type=MemoryType.SEMANTIC,
                context={"agent_id": "test-agent"},
                metadata={"test_memory": True, "category": "learning"},
            )
            memory_id = await self.coordinator.store(request)
            if memory_id:
                memory_ids.append(memory_id)

        # Create procedural memories (workflows)
        for i in range(num_memories // 5):
            request = StorageRequest(
                content=f"Workflow: To deploy feature {i}, run tests, build artifacts, deploy to staging, verify, then deploy to production.",
                memory_type=MemoryType.PROCEDURAL,
                context={"agent_id": "test-agent"},
                metadata={"test_memory": True, "category": "workflow"},
            )
            memory_id = await self.coordinator.store(request)
            if memory_id:
                memory_ids.append(memory_id)

        # Create prospective memories (TODOs)
        for i in range(num_memories // 5):
            request = StorageRequest(
                content=f"TODO: Refactor feature {i} to use new API pattern and improve error handling.",
                memory_type=MemoryType.PROSPECTIVE,
                context={"agent_id": "test-agent"},
                metadata={"test_memory": True, "category": "todo"},
            )
            memory_id = await self.coordinator.store(request)
            if memory_id:
                memory_ids.append(memory_id)

        # Create working memories (task context)
        for i in range(num_memories // 5):
            request = StorageRequest(
                content=f"Current task: Implementing feature {i}, waiting on API response from service X.",
                memory_type=MemoryType.WORKING,
                context={"agent_id": "test-agent"},
                metadata={"test_memory": True, "category": "task"},
            )
            memory_id = await self.coordinator.store(request)
            if memory_id:
                memory_ids.append(memory_id)

        # Create test queries
        # Query 1: Search for specific feature
        test_queries.append(
            QueryTestCase(
                query_text="feature 0",
                relevant_memory_ids=[
                    mid
                    for mid in memory_ids[:5]  # First 5 should contain "feature 0"
                ],
            )
        )

        # Query 2: Search for patterns
        test_queries.append(
            QueryTestCase(
                query_text="pattern learned validation",
                relevant_memory_ids=[mid for mid in memory_ids if "Pattern learned" in str(mid)],
            )
        )

        # Query 3: Search for workflows
        test_queries.append(
            QueryTestCase(
                query_text="deployment workflow",
                relevant_memory_ids=[mid for mid in memory_ids if "Workflow" in str(mid)],
            )
        )

        return test_queries


__all__ = ["QualityEvaluator", "QualityMetrics", "QueryTestCase"]
