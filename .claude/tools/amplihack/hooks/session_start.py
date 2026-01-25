#!/usr/bin/env python3
"""
Claude Code hook for session start.
Uses unified HookProcessor for common functionality.
"""

# Import the base processor
import sys
from pathlib import Path
from typing import Any

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor

# Clean imports through package structure
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from context_preservation import ContextPreserver
    from paths import get_project_root
    from settings_migrator import migrate_global_hooks

    from amplihack.context.adaptive.detector import LauncherDetector
    from amplihack.context.adaptive.strategies import ClaudeStrategy, CopilotStrategy
    from amplihack.utils.paths import FrameworkPathResolver
except ImportError:
    # Fallback imports for standalone execution
    get_project_root = None
    ContextPreserver = None
    FrameworkPathResolver = None
    migrate_global_hooks = None
    LauncherDetector = None
    ClaudeStrategy = None
    CopilotStrategy = None


class SessionStartHook(HookProcessor):
    """Hook processor for session start events."""

    def __init__(self):
        super().__init__("session_start")

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process session start event.

        Checks performed:
        1. Version mismatch detection and auto-update
        2. Global hook migration (prevents duplicate hook execution)
        3. Original request capture for context preservation
        4. Neo4j memory system startup (if enabled)

        Args:
            input_data: Input from Claude Code

        Returns:
            Additional context to add to the session
        """
        # Check for version mismatch FIRST (before any heavy operations)
        self._check_version_mismatch()

        # NEW: Check for global hook duplication and migrate
        self._migrate_global_hooks()

        # Detect launcher and select strategy
        strategy = self._select_strategy()
        self.log(f"Using strategy: {strategy.__class__.__name__}")

        # Extract prompt
        prompt = input_data.get("prompt", "")
        self.log(f"Prompt length: {len(prompt)}")

        # Save metric
        self.save_metric("prompt_length", len(prompt))

        # Capture original request for substantial prompts
        original_request_context = ""
        original_request_captured = False

        # Simple check for substantial requests
        substantial_keywords = [
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
        ]
        is_substantial = len(prompt) > 20 or any(
            word in prompt.lower() for word in substantial_keywords
        )

        if ContextPreserver and is_substantial:
            try:
                # Create context preserver with current session ID
                session_id = self.get_session_id()
                preserver = ContextPreserver(session_id)

                # Extract and save original request
                original_request = preserver.extract_original_request(prompt)

                # Simple verification and context formatting
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

        # Settings.json initialization/merge with UVX template
        # Ensures statusLine and other critical configurations are present
        try:
            from amplihack.utils.uvx_settings_manager import UVXSettingsManager

            settings_path = self.project_root / ".claude" / "settings.json"
            manager = UVXSettingsManager()

            # Check if settings need updating (empty, missing statusLine, etc.)
            if manager.should_use_uvx_template(settings_path):
                success = manager.create_uvx_settings(settings_path, preserve_existing=True)
                if success:
                    self.log("✅ Settings.json updated with UVX template (includes statusLine)")
                    self.save_metric("settings_updated", True)
                else:
                    self.log("⚠️ Failed to update settings.json with template", "WARNING")
                    self.save_metric("settings_updated", False)
            else:
                self.log("Settings.json already complete")
                self.save_metric("settings_updated", False)
        except ImportError as e:
            self.log(f"UVXSettingsManager not available: {e}", "WARNING")
            self.save_metric("settings_updated", False)
        except Exception as e:
            # Fail gracefully - don't break session start
            self.log(f"Settings merge failed (non-critical): {e}", "WARNING")
            self.save_metric("settings_update_error", True)

        # Neo4j Startup (Conditional - Opt-In Only)
        # Why opt-in: Neo4j requires Docker, external dependencies (Blarify), and adds complexity
        # Most users don't need advanced graph memory features
        import os

        neo4j_enabled = os.environ.get("AMPLIHACK_ENABLE_NEO4J_MEMORY") == "1"

        if neo4j_enabled:
            self.log("Neo4j opt-in flag detected, starting memory system...")
            try:
                from amplihack.memory.neo4j.startup_wizard import interactive_neo4j_startup

                # Interactive startup with user feedback
                success = interactive_neo4j_startup()

                if success:
                    self.log("✅ Neo4j memory system ready")
                    self.save_metric("neo4j_enabled", True)
                else:
                    self.log("⚠️ Neo4j startup declined or failed, using basic memory", "WARNING")
                    self.save_metric("neo4j_enabled", False)

            except Exception as e:
                self.log(f"Neo4j startup failed: {e}", "ERROR")
                self.save_metric("neo4j_enabled", False)
        else:
            self.log("Neo4j not enabled (use --enable-neo4j-memory to enable)")
            self.save_metric("neo4j_enabled", False)

        # Check and update .gitignore for runtime directories
        try:
            from gitignore_checker import GitignoreChecker

            checker = GitignoreChecker()
            result = checker.run(display_warnings=True)
            if result.get("modified"):
                print(result.get("warning_message", ""), file=sys.stderr)
                self.save_metric("gitignore_modified", True)
        except ImportError:
            # gitignore_checker not available (shouldn't happen)
            self.log("gitignore_checker module not found", "WARNING")
        except Exception as e:
            # Fail-safe: don't break session start
            self.log(f"Gitignore check failed (non-critical): {e}", "WARNING")

        # Build context if needed
        context_parts = []

        # Add project context
        context_parts.append("## Project Context")
        context_parts.append("This is the Microsoft Hackathon 2025 Agentic Coding project.")
        context_parts.append("Focus on building AI-powered development tools.")

        # Check for recent discoveries from memory
        context_parts.append("\n## Recent Learnings")
        try:
            from amplihack.memory.discoveries import get_recent_discoveries

            recent_discoveries = get_recent_discoveries(days=30, limit=5)
            if recent_discoveries:
                context_parts.append(
                    f"Found {len(recent_discoveries)} recent discoveries in memory:"
                )
                for disc in recent_discoveries:
                    summary = disc.get("summary", "No summary")
                    category = disc.get("category", "uncategorized")
                    context_parts.append(f"- [{category}] {summary}")
            else:
                context_parts.append("Check .claude/context/DISCOVERIES.md for recent insights.")
        except ImportError:
            # Fallback if memory module not available
            context_parts.append("Check .claude/context/DISCOVERIES.md for recent insights.")

        # Simplified preference file resolution
        preferences_file = (
            FrameworkPathResolver.resolve_preferences_file()
            if FrameworkPathResolver
            else self.project_root / ".claude" / "context" / "USER_PREFERENCES.md"
        )

        if preferences_file and preferences_file.exists():
            try:
                with open(preferences_file) as f:
                    full_prefs_content = f.read()
                self.log(f"Successfully read preferences from: {preferences_file}")

                # Use strategy to inject preferences (launcher-specific format)
                if strategy:
                    prefs_context = strategy.inject_context(full_prefs_content)
                    context_parts.append(prefs_context)
                    self.log(f"Injected preferences using {strategy.__class__.__name__}")
                else:
                    # Fallback to default injection
                    context_parts.append("\n## 🎯 USER PREFERENCES (MANDATORY - MUST FOLLOW)")
                    context_parts.append(
                        "\nApply these preferences to all responses. These preferences are READ-ONLY except when using /amplihack:customize command.\n"
                    )
                    context_parts.append(
                        "\n💡 **Preference Management**: Use /amplihack:customize to view or modify preferences.\n"
                    )
                    context_parts.append(full_prefs_content)
                    self.log("Injected full USER_PREFERENCES.md content into session (fallback)")

            except Exception as e:
                self.log(f"Could not read preferences: {e}", "WARNING")
                # Fail silently - don't break session start

        # Add workflow information at startup with UVX support
        context_parts.append("\n## 📝 Default Workflow")
        context_parts.append("The multi-step workflow is automatically followed by `/ultrathink`")

        # Use FrameworkPathResolver for workflow path
        workflow_file = None
        if FrameworkPathResolver:
            workflow_file = FrameworkPathResolver.resolve_workflow_file()

        if workflow_file:
            context_parts.append(f"• To view the workflow: Read {workflow_file}")
            context_parts.append("• To customize: Edit the workflow file directly")
        else:
            context_parts.append(
                "• To view the workflow: Use FrameworkPathResolver.resolve_workflow_file() (UVX-compatible)"
            )
            context_parts.append("• To customize: Edit the workflow file directly")
        context_parts.append(
            "• Steps include: Requirements → Issue → Branch → Design → Implement → Review → Merge"
        )

        # Add verbosity instructions
        context_parts.append("\n## 🎤 Verbosity Mode")
        context_parts.append("• Current setting: balanced")
        context_parts.append(
            "• To enable verbose: Use TodoWrite tool frequently and provide detailed explanations"
        )
        context_parts.append("• Claude will adapt to your verbosity preference in responses")

        # Build response
        output = {}
        if context_parts:
            # Create comprehensive startup context
            full_context = "\n".join(context_parts)

            # Build a visible startup message (even though Claude Code may not display it)
            startup_msg_parts = ["🚀 AmplifyHack Session Initialized", "━" * 40]

            # Add preference summary if any exist
            if len([p for p in context_parts if "**" in p and ":" in p]) > 0:
                startup_msg_parts.append("🎯 Active preferences loaded and enforced")

            startup_msg_parts.extend(
                [
                    "",
                    "📝 Workflow: Use `/ultrathink` for the multi-step process",
                    "⚙️  Customize: Edit the workflow file (use FrameworkPathResolver for UVX compatibility)",
                    "🎯 Preferences: Loaded from USER_PREFERENCES.md",
                    "",
                    "Type `/help` for available commands",
                ]
            )

            # CRITICAL: Inject original request context at top priority
            if original_request_context:
                full_context = original_request_context + "\n\n" + full_context

            # Use correct SessionStart hook protocol format
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": full_context,
                }
            }
            self.log(
                f"Session initialized - Original request: {'✅' if original_request_captured else '❌'}"
            )
            self.log(f"Injected {len(full_context)} characters of context")

        return output

    def _select_strategy(self):
        """Detect launcher and select appropriate strategy."""
        if LauncherDetector is None or ClaudeStrategy is None or CopilotStrategy is None:
            # Fallback to default (no strategy)
            return None

        detector = LauncherDetector(self.project_root)
        launcher_type = detector.detect()  # Returns string: "claude", "copilot", "unknown"

        if launcher_type == "copilot":
            return CopilotStrategy(self.project_root, self.log)
        return ClaudeStrategy(self.project_root, self.log)

    def _check_version_mismatch(self) -> None:
        """Check for version mismatch and offer to update.

        Phase 2: Interactive update with user prompt.
        Fails gracefully - never raises exceptions.
        """
        try:
            # Import modules
            sys.path.insert(0, str(self.project_root / ".claude" / "tools" / "amplihack"))
            from update_engine import perform_update
            from update_prefs import load_update_preference, save_update_preference
            from version_checker import check_version_mismatch

            # Check for mismatch
            version_info = check_version_mismatch()

            if not version_info.is_mismatched:
                self.log("✅ .claude/ directory version matches package")
                return

            # Log mismatch
            self.log(
                f"⚠️ Version mismatch detected: package={version_info.package_commit}, project={version_info.project_commit}",
                "WARNING",
            )

            # Check user preference
            preference = load_update_preference()

            if preference == "always":
                # Auto-update without prompting
                self.log("Auto-updating per user preference")
                result = perform_update(
                    version_info.package_path,
                    version_info.project_path,
                    version_info.project_commit,
                )

                if result.success:
                    print(
                        f"\n✓ Updated .claude/ directory to version {result.new_version}",
                        file=sys.stderr,
                    )
                    print(
                        f"  Updated {len(result.updated_files)} files, preserved {len(result.preserved_files)} files",
                        file=sys.stderr,
                    )
                    print(f"  Backup: {result.backup_path}\n", file=sys.stderr)
                else:
                    print(
                        f"\n✗ Update failed: {result.error}",
                        file=sys.stderr,
                    )
                    print(f"  Backup preserved: {result.backup_path}\n", file=sys.stderr)

                self.save_metric("auto_update_executed", result.success)
                return

            if preference == "never":
                # Skip per user preference - just log
                self.log("Skipping update per user preference (never)")
                print(
                    f"\n⚠️  .claude/ directory out of date (package: {version_info.package_commit}, project: {version_info.project_commit or 'unknown'})",
                    file=sys.stderr,
                )
                print(
                    "  Auto-update disabled. To update: /amplihack:customize set auto_update always\n",
                    file=sys.stderr,
                )
                return

            # No preference - prompt user
            print("\n" + "=" * 70, file=sys.stderr)
            print("⚠️  Version Mismatch Detected", file=sys.stderr)
            print("=" * 70, file=sys.stderr)
            print(
                "\nYour project's .claude/ directory is out of date:",
                file=sys.stderr,
            )
            print(f"  Package version:  {version_info.package_commit} (installed)", file=sys.stderr)
            print(
                f"  Project version:  {version_info.project_commit or 'unknown'} (in .claude/.version)",
                file=sys.stderr,
            )
            print(
                "\nThis may cause bugs or unexpected behavior (like stale hooks).",
                file=sys.stderr,
            )
            print("\nUpdate now? Your custom files will be preserved.", file=sys.stderr)
            print("\n[y] Yes, update now", file=sys.stderr)
            print("[n] No, skip this time", file=sys.stderr)
            print("[a] Always auto-update (don't ask again)", file=sys.stderr)
            print("[v] Never auto-update (don't ask again)", file=sys.stderr)
            print("\n" + "=" * 70, file=sys.stderr)

            # Get user input with timeout
            import select

            print("\nChoice (y/n/a/v): ", end="", file=sys.stderr, flush=True)

            # 30 second timeout for user response
            ready, _, _ = select.select([sys.stdin], [], [], 30)

            if not ready:
                print("\n\n(timeout - skipping update)\n", file=sys.stderr)
                self.log("User prompt timed out - skipping update")
                return

            choice = sys.stdin.readline().strip().lower()

            # Handle response
            if choice in ["a", "always"]:
                save_update_preference("always")
                self.log("User selected 'always' - saving preference and updating")
                choice = "yes"
            elif choice in ["v", "never"]:
                save_update_preference("never")
                self.log("User selected 'never' - saving preference and skipping")
                print("\n✓ Preference saved: never auto-update\n", file=sys.stderr)
                return
            elif choice not in ["y", "yes"]:
                self.log(f"User declined update (choice: {choice})")
                print("\n✓ Skipping update\n", file=sys.stderr)
                return

            # Perform update
            print("\nUpdating .claude/ directory...\n", file=sys.stderr)
            result = perform_update(
                version_info.package_path, version_info.project_path, version_info.project_commit
            )

            if result.success:
                print(f"\n✓ Update complete! Version {result.new_version}", file=sys.stderr)
                print(
                    f"  Updated: {len(result.updated_files)} files",
                    file=sys.stderr,
                )
                print(
                    f"  Preserved: {len(result.preserved_files)} files (you modified these)",
                    file=sys.stderr,
                )
                print(f"  Backup: {result.backup_path}", file=sys.stderr)
                print("\n" + "=" * 70 + "\n", file=sys.stderr)
                self.save_metric("update_success", True)
            else:
                print(f"\n✗ Update failed: {result.error}", file=sys.stderr)
                print(f"  Backup preserved: {result.backup_path}", file=sys.stderr)
                print("\n" + "=" * 70 + "\n", file=sys.stderr)
                self.save_metric("update_success", False)

        except Exception as e:
            # Fail gracefully - don't break session start
            self.log(f"Version check failed: {e}", "WARNING")
            self.save_metric("version_check_error", True)

    def _migrate_global_hooks(self) -> None:
        """Migrate global amplihack hooks to project-local.

        Detects and removes amplihack hooks from ~/.claude/settings.json
        to prevent duplicate execution. Fail-safe: errors are logged but
        don't break session startup.

        This prevents the duplicate stop hook issue where hooks run twice
        (once from global, once from project-local).
        """
        # Skip if migrator not available
        if migrate_global_hooks is None:
            return

        try:
            result = migrate_global_hooks(self.project_root)

            if result.global_hooks_removed:
                # User has been notified by migrator - just log
                self.log("✅ Global amplihack hooks migrated to project-local")
                self.save_metric("global_hooks_migrated", True)

                # Additional user notification
                print("\n" + "=" * 70, file=sys.stderr)
                print("✓ Hook Migration Complete", file=sys.stderr)
                print("=" * 70, file=sys.stderr)
                print(
                    "\nGlobal amplihack hooks have been removed from ~/.claude/settings.json",
                    file=sys.stderr,
                )
                print(
                    "Hooks now run only from project-local settings (no more duplicates!).",
                    file=sys.stderr,
                )
                if result.backup_created:
                    print(f"Backup created: {result.backup_created}", file=sys.stderr)
                print("\n" + "=" * 70 + "\n", file=sys.stderr)

            elif result.global_hooks_found and not result.global_hooks_removed:
                # Migration attempted but failed
                self.log("⚠️ Global hooks detected but migration failed", "WARNING")
                self.save_metric("global_hooks_migrated", False)

            else:
                # No global hooks found - normal case
                self.save_metric("global_hooks_migrated", False)

        except Exception as e:
            # Fail-safe: Log but don't break session
            self.log(f"Hook migration failed (non-critical): {e}", "WARNING")
            self.save_metric("hook_migration_error", True)


def main():
    """Entry point for the session start hook."""
    hook = SessionStartHook()
    hook.run()


if __name__ == "__main__":
    main()
