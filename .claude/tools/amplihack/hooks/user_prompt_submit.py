#!/usr/bin/env python3
"""
UserPromptSubmit hook - Inject user preferences on every message.
Ensures preferences persist across all conversation turns in REPL mode.
"""

__all__ = ["UserPromptSubmitHook", "main"]

import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor

# ============================================================================
# PERFORMANCE: Pre-compiled regex patterns (module-level constants)
# ============================================================================
# Compile once at import time instead of per-message to improve performance

# Session ID validation (alphanumeric, underscore, hyphen only)
_SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

# Workflow reminder preference detection
_WORKFLOW_REMINDER_PATTERN = re.compile(r"Workflow Reminders:\s*(\w+)", re.IGNORECASE)

# Preference extraction patterns (compiled once, reused per preference)
_PREFERENCE_PATTERNS = {
    "Communication Style": re.compile(r"### Communication Style\s*\n\s*([^\n]+)"),
    "Verbosity": re.compile(r"### Verbosity\s*\n\s*([^\n]+)"),
    "Collaboration Style": re.compile(r"### Collaboration Style\s*\n\s*([^\n]+)"),
    "Update Frequency": re.compile(r"### Update Frequency\s*\n\s*([^\n]+)"),
    "Priority Type": re.compile(r"### Priority Type\s*\n\s*([^\n]+)"),
    "Preferred Languages": re.compile(r"### Preferred Languages\s*\n\s*([^\n]+)"),
    "Coding Standards": re.compile(r"### Coding Standards\s*\n\s*([^\n]+)"),
    "Workflow Preferences": re.compile(r"### Workflow Preferences\s*\n\s*([^\n]+)"),
}

# ============================================================================
# PERFORMANCE: Static constants (avoid runtime construction)
# ============================================================================

# Workflow reminder template (static, never changes)
_WORKFLOW_REMINDER_TEMPLATE = """⚙️ **Workflow Classification Reminder**

Consider using structured workflows for complex tasks:
• Use `recipes` tool to execute `default-workflow.yaml` for features/bugs/refactoring
• Workflows provide: analysis → design → implementation → review → test phases
• Avoid jumping directly to implementation without design phase

**How to use**:
  `recipes(operation="execute", recipe_path="@recipes:default-workflow.yaml")`

Or ask me: "Run the default workflow for this feature"

Available via: recipes tool with default-workflow.yaml"""

# Direction change keywords (immutable tuple for faster iteration)
_DIRECTION_KEYWORDS = (
    "now let's",
    "next",
    "different topic",
    "moving on",
    "switching to",
)

# Implementation keywords (immutable tuple for faster iteration)
_IMPLEMENTATION_KEYWORDS = (
    "implement",
    "build",
    "create feature",
    "add",
    "develop",
    "write code",
)

# Workflow reminder enabled values (frozenset for O(1) lookup)
_ENABLED_VALUES = frozenset({"enabled", "yes", "on", "true"})
_DISABLED_VALUES = frozenset({"disabled", "no", "off", "false"})

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
        # Workflow reminder state
        self._workflow_state_dir: Path | None = None

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

        # Use pre-compiled patterns for better performance
        for pref_name, pattern in _PREFERENCE_PATTERNS.items():
            match = pattern.search(content)
            if match:
                value = match.group(1).strip()
                # Skip empty or placeholder values (tuple for faster membership test)
                if value and value not in ("", "(not set)", "not set"):
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
            self.log(f"Error reading preferences: {e}", "ERROR")
            self.save_metric("preferences_error", 1)
            return {}  # Return empty dict - caller will skip injection

    def _validate_session_id(self, session_id: str) -> bool:
        """Validate session ID to prevent path traversal attacks.

        Args:
            session_id: Session ID to validate

        Returns:
            True if session ID is valid, False otherwise
        """
        # Use pre-compiled pattern for better performance
        return bool(_SESSION_ID_PATTERN.match(session_id))

    def _init_workflow_state_dir(self) -> None:
        """Initialize workflow state directory with secure permissions."""
        if self._workflow_state_dir is not None:
            return  # Already initialized

        try:
            # Get runtime directory (set by parent HookProcessor)
            runtime_dir = getattr(self, "runtime_dir", None)
            if runtime_dir is None:
                # Fallback for test environments
                runtime_dir = Path.home() / ".amplifier" / "runtime" / "logs"
                runtime_dir.mkdir(parents=True, exist_ok=True)

            # Create classification_state subdirectory
            state_dir = runtime_dir / "classification_state"
            state_dir.mkdir(parents=True, exist_ok=True)

            # Set secure permissions (0o700 - owner only)
            os.chmod(state_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

            self._workflow_state_dir = state_dir
            self.log(f"Initialized workflow state directory: {state_dir}")
        except Exception as e:
            self.log(f"Failed to initialize workflow state directory: {e}", "ERROR")
            self.save_metric("workflow_state_init_error", 1)
            # Set to None to indicate failure
            self._workflow_state_dir = None

    def _get_workflow_state_file(self, session_id: str) -> Path | None:
        """Get workflow state file path with validation.

        Args:
            session_id: Session ID

        Returns:
            Path to state file or None if validation fails
        """
        # Validate session ID first (security)
        if not self._validate_session_id(session_id):
            self.log(f"Invalid session ID rejected: {session_id}", "WARNING")
            self.save_metric("workflow_security_session_id_rejected", 1)
            return None

        # Ensure state directory is initialized
        if self._workflow_state_dir is None:
            self._init_workflow_state_dir()

        if self._workflow_state_dir is None:
            return None  # Initialization failed

        # Build state file path
        state_file = self._workflow_state_dir / f"{session_id}.json"

        # Additional security: verify path is inside state directory (prevent traversal)
        try:
            state_file.resolve().relative_to(self._workflow_state_dir.resolve())
        except ValueError:
            self.log(f"Path traversal attempt blocked: {session_id}", "WARNING")
            self.save_metric("workflow_security_path_traversal_blocked", 1)
            return None

        return state_file

    def _safe_json_load(self, file_path: Path) -> dict[str, Any] | None:
        """Safely load and validate JSON from file.

        Args:
            file_path: Path to JSON file

        Returns:
            Parsed dictionary or None if invalid
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            data = json.loads(content)

            # Validate it's a dictionary
            if not isinstance(data, dict):
                self.log(f"Invalid JSON structure in {file_path}: not a dict", "WARNING")
                return None

            return data
        except json.JSONDecodeError as e:
            self.log(f"Invalid JSON in {file_path}: {e}", "WARNING")
            self.save_metric("workflow_json_parse_error", 1)
            return None
        except Exception as e:
            self.log(f"Error reading state file {file_path}: {e}", "WARNING")
            return None

    def _is_workflow_reminder_enabled(self) -> bool:
        """Check if workflow reminders are enabled in user preferences.

        Returns:
            True if enabled (default), False if disabled
        """
        try:
            pref_file = self.find_user_preferences()
            if not pref_file or not pref_file.exists():
                return True  # Default: enabled

            content = pref_file.read_text(encoding="utf-8")

            # Use pre-compiled pattern for better performance
            match = _WORKFLOW_REMINDER_PATTERN.search(content)

            if not match:
                return True  # Not specified, default to enabled

            value = match.group(1).lower()

            # Use frozensets for O(1) membership lookup
            if value in _ENABLED_VALUES:
                return True
            elif value in _DISABLED_VALUES:
                return False
            else:
                # Unknown value, default to enabled
                self.log(
                    f"Unknown workflow reminder preference: {value}, defaulting to enabled",
                    "WARNING",
                )
                return True
        except Exception as e:
            self.log(f"Error checking workflow reminder preference: {e}", "ERROR")
            self.save_metric("workflow_preference_check_error", 1)
            return True  # Default to enabled on error

    def _is_recipe_active(self) -> bool:
        """Check if a recipe is currently active.

        Returns:
            True if recipe is active, False otherwise
        """
        try:
            # Check environment variables
            if os.environ.get("AMPLIFIER_RECIPE_ACTIVE") == "true":
                return True
            if os.environ.get("RECIPE_SESSION"):
                return True

            # Check for recipe lock file (runtime_dir or fallback to home)
            session_id = self.get_session_id()
            runtime_dir = getattr(self, "runtime_dir", None)
            lock_dir = (
                runtime_dir / "recipe_locks"
                if runtime_dir
                else Path.home() / ".amplifier" / "runtime" / "recipe_locks"
            )
            lock_file = lock_dir / f"{session_id}.lock"
            if lock_file.exists():
                return True

            return False
        except Exception as e:
            self.log(f"Error checking recipe active status: {e}", "ERROR")
            self.save_metric("recipe_check_error", 1)
            return False  # Fail-safe: assume not active

    def _is_new_workflow_topic(self, prompt: str, turn_number: int) -> bool:
        """Detect if this is a new workflow topic requiring reminder.

        Args:
            prompt: User's message
            turn_number: Turn number (0-indexed)

        Returns:
            True if new topic detected
        """
        try:
            # First message detection (turn 0)
            if turn_number == 0:
                return True

            # Use pre-lowercased prompt for faster keyword matching
            prompt_lower = prompt.lower()

            # Check for direction change (using static tuples)
            for keyword in _DIRECTION_KEYWORDS:
                if keyword in prompt_lower:
                    return True

            # Check for implementation keywords (using static tuples)
            for keyword in _IMPLEMENTATION_KEYWORDS:
                if keyword in prompt_lower:
                    # Check if we recently classified (caching)
                    session_id = self.get_session_id()
                    last_turn = self._get_last_classified_turn(session_id)

                    # If classified within last 3 turns, skip
                    if last_turn is not None and turn_number - last_turn < 3:
                        return False

                    # Implementation keyword found and no recent classification
                    return True
            # Not a new topic
            return False
        except Exception as e:
            self.log(f"Error detecting new workflow topic: {e}", "ERROR")
            self.save_metric("workflow_topic_detection_error", 1)
            return False  # Fail-safe: don't inject on error

    def _get_last_classified_turn(self, session_id: str) -> int | None:
        """Get last classified turn number from state file.

        Args:
            session_id: Session ID

        Returns:
            Last classified turn number or None if no state exists
        """
        try:
            state_file = self._get_workflow_state_file(session_id)
            if not state_file or not state_file.exists():
                return None

            state = self._safe_json_load(state_file)
            if not state:
                return None

            last_turn = state.get("last_classified_turn", -1)
            return last_turn if isinstance(last_turn, int) else None
        except Exception as e:
            self.log(f"Error reading workflow state: {e}", "ERROR")
            self.save_metric("workflow_state_read_error", 1)
            return None

    def _save_workflow_classification_state(self, session_id: str, turn: int) -> None:
        """Save workflow classification state atomically.

        Args:
            session_id: Session ID
            turn: Turn number
        """
        try:
            state_file = self._get_workflow_state_file(session_id)
            if not state_file:
                return  # Validation failed

            # Build state data
            state = {
                "last_classified_turn": turn,
                "session_id": session_id,
            }

            # Atomic write pattern: write to .tmp, chmod, rename
            tmp_file = state_file.with_suffix(".tmp")
            tmp_file.write_text(json.dumps(state), encoding="utf-8")

            # Set secure permissions (0o600 - owner read/write only)
            os.chmod(tmp_file, stat.S_IRUSR | stat.S_IWUSR)

            # Atomic rename
            tmp_file.rename(state_file)

            self.log(f"Saved workflow classification state: turn {turn}")
        except Exception as e:
            self.log(f"Error saving workflow classification state: {e}", "ERROR")
            self.save_metric("workflow_state_save_error", 1)
            # Non-fatal - continue

    def _build_workflow_reminder(self) -> str:
        """Build workflow reminder text (static template).

        Returns:
            Formatted reminder text (~110 tokens)
        """
        # Use pre-built static template (no runtime construction)
        return _WORKFLOW_REMINDER_TEMPLATE

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
            self.log(f"Could not check AMPLIHACK.md vs CLAUDE.md: {e}", "ERROR")
            self.save_metric("amplihack_injection_error", 1)
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
            self.log(f"Memory injection failed (non-fatal): {e}", "ERROR")
            self.save_metric("agent_memory_error", 1)

        # 3. Inject AMPLIHACK.md framework instructions (if CLAUDE.md differs)
        amplihack_context = self._inject_amplihack_if_different()
        if amplihack_context:
            context_parts.append(amplihack_context)
            self.log("Injected AMPLIHACK.md framework instructions")

        # 4. Inject workflow reminder (if appropriate)
        try:
            # Check if workflow reminders are enabled
            if not self._is_workflow_reminder_enabled():
                self.log("Workflow reminders disabled via user preferences")
                self.save_metric("workflow_reminder_disabled", 1)
            # Check if recipe is active (skip during recipe execution)
            elif self._is_recipe_active():
                self.log("Recipe active - skipping workflow reminder")
                self.save_metric("workflow_reminder_skipped_recipe", 1)
            else:
                # Check if this is a new workflow topic
                turn_count = input_data.get("turnCount", 0)
                if self._is_new_workflow_topic(user_prompt, turn_count):
                    # Initialize state directory if needed
                    self._init_workflow_state_dir()

                    # Inject reminder
                    reminder = self._build_workflow_reminder()
                    context_parts.append(reminder)

                    # Save state
                    session_id = self.get_session_id()
                    self._save_workflow_classification_state(session_id, turn_count)

                    # Log and metrics
                    self.log(f"Injected workflow reminder at turn {turn_count}")
                    self.save_metric("workflow_reminder_injected", 1)
                else:
                    self.log("Follow-up message - skipping workflow reminder")
                    self.save_metric("workflow_reminder_skipped_followup", 1)
        except Exception as e:
            self.log(f"Workflow reminder injection failed (non-fatal): {e}", "WARNING")
            self.save_metric("workflow_reminder_error", 1)
            # Continue without failing hook

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
