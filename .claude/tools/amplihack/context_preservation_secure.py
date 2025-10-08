#!/usr/bin/env python3
"""
Context Preservation System - amplihack Style with Security Enhancements
Preserves original user requests and conversation context to prevent loss during compaction.

SECURITY FEATURES:
- Input size validation (max 50KB)
- Regex timeout protection (1 second)
- Input sanitization using whitelist approach
- Memory usage limits to prevent DoS
- Comprehensive error handling for malformed input
"""

import html
import json
import re
import signal
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional

# Use clean import through dedicated paths module
from paths import get_project_root

try:
    from amplihack.utils.paths import FrameworkPathResolver
except ImportError:
    FrameworkPathResolver = None


class SecurityConfig:
    """Security configuration for input validation and regex protection."""

    # Input size limits
    MAX_INPUT_SIZE = 50 * 1024  # 50KB maximum input
    MAX_LINE_LENGTH = 1000  # Maximum line length
    MAX_SENTENCES = 100  # Maximum sentences to process
    MAX_BULLETS = 20  # Maximum bullet points to extract
    MAX_REQUIREMENTS = 10  # Maximum requirements to extract
    MAX_CONSTRAINTS = 5  # Maximum constraints to extract
    MAX_CRITERIA = 5  # Maximum success criteria to extract

    # Regex timeout protection
    REGEX_TIMEOUT = 1.0  # 1 second timeout for regex operations

    # Allowed characters (whitelist approach)
    ALLOWED_CHARS = set(
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        " \t\n\r"
        ".,!?;:"
        "()[]{}"
        "\"'\\-_"
        "*\u2022-"
        "#@$%&+=<>/\\|`~"
    )


class RegexTimeoutError(Exception):
    """Raised when regex operation times out."""


class InputValidationError(Exception):
    """Raised when input validation fails."""


class SecurityValidator:
    """Handles input validation and sanitization for regex DoS protection."""

    @staticmethod
    def validate_input_size(text: str) -> str:
        """Validate input size limits to prevent memory exhaustion.

        Args:
            text: Input text to validate

        Returns:
            Validated text

        Raises:
            InputValidationError: If input exceeds size limits
        """
        if not isinstance(text, str):
            raise InputValidationError("Input must be a string")

        if len(text) > SecurityConfig.MAX_INPUT_SIZE:
            raise InputValidationError(
                f"Input size ({len(text)} bytes) exceeds maximum allowed "
                f"({SecurityConfig.MAX_INPUT_SIZE} bytes)"
            )

        # Check for excessively long lines that could cause issues
        lines = text.split("\n")
        for i, line in enumerate(lines[:100]):  # Check first 100 lines only
            if len(line) > SecurityConfig.MAX_LINE_LENGTH:
                raise InputValidationError(
                    f"Line {i + 1} length ({len(line)}) exceeds maximum "
                    f"({SecurityConfig.MAX_LINE_LENGTH})"
                )

        return text

    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize input text using whitelist approach to prevent injection.

        Args:
            text: Input text to sanitize

        Returns:
            Sanitized text with only allowed characters
        """
        # Normalize unicode to prevent encoding attacks
        text = unicodedata.normalize("NFKC", text)

        # Remove characters not in whitelist
        sanitized_chars = []
        for char in text:
            if char in SecurityConfig.ALLOWED_CHARS:
                sanitized_chars.append(char)
            else:
                # Replace with space for readability
                sanitized_chars.append(" ")

        # Clean up multiple spaces
        sanitized = "".join(sanitized_chars)
        sanitized = re.sub(r"\s+", " ", sanitized)

        return sanitized.strip()

    @staticmethod
    def safe_regex_finditer(pattern: str, text: str, flags: int = 0, max_matches: int = 100):
        """Safely execute regex finditer with timeout protection.

        Args:
            pattern: Regex pattern
            text: Text to search
            flags: Regex flags
            max_matches: Maximum number of matches to return

        Returns:
            List of matches (limited)

        Raises:
            RegexTimeoutError: If regex times out
        """

        def timeout_handler(signum, frame):
            raise RegexTimeoutError(
                f"Regex operation timed out after {SecurityConfig.REGEX_TIMEOUT}s"
            )

        # Set up timeout (Unix/Linux/macOS only)
        old_handler = None
        try:
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(SecurityConfig.REGEX_TIMEOUT))

            matches = []
            for i, match in enumerate(re.finditer(pattern, text, flags)):
                if i >= max_matches:
                    break
                matches.append(match)
            return matches
        except AttributeError:
            # Windows doesn't have SIGALRM, fallback without timeout
            matches = []
            for i, match in enumerate(re.finditer(pattern, text, flags)):
                if i >= max_matches:
                    break
                matches.append(match)
            return matches
        finally:
            # Reset alarm
            try:
                signal.alarm(0)
                if old_handler is not None:
                    signal.signal(signal.SIGALRM, old_handler)
            except AttributeError:
                pass  # Windows doesn't support signal.alarm

    @staticmethod
    def safe_regex_search(pattern: str, text: str, flags: int = 0):
        """Safely execute regex search with timeout protection.

        Args:
            pattern: Regex pattern
            text: Text to search
            flags: Regex flags

        Returns:
            Match object or None

        Raises:
            RegexTimeoutError: If regex times out
        """

        def timeout_handler(signum, frame):
            raise RegexTimeoutError(
                f"Regex operation timed out after {SecurityConfig.REGEX_TIMEOUT}s"
            )

        # Set up timeout (Unix/Linux/macOS only)
        old_handler = None
        try:
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(SecurityConfig.REGEX_TIMEOUT))
            return re.search(pattern, text, flags)
        except AttributeError:
            # Windows doesn't have SIGALRM, fallback without timeout
            return re.search(pattern, text, flags)
        finally:
            # Reset alarm
            try:
                signal.alarm(0)
                if old_handler is not None:
                    signal.signal(signal.SIGALRM, old_handler)
            except AttributeError:
                pass  # Windows doesn't support signal.alarm

    @staticmethod
    def safe_regex_findall(pattern: str, text: str, flags: int = 0, max_matches: int = 100):
        """Safely execute regex findall with timeout protection.

        Args:
            pattern: Regex pattern
            text: Text to search
            flags: Regex flags
            max_matches: Maximum number of matches to return

        Returns:
            List of matches (limited)

        Raises:
            RegexTimeoutError: If regex times out
        """

        def timeout_handler(signum, frame):
            raise RegexTimeoutError(
                f"Regex operation timed out after {SecurityConfig.REGEX_TIMEOUT}s"
            )

        # Set up timeout (Unix/Linux/macOS only)
        old_handler = None
        try:
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(SecurityConfig.REGEX_TIMEOUT))
            matches = re.findall(pattern, text, flags)
            return matches[:max_matches]  # Limit results
        except AttributeError:
            # Windows doesn't have SIGALRM, fallback without timeout
            matches = re.findall(pattern, text, flags)
            return matches[:max_matches]  # Limit results
        finally:
            # Reset alarm
            try:
                signal.alarm(0)
                if old_handler is not None:
                    signal.signal(signal.SIGALRM, old_handler)
            except AttributeError:
                pass  # Windows doesn't support signal.alarm

    @staticmethod
    def safe_split(text: str, pattern: str, max_splits: int = 1000) -> List[str]:
        """Safely split text with limits to prevent DoS.

        Args:
            text: Text to split
            pattern: Split pattern
            max_splits: Maximum number of splits

        Returns:
            List of split strings (limited)
        """
        try:
            # Use safe regex split with timeout
            def timeout_handler(signum, frame):
                raise RegexTimeoutError(
                    f"Split operation timed out after {SecurityConfig.REGEX_TIMEOUT}s"
                )

            old_handler = None
            try:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(SecurityConfig.REGEX_TIMEOUT))
                parts = re.split(pattern, text)
                return parts[:max_splits]  # Limit results
            except AttributeError:
                # Windows doesn't have SIGALRM, fallback without timeout
                parts = re.split(pattern, text)
                return parts[:max_splits]  # Limit results
            finally:
                # Reset alarm
                try:
                    signal.alarm(0)
                    if old_handler is not None:
                        signal.signal(signal.SIGALRM, old_handler)
                except AttributeError:
                    pass  # Windows doesn't support signal.alarm
        except RegexTimeoutError:
            # Fallback to simple string split for basic patterns
            if pattern in ["\n", ".", "!", "?"]:
                return text.split(pattern)[:max_splits]
            raise


class ContextPreserver:
    """Handles preservation and retrieval of conversation context and original requests.

    Security Features:
    - Input size validation (max 50KB)
    - Regex timeout protection (1 second)
    - Input sanitization using whitelist approach
    - Memory usage limits to prevent DoS
    - Comprehensive error handling for malformed input
    """

    def __init__(self, session_id: Optional[str] = None):
        """Initialize context preserver.

        Args:
            session_id: Optional session ID. If not provided, generates one from timestamp.
        """
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.project_root = get_project_root()
        self.session_dir = self.project_root / ".claude" / "runtime" / "logs" / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def extract_original_request(self, prompt: str) -> Dict[str, Any]:
        """Extract and structure original user requirements from initial prompt.

        Args:
            prompt: The initial user prompt/request

        Returns:
            Structured original request data

        Raises:
            InputValidationError: If input validation fails
            RegexTimeoutError: If regex operations timeout
        """
        try:
            # Security: Validate input size and sanitize
            prompt = SecurityValidator.validate_input_size(prompt)
            prompt = SecurityValidator.sanitize_input(prompt)

            # Clean the prompt
            prompt = prompt.strip()

            if not prompt:
                raise InputValidationError("Empty prompt after sanitization")

        except (InputValidationError, RegexTimeoutError) as e:
            # Log security event but don't expose details to user
            error_msg = f"Input validation failed: {type(e).__name__}"
            return {
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "raw_prompt": "[INVALID INPUT - SANITIZED]",
                "target": "Security validation failed",
                "requirements": ["Input validation failed"],
                "constraints": ["Security constraints enforced"],
                "success_criteria": ["Valid input required"],
                "word_count": 0,
                "char_count": 0,
                "extracted_at": datetime.now().isoformat(),
                "security_error": error_msg,
            }
        except Exception:
            # Unexpected error - fail securely
            return {
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "raw_prompt": "[ERROR - SANITIZED]",
                "target": "Processing failed",
                "requirements": ["Error handling"],
                "constraints": ["Security constraints enforced"],
                "success_criteria": ["Valid processing required"],
                "word_count": 0,
                "char_count": 0,
                "extracted_at": datetime.now().isoformat(),
                "processing_error": "Unexpected error occurred",
            }

        # Extract explicit requirements using patterns
        requirements = self._parse_requirements(prompt)

        # Extract constraints
        constraints = self._parse_constraints(prompt)

        # Extract success criteria
        success_criteria = self._parse_success_criteria(prompt)

        # Extract target/goal
        target = self._parse_target(prompt)

        original_request = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "raw_prompt": prompt,
            "target": target,
            "requirements": requirements,
            "constraints": constraints,
            "success_criteria": success_criteria,
            "word_count": len(prompt.split()),
            "char_count": len(prompt),
            "extracted_at": datetime.now().isoformat(),
        }

        # Save to session logs
        self._save_original_request(original_request)

        return original_request

    def _parse_requirements(self, prompt: str) -> List[str]:
        """Parse explicit requirements from prompt with security protections.

        Args:
            prompt: Sanitized prompt text

        Returns:
            List of extracted requirements (limited to prevent DoS)
        """
        requirements = []

        try:
            # Extract marked sections first - using safe regex
            pattern = r"\*\*(Target|Problem)\*\*:\s*(.+?)(?:\n|$)"
            matches = SecurityValidator.safe_regex_finditer(
                pattern, prompt, re.IGNORECASE, max_matches=10
            )
            for match in matches:
                req_text = f"{match.group(1).upper()}: {match.group(2).strip()}"
                if len(req_text) <= 500:  # Limit requirement length
                    requirements.append(req_text)

            # Extract quantified statements (ALL, EVERY, etc.) - with limits
            quantifier_words = ["ALL", "EVERY", "EACH", "COMPLETE", "COMPREHENSIVE"]
            sentences = SecurityValidator.safe_split(
                prompt, r"[.!?\n]+", max_splits=SecurityConfig.MAX_SENTENCES
            )

            for sentence in sentences[: SecurityConfig.MAX_SENTENCES]:
                sentence = sentence.strip()
                if (
                    len(sentence) > 10
                    and len(sentence) <= 500
                    and any(word in sentence.upper() for word in quantifier_words)
                ):
                    if (
                        sentence not in requirements
                        and len(requirements) < SecurityConfig.MAX_REQUIREMENTS
                    ):
                        requirements.append(sentence)

            # Extract bullet points - with safe regex and limits
            bullet_pattern = r"[-\u2022*]\s*([^\n]+)"
            bullets = SecurityValidator.safe_regex_findall(
                bullet_pattern, prompt, max_matches=SecurityConfig.MAX_BULLETS
            )

            for bullet in bullets:
                bullet = bullet.strip()
                if (
                    len(bullet) > 5
                    and len(bullet) <= 500
                    and bullet not in requirements
                    and len(requirements) < SecurityConfig.MAX_REQUIREMENTS
                ):
                    requirements.append(bullet)

        except (RegexTimeoutError, Exception):
            # If regex fails, add a fallback requirement
            requirements.append("[Requirements extraction failed - manual review needed]")

        return requirements[: SecurityConfig.MAX_REQUIREMENTS]

    def _parse_constraints(self, prompt: str) -> List[str]:
        """Parse constraints from prompt with security protections.

        Args:
            prompt: Sanitized prompt text

        Returns:
            List of extracted constraints (limited to prevent DoS)
        """
        constraints = []

        try:
            # Extract marked constraints - using safe regex
            constraint_pattern = r"\*\*Constraints?\*\*:\s*(.+?)(?:\n|$)"
            constraint_match = SecurityValidator.safe_regex_search(
                constraint_pattern, prompt, re.IGNORECASE
            )
            if constraint_match:
                constraint_text = constraint_match.group(1).strip()
                if len(constraint_text) <= 500:  # Limit constraint length
                    constraints.append(constraint_text)

            # Extract negative statements - with limits
            negative_patterns = ["must not", "cannot", "avoid", "limitation", "restriction"]
            sentences = SecurityValidator.safe_split(
                prompt, r"[.!?\n]+", max_splits=SecurityConfig.MAX_SENTENCES
            )

            for sentence in sentences[: SecurityConfig.MAX_SENTENCES]:
                sentence = sentence.strip()
                if (
                    any(pattern in sentence.lower() for pattern in negative_patterns)
                    and len(sentence) > 5
                    and len(sentence) <= 500
                    and sentence not in constraints
                    and len(constraints) < SecurityConfig.MAX_CONSTRAINTS
                ):
                    constraints.append(sentence)

        except (RegexTimeoutError, Exception):
            # If regex fails, add a fallback constraint
            constraints.append("[Constraints extraction failed - manual review needed]")

        return constraints[: SecurityConfig.MAX_CONSTRAINTS]

    def _parse_success_criteria(self, prompt: str) -> List[str]:
        """Parse success criteria from prompt with security protections.

        Args:
            prompt: Sanitized prompt text

        Returns:
            List of extracted success criteria (limited to prevent DoS)
        """
        criteria = []

        try:
            # Simple pattern matching for common success indicators
            success_patterns = ["success criteria", "acceptance criteria", "goal", "outcome"]

            # Safe split with limits
            lines = prompt.split("\n")[:100]  # Limit lines processed

            for line in lines:
                line = line.strip()
                if (
                    len(line) <= 500  # Limit line length
                    and any(pattern in line.lower() for pattern in success_patterns)
                    and ":" in line
                ):
                    parts = line.split(":", 1)
                    if (
                        len(parts) > 1
                        and len(parts[1].strip()) > 5
                        and len(parts[1].strip()) <= 500
                        and len(criteria) < SecurityConfig.MAX_CRITERIA
                    ):
                        criteria.append(parts[1].strip())

        except Exception:
            # If processing fails, add a fallback criterion
            criteria.append("[Success criteria extraction failed - manual review needed]")

        return criteria[: SecurityConfig.MAX_CRITERIA]

    def _parse_target(self, prompt: str) -> str:
        """Parse the main target/goal from prompt with security protections.

        Args:
            prompt: Sanitized prompt text

        Returns:
            Target string (length limited for security)
        """
        try:
            # Check for explicit target - using safe regex
            target_pattern = r"\*\*Target\*\*:\s*(.+?)(?:\n|$)"
            target_match = SecurityValidator.safe_regex_search(
                target_pattern, prompt, re.IGNORECASE
            )
            if target_match:
                target_text = target_match.group(1).strip()
                if len(target_text) <= 200:  # Limit target length
                    return target_text

            # Use first substantial sentence with action words
            action_words = ["implement", "create", "build", "add", "fix", "update", "improve"]
            sentences = SecurityValidator.safe_split(prompt, r"[.!?]+", max_splits=10)[:3]

            for sentence in sentences:
                sentence = sentence.strip()
                if (
                    len(sentence) > 15
                    and len(sentence) <= 200
                    and any(word in sentence.lower() for word in action_words)
                ):
                    return sentence

            # Fallback to first non-empty sentence
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 10 and len(sentence) <= 200:
                    return sentence

        except (RegexTimeoutError, Exception):
            # If parsing fails, return safe fallback
            pass

        return "General development task"

    def _save_original_request(self, original_request: Dict[str, Any]):
        """Save original request to session logs with HTML escaping for security."""
        request_file = self.session_dir / "ORIGINAL_REQUEST.md"

        # Escape HTML to prevent injection in markdown
        escaped_prompt = html.escape(original_request["raw_prompt"])
        escaped_target = html.escape(original_request["target"])

        content = f"""# Original User Request

**Session**: {self.session_id}
**Timestamp**: {original_request["timestamp"]}
**Target**: {escaped_target}

## Raw Request
```
{escaped_prompt}
```

## Extracted Requirements
"""

        for i, req in enumerate(original_request["requirements"], 1):
            escaped_req = html.escape(req)
            content += f"{i}. {escaped_req}\n"

        if original_request["constraints"]:
            content += "\n## Constraints\n"
            for i, constraint in enumerate(original_request["constraints"], 1):
                escaped_constraint = html.escape(constraint)
                content += f"{i}. {escaped_constraint}\n"

        if original_request["success_criteria"]:
            content += "\n## Success Criteria\n"
            for i, criterion in enumerate(original_request["success_criteria"], 1):
                escaped_criterion = html.escape(criterion)
                content += f"{i}. {escaped_criterion}\n"

        content += f"""
## Metadata
- Word count: {original_request["word_count"]}
- Character count: {original_request["char_count"]}
- Extracted at: {original_request["extracted_at"]}

## Security Notes
- Input validated and sanitized for security
- All content escaped to prevent injection attacks
- Regex operations protected with timeouts

## Usage Notes
This file preserves the original user requirements to prevent loss during context compaction.
All agents should receive this context to ensure user requirements are preserved throughout the workflow.
"""

        with open(request_file, "w") as f:
            f.write(content)

        # Also save as JSON for programmatic access
        json_file = self.session_dir / "original_request.json"
        with open(json_file, "w") as f:
            json.dump(original_request, f, indent=2)

    def get_original_request(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve original request for a session.

        Args:
            session_id: Session ID to retrieve. Uses current session if not provided.

        Returns:
            Original request data or None if not found
        """
        target_session_id = session_id or self.session_id
        json_file = (
            self.project_root
            / ".claude"
            / "runtime"
            / "logs"
            / target_session_id
            / "original_request.json"
        )

        if not json_file.exists():
            return None

        try:
            with open(json_file) as f:
                return json.load(f)
        except Exception:
            return None

    def format_agent_context(self, original_request: Optional[Dict[str, Any]] = None) -> str:
        """Format original request as context for agent injection.

        Args:
            original_request: Original request data. Retrieves current session if not provided.

        Returns:
            Formatted context string for agent injection
        """
        if not original_request:
            original_request = self.get_original_request()

        if not original_request:
            return ""

        # Escape content for security
        escaped_target = html.escape(original_request["target"])

        context_parts = [
            "## 🎯 ORIGINAL USER REQUEST - PRESERVE THESE REQUIREMENTS",
            "",
            f"**Target**: {escaped_target}",
            "",
        ]

        if original_request["requirements"]:
            context_parts.append("**Requirements**:")
            for req in original_request["requirements"]:
                escaped_req = html.escape(req)
                context_parts.append(f"• {escaped_req}")
            context_parts.append("")

        if original_request["constraints"]:
            context_parts.append("**Constraints**:")
            for constraint in original_request["constraints"]:
                escaped_constraint = html.escape(constraint)
                context_parts.append(f"• {escaped_constraint}")
            context_parts.append("")

        if original_request["success_criteria"]:
            context_parts.append("**Success Criteria**:")
            for criterion in original_request["success_criteria"]:
                escaped_criterion = html.escape(criterion)
                context_parts.append(f"• {escaped_criterion}")
            context_parts.append("")

        context_parts.extend(
            [
                "**CRITICAL**: These are the user's explicit requirements. Do NOT optimize them away.",
                "Your solution must address ALL requirements while following the constraints.",
                "━" * 60,
            ]
        )

        return "\n".join(context_parts)

    def export_conversation_transcript(self, conversation_data: List[Dict[str, Any]]) -> str:
        """Export complete conversation transcript (Amplifier-style).

        Args:
            conversation_data: List of conversation messages/interactions

        Returns:
            Path to exported transcript file
        """
        transcript_file = self.session_dir / "CONVERSATION_TRANSCRIPT.md"

        content = [
            f"# Conversation Transcript - Session {self.session_id}",
            "",
            f"**Exported**: {datetime.now().isoformat()}",
            f"**Messages**: {len(conversation_data)}",
            "",
            "━" * 80,
            "",
        ]

        for i, message in enumerate(conversation_data, 1):
            timestamp = message.get("timestamp", "Unknown")
            role = message.get("role", "Unknown")
            text = message.get("text", message.get("content", ""))

            # Escape HTML for security
            escaped_role = html.escape(role.upper())
            escaped_timestamp = html.escape(str(timestamp))
            escaped_text = html.escape(text)

            content.append(f"## Message {i} - {escaped_role}")
            content.append(f"**Timestamp**: {escaped_timestamp}")
            content.append("")
            content.append(escaped_text)
            content.append("")
            content.append("─" * 40)
            content.append("")

        transcript_content = "\n".join(content)

        with open(transcript_file, "w") as f:
            f.write(transcript_content)

        return str(transcript_file)

    def get_latest_session_id(self) -> Optional[str]:
        """Get the most recent session ID with security protections."""
        try:
            logs_dir = self.project_root / ".claude" / "runtime" / "logs"
            if not logs_dir.exists():
                return None

            # Safe regex pattern for session ID validation
            session_pattern = r"\d{8}_\d{6}"
            session_dirs = []

            # Limit directory scanning to prevent DoS
            dir_count = 0
            for d in logs_dir.iterdir():
                if dir_count >= 1000:  # Limit number of directories scanned
                    break
                dir_count += 1

                if d.is_dir():
                    try:
                        # Use safe regex matching with timeout
                        if SecurityValidator.safe_regex_search(session_pattern, d.name):
                            session_dirs.append(d)
                    except RegexTimeoutError:
                        continue  # Skip this directory if regex times out

            if not session_dirs:
                return None

            return sorted(session_dirs)[-1].name

        except Exception:
            # Fail securely - return None if any error occurs
            return None


def create_context_preserver(session_id: Optional[str] = None) -> ContextPreserver:
    """Factory function to create a ContextPreserver instance."""
    return ContextPreserver(session_id)


# Example usage for testing
if __name__ == "__main__":
    # Test with sample prompt
    sample_prompt = """
Implement conversation transcript and original request preservation for amplihack.

**Target**: Context preservation system for original user requirements
**Problem**: Original user requests get lost during context compaction and aren't consistently passed to subagents
**Constraints**: Simple implementation based on Amplifier's proven approach

## Required Implementation

### 1. **Original Request Extraction & Preservation**
- Extract explicit user requirements from initial request
- Store in structured format accessible to all agents
- Include in `.claude/runtime/logs/<session_id>/ORIGINAL_REQUEST.md`
"""

    preserver = ContextPreserver()
    original_request = preserver.extract_original_request(sample_prompt)
    print("Original request extracted and saved!")
    print(f"Session ID: {preserver.session_id}")
    print(f"Target: {original_request['target']}")
    print(f"Requirements: {len(original_request['requirements'])}")

    # Test agent context formatting
    agent_context = preserver.format_agent_context(original_request)
    print("\nAgent context preview:")
    print(agent_context[:200] + "...")
