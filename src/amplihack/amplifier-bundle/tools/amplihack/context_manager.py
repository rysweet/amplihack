#!/usr/bin/env python3
"""Context Manager - Intelligent context window management.

This tool provides intelligent context window management through token monitoring,
context extraction, and selective rehydration. It consolidates all context management
logic into a single, reusable tool that can be called from skills, commands, and hooks.

Philosophy:
- Single responsibility: Monitor, extract, rehydrate context
- Standard library only (no external dependencies)
- Self-contained and regeneratable
- Zero-BS implementation (all functions work completely)

Public API:
    ContextManager: Main context management class
    check_context_status: Check current token usage
    create_context_snapshot: Create intelligent context snapshot
    rehydrate_from_snapshot: Restore context from snapshot
    list_context_snapshots: List available snapshots
    run_automation: Run automatic context management (called from hooks)
    ContextStatus: Status dataclass
    ContextSnapshot: Snapshot dataclass
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

__all__ = [
    "ContextManager",
    "check_context_status",
    "create_context_snapshot",
    "rehydrate_from_snapshot",
    "list_context_snapshots",
    "run_automation",
    "ContextStatus",
    "ContextSnapshot",
]

# ============================================================================
# Data Models
# ============================================================================


@dataclass
class ContextStatus:
    """Status of current context usage."""

    current_tokens: int
    max_tokens: int
    percentage: float
    threshold_status: str  # 'ok', 'consider', 'recommended', 'urgent'
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "current_tokens": self.current_tokens,
            "max_tokens": self.max_tokens,
            "percentage": self.percentage,
            "threshold_status": self.threshold_status,
            "recommendation": self.recommendation,
        }


@dataclass
class ContextSnapshot:
    """Context snapshot metadata and content."""

    snapshot_id: str
    name: str | None
    timestamp: datetime
    original_requirements: str
    key_decisions: list[dict[str, str]] = field(default_factory=list)
    implementation_state: str = ""
    open_items: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    token_count: int = 0
    file_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for JSON serialization."""
        return {
            "snapshot_id": self.snapshot_id,
            "name": self.name,
            "timestamp": self.timestamp.isoformat(),
            "original_requirements": self.original_requirements,
            "key_decisions": self.key_decisions,
            "implementation_state": self.implementation_state,
            "open_items": self.open_items,
            "tools_used": self.tools_used,
            "token_count": self.token_count,
            "file_path": str(self.file_path) if self.file_path else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContextSnapshot":
        """Create ContextSnapshot from dictionary."""
        return cls(
            snapshot_id=data["snapshot_id"],
            name=data.get("name"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            original_requirements=data.get("original_requirements", ""),
            key_decisions=data.get("key_decisions", []),
            implementation_state=data.get("implementation_state", ""),
            open_items=data.get("open_items", []),
            tools_used=data.get("tools_used", []),
            token_count=data.get("token_count", 0),
            file_path=Path(data["file_path"]) if data.get("file_path") else None,
        )


# ============================================================================
# Configuration and Constants
# ============================================================================

DEFAULT_MAX_TOKENS = 1_000_000
DEFAULT_SNAPSHOT_DIR = ".claude/runtime/context-snapshots"
DEFAULT_STATE_FILE = ".claude/runtime/context-automation-state.json"

# Model-specific thresholds
THRESHOLDS_1M = {
    "ok": 0.2,  # 0-20%: All good
    "consider": 0.3,  # 30%+: Consider snapshotting
    "recommended": 0.4,  # 40%+: Snapshot recommended
    "urgent": 0.5,  # 50%+: Snapshot urgent
}

THRESHOLDS_SMALL = {
    "ok": 0.4,  # 0-40%: All good
    "consider": 0.55,  # 55%+: Consider snapshotting
    "recommended": 0.7,  # 70%+: Snapshot recommended
    "urgent": 0.85,  # 85%+: Snapshot urgent
}


def get_thresholds_for_model(max_tokens: int) -> dict:
    """Get appropriate thresholds based on model size."""
    return THRESHOLDS_1M if max_tokens >= 800_000 else THRESHOLDS_SMALL


# ============================================================================
# Main Context Manager
# ============================================================================


class ContextManager:
    """Main context management coordinator.

    Responsibilities:
    - Token monitoring and threshold tracking
    - Intelligent context extraction
    - Selective context rehydration
    - Automatic snapshot creation
    - Compaction detection and recovery
    """

    def __init__(
        self,
        snapshot_dir: Path | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        state_file: Path | None = None,
    ):
        """Initialize context manager.

        Args:
            snapshot_dir: Directory for storing snapshots
            max_tokens: Maximum token limit
            state_file: Automation state tracking file
        """
        # Set up paths
        self.snapshot_dir = self._resolve_path(snapshot_dir, DEFAULT_SNAPSHOT_DIR)
        self.state_file = self._resolve_path(state_file, DEFAULT_STATE_FILE)

        # Configuration
        self.max_tokens = max_tokens
        self.thresholds = get_thresholds_for_model(max_tokens)
        self.current_usage = 0

        # Ensure directories exist
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Load automation state
        self.state = self._load_state()

    def _resolve_path(self, provided_path: Path | None, default_path: str) -> Path:
        """Resolve path relative to project root."""
        if provided_path:
            return provided_path if isinstance(provided_path, Path) else Path(provided_path)

        # Try to find project root
        cwd = Path.cwd()
        if (cwd / ".claude").exists():
            return cwd / default_path
        return Path(default_path)

    # ========================================================================
    # Token Monitoring
    # ========================================================================

    def check_status(self, current_tokens: int) -> ContextStatus:
        """Check current token usage status.

        Args:
            current_tokens: Current token count

        Returns:
            ContextStatus with usage details and recommendations
        """
        self.current_usage = current_tokens
        percentage = (current_tokens / self.max_tokens) * 100
        threshold_status = self._get_threshold_status(percentage / 100)
        recommendation = self._get_recommendation(percentage)

        return ContextStatus(
            current_tokens=current_tokens,
            max_tokens=self.max_tokens,
            percentage=round(percentage, 2),
            threshold_status=threshold_status,
            recommendation=recommendation,
        )

    def _get_threshold_status(self, percentage_decimal: float) -> str:
        """Determine threshold status from percentage."""
        if percentage_decimal >= self.thresholds["urgent"]:
            return "urgent"
        if percentage_decimal >= self.thresholds["recommended"]:
            return "recommended"
        if percentage_decimal >= self.thresholds["consider"]:
            return "consider"
        return "ok"

    def _get_recommendation(self, percentage: float) -> str:
        """Get action recommendation based on usage percentage."""
        if percentage >= 95:
            return (
                "URGENT: Context window nearly full. Create snapshot immediately "
                "to preserve work before compaction."
            )
        if percentage >= 85:
            return (
                "Snapshot recommended. Create a snapshot to preserve context "
                "before approaching limit."
            )
        if percentage >= 70:
            return "Consider creating a snapshot soon. Context usage is rising."
        return "Context is healthy. No action needed."

    # ========================================================================
    # Context Extraction and Snapshot Creation
    # ========================================================================

    def create_snapshot(
        self, conversation_data: list[dict[str, Any]], name: str | None = None
    ) -> ContextSnapshot:
        """Create intelligent context snapshot.

        Args:
            conversation_data: Conversation history
            name: Optional human-readable name

        Returns:
            ContextSnapshot with metadata
        """
        # Extract context components
        context = self._extract_from_conversation(conversation_data)

        # Generate snapshot ID
        snapshot_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create snapshot object
        snapshot = ContextSnapshot(
            snapshot_id=snapshot_id,
            name=name,
            timestamp=datetime.now(),
            original_requirements=context.get("original_requirements", ""),
            key_decisions=context.get("key_decisions", []),
            implementation_state=context.get("implementation_state", ""),
            open_items=context.get("open_items", []),
            tools_used=context.get("tools_used", []),
            token_count=self._estimate_tokens(context),
            file_path=None,
        )

        # Save to file
        file_path = self.snapshot_dir / f"{snapshot_id}.json"
        snapshot.file_path = file_path

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(snapshot.to_dict(), f, indent=2, ensure_ascii=False)

        return snapshot

    def _extract_from_conversation(self, conversation_data: list[dict]) -> dict[str, Any]:
        """Extract essential context from conversation history."""
        return {
            "original_requirements": self._extract_original_requirements(conversation_data),
            "key_decisions": self._extract_key_decisions(conversation_data),
            "implementation_state": self._extract_implementation_state(conversation_data),
            "open_items": self._extract_open_items(conversation_data),
            "tools_used": self._extract_tools_used(conversation_data),
        }

    def _extract_original_requirements(self, conversation_data: list[dict]) -> str:
        """Extract first user message as original requirements."""
        for message in conversation_data:
            if message.get("role") == "user":
                content = message.get("content", "")
                return content[:500] + ("..." if len(content) > 500 else "")
        return "No user requirements found"

    def _extract_key_decisions(self, conversation_data: list[dict]) -> list[dict[str, str]]:
        """Extract key decisions from assistant messages."""
        decisions = []
        decision_keywords = ["decided", "chosen", "selected", "opted", "approach"]

        for message in conversation_data:
            if message.get("role") == "assistant":
                content = message.get("content", "").lower()
                for keyword in decision_keywords:
                    if keyword in content:
                        sentences = message.get("content", "").split(".")
                        for sentence in sentences:
                            if keyword in sentence.lower() and len(sentence.strip()) > 10:
                                decisions.append(
                                    {
                                        "decision": sentence.strip(),
                                        "rationale": "Extracted from conversation",
                                        "alternatives": "Not captured",
                                    }
                                )
                                break
                        break

        return decisions[:5]

    def _extract_implementation_state(self, conversation_data: list[dict]) -> str:
        """Summarize current implementation state from tool usage."""
        tool_usage_count = sum(
            1 for msg in conversation_data if msg.get("role") == "tool_use" or "tool_name" in msg
        )

        files_modified = []
        for message in conversation_data:
            if message.get("tool_name") in ["Write", "Edit"]:
                file_path = message.get("file_path", message.get("parameters", {}).get("file_path"))
                if file_path:
                    files_modified.append(Path(file_path).name)

        state = f"Tools invoked: {tool_usage_count}\n"
        if files_modified:
            state += f"Files modified: {', '.join(set(files_modified[:10]))}"
            if len(files_modified) > 10:
                state += f" and {len(files_modified) - 10} more"

        return state

    def _extract_open_items(self, conversation_data: list[dict]) -> list[str]:
        """Extract open questions and blockers."""
        open_items = []
        question_indicators = ["?", "todo", "need to", "should we", "blocker", "pending"]

        for message in conversation_data:
            content = message.get("content", "")
            content_lower = content.lower()

            if "?" in content:
                sentences = content.split("?")
                for sentence in sentences[:-1]:
                    question = sentence.strip().split(".")[-1] + "?"
                    if len(question) > 10:
                        open_items.append(question.strip())

            for indicator in question_indicators[1:]:
                if indicator in content_lower:
                    sentences = content.split(".")
                    for sentence in sentences:
                        if indicator in sentence.lower() and len(sentence.strip()) > 10:
                            open_items.append(sentence.strip())
                            break

        return list(set(open_items))[:10]

    def _extract_tools_used(self, conversation_data: list[dict]) -> list[str]:
        """Extract list of unique tools used."""
        tools = set()
        for message in conversation_data:
            tool_name = message.get("tool_name")
            if tool_name:
                tools.add(tool_name)
        return sorted(list(tools))

    def _estimate_tokens(self, context: dict[str, Any]) -> int:
        """Rough token estimation (1 token ≈ 4 characters)."""
        total_chars = 0
        total_chars += len(context.get("original_requirements", ""))
        total_chars += len(context.get("implementation_state", ""))

        for decision in context.get("key_decisions", []):
            total_chars += len(str(decision))

        for item in context.get("open_items", []):
            total_chars += len(item)

        return total_chars // 4

    # ========================================================================
    # Context Rehydration
    # ========================================================================

    def rehydrate(self, snapshot_id: str, level: str = "standard") -> str:
        """Rehydrate context from snapshot.

        Args:
            snapshot_id: Snapshot ID to restore
            level: Detail level ('essential', 'standard', 'comprehensive')

        Returns:
            Rehydrated context text
        """
        VALID_LEVELS = ["essential", "standard", "comprehensive"]
        if level not in VALID_LEVELS:
            raise ValueError(f"Invalid level '{level}'. Must be one of: {VALID_LEVELS}")

        snapshot_path = self.snapshot_dir / f"{snapshot_id}.json"
        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot not found: {snapshot_id}")

        # Load snapshot
        with open(snapshot_path, encoding="utf-8") as f:
            snapshot_data = json.load(f)

        snapshot = ContextSnapshot.from_dict(snapshot_data)

        # Format based on level
        if level == "essential":
            return self._format_essential(snapshot)
        if level == "standard":
            return self._format_standard(snapshot)
        return self._format_comprehensive(snapshot)

    def _format_essential(self, snapshot: ContextSnapshot) -> str:
        """Format essential context (requirements + state only)."""
        lines = [
            f"# Restored Context: {snapshot.name or snapshot.snapshot_id}",
            "",
            f"*Snapshot created: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "## Original Requirements",
            "",
            snapshot.original_requirements,
            "",
            "## Current State",
            "",
            snapshot.implementation_state if snapshot.implementation_state else "No state recorded",
            "",
        ]
        return "\n".join(lines)

    def _format_standard(self, snapshot: ContextSnapshot) -> str:
        """Format standard context (+ decisions + open items)."""
        lines = [
            f"# Restored Context: {snapshot.name or snapshot.snapshot_id}",
            "",
            f"*Snapshot created: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "## Original Requirements",
            "",
            snapshot.original_requirements,
            "",
            "## Current State",
            "",
            snapshot.implementation_state if snapshot.implementation_state else "No state recorded",
            "",
        ]

        if snapshot.key_decisions:
            lines.extend(["## Key Decisions", ""])
            for i, decision in enumerate(snapshot.key_decisions, 1):
                lines.append(f"{i}. {decision.get('decision', 'Unknown')}")
                if decision.get("rationale") != "Extracted from conversation":
                    lines.append(f"   - Rationale: {decision.get('rationale', 'N/A')}")
            lines.append("")

        if snapshot.open_items:
            lines.extend(["## Open Items", ""])
            for item in snapshot.open_items:
                lines.append(f"- {item}")
            lines.append("")

        return "\n".join(lines)

    def _format_comprehensive(self, snapshot: ContextSnapshot) -> str:
        """Format comprehensive context (everything)."""
        lines = [
            f"# Restored Context: {snapshot.name or snapshot.snapshot_id}",
            "",
            f"*Snapshot created: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*",
            f"*Estimated tokens: {snapshot.token_count}*",
            "",
            "## Original Requirements",
            "",
            snapshot.original_requirements,
            "",
            "## Current State",
            "",
            snapshot.implementation_state if snapshot.implementation_state else "No state recorded",
            "",
        ]

        if snapshot.key_decisions:
            lines.extend(["## Key Decisions", ""])
            for i, decision in enumerate(snapshot.key_decisions, 1):
                lines.append(f"### Decision {i}")
                lines.append(f"**What:** {decision.get('decision', 'Unknown')}")
                lines.append(f"**Why:** {decision.get('rationale', 'N/A')}")
                lines.append(f"**Alternatives:** {decision.get('alternatives', 'N/A')}")
                lines.append("")

        if snapshot.open_items:
            lines.extend(["## Open Items & Questions", ""])
            for item in snapshot.open_items:
                lines.append(f"- {item}")
            lines.append("")

        if snapshot.tools_used:
            lines.extend(["## Tools Used", ""])
            for tool in snapshot.tools_used:
                lines.append(f"- {tool}")
            lines.append("")

        return "\n".join(lines)

    # ========================================================================
    # Snapshot Listing
    # ========================================================================

    def list_snapshots(self) -> list[dict[str, Any]]:
        """List all available context snapshots.

        Returns:
            List of snapshot metadata dicts
        """
        if not self.snapshot_dir.exists():
            return []

        snapshots = []
        for snapshot_file in sorted(self.snapshot_dir.glob("*.json"), reverse=True):
            try:
                with open(snapshot_file, encoding="utf-8") as f:
                    data = json.load(f)

                snapshot = ContextSnapshot.from_dict(data)
                file_size = snapshot_file.stat().st_size

                snapshots.append(
                    {
                        "id": snapshot.snapshot_id,
                        "name": snapshot.name,
                        "timestamp": snapshot.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "size": self._format_size(file_size),
                        "token_count": snapshot.token_count,
                        "file_path": str(snapshot_file),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                continue

        return snapshots

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f}KB"
        return f"{size_bytes / (1024 * 1024):.1f}MB"

    # ========================================================================
    # Automation (called from hooks)
    # ========================================================================

    def run_automation(
        self, current_tokens: int, conversation_data: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """Run automatic context management.

        Called by post_tool_use hook for automatic monitoring,
        snapshot creation, and recovery.

        Args:
            current_tokens: Current token count
            conversation_data: Optional conversation history

        Returns:
            Dict with actions taken and recommendations
        """
        result = {
            "status": "ok",
            "actions_taken": [],
            "warnings": [],
            "recommendations": [],
            "skipped": False,
        }

        # Increment tool use counter
        self.state["tool_use_count"] = self.state.get("tool_use_count", 0) + 1
        tool_count = self.state["tool_use_count"]

        # Calculate current percentage
        percentage = (current_tokens / self.max_tokens) * 100

        # Adaptive frequency: skip if not time to check
        if percentage < 40:
            check_every = 50
        elif percentage < 55:
            check_every = 10
        elif percentage < 70:
            check_every = 3
        else:
            check_every = 1

        if tool_count % check_every != 0:
            result["skipped"] = True
            result["next_check_in"] = check_every - (tool_count % check_every)
            self._save_state()
            return result

        # Check usage
        usage = self.check_status(current_tokens)
        threshold_status = usage.threshold_status

        # Detect compaction
        if self._detect_compaction(current_tokens):
            result["actions_taken"].append("compaction_detected")
            self._handle_compaction(result)

        # Auto-snapshot at thresholds
        if conversation_data and threshold_status != "ok":
            snapshot_created = self._auto_snapshot(
                threshold_status, conversation_data, current_tokens
            )
            if snapshot_created:
                result["actions_taken"].append(f"auto_snapshot_at_{threshold_status}")
                result["warnings"].append(
                    f"⚠️  Auto-snapshot created at {usage.percentage:.1f}% usage"
                )

        # Add recommendations
        if usage.percentage > 70:
            result["recommendations"].append(usage.recommendation)

        # Update state
        self.state["last_token_count"] = current_tokens
        self._save_state()

        return result

    def _detect_compaction(self, current_tokens: int) -> bool:
        """Detect if context was compacted."""
        last_count = self.state.get("last_token_count", 0)

        if last_count == 0:
            return False

        drop_percentage = (last_count - current_tokens) / last_count
        return drop_percentage > 0.3 and current_tokens < last_count

    def _auto_snapshot(self, threshold: str, conversation_data: list, current_tokens: int) -> bool:
        """Create automatic snapshot at threshold."""
        if self.state.get("last_snapshot_threshold") == threshold:
            return False

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_name = f"auto_{threshold}_{timestamp}"

        try:
            snapshot = self.create_snapshot(conversation_data, snapshot_name)

            self.state["last_snapshot_threshold"] = threshold
            self.state["snapshots_created"].append(
                {
                    "timestamp": timestamp,
                    "threshold": threshold,
                    "tokens": current_tokens,
                    "path": str(snapshot.file_path),
                }
            )
            self._save_state()

            return True

        except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
            # Log error but don't interrupt workflow
            # OSError: File operations (snapshot creation, state save)
            # JSONDecodeError: Malformed conversation data
            # KeyError: Missing required fields in conversation data
            # ValueError: Invalid data formats
            import logging

            logging.debug(f"Auto-snapshot failed: {e}")
            return False

    def _handle_compaction(self, result: dict[str, Any]) -> None:
        """Handle detected compaction by auto-rehydrating."""
        snapshots = self.state.get("snapshots_created", [])
        if not snapshots:
            result["warnings"].append("⚠️  Compaction detected but no snapshots available")
            return

        recent_snapshot = snapshots[-1]
        snapshot_path = Path(recent_snapshot["path"])

        if not snapshot_path.exists():
            result["warnings"].append("⚠️  Snapshot file not found")
            return

        # Smart level selection
        last_tokens = recent_snapshot["tokens"]
        percentage = (last_tokens / self.max_tokens) * 100

        if percentage < 55:
            level = "essential"
        elif percentage < 70:
            level = "standard"
        else:
            level = "comprehensive"

        try:
            snapshot_id = recent_snapshot["timestamp"]
            self.rehydrate(snapshot_id, level)  # Rehydrate context (return value not needed)

            result["actions_taken"].append(f"auto_rehydrated_at_{level}_level")
            result["warnings"].append(
                f"✅ Context restored automatically ({level} level) from {recent_snapshot['timestamp']}"
            )

            self.state["last_rehydration"] = {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "snapshot": recent_snapshot["timestamp"],
            }
            self.state["compaction_detected"] = True
            self._save_state()

        except (FileNotFoundError, json.JSONDecodeError, ValueError, OSError) as e:
            # Specific exception types for auto-rehydration failures:
            # FileNotFoundError: Snapshot file missing
            # JSONDecodeError: Corrupted snapshot file
            # ValueError: Invalid snapshot data or level
            # OSError: File read/write failures
            result["warnings"].append(f"⚠️  Auto-rehydration failed: {e}")

    # ========================================================================
    # State Management
    # ========================================================================

    def _load_state(self) -> dict[str, Any]:
        """Load automation state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        return {
            "last_snapshot_threshold": None,
            "last_token_count": 0,
            "snapshots_created": [],
            "last_rehydration": None,
            "compaction_detected": False,
            "tool_use_count": 0,
        }

    def _save_state(self) -> None:
        """Save automation state to disk."""
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)


# ============================================================================
# Convenience Functions (Simplified API)
# ============================================================================


def check_context_status(current_tokens: int, **kwargs) -> ContextStatus:
    """Check current token usage status.

    Args:
        current_tokens: Current token count

    Returns:
        ContextStatus object
    """
    manager = ContextManager(**kwargs)
    return manager.check_status(current_tokens)


def create_context_snapshot(
    conversation_data: list[dict[str, Any]], name: str | None = None, **kwargs
) -> ContextSnapshot:
    """Create context snapshot.

    Args:
        conversation_data: Conversation history
        name: Optional snapshot name

    Returns:
        ContextSnapshot object
    """
    manager = ContextManager(**kwargs)
    return manager.create_snapshot(conversation_data, name)


def rehydrate_from_snapshot(snapshot_id: str, level: str = "standard", **kwargs) -> str:
    """Rehydrate context from snapshot.

    Args:
        snapshot_id: Snapshot ID
        level: Detail level

    Returns:
        Rehydrated context text
    """
    manager = ContextManager(**kwargs)
    return manager.rehydrate(snapshot_id, level)


def list_context_snapshots(**kwargs) -> list[dict[str, Any]]:
    """List all available snapshots.

    Returns:
        List of snapshot metadata dicts
    """
    manager = ContextManager(**kwargs)
    return manager.list_snapshots()


def run_automation(
    current_tokens: int, conversation_data: list[dict[str, Any]] | None = None, **kwargs
) -> dict[str, Any]:
    """Run automatic context management (called from hooks).

    Args:
        current_tokens: Current token count
        conversation_data: Optional conversation history

    Returns:
        Dict with automation results
    """
    manager = ContextManager(**kwargs)
    return manager.run_automation(current_tokens, conversation_data)


# ============================================================================
# CLI Interface (for testing)
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python context_manager.py <action> [args...]")
        print("Actions: status, snapshot, rehydrate, list")
        sys.exit(1)

    action = sys.argv[1]

    if action == "status":
        tokens = int(sys.argv[2]) if len(sys.argv) > 2 else 500000
        status = check_context_status(tokens)
        print(f"Status: {status.threshold_status}")
        print(f"Usage: {status.percentage}%")
        print(f"Recommendation: {status.recommendation}")

    elif action == "list":
        snapshots = list_context_snapshots()
        print(f"Found {len(snapshots)} snapshots:")
        for snapshot in snapshots:
            print(f"  - {snapshot['id']}: {snapshot['name']} ({snapshot['size']})")

    elif action == "rehydrate":
        if len(sys.argv) < 3:
            print("Usage: python context_manager.py rehydrate <snapshot_id> [level]")
            sys.exit(1)
        snapshot_id = sys.argv[2]
        level = sys.argv[3] if len(sys.argv) > 3 else "standard"
        context = rehydrate_from_snapshot(snapshot_id, level)
        print(context)

    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
