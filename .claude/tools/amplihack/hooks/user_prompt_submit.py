#!/usr/bin/env python3
"""
UserPromptSubmit hook - Inject user preferences on every message.
Ensures preferences persist across all conversation turns in REPL mode.
"""

import os
import re
import sys
from pathlib import Path
from typing import Any

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor

# Import path utilities
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from amplihack.utils.paths import FrameworkPathResolver
except ImportError:
    FrameworkPathResolver = None


class UserPromptSubmitHook(HookProcessor):
    """Hook processor for user prompt submit events."""

    def __init__(self):
        super().__init__("user_prompt_submit")
        self.strategy = None
        self._preferences_cache: dict[str, str] | None = None
        self._cache_timestamp: float | None = None
        self._amplihack_cache: str | None = None
        self._amplihack_cache_timestamp: tuple[float, float] | None = None

    def find_user_preferences(self) -> Path | None:
        """Find USER_PREFERENCES.md file using FrameworkPathResolver or fallback."""
        # Try FrameworkPathResolver first (handles UVX and installed packages)
        if FrameworkPathResolver:
            pref_file = FrameworkPathResolver.resolve_preferences_file()
            if pref_file and pref_file.exists():
                return pref_file

        # Fallback: Check in project root
        pref_file = self.project_root / ".claude" / "context" / "USER_PREFERENCES.md"
        if pref_file.exists():
            return pref_file

        # Try src/amplihack location
        pref_file = (
            self.project_root / "src" / "amplihack" / ".claude" / "context" / "USER_PREFERENCES.md"
        )
        if pref_file.exists():
            return pref_file

        return None

    def extract_preferences(self, content: str) -> dict[str, str]:
        """Extract preferences from USER_PREFERENCES.md content.

        Args:
            content: The raw content of USER_PREFERENCES.md

        Returns:
            Dictionary mapping preference names to values
        """
        preferences = {}

        # Key preferences to extract (aligned with session_start.py)
        key_prefs = [
            "Communication Style",
            "Verbosity",
            "Collaboration Style",
            "Update Frequency",
            "Priority Type",
            "Preferred Languages",
            "Coding Standards",
            "Workflow Preferences",
        ]

        # Extract each preference using regex pattern
        for pref_name in key_prefs:
            # Pattern: ### Preference Name\n\nvalue
            pattern = rf"### {re.escape(pref_name)}\s*\n\s*([^\n]+)"
            match = re.search(pattern, content)
            if match:
                value = match.group(1).strip()
                # Skip empty or placeholder values
                if value and value not in ["", "(not set)", "not set"]:
                    preferences[pref_name] = value

        # Extract learned patterns (brief mention only)
        if "## Learned Patterns" in content:
            learned_section = content.split("## Learned Patterns", 1)[1]
            # Check if there's content beyond just the comment
            if learned_section.strip() and "###" in learned_section:
                preferences["Has Learned Patterns"] = "Yes (see USER_PREFERENCES.md)"

        return preferences

    def build_preference_context(self, preferences: dict[str, str]) -> str:
        """Build concise preference enforcement context for injection.

        This must be brief but clear enough to enforce preferences.

        Args:
            preferences: Dictionary of preference name -> value

        Returns:
            Formatted context string for injection
        """
        if not preferences:
            return ""

        lines = ["🎯 ACTIVE USER PREFERENCES (MANDATORY - Apply to all responses):"]

        # Priority order for displaying preferences (most impactful first)
        priority_order = [
            "Communication Style",
            "Verbosity",
            "Collaboration Style",
            "Update Frequency",
            "Priority Type",
            "Preferred Languages",
            "Coding Standards",
            "Workflow Preferences",
            "Has Learned Patterns",
        ]

        # Add preferences in priority order
        for pref_name in priority_order:
            if pref_name in preferences:
                value = preferences[pref_name]

                # Add specific enforcement instruction based on preference type
                if pref_name == "Communication Style":
                    lines.append(f"• {pref_name}: {value} - Use this style in your response")
                elif pref_name == "Verbosity":
                    lines.append(f"• {pref_name}: {value} - Match this detail level")
                elif pref_name == "Collaboration Style":
                    lines.append(f"• {pref_name}: {value} - Follow this approach")
                elif pref_name == "Update Frequency":
                    lines.append(f"• {pref_name}: {value} - Provide updates at this frequency")
                elif pref_name == "Priority Type":
                    lines.append(f"• {pref_name}: {value} - Consider this priority in decisions")
                elif pref_name == "Has Learned Patterns":
                    lines.append(f"• {value}")
                else:
                    lines.append(f"• {pref_name}: {value}")

        lines.append("")
        lines.append(
            "Apply these preferences to this response. These preferences are READ-ONLY except when using /amplihack:customize command."
        )

        return "\n".join(lines)

    def get_cached_preferences(self, pref_file: Path) -> dict[str, str]:
        """Get preferences with simple caching to improve performance.

        Args:
            pref_file: Path to preferences file

        Returns:
            Dictionary of preferences
        """
        try:
            current_mtime = pref_file.stat().st_mtime
            if self._cache_timestamp == current_mtime:
                return self._preferences_cache

            # Read and parse preferences
            content = pref_file.read_text(encoding="utf-8")
            preferences = self.extract_preferences(content)

            # Update cache
            self._preferences_cache = preferences
            self._cache_timestamp = current_mtime

            return preferences

        except Exception as e:
            self.log(f"Error reading preferences: {e}", "WARNING")
            return {}

    def _inject_amplihack_if_different(self) -> str:
        """Inject AMPLIHACK.md contents if it differs from CLAUDE.md.

        This ensures framework instructions are always present even when users
        have custom project-specific CLAUDE.md files.

        Uses caching with mtime checks to avoid repeated file reads (performance).

        Returns:
            AMPLIHACK.md contents if different from CLAUDE.md, empty string otherwise
        """
        try:
            claude_md = self.project_root / "CLAUDE.md"

            # Find AMPLIHACK.md in centralized plugin location (Issue #1948)
            amplihack_md = None

            # Try centralized plugin location first (plugin architecture)
            plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
            if plugin_root:
                plugin_path = Path(plugin_root)
                if plugin_path.exists() and plugin_path.is_dir():
                    candidate = plugin_path / "AMPLIHACK.md"
                    if candidate.exists():
                        amplihack_md = candidate

            # Fallback: Check project .claude/ directory (per-project mode)
            if not amplihack_md:
                candidate = self.project_root / ".claude" / "AMPLIHACK.md"
                if candidate.exists():
                    amplihack_md = candidate

            # If we can't find AMPLIHACK.md, nothing to inject
            if not amplihack_md:
                self.log("No AMPLIHACK.md found - skipping framework injection")
                return ""

            # Check cache validity using mtimes (avoids re-reading ~2000 lines per message)
            amplihack_mtime = amplihack_md.stat().st_mtime
            claude_mtime = claude_md.stat().st_mtime if claude_md.exists() else 0

            if (
                self._amplihack_cache is not None
                and self._amplihack_cache_timestamp is not None
                and self._amplihack_cache_timestamp == (amplihack_mtime, claude_mtime)
            ):
                # Cache hit - files haven't changed
                return self._amplihack_cache

            # Cache miss - read and compare files
            amplihack_content = amplihack_md.read_text(encoding="utf-8")
            claude_content = claude_md.read_text(encoding="utf-8") if claude_md.exists() else ""

            # Compare contents (whitespace-normalized to avoid formatting differences)
            # NOTE: In amplihack's own repo, CLAUDE.md == AMPLIHACK.md, so this returns ""
            if claude_content.strip() == amplihack_content.strip():
                result = ""
            else:
                result = amplihack_content

            # Update cache
            self._amplihack_cache = result
            self._amplihack_cache_timestamp = (amplihack_mtime, claude_mtime)

            return result

        except Exception as e:
            # Don't fail the hook if this doesn't work
            self.log(f"Could not check AMPLIHACK.md vs CLAUDE.md: {e}", "WARNING")
            return ""

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process user prompt submit event.

        Injection order (intentional):
        1. User preferences (behavioral guidance)
        2. Agent memories (context for mentioned agents)
        3. AMPLIHACK.md framework instructions (if CLAUDE.md differs)

        Args:
            input_data: Input from Claude Code

        Returns:
            Additional context to inject
        """
        # Detect launcher and select strategy
        self.strategy = self._select_strategy()
        if self.strategy:
            self.log(f"Using strategy: {self.strategy.__class__.__name__}")
            # Check for strategy-specific prompt handling
            strategy_result = self.strategy.handle_user_prompt_submit(input_data)
            if strategy_result:
                self.log("Strategy provided custom prompt handling")
                return strategy_result

        # Extract user prompt - handle both string and dict formats
        user_message = input_data.get("userMessage", "")
        if isinstance(user_message, dict):
            user_prompt = user_message.get("text", "")
        else:
            user_prompt = str(user_message)

        # Build context parts (in order)
        context_parts = []

        # 1. Inject user preferences first (behavioral guidance)
        pref_file = self.find_user_preferences()
        if pref_file:
            # Get preferences (with caching for performance)
            preferences = self.get_cached_preferences(pref_file)

            if preferences:
                # Build preference context
                pref_context = self.build_preference_context(preferences)
                context_parts.append(pref_context)

                # Log activity (for debugging)
                self.log(f"Injected {len(preferences)} preferences on user prompt")
                self.save_metric("preferences_injected", len(preferences))
        else:
            self.log("No USER_PREFERENCES.md found - skipping preference injection")

        # 2. Inject agent memories (context for mentioned agents)
        memory_context = ""
        try:
            from agent_memory_hook import (
                detect_agent_references,
                detect_slash_command_agent,
                format_memory_injection_notice,
                inject_memory_for_agents_sync,
            )

            # Detect agent references
            agent_types = detect_agent_references(user_prompt)

            # Also check for slash command agents
            slash_agent = detect_slash_command_agent(user_prompt)
            if slash_agent:
                agent_types.append(slash_agent)

            if agent_types:
                self.log(f"Detected agents: {agent_types}")

                # Inject memory context for these agents (using sync wrapper)
                session_id = self.get_session_id()
                enhanced_prompt, memory_metadata = inject_memory_for_agents_sync(
                    user_prompt, agent_types, session_id
                )

                # Extract memory context (everything before the original prompt)
                if enhanced_prompt != user_prompt:
                    memory_context = enhanced_prompt.replace(user_prompt, "").strip()
                    if memory_context:
                        context_parts.append(memory_context)

                # Log memory injection
                notice = format_memory_injection_notice(memory_metadata)
                if notice:
                    self.log(notice)

                # Save metrics
                self.save_metric(
                    "agent_memory_injected", memory_metadata.get("memories_injected", 0)
                )
                self.save_metric("agents_detected", len(agent_types))

        except Exception as e:
            self.log(f"Memory injection failed (non-fatal): {e}", "WARNING")

        # 3. Inject AMPLIHACK.md framework instructions (if CLAUDE.md differs)
        amplihack_context = self._inject_amplihack_if_different()
        if amplihack_context:
            context_parts.append(amplihack_context)
            self.log("Injected AMPLIHACK.md framework instructions")

        # Combine all context parts
        full_context = "\n\n".join(context_parts)

        # Save total context length metric
        self.save_metric("context_length", len(full_context))

        # Return output in correct format
        return {
            "additionalContext": full_context,
        }

    def _select_strategy(self):
        """Detect launcher and select appropriate strategy."""
        try:
            # Import adaptive components
            sys.path.insert(0, str(self.project_root / "src" / "amplihack"))
            from amplihack.context.adaptive.detector import LauncherDetector
            from amplihack.context.adaptive.strategies import ClaudeStrategy, CopilotStrategy

            detector = LauncherDetector(self.project_root)
            launcher_type = detector.detect()

            if launcher_type == "copilot":
                return CopilotStrategy(self.project_root, self.log)
            return ClaudeStrategy(self.project_root, self.log)

        except ImportError as e:
            self.log(f"Adaptive strategy not available: {e}", "DEBUG")
            return None


def main():
    """Entry point for the user_prompt_submit hook."""
    hook = UserPromptSubmitHook()
    hook.run()


if __name__ == "__main__":
    main()
