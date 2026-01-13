"""Reliability evaluator fer memory backends.

Measures robustness and data integrity:
- Data integrity: Can retrieve what was stored?
- Concurrent safety: Multi-thread safe operations?
- Error recovery: Handles failures gracefully?

Philosophy:
- Real stress tests: Actual failure scenarios
- Comprehensive: Multiple reliability dimensions
- Fair comparison: Same test conditions

Public API:
    ReliabilityEvaluator: Main evaluator class
    ReliabilityMetrics: Results dataclass
"""

import asyncio
import logging
from dataclasses import dataclass

from ..coordinator import MemoryCoordinator, RetrievalQuery, StorageRequest
from ..types import MemoryType

logger = logging.getLogger(__name__)


@dataclass
class ReliabilityMetrics:
    """Reliability evaluation results.

    Args:
        data_integrity_score: % of stored memories retrievable (0-1)
        concurrent_safety_score: % of concurrent operations successful (0-1)
        error_recovery_score: % of errors handled gracefully (0-1)
        num_tests: Number of reliability tests run
        backend_name: Name of evaluated backend
    """

    data_integrity_score: float
    concurrent_safety_score: float
    error_recovery_score: float
    num_tests: int
    backend_name: str


class ReliabilityEvaluator:
    """Evaluates memory backend reliability.

    Measures:
    - Data integrity: Can retrieve what was stored?
    - Concurrent safety: Multi-thread safe?
    - Error recovery: Handles failures gracefully?
    """

    def __init__(self, coordinator: MemoryCoordinator):
        """Initialize evaluator.

        Args:
            coordinator: Memory coordinator to evaluate
        """
        self.coordinator = coordinator
        self.backend = coordinator.backend

    async def evaluate(self) -> ReliabilityMetrics:
        """Evaluate reliability with stress tests.

        Returns:
            Reliability metrics
        """
        # Test data integrity
        integrity_score = await self._test_data_integrity()

        # Test concurrent safety
        concurrency_score = await self._test_concurrent_safety()

        # Test error recovery
        recovery_score = await self._test_error_recovery()

        return ReliabilityMetrics(
            data_integrity_score=integrity_score,
            concurrent_safety_score=concurrency_score,
            error_recovery_score=recovery_score,
            num_tests=3,  # Three test categories
            backend_name=self.backend.get_capabilities().backend_name,
        )

    async def _test_data_integrity(self) -> float:
        """Test that stored data can be retrieved accurately.

        Returns:
            Data integrity score (0-1)
        """
        test_data = [
            ("Simple text", MemoryType.EPISODIC),
            ("Text with special chars: !@#$%^&*()", MemoryType.SEMANTIC),
            ("Multi-line\ntext\nwith\nnewlines", MemoryType.PROCEDURAL),
            ("Unicode: 你好 мир 🎉", MemoryType.PROSPECTIVE),
            ("Very long text " * 100, MemoryType.WORKING),
        ]

        successful_roundtrips = 0
        total_tests = len(test_data)

        for content, memory_type in test_data:
            try:
                # Store memory
                request = StorageRequest(
                    content=content,
                    memory_type=memory_type,
                    context={"agent_id": "integrity-test"},
                    metadata={"test_memory": True},
                )
                memory_id = await self.coordinator.store(request)

                if not memory_id:
                    continue

                # Retrieve memory
                memory = self.backend.get_memory_by_id(memory_id)

                # Verify content matches
                if memory and memory.content == content:
                    successful_roundtrips += 1
                else:
                    logger.warning(
                        f"Data integrity failure: Expected '{content[:50]}...', "
                        f"got '{memory.content[:50] if memory else None}...'"
                    )

            except Exception as e:
                logger.error(f"Data integrity test failed: {e}")
                continue

        return successful_roundtrips / total_tests if total_tests > 0 else 0.0

    async def _test_concurrent_safety(self) -> float:
        """Test concurrent operations (multi-threading safety).

        Returns:
            Concurrent safety score (0-1)
        """
        num_concurrent_ops = 10
        successful_ops = 0

        # Create tasks fer concurrent storage
        async def store_memory(index: int) -> bool:
            try:
                request = StorageRequest(
                    content=f"Concurrent test memory {index}",
                    memory_type=MemoryType.EPISODIC,
                    context={"agent_id": "concurrency-test"},
                    metadata={"test_memory": True, "index": index},
                )
                memory_id = await self.coordinator.store(request)
                return memory_id is not None
            except Exception as e:
                logger.error(f"Concurrent storage failed: {e}")
                return False

        # Run concurrent operations
        tasks = [store_memory(i) for i in range(num_concurrent_ops)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful operations
        for result in results:
            if isinstance(result, bool) and result:
                successful_ops += 1

        return successful_ops / num_concurrent_ops if num_concurrent_ops > 0 else 0.0

    async def _test_error_recovery(self) -> float:
        """Test error handling and recovery.

        Returns:
            Error recovery score (0-1)
        """
        graceful_failures = 0
        total_scenarios = 3

        # Test 1: Invalid memory ID
        try:
            result = self.backend.get_memory_by_id("nonexistent-id")
            if result is None:
                graceful_failures += 1
        except Exception as e:
            if isinstance(e, (ValueError, KeyError, TypeError)):
                graceful_failures += 1

        # Test 2: Empty query
        try:
            result = await self.coordinator.retrieve(RetrievalQuery(query_text=""))
            if result == []:
                graceful_failures += 1
        except Exception as e:
            if isinstance(e, (ValueError, KeyError, TypeError)):
                graceful_failures += 1

        # Test 3: Invalid memory type filter
        try:
            result = await self.coordinator.retrieve(
                RetrievalQuery(query_text="test", memory_types=[])
            )
            if result == []:
                graceful_failures += 1
        except Exception as e:
            if isinstance(e, (ValueError, KeyError, TypeError)):
                graceful_failures += 1

        return graceful_failures / total_scenarios if total_scenarios > 0 else 0.0


__all__ = ["ReliabilityEvaluator", "ReliabilityMetrics"]
