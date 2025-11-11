"""
SelfHealingManager: Detects and recovers from execution failures.

Implements retry, skip, simplify, and escalate strategies with learning.
"""

import uuid
from collections import defaultdict
from typing import Dict, List, Optional

from ..models import (
    ExecutionEvent,
    ExecutionTrace,
    PlanPhase,
    RecoveryStrategy,
)


class SelfHealingManager:
    """
    Manages self-healing and recovery during execution failures.

    Learns from past recoveries to improve future responses.
    """

    def __init__(self, max_retries: int = 3):
        """
        Initialize self-healing manager.

        Args:
            max_retries: Maximum retry attempts per phase
        """
        self.max_retries = max_retries
        self.recovery_history: Dict[str, List[RecoveryStrategy]] = defaultdict(list)
        self.success_rates: Dict[str, Dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )

    def detect_failure(
        self,
        trace: ExecutionTrace,
        phase: PlanPhase,
        error: Exception,
    ) -> Optional[str]:
        """
        Detect and classify failure.

        Args:
            trace: Current execution trace
            phase: Phase that failed
            error: Exception that occurred

        Returns:
            Failure classification or None if not a recoverable failure

        Example:
            >>> failure_type = manager.detect_failure(trace, phase, error)
            >>> if failure_type:
            ...     strategy = manager.generate_recovery_strategy(...)
        """
        error_msg = str(error)

        # Classify error type
        if "timeout" in error_msg.lower():
            return "timeout"
        elif "permission" in error_msg.lower() or "access" in error_msg.lower():
            return "permission_denied"
        elif "not found" in error_msg.lower():
            return "resource_not_found"
        elif "connection" in error_msg.lower() or "network" in error_msg.lower():
            return "network_error"
        elif "memory" in error_msg.lower() or "oom" in error_msg.lower():
            return "resource_exhaustion"
        elif "syntax" in error_msg.lower() or "parse" in error_msg.lower():
            return "syntax_error"
        else:
            return "unknown_error"

    def generate_recovery_strategy(
        self,
        trace: ExecutionTrace,
        phase: PlanPhase,
        failure_type: str,
        retry_count: int = 0,
    ) -> RecoveryStrategy:
        """
        Generate recovery strategy for a failure.

        Args:
            trace: Current execution trace
            phase: Phase that failed
            failure_type: Type of failure detected
            retry_count: Number of retries already attempted

        Returns:
            RecoveryStrategy to attempt

        Example:
            >>> strategy = manager.generate_recovery_strategy(trace, phase, "timeout")
            >>> print(f"Strategy: {strategy.strategy_type}")
        """
        # Check retry history
        if retry_count >= self.max_retries:
            return self._escalate_strategy(phase, failure_type, "Max retries exceeded")

        # Check learned success rates
        best_strategy = self._get_best_learned_strategy(phase.name, failure_type)
        if best_strategy:
            return best_strategy

        # Default strategies based on failure type
        if failure_type == "timeout":
            return self._retry_strategy(phase, failure_type, "Timeout may be transient")

        elif failure_type == "network_error":
            return self._retry_strategy(
                phase, failure_type, "Network issues often resolve"
            )

        elif failure_type == "resource_not_found":
            return self._simplify_strategy(
                phase, failure_type, "Resource may need to be created first"
            )

        elif failure_type == "permission_denied":
            return self._escalate_strategy(
                phase, failure_type, "Permission issues require manual intervention"
            )

        elif failure_type == "resource_exhaustion":
            return self._simplify_strategy(
                phase, failure_type, "Reduce resource requirements"
            )

        elif failure_type == "syntax_error":
            if retry_count == 0:
                return self._retry_strategy(
                    phase, failure_type, "Retry with corrected syntax"
                )
            else:
                return self._skip_strategy(phase, failure_type, "Syntax cannot be fixed")

        else:
            return self._retry_strategy(
                phase, failure_type, "Unknown error - try once more"
            )

    def _retry_strategy(
        self, phase: PlanPhase, failure_type: str, reason: str
    ) -> RecoveryStrategy:
        """Generate retry strategy."""
        return RecoveryStrategy(
            strategy_type="retry",
            phase_name=phase.name,
            reason=reason,
            actions=[
                f"Wait 5 seconds",
                f"Retry phase '{phase.name}'",
                f"Log retry attempt",
            ],
            confidence=0.7,
            estimated_cost=float(phase.estimated_duration.split()[0]) * 1.2,
        )

    def _skip_strategy(
        self, phase: PlanPhase, failure_type: str, reason: str
    ) -> RecoveryStrategy:
        """Generate skip strategy."""
        return RecoveryStrategy(
            strategy_type="skip",
            phase_name=phase.name,
            reason=reason,
            actions=[
                f"Mark phase '{phase.name}' as skipped",
                f"Continue to next phase",
                f"Log skip decision",
            ],
            confidence=0.5,
            estimated_cost=0.0,
        )

    def _simplify_strategy(
        self, phase: PlanPhase, failure_type: str, reason: str
    ) -> RecoveryStrategy:
        """Generate simplify strategy."""
        return RecoveryStrategy(
            strategy_type="simplify",
            phase_name=phase.name,
            reason=reason,
            actions=[
                f"Reduce scope of '{phase.name}'",
                f"Use simpler approach",
                f"Retry with reduced complexity",
            ],
            confidence=0.6,
            estimated_cost=float(phase.estimated_duration.split()[0]) * 0.8,
        )

    def _escalate_strategy(
        self, phase: PlanPhase, failure_type: str, reason: str
    ) -> RecoveryStrategy:
        """Generate escalate strategy."""
        return RecoveryStrategy(
            strategy_type="escalate",
            phase_name=phase.name,
            reason=reason,
            actions=[
                f"Pause execution",
                f"Request human intervention for '{phase.name}'",
                f"Provide error details and context",
            ],
            confidence=1.0,  # Human intervention is most reliable
            estimated_cost=300.0,  # 5 minutes for human to respond
        )

    def execute_recovery(
        self,
        strategy: RecoveryStrategy,
        trace: ExecutionTrace,
    ) -> bool:
        """
        Execute recovery strategy.

        Args:
            strategy: Recovery strategy to execute
            trace: Current execution trace

        Returns:
            True if recovery succeeded, False otherwise

        Example:
            >>> success = manager.execute_recovery(strategy, trace)
            >>> if success:
            ...     print("Recovery successful")
        """
        # Record recovery attempt
        self.recovery_history[strategy.phase_name].append(strategy)

        # Record event in trace
        trace.events.append(
            ExecutionEvent(
                timestamp=trace.start_time,
                event_type="recovery_attempt",
                phase_name=strategy.phase_name,
                data={
                    "strategy": strategy.strategy_type,
                    "reason": strategy.reason,
                    "confidence": strategy.confidence,
                },
            )
        )

        # In real implementation, would actually execute the recovery
        # For now, simulate based on confidence
        import random

        success = random.random() < strategy.confidence

        # Learn from outcome
        self._learn_from_recovery(strategy, success)

        return success

    def _learn_from_recovery(
        self, strategy: RecoveryStrategy, success: bool
    ) -> None:
        """
        Learn from recovery attempt outcome.

        Updates success rates for strategy types.
        """
        phase_name = strategy.phase_name
        strategy_type = strategy.strategy_type

        # Get current success rate
        current_rate = self.success_rates[phase_name][strategy_type]

        # Update with exponential moving average
        alpha = 0.3  # Learning rate
        new_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * current_rate

        self.success_rates[phase_name][strategy_type] = new_rate

    def _get_best_learned_strategy(
        self, phase_name: str, failure_type: str
    ) -> Optional[RecoveryStrategy]:
        """
        Get best strategy based on learned success rates.

        Returns None if no learned strategy available.
        """
        if phase_name not in self.success_rates:
            return None

        strategy_rates = self.success_rates[phase_name]
        if not strategy_rates:
            return None

        # Find strategy with highest success rate
        best_type = max(strategy_rates.items(), key=lambda x: x[1])

        if best_type[1] < 0.3:  # Don't use if success rate too low
            return None

        # Generate strategy of best type
        # (Simplified - in reality would use phase info)
        return RecoveryStrategy(
            strategy_type=best_type[0],  # type: ignore
            phase_name=phase_name,
            reason=f"Learned strategy (success rate: {best_type[1]:.1%})",
            actions=[f"Execute learned {best_type[0]} strategy"],
            confidence=best_type[1],
            estimated_cost=60.0,
        )

    def get_recovery_statistics(self) -> Dict[str, any]:
        """
        Get statistics about recovery attempts.

        Returns:
            Dictionary with recovery stats

        Example:
            >>> stats = manager.get_recovery_statistics()
            >>> print(f"Total recoveries: {stats['total_attempts']}")
        """
        total_attempts = sum(len(attempts) for attempts in self.recovery_history.values())

        strategy_counts = defaultdict(int)
        for attempts in self.recovery_history.values():
            for strategy in attempts:
                strategy_counts[strategy.strategy_type] += 1

        avg_success_rates = {}
        for phase_name, rates in self.success_rates.items():
            if rates:
                avg_success_rates[phase_name] = sum(rates.values()) / len(rates)

        return {
            "total_attempts": total_attempts,
            "phases_with_failures": len(self.recovery_history),
            "strategy_counts": dict(strategy_counts),
            "average_success_rates": avg_success_rates,
            "most_successful_strategy": (
                max(strategy_counts.items(), key=lambda x: x[1])[0]
                if strategy_counts
                else None
            ),
        }

    def should_abort_execution(
        self, trace: ExecutionTrace, consecutive_failures: int
    ) -> bool:
        """
        Decide if execution should be aborted.

        Args:
            trace: Current execution trace
            consecutive_failures: Number of consecutive failures

        Returns:
            True if execution should be aborted

        Example:
            >>> if manager.should_abort_execution(trace, failure_count):
            ...     print("Aborting execution")
        """
        # Abort after too many consecutive failures
        if consecutive_failures >= 5:
            return True

        # Abort if too many total errors
        error_count = len([e for e in trace.events if e.event_type == "error"])
        if error_count >= 10:
            return True

        # Check if we're making progress
        phase_events = [e for e in trace.events if e.event_type == "phase_end"]
        if not phase_events and len(trace.events) > 20:
            return True  # No phases completed and lots of activity

        return False

    def create_recovery_report(
        self, trace: ExecutionTrace
    ) -> Dict[str, any]:
        """
        Create report of recovery actions taken.

        Args:
            trace: Execution trace

        Returns:
            Recovery report dictionary

        Example:
            >>> report = manager.create_recovery_report(trace)
            >>> print(f"Recoveries: {report['recovery_count']}")
        """
        recovery_events = [
            e for e in trace.events if e.event_type == "recovery_attempt"
        ]

        strategies_used = [e.data.get("strategy") for e in recovery_events]
        strategy_counts = dict(
            (s, strategies_used.count(s)) for s in set(strategies_used)
        )

        return {
            "execution_id": str(trace.execution_id),
            "recovery_count": len(recovery_events),
            "strategies_used": strategy_counts,
            "phases_with_recovery": len(
                set(e.phase_name for e in recovery_events if e.phase_name)
            ),
            "execution_recovered": trace.status == "recovered",
            "final_status": trace.status,
        }
