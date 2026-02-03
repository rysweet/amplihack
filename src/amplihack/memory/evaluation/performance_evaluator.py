"""Performance evaluator fer memory backends.

Measures speed, throughput, and scalability:
- Storage latency: Time to store memories (ms)
- Retrieval latency: Time to retrieve memories (ms)
- Memory usage: RAM consumption (bytes)
- Disk usage: Storage space (bytes)
- Scalability: Performance vs database size

Philosophy:
- Real benchmarks: Actual timing measurements
- Multiple scales: Test 100, 1000, 10000 memories
- Fair comparison: Same data fer all backends

Public API:
    PerformanceEvaluator: Main evaluator class
    PerformanceMetrics: Results dataclass
"""

import inspect
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from ..coordinator import MemoryCoordinator, RetrievalQuery, StorageRequest
from ..types import MemoryType

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance evaluation results.

    Args:
        storage_latency_ms: Average time to store memory (milliseconds)
        retrieval_latency_ms: Average time to retrieve memories (milliseconds)
        storage_throughput: Memories stored per second
        retrieval_throughput: Queries per second
        memory_usage_bytes: RAM usage (bytes)
        disk_usage_bytes: Disk usage (bytes)
        num_memories: Number of memories in database
        backend_name: Name of evaluated backend
    """

    storage_latency_ms: float
    retrieval_latency_ms: float
    storage_throughput: float
    retrieval_throughput: float
    memory_usage_bytes: int
    disk_usage_bytes: int
    num_memories: int
    backend_name: str


class PerformanceEvaluator:
    """Evaluates memory backend performance.

    Measures:
    - Storage latency: Time to store memories (target: <500ms)
    - Retrieval latency: Time to retrieve memories (target: <50ms)
    - Throughput: Operations per second
    - Scalability: Performance vs database size
    """

    def __init__(self, coordinator: MemoryCoordinator):
        """Initialize evaluator.

        Args:
            coordinator: Memory coordinator to evaluate
        """
        self.coordinator = coordinator
        self.backend = coordinator.backend

    async def evaluate(self, num_operations: int = 100) -> PerformanceMetrics:
        """Evaluate performance with benchmark operations.

        Args:
            num_operations: Number of store/retrieve operations

        Returns:
            Performance metrics
        """
        # Measure storage latency
        storage_times = []
        for i in range(num_operations):
            request = StorageRequest(
                content=f"Performance test memory {i} with some content to store.",
                memory_type=MemoryType.EPISODIC,
                context={"agent_id": "perf-test"},
                metadata={"test_memory": True, "index": i},
            )

            start_time = time.perf_counter()
            await self.coordinator.store(request)
            end_time = time.perf_counter()

            storage_times.append((end_time - start_time) * 1000)  # Convert to ms

        avg_storage_latency = sum(storage_times) / len(storage_times) if storage_times else 0

        # Measure retrieval latency
        retrieval_times = []
        for i in range(num_operations):
            query = RetrievalQuery(query_text=f"memory {i}")

            start_time = time.perf_counter()
            await self.coordinator.retrieve(query)
            end_time = time.perf_counter()

            retrieval_times.append((end_time - start_time) * 1000)  # Convert to ms

        avg_retrieval_latency = (
            sum(retrieval_times) / len(retrieval_times) if retrieval_times else 0
        )

        # Calculate throughput
        storage_throughput = 1000 / avg_storage_latency if avg_storage_latency > 0 else 0
        retrieval_throughput = 1000 / avg_retrieval_latency if avg_retrieval_latency > 0 else 0

        # Get resource usage
        stats_result = self.backend.get_stats()
        # Handle both sync and async backends
        if inspect.iscoroutine(stats_result):
            stats = await stats_result
        else:
            stats = stats_result
        num_memories = stats.get("total_memories", 0)
        disk_usage = self._get_disk_usage()

        return PerformanceMetrics(
            storage_latency_ms=avg_storage_latency,
            retrieval_latency_ms=avg_retrieval_latency,
            storage_throughput=storage_throughput,
            retrieval_throughput=retrieval_throughput,
            memory_usage_bytes=0,  # TODO: Add memory profiling
            disk_usage_bytes=disk_usage,
            num_memories=num_memories,
            backend_name=self.backend.get_capabilities().backend_name,
        )

    async def evaluate_scalability(
        self, scales: list[int] | None = None
    ) -> dict[int, PerformanceMetrics]:
        """Evaluate performance at different scales.

        Args:
            scales: List of database sizes to test (default: [100, 1000, 10000])

        Returns:
            Dict mapping scale to performance metrics
        """
        if scales is None:
            scales = [100, 1000, 10000]

        results = {}

        for scale in scales:
            # Clear database
            await self.coordinator.clear_all(session_id=self.coordinator.session_id)

            # Populate database to target scale
            for i in range(scale):
                request = StorageRequest(
                    content=f"Scale test memory {i} at scale {scale}.",
                    memory_type=MemoryType.EPISODIC,
                    context={"agent_id": "scale-test"},
                    metadata={"test_memory": True, "scale": scale},
                )
                await self.coordinator.store(request)

            # Measure performance at this scale
            metrics = await self.evaluate(num_operations=100)
            results[scale] = metrics

            logger.info(
                f"Scale {scale}: Storage={metrics.storage_latency_ms:.2f}ms, "
                f"Retrieval={metrics.retrieval_latency_ms:.2f}ms"
            )

        return results

    def _get_disk_usage(self) -> int:
        """Get disk usage of backend storage.

        Returns:
            Disk usage in bytes
        """
        try:
            # Try to get database file path from backend
            if hasattr(self.backend, "db_path"):
                db_path = Path(self.backend.db_path)  # type: ignore[attr-defined]
                if db_path.exists():
                    return db_path.stat().st_size

            # Fallback: Try common database locations
            possible_paths = [
                Path("memory.db"),
                Path("memory.sqlite"),
                Path(".amplihack/memory.db"),
            ]

            for path in possible_paths:
                if path.exists():
                    return path.stat().st_size

            return 0

        except Exception as e:
            logger.warning(f"Could not determine disk usage: {e}")
            return 0

    def check_performance_contracts(self, metrics: PerformanceMetrics) -> dict[str, bool]:
        """Check if backend meets performance contracts.

        Performance contracts from backend protocol:
        - Storage: <500ms
        - Retrieval: <50ms

        Args:
            metrics: Performance metrics to check

        Returns:
            Dict of contract name -> passed boolean
        """
        return {
            "storage_latency_ok": metrics.storage_latency_ms < 500,
            "retrieval_latency_ok": metrics.retrieval_latency_ms < 50,
            "storage_throughput_ok": metrics.storage_throughput >= 2,  # At least 2 stores/sec
            "retrieval_throughput_ok": metrics.retrieval_throughput
            >= 20,  # At least 20 queries/sec
        }


__all__ = ["PerformanceEvaluator", "PerformanceMetrics"]
