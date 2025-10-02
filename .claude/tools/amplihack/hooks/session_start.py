#!/usr/bin/env python3
"""
Claude Code hook for session start.
Uses unified HookProcessor for common functionality.
"""

# Import the base processor
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor

# Clean imports through package structure
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from context_preservation import ContextPreserver
    from paths import get_project_root

    from amplihack.utils.paths import FrameworkPathResolver
except ImportError:
    # Fallback imports for standalone execution
    get_project_root = None
    ContextPreserver = None
    FrameworkPathResolver = None


class SessionStartHook(HookProcessor):
    """Hook processor for session start events with performance optimizations."""

    def __init__(self):
        super().__init__("session_start")
        # Performance optimizations: caching for repeated operations
        self._env_cache = {}
        self._path_validation_cache = {}
        self._preferences_cache = None
        self._preferences_cache_time = 0

    def _validate_launch_directory(self, path: str) -> bool:
        """Validate launch directory path for security with caching.

        Args:
            path: Directory path to validate

        Returns:
            True if path is valid and accessible
        """
        # Use cached result if available
        if path in self._path_validation_cache:
            return self._path_validation_cache[path]

        try:
            # Early exit for empty or whitespace-only paths
            if not path or not path.strip():
                self._path_validation_cache[path] = False
                return False

            path_obj = Path(path.strip())

            # Quick existence check first (fastest operation)
            if not path_obj.exists():
                self._path_validation_cache[path] = False
                return False

            # Then check if it's a directory
            if not path_obj.is_dir():
                self._path_validation_cache[path] = False
                return False

            # Finally canonicalize (most expensive operation)
            path_obj.resolve()
            self._path_validation_cache[path] = True
            return True

        except (OSError, ValueError):
            self._path_validation_cache[path] = False
            return False

    def _add_launch_directory_context(self, launch_dir: str) -> str:
        """Add launch directory context with security validation.

        Args:
            launch_dir: UVX launch directory path

        Returns:
            Context message for launch directory
        """
        if not self._validate_launch_directory(launch_dir):
            self.log(f"Invalid or inaccessible launch directory: {launch_dir}", "WARNING")
            return ""

        # Use the user's exact message format
        context = (
            f"You are going to work on the project in the directory {launch_dir}. "
            f"Change working dir to there and all subsequent commands should be relative to that dir and repo."
        )

        self.log(f"Added UVX launch directory context: {launch_dir}")
        return context

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process session start event.

        Args:
            input_data: Input from Claude Code

        Returns:
            Additional context to add to the session
        """
        # Extract prompt
        prompt = input_data.get("prompt", "")
        self.log(f"Prompt length: {len(prompt)}")

        # Save metric
        self.save_metric("prompt_length", len(prompt))

        # Capture original request for substantial prompts
        original_request_context = ""
        original_request_captured = False

        # Optimized substantial request detection
        is_substantial = len(prompt) > 20
        if not is_substantial:
            # Use set for O(1) lookup instead of list iteration
            substantial_keywords = {
                "implement",
                "create",
                "build",
                "add",
                "fix",
                "update",
                "all",
                "every",
                "each",
                "complete",
                "comprehensive",
            }
            prompt_lower = prompt.lower()
            is_substantial = any(word in prompt_lower for word in substantial_keywords)

        if ContextPreserver and is_substantial:
            try:
                # Create context preserver with current session ID
                session_id = self.get_session_id()
                preserver = ContextPreserver(session_id)

                # Extract and save original request
                original_request = preserver.extract_original_request(prompt)

                # Verify and format context
                session_dir = self.project_root / ".claude" / "runtime" / "logs" / session_id
                original_request_captured = (session_dir / "ORIGINAL_REQUEST.md").exists()

                if original_request_captured:
                    self.log(
                        f"✅ Original request captured: {original_request.get('target', 'Unknown')}"
                    )
                    original_request_context = preserver.format_agent_context(original_request)
                else:
                    self.log("⚠️ Original request extraction failed", "WARNING")

                self.save_metric("original_request_captured", original_request_captured)

            except Exception as e:
                self.log(f"Failed to capture original request: {e}", "ERROR")
                self.save_metric("original_request_captured", False)

        # UVX staging if available
        try:
            from amplihack.utils.uvx_staging import is_uvx_deployment, stage_uvx_framework

            if is_uvx_deployment():
                staged = stage_uvx_framework()
                self.save_metric("uvx_staging_success", staged)
        except ImportError:
            pass

        # Optimized UVX launch directory check with caching
        uvx_launch_context = ""
        # Cache environment variable access for performance
        if "UVX_LAUNCH_DIRECTORY" not in self._env_cache:
            self._env_cache["UVX_LAUNCH_DIRECTORY"] = os.environ.get("UVX_LAUNCH_DIRECTORY")

        uvx_launch_dir = self._env_cache["UVX_LAUNCH_DIRECTORY"]
        if uvx_launch_dir:
            uvx_launch_context = self._add_launch_directory_context(uvx_launch_dir)
            self.save_metric("uvx_launch_directory_set", True)
        else:
            self.save_metric("uvx_launch_directory_set", False)

        # Build context if needed
        context_parts = []
        preference_enforcement = []

        # Add project context
        context_parts.append("## Project Context")
        context_parts.append("This is the Microsoft Hackathon 2025 Agentic Coding project.")
        context_parts.append("Focus on building AI-powered development tools.")

        # Check for recent discoveries
        discoveries_file = self.project_root / ".claude" / "context" / "DISCOVERIES.md"
        if discoveries_file.exists():
            context_parts.append("\n## Recent Learnings")
            context_parts.append("Check .claude/context/DISCOVERIES.md for recent insights.")

        # Simplified preference file resolution
        preferences_file = (
            FrameworkPathResolver.resolve_preferences_file()
            if FrameworkPathResolver
            else self.project_root / ".claude" / "context" / "USER_PREFERENCES.md"
        )

        # Optimized preferences reading with time-based caching
        prefs_content = None
        if preferences_file:
            try:
                # Check if file exists first (cheap operation)
                if preferences_file.exists():
                    # Get file modification time
                    mtime = preferences_file.stat().st_mtime

                    # Return cached content if file hasn't changed
                    if (
                        self._preferences_cache is not None
                        and mtime <= self._preferences_cache_time
                    ):
                        prefs_content = self._preferences_cache
                        self.log(f"Using cached preferences from: {preferences_file}")
                    else:
                        # Read and cache the content
                        with open(preferences_file, "r") as f:
                            prefs_content = f.read()
                        self._preferences_cache = prefs_content
                        self._preferences_cache_time = mtime
                        self.log(
                            f"Successfully read and cached preferences from: {preferences_file}"
                        )
            except (OSError, IOError) as e:
                self.log(f"Could not read preferences: {e}")

        if prefs_content:
            try:
                import re

                context_parts.append("\n## 🎯 Active User Preferences")

                # Extract key preferences
                key_prefs = [
                    "Communication Style",
                    "Verbosity",
                    "Collaboration Style",
                    "Priority Type",
                ]
                active_prefs = []

                for pref in key_prefs:
                    pattern = f"### {pref}\\s*\\n\\s*([^\\n]+)"
                    match = re.search(pattern, prefs_content)
                    if match and match.group(1).strip() not in ["", "(not set)"]:
                        value = match.group(1).strip()
                        active_prefs.append(f"• **{pref}**: {value}")
                        preference_enforcement.append(f"MUST use {value} {pref.lower()}")

                if active_prefs:
                    context_parts.extend(active_prefs)
                else:
                    context_parts.append("• Using default settings")

            except Exception as e:
                self.log(f"Could not process preferences: {e}")

        # Add workflow information
        context_parts.append("\n## 📝 Default Workflow")
        context_parts.append("The 13-step workflow is automatically followed by `/ultrathink`")

        workflow_file = (
            FrameworkPathResolver.resolve_workflow_file() if FrameworkPathResolver else None
        )
        if workflow_file:
            context_parts.append(f"• To view: Read {workflow_file}")
        else:
            context_parts.append("• To view: Use FrameworkPathResolver.resolve_workflow_file()")
        context_parts.append("• To customize: Edit the workflow file directly")
        context_parts.append(
            "• Steps: Requirements → Issue → Branch → Design → Implement → Review → Merge"
        )

        # Add verbosity instructions
        context_parts.append("\n## 🎤 Verbosity Mode")
        context_parts.append("• Current setting: balanced")
        context_parts.append("• To enable verbose: Use TodoWrite tool frequently")
        context_parts.append("• Claude adapts to your verbosity preference")

        # Build response
        output = {}
        if context_parts:
            # Create comprehensive startup context
            full_context = "\n".join(context_parts)

            # Build startup message
            startup_msg_parts = ["🚀 AmplifyHack Session Initialized", "━" * 40]

            if any("**" in p and ":" in p for p in context_parts):
                startup_msg_parts.append("🎯 Active preferences loaded and enforced")

            startup_msg_parts.extend(
                [
                    "",
                    "📝 Workflow: Use `/ultrathink` for the 13-step process",
                    "⚙️ Customize: Edit the workflow file",
                    "🎯 Preferences: Loaded from USER_PREFERENCES.md",
                    "",
                    "Type `/help` for available commands",
                ]
            )

            startup_message = "\n".join(startup_msg_parts)

            # Add UVX launch directory context at highest priority
            if uvx_launch_context:
                full_context = uvx_launch_context + "\n\n" + full_context

            # Add preference enforcement instructions to context
            if preference_enforcement:
                enforcement = (
                    "🎯 USER PREFERENCES (MANDATORY):\n"
                    + "\n".join(f"• {rule}" for rule in preference_enforcement)
                    + "\n\n"
                )
                full_context = enforcement + full_context

            # Add original request context to prevent requirement loss (highest priority)
            if original_request_context:
                full_context = original_request_context + "\n\n" + full_context

            output = {
                "additionalContext": full_context,
                "message": startup_message,
                "metadata": {
                    "source": "amplihack_session_start",
                    "timestamp": datetime.now().isoformat(),
                    "original_request_captured": original_request_captured,
                },
            }
            self.log(
                f"Session initialized - Original request: {'✅' if original_request_captured else '❌'}"
            )

        return output


def main():
    """Entry point for the session start hook."""
    hook = SessionStartHook()
    hook.run()


if __name__ == "__main__":
    main()
