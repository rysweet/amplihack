"""
XPIA Claude Code Hook Integration

Provides hook adapters for integrating XPIA defense with Claude Code's
PreToolUse and PostToolUse hook system.
"""

import asyncio
import json
import logging
import os

# Import from specifications
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from .xpia_defender import WebFetchXPIADefender

sys.path.append("/Users/ryan/src/hackathon/MicrosoftHackathon2025-AgenticCoding-xpia-133/Specs")
from xpia_defense_interface import (
    RiskLevel,
    ValidationResult,
    create_validation_context,
    get_threat_summary,
)

logger = logging.getLogger(__name__)


class XPIAHookAdapter:
    """
    Adapter for integrating XPIA defense with Claude Code hooks

    This class provides the interface between Claude Code's hook system
    and the XPIA defense implementation.
    """

    def __init__(self, defender: Optional[WebFetchXPIADefender] = None):
        """Initialize hook adapter with defender instance"""
        self.defender = defender or WebFetchXPIADefender()
        self.enabled = os.getenv("XPIA_ENABLED", "true").lower() != "false"
        self.block_on_high_risk = os.getenv("XPIA_BLOCK_HIGH_RISK", "true").lower() == "true"
        self.verbose_feedback = os.getenv("XPIA_VERBOSE_FEEDBACK", "false").lower() == "true"

        logger.info(f"XPIA Hook Adapter initialized (enabled={self.enabled})")

    async def pre_tool_use(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        PreToolUse hook for Claude Code

        Intercepts tool calls before execution to validate security.

        Args:
            context: Hook context containing tool information
                - tool_name: Name of the tool being called
                - parameters: Tool parameters
                - session_id: Current session ID
                - timestamp: Call timestamp

        Returns:
            Hook response with validation results
                - allow: Whether to proceed with tool execution
                - message: User-facing message if blocked
                - metadata: Additional validation details
        """
        if not self.enabled:
            return {"allow": True, "message": None, "metadata": {"xpia_enabled": False}}

        tool_name = context.get("tool_name", "")
        parameters = context.get("parameters", {})

        # Handle WebFetch tool specifically
        if tool_name == "WebFetch":
            return await self._handle_webfetch_validation(parameters, context)

        # Handle Bash tool
        if tool_name == "Bash":
            return await self._handle_bash_validation(parameters, context)

        # Handle other tools with general validation
        return await self._handle_general_validation(tool_name, parameters, context)

    async def post_tool_use(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        PostToolUse hook for Claude Code

        Analyzes tool execution results for security issues.

        Args:
            context: Hook context with execution results
                - tool_name: Name of the tool that was called
                - parameters: Original parameters
                - result: Tool execution result
                - error: Any error that occurred

        Returns:
            Hook response with post-execution analysis
        """
        if not self.enabled:
            return {"processed": True}

        tool_name = context.get("tool_name", "")
        result = context.get("result", "")

        # Check result for potential security issues
        if result and isinstance(result, str):
            validation_context = create_validation_context(
                source="tool_result", session_id=context.get("session_id")
            )

            # Use asyncio to run async validation
            validation = await self.defender.validate_content(
                result, ContentType.DATA, validation_context
            )

            if validation.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                logger.warning(
                    f"High risk content detected in {tool_name} result: {get_threat_summary(validation)}"
                )

                return {
                    "processed": True,
                    "warning": f"Security risk detected in tool output: {get_threat_summary(validation)}",
                    "metadata": {
                        "risk_level": validation.risk_level.value,
                        "threats": len(validation.threats),
                    },
                }

        return {"processed": True}

    async def _handle_webfetch_validation(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle WebFetch tool validation"""
        url = parameters.get("url", "")
        prompt = parameters.get("prompt", "")

        if not url or not prompt:
            return {
                "allow": True,
                "message": None,
                "metadata": {"validation_skipped": "missing_parameters"},
            }

        # Create validation context
        validation_context = create_validation_context(
            source="webfetch_hook",
            session_id=context.get("session_id"),
            agent_id=context.get("agent_id"),
        )

        # Validate WebFetch request
        validation = await self.defender.validate_webfetch_request(url, prompt, validation_context)

        # Determine if we should block
        should_block = validation.should_block or (
            self.block_on_high_risk and validation.risk_level == RiskLevel.HIGH
        )

        if should_block:
            message = self._create_block_message(validation, "WebFetch")
            logger.warning(f"Blocked WebFetch request to {url}: {get_threat_summary(validation)}")

            return {
                "allow": False,
                "message": message,
                "metadata": {
                    "risk_level": validation.risk_level.value,
                    "threats": [
                        {
                            "type": t.threat_type.value,
                            "severity": t.severity.value,
                            "description": t.description,
                        }
                        for t in validation.threats
                    ],
                    "url": url,
                },
            }

        # Allow but with warnings if medium risk
        if validation.risk_level == RiskLevel.MEDIUM:
            logger.info(f"Allowing WebFetch with warnings for {url}")

            return {
                "allow": True,
                "message": None,
                "warning": f"Proceeding with caution: {validation.recommendations[0] if validation.recommendations else 'Potential security concerns detected'}",
                "metadata": {
                    "risk_level": validation.risk_level.value,
                    "threats": len(validation.threats),
                },
            }

        # Allow clean requests
        return {
            "allow": True,
            "message": None,
            "metadata": {"risk_level": validation.risk_level.value, "validation": "passed"},
        }

    async def _handle_bash_validation(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle Bash tool validation"""
        command = parameters.get("command", "")

        if not command:
            return {
                "allow": True,
                "message": None,
                "metadata": {"validation_skipped": "no_command"},
            }

        # Create validation context
        validation_context = create_validation_context(
            source="bash_hook",
            session_id=context.get("session_id"),
            working_directory=context.get("working_directory"),
        )

        # Validate bash command
        validation = await self.defender.validate_bash_command(command, context=validation_context)

        # Determine if we should block
        should_block = validation.should_block or (
            self.block_on_high_risk and validation.risk_level == RiskLevel.HIGH
        )

        if should_block:
            message = self._create_block_message(validation, "Bash")
            logger.warning(
                f"Blocked Bash command: {command[:100]}... - {get_threat_summary(validation)}"
            )

            return {
                "allow": False,
                "message": message,
                "metadata": {
                    "risk_level": validation.risk_level.value,
                    "threats": len(validation.threats),
                    "command_preview": command[:100],
                },
            }

        return {
            "allow": True,
            "message": None,
            "metadata": {"risk_level": validation.risk_level.value, "validation": "passed"},
        }

    async def _handle_general_validation(
        self, tool_name: str, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle validation for other tools"""
        # Convert parameters to string for validation
        content = json.dumps(parameters)

        # Skip validation for very short content
        if len(content) < 10:
            return {
                "allow": True,
                "message": None,
                "metadata": {"validation_skipped": "content_too_short"},
            }

        validation_context = create_validation_context(
            source=f"{tool_name}_hook", session_id=context.get("session_id")
        )

        from xpia_defense_interface import ContentType

        validation = await self.defender.validate_content(
            content, ContentType.DATA, validation_context
        )

        if validation.should_block:
            message = self._create_block_message(validation, tool_name)
            logger.warning(f"Blocked {tool_name} call: {get_threat_summary(validation)}")

            return {
                "allow": False,
                "message": message,
                "metadata": {
                    "risk_level": validation.risk_level.value,
                    "threats": len(validation.threats),
                },
            }

        return {
            "allow": True,
            "message": None,
            "metadata": {"risk_level": validation.risk_level.value, "validation": "passed"},
        }

    def _create_block_message(self, validation: ValidationResult, tool_name: str) -> str:
        """Create user-friendly block message"""
        if not self.verbose_feedback:
            return (
                f"🛡️ Security Alert: {tool_name} request blocked due to potential security risk.\n"
                f"Risk Level: {validation.risk_level.value}\n"
                f"Please review and modify your request."
            )

        # Verbose feedback with details
        message = f"🛡️ Security Alert: {tool_name} request blocked\n"
        message += f"Risk Level: {validation.risk_level.value}\n\n"

        if validation.threats:
            message += "Detected Threats:\n"
            for threat in validation.threats[:3]:  # Show top 3 threats
                message += f"  • {threat.description}\n"
                if threat.mitigation:
                    message += f"    Mitigation: {threat.mitigation}\n"

        if validation.recommendations:
            message += "\nRecommendations:\n"
            for rec in validation.recommendations[:2]:  # Show top 2 recommendations
                message += f"  • {rec}\n"

        return message


class ClaudeCodeXPIAHook:
    """
    Main hook class for Claude Code integration

    This class provides the actual hook functions that Claude Code will call.
    """

    def __init__(self):
        """Initialize Claude Code XPIA Hook"""
        self.adapter = XPIAHookAdapter()
        self.stats = {
            "total_validations": 0,
            "blocked_requests": 0,
            "high_risk_detections": 0,
            "start_time": datetime.now(),
        }

    def pre_tool_use(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        PreToolUse hook implementation

        This is the actual function that Claude Code will call.
        """
        # Run async validation in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(self.adapter.pre_tool_use(context))

            # Update stats
            self.stats["total_validations"] += 1
            if not result.get("allow", True):
                self.stats["blocked_requests"] += 1
            if result.get("metadata", {}).get("risk_level") in ["high", "critical"]:
                self.stats["high_risk_detections"] += 1

            return result

        except Exception as e:
            logger.error(f"Error in pre_tool_use hook: {e}")
            # On error, allow but log
            return {"allow": True, "message": None, "metadata": {"error": str(e)}}
        finally:
            loop.close()

    def post_tool_use(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        PostToolUse hook implementation

        This is the actual function that Claude Code will call.
        """
        # Run async validation in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(self.adapter.post_tool_use(context))

        except Exception as e:
            logger.error(f"Error in post_tool_use hook: {e}")
            return {"processed": True, "error": str(e)}
        finally:
            loop.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get hook statistics"""
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds()
        return {
            **self.stats,
            "uptime_seconds": uptime,
            "block_rate": (
                self.stats["blocked_requests"] / self.stats["total_validations"]
                if self.stats["total_validations"] > 0
                else 0
            ),
        }


# Hook registration helper
def register_xpia_hooks():
    """
    Register XPIA hooks with Claude Code

    This function should be called during initialization to register
    the XPIA defense hooks with Claude Code's hook system.
    """
    hook = ClaudeCodeXPIAHook()

    # The actual registration would depend on Claude Code's API
    # This is a placeholder implementation
    return {
        "pre_tool_use": hook.pre_tool_use,
        "post_tool_use": hook.post_tool_use,
        "get_stats": hook.get_stats,
    }


# Export the main hook instance for direct use
xpia_hook = ClaudeCodeXPIAHook()
