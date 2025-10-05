"""
Auto-Mode Command Handler

Implements the /auto-mode slash command functionality for Claude Code integration.
Provides user interface for controlling and interacting with auto-mode features.
"""

import shlex
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .orchestrator import AutoModeOrchestrator, OrchestratorConfig


@dataclass
class CommandResult:
    """Result of a command execution"""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None


class AutoModeCommandHandler:
    """
    Handles /auto-mode slash command execution.
    """

    def __init__(self, orchestrator: Optional[AutoModeOrchestrator] = None):
        self.orchestrator = orchestrator
        self.command_history: List[Dict[str, Any]] = []

        # Configuration presets
        self.config_presets = {
            "default": OrchestratorConfig(),
            "aggressive_analysis": OrchestratorConfig(
                analysis_interval_seconds=15.0,
                min_quality_threshold=0.5,
                intervention_confidence_threshold=0.5,
            ),
            "minimal_intervention": OrchestratorConfig(
                analysis_interval_seconds=60.0,
                min_quality_threshold=0.3,
                intervention_confidence_threshold=0.9,
            ),
            "learning_mode": OrchestratorConfig(
                learning_mode_enabled=True, intervention_confidence_threshold=0.6
            ),
            "privacy_focused": OrchestratorConfig(
                background_analysis_enabled=False,
                learning_mode_enabled=False,
                detailed_logging=False,
            ),
        }

    async def handle_command(self, command_args: str, context: Dict[str, Any]) -> CommandResult:
        """
        Handle /auto-mode command execution.

        Args:
            command_args: Command arguments string
            context: Execution context (user_id, session_id, etc.)

        Returns:
            CommandResult: Result of command execution
        """
        try:
            # Parse command arguments
            args = self._parse_args(command_args)

            if not args:
                return CommandResult(
                    success=False,
                    message="Invalid command syntax. Use '/auto-mode help' for usage information.",
                    error_code="invalid_syntax",
                )

            action = args.get("action", "help")

            # Record command in history
            self._record_command(action, args, context)

            # Route to appropriate handler
            if action == "start":
                return await self._handle_start(args, context)
            elif action == "stop":
                return await self._handle_stop(args, context)
            elif action == "status":
                return await self._handle_status(args, context)
            elif action == "configure":
                return await self._handle_configure(args, context)
            elif action == "analyze":
                return await self._handle_analyze(args, context)
            elif action == "insights":
                return await self._handle_insights(args, context)
            elif action == "feedback":
                return await self._handle_feedback(args, context)
            elif action == "summary":
                return await self._handle_summary(args, context)
            elif action == "help":
                return await self._handle_help(args, context)
            else:
                return CommandResult(
                    success=False,
                    message=f"Unknown action '{action}'. Use '/auto-mode help' for available actions.",
                    error_code="unknown_action",
                )

        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Command execution failed: {str(e)}",
                error_code="execution_error",
            )

    def _parse_args(self, command_args: str) -> Optional[Dict[str, Any]]:
        """Parse command arguments using argparse-like logic"""
        try:
            # Split command args respecting quotes
            tokens = shlex.split(command_args) if command_args.strip() else []

            if not tokens:
                return {"action": "help"}

            args = {"action": tokens[0]}

            # Parse remaining arguments
            i = 1
            while i < len(tokens):
                token = tokens[i]

                if token.startswith("--"):
                    # Long option
                    option_name = token[2:]
                    if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                        # Option with value
                        args[option_name] = tokens[i + 1]
                        i += 2
                    else:
                        # Boolean option
                        args[option_name] = True
                        i += 1
                elif token.startswith("-"):
                    # Short option
                    option_name = token[1:]
                    if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                        args[option_name] = tokens[i + 1]
                        i += 2
                    else:
                        args[option_name] = True
                        i += 1
                else:
                    # Positional argument
                    if "positional" not in args:
                        args["positional"] = []
                    args["positional"].append(token)
                    i += 1

            return args

        except Exception as e:
            print(f"Failed to parse command args: {e}")
            return None

    async def _handle_start(self, args: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Handle 'start' action"""
        try:
            # Initialize orchestrator if needed
            if not self.orchestrator:
                config_name = args.get("config", "default")
                config = self.config_presets.get(config_name, self.config_presets["default"])
                self.orchestrator = AutoModeOrchestrator(config)

                initialized = await self.orchestrator.initialize()
                if not initialized:
                    return CommandResult(
                        success=False,
                        message="Failed to initialize auto-mode orchestrator",
                        error_code="initialization_failed",
                    )

            # Extract context information
            user_id = args.get("user-id") or context.get("user_id", "anonymous")
            conversation_context = context.get("conversation_context", {})

            # Start session
            session_id = await self.orchestrator.start_session(user_id, conversation_context)

            return CommandResult(
                success=True,
                message="Auto-mode session started successfully",
                data={
                    "session_id": session_id,
                    "user_id": user_id,
                    "config": args.get("config", "default"),
                    "status": "active",
                },
            )

        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to start auto-mode session: {str(e)}",
                error_code="start_failed",
            )

    async def _handle_stop(self, args: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Handle 'stop' action"""
        try:
            if not self.orchestrator:
                return CommandResult(
                    success=False, message="Auto-mode is not running", error_code="not_running"
                )

            session_id = args.get("session-id") or context.get("current_session_id")

            if not session_id:
                # Stop all sessions for user
                user_id = context.get("user_id", "anonymous")
                stopped_count = 0

                for sid, session_state in list(self.orchestrator.active_sessions.items()):
                    if session_state.user_id == user_id:
                        if await self.orchestrator.stop_session(sid):
                            stopped_count += 1

                if stopped_count == 0:
                    return CommandResult(
                        success=False,
                        message="No active auto-mode sessions found",
                        error_code="no_sessions",
                    )

                return CommandResult(
                    success=True,
                    message=f"Stopped {stopped_count} auto-mode session(s)",
                    data={"stopped_sessions": stopped_count},
                )

            else:
                # Stop specific session
                success = await self.orchestrator.stop_session(session_id)

                if success:
                    return CommandResult(
                        success=True,
                        message=f"Auto-mode session {session_id} stopped successfully",
                        data={"session_id": session_id},
                    )
                else:
                    return CommandResult(
                        success=False,
                        message=f"Failed to stop session {session_id}",
                        error_code="stop_failed",
                    )

        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to stop auto-mode: {str(e)}",
                error_code="stop_error",
            )

    async def _handle_status(self, args: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Handle 'status' action"""
        try:
            if not self.orchestrator:
                return CommandResult(
                    success=True,
                    message="Auto-mode is not running",
                    data={
                        "status": "inactive",
                        "active_sessions": 0,
                        "sdk_connection": "disconnected",
                    },
                )

            detailed = args.get("detailed", False)
            session_id = args.get("session-id")

            if session_id:
                # Status for specific session
                session_status = await self.orchestrator.get_session_status(session_id)

                if not session_status:
                    return CommandResult(
                        success=False,
                        message=f"Session {session_id} not found",
                        error_code="session_not_found",
                    )

                return CommandResult(
                    success=True, message=f"Status for session {session_id}", data=session_status
                )

            else:
                # General status
                metrics = self.orchestrator.get_metrics()
                sdk_status = self.orchestrator.sdk_client.get_connection_status()

                status_data = {
                    "status": self.orchestrator.state.value,
                    "active_sessions": len(self.orchestrator.active_sessions),
                    "total_sessions": metrics["total_sessions"],
                    "analysis_cycles": metrics["total_analysis_cycles"],
                    "interventions": metrics["total_interventions"],
                    "average_quality": metrics["average_quality_score"],
                    "uptime": f"{metrics['uptime_seconds']:.0f}s",
                    "sdk_connection": sdk_status["connection_state"],
                }

                if detailed:
                    status_data.update(
                        {
                            "detailed_metrics": metrics,
                            "sdk_status": sdk_status,
                            "active_session_details": [
                                await self.orchestrator.get_session_status(sid)
                                for sid in self.orchestrator.active_sessions.keys()
                            ],
                        }
                    )

                return CommandResult(success=True, message="Auto-mode status", data=status_data)

        except Exception as e:
            return CommandResult(
                success=False, message=f"Failed to get status: {str(e)}", error_code="status_error"
            )

    async def _handle_configure(
        self, args: Dict[str, Any], context: Dict[str, Any]
    ) -> CommandResult:
        """Handle 'configure' action"""
        try:
            if not self.orchestrator:
                return CommandResult(
                    success=False,
                    message="Auto-mode is not running. Start auto-mode first.",
                    error_code="not_running",
                )

            setting = args.get("positional", [None])[0] if args.get("positional") else None
            value = (
                args.get("positional", [None, None])[1]
                if len(args.get("positional", [])) > 1
                else None
            )

            if not setting:
                # Show current configuration
                config = self.orchestrator.config
                config_data = {
                    "analysis_frequency": "adaptive",  # Based on analysis_interval_seconds
                    "intervention_threshold": config.intervention_confidence_threshold,
                    "background_mode": config.background_analysis_enabled,
                    "learning_mode": config.learning_mode_enabled,
                    "privacy_level": "balanced",  # Simplified for display
                }

                return CommandResult(
                    success=True, message="Current auto-mode configuration", data=config_data
                )

            if not value:
                return CommandResult(
                    success=False,
                    message=f"No value provided for setting '{setting}'",
                    error_code="missing_value",
                )

            # Apply configuration change
            success = await self._apply_configuration(setting, value)

            if success:
                return CommandResult(
                    success=True,
                    message=f"Configuration updated: {setting} = {value}",
                    data={setting: value},
                )
            else:
                return CommandResult(
                    success=False,
                    message=f"Failed to update configuration: {setting}",
                    error_code="config_failed",
                )

        except Exception as e:
            return CommandResult(
                success=False, message=f"Configuration error: {str(e)}", error_code="config_error"
            )

    async def _handle_analyze(self, args: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Handle 'analyze' action"""
        try:
            if not self.orchestrator:
                return CommandResult(
                    success=False,
                    message="Auto-mode is not running. Start auto-mode first.",
                    error_code="not_running",
                )

            # args.get("type", "comprehensive")  # Future use for analysis type
            # args.get("scope", "current")  # Future use for scope
            output_format = args.get("output", "summary")

            # Get current session
            user_id = context.get("user_id", "anonymous")
            current_session = None

            for session_state in self.orchestrator.active_sessions.values():
                if session_state.user_id == user_id:
                    current_session = session_state
                    break

            if not current_session:
                return CommandResult(
                    success=False,
                    message="No active auto-mode session found",
                    error_code="no_session",
                )

            # Perform analysis
            analysis = await self.orchestrator.analysis_engine.analyze_conversation(
                conversation_context=current_session.conversation_context,
                session_history=current_session.analysis_history,
            )

            # Format output based on requested format
            if output_format == "json":
                return CommandResult(
                    success=True,
                    message="Conversation analysis completed",
                    data=self._format_analysis_json(analysis),
                )
            elif output_format == "detailed":
                return CommandResult(success=True, message=self._format_analysis_detailed(analysis))
            else:  # summary
                return CommandResult(success=True, message=self._format_analysis_summary(analysis))

        except Exception as e:
            return CommandResult(
                success=False, message=f"Analysis failed: {str(e)}", error_code="analysis_error"
            )

    async def _handle_insights(
        self, args: Dict[str, Any], context: Dict[str, Any]
    ) -> CommandResult:
        """Handle 'insights' action"""
        # Implementation for insights viewing
        return CommandResult(
            success=True, message="Insights feature coming soon", data={"insights": []}
        )

    async def _handle_feedback(
        self, args: Dict[str, Any], context: Dict[str, Any]
    ) -> CommandResult:
        """Handle 'feedback' action"""
        # Implementation for feedback collection
        return CommandResult(
            success=True, message="Thank you for your feedback", data={"feedback_recorded": True}
        )

    async def _handle_summary(self, args: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Handle 'summary' action"""
        # Implementation for session summary generation
        return CommandResult(
            success=True,
            message="Session summary feature coming soon",
            data={"summary": "placeholder"},
        )

    async def _handle_help(self, args: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Handle 'help' action"""
        command = args.get("positional", [None])[0] if args.get("positional") else None

        if command:
            help_text = self._get_command_help(command)
        else:
            help_text = self._get_general_help()

        return CommandResult(success=True, message=help_text)

    async def _apply_configuration(self, setting: str, value: str) -> bool:
        """Apply a configuration change"""
        try:
            if setting == "analysis_frequency":
                if value == "low":
                    self.orchestrator.config.analysis_interval_seconds = 60.0
                elif value == "normal":
                    self.orchestrator.config.analysis_interval_seconds = 30.0
                elif value == "high":
                    self.orchestrator.config.analysis_interval_seconds = 15.0
                elif value == "adaptive":
                    # Keep current adaptive behavior
                    pass
                else:
                    return False

            elif setting == "intervention_threshold":
                threshold = float(value)
                if 0.0 <= threshold <= 1.0:
                    self.orchestrator.config.intervention_confidence_threshold = threshold
                else:
                    return False

            elif setting == "background_mode":
                enabled = value.lower() in ("true", "1", "yes", "on")
                self.orchestrator.config.background_analysis_enabled = enabled

            elif setting == "learning_mode":
                enabled = value.lower() in ("true", "1", "yes", "on")
                self.orchestrator.config.learning_mode_enabled = enabled

            else:
                return False

            return True

        except (ValueError, AttributeError):
            return False

    def _format_analysis_json(self, analysis) -> Dict[str, Any]:
        """Format analysis results as JSON"""
        return {
            "timestamp": analysis.timestamp,
            "quality_score": analysis.quality_score,
            "conversation_length": analysis.conversation_length,
            "quality_dimensions": [
                {
                    "dimension": dim.dimension,
                    "score": dim.score,
                    "suggestions": dim.improvement_suggestions,
                }
                for dim in analysis.quality_dimensions
            ],
            "patterns": [
                {
                    "type": pattern.pattern_type,
                    "description": pattern.description,
                    "confidence": pattern.confidence,
                }
                for pattern in analysis.identified_patterns
            ],
            "opportunities": analysis.improvement_opportunities,
            "satisfaction": analysis.satisfaction_signals,
        }

    def _format_analysis_detailed(self, analysis) -> str:
        """Format analysis results as detailed text"""
        lines = [
            "📊 **Detailed Conversation Analysis**",
            f"Quality Score: {analysis.quality_score:.2f}/1.0",
            f"Messages: {analysis.conversation_length} total",
            "",
            "**Quality Dimensions:**",
        ]

        for dim in analysis.quality_dimensions:
            lines.append(f"• {dim.dimension.title()}: {dim.score:.2f}")
            for suggestion in dim.improvement_suggestions:
                lines.append(f"  → {suggestion}")

        if analysis.identified_patterns:
            lines.append("\n**Detected Patterns:**")
            for pattern in analysis.identified_patterns:
                lines.append(f"• {pattern.pattern_type}: {pattern.description}")

        if analysis.improvement_opportunities:
            lines.append("\n**Improvement Opportunities:**")
            for opp in analysis.improvement_opportunities:
                lines.append(f"• {opp.get('area', 'General')}: {opp.get('description', '')}")

        return "\n".join(lines)

    def _format_analysis_summary(self, analysis) -> str:
        """Format analysis results as brief summary"""
        quality_emoji = (
            "🟢"
            if analysis.quality_score >= 0.7
            else "🟡"
            if analysis.quality_score >= 0.5
            else "🔴"
        )

        summary = f"{quality_emoji} Conversation Quality: {analysis.quality_score:.2f}/1.0"

        if analysis.improvement_opportunities:
            top_opportunity = analysis.improvement_opportunities[0]
            summary += f"\n💡 Top Suggestion: {top_opportunity.get('description', 'No specific suggestion')}"

        return summary

    def _get_general_help(self) -> str:
        """Get general help text"""
        return """
🤖 **Auto-Mode Help**

Available actions:
• `start` - Start auto-mode session
• `stop` - Stop auto-mode session
• `status` - Check auto-mode status
• `configure` - Configure settings
• `analyze` - Request manual analysis
• `insights` - View learned insights
• `feedback` - Provide feedback
• `summary` - Generate session summary
• `help [command]` - Show help for specific command

Use `/auto-mode help [action]` for detailed help on specific actions.
"""

    def _get_command_help(self, command: str) -> str:
        """Get help text for specific command"""
        help_texts = {
            "start": """
**Auto-Mode Start**
`/auto-mode start [--config CONFIG] [--user-id USER_ID]`

Start a new auto-mode session with persistent analysis.

Options:
• `--config`: Configuration preset (default, aggressive_analysis, minimal_intervention, learning_mode, privacy_focused)
• `--user-id`: Specify user identifier

Examples:
• `/auto-mode start`
• `/auto-mode start --config learning_mode`
""",
            "status": """
**Auto-Mode Status**
`/auto-mode status [--detailed] [--session-id ID]`

Show current auto-mode status and metrics.

Options:
• `--detailed`: Show detailed metrics and analysis
• `--session-id`: Show status for specific session

Examples:
• `/auto-mode status`
• `/auto-mode status --detailed`
""",
            "configure": """
**Auto-Mode Configure**
`/auto-mode configure [SETTING] [VALUE]`

Configure auto-mode behavior and preferences.

Settings:
• `analysis_frequency`: low, normal, high, adaptive
• `intervention_threshold`: 0.0 - 1.0
• `background_mode`: true, false
• `learning_mode`: true, false

Examples:
• `/auto-mode configure` (show current config)
• `/auto-mode configure analysis_frequency adaptive`
• `/auto-mode configure intervention_threshold 0.8`
""",
        }

        return help_texts.get(command, f"No help available for '{command}'")

    def _record_command(self, action: str, args: Dict[str, Any], context: Dict[str, Any]):
        """Record command in history for analytics"""
        self.command_history.append(
            {
                "timestamp": time.time(),
                "action": action,
                "args": args,
                "user_id": context.get("user_id", "anonymous"),
                "session_id": context.get("current_session_id"),
            }
        )
