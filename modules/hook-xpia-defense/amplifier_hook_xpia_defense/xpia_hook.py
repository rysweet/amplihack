"""XPIA Defense Hook Implementation.

Simplified cross-prompt injection attack detection hook for Amplifier.
Monitors tool calls and user prompts for injection patterns.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Severity level of detected threats."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def __lt__(self, other: "ThreatLevel") -> bool:
        """Compare threat levels by severity."""
        order = [
            ThreatLevel.NONE,
            ThreatLevel.LOW,
            ThreatLevel.MEDIUM,
            ThreatLevel.HIGH,
            ThreatLevel.CRITICAL,
        ]
        return order.index(self) < order.index(other)

    def __le__(self, other: "ThreatLevel") -> bool:
        return self == other or self < other

    def __gt__(self, other: "ThreatLevel") -> bool:
        return not self <= other

    def __ge__(self, other: "ThreatLevel") -> bool:
        return not self < other


class HookAction(Enum):
    """Action the hook recommends."""

    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class ThreatMatch:
    """A detected threat pattern match."""

    pattern_name: str
    level: ThreatLevel
    description: str
    matched_text: str
    category: str


@dataclass
class HookResult:
    """Result from hook execution.

    Follows Amplifier hook contract:
    - action: What the system should do (allow, warn, block)
    - message: Human-readable message about the result
    - threats: List of detected threats (if any)
    - metadata: Additional data for logging/debugging
    """

    action: HookAction
    message: str
    threats: list[ThreatMatch] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def should_block(self) -> bool:
        """Whether the content should be blocked."""
        return self.action == HookAction.BLOCK

    @property
    def should_warn(self) -> bool:
        """Whether a warning should be issued."""
        return self.action in (HookAction.WARN, HookAction.BLOCK)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "action": self.action.value,
            "message": self.message,
            "should_block": self.should_block,
            "threats": [
                {
                    "pattern": t.pattern_name,
                    "level": t.level.value,
                    "description": t.description,
                    "category": t.category,
                }
                for t in self.threats
            ],
            "metadata": self.metadata,
        }


# Threat pattern definitions - simplified from original
# Format: (pattern_name, regex, level, description, category)
THREAT_PATTERNS: list[tuple[str, str, ThreatLevel, str, str]] = [
    # Critical: System prompt override attempts
    (
        "ignore_instructions",
        r"(?i)ignore\s+(?:all\s+)?(?:previous\s+)?instructions?",
        ThreatLevel.CRITICAL,
        "Attempt to ignore system instructions",
        "system_override",
    ),
    (
        "forget_above",
        r"(?i)forget\s+(?:everything\s+)?(?:above|before|prior)",
        ThreatLevel.CRITICAL,
        "Attempt to forget previous context",
        "system_override",
    ),
    (
        "disregard_prompt",
        r"(?i)disregard\s+(?:all\s+)?(?:previous\s+)?(?:instructions?|prompts?)",
        ThreatLevel.CRITICAL,
        "Attempt to disregard instructions",
        "system_override",
    ),
    (
        "new_instructions",
        r"(?i)(?:new|updated|revised)\s+(?:system\s+)?instructions?(?:\s*:|$)",
        ThreatLevel.CRITICAL,
        "Attempt to inject new instructions",
        "system_override",
    ),
    # High: Role manipulation
    (
        "role_change",
        r"(?i)you\s+are\s+now\s+(?:a\s+)?(?!analyzing|reviewing|working|looking)",
        ThreatLevel.HIGH,
        "Attempt to change agent role",
        "role_manipulation",
    ),
    (
        "act_as",
        r"(?i)act\s+as\s+(?:a\s+)?(?!if|though)",
        ThreatLevel.HIGH,
        "Role play injection attempt",
        "role_manipulation",
    ),
    (
        "pretend_to_be",
        r"(?i)pretend\s+(?:to\s+be|you\s+are)",
        ThreatLevel.HIGH,
        "Pretend/impersonation attempt",
        "role_manipulation",
    ),
    # High: Information extraction
    (
        "reveal_prompt",
        r"(?i)(?:reveal|show|display|print|output)\s+(?:your\s+)?(?:system\s+)?prompt",
        ThreatLevel.HIGH,
        "Attempt to extract system prompt",
        "data_exfiltration",
    ),
    (
        "show_instructions",
        r"(?i)(?:what\s+are|tell\s+me|show)\s+your\s+(?:original\s+)?instructions",
        ThreatLevel.HIGH,
        "Attempt to extract instructions",
        "data_exfiltration",
    ),
    (
        "reveal_secrets",
        r"(?i)(?:reveal|show|tell).*(?:api\s+keys?|passwords?|tokens?|credentials?|secrets?)",
        ThreatLevel.CRITICAL,
        "Attempt to extract secrets",
        "data_exfiltration",
    ),
    # Critical: Dangerous commands (for tool:call:before)
    (
        "destructive_rm",
        r"rm\s+-rf\s*[/\\]",
        ThreatLevel.CRITICAL,
        "Destructive rm -rf command",
        "command_injection",
    ),
    (
        "curl_to_shell",
        r"curl\s+.*\|\s*(?:bash|sh|zsh)",
        ThreatLevel.CRITICAL,
        "Curl piped to shell execution",
        "command_injection",
    ),
    (
        "wget_to_shell",
        r"wget\s+.*\|\s*(?:bash|sh|zsh)",
        ThreatLevel.CRITICAL,
        "Wget piped to shell execution",
        "command_injection",
    ),
    # Medium: Security bypass attempts
    (
        "bypass_security",
        r"(?i)(?:bypass|skip|disable|turn\s+off)\s+(?:security|validation|checks?)",
        ThreatLevel.MEDIUM,
        "Attempt to bypass security",
        "privilege_escalation",
    ),
    (
        "ignore_safety",
        r"(?i)(?:ignore|skip)\s+(?:safety|protection|filtering)",
        ThreatLevel.MEDIUM,
        "Attempt to ignore safety measures",
        "privilege_escalation",
    ),
]

# Compiled patterns for performance
_COMPILED_PATTERNS: list[tuple[str, re.Pattern[str], ThreatLevel, str, str]] = []


def _compile_patterns() -> None:
    """Compile regex patterns on first use."""
    global _COMPILED_PATTERNS
    if _COMPILED_PATTERNS:
        return

    for name, pattern, level, desc, category in THREAT_PATTERNS:
        try:
            compiled = re.compile(pattern)
            _COMPILED_PATTERNS.append((name, compiled, level, desc, category))
        except re.error as e:
            logger.warning(f"Failed to compile pattern {name}: {e}")


class XPIADefenseHook:
    """Cross-Prompt Injection Attack defense hook.

    Monitors tool calls and user prompts for injection attempts.

    Operating modes:
        - standard: Block critical, warn on high/medium
        - strict: Block critical and high, warn on medium
        - learning: Log all, block none (analysis mode)

    Config options:
        - mode: Operating mode (default: 'standard')
        - block_on_critical: Block critical threats (default: True)
        - log_all: Log all checks, not just threats (default: False)
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the XPIA defense hook.

        Args:
            config: Configuration options
        """
        self._config = config or {}
        self._mode = self._config.get("mode", "standard")
        self._block_on_critical = self._config.get("block_on_critical", True)
        self._log_all = self._config.get("log_all", False)

        # Compile patterns on init
        _compile_patterns()

    @property
    def name(self) -> str:
        """Hook name for identification."""
        return "xpia-defense"

    def __call__(self, event: str, data: dict[str, Any]) -> HookResult:
        """Execute the hook for an event.

        This is the main Amplifier hook contract method.

        Args:
            event: Event name (e.g., 'tool:call:before', 'prompt:submit:before')
            data: Event data dictionary

        Returns:
            HookResult with action, message, and any detected threats
        """
        # Extract content based on event type
        content = self._extract_content(event, data)

        if not content:
            return HookResult(
                action=HookAction.ALLOW,
                message="No content to analyze",
                metadata={"event": event},
            )

        # Scan for threats
        threats = self._scan_content(content)

        if not threats:
            if self._log_all:
                logger.debug(f"XPIA check passed for {event}")
            return HookResult(
                action=HookAction.ALLOW,
                message="No threats detected",
                metadata={"event": event, "content_length": len(content)},
            )

        # Determine action based on mode and threat levels
        action = self._determine_action(threats)
        message = self._build_message(threats, action)

        # Log the detection
        logger.warning(f"XPIA threats detected in {event}: {message}")

        return HookResult(
            action=action,
            message=message,
            threats=threats,
            metadata={
                "event": event,
                "mode": self._mode,
                "threat_count": len(threats),
                "max_level": max(t.level.value for t in threats),
            },
        )

    def _extract_content(self, event: str, data: dict[str, Any]) -> str:
        """Extract content to analyze from event data.

        Args:
            event: Event name
            data: Event data

        Returns:
            Content string to analyze
        """
        if event == "tool:call:before":
            # For tool calls, check the tool input/arguments
            tool_input = data.get("input", {})
            if isinstance(tool_input, dict):
                # Concatenate all string values
                parts = []
                for key, value in tool_input.items():
                    if isinstance(value, str):
                        parts.append(value)
                    elif isinstance(value, list):
                        parts.extend(str(v) for v in value if isinstance(v, str))
                return " ".join(parts)
            return str(tool_input)

        elif event == "prompt:submit:before":
            # For prompts, check the user's input
            return data.get("content", "") or data.get("prompt", "")

        # Generic fallback
        return data.get("content", "") or data.get("text", "")

    def _scan_content(self, content: str) -> list[ThreatMatch]:
        """Scan content for threat patterns.

        Args:
            content: Content to scan

        Returns:
            List of matched threats
        """
        threats: list[ThreatMatch] = []

        for name, pattern, level, desc, category in _COMPILED_PATTERNS:
            match = pattern.search(content)
            if match:
                threats.append(
                    ThreatMatch(
                        pattern_name=name,
                        level=level,
                        description=desc,
                        matched_text=match.group(0)[:100],  # Truncate for safety
                        category=category,
                    )
                )

        return threats

    def _determine_action(self, threats: list[ThreatMatch]) -> HookAction:
        """Determine action based on threats and mode.

        Args:
            threats: List of detected threats

        Returns:
            Recommended action
        """
        if not threats:
            return HookAction.ALLOW

        max_level = max(t.level for t in threats)

        # Learning mode: always allow, just log
        if self._mode == "learning":
            return HookAction.WARN

        # Strict mode: block high and above
        if self._mode == "strict":
            if max_level in (ThreatLevel.CRITICAL, ThreatLevel.HIGH):
                return HookAction.BLOCK if self._block_on_critical else HookAction.WARN
            if max_level == ThreatLevel.MEDIUM:
                return HookAction.WARN
            return HookAction.ALLOW

        # Standard mode (default): block critical only
        if max_level == ThreatLevel.CRITICAL:
            return HookAction.BLOCK if self._block_on_critical else HookAction.WARN
        if max_level in (ThreatLevel.HIGH, ThreatLevel.MEDIUM):
            return HookAction.WARN
        return HookAction.ALLOW

    def _build_message(self, threats: list[ThreatMatch], action: HookAction) -> str:
        """Build human-readable message about threats.

        Args:
            threats: List of detected threats
            action: Determined action

        Returns:
            Message string
        """
        if not threats:
            return "No threats detected"

        threat_summary = ", ".join(f"{t.category}:{t.level.value}" for t in threats[:3])
        if len(threats) > 3:
            threat_summary += f" (+{len(threats) - 3} more)"

        action_text = {
            HookAction.ALLOW: "Allowed",
            HookAction.WARN: "Warning",
            HookAction.BLOCK: "Blocked",
        }[action]

        return f"{action_text}: {threat_summary}"
