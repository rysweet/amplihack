"""
Session State Integration for Auto-Mode

Provides bidirectional state sharing between Claude Code sessions and
the auto-mode system, with persistence and coordination capabilities.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .analysis_engine import AnalysisResult, AnalysisType, ConversationAnalysisEngine
from .prompt_coordinator import PromptContext, PromptCoordinator, PromptType
from .session_manager import SDKSessionManager, SessionConfig

logger = logging.getLogger(__name__)


class AutoModeState(Enum):
    """States of auto-mode operation"""

    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"
    STOPPED = "stopped"


@dataclass
class AutoModeConfig:
    """Configuration for auto-mode integration"""

    max_iterations: int = 50
    iteration_timeout_seconds: int = 300
    min_confidence_threshold: float = 0.6
    auto_progression_enabled: bool = True
    persistence_enabled: bool = True
    state_sync_interval_seconds: int = 30
    error_recovery_attempts: int = 3

    def __post_init__(self):
        """Validate configuration after initialization"""
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate configuration parameters"""
        errors = []

        # Validate max_iterations
        if not isinstance(self.max_iterations, int) or self.max_iterations <= 0:
            errors.append("max_iterations must be a positive integer")
        elif self.max_iterations > 1000:
            errors.append("max_iterations cannot exceed 1000")

        # Validate iteration_timeout_seconds
        if (
            not isinstance(self.iteration_timeout_seconds, int)
            or self.iteration_timeout_seconds <= 0
        ):
            errors.append("iteration_timeout_seconds must be a positive integer")
        elif self.iteration_timeout_seconds > 3600:  # 1 hour max
            errors.append("iteration_timeout_seconds cannot exceed 3600 (1 hour)")

        # Validate min_confidence_threshold
        if not isinstance(self.min_confidence_threshold, (int, float)):
            errors.append("min_confidence_threshold must be a number")
        elif not 0.0 <= self.min_confidence_threshold <= 1.0:
            errors.append("min_confidence_threshold must be between 0.0 and 1.0")

        # Validate state_sync_interval_seconds
        if (
            not isinstance(self.state_sync_interval_seconds, int)
            or self.state_sync_interval_seconds <= 0
        ):
            errors.append("state_sync_interval_seconds must be a positive integer")
        elif self.state_sync_interval_seconds > 300:  # 5 minutes max
            errors.append("state_sync_interval_seconds cannot exceed 300 (5 minutes)")

        # Validate error_recovery_attempts
        if not isinstance(self.error_recovery_attempts, int) or self.error_recovery_attempts < 0:
            errors.append("error_recovery_attempts must be a non-negative integer")
        elif self.error_recovery_attempts > 10:
            errors.append("error_recovery_attempts cannot exceed 10")

        # Validate boolean types
        if not isinstance(self.auto_progression_enabled, bool):
            errors.append("auto_progression_enabled must be a boolean")
        if not isinstance(self.persistence_enabled, bool):
            errors.append("persistence_enabled must be a boolean")

        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")


@dataclass
class StateSnapshot:
    """Snapshot of auto-mode state at a point in time"""

    timestamp: datetime
    session_id: str
    auto_mode_state: AutoModeState
    current_iteration: int
    user_objective: str
    working_directory: str
    latest_claude_output: str
    latest_analysis: Optional[AnalysisResult]
    pending_prompts: List[str]
    error_count: int
    metadata: Dict[str, Any]


@dataclass
class ProgressMilestone:
    """A milestone in auto-mode progress"""

    id: str
    iteration: int
    timestamp: datetime
    description: str
    confidence: float
    evidence: List[str]
    next_actions: List[str]


class StateIntegrationError(Exception):
    """Raised when state integration operations fail"""

    pass


class AutoModeOrchestrator:
    """
    Main orchestrator for auto-mode state integration.

    Coordinates session management, analysis, and prompt generation
    with bidirectional state synchronization and persistence.
    """

    def __init__(
        self,
        config: AutoModeConfig = AutoModeConfig(),
        session_config: Optional[SessionConfig] = None,
    ):
        self.config = config
        self.auto_mode_state = AutoModeState.INITIALIZING
        self.current_iteration = 0
        self.error_count = 0

        # Initialize components
        self.session_manager = SDKSessionManager(session_config or SessionConfig())
        self.analysis_engine = ConversationAnalysisEngine()
        self.prompt_coordinator = PromptCoordinator()

        # State tracking
        self.state_snapshots: List[StateSnapshot] = []
        self.progress_milestones: List[ProgressMilestone] = []
        self.active_session_id: Optional[str] = None
        self.current_context: Optional[PromptContext] = None

        # Event system
        self.state_change_callbacks: List[Callable[[AutoModeState, StateSnapshot], None]] = []
        self.milestone_callbacks: List[Callable[[ProgressMilestone], None]] = []

        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()

        self._ensure_persistence_directory()

    def _ensure_persistence_directory(self) -> None:
        """Ensure persistence directory exists"""
        if self.config.persistence_enabled:
            Path(".claude/runtime/auto_mode").mkdir(parents=True, exist_ok=True)

    async def start_auto_mode_session(self, user_objective: str, working_directory: str) -> str:
        """
        Start a new auto-mode session.

        Args:
            user_objective: User's stated objective
            working_directory: Working directory for the session

        Returns:
            Session ID for the auto-mode session

        Raises:
            StateIntegrationError: If session start fails
        """
        try:
            # Validate inputs
            self._validate_session_inputs(user_objective, working_directory)

            self.auto_mode_state = AutoModeState.INITIALIZING
            self.current_iteration = 0
            self.error_count = 0

            # Create SDK session
            session_id = await self.session_manager.create_session(
                user_objective, working_directory
            )
            self.active_session_id = session_id

            # Create initial context
            self.current_context = self.prompt_coordinator.create_context(
                session_id=session_id,
                user_objective=user_objective,
                working_directory=working_directory,
                current_step=1,
                total_steps=self.config.max_iterations,
            )

            # Take initial snapshot
            await self._take_state_snapshot("Session initialized")

            # Start background tasks
            await self._start_background_tasks()

            # Transition to active state
            await self._transition_state(AutoModeState.ACTIVE)

            logger.info(f"Started auto-mode session {session_id} for objective: {user_objective}")
            return session_id

        except Exception as e:
            self.auto_mode_state = AutoModeState.ERROR
            raise StateIntegrationError(f"Failed to start auto-mode session: {e}")

    async def process_claude_output(
        self, claude_output: str, output_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process new Claude Code output and determine next actions.

        Args:
            claude_output: Output from Claude Code to analyze
            output_metadata: Additional metadata about the output

        Returns:
            Processing result with next actions and analysis

        Raises:
            StateIntegrationError: If processing fails
        """
        if not self.active_session_id or not self.current_context:
            raise StateIntegrationError("No active auto-mode session")

        try:
            self.current_iteration += 1

            # Update session activity
            await self.session_manager.update_session_activity(self.active_session_id)

            # Add to conversation history
            await self.session_manager.add_conversation_message(
                self.active_session_id,
                role="assistant",
                content=claude_output,
                message_type="claude_output",
                metadata=output_metadata,
            )

            # Analyze the output
            analysis_result = await self.analysis_engine.analyze_conversation(
                session_id=self.active_session_id,
                claude_output=claude_output,
                user_objective=self.current_context.user_objective,
                analysis_type=AnalysisType.PROGRESS_EVALUATION,
                context=asdict(self.current_context),
            )

            # Update context with analysis
            self.current_context = self.prompt_coordinator.update_context(
                self.current_context,
                current_step=self.current_iteration,
                previous_outputs=self.current_context.previous_outputs + [claude_output],
                analysis_results=self.current_context.analysis_results + [asdict(analysis_result)],
            )

            # Check for milestones
            await self._check_for_milestones(analysis_result)

            # Generate next action if confidence is sufficient
            next_action = None
            if analysis_result.confidence >= self.config.min_confidence_threshold:
                next_action = await self._generate_next_action(analysis_result)

            # Take state snapshot
            await self._take_state_snapshot(f"Processed iteration {self.current_iteration}")

            # Prepare response
            response = {
                "iteration": self.current_iteration,
                "analysis": asdict(analysis_result),
                "next_action": next_action,
                "confidence": analysis_result.confidence,
                "should_continue": await self._should_continue_auto_mode(analysis_result),
                "state": self.auto_mode_state.value,
            }

            logger.info(f"Processed Claude output for iteration {self.current_iteration}")
            return response

        except Exception as e:
            self.error_count += 1
            logger.error(f"Error processing Claude output: {e}")

            # Enhanced error handling with configuration validation
            if self.error_count >= self.config.error_recovery_attempts:
                await self._transition_state(AutoModeState.ERROR)
                logger.critical(f"Auto-mode entering error state after {self.error_count} failures")

            raise StateIntegrationError(f"Failed to process Claude output: {e}")

    def _validate_session_inputs(self, user_objective: str, working_directory: str) -> None:
        """Validate session creation inputs"""
        if not user_objective or not user_objective.strip():
            raise ValueError("user_objective cannot be empty")

        if len(user_objective) > 10000:
            raise ValueError("user_objective is too long (max 10000 characters)")

        if not working_directory or not working_directory.strip():
            raise ValueError("working_directory cannot be empty")

        # Basic path validation
        try:
            from pathlib import Path

            path = Path(working_directory)
            if not path.is_absolute():
                raise ValueError("working_directory must be an absolute path")
        except Exception as e:
            raise ValueError(f"Invalid working_directory: {e}")

        # Security check for dangerous paths
        dangerous_paths = ["/etc", "/bin", "/sbin", "/usr/bin", "/usr/sbin", "/root"]
        for dangerous_path in dangerous_paths:
            if working_directory.startswith(dangerous_path):
                raise ValueError(
                    f"working_directory cannot be in restricted system directory: {dangerous_path}"
                )

    async def _generate_next_action(self, analysis_result: AnalysisResult) -> Optional[str]:
        """Generate the next action based on analysis results"""
        try:
            # Determine appropriate prompt type
            prompt_type = PromptType.NEXT_ACTION

            if analysis_result.confidence < 0.7:
                prompt_type = PromptType.OBJECTIVE_CLARIFICATION
            elif "error" in analysis_result.ai_reasoning.lower():
                prompt_type = PromptType.ERROR_RESOLUTION
            elif self.current_iteration % 5 == 0:  # Periodic quality check
                prompt_type = PromptType.QUALITY_REVIEW

            # Find appropriate template
            templates = self.prompt_coordinator.list_templates(prompt_type)
            if not templates:
                logger.warning(f"No templates found for type {prompt_type}")
                return None

            template = templates[0]  # Use first available template

            # Render prompt (ensure context exists)
            if self.current_context is None:
                logger.warning("Current context is None, creating default context")
                self.current_context = self.prompt_coordinator.create_context(
                    session_id="default",
                    user_objective="Generate next action",
                    working_directory="/tmp",
                    current_step=1,
                )

            rendered_prompt = self.prompt_coordinator.render_prompt(
                template.id, self.current_context, {"analysis_insights": analysis_result.findings}
            )

            return rendered_prompt.content

        except Exception as e:
            logger.error(f"Failed to generate next action: {e}")
            return None

    async def _check_for_milestones(self, analysis_result: AnalysisResult) -> None:
        """Check if current state represents a significant milestone"""
        try:
            # Define milestone criteria
            is_milestone = (
                analysis_result.confidence > 0.8
                or analysis_result.quality_score > 0.8
                or len(analysis_result.recommendations) > 3
                or self.current_iteration % 10 == 0  # Every 10 iterations
            )

            if is_milestone:
                milestone = ProgressMilestone(
                    id=str(uuid.uuid4()),
                    iteration=self.current_iteration,
                    timestamp=datetime.now(),
                    description=f"Milestone at iteration {self.current_iteration}",
                    confidence=analysis_result.confidence,
                    evidence=analysis_result.findings,
                    next_actions=analysis_result.recommendations,
                )

                self.progress_milestones.append(milestone)

                # Notify callbacks
                for callback in self.milestone_callbacks:
                    try:
                        callback(milestone)
                    except Exception as e:
                        logger.error(f"Milestone callback error: {e}")

                logger.info(f"Reached milestone: {milestone.description}")

        except Exception as e:
            logger.error(f"Error checking milestones: {e}")

    async def _should_continue_auto_mode(self, analysis_result: AnalysisResult) -> bool:
        """Determine if auto-mode should continue"""
        # Check iteration limit
        if self.current_iteration >= self.config.max_iterations:
            return False

        # Check confidence threshold
        if analysis_result.confidence < self.config.min_confidence_threshold:
            return False

        # Check for completion indicators
        completion_keywords = ["complete", "finished", "done", "accomplished"]
        if any(keyword in analysis_result.ai_reasoning.lower() for keyword in completion_keywords):
            return False

        # Check error state
        if self.auto_mode_state == AutoModeState.ERROR:
            return False

        return True

    async def _take_state_snapshot(self, description: str) -> StateSnapshot:
        """Take a snapshot of current auto-mode state"""
        try:
            latest_output = ""
            if self.current_context and self.current_context.previous_outputs:
                latest_output = self.current_context.previous_outputs[-1]

            # Note: Analysis results would be processed here if needed
            # Currently using basic snapshot without detailed analysis integration

            snapshot = StateSnapshot(
                timestamp=datetime.now(),
                session_id=self.active_session_id or "",
                auto_mode_state=self.auto_mode_state,
                current_iteration=self.current_iteration,
                user_objective=self.current_context.user_objective if self.current_context else "",
                working_directory=self.current_context.working_directory
                if self.current_context
                else "",
                latest_claude_output=latest_output,
                latest_analysis=None,  # Simplified for now
                pending_prompts=[],
                error_count=self.error_count,
                metadata={"description": description},
            )

            self.state_snapshots.append(snapshot)

            # Persist if enabled
            if self.config.persistence_enabled:
                await self._persist_state_snapshot(snapshot)

            return snapshot

        except Exception as e:
            logger.error(f"Failed to take state snapshot: {e}")
            raise

    async def _persist_state_snapshot(self, snapshot: StateSnapshot) -> None:
        """Persist state snapshot to disk"""
        try:
            snapshot_file = Path(f".claude/runtime/auto_mode/{snapshot.session_id}_snapshots.jsonl")

            # Convert to serializable format
            snapshot_data = asdict(snapshot)
            snapshot_data["timestamp"] = snapshot.timestamp.isoformat()
            snapshot_data["auto_mode_state"] = snapshot.auto_mode_state.value

            # Append to JSONL file
            with open(snapshot_file, "a") as f:
                f.write(json.dumps(snapshot_data) + "\n")

        except Exception as e:
            logger.error(f"Failed to persist snapshot: {e}")

    async def _transition_state(self, new_state: AutoModeState) -> None:
        """Transition to a new auto-mode state"""
        old_state = self.auto_mode_state
        self.auto_mode_state = new_state

        # Take snapshot of state change
        snapshot = await self._take_state_snapshot(
            f"State transition: {old_state.value} -> {new_state.value}"
        )

        # Notify callbacks
        for callback in self.state_change_callbacks:
            try:
                callback(new_state, snapshot)
            except Exception as e:
                logger.error(f"State change callback error: {e}")

        logger.info(f"Auto-mode state transition: {old_state.value} -> {new_state.value}")

    async def _start_background_tasks(self) -> None:
        """Start background tasks for state management"""
        # State synchronization task
        sync_task = asyncio.create_task(self._state_sync_loop())
        self._background_tasks.append(sync_task)

        # Session cleanup task
        cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._background_tasks.append(cleanup_task)

    async def _state_sync_loop(self) -> None:
        """Background loop for state synchronization"""
        while not self._shutdown_event.is_set():
            try:
                if self.active_session_id:
                    # Sync with session manager
                    session_state = await self.session_manager.get_session(self.active_session_id)
                    if session_state and session_state.status == "expired":
                        await self._transition_state(AutoModeState.ERROR)

                await asyncio.sleep(self.config.state_sync_interval_seconds)

            except Exception as e:
                logger.error(f"State sync error: {e}")
                await asyncio.sleep(self.config.state_sync_interval_seconds)

    async def _cleanup_loop(self) -> None:
        """Background loop for cleanup tasks"""
        while not self._shutdown_event.is_set():
            try:
                # Cleanup expired sessions
                await self.session_manager.cleanup_expired_sessions()

                # Cleanup old snapshots (keep last 100)
                if len(self.state_snapshots) > 100:
                    self.state_snapshots = self.state_snapshots[-100:]

                await asyncio.sleep(300)  # Run every 5 minutes

            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                await asyncio.sleep(300)

    async def pause_auto_mode(self) -> None:
        """Pause auto-mode operation"""
        await self._transition_state(AutoModeState.PAUSED)

    async def resume_auto_mode(self) -> None:
        """Resume auto-mode operation"""
        await self._transition_state(AutoModeState.ACTIVE)

    async def stop_auto_mode(self) -> None:
        """Stop auto-mode operation and cleanup"""
        await self._transition_state(AutoModeState.STOPPED)

        # Signal shutdown
        self._shutdown_event.set()

        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()

        # Close session if active
        if self.active_session_id:
            await self.session_manager.close_session(self.active_session_id)

        logger.info("Auto-mode stopped")

    def add_state_change_callback(
        self, callback: Callable[[AutoModeState, StateSnapshot], None]
    ) -> None:
        """Add callback for state changes"""
        self.state_change_callbacks.append(callback)

    def add_milestone_callback(self, callback: Callable[[ProgressMilestone], None]) -> None:
        """Add callback for progress milestones"""
        self.milestone_callbacks.append(callback)

    def get_current_state(self) -> Dict[str, Any]:
        """Get current auto-mode state"""
        return {
            "state": self.auto_mode_state.value,
            "iteration": self.current_iteration,
            "error_count": self.error_count,
            "session_id": self.active_session_id,
            "snapshots_count": len(self.state_snapshots),
            "milestones_count": len(self.progress_milestones),
        }

    def get_progress_summary(self) -> Dict[str, Any]:
        """Get summary of auto-mode progress"""
        if not self.progress_milestones:
            return {"milestones": 0, "progress_percentage": 0.0}

        latest_milestone = self.progress_milestones[-1]
        progress_percentage = (self.current_iteration / self.config.max_iterations) * 100

        return {
            "milestones": len(self.progress_milestones),
            "progress_percentage": progress_percentage,
            "latest_milestone": asdict(latest_milestone),
            "average_confidence": sum(m.confidence for m in self.progress_milestones)
            / len(self.progress_milestones),
        }

    @staticmethod
    def validate_config_dict(config_dict: Dict[str, Any]) -> AutoModeConfig:
        """Validate and create config from dictionary"""
        try:
            return AutoModeConfig(**config_dict)
        except TypeError as e:
            raise ValueError(f"Invalid configuration parameters: {e}")
        except ValueError as e:
            raise ValueError(f"Configuration validation failed: {e}")

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update configuration with validation"""
        # Validate new config (validation logic would be applied here)
        # Note: validated_config = self.validate_config_dict({**asdict(self.config), **new_config})

        # Apply updates
        for key, value in new_config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                logger.warning(f"Unknown configuration parameter: {key}")

        logger.info(f"Configuration updated: {new_config}")
