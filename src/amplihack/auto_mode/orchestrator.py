"""
Auto-Mode Orchestrator

Core orchestration engine for auto-mode functionality.
Manages the agentic loop, coordinates with Claude Agent SDK,
and handles session lifecycle.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid

from .session import SessionManager, SessionState
from .analysis import AnalysisEngine, ConversationAnalysis
from .quality_gates import QualityGateEvaluator, QualityGateResult
from .sdk_integration import ClaudeAgentSDKClient


class OrchestratorState(Enum):
    """States of the auto-mode orchestrator"""
    INACTIVE = "inactive"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    ANALYZING = "analyzing"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class OrchestratorConfig:
    """Configuration for the auto-mode orchestrator"""
    # Analysis cycle timing
    analysis_interval_seconds: float = 30.0
    max_analysis_cycles: int = 100

    # Quality thresholds
    min_quality_threshold: float = 0.6
    intervention_confidence_threshold: float = 0.7

    # Session management
    session_timeout_minutes: int = 60
    max_concurrent_sessions: int = 10

    # SDK integration
    sdk_retry_attempts: int = 3
    sdk_timeout_seconds: float = 10.0

    # User preferences
    background_analysis_enabled: bool = True
    intervention_suggestions_enabled: bool = True
    learning_mode_enabled: bool = True

    # Logging and monitoring
    detailed_logging: bool = False
    metrics_collection: bool = True


@dataclass
class AnalysisCycleResult:
    """Result of a single analysis cycle"""
    cycle_id: str
    session_id: str
    timestamp: float
    analysis: ConversationAnalysis
    quality_gates: List[QualityGateResult]
    interventions_suggested: List[Dict[str, Any]]
    next_cycle_delay: float = field(default=30.0)


class AutoModeOrchestrator:
    """
    Main orchestrator for auto-mode functionality.

    Responsibilities:
    - Manage persistent analysis sessions
    - Execute agentic analysis loops
    - Coordinate with Claude Agent SDK
    - Handle quality gate evaluation
    - Provide user interface for control
    """

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()
        self.state = OrchestratorState.INACTIVE
        self.logger = logging.getLogger(__name__)

        # Core components
        self.session_manager = SessionManager()
        self.analysis_engine = AnalysisEngine()
        self.quality_gate_evaluator = QualityGateEvaluator()
        self.sdk_client = ClaudeAgentSDKClient()

        # Runtime state
        self.active_sessions: Dict[str, SessionState] = {}
        self.analysis_tasks: Dict[str, asyncio.Task] = {}
        self.metrics: Dict[str, Any] = {
            'total_sessions': 0,
            'total_analysis_cycles': 0,
            'total_interventions': 0,
            'average_quality_score': 0.0,
            'uptime_seconds': 0.0
        }
        self.start_time = time.time()

        # Event callbacks
        self.on_session_started: List[Callable] = []
        self.on_analysis_complete: List[Callable] = []
        self.on_intervention_suggested: List[Callable] = []
        self.on_session_ended: List[Callable] = []

    async def initialize(self) -> bool:
        """
        Initialize the orchestrator and all components.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self.state = OrchestratorState.INITIALIZING
            self.logger.info("Initializing Auto-Mode Orchestrator")

            # Initialize core components
            await self.session_manager.initialize()
            await self.analysis_engine.initialize()
            await self.quality_gate_evaluator.initialize()

            # Initialize SDK connection
            sdk_initialized = await self.sdk_client.initialize(
                timeout=self.config.sdk_timeout_seconds,
                retry_attempts=self.config.sdk_retry_attempts
            )

            if not sdk_initialized:
                self.logger.warning("Claude Agent SDK initialization failed - continuing without SDK")

            self.state = OrchestratorState.ACTIVE
            self.logger.info("Auto-Mode Orchestrator initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize orchestrator: {e}")
            self.state = OrchestratorState.ERROR
            return False

    async def start_session(self, user_id: str, conversation_context: Dict[str, Any]) -> str:
        """
        Start a new auto-mode session.

        Args:
            user_id: Unique user identifier
            conversation_context: Initial conversation context

        Returns:
            str: Session ID of the created session
        """
        session_id = str(uuid.uuid4())

        try:
            # Check session limits
            if len(self.active_sessions) >= self.config.max_concurrent_sessions:
                raise RuntimeError("Maximum concurrent sessions reached")

            # Create session state
            session_state = await self.session_manager.create_session(
                session_id=session_id,
                user_id=user_id,
                initial_context=conversation_context
            )

            self.active_sessions[session_id] = session_state

            # Start analysis loop if background analysis is enabled
            if self.config.background_analysis_enabled:
                task = asyncio.create_task(self._run_analysis_loop(session_id))
                self.analysis_tasks[session_id] = task

            # Update metrics
            self.metrics['total_sessions'] += 1

            # Notify callbacks
            for callback in self.on_session_started:
                try:
                    await callback(session_state)
                except Exception as e:
                    self.logger.warning(f"Session started callback failed: {e}")

            self.logger.info(f"Started auto-mode session: {session_id}")
            return session_id

        except Exception as e:
            self.logger.error(f"Failed to start session: {e}")
            # Cleanup on failure
            self.active_sessions.pop(session_id, None)
            raise

    async def update_conversation(self, session_id: str, conversation_update: Dict[str, Any]) -> bool:
        """
        Update conversation context for an active session.

        Args:
            session_id: Session to update
            conversation_update: New conversation data

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            if session_id not in self.active_sessions:
                self.logger.warning(f"Attempted to update non-existent session: {session_id}")
                return False

            session_state = self.active_sessions[session_id]
            await self.session_manager.update_conversation(session_state, conversation_update)

            return True

        except Exception as e:
            self.logger.error(f"Failed to update conversation for session {session_id}: {e}")
            return False

    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a session.

        Args:
            session_id: Session to query

        Returns:
            Optional[Dict]: Session status information or None if not found
        """
        if session_id not in self.active_sessions:
            return None

        session_state = self.active_sessions[session_id]

        return {
            'session_id': session_id,
            'user_id': session_state.user_id,
            'created_at': session_state.created_at,
            'last_updated': session_state.last_updated,
            'analysis_cycles': session_state.analysis_cycles,
            'current_quality_score': session_state.current_quality_score,
            'total_interventions': session_state.total_interventions,
            'status': 'active' if session_id in self.analysis_tasks else 'paused'
        }

    async def stop_session(self, session_id: str) -> bool:
        """
        Stop an active auto-mode session.

        Args:
            session_id: Session to stop

        Returns:
            bool: True if session stopped successfully, False otherwise
        """
        try:
            if session_id not in self.active_sessions:
                self.logger.warning(f"Attempted to stop non-existent session: {session_id}")
                return False

            # Cancel analysis task if running
            if session_id in self.analysis_tasks:
                self.analysis_tasks[session_id].cancel()
                del self.analysis_tasks[session_id]

            # Get session state for callbacks
            session_state = self.active_sessions[session_id]

            # Clean up session
            await self.session_manager.close_session(session_state)
            del self.active_sessions[session_id]

            # Notify callbacks
            for callback in self.on_session_ended:
                try:
                    await callback(session_state)
                except Exception as e:
                    self.logger.warning(f"Session ended callback failed: {e}")

            self.logger.info(f"Stopped auto-mode session: {session_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to stop session {session_id}: {e}")
            return False

    async def _run_analysis_loop(self, session_id: str):
        """
        Main agentic analysis loop for a session.

        Args:
            session_id: Session to analyze
        """
        cycle_count = 0

        try:
            while (cycle_count < self.config.max_analysis_cycles and
                   session_id in self.active_sessions):

                cycle_start = time.time()
                cycle_id = f"{session_id}-{cycle_count}"

                try:
                    # Perform analysis cycle
                    result = await self._execute_analysis_cycle(session_id, cycle_id)

                    # Update session state
                    session_state = self.active_sessions[session_id]
                    session_state.last_analysis = result.analysis
                    session_state.analysis_cycles += 1
                    session_state.current_quality_score = result.analysis.quality_score
                    session_state.last_updated = time.time()

                    # Handle quality gate results
                    await self._handle_quality_gates(session_id, result.quality_gates)

                    # Update metrics
                    self.metrics['total_analysis_cycles'] += 1
                    if result.interventions_suggested:
                        self.metrics['total_interventions'] += len(result.interventions_suggested)

                    # Notify callbacks
                    for callback in self.on_analysis_complete:
                        try:
                            await callback(result)
                        except Exception as e:
                            self.logger.warning(f"Analysis complete callback failed: {e}")

                    # Wait for next cycle
                    cycle_duration = time.time() - cycle_start
                    wait_time = max(0, result.next_cycle_delay - cycle_duration)

                    if wait_time > 0:
                        await asyncio.sleep(wait_time)

                except asyncio.CancelledError:
                    self.logger.info(f"Analysis loop cancelled for session: {session_id}")
                    break
                except Exception as e:
                    self.logger.error(f"Analysis cycle failed for session {session_id}: {e}")
                    # Continue with next cycle after error delay
                    await asyncio.sleep(5.0)

                cycle_count += 1

        except Exception as e:
            self.logger.error(f"Analysis loop failed for session {session_id}: {e}")
        finally:
            # Clean up analysis task reference
            self.analysis_tasks.pop(session_id, None)

    async def _execute_analysis_cycle(self, session_id: str, cycle_id: str) -> AnalysisCycleResult:
        """
        Execute a single analysis cycle.

        Args:
            session_id: Session being analyzed
            cycle_id: Unique cycle identifier

        Returns:
            AnalysisCycleResult: Results of the analysis cycle
        """
        session_state = self.active_sessions[session_id]

        # Perform conversation analysis
        analysis = await self.analysis_engine.analyze_conversation(
            conversation_context=session_state.conversation_context,
            session_history=session_state.analysis_history
        )

        # Evaluate quality gates
        quality_gates = await self.quality_gate_evaluator.evaluate(
            analysis=analysis,
            session_state=session_state,
            config=self.config
        )

        # Generate interventions based on quality gates
        interventions = []
        for gate_result in quality_gates:
            if gate_result.triggered and gate_result.confidence >= self.config.intervention_confidence_threshold:
                interventions.extend(gate_result.suggested_actions)

        # Calculate next cycle delay (adaptive based on activity)
        base_interval = self.config.analysis_interval_seconds
        activity_factor = min(2.0, analysis.conversation_activity_level)
        next_cycle_delay = base_interval / activity_factor

        result = AnalysisCycleResult(
            cycle_id=cycle_id,
            session_id=session_id,
            timestamp=time.time(),
            analysis=analysis,
            quality_gates=quality_gates,
            interventions_suggested=interventions,
            next_cycle_delay=next_cycle_delay
        )

        # Store in session history
        session_state.analysis_history.append(result)

        return result

    async def _handle_quality_gates(self, session_id: str, quality_gates: List[QualityGateResult]):
        """
        Handle quality gate results and trigger appropriate interventions.

        Args:
            session_id: Session being processed
            quality_gates: Quality gate evaluation results
        """
        session_state = self.active_sessions[session_id]

        for gate_result in quality_gates:
            if not gate_result.triggered:
                continue

            # Check if intervention should be suggested
            if (self.config.intervention_suggestions_enabled and
                gate_result.confidence >= self.config.intervention_confidence_threshold):

                # Update session intervention count
                session_state.total_interventions += len(gate_result.suggested_actions)

                # Notify callbacks
                for callback in self.on_intervention_suggested:
                    try:
                        await callback(session_id, gate_result)
                    except Exception as e:
                        self.logger.warning(f"Intervention suggested callback failed: {e}")

    async def shutdown(self):
        """Gracefully shutdown the orchestrator"""
        try:
            self.logger.info("Shutting down Auto-Mode Orchestrator")

            # Cancel all analysis tasks
            for task in self.analysis_tasks.values():
                task.cancel()

            # Wait for tasks to complete
            if self.analysis_tasks:
                await asyncio.gather(*self.analysis_tasks.values(), return_exceptions=True)

            # Close all sessions
            for session_id in list(self.active_sessions.keys()):
                await self.stop_session(session_id)

            # Shutdown components
            await self.sdk_client.shutdown()
            await self.session_manager.shutdown()

            self.state = OrchestratorState.INACTIVE
            self.logger.info("Auto-Mode Orchestrator shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during orchestrator shutdown: {e}")
            self.state = OrchestratorState.ERROR

    def get_metrics(self) -> Dict[str, Any]:
        """Get current orchestrator metrics"""
        current_time = time.time()
        self.metrics['uptime_seconds'] = current_time - self.start_time
        self.metrics['active_sessions'] = len(self.active_sessions)
        self.metrics['active_analysis_tasks'] = len(self.analysis_tasks)

        # Calculate average quality score
        if self.active_sessions:
            total_quality = sum(s.current_quality_score for s in self.active_sessions.values())
            self.metrics['average_quality_score'] = total_quality / len(self.active_sessions)

        return self.metrics.copy()