"""Metrics tracking utilities - Batch 459"""

import time
from typing import Dict, Optional
from collections import defaultdict

class MetricsTracker:
    """Track and aggregate metrics."""

    def __init__(self):
        self.counters: Dict[str, int] = defaultdict(int)
        self.timers: Dict[str, list[float]] = defaultdict(list)
        self.gauges: Dict[str, float] = {{}}

    def increment(self, metric: str, value: int = 1) -> None:
        """Increment a counter metric."""
        self.counters[metric] += value

    def record_time(self, metric: str, duration: float) -> None:
        """Record a timing metric."""
        self.timers[metric].append(duration)

    def set_gauge(self, metric: str, value: float) -> None:
        """Set a gauge metric."""
        self.gauges[metric] = value

    def get_stats(self, metric: str) -> Optional[Dict[str, float]]:
        """Get statistics for a timer metric."""
        if metric not in self.timers or not self.timers[metric]:
            return None

        values = self.timers[metric]
        return {{
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values)
        }}

    def reset(self) -> None:
        """Reset all metrics."""
        self.counters.clear()
        self.timers.clear()
        self.gauges.clear()
