"""
Auto-Mode Slash Command Implementation

Provides the /amplihack:auto-mode command for persistent analysis and  # noqa
autonomous progression through objectives using Claude Agent SDK.

# noqa: print - CLI/slash command code uses print for output
# noqa - "amplihack" is the project name, not a development artifact
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from amplihack.sdk import AutoModeConfig, AutoModeOrchestrator, StateIntegrationError


class AutoModeCommand:
    """Implementation of the /amplihack:auto-mode slash command"""

    def __init__(self):
        self.orchestrator: Optional[AutoModeOrchestrator] = None
        self.active_session_id: Optional[str] = None

    def run_objective(self, objective: str, working_dir: str, max_iterations: int = 50) -> int:
        """
        Simplified auto-mode: Run an objective synchronously until completion.

        This is the streamlined interface for auto-mode that takes an objective
        and runs it to completion in the foreground.

        Args:
            objective: The objective to achieve
            working_dir: Working directory for the objective
            max_iterations: Maximum iterations before stopping

        Returns:
            Exit code (0 for success, 1 for error)
        """
        return asyncio.run(self._run_objective_async(objective, working_dir, max_iterations))

    async def _run_objective_async(
        self, objective: str, working_dir: str, max_iterations: int
    ) -> int:
        """
        Async implementation of run_objective.

        Runs the objective synchronously in a loop until:
        - Objective is achieved (confidence >= threshold)
        - Max iterations reached
        - User interrupts (Ctrl+C)
        - Unrecoverable error occurs
        """
        try:
            # Create orchestrator
            config = AutoModeConfig(
                max_iterations=max_iterations,
                persistence_enabled=False,  # Simplified: no persistence for synchronous mode
                auto_progression_enabled=True,  # Core feature: automatic progression
            )
            self.orchestrator = AutoModeOrchestrator(config)

            # Start session
            print("📋 Starting auto-mode session...")
            session_id = await self.orchestrator.start_auto_mode_session(objective, working_dir)
            self.active_session_id = session_id
            print(f"✓ Session started: {session_id}\n")

            iteration = 0
            while iteration < max_iterations:
                iteration += 1
                print(f"\n🔄 Iteration {iteration}/{max_iterations}")
                print("=" * 60)

                # Get current state
                current_state = self.orchestrator.get_current_state()

                # Check if we should continue
                if not current_state.get("should_continue", True):
                    print("\n✅ Objective achieved!")
                    print(f"Final confidence: {current_state.get('confidence', 0.0):.2f}")
                    return 0

                # Generate and execute next action
                progress = self.orchestrator.get_progress_summary()
                print(f"Progress: {progress.get('progress_percentage', 0)}%")
                print(f"Confidence: {current_state.get('confidence', 0.0):.2f}")

                # In a real implementation, this would:
                # 1. Generate next prompt from AI analysis
                # 2. Execute it via Claude SDK
                # 3. Process the output
                # 4. Loop

                # For now, print status
                print("\n⚠️  Note: Full auto-mode implementation requires Claude SDK integration")
                print("This simplified version shows the structure but needs SDK connection.")
                break

            if iteration >= max_iterations:
                print(f"\n⏱️  Max iterations ({max_iterations}) reached")
                print("Consider increasing --max-iterations or refining the objective")
                return 1

            return 0

        except KeyboardInterrupt:
            print("\n\n⏹️  Stopped by user")
            return 0
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback

            traceback.print_exc()
            return 1
        finally:
            # Cleanup
            if self.orchestrator:
                try:
                    await self.orchestrator.stop_auto_mode()
                except Exception:
                    # Ignore cleanup errors
                    pass
                self.orchestrator = None
                self.active_session_id = None

    async def execute(self, args: List[str]) -> Dict[str, Any]:
        """
        Execute auto-mode command with given arguments.

        Args:
            args: Command line arguments

        Returns:
            Command execution result
        """
        if not args:
            return self._show_help()

        command = args[0].lower()

        try:
            if command == "start":
                return await self._start_command(args[1:])
            if command == "process":
                return await self._process_command(args[1:])
            if command == "status":
                return await self._status_command(args[1:])
            if command == "pause":
                return await self._pause_command(args[1:])
            if command == "resume":
                return await self._resume_command(args[1:])
            if command == "stop":
                return await self._stop_command(args[1:])
            if command == "help":
                return self._show_help()
            return {
                "success": False,
                "error": f"Unknown command: {command}",
                "help": "Use '/amplihack:auto-mode help' for usage information",
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Command execution failed: {e!s}",
                "type": type(e).__name__,
            }

    async def _start_command(self, args: List[str]) -> Dict[str, Any]:
        """Start a new auto-mode session"""
        if not args:
            return {
                "success": False,
                "error": "Objective is required",
                "usage": '/amplihack:auto-mode start "Objective description"',
            }

        # Parse arguments
        objective = args[0]
        working_dir = os.getcwd()
        max_iterations = 50

        # Parse optional arguments
        i = 1
        while i < len(args):
            if args[i] == "--working-dir" and i + 1 < len(args):
                working_dir = args[i + 1]
                i += 2
            elif args[i] == "--max-iterations" and i + 1 < len(args):
                max_iterations = int(args[i + 1])
                i += 2
            else:
                i += 1

        try:
            # Create orchestrator if not exists
            if not self.orchestrator:
                config = AutoModeConfig(
                    max_iterations=max_iterations,
                    persistence_enabled=True,
                    auto_progression_enabled=True,
                )
                self.orchestrator = AutoModeOrchestrator(config)

            # Start session
            session_id = await self.orchestrator.start_auto_mode_session(objective, working_dir)
            self.active_session_id = session_id

            return {
                "success": True,
                "session_id": session_id,
                "objective": objective,
                "working_directory": working_dir,
                "max_iterations": max_iterations,
                "state": "active",
                "message": f"Auto-mode session started for: {objective[:60]}...",
            }

        except StateIntegrationError as e:
            return {
                "success": False,
                "error": f"Failed to start session: {e!s}",
                "type": "StateIntegrationError",
            }

    async def _process_command(self, args: List[str]) -> Dict[str, Any]:
        """Process Claude Code output through auto-mode analysis"""
        if not args:
            return {
                "success": False,
                "error": "Claude output is required",
                "usage": '/amplihack:auto-mode process "Claude output text"',
            }

        if not self.orchestrator or not self.active_session_id:
            return {
                "success": False,
                "error": "No active auto-mode session. Start one with 'auto-mode start'",
                "suggestion": "Use '/amplihack:auto-mode start \"Your objective\"' first",
            }

        claude_output = args[0]

        # Parse optional session ID (currently not used)
        i = 1
        while i < len(args):
            if args[i] == "--session-id" and i + 1 < len(args):
                # Skip session-id argument for now (not used in current implementation)
                i += 2
            else:
                i += 1

        try:
            # Process output
            result = await self.orchestrator.process_claude_output(
                claude_output, {"processed_at": datetime.now().isoformat()}
            )

            # Format response
            response = {
                "success": True,
                "session_id": self.active_session_id,
                "iteration": result["iteration"],
                "analysis": {
                    "confidence": result["confidence"],
                    "findings": result["analysis"]["findings"][:3],  # Top 3 findings
                    "quality_score": result["analysis"]["quality_score"],
                    "ai_reasoning": result["analysis"]["ai_reasoning"][:200]
                    + "...",  # Truncate for display
                },
                "recommendations": result["analysis"]["recommendations"][
                    :3
                ],  # Top 3 recommendations
                "should_continue": result["should_continue"],
                "state": result["state"],
            }

            # Add next action if available
            if result.get("next_action"):
                response["next_prompt"] = result["next_action"]
                response["message"] = "Analysis complete. Next prompt generated."
            else:
                response["message"] = "Analysis complete. Manual intervention may be needed."

            return response

        except StateIntegrationError as e:
            return {
                "success": False,
                "error": f"Processing failed: {e!s}",
                "type": "StateIntegrationError",
            }

    async def _status_command(self, args: List[str]) -> Dict[str, Any]:
        """Get current auto-mode session status"""
        if not self.orchestrator:
            return {
                "success": False,
                "error": "No auto-mode session active",
                "suggestion": "Start a session with '/amplihack:auto-mode start'",
            }

        try:
            current_state = self.orchestrator.get_current_state()
            progress_summary = self.orchestrator.get_progress_summary()

            # Get session stats
            session_stats = self.orchestrator.session_manager.get_session_stats()
            analysis_stats = self.orchestrator.analysis_engine.get_analysis_stats()

            return {
                "success": True,
                "session": {
                    "id": current_state["session_id"],
                    "state": current_state["state"],
                    "iteration": current_state["iteration"],
                    "error_count": current_state["error_count"],
                },
                "progress": {
                    "milestones": progress_summary["milestones"],
                    "progress_percentage": progress_summary["progress_percentage"],
                    "average_confidence": progress_summary.get("average_confidence", 0.0),
                },
                "statistics": {
                    "total_sessions": session_stats["total_sessions"],
                    "active_sessions": session_stats["active_sessions"],
                    "total_analyses": analysis_stats["total_analyses"],
                    "cache_hit_rate": analysis_stats.get("cache_hit_rate", 0.0),
                },
                "context": {
                    "objective": self.orchestrator.current_context.user_objective
                    if self.orchestrator.current_context
                    else "Unknown",
                    "working_directory": self.orchestrator.current_context.working_directory
                    if self.orchestrator.current_context
                    else "Unknown",
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Status check failed: {e!s}",
                "type": type(e).__name__,
            }

    async def _pause_command(self, args: List[str]) -> Dict[str, Any]:
        """Pause auto-mode session"""
        if not self.orchestrator:
            return {"success": False, "error": "No auto-mode session to pause"}

        try:
            await self.orchestrator.pause_auto_mode()
            return {"success": True, "message": "Auto-mode session paused", "state": "paused"}

        except Exception as e:
            return {"success": False, "error": f"Failed to pause: {e!s}"}

    async def _resume_command(self, args: List[str]) -> Dict[str, Any]:
        """Resume auto-mode session"""
        if not self.orchestrator:
            return {"success": False, "error": "No auto-mode session to resume"}

        try:
            await self.orchestrator.resume_auto_mode()
            return {"success": True, "message": "Auto-mode session resumed", "state": "active"}

        except Exception as e:
            return {"success": False, "error": f"Failed to resume: {e!s}"}

    async def _stop_command(self, args: List[str]) -> Dict[str, Any]:
        """Stop auto-mode session"""
        if not self.orchestrator:
            return {"success": False, "error": "No auto-mode session to stop"}

        try:
            # Get final stats before stopping
            current_state = self.orchestrator.get_current_state()
            progress_summary = self.orchestrator.get_progress_summary()

            await self.orchestrator.stop_auto_mode()

            # Clean up
            self.orchestrator = None
            self.active_session_id = None

            return {
                "success": True,
                "message": "Auto-mode session stopped",
                "final_stats": {
                    "total_iterations": current_state["iteration"],
                    "milestones_achieved": progress_summary["milestones"],
                    "final_progress": progress_summary["progress_percentage"],
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to stop: {e!s}"}

    def _show_help(self) -> Dict[str, Any]:
        """Show help information for auto-mode command"""
        return {
            "success": True,
            "command": "/amplihack:auto-mode",
            "description": "Persistent analysis and autonomous progression through objectives",
            "usage": {
                "start": {
                    "syntax": '/amplihack:auto-mode start "Objective" [--working-dir /path] [--max-iterations 50]',
                    "description": "Start new auto-mode session",
                    "example": '/amplihack:auto-mode start "Build a REST API with authentication"',
                },
                "process": {
                    "syntax": '/amplihack:auto-mode process "Claude output"',
                    "description": "Process Claude Code output through analysis",
                    "example": '/amplihack:auto-mode process "I\'ve implemented the user authentication system."',
                },
                "status": {
                    "syntax": "/amplihack:auto-mode status",
                    "description": "Check current session status and progress",
                },
                "pause": {
                    "syntax": "/amplihack:auto-mode pause",
                    "description": "Pause the current session",
                },
                "resume": {
                    "syntax": "/amplihack:auto-mode resume",
                    "description": "Resume a paused session",
                },
                "stop": {
                    "syntax": "/amplihack:auto-mode stop",
                    "description": "Stop and cleanup current session",
                },
            },
            "features": [
                "Real-time progress analysis using Claude Agent SDK",
                "Automatic next prompt generation",
                "Session persistence and recovery",
                "Quality assessment and recommendations",
                "Milestone tracking and progress monitoring",
                "Error handling and recovery mechanisms",
            ],
        }


# Command line interface for testing
async def main():
    """Test interface for auto-mode command"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python auto_mode.py <command> [args...]")
        return

    command = AutoModeCommand()
    result = await command.execute(sys.argv[1:])

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
