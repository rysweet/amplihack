"""Quality checks mixin - checks for code quality and philosophy compliance."""

import re

# Constants for quality checks
MAX_ASK_USER_COUNT = 3
MIN_SHORTCUT_USAGE_COUNT = 10

# Pre-compiled patterns for _check_shortcuts (avoids re-compilation on every call)
_SHORTCUT_PATTERNS = [
    re.compile(r"\bpass\b.*#.*\blater\b", re.IGNORECASE),
    re.compile(r"#.*\bhack\b", re.IGNORECASE),
    re.compile(r"#.*\bworkaround\b", re.IGNORECASE),
    re.compile(r"#.*\btemporary\b", re.IGNORECASE),
    re.compile(r"#.*\bfix\b.*\blater\b", re.IGNORECASE),
]

# Pre-compiled patterns for _check_philosophy_compliance
_TODO_FIXME_PATTERN = re.compile(r"\b(TODO|FIXME|XXX)\b")
_STUB_INLINE_PATTERN = re.compile(
    r"def\s+\w+\([^)]*\)(?:\s*->.*?)?:\s*(?:pass|\.\.\.)\s*$", re.MULTILINE
)
_STUB_MULTILINE_PATTERN = re.compile(
    r"def\s+\w+\([^)]*\)(?:\s*->.*?)?:\s*\n\s+(?:pass|\.\.\.)\s*$", re.MULTILINE
)
_ABC_CLASS_PATTERN = re.compile(r"class\s+\w+\(.*\bABC\b")


class ChecksQualityMixin:
    """Mixin with code quality and philosophy compliance check methods."""

    # File extensions where TODO/FIXME/stubs are acceptable (docs, config, YAML)
    NON_CODE_EXTENSIONS = [".md", ".txt", ".rst", ".yml", ".yaml", ".json", ".toml", ".cfg", ".ini"]

    def _check_philosophy_compliance(self, transcript: list[dict], session_id: str) -> bool:
        """Check for PHILOSOPHY adherence (zero-BS).

        Heuristics:
        - Look for "TODO", "FIXME", "XXX" in Write/Edit tool calls to CODE files
        - Check for stub implementations (NotImplementedError, pass)
        - Detect placeholder comments
        - Skip documentation, YAML, and config files where these words may
          appear legitimately (e.g., YAML questions mentioning TODO, docs
          explaining the philosophy)

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if compliant, False otherwise
        """
        # Check Write and Edit tool calls for anti-patterns
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_name = block.get("name", "")
                            if tool_name in ["Write", "Edit"]:
                                tool_input = block.get("input", {})
                                file_path = tool_input.get("file_path", "")

                                # Skip non-code files (docs, YAML, config) where
                                # TODO/FIXME may appear legitimately
                                if any(file_path.endswith(ext) for ext in self.NON_CODE_EXTENSIONS):
                                    continue

                                file_path_lower = file_path.lower()
                                # Skip test files — they may contain TODO/NotImplementedError
                                # as test data or assertion targets, not as actual stubs
                                is_test_file = (
                                    "/test/" in file_path_lower
                                    or "/tests/" in file_path_lower
                                    or file_path_lower.split("/")[-1].startswith("test_")
                                )

                                # Check content for anti-patterns
                                content_to_check = ""
                                if "content" in tool_input:
                                    content_to_check = str(tool_input["content"])
                                elif "new_string" in tool_input:
                                    content_to_check = str(tool_input["new_string"])

                                # Look for TODO/FIXME/XXX (skip test files where these
                                # may appear as test data or assertion strings)
                                if not is_test_file and _TODO_FIXME_PATTERN.search(
                                    content_to_check
                                ):
                                    return False

                                # Look for NotImplementedError (skip test files where
                                # this appears in pytest.raises assertions)
                                if not is_test_file and "NotImplementedError" in content_to_check:
                                    return False

                                # Look for stub patterns (with optional -> return type):
                                # - Single-line: def f(): pass / def f() -> None: pass
                                # - Multi-line:  def f():\n    pass
                                # - Ellipsis:    def f(): ... / def f() -> int: ...
                                # Skip if @abstractmethod context detected (legitimate pattern)
                                # Use specific ABC patterns to avoid false matches on
                                # "ABC Corp", "ABC123", etc. (Issue: round 4 audit D4)
                                content_lower = content_to_check.lower()
                                has_abstract = (
                                    "@abstractmethod" in content_to_check
                                    or "from abc import" in content_lower
                                    or "import abc" in content_lower
                                    or _ABC_CLASS_PATTERN.search(content_to_check)
                                )
                                if not has_abstract:
                                    if _STUB_INLINE_PATTERN.search(content_to_check):
                                        return False
                                    if _STUB_MULTILINE_PATTERN.search(content_to_check):
                                        return False

        return True

    @staticmethod
    def _is_meaningful_validation(command: str) -> bool:
        """Check if a python -c or node -e command does meaningful validation.

        Rejects trivial commands like print('hello') and accepts commands that
        import modules, open files, parse data, or run actual validation logic.

        Args:
            command: The full Bash command string

        Returns:
            True if the command appears to do real validation
        """
        validation_signals = [
            "import ",
            "from ",
            "open(",
            "load(",
            "parse(",
            "validate",
            "check",
            "assert",
            "yaml",
            "json",
            "safe_load",
            "read_text",
            "read()",
        ]
        cmd_lower = command.lower()
        return any(signal in cmd_lower for signal in validation_signals)

    def _check_local_testing(self, transcript: list[dict], session_id: str) -> bool:
        """Check if agent tested locally.

        Heuristics:
        - Look for Bash tool calls with pytest, npm test, cargo test, etc.
        - Check exit codes (0 = success)
        - Look for "PASSED" or "OK" in output

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if tests run and passed, False otherwise
        """
        # Build O(1) lookup: tool_use_id → Bash command (avoids O(n²) inner scan)
        bash_tool_uses: dict[str, str] = {}
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if (
                            isinstance(block, dict)
                            and block.get("type") == "tool_use"
                            and block.get("name") == "Bash"
                            and block.get("id")
                        ):
                            bash_tool_uses[block["id"]] = block.get("input", {}).get("command", "")

        # Look for test execution in tool results — O(n) with pre-indexed map
        for msg in transcript:
            if msg.get("type") == "tool_result" and "message" in msg:
                msg_data = msg["message"]
                tool_use_id = msg_data.get("tool_use_id")
                if tool_use_id and tool_use_id in bash_tool_uses:
                    command = bash_tool_uses[tool_use_id]
                    if any(pattern in command for pattern in self.TEST_COMMAND_PATTERNS):
                        # Check result content for pass indicators
                        result_content = msg_data.get("content", [])
                        if isinstance(result_content, list):
                            for result_block in result_content:
                                if (
                                    isinstance(result_block, dict)
                                    and result_block.get("type") == "tool_result"
                                ):
                                    output = str(result_block.get("content", ""))
                                    if "PASSED" in output or "passed" in output:
                                        return True
                                    if "OK" in output and "FAILED" not in output:
                                        return True
                        # Also check msg_data content directly (some formats nest differently)
                        direct_content = msg_data.get("content", "")
                        if isinstance(direct_content, str):
                            if "PASSED" in direct_content or "passed" in direct_content:
                                return True
                            if "OK" in direct_content and "FAILED" not in direct_content:
                                return True

        # Also accept validation commands (ruff, mypy, etc.) as testing
        # for sessions where formal test suites don't exist or aren't applicable
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "Bash":
                                command = block.get("input", {}).get("command", "")
                                # Accept linting/type-checking tools directly
                                if any(
                                    pattern in command
                                    for pattern in self.VALIDATION_COMMAND_PATTERNS
                                ):
                                    return True
                                # Accept python -c / node -e only if they do
                                # meaningful validation (not just print('hello'))
                                if any(
                                    pattern in command
                                    for pattern in self.INLINE_VALIDATION_PATTERNS
                                ) and self._is_meaningful_validation(command):
                                    return True

        # No tests or validation found
        return False

    def _check_agent_unnecessary_questions(self, transcript: list[dict], session_id: str) -> bool:
        """Check if agent asked unnecessary questions instead of proceeding.

        Detects questions that could have been inferred from context.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if no unnecessary questions, False otherwise
        """
        # Count questions asked by assistant (question marks in text)
        assistant_questions = 0
        for msg in transcript:
            if msg.get("type") == "assistant":
                content = msg.get("message", {}).get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = str(block.get("text", ""))
                            # Count question marks in assistant responses
                            assistant_questions += text.count("?")

        # Heuristic: If assistant asked more than 3 questions, might be excessive
        if assistant_questions > MAX_ASK_USER_COUNT:
            return False

        return True

    def _check_objective_completion(self, transcript: list[dict], session_id: str) -> bool:
        """Check if original user objective was fully accomplished.

        Looks for completion indicators in later messages.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if objective appears complete, False otherwise
        """
        # Get first user message (the objective)
        first_user_msg = None
        for msg in transcript:
            if msg.get("type") == "user":
                first_user_msg = msg
                break

        if not first_user_msg:
            return True  # No objective to check

        # Look for completion indicators in assistant messages
        completion_indicators = [
            "complete",
            "finished",
            "done",
            "implemented",
            "successfully",
            "all tests pass",
            "pr created",
            "pr ready",
            "pushed to",
            "merged",
            "no bug",
            "no issue found",
            "not a bug",
            "as expected",
            "by design",
            "no changes needed",
        ]

        for msg in reversed(transcript[-10:]):  # Check last 10 messages
            if msg.get("type") == "assistant":
                content = msg.get("message", {}).get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = str(block.get("text", "")).lower()
                            if any(indicator in text for indicator in completion_indicators):
                                return True

        # Also check for structural completion: PR creation or git push
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "Bash":
                                command = block.get("input", {}).get("command", "")
                                if "gh pr create" in command or "git push" in command:
                                    return True

        return False  # No completion indicators found

    def _check_shortcuts(self, transcript: list[dict], session_id: str) -> bool:
        """Check if any quality shortcuts were taken.

        Identifies compromises like skipped error handling or incomplete validation.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if no shortcuts, False if compromises detected
        """
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_name = block.get("name", "")
                            if tool_name in ["Write", "Edit"]:
                                tool_input = block.get("input", {})
                                content_to_check = str(tool_input.get("content", "")) + str(
                                    tool_input.get("new_string", "")
                                )

                                # Check for shortcut patterns (module-level compiled)
                                for pattern in _SHORTCUT_PATTERNS:
                                    if pattern.search(content_to_check):
                                        return False

        return True

    def _check_interactive_testing(self, transcript: list[dict], session_id: str) -> bool:
        """Check if agent tested interactively beyond automated tests.

        Looks for manual verification, edge case testing, UI validation.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if interactive testing done, False if only automated tests
        """
        # Look for interactive testing indicators in assistant messages
        interactive_keywords = [
            "manually tested",
            "manually verified",
            "tried it",
            "verified the output",
            "checked the result",
            "confirmed it works",
            "validated the behavior",
            "tested end-to-end",
            "ran the command",
            "tested with real",
        ]

        for msg in transcript:
            if msg.get("type") == "assistant":
                content = msg.get("message", {}).get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = str(block.get("text", "")).lower()
                            if any(keyword in text for keyword in interactive_keywords):
                                return True

        # Also accept if automated tests show a substantial passing count.
        # Use regex to find patterns like "N passed" or "N tests passed"
        # instead of naively counting occurrences of "passed" and "ok".
        for msg in transcript:
            if msg.get("type") == "tool_result":
                output = str(msg.get("message", {}).get("content", ""))
                # Match pytest-style "N passed" or "N tests passed"
                import re as _re
                match = _re.search(r"(\d+)\s+passed", output, _re.IGNORECASE)
                if match:
                    count = int(match.group(1))
                    if count >= MIN_SHORTCUT_USAGE_COUNT:
                        return True

        return False

    def _check_unrelated_changes(self, transcript: list[dict], session_id: str) -> bool:
        """Check if there are unrelated changes in PR.

        Detects scope creep and unrelated modifications.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if no unrelated changes, False if scope creep detected
        """
        # Check files modified
        files_modified = []
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") in ["Write", "Edit"]:
                                file_path = block.get("input", {}).get("file_path", "")
                                files_modified.append(file_path.lower())

        # Heuristic: If more than 20 files modified, might have scope creep
        if len(files_modified) > 20:
            return False

        return True

    def _check_root_pollution(self, transcript: list[dict], session_id: str) -> bool:
        """Check if PR polluted project root with new files.

        Flags new top-level files that should be in subdirectories.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if no root pollution, False if new top-level files added
        """
        # Check for new files in project root
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "Write":
                                file_path = block.get("input", {}).get("file_path", "")

                                # Check if file is in root (only one path component)
                                path_parts = file_path.strip("/").split("/")
                                if len(path_parts) == 1:
                                    # New file in root - check if it's acceptable
                                    filename = path_parts[0].lower()
                                    acceptable_root_files = [
                                        "readme",
                                        "license",
                                        "makefile",
                                        "dockerfile",
                                        ".gitignore",
                                        ".gitattributes",
                                        ".dockerignore",
                                        ".editorconfig",
                                        ".env.example",
                                        "setup.py",
                                        "setup.cfg",
                                        "pyproject.toml",
                                        "requirements.txt",
                                        "package.json",
                                        "tsconfig.json",
                                        "cargo.toml",
                                        "go.mod",
                                        "docker-compose",
                                        "justfile",
                                        "claude.md",
                                        ".pre-commit",
                                        "conftest.py",
                                        "pytest.ini",
                                        "manifest.in",
                                    ]

                                    if not any(
                                        acceptable in filename
                                        for acceptable in acceptable_root_files
                                    ):
                                        return False

        return True
