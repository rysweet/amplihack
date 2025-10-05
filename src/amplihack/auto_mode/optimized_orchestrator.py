"""
Optimized Auto-Mode Orchestrator

High-performance orchestrator with async optimization, connection pooling,
and intelligent scheduling while preserving all auto-mode requirements.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
from collections import defaultdict, deque

from .optimized_session import OptimizedSessionManager, OptimizedSessionState
from .optimized_analysis import OptimizedAnalysisEngine, ConversationAnalysis
from .quality_gates import QualityGateEvaluator, QualityGateResult
from .optimized_sdk_integration import OptimizedClaudeAgentSDKClient


class OrchestratorState(Enum):
    """States of the auto-mode orchestrator (preserved)"""
    INACTIVE = "inactive"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    ANALYZING = "analyzing"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class OptimizedOrchestratorConfig:
    """Optimized configuration with performance tuning"""
    # Analysis cycle timing (optimized defaults)
    analysis_interval_seconds: float = 20.0  # Reduced from 30.0
    max_analysis_cycles: int = 200  # Increased from 100
    adaptive_interval_enabled: bool = True  # New: adaptive timing

    # Quality thresholds (preserved)
    min_quality_threshold: float = 0.6
    intervention_confidence_threshold: float = 0.7

    # Session management (optimized)
    session_timeout_minutes: int = 60
    max_concurrent_sessions: int = 20  # Increased from 10
    session_cleanup_batch_size: int = 5  # New: batch cleanup

    # SDK integration (optimized)
    sdk_retry_attempts: int = 3
    sdk_timeout_seconds: float = 5.0  # Reduced from 10.0
    sdk_connection_pool_size: int = 10  # New: connection pooling

    # User preferences (preserved)
    background_analysis_enabled: bool = True
    intervention_suggestions_enabled: bool = True
    learning_mode_enabled: bool = True

    # Performance optimizations (new)
    enable_analysis_caching: bool = True
    batch_analysis_size: int = 5
    max_memory_usage_mb: int = 500
    enable_incremental_analysis: bool = True

    # Logging and monitoring (optimized)
    detailed_logging: bool = False
    metrics_collection: bool = True
    metrics_aggregation_interval: int = 300  # 5 minutes


@dataclass
class OptimizedAnalysisCycleResult:
    """Optimized analysis cycle result with performance metadata"""
    cycle_id: str
    session_id: str
    timestamp: float
    analysis: ConversationAnalysis
    quality_gates: List[QualityGateResult]
    interventions_suggested: List[Dict[str, Any]]
    next_cycle_delay: float = field(default=20.0)

    # Performance metadata
    cycle_duration: float = 0.0
    cache_hit: bool = False
    sdk_response_time: float = 0.0
    analysis_performance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    # Orchestrator metrics
    total_sessions: int = 0
    active_sessions: int = 0
    total_analysis_cycles: int = 0
    total_interventions: int = 0
    average_quality_score: float = 0.0
    uptime_seconds: float = 0.0

    # Performance metrics
    avg_cycle_duration: float = 0.0
    cache_hit_rate: float = 0.0
    sdk_response_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    # Throughput metrics
    cycles_per_minute: float = 0.0
    sessions_per_hour: float = 0.0
    interventions_per_hour: float = 0.0


class OptimizedAutoModeOrchestrator:
    """
    High-performance auto-mode orchestrator with comprehensive optimizations.

    PRESERVES: All auto-mode functionality and user requirements
    OPTIMIZES: Performance, memory usage, and response times
    """

    def __init__(self, config: Optional[OptimizedOrchestratorConfig] = None):
        self.config = config or OptimizedOrchestratorConfig()
        self.state = OrchestratorState.INACTIVE
        self.logger = logging.getLogger(__name__)

        # Optimized core components
        self.session_manager = OptimizedSessionManager()
        self.analysis_engine = OptimizedAnalysisEngine()
        self.quality_gate_evaluator = QualityGateEvaluator()
        self.sdk_client = OptimizedClaudeAgentSDKClient()

        # Optimized runtime state
        self.active_sessions: Dict[str, OptimizedSessionState] = {}
        self.analysis_tasks: Dict[str, asyncio.Task] = {}
        self.background_tasks: set = set()

        # Performance monitoring
        self.metrics = PerformanceMetrics()
        self.start_time = time.time()
        self.cycle_times = deque(maxlen=100)
        self.analysis_queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        # Event callbacks (preserved)
        self.on_session_started: List[Callable] = []
        self.on_analysis_complete: List[Callable] = []
        self.on_intervention_suggested: List[Callable] = []
        self.on_session_ended: List[Callable] = []

        # Optimization features
        self._analysis_cache: Dict[str, ConversationAnalysis] = {}
        self._adaptive_intervals: Dict[str, float] = {}
        self._session_priorities: Dict[str, int] = defaultdict(int)

    async def initialize_optimized(self) -> bool:
        """
        Optimized initialization with parallel component startup.

        PRESERVES: All initialization requirements
        OPTIMIZES: Parallel initialization and reduced startup time
        """
        try:
            self.state = OrchestratorState.INITIALIZING
            self.logger.info("Initializing Optimized Auto-Mode Orchestrator")

            # Parallel component initialization
            init_tasks = [
                self.session_manager.initialize(),
                self.analysis_engine.initialize_optimized(),
                self.quality_gate_evaluator.initialize(),
                self.sdk_client.initialize(
                    timeout=self.config.sdk_timeout_seconds,
                    retry_attempts=self.config.sdk_retry_attempts
                )
            ]

            results = await asyncio.gather(*init_tasks, return_exceptions=True)

            # Check for initialization failures
            sdk_initialized = True
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    if i == 3:  # SDK initialization
                        self.logger.warning(f"SDK initialization failed: {result}")
                        sdk_initialized = False
                    else:
                        raise result

            # Start optimized background tasks
            self._start_optimized_background_tasks()

            self.state = OrchestratorState.ACTIVE
            self.logger.info("Optimized Auto-Mode Orchestrator initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize optimized orchestrator: {e}")
            self.state = OrchestratorState.ERROR
            return False

    def _start_optimized_background_tasks(self):
        """Start optimized background tasks for performance monitoring"""

        # Batch analysis processor
        task = asyncio.create_task(self._batch_analysis_processor())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

        # Performance metrics aggregator
        task = asyncio.create_task(self._performance_metrics_aggregator())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

        # Memory and resource monitor
        task = asyncio.create_task(self._resource_monitor())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

        # Adaptive interval optimizer
        if self.config.adaptive_interval_enabled:
            task = asyncio.create_task(self._adaptive_interval_optimizer())
            self.background_tasks.add(task)
            task.add_done_callback(self.background_tasks.discard)

    async def start_session_optimized(self, user_id: str, conversation_context: Dict[str, Any]) -> str:
        """
        Optimized session creation with performance enhancements.

        PRESERVES: All session creation requirements
        OPTIMIZES: Session limit checking and initialization
        """
        session_id = str(uuid.uuid4())
        session_start_time = time.time()

        try:
            # Optimized session limit check
            if len(self.active_sessions) >= self.config.max_concurrent_sessions:
                # Intelligent session eviction based on activity
                await self._evict_inactive_sessions()

                if len(self.active_sessions) >= self.config.max_concurrent_sessions:
                    raise RuntimeError("Maximum concurrent sessions reached")

            # Create optimized session state
            session_state = await self.session_manager.create_session_optimized(
                session_id=session_id,
                user_id=user_id,
                initial_context=conversation_context
            )

            self.active_sessions[session_id] = session_state

            # Start optimized analysis loop with priority
            if self.config.background_analysis_enabled:
                task = asyncio.create_task(
                    self._run_optimized_analysis_loop(session_id)
                )
                self.analysis_tasks[session_id] = task

            # Update metrics
            self.metrics.total_sessions += 1
            self.metrics.active_sessions = len(self.active_sessions)

            # Initialize adaptive interval
            if self.config.adaptive_interval_enabled:
                self._adaptive_intervals[session_id] = self.config.analysis_interval_seconds

            # Notify callbacks asynchronously
            if self.on_session_started:
                asyncio.create_task(self._notify_callbacks(self.on_session_started, session_state))

            session_duration = time.time() - session_start_time
            self.logger.info(f"Started optimized session: {session_id} in {session_duration:.3f}s")
            return session_id

        except Exception as e:
            self.logger.error(f"Failed to start optimized session: {e}")
            self.active_sessions.pop(session_id, None)
            raise

    async def _evict_inactive_sessions(self):
        """Intelligently evict inactive sessions based on activity"""
        if not self.active_sessions:
            return

        # Sort sessions by last activity and priority
        session_items = list(self.active_sessions.items())
        session_items.sort(
            key=lambda x: (
                self._session_priorities[x[0]],  # Lower priority first
                x[1].last_updated  # Older sessions first
            )
        )

        # Evict up to batch_size sessions
        evicted_count = 0
        for session_id, session_state in session_items:
            if evicted_count >= self.config.session_cleanup_batch_size:
                break

            # Check if session is truly inactive
            idle_time = time.time() - session_state.last_updated
            if idle_time > (self.config.session_timeout_minutes * 60 * 0.5):  # 50% of timeout
                await self.stop_session_optimized(session_id)
                evicted_count += 1

    async def _run_optimized_analysis_loop(self, session_id: str):
        """
        Optimized agentic analysis loop with adaptive timing and batching.

        PRESERVES: All analysis loop functionality
        OPTIMIZES: Timing, batching, and resource usage
        """
        cycle_count = 0
        consecutive_errors = 0
        max_consecutive_errors = 3

        try:
            while (cycle_count < self.config.max_analysis_cycles and
                   session_id in self.active_sessions and
                   consecutive_errors < max_consecutive_errors):

                cycle_start = time.time()
                cycle_id = f"{session_id}-{cycle_count}"

                try:
                    # Get adaptive interval for this session
                    wait_interval = self._adaptive_intervals.get(
                        session_id, self.config.analysis_interval_seconds
                    )

                    # Check if session needs analysis (optimized)
                    if not await self._should_analyze_session(session_id):
                        await asyncio.sleep(wait_interval * 0.5)  # Shorter wait for inactive sessions
                        continue

                    # Execute optimized analysis cycle
                    result = await self._execute_optimized_analysis_cycle(session_id, cycle_id)

                    if result:
                        # Update session state efficiently
                        await self._update_session_from_analysis(session_id, result)

                        # Handle quality gates asynchronously
                        if result.quality_gates:
                            asyncio.create_task(
                                self._handle_quality_gates_async(session_id, result.quality_gates)
                            )

                        # Update metrics
                        self.metrics.total_analysis_cycles += 1
                        cycle_duration = time.time() - cycle_start
                        self.cycle_times.append(cycle_duration)

                        # Update adaptive interval
                        if self.config.adaptive_interval_enabled:
                            self._update_adaptive_interval(session_id, result)

                        # Notify callbacks asynchronously
                        if self.on_analysis_complete:
                            asyncio.create_task(self._notify_callbacks(self.on_analysis_complete, result))

                        # Calculate next cycle delay
                        next_delay = result.next_cycle_delay
                        if cycle_duration < next_delay:
                            await asyncio.sleep(next_delay - cycle_duration)

                        consecutive_errors = 0  # Reset error count on success

                    else:
                        consecutive_errors += 1
                        await asyncio.sleep(min(5.0 * consecutive_errors, 30.0))  # Exponential backoff

                except asyncio.CancelledError:
                    self.logger.info(f"Optimized analysis loop cancelled for session: {session_id}")
                    break
                except Exception as e:
                    consecutive_errors += 1
                    self.logger.error(f"Optimized analysis cycle failed for session {session_id}: {e}")
                    await asyncio.sleep(min(2.0 * consecutive_errors, 10.0))

                cycle_count += 1

        except Exception as e:
            self.logger.error(f"Optimized analysis loop failed for session {session_id}: {e}")
        finally:
            # Clean up
            self.analysis_tasks.pop(session_id, None)
            self._adaptive_intervals.pop(session_id, None)

    async def _should_analyze_session(self, session_id: str) -> bool:
        """Determine if session needs analysis based on activity"""
        if session_id not in self.active_sessions:
            return False

        session_state = self.active_sessions[session_id]

        # Check activity level
        time_since_update = time.time() - session_state.last_updated

        # More frequent analysis for active sessions
        if time_since_update < 60:  # Active in last minute
            return True

        # Less frequent analysis for idle sessions
        if time_since_update > 600:  # Idle for 10+ minutes
            return time_since_update % 300 < 20  # Analyze every 5 minutes

        return True

    async def _execute_optimized_analysis_cycle(self, session_id: str, cycle_id: str) -> Optional[OptimizedAnalysisCycleResult]:
        """
        Execute optimized analysis cycle with caching and batching.

        PRESERVES: All analysis functionality
        OPTIMIZES: Caching, batching, and parallel operations
        """
        if session_id not in self.active_sessions:
            return None

        session_state = self.active_sessions[session_id]
        cycle_start = time.time()

        try:
            # Check analysis cache first
            cache_key = self._get_analysis_cache_key(session_state)
            cached_analysis = None

            if self.config.enable_analysis_caching:
                cached_analysis = self._analysis_cache.get(cache_key)

            if cached_analysis and self._is_cache_valid(cached_analysis):
                # Use cached analysis
                analysis = cached_analysis
                cache_hit = True
                sdk_response_time = 0.0
            else:
                # Perform fresh analysis
                analysis = await self.analysis_engine.analyze_conversation_optimized(
                    conversation_context=session_state.conversation_context,
                    session_history=session_state.analysis_history
                )

                # Cache the result
                if self.config.enable_analysis_caching:
                    self._analysis_cache[cache_key] = analysis

                cache_hit = False
                sdk_response_time = analysis.analysis_duration

            # Parallel quality gate evaluation
            quality_gates_task = asyncio.create_task(
                self.quality_gate_evaluator.evaluate(
                    analysis=analysis,
                    session_state=session_state,
                    config=self.config
                )
            )

            # Wait for quality gates
            quality_gates = await quality_gates_task

            # Generate interventions efficiently
            interventions = []
            for gate_result in quality_gates:
                if (gate_result.triggered and
                    gate_result.confidence >= self.config.intervention_confidence_threshold):
                    interventions.extend(gate_result.suggested_actions)

            # Calculate adaptive next cycle delay
            next_cycle_delay = self._calculate_adaptive_delay(analysis, session_state)

            # Create optimized result
            result = OptimizedAnalysisCycleResult(
                cycle_id=cycle_id,
                session_id=session_id,
                timestamp=time.time(),
                analysis=analysis,
                quality_gates=quality_gates,
                interventions_suggested=interventions,
                next_cycle_delay=next_cycle_delay,
                cycle_duration=time.time() - cycle_start,
                cache_hit=cache_hit,
                sdk_response_time=sdk_response_time,
                analysis_performance=self.analysis_engine.get_performance_metrics()
            )

            return result

        except Exception as e:
            self.logger.error(f"Optimized analysis cycle execution failed: {e}")
            return None

    def _get_analysis_cache_key(self, session_state: OptimizedSessionState) -> str:
        """Generate cache key for analysis results"""
        # Create hash based on conversation context
        context_str = str(session_state.conversation_context)
        import hashlib
        return hashlib.md5(context_str.encode()).hexdigest()

    def _is_cache_valid(self, cached_analysis: ConversationAnalysis) -> bool:
        """Check if cached analysis is still valid"""
        # Cache valid for 5 minutes
        return time.time() - cached_analysis.timestamp < 300

    def _calculate_adaptive_delay(self, analysis: ConversationAnalysis,
                                session_state: OptimizedSessionState) -> float:
        """Calculate adaptive delay based on analysis results"""
        base_interval = self.config.analysis_interval_seconds

        # Adjust based on activity level
        activity_factor = analysis.conversation_activity_level

        # Adjust based on quality score
        if analysis.quality_score < 0.5:
            quality_factor = 0.7  # More frequent analysis for poor quality
        elif analysis.quality_score > 0.8:
            quality_factor = 1.5  # Less frequent analysis for good quality
        else:
            quality_factor = 1.0

        adaptive_delay = base_interval * quality_factor / activity_factor
        return max(10.0, min(60.0, adaptive_delay))  # Clamp between 10s and 60s

    async def _update_session_from_analysis(self, session_id: str,
                                          result: OptimizedAnalysisCycleResult):
        """Efficiently update session state from analysis results"""
        if session_id not in self.active_sessions:
            return

        session_state = self.active_sessions[session_id]

        # Update efficiently
        session_state.last_analysis = result.analysis
        session_state.analysis_cycles += 1
        session_state.current_quality_score = result.analysis.quality_score
        session_state.mark_dirty()

        # Limit analysis history size for memory efficiency
        session_state.analysis_history.append(result)
        if len(session_state.analysis_history) > 20:
            session_state.analysis_history = session_state.analysis_history[-10:]

        # Update session priority based on quality
        if result.analysis.quality_score < 0.5:
            self._session_priorities[session_id] = 10  # High priority
        elif result.analysis.quality_score > 0.8:
            self._session_priorities[session_id] = 1   # Low priority
        else:
            self._session_priorities[session_id] = 5   # Medium priority

    async def _handle_quality_gates_async(self, session_id: str,
                                        quality_gates: List[QualityGateResult]):
        """Handle quality gates asynchronously"""
        try:
            if session_id not in self.active_sessions:
                return

            session_state = self.active_sessions[session_id]

            for gate_result in quality_gates:
                if not gate_result.triggered:
                    continue

                if (self.config.intervention_suggestions_enabled and
                    gate_result.confidence >= self.config.intervention_confidence_threshold):

                    # Update intervention count
                    session_state.total_interventions += len(gate_result.suggested_actions)
                    session_state.mark_dirty()

                    # Update metrics
                    self.metrics.total_interventions += len(gate_result.suggested_actions)

                    # Notify callbacks
                    if self.on_intervention_suggested:
                        await self._notify_callbacks(self.on_intervention_suggested, session_id, gate_result)

        except Exception as e:
            self.logger.error(f"Error handling quality gates: {e}")

    async def _notify_callbacks(self, callbacks: List[Callable], *args):
        """Efficiently notify callbacks with error handling"""
        if not callbacks:
            return

        tasks = []
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(callback(*args))
                else:
                    # Run sync callback in thread pool
                    tasks.append(asyncio.create_task(
                        asyncio.get_event_loop().run_in_executor(None, callback, *args)
                    ))
            except Exception as e:
                self.logger.warning(f"Callback preparation failed: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _batch_analysis_processor(self):
        """Background task for batch processing analysis requests"""
        while self.state == OrchestratorState.ACTIVE:
            try:
                # Collect batch of analysis requests
                batch = []
                timeout = 1.0

                for _ in range(self.config.batch_analysis_size):
                    try:
                        request = await asyncio.wait_for(self.analysis_queue.get(), timeout=timeout)
                        batch.append(request)
                        timeout = 0.1  # Shorter timeout for subsequent items
                    except asyncio.TimeoutError:
                        break

                if batch:
                    # Process batch in parallel
                    await asyncio.gather(*batch, return_exceptions=True)

                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Batch analysis processor error: {e}")

    async def _performance_metrics_aggregator(self):
        """Background task for aggregating performance metrics"""
        while self.state == OrchestratorState.ACTIVE:
            try:
                await asyncio.sleep(self.config.metrics_aggregation_interval)

                # Update comprehensive metrics
                current_time = time.time()
                self.metrics.uptime_seconds = current_time - self.start_time
                self.metrics.active_sessions = len(self.active_sessions)

                # Calculate averages
                if self.cycle_times:
                    self.metrics.avg_cycle_duration = sum(self.cycle_times) / len(self.cycle_times)

                # Calculate throughput
                if self.metrics.uptime_seconds > 0:
                    self.metrics.cycles_per_minute = (self.metrics.total_analysis_cycles * 60) / self.metrics.uptime_seconds
                    self.metrics.sessions_per_hour = (self.metrics.total_sessions * 3600) / self.metrics.uptime_seconds

                # Log performance summary
                if self.config.detailed_logging:
                    self.logger.info(f"Performance: {self.metrics.cycles_per_minute:.1f} cycles/min, "
                                   f"{self.metrics.avg_cycle_duration:.3f}s avg duration, "
                                   f"{self.metrics.active_sessions} active sessions")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics aggregator error: {e}")

    async def _resource_monitor(self):
        """Background task for monitoring resource usage"""
        while self.state == OrchestratorState.ACTIVE:
            try:
                await asyncio.sleep(60)  # Check every minute

                # Memory usage estimation
                import sys
                memory_mb = sys.getsizeof(self.active_sessions) / (1024 * 1024)
                memory_mb += sum(sys.getsizeof(session) for session in self.active_sessions.values()) / (1024 * 1024)

                self.metrics.memory_usage_mb = memory_mb

                # Check memory limits
                if memory_mb > self.config.max_memory_usage_mb:
                    self.logger.warning(f"Memory usage ({memory_mb:.1f}MB) exceeds limit ({self.config.max_memory_usage_mb}MB)")
                    await self._cleanup_memory()

                # Cleanup analysis cache periodically
                if len(self._analysis_cache) > 100:
                    # Remove old entries
                    current_time = time.time()
                    expired_keys = [
                        key for key, analysis in self._analysis_cache.items()
                        if current_time - analysis.timestamp > 600  # 10 minutes
                    ]

                    for key in expired_keys:
                        del self._analysis_cache[key]

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Resource monitor error: {e}")

    async def _cleanup_memory(self):
        """Clean up memory when usage is high"""
        try:
            # Clear analysis cache
            self._analysis_cache.clear()

            # Trigger session cleanup
            await self._evict_inactive_sessions()

            # Limit cycle times tracking
            if len(self.cycle_times) > 50:
                # Keep only recent times
                recent_times = list(self.cycle_times)[-25:]
                self.cycle_times.clear()
                self.cycle_times.extend(recent_times)

            self.logger.info("Memory cleanup completed")

        except Exception as e:
            self.logger.error(f"Memory cleanup error: {e}")

    async def _adaptive_interval_optimizer(self):
        """Background task for optimizing analysis intervals"""
        while self.state == OrchestratorState.ACTIVE:
            try:
                await asyncio.sleep(300)  # Optimize every 5 minutes

                for session_id in list(self._adaptive_intervals.keys()):
                    if session_id not in self.active_sessions:
                        self._adaptive_intervals.pop(session_id, None)
                        continue

                    session_state = self.active_sessions[session_id]

                    # Adjust interval based on session activity
                    time_since_update = time.time() - session_state.last_updated

                    if time_since_update < 60:  # Very active
                        self._adaptive_intervals[session_id] = max(10.0, self._adaptive_intervals[session_id] * 0.8)
                    elif time_since_update > 600:  # Inactive
                        self._adaptive_intervals[session_id] = min(120.0, self._adaptive_intervals[session_id] * 1.5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Adaptive interval optimizer error: {e}")

    def _update_adaptive_interval(self, session_id: str, result: OptimizedAnalysisCycleResult):
        """Update adaptive interval based on analysis results"""
        if session_id not in self._adaptive_intervals:
            return

        current_interval = self._adaptive_intervals[session_id]

        # Adjust based on analysis results
        if result.analysis.quality_score < 0.5:
            # Poor quality - analyze more frequently
            new_interval = max(10.0, current_interval * 0.8)
        elif result.analysis.quality_score > 0.8:
            # Good quality - analyze less frequently
            new_interval = min(60.0, current_interval * 1.2)
        else:
            # Maintain current interval
            new_interval = current_interval

        self._adaptive_intervals[session_id] = new_interval

    async def stop_session_optimized(self, session_id: str) -> bool:
        """
        Optimized session stopping with efficient cleanup.

        PRESERVES: All session stopping requirements
        OPTIMIZES: Cleanup efficiency and resource management
        """
        try:
            if session_id not in self.active_sessions:
                self.logger.warning(f"Attempted to stop non-existent session: {session_id}")
                return False

            # Cancel analysis task efficiently
            if session_id in self.analysis_tasks:
                task = self.analysis_tasks[session_id]
                if not task.done():
                    task.cancel()
                    try:
                        await asyncio.wait_for(task, timeout=1.0)
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        pass
                del self.analysis_tasks[session_id]

            # Get session state for callbacks
            session_state = self.active_sessions[session_id]

            # Clean up session efficiently
            await self.session_manager.close_session_optimized(session_id)
            del self.active_sessions[session_id]

            # Clean up optimization data
            self._adaptive_intervals.pop(session_id, None)
            self._session_priorities.pop(session_id, None)

            # Update metrics
            self.metrics.active_sessions = len(self.active_sessions)

            # Notify callbacks asynchronously
            if self.on_session_ended:
                asyncio.create_task(self._notify_callbacks(self.on_session_ended, session_state))

            self.logger.info(f"Stopped optimized session: {session_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to stop optimized session {session_id}: {e}")
            return False

    async def shutdown_optimized(self):
        """
        Optimized shutdown with efficient resource cleanup.

        PRESERVES: All shutdown requirements
        OPTIMIZES: Cleanup speed and resource management
        """
        try:
            self.logger.info("Shutting down Optimized Auto-Mode Orchestrator")

            # Cancel all background tasks
            for task in self.background_tasks:
                if not task.done():
                    task.cancel()

            # Cancel all analysis tasks
            analysis_tasks = list(self.analysis_tasks.values())
            for task in analysis_tasks:
                if not task.done():
                    task.cancel()

            # Wait for all tasks to complete (with timeout)
            all_tasks = list(self.background_tasks) + analysis_tasks
            if all_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*all_tasks, return_exceptions=True),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("Some tasks did not complete within timeout")

            # Close all sessions in parallel
            if self.active_sessions:
                session_ids = list(self.active_sessions.keys())
                close_tasks = [self.stop_session_optimized(sid) for sid in session_ids]
                await asyncio.gather(*close_tasks, return_exceptions=True)

            # Shutdown components in parallel
            shutdown_tasks = [
                self.sdk_client.shutdown(),
                self.session_manager.shutdown_optimized()
            ]
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)

            # Final cleanup
            self._analysis_cache.clear()
            self._adaptive_intervals.clear()
            self._session_priorities.clear()

            self.state = OrchestratorState.INACTIVE
            self.logger.info("Optimized Auto-Mode Orchestrator shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during optimized orchestrator shutdown: {e}")
            self.state = OrchestratorState.ERROR

    def get_optimized_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        # Update dynamic metrics
        current_time = time.time()
        self.metrics.uptime_seconds = current_time - self.start_time

        # Get component metrics
        sdk_metrics = self.sdk_client.get_performance_metrics() if hasattr(self.sdk_client, 'get_performance_metrics') else {}
        session_metrics = self.session_manager.get_performance_stats() if hasattr(self.session_manager, 'get_performance_stats') else {}
        analysis_metrics = self.analysis_engine.get_performance_metrics() if hasattr(self.analysis_engine, 'get_performance_metrics') else {}

        return {
            'orchestrator_metrics': {
                'total_sessions': self.metrics.total_sessions,
                'active_sessions': self.metrics.active_sessions,
                'total_analysis_cycles': self.metrics.total_analysis_cycles,
                'total_interventions': self.metrics.total_interventions,
                'average_quality_score': self.metrics.average_quality_score,
                'uptime_seconds': self.metrics.uptime_seconds,
                'avg_cycle_duration': self.metrics.avg_cycle_duration,
                'cycles_per_minute': self.metrics.cycles_per_minute,
                'memory_usage_mb': self.metrics.memory_usage_mb
            },
            'sdk_metrics': sdk_metrics,
            'session_metrics': session_metrics,
            'analysis_metrics': analysis_metrics,
            'optimization_features': {
                'adaptive_intervals_enabled': self.config.adaptive_interval_enabled,
                'analysis_caching_enabled': self.config.enable_analysis_caching,
                'batch_analysis_enabled': self.config.batch_analysis_size > 1,
                'active_adaptive_intervals': len(self._adaptive_intervals),
                'analysis_cache_size': len(self._analysis_cache)
            }
        }