#!/usr/bin/env python3
"""
Copilot CLI session start hook for agent mirroring.

Ensures .github/agents/ is synchronized with .claude/agents/ at session start.
Runs fast staleness checks and auto-syncs if needed.

Philosophy:
- Non-intrusive (< 500ms for staleness check)
- Fail-safe (errors don't break session)
- User-controlled (respects auto-sync preferences)
- Clear feedback (logs sync operations)
"""

import json
import sys
from pathlib import Path
from typing import Any

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor


class CopilotSessionStartHook(HookProcessor):
    """Hook processor for Copilot CLI session start events."""

    def __init__(self):
        super().__init__("copilot_session_start")

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process Copilot session start event.

        Checks performed:
        1. Check if .github/agents/ exists
        2. Check if agents are stale (compare timestamps)
        3. Auto-sync if missing or stale (unless disabled)
        4. Log sync operation

        Args:
            input_data: Input from Claude Code

        Returns:
            Additional context to add to the session
        """
        # Check if Copilot CLI environment
        if not self._is_copilot_environment():
            self.log("Not a Copilot CLI environment, skipping agent sync")
            return {}

        # Check for .github/agents/ directory
        github_agents_dir = self.project_root / ".github" / "agents"
        claude_agents_dir = self.project_root / ".claude" / "agents"

        if not claude_agents_dir.exists():
            self.log(
                "⚠️ .claude/agents/ directory not found, skipping sync", "WARNING"
            )
            return {}

        # Check staleness (< 500ms requirement)
        try:
            is_stale = self._check_agents_stale(github_agents_dir, claude_agents_dir)

            if not github_agents_dir.exists():
                self.log("🔄 .github/agents/ missing, sync needed")
                should_sync = True
            elif is_stale:
                self.log("🔄 .github/agents/ stale, sync needed")
                should_sync = True
            else:
                self.log("✅ .github/agents/ up to date")
                should_sync = False
                return {}

            # Check user preference for auto-sync
            if should_sync:
                preference = self._get_copilot_auto_sync_preference()

                if preference == "never":
                    self.log("Auto-sync disabled per user preference")
                    print(
                        "\n⚠️  .github/agents/ out of date but auto-sync is disabled",
                        file=sys.stderr,
                    )
                    print(
                        "  To sync: run 'amplihack setup-copilot' or set copilot_auto_sync_agents=true",
                        file=sys.stderr,
                    )
                    return {}

                if preference == "ask":
                    # Prompt user (with timeout)
                    if not self._prompt_user_for_sync():
                        self.log("User declined sync")
                        return {}

                # Auto-sync (preference == "always" or user said yes)
                self._sync_agents(claude_agents_dir, github_agents_dir)

        except Exception as e:
            # Fail-safe: log error but don't break session
            self.log(f"Agent sync check failed (non-critical): {e}", "ERROR")
            self.save_metric("copilot_sync_error", True)

        return {}

    def _is_copilot_environment(self) -> bool:
        """Detect if running in Copilot CLI environment.

        Returns:
            True if Copilot CLI environment detected
        """
        # Check for Copilot CLI indicators
        import os

        # Environment variables that indicate Copilot CLI
        copilot_indicators = [
            "GITHUB_COPILOT_CLI",
            "COPILOT_SESSION",
            "GITHUB_COPILOT_TOKEN",
        ]

        for indicator in copilot_indicators:
            if os.environ.get(indicator):
                return True

        # Check for .github/copilot-instructions.md (strong indicator)
        copilot_instructions = self.project_root / ".github" / "copilot-instructions.md"
        return copilot_instructions.exists()

    def _check_agents_stale(
        self, github_agents_dir: Path, claude_agents_dir: Path
    ) -> bool:
        """Check if .github/agents/ is stale compared to .claude/agents/.

        Fast check (< 500ms): Compare newest modification time in each directory.

        Args:
            github_agents_dir: Path to .github/agents/
            claude_agents_dir: Path to .claude/agents/

        Returns:
            True if sync needed
        """
        if not github_agents_dir.exists():
            return True

        # Get newest file in each directory (fast)
        try:
            claude_newest = max(
                claude_agents_dir.rglob("*.md"), key=lambda p: p.stat().st_mtime
            )
            github_newest = max(
                github_agents_dir.rglob("*.md"), key=lambda p: p.stat().st_mtime
            )

            # If Claude agents are newer, sync is needed
            return claude_newest.stat().st_mtime > github_newest.stat().st_mtime

        except (StopIteration, ValueError):
            # No .md files found or other error - assume sync needed
            return True

    def _get_copilot_auto_sync_preference(self) -> str:
        """Get user preference for Copilot auto-sync.

        Reads from .claude/config.json or USER_PREFERENCES.md.

        Returns:
            "always", "never", or "ask" (default)
        """
        # Try .claude/config.json first
        config_file = self.project_root / ".claude" / "config.json"
        if config_file.exists():
            try:
                config = json.loads(config_file.read_text())
                return config.get("copilot_auto_sync_agents", "ask")
            except Exception:
                pass

        # Try USER_PREFERENCES.md
        prefs_file = self.project_root / ".claude" / "context" / "USER_PREFERENCES.md"
        if prefs_file.exists():
            try:
                content = prefs_file.read_text()
                if "copilot_auto_sync_agents: always" in content.lower():
                    return "always"
                if "copilot_auto_sync_agents: never" in content.lower():
                    return "never"
            except Exception:
                pass

        return "ask"

    def _prompt_user_for_sync(self) -> bool:
        """Prompt user to sync agents (with timeout).

        Returns:
            True if user wants to sync
        """
        import select

        print("\n" + "=" * 70, file=sys.stderr)
        print("🔄 Copilot CLI Agent Sync", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(
            "\n.github/agents/ directory is out of date with .claude/agents/",
            file=sys.stderr,
        )
        print("Sync now? [y/n/always/never]", file=sys.stderr)
        print("\n[y] Yes, sync now", file=sys.stderr)
        print("[n] No, skip this time", file=sys.stderr)
        print("[always] Always auto-sync (don't ask again)", file=sys.stderr)
        print("[never] Never auto-sync (don't ask again)", file=sys.stderr)
        print("\n" + "=" * 70, file=sys.stderr)

        print("\nChoice (y/n/always/never): ", end="", file=sys.stderr, flush=True)

        # 30 second timeout
        ready, _, _ = select.select([sys.stdin], [], [], 30)

        if not ready:
            print("\n\n(timeout - skipping sync)\n", file=sys.stderr)
            return False

        choice = sys.stdin.readline().strip().lower()

        # Handle response
        if choice in ["always"]:
            self._save_copilot_sync_preference("always")
            self.log("User selected 'always' - saving preference")
            return True
        elif choice in ["never"]:
            self._save_copilot_sync_preference("never")
            self.log("User selected 'never' - saving preference")
            print("\n✓ Preference saved: never auto-sync\n", file=sys.stderr)
            return False
        elif choice in ["y", "yes"]:
            return True
        else:
            self.log(f"User declined sync (choice: {choice})")
            print("\n✓ Skipping sync\n", file=sys.stderr)
            return False

    def _save_copilot_sync_preference(self, preference: str) -> None:
        """Save Copilot auto-sync preference to config.

        Args:
            preference: "always" or "never"
        """
        config_file = self.project_root / ".claude" / "config.json"

        try:
            if config_file.exists():
                config = json.loads(config_file.read_text())
            else:
                config = {}

            config["copilot_auto_sync_agents"] = preference
            config_file.write_text(json.dumps(config, indent=2))

            self.log(f"Saved preference: copilot_auto_sync_agents={preference}")

        except Exception as e:
            self.log(f"Failed to save preference: {e}", "ERROR")

    def _sync_agents(self, source_dir: Path, target_dir: Path) -> None:
        """Sync agents from .claude/agents/ to .github/agents/.

        Args:
            source_dir: .claude/agents/
            target_dir: .github/agents/
        """
        try:
            # Import sync-agents functionality
            sys.path.insert(
                0, str(self.project_root / ".claude" / "tools" / "amplihack")
            )
            from sync_agents import sync_agents

            print("\n🔄 Syncing agents...\n", file=sys.stderr)

            result = sync_agents(source_dir, target_dir)

            if result["success"]:
                print(
                    f"\n✓ Synced {result['synced_count']} agents to .github/agents/",
                    file=sys.stderr,
                )
                print(f"  Registry updated: {result['registry_path']}", file=sys.stderr)
                print("\n" + "=" * 70 + "\n", file=sys.stderr)

                self.log(f"✅ Synced {result['synced_count']} agents")
                self.save_metric("copilot_sync_success", True)
                self.save_metric("copilot_synced_count", result["synced_count"])
            else:
                print(
                    f"\n✗ Sync failed: {result.get('error', 'Unknown error')}",
                    file=sys.stderr,
                )
                print("\n" + "=" * 70 + "\n", file=sys.stderr)

                self.log(f"❌ Sync failed: {result.get('error')}", "ERROR")
                self.save_metric("copilot_sync_success", False)

        except ImportError:
            self.log("sync_agents module not found, skipping sync", "ERROR")
            print(
                "\n✗ Could not import sync_agents module",
                file=sys.stderr,
            )
            print(
                "  Run 'amplihack setup-copilot' to set up agent syncing",
                file=sys.stderr,
            )
        except Exception as e:
            self.log(f"Agent sync failed: {e}", "ERROR")
            print(f"\n✗ Sync failed: {e}", file=sys.stderr)


def main():
    """Entry point for the Copilot session start hook."""
    hook = CopilotSessionStartHook()
    hook.run()


if __name__ == "__main__":
    main()
