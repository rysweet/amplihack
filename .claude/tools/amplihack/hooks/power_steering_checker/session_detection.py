"""Session detection mixin - classifies session type from transcript."""

import os
from typing import Any

# Threshold for question density to classify as INFORMATIONAL session
QA_QUESTION_DENSITY_THRESHOLD = 0.5


class SessionDetectionMixin:
    """Mixin with session type detection methods."""

    # File extension constants for session type detection
    CODE_FILE_EXTENSIONS = [
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".java",
        ".go",
        ".rs",
        ".c",
        ".cpp",
        ".h",
    ]
    DOC_FILE_EXTENSIONS = [".md", ".txt", ".rst", "readme", "changelog"]
    CONFIG_FILE_EXTENSIONS = [".yml", ".yaml", ".json"]
    TEST_COMMAND_PATTERNS = [
        "pytest",
        "npm test",
        "cargo test",
        "go test",
        "python -m pytest",
        "python -m unittest",
        "uvx --from",  # Outside-in package testing (user-mandated)
        "uvx --from git+",  # Outside-in from branch
    ]
    # Broader validation patterns (config checks, smoke tests, linting)
    # Note: python -c requires an additional content check (must contain
    # import/open/load/parse/validate) to avoid accepting trivial no-ops
    # like python -c "print('hello')". See _is_meaningful_validation().
    VALIDATION_COMMAND_PATTERNS = [
        "ruff check",  # Linting
        "mypy",  # Type checking
        "flake8",  # Linting
    ]
    # These patterns require content validation via _is_meaningful_validation()
    INLINE_VALIDATION_PATTERNS = [
        "python -c",  # Inline validation (YAML, imports, smoke tests)
        "node -e",  # Inline JS validation
    ]

    # Keywords that indicate simple housekeeping tasks (skip power-steering)
    # When found in user messages, session is classified as SIMPLE and most
    # considerations are skipped. These are routine maintenance tasks.
    SIMPLE_TASK_KEYWORDS = [
        "cleanup",
        "clean up",
        "fetch",
        "git fetch",
        "git pull",
        "pull latest",
        "sync",
        "update branch",
        "rebase",
        "git rebase",
        "merge main",
        "merge master",
        "merge pr",
        "merge the pr",
        "merge this pr",
        "merge it",
        "review pr",
        "review the pr",
        "review and merge",
        "approve and merge",
        "workspace",
        "stash",
        "git stash",
        "discard changes",
        "reset",
        "checkout",
        "switch branch",
        "list files",
        "show status",
        "git status",
        "what's changed",
        "what changed",
    ]

    # Keywords that indicate PM/Operations/Planning sessions (fixes #2913/#2914)
    # When found in early user messages, session is classified as OPERATIONS.
    # These sessions involve reading data (backlogs, issues, roadmaps) to produce
    # planning output - they do NOT require development workflow checks.
    # Checked BEFORE investigation tool-usage heuristics to prevent misclassification.
    OPERATIONS_KEYWORDS = [
        "prioritize",
        "prioritise",
        "backlog",
        "roadmap",
        "sprint",
        "triage",
        "pm-architect",
        "project management",
        "project manager",
        "product management",
        "product manager",
        "milestone",
        "epic",
        "user story",
        "release plan",
        "capacity planning",
        "scrum",
        "kanban",
        "planning session",
        "prioritization",
        "work items",
        "what should we work on",
        "what to work on",
        "what should i work on",
        "next steps",
        "determine next steps",
        "survey the project",
    ]

    # Keywords that indicate investigation/troubleshooting sessions
    # When found in early user messages, session is classified as INVESTIGATION
    # regardless of tool usage patterns (fixes #1604)
    #
    # Note: Using substring matching, so shorter forms match longer variants:
    # - "troubleshoot" matches "troubleshooting"
    # - "diagnos" matches "diagnose", "diagnosis", "diagnosing"
    # - "debug" matches "debugging"
    INVESTIGATION_KEYWORDS = [
        "investigate",
        "troubleshoot",
        "diagnos",  # matches diagnose, diagnosis, diagnosing
        "analyze",
        "analyse",
        "research",
        "explore",
        "understand",
        "figure out",
        "why does",
        "why is",
        "how does",
        "how is",
        "what causes",
        "what's causing",
        "root cause",
        "debug",
        "explain",
    ]

    def _has_development_indicators(
        self,
        code_files_modified: bool,
        test_executions: int,
        pr_dev_operations: bool,
    ) -> bool:
        """Check if transcript shows development indicators.

        Args:
            code_files_modified: Whether code files were modified
            test_executions: Number of test executions
            pr_dev_operations: Whether PR creation/edit operations were performed
                (PR view/merge/review are ops, not development signals)

        Returns:
            True if development indicators present
        """
        return code_files_modified or test_executions > 0 or pr_dev_operations

    def _has_informational_indicators(
        self,
        write_edit_operations: int,
        read_grep_operations: int,
        question_count: int,
        user_messages: list[dict],
    ) -> bool:
        """Check if transcript shows informational session indicators.

        Args:
            write_edit_operations: Number of Write/Edit operations
            read_grep_operations: Number of Read/Grep operations
            question_count: Number of questions in user messages
            user_messages: List of user message dicts

        Returns:
            True if informational indicators present
        """
        # No tool usage or only Read tools with high question density
        if write_edit_operations == 0:
            if read_grep_operations <= 1 and question_count > 0:
                # High question density indicates INFORMATIONAL
                if (
                    user_messages
                    and question_count / len(user_messages) > QA_QUESTION_DENSITY_THRESHOLD
                ):
                    return True
        return False

    def _has_maintenance_indicators(
        self,
        write_edit_operations: int,
        doc_files_only: bool,
        git_operations: bool,
        code_files_modified: bool,
    ) -> bool:
        """Check if transcript shows maintenance indicators.

        Args:
            write_edit_operations: Number of Write/Edit operations
            doc_files_only: Whether only doc files were modified
            git_operations: Whether git operations were performed
            code_files_modified: Whether code files were modified

        Returns:
            True if maintenance indicators present
        """
        # Only doc/config files modified
        if write_edit_operations > 0 and doc_files_only:
            return True

        # Git operations without code changes
        if git_operations and not code_files_modified and write_edit_operations == 0:
            return True

        return False

    def _has_investigation_indicators(
        self,
        read_grep_operations: int,
        write_edit_operations: int,
    ) -> bool:
        """Check if transcript shows investigation indicators.

        Args:
            read_grep_operations: Number of Read/Grep operations
            write_edit_operations: Number of Write/Edit operations

        Returns:
            True if investigation indicators present
        """
        # Multiple Read/Grep without modifications
        return read_grep_operations >= 2 and write_edit_operations == 0

    def _has_investigation_keywords(self, transcript: list[dict]) -> bool:
        """Check early user messages for investigation/troubleshooting keywords.

        This check takes PRIORITY over tool-based heuristics. If investigation
        keywords are found, the session is classified as INVESTIGATION regardless
        of what tools were used. This fixes #1604 where troubleshooting sessions
        were incorrectly blocked by development-specific checks.

        Args:
            transcript: List of message dictionaries

        Returns:
            True if investigation keywords found in early user messages
        """
        # Check first 5 user messages for investigation keywords
        user_messages = [m for m in transcript if m.get("type") == "user"][:5]

        if not user_messages:
            return False

        for msg in user_messages:
            content = str(msg.get("message", {}).get("content", "")).lower()

            # Check for investigation keywords
            for keyword in self.INVESTIGATION_KEYWORDS:
                if keyword in content:
                    self._log(
                        f"Investigation keyword '{keyword}' found in user message",
                        "DEBUG",
                    )
                    return True

        return False

    def detect_session_type(self, transcript: list[dict]) -> str:
        """Detect session type for selective consideration application.

        Session Types:
        - SIMPLE: Routine housekeeping tasks (cleanup, fetch, sync) - skip most checks
        - DEVELOPMENT: Code changes, tests, PR operations
        - INFORMATIONAL: Q&A, help queries, capability questions
        - MAINTENANCE: Documentation and configuration updates only
        - INVESTIGATION: Exploration, analysis, troubleshooting, and debugging
        - OPERATIONS: PM/planning/backlog triage - skip development workflow checks (fixes #2913)

        Detection Priority (UPDATED for Issue #2196, #2913):
        1. Environment override (AMPLIHACK_SESSION_TYPE)
        2. Simple task keywords (cleanup, fetch, workspace) - highest priority heuristic
        3. OPERATIONS keywords (prioritize, backlog, roadmap, sprint) - before tool analysis
        4. Tool usage patterns (code changes, tests, etc.) - CONCRETE EVIDENCE
        5. Investigation keywords in user messages - TIEBREAKER ONLY

        Tool usage patterns now take priority over keywords because they provide
        concrete evidence of the session's actual work. Keywords like "analyze and fix"
        are ambiguous, but Write/Edit tools with code changes are definitive signals
        of DEVELOPMENT work. Investigation keywords are only checked as a fallback
        when tool patterns are ambiguous (fixes #2196).

        Args:
            transcript: List of message dictionaries

        Returns:
            Session type string: "SIMPLE", "DEVELOPMENT", "INFORMATIONAL", "MAINTENANCE", or "INVESTIGATION"
        """
        # Check for environment override first
        env_override = os.getenv("AMPLIHACK_SESSION_TYPE", "").upper()
        if env_override in [
            "SIMPLE",
            "DEVELOPMENT",
            "INFORMATIONAL",
            "MAINTENANCE",
            "INVESTIGATION",
            "OPERATIONS",
        ]:
            self._log(f"Session type overridden by environment: {env_override}", "INFO")
            return env_override

        # Empty transcript defaults to INFORMATIONAL (fail-open)
        if not transcript:
            return "INFORMATIONAL"

        # Pre-filter user messages ONCE — used for keyword checks and question counting.
        # Avoids re-scanning transcript 3× (once here + once each in helper methods).
        user_messages = [m for m in transcript if m.get("type") == "user"]

        # HIGHEST PRIORITY: Simple task keywords (cleanup, fetch, sync, workspace)
        # These routine maintenance tasks should skip most power-steering checks
        # Inline the first-3 user message check to reuse the already-built list.
        found_simple = False
        for msg in user_messages[:3]:
            content = str(msg.get("message", {}).get("content", "")).lower()
            for keyword in self.SIMPLE_TASK_KEYWORDS:
                if keyword in content:
                    self._log(f"Simple task keyword '{keyword}' found in user message", "DEBUG")
                    found_simple = True
                    break
            if found_simple:
                break
        if found_simple:
            self._log("Session classified as SIMPLE via keyword detection", "INFO")
            return "SIMPLE"

        # OPERATIONS: PM/planning/backlog triage sessions (fixes #2913/#2914)
        # Check before tool usage analysis to prevent PM sessions from being
        # misclassified as INVESTIGATION by Read/Grep heuristics.
        found_operations = False
        for msg in user_messages[:5]:
            content = str(msg.get("message", {}).get("content", "")).lower()
            for keyword in self.OPERATIONS_KEYWORDS:
                if keyword in content:
                    self._log(f"Operations/PM keyword '{keyword}' found in user message", "DEBUG")
                    found_operations = True
                    break
            if found_operations:
                break
        if found_operations:
            self._log("Session classified as OPERATIONS via keyword detection", "INFO")
            return "OPERATIONS"

        # Count questions in user messages for INFORMATIONAL detection
        question_count = sum(
            str(m.get("message", {}).get("content", "")).count("?") for m in user_messages
        )

        # Collect indicators from transcript
        # Tool usage patterns are stronger signals than keywords (fixes #2196)
        code_files_modified = False
        doc_files_only = True
        write_edit_operations = 0
        read_grep_operations = 0
        test_executions = 0
        pr_dev_operations = False  # PR creation/edit (development signals)
        git_operations = False

        # Analyze tool usage
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if not isinstance(content, list):
                    content = [content]
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_name = block.get("name", "")
                        tool_input = block.get("input", {})

                        # Write/Edit operations
                        if tool_name in ["Write", "Edit"]:
                            write_edit_operations += 1
                            file_path = tool_input.get("file_path", "")

                            # Check if code file using class constant (use endswith to avoid false positives)
                            if any(file_path.endswith(ext) for ext in self.CODE_FILE_EXTENSIONS):
                                code_files_modified = True
                                doc_files_only = False

                            # Check if doc file using class constants (use endswith or special names)
                            is_doc_file = any(
                                file_path.endswith(ext) if ext.startswith(".") else ext in file_path
                                for ext in self.DOC_FILE_EXTENSIONS
                            )
                            is_config_file = any(
                                file_path.endswith(ext) for ext in self.CONFIG_FILE_EXTENSIONS
                            )

                            if not is_doc_file and not is_config_file:
                                doc_files_only = False

                        # Read/Grep operations (investigation indicators)
                        elif tool_name in ["Read", "Grep", "Glob"]:
                            read_grep_operations += 1

                        # Test execution
                        elif tool_name == "Bash":
                            command = tool_input.get("command", "")
                            # Test patterns using class constant
                            if any(pattern in command for pattern in self.TEST_COMMAND_PATTERNS):
                                test_executions += 1

                            # PR operations - distinguish dev (create/edit) from ops (view/merge/review)
                            if "gh pr create" in command or "gh pr edit" in command:
                                pr_dev_operations = True
                            elif "gh pr" in command:
                                pass  # view/merge/checks/diff/ready - ops, not development

                            # Git operations
                            if "git commit" in command or "git push" in command:
                                git_operations = True

        # Decision logic (REFINED for Issue #2196):
        # 1. Investigation keywords checked early BUT can be overridden by CODE modifications
        # 2. CODE modifications (code files) take priority → DEVELOPMENT
        # 3. NON-CODE modifications (docs, configs, git) DON'T override investigation keywords
        # 4. Default to INFORMATIONAL (fail-open)

        # Check for investigation keywords — inline first-5 user messages scan to reuse
        # already-built user_messages list (avoids a third full transcript scan).
        has_investigation_keywords = False
        for msg in user_messages[:5]:
            content = str(msg.get("message", {}).get("content", "")).lower()
            for keyword in self.INVESTIGATION_KEYWORDS:
                if keyword in content:
                    self._log(f"Investigation keyword '{keyword}' found in user message", "DEBUG")
                    has_investigation_keywords = True
                    break
            if has_investigation_keywords:
                break

        # DEVELOPMENT: CODE modifications override investigation keywords (fixes #2196)
        # Only override keywords if we have actual CODE file modifications
        # Doc/config updates or git operations should NOT override investigation keywords
        # PR ops (view/merge/review/checks) are NOT development signals (fixes #2563)
        if code_files_modified or test_executions > 0 or pr_dev_operations:
            # Strong signal: Write/Edit of CODE files, tests run, PR creation/editing
            self._log("Session classified as DEVELOPMENT via CODE modification patterns", "INFO")
            return "DEVELOPMENT"

        # INVESTIGATION: Keywords found and NO code modifications
        # This handles "investigate X", "how does X work", "troubleshoot Y" with:
        # - No tools (pure questions)
        # - Doc/config updates only (documenting findings)
        # - Git operations only (committing investigation notes)
        if has_investigation_keywords:
            self._log(
                "Session classified as INVESTIGATION via keywords (no code modifications)", "INFO"
            )
            return "INVESTIGATION"

        # INFORMATIONAL: No tool usage or only Read tools with high question density
        # Questions without investigation keywords
        if self._has_informational_indicators(
            write_edit_operations, read_grep_operations, question_count, user_messages
        ):
            return "INFORMATIONAL"

        # INVESTIGATION: Tool-based heuristics (Read/Grep without modifications)
        # Catches investigation sessions that don't have explicit keywords
        if self._has_investigation_indicators(read_grep_operations, write_edit_operations):
            self._log("Session classified as INVESTIGATION via tool usage patterns", "INFO")
            return "INVESTIGATION"

        # MAINTENANCE: Only doc/config files modified OR git operations without code changes
        if self._has_maintenance_indicators(
            write_edit_operations, doc_files_only, git_operations, code_files_modified
        ):
            return "MAINTENANCE"

        # Default to INFORMATIONAL if unclear (fail-open, conservative)
        return "INFORMATIONAL"

    def get_applicable_considerations(self, session_type: str) -> list[dict[str, Any]]:
        """Get considerations applicable to a specific session type.

        Args:
            session_type: Session type ("SIMPLE", "DEVELOPMENT", "INFORMATIONAL", "MAINTENANCE", "INVESTIGATION", "OPERATIONS")

        Returns:
            List of consideration dictionaries applicable to this session type
        """
        # SIMPLE and OPERATIONS sessions skip ALL considerations
        # SIMPLE: routine maintenance (cleanup, fetch, sync)
        # OPERATIONS: PM/planning sessions that don't modify code (fixes #2913)
        if session_type in ("SIMPLE", "OPERATIONS"):
            self._log(f"{session_type} session - skipping all considerations", "INFO")
            return []

        # Filter considerations based on session type
        applicable = []

        for consideration in self.considerations:
            # Check if consideration has applicable_session_types field
            applicable_types = consideration.get("applicable_session_types", [])

            # If no field or empty, check if this is Phase 1 fallback
            if not applicable_types:
                # Phase 1 considerations (no applicable_session_types field)
                # Only apply to DEVELOPMENT sessions by default
                if session_type == "DEVELOPMENT":
                    applicable.append(consideration)
                continue

            # Check if this session type is in the list
            if session_type in applicable_types or "*" in applicable_types:
                applicable.append(consideration)

        return applicable

    def _is_qa_session(self, transcript: list[dict]) -> bool:
        """Detect if session is interactive Q&A (skip power-steering).

        Heuristics:
        1. No tool calls (no file operations)
        2. High question count in user messages
        3. Short session (< 5 turns)

        Args:
            transcript: List of message dictionaries

        Returns:
            True if Q&A session, False otherwise
        """
        # Count tool uses - check for tool_use blocks in assistant messages
        # Note: We check both 'type' field and 'name' field because transcript
        # format can vary between direct tool_use blocks and nested formats
        tool_uses = 0
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if not isinstance(content, list):
                    content = [content]
                for block in content:
                    if isinstance(block, dict):
                        # Check for tool_use type OR presence of name field (tool indicator)
                        if block.get("type") == "tool_use" or (
                            "name" in block and block.get("name")
                        ):
                            tool_uses += 1

        # If we have substantial tool usage, not Q&A
        if tool_uses >= 2:
            return False

        # If no tool uses, check for Q&A pattern
        if tool_uses == 0:
            # Count user messages with questions
            user_messages = [m for m in transcript if m.get("type") == "user"]
            if len(user_messages) == 0:
                return True  # No user messages = skip

            questions = sum(
                1 for m in user_messages if "?" in str(m.get("message", {}).get("content", ""))
            )

            # If >50% of user messages are questions, likely Q&A
            if questions / len(user_messages) > QA_QUESTION_DENSITY_THRESHOLD:
                return True

        # Short sessions with few tools = likely Q&A
        if len(transcript) < 5 and tool_uses < 2:
            return True

        return False
