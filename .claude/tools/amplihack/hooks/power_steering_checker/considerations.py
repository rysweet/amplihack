"""Considerations module - dataclasses and ConsiderationsMixin."""

import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Literal, Optional


def _env_int(var: str, default: int) -> int:
    """Parse an integer from an environment variable, falling back to default.

    REQ-SEC-2: Non-numeric env vars must not raise ValueError at module import
    time, which would silently disable the hook.
    """
    raw = os.getenv(var)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# Module-level constants extracted from inline code
QA_QUESTION_DENSITY_THRESHOLD = 0.5
MAX_ASK_USER_COUNT = 3
MIN_README_PATHS = 2
MIN_SHORTCUT_USAGE_COUNT = 10

# Pre-compiled regex patterns for hot-path matching
_HANDOFF_PATTERNS = [
    re.compile(r"wait\s+for\s+(ci|review|approval|merge)"),
    re.compile(r"(user|you)\s+(should|can|may|need to)"),
    re.compile(r"filed\s+(as|in)\s+#"),
    re.compile(r"tracked\s+in\s+#"),
    re.compile(r"when\s+ci\s+passes"),
    re.compile(r"pr\s+ready\s+for\s+review"),
    re.compile(r"ready\s+for\s+(review|merge|approval)"),
    re.compile(r"waiting\s+for\s+(review|approval|ci|merge)"),
]

# Pre-compiled patterns for _check_shortcuts (avoids re-compilation on every call)
_SHORTCUT_PATTERNS = [
    re.compile(r"\bpass\b.*#.*\blater\b", re.IGNORECASE),
    re.compile(r"#.*\bhack\b", re.IGNORECASE),
    re.compile(r"#.*\bworkaround\b", re.IGNORECASE),
    re.compile(r"#.*\btemporary\b", re.IGNORECASE),
    re.compile(r"#.*\bfix\b.*\blater\b", re.IGNORECASE),
]

# Pre-compiled patterns for _check_next_steps (avoids re-compilation on every call)
_NEXT_STEPS_PATTERNS = [
    re.compile(
        r"(next steps?|remaining|todo|outstanding|still need to):\s*[\r\n]+\s*[-•*\d.]",
        re.IGNORECASE,
    ),
]
_NEGATION_PATTERNS = [
    re.compile(r"no\s+(next\s+steps?|remaining|outstanding|todo)", re.IGNORECASE),
    re.compile(
        r"(next\s+steps?|remaining|outstanding|todo)\s+(?:are\s+)?(?:none|empty|complete)",
        re.IGNORECASE,
    ),
    re.compile(r"all\s+(?:done|complete|finished)", re.IGNORECASE),
    re.compile(r"nothing\s+(?:left|remaining|outstanding)", re.IGNORECASE),
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


@dataclass
class CheckerResult:
    """Result from a single consideration checker."""

    consideration_id: str
    satisfied: bool
    reason: str
    severity: Literal["blocker", "warning"]
    recovery_steps: list[str] = field(default_factory=list)  # Optional recovery guidance
    executed: bool = True  # Whether this check was actually executed

    @property
    def id(self) -> str:
        """Alias for consideration_id for backward compatibility."""
        return self.consideration_id


@dataclass
class ConsiderationAnalysis:
    """Results of analyzing all considerations."""

    results: dict[str, CheckerResult] = field(default_factory=dict)
    failed_blockers: list[CheckerResult] = field(default_factory=list)
    failed_warnings: list[CheckerResult] = field(default_factory=list)

    @property
    def has_blockers(self) -> bool:
        """True if any blocker consideration failed."""
        return len(self.failed_blockers) > 0

    def add_result(self, result: CheckerResult) -> None:
        """Add result for a consideration."""
        self.results[result.consideration_id] = result
        if not result.satisfied:
            if result.severity == "blocker":
                self.failed_blockers.append(result)
            else:
                self.failed_warnings.append(result)

    def group_by_category(self) -> dict[str, list[CheckerResult]]:
        """Group failed considerations by category."""
        # For Phase 1, use simplified categories based on consideration ID prefix
        grouped: dict[str, list[CheckerResult]] = {}
        for result in self.failed_blockers + self.failed_warnings:
            # Simple category derivation from ID
            if "workflow" in result.consideration_id or "philosophy" in result.consideration_id:
                category = "Workflow & Philosophy"
            elif "testing" in result.consideration_id or "ci" in result.consideration_id:
                category = "Testing & CI/CD"
            else:
                category = "Completion Checks"

            if category not in grouped:
                grouped[category] = []
            grouped[category].append(result)
        return grouped


@dataclass
class PowerSteeringRedirect:
    """Record of a power-steering redirect (blocked session)."""

    redirect_number: int
    timestamp: str  # ISO format
    failed_considerations: list[str]  # IDs of failed checks
    continuation_prompt: str
    work_summary: str | None = None


@dataclass
class PowerSteeringResult:
    """Final decision from power-steering analysis."""

    decision: Literal["approve", "block"]
    reasons: list[str]
    continuation_prompt: str | None = None
    summary: str | None = None
    analysis: Optional["ConsiderationAnalysis"] = None  # Full analysis results for visibility
    is_first_stop: bool = False  # True if this is the first stop attempt in session
    evidence_results: list = field(default_factory=list)  # Concrete evidence from Phase 1
    compaction_context: Any = None  # Compaction diagnostics (CompactionContext if available)
    considerations: list = field(
        default_factory=list
    )  # List of CheckerResult objects for visibility


class ConsiderationsMixin:
    """Mixin with all consideration-related methods."""

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

    # Phase 1 fallback: Hardcoded considerations (top 5 critical)
    # Used when YAML file is missing or invalid
    PHASE1_CONSIDERATIONS = [
        {
            "id": "todos_complete",
            "category": "Session Completion & Progress",
            "question": "Were all TodoWrite task items marked as completed before the session ended?",
            "severity": "blocker",
            "checker": "_check_todos_complete",
        },
        {
            "id": "dev_workflow_complete",
            "category": "Workflow Process Adherence",
            "question": "Were all required DEFAULT_WORKFLOW steps completed this session, including requirements clarification, design, implementation, testing, and PR creation?",
            "severity": "blocker",
            "checker": "_check_dev_workflow_complete",
        },
        {
            "id": "philosophy_compliance",
            "category": "Code Quality & Philosophy",
            "question": "Does all code written this session comply with the zero-BS philosophy, meaning no TODO comments, no NotImplementedError stubs, no placeholder functions, and no unimplemented code paths?",
            "severity": "blocker",
            "checker": "_check_philosophy_compliance",
        },
        {
            "id": "local_testing",
            "category": "Testing & Local Validation",
            "question": "Did the agent run the test suite locally (e.g., pytest, npm test, cargo test) and confirm all tests passed before declaring the work complete?",
            "severity": "blocker",
            "checker": "_check_local_testing",
        },
        {
            "id": "ci_status",
            "category": "CI/CD & Mergeability",
            "question": "Are all GitHub Actions CI checks passing and the PR in a mergeable state, with no failing required checks or unresolved merge conflicts?",
            "severity": "blocker",
            "checker": "_check_ci_status",
        },
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

        Detection Priority (UPDATED for Issue #2196):
        1. Environment override (AMPLIHACK_SESSION_TYPE)
        2. Simple task keywords (cleanup, fetch, workspace) - highest priority heuristic
        3. Tool usage patterns (code changes, tests, etc.) - CONCRETE EVIDENCE
        4. Investigation keywords in user messages - TIEBREAKER ONLY

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
            session_type: Session type ("SIMPLE", "DEVELOPMENT", "INFORMATIONAL", "MAINTENANCE", "INVESTIGATION")

        Returns:
            List of consideration dictionaries applicable to this session type
        """
        # SIMPLE sessions skip ALL considerations - they are routine maintenance tasks
        # like cleanup, fetch, sync, workspace management that don't need verification
        if session_type == "SIMPLE":
            self._log("SIMPLE session - skipping all considerations", "INFO")
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

    def _generic_analyzer(
        self, transcript: list[dict], session_id: str, consideration: dict[str, Any]
    ) -> bool:
        """Generic analyzer for considerations without specific checkers.

        Uses simple keyword matching on the consideration question.
        Phase 2: Simple heuristics (future: LLM-based analysis)

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier
            consideration: Consideration dictionary with question

        Returns:
            True if satisfied (fail-open default), False if potential issues detected
        """
        return True  # Fail-open fallback

    @staticmethod
    def _find_last_todo_write(transcript: list[dict]) -> dict | None:
        """Find the most recent TodoWrite tool call input in the transcript.

        Args:
            transcript: List of message dictionaries

        Returns:
            TodoWrite input dict (with 'todos' key), or None if not found
        """
        for msg in reversed(transcript):
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "TodoWrite":
                                return block.get("input", {})
        return None

    def _extract_incomplete_todos(self, transcript: list[dict]) -> list[str]:
        """Extract list of incomplete todo items from transcript.

        Helper method used by continuation prompt generation to show
        specific items the agent needs to complete.

        Args:
            transcript: List of message dictionaries

        Returns:
            List of incomplete todo item descriptions
        """
        last_todo_write = self._find_last_todo_write(transcript)
        if not last_todo_write:
            return []

        return [
            f"[{todo.get('status', 'pending')}] {todo.get('content', 'Unknown task')}"
            for todo in last_todo_write.get("todos", [])
            if todo.get("status") != "completed"
        ]

    def _extract_next_steps_mentioned(self, transcript: list[dict]) -> list[str]:
        """Extract specific next steps mentioned in recent assistant messages.

        Helper method used by continuation prompt generation to show
        specific next steps the agent mentioned but hasn't completed.

        Args:
            transcript: List of message dictionaries

        Returns:
            List of next step descriptions (extracted sentences/phrases)
        """
        next_steps = []
        next_steps_triggers = [
            "next step",
            "next steps",
            "follow-up",
            "remaining",
            "still need",
            "todo",
            "left to",
        ]

        # Check recent assistant messages
        recent_messages = [m for m in transcript[-15:] if m.get("type") == "assistant"][-5:]

        for msg in recent_messages:
            content = msg.get("message", {}).get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = str(block.get("text", ""))
                        text_lower = text.lower()

                        # Check if this block mentions next steps
                        if any(trigger in text_lower for trigger in next_steps_triggers):
                            # Extract sentences containing the trigger
                            sentences = text.replace("\n", " ").split(". ")
                            for sentence in sentences:
                                sentence_lower = sentence.lower()
                                if any(
                                    trigger in sentence_lower for trigger in next_steps_triggers
                                ):
                                    clean_sentence = sentence.strip()
                                    if clean_sentence and len(clean_sentence) > 10:
                                        # Truncate long sentences
                                        if len(clean_sentence) > 150:
                                            clean_sentence = clean_sentence[:147] + "..."
                                        if clean_sentence not in next_steps:
                                            next_steps.append(clean_sentence)

        return next_steps[:5]  # Limit to 5 items

    def _check_todos_complete(self, transcript: list[dict], session_id: str) -> bool:
        """Check if all TODO items completed.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if all TODOs completed, False otherwise
        """
        last_todo_write = self._find_last_todo_write(transcript)
        if not last_todo_write:
            return True  # No todos to check

        todos = last_todo_write.get("todos", [])
        return all(todo.get("status") == "completed" for todo in todos)

    def _check_workflow_invocation(self, transcript: list[dict], session_id: str) -> bool:
        """Check if workflow was properly invoked using Claude SDK analysis.

        Uses context-aware AI analysis to detect workflow invocation patterns:
        - Explicit Skill tool invocation
        - Explicit Read tool invocation
        - Implicit step-by-step workflow following
        - Async completion (PR created for review, CI running)

        Issue #2040: Enforce workflow invocation compliance

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if workflow properly invoked or not required, False otherwise
        """
        try:
            # Import SDK analysis function
            from claude_power_steering import analyze_workflow_invocation_sync

            # Determine session type from state if available
            session_type = "DEVELOPMENT"  # Default
            try:
                state_file = self.runtime_dir / session_id / "turn_state.json"
                if state_file.exists():
                    state = json.loads(state_file.read_text())
                    session_type = state.get("session_type", "DEVELOPMENT")
            except Exception as e:
                self._log(
                    f"Could not load session type from state file, using default: {e}",
                    "WARNING",
                    exc_info=True,
                )

            # Use SDK analysis for workflow invocation validation
            valid, reason = analyze_workflow_invocation_sync(
                transcript, session_type, self.project_root
            )

            if not valid:
                # Log violation details
                self._log_violation(
                    "workflow_invocation",
                    {
                        "reason": reason or "Workflow not properly invoked",
                        "session_type": session_type,
                    },
                    session_id,
                )

            return valid

        except ImportError:
            # SDK not available - fail open
            sys.stderr.write(
                "[Power Steering] claude_power_steering not available, skipping workflow check\n"
            )
            return True
        except Exception as e:
            # Fail-open on errors
            sys.stderr.write(f"[Power Steering] Error in _check_workflow_invocation: {e}\n")
            self._log(f"Error in _check_workflow_invocation: {e}", "WARNING", exc_info=True)
            return True

    def _transcript_to_text(self, transcript: list[dict]) -> str:
        """Convert transcript list to plain text for pattern matching.

        Args:
            transcript: List of message dictionaries

        Returns:
            Plain text representation of transcript
        """
        lines = []
        for msg in transcript:
            role = msg.get("type", "unknown")
            if role == "user":
                lines.append(f"User: {self._extract_message_text(msg)}")
            elif role == "assistant":
                lines.append(f"Claude: {self._extract_message_text(msg)}")
        return "\n".join(lines)

    def _extract_message_text(self, msg: dict) -> str:
        """Extract text content from message.

        Args:
            msg: Message dictionary

        Returns:
            Text content
        """
        message = msg.get("message", {})
        content = message.get("content", [])

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            texts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        texts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        # Include tool invocations in text
                        tool_name = block.get("name", "")
                        tool_input = block.get("input", {})
                        texts.append(f'<invoke name="{tool_name}">{tool_input}')
            return " ".join(texts)

        return ""

    def _check_no_direct_main_commit(self, transcript: list[dict], session_id: str) -> bool:
        """Check that the agent did not commit directly to main.

        Verifies the mandatory user preference that all code changes go through
        a feature branch and PR, never committing directly to main/master.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if no direct-to-main commits detected, False otherwise
        """
        for i, msg in enumerate(transcript):
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "Bash":
                                command = block.get("input", {}).get("command", "")
                                # Detect git commit on main/master
                                if "git commit" in command:
                                    # Check NEARBY messages for branch context
                                    if self._is_on_main_branch_near(transcript, i):
                                        return False
                                # Detect git push to main/master (explicit or bare)
                                if "git push" in command:
                                    if "origin main" in command or "origin master" in command:
                                        return False
                                    # Bare git push (no branch specified) while on main
                                    if (
                                        "origin main" not in command
                                        and "origin master" not in command
                                    ):
                                        # Only flag if no branch is specified at all
                                        # (git push, git push origin, git push -u origin)
                                        parts = command.strip().split()
                                        # If command is just "git push" or "git push origin"
                                        # (no branch arg), check if we're on main
                                        has_branch_arg = len(parts) > 3 or any(
                                            p.startswith("feat/")
                                            or p.startswith("fix/")
                                            or p.startswith("docs/")
                                            for p in parts
                                        )
                                        if not has_branch_arg and self._is_on_main_branch_near(
                                            transcript, i
                                        ):
                                            return False
        return True

    def _is_on_main_branch_near(self, transcript: list[dict], commit_index: int) -> bool:
        """Check if git context NEAR a commit command shows we're on main/master.

        Searches within 10 messages before the commit for the most recent
        branch indicator. This avoids false positives where the session started
        on main but switched to a feature branch before committing.

        Args:
            transcript: List of message dictionaries
            commit_index: Index of the message containing the git commit

        Returns:
            True if nearest branch evidence shows main/master
        """
        # Search the 10 messages before the commit for branch context
        start = max(0, commit_index - 10)
        # Also check the most recent branch indicator, not just any indicator
        for msg in reversed(transcript[start:commit_index]):
            if msg.get("type") == "tool_result":
                output = str(msg.get("message", {}).get("content", "")).lower()
                # If we find a feature branch indicator, we're NOT on main
                if (
                    "on branch " in output
                    and "on branch main" not in output
                    and "on branch master" not in output
                ):
                    return False
                # If we find main/master indicator, we ARE on main
                if "on branch main" in output or "on branch master" in output:
                    return True
                if "* main" in output or "* master" in output:
                    return True
        # No branch context found nearby — fail-open (assume not on main)
        return False

    def _check_dev_workflow_complete(self, transcript: list[dict], session_id: str) -> bool:
        """Check if full DEFAULT_WORKFLOW followed.

        Heuristics:
        - Look for multiple agent invocations (architect, builder, reviewer)
        - Check for test execution
        - Verify git operations (commit, push)

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if workflow complete, False otherwise
        """
        # Single-pass: collect file ops and test commands simultaneously
        has_file_ops = False
        has_tests = False
        direct_patterns = self.TEST_COMMAND_PATTERNS + self.VALIDATION_COMMAND_PATTERNS
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict) or block.get("type") != "tool_use":
                            continue
                        tool_name = block.get("name", "")
                        if tool_name in ("Edit", "Write"):
                            has_file_ops = True
                        elif tool_name == "Bash" and not has_tests:
                            command = block.get("input", {}).get("command", "")
                            if any(p in command for p in direct_patterns):
                                has_tests = True
                            elif any(
                                p in command for p in self.INLINE_VALIDATION_PATTERNS
                            ) and self._is_meaningful_validation(command):
                                has_tests = True
            # Early exit once both flags are set
            if has_file_ops and has_tests:
                break

        # If no file operations, likely not a development task
        if not has_file_ops:
            return True

        if not has_tests:
            return False

        return True

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

    # Sentinel to distinguish "not yet cached" from False result
    _NO_AUTO_MERGE_UNSET = object()
    _MERGE_PREFERENCE_PATTERN = re.compile(
        r"(never|must not|do not|don't).*merge.*without.*(permission|approval|explicit)",
        re.IGNORECASE | re.DOTALL,
    )

    def _user_prefers_no_auto_merge(self) -> bool:
        """Detect if user has set preference to never auto-merge PRs.

        Searches .claude/context/USER_PREFERENCES.md for pattern:
        "(never|must not|do not|don't) ... merge ... without ... (permission|approval|explicit)"

        Result is cached per-instance — the preference file doesn't change during a session.

        Returns:
            True if preference detected, False otherwise (fail-open on any error)
        """
        # Return cached result if already computed (avoids repeated file I/O)
        cached = getattr(self, "_no_auto_merge_cache", self._NO_AUTO_MERGE_UNSET)
        if cached is not self._NO_AUTO_MERGE_UNSET:
            return cached  # type: ignore[return-value]

        result = False
        try:
            preferences_path = self.project_root / ".claude" / "context" / "USER_PREFERENCES.md"

            if preferences_path.exists():
                content = preferences_path.read_text(encoding="utf-8")
                result = self._MERGE_PREFERENCE_PATTERN.search(content) is not None

        except Exception as e:
            # Fail-open: any error returns False
            self._log(f"Error detecting merge preference: {e}", "WARNING", exc_info=True)

        self._no_auto_merge_cache = result
        return result

    def _check_ci_status_no_auto_merge(self, transcript: list[dict]) -> bool:
        """Check CI status WITHOUT requiring PR merge.

        Used when user preference "never merge without permission" is active.
        Treats "PR ready + CI passing" as valid completion state.

        Args:
            transcript: List of message dictionaries

        Returns:
            True if PR ready and CI passing, False if CI failing or draft PR
        """
        # Look for PR and CI indicators
        pr_mentioned = False
        ci_mentioned = False
        ci_passing = False
        is_draft = False

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                text = str(block.get("text", "")).lower()

                                # Check for PR mentions
                                if any(
                                    keyword in text
                                    for keyword in ["pr #", "pull request", "created pr"]
                                ):
                                    pr_mentioned = True

                                # Check for draft PR
                                if "draft" in text and "pr" in text:
                                    is_draft = True

                                # Check for CI mentions
                                if any(
                                    keyword in text
                                    for keyword in [
                                        "ci",
                                        "github actions",
                                        "continuous integration",
                                        "checks",
                                    ]
                                ):
                                    ci_mentioned = True

                                    # Check for passing indicators
                                    if any(
                                        keyword in text
                                        for keyword in [
                                            "passing",
                                            "passed",
                                            "success",
                                            "ready for review",
                                            "ready for your review",
                                        ]
                                    ):
                                        ci_passing = True

                                    # Check for failing indicators
                                    if any(
                                        keyword in text
                                        for keyword in ["failing", "failed", "error"]
                                    ):
                                        return False

        # If draft PR, not ready
        if is_draft:
            return False

        # If CI mentioned and failing, return False
        if ci_mentioned and not ci_passing:
            return False

        # If PR mentioned with CI passing, or PR ready indicators
        if pr_mentioned and (ci_passing or not ci_mentioned):
            return True

        # If neither PR nor CI mentioned, assume satisfied (fail-open)
        if not pr_mentioned and not ci_mentioned:
            return True

        # Default: if we have indicators but unclear state, be conservative
        return ci_passing or not ci_mentioned

    def _check_ci_status(self, transcript: list[dict], session_id: str) -> bool:
        """Check if CI passing/mergeable (preference-aware).

        This method delegates to the appropriate CI checker based on user preference:
        - If user prefers no auto-merge: use _check_ci_status_no_auto_merge()
        - Otherwise: use standard CI check logic (requires merge indicators)

        Heuristics (standard mode):
        - Look for CI status checks (gh pr view, CI commands)
        - Check for "passing", "success", "mergeable" (strict - requires "mergeable")
        - Look for failure indicators

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if CI passing or not applicable, False if CI failing
        """
        # Check user preference first (lazy detection)
        if self._user_prefers_no_auto_merge():
            return self._check_ci_status_no_auto_merge(transcript)

        # Standard logic for users without preference (strict - requires "mergeable")
        ci_mentioned = False
        mergeable_mentioned = False

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            # Check text content for CI mentions
                            if block.get("type") == "text":
                                text = str(block.get("text", ""))
                                text_lower = text.lower()

                                if any(
                                    keyword in text_lower
                                    for keyword in [
                                        "ci",
                                        "github actions",
                                        "continuous integration",
                                    ]
                                ):
                                    ci_mentioned = True

                                # Standard mode: only accept explicit "mergeable" or "passing" + "mergeable"
                                # Don't accept just "ready" or "passing" alone
                                if "mergeable" in text_lower:
                                    mergeable_mentioned = True

                                # Check for failure indicators
                                if any(
                                    keyword in text_lower
                                    for keyword in ["failing", "failed", "error"]
                                ):
                                    return False

        # If CI not mentioned, consider satisfied (not applicable)
        if not ci_mentioned:
            return True

        # Standard mode requires explicit "mergeable" indicator
        return mergeable_mentioned

    def _check_agent_unnecessary_questions(self, transcript: list[dict], session_id: str) -> bool:
        """Check if agent asked unnecessary questions instead of proceeding autonomously.

        Detects use of AskUserQuestion tool, which is the concrete signal that the
        agent stopped to ask the user something. Simple question marks in prose
        (explanations, documentation, rhetorical questions) are NOT counted.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if no excessive questioning, False if agent over-asked
        """
        # Count actual AskUserQuestion tool invocations (the concrete signal)
        ask_user_count = 0
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "AskUserQuestion":
                                ask_user_count += 1

        # More than 3 explicit AskUserQuestion invocations suggests the agent
        # was not working autonomously. This avoids false positives from
        # question marks in prose, documentation, or code comments.
        if ask_user_count > MAX_ASK_USER_COUNT:
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

    # Paths that indicate user-facing/public code changes requiring doc updates
    # Paths indicating user-facing/public code. __init__.py and __main__.py
    # are only public when inside a public directory (commands, skills, etc.)
    # so they are checked separately via _is_public_init.
    PUBLIC_CODE_INDICATORS = [
        "/commands/",
        "/skills/",
        "/scenarios/",
        "/cli/",
        "/cli.py",
        "__main__.py",
        "setup.py",
        "pyproject.toml",
    ]

    def _check_documentation_updates(self, transcript: list[dict], session_id: str) -> bool:
        """Check if relevant documentation files were updated.

        Only flags missing docs when PUBLIC-FACING code was changed (commands,
        skills, CLIs, public APIs). Internal code changes (hooks, utilities,
        tests, configs) do not require documentation updates.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if docs updated or not applicable, False if needed but missing
        """
        public_code_modified = False
        doc_files_modified = False

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_name = block.get("name", "")
                            if tool_name in ["Write", "Edit"]:
                                tool_input = block.get("input", {})
                                file_path = tool_input.get("file_path", "").lower()

                                # Only flag public-facing code changes
                                is_code = any(
                                    file_path.endswith(ext) for ext in self.CODE_FILE_EXTENSIONS
                                )
                                is_public = any(
                                    indicator in file_path
                                    for indicator in self.PUBLIC_CODE_INDICATORS
                                )
                                # __init__.py is public only inside public dirs
                                if "__init__.py" in file_path and any(
                                    d in file_path
                                    for d in ["/commands/", "/skills/", "/scenarios/"]
                                ):
                                    is_public = True
                                if is_code and is_public:
                                    public_code_modified = True

                                # Check for doc files using class constant
                                if any(
                                    file_path.endswith(ext)
                                    if ext.startswith(".")
                                    else ext in file_path
                                    for ext in self.DOC_FILE_EXTENSIONS
                                ):
                                    doc_files_modified = True

        # Only flag if public-facing code was changed without doc updates
        if public_code_modified and not doc_files_modified:
            return False

        return True

    def _check_tutorial_needed(self, transcript: list[dict], session_id: str) -> bool:
        """Check if new feature needs tutorial/how-to.

        Detects new user-facing features that should have examples.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if tutorial exists or not needed, False if missing
        """
        # Look for new feature indicators
        feature_keywords = ["new feature", "add feature", "implement feature", "create feature"]
        has_new_feature = False

        for msg in transcript:
            if msg.get("type") == "user":
                content = str(msg.get("message", {}).get("content", "")).lower()
                if any(keyword in content for keyword in feature_keywords):
                    has_new_feature = True
                    break

        if not has_new_feature:
            return True  # No new feature, tutorial not needed

        # Check for example/tutorial files
        tutorial_patterns = ["example", "tutorial", "how_to", "guide", "demo"]
        has_tutorial = False

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_name = block.get("name", "")
                            if tool_name in ["Write", "Edit"]:
                                file_path = block.get("input", {}).get("file_path", "").lower()
                                if any(pattern in file_path for pattern in tutorial_patterns):
                                    has_tutorial = True
                                    break

        return has_tutorial

    def _check_presentation_needed(self, transcript: list[dict], session_id: str) -> bool:
        """Check if work needs presentation deck.

        Detects high-impact work that should be presented to stakeholders.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if presentation exists or not needed, False if missing
        """
        # This is a low-priority check, default to satisfied
        # Could be enhanced to detect high-impact work patterns
        return True

    def _check_feature_docs_discoverable(self, transcript: list[dict], session_id: str) -> bool:
        """Check if feature documentation is discoverable from multiple paths.

        Verifies new features have documentation discoverable from README and docs/ directory.
        This ensures users can find documentation through:
        1. README features/documentation section
        2. docs/ directory listing

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if docs are discoverable or not applicable, False if missing navigation
        """
        try:
            # Phase 1: Detect new features
            # Look for new commands, agents, skills, scenarios in Write/Edit operations
            new_features = []
            docs_file = None

            for msg in transcript:
                if msg.get("type") == "assistant" and "message" in msg:
                    content = msg["message"].get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                tool_name = block.get("name", "")
                                if tool_name in ["Write", "Edit"]:
                                    file_path = block.get("input", {}).get("file_path", "")

                                    # Detect new feature by file location
                                    if ".claude/commands/" in file_path and file_path.endswith(
                                        ".md"
                                    ):
                                        new_features.append(("command", file_path))
                                    elif ".claude/agents/" in file_path and file_path.endswith(
                                        ".md"
                                    ):
                                        new_features.append(("agent", file_path))
                                    elif ".claude/skills/" in file_path:
                                        new_features.append(("skill", file_path))
                                    elif ".claude/scenarios/" in file_path:
                                        new_features.append(("scenario", file_path))

                                    # Track docs file creation in docs/
                                    if "docs/" in file_path and file_path.endswith(".md"):
                                        docs_file = file_path

            # Edge case 1: No new features detected
            if not new_features:
                return True

            # Edge case 2: Docs-only session (no code files modified)
            # But NOT if the "docs" are actually feature definitions (.md files
            # in commands/agents/skills) — those ARE the feature, not just docs
            if self._is_docs_only_session(transcript) and not new_features:
                return True

            # Edge case 3: Internal changes (tools/, tests/, etc.)
            # If all features are in internal paths, pass
            internal_paths = [".claude/tools/", "tests/", ".claude/runtime/"]
            all_internal = all(
                any(internal in feature[1] for internal in internal_paths)
                for feature in new_features
            )
            if all_internal:
                return True

            # Phase 2: Check for docs file in docs/ directory
            if not docs_file:
                return False  # New feature but no docs file created

            # Phase 3: Verify 2+ navigation paths in README
            readme_paths_count = 0

            for msg in transcript:
                if msg.get("type") == "assistant" and "message" in msg:
                    content = msg["message"].get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                tool_name = block.get("name", "")
                                if tool_name in ["Write", "Edit"]:
                                    file_path = block.get("input", {}).get("file_path", "")

                                    # Check if README was edited
                                    if "readme.md" in file_path.lower():
                                        # Get the new content to check for documentation links
                                        new_string = block.get("input", {}).get("new_string", "")
                                        content_to_check = block.get("input", {}).get("content", "")
                                        full_content = new_string or content_to_check

                                        # Count references to the docs file
                                        if docs_file and full_content:
                                            # Extract just the filename from the path
                                            doc_filename = docs_file.split("/")[-1]
                                            # Count occurrences of the doc filename in README content
                                            readme_paths_count += full_content.count(doc_filename)

            # Need at least 2 navigation paths (e.g., Features section + Documentation section)
            if readme_paths_count < MIN_README_PATHS:
                return False

            # All checks passed
            return True

        except Exception as e:
            # Fail-open: Return True on errors to avoid blocking users
            self._log(f"PR content validation error (fail-open): {e}", "WARNING", exc_info=True)
            return True

    def _is_docs_only_session(self, transcript: list[dict]) -> bool:
        """Check if session only modified documentation files.

        Helper method to detect docs-only sessions where no code files were touched.

        Args:
            transcript: List of message dictionaries

        Returns:
            True if only .md files were modified, False if code files modified
        """
        try:
            code_modified = False
            docs_modified = False

            for msg in transcript:
                if msg.get("type") == "assistant" and "message" in msg:
                    content = msg["message"].get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                tool_name = block.get("name", "")
                                if tool_name in ["Write", "Edit"]:
                                    file_path = block.get("input", {}).get("file_path", "")

                                    # Check for code files using class constant
                                    if any(
                                        file_path.endswith(ext) for ext in self.CODE_FILE_EXTENSIONS
                                    ):
                                        code_modified = True

                                    # Check for doc files using class constant
                                    if any(
                                        file_path.endswith(ext)
                                        if ext.startswith(".")
                                        else ext in file_path
                                        for ext in self.DOC_FILE_EXTENSIONS
                                    ):
                                        docs_modified = True

            # Docs-only session if docs modified but no code files
            return docs_modified and not code_modified

        except Exception as e:
            # Fail-open: Return False on errors (assume code might be modified)
            self._log(
                f"Docs-only session detection error (fail-open): {e}", "WARNING", exc_info=True
            )
            return False

    def _check_next_steps(self, transcript: list[dict], session_id: str) -> bool:
        """Check that work is complete with NO remaining next steps (Issue #2196 - Enhanced).

        UPDATED LOGIC (Issue #2196):
        - Uses regex patterns to detect STRUCTURED next steps (bulleted lists)
        - Handles negation ("no next steps", "no remaining work")
        - Ignores status observations ("CI pending", "waiting for")
        - Prevents false positives on completion statements

        INVERTED LOGIC: If the agent mentions concrete next steps in structured format,
        work is incomplete. Simple keywords without structure are ignored to prevent
        false positives.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if NO next steps found (work is complete)
            False if next steps ARE found (work is incomplete - should continue)
        """
        # Check RECENT assistant messages (last 10) for structured next steps
        recent_messages = [m for m in transcript[-20:] if m.get("type") == "assistant"][-10:]

        for msg in reversed(recent_messages):
            content = msg.get("message", {}).get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = str(block.get("text", ""))

                        # First check for negation patterns (completion statements)
                        # These should PASS the check (return True)
                        # Use module-level pre-compiled _NEGATION_PATTERNS
                        negation_matched = any(p.search(text) for p in _NEGATION_PATTERNS)
                        if negation_matched:
                            self._log(
                                "Completion statement found: negation pattern matched",
                                "INFO",
                            )
                            continue

                        # Check for STRUCTURED next steps (bulleted/numbered lists)
                        # These indicate CONCRETE remaining work
                        # Use module-level pre-compiled _NEXT_STEPS_PATTERNS
                        for pattern in _NEXT_STEPS_PATTERNS:
                            if pattern.search(text):
                                # Before flagging, check if ALL bullet items are
                                # user-handoff or deferred-to-issue patterns
                                text_lower = text.lower()
                                is_handoff = any(hp.search(text_lower) for hp in _HANDOFF_PATTERNS)
                                if is_handoff:
                                    self._log(
                                        "Structured list detected but contains handoff/deferred items - treating as complete",
                                        "INFO",
                                    )
                                    continue  # Skip this match, not real remaining work
                                self._log(
                                    f"Structured next steps found: pattern '{pattern.pattern}' - agent should continue",
                                    "INFO",
                                )
                                return False  # Work is INCOMPLETE (concrete next steps exist)

        # No structured next steps found - work is complete
        return True

    def _check_docs_organization(self, transcript: list[dict], session_id: str) -> bool:
        """Check if investigation/session docs are organized properly.

        Verifies documentation is in correct directories.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if docs properly organized, False otherwise
        """
        # Check for doc files created in wrong locations
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "Write":
                                file_path = block.get("input", {}).get("file_path", "")

                                # Check for investigation/session docs in wrong places
                                if any(
                                    pattern in file_path.lower()
                                    for pattern in ["investigation", "session", "log"]
                                ):
                                    # Should be in .claude/runtime or .claude/docs
                                    if ".claude" not in file_path:
                                        return False

        return True

    def _check_investigation_docs(self, transcript: list[dict], session_id: str) -> bool:
        """Check if investigation findings were documented.

        Ensures exploration work is captured in persistent documentation.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if investigation documented, False if missing
        """
        # Look for investigation indicators
        investigation_keywords = [
            "investigate",
            "investigation",
            "explore",
            "exploration",
            "research",
            "analyze",
            "analyse",
            "analysis",
            "findings",
        ]

        has_investigation = False
        for msg in transcript:
            if msg.get("type") == "user":
                content = str(msg.get("message", {}).get("content", "")).lower()
                if any(keyword in content for keyword in investigation_keywords):
                    has_investigation = True
                    break

        if not has_investigation:
            return True  # No investigation, docs not needed

        # Check for documentation of findings
        doc_created = False
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "Write":
                                file_path = block.get("input", {}).get("file_path", "").lower()
                                if any(
                                    pattern in file_path for pattern in [".md", "readme", "doc"]
                                ):
                                    doc_created = True
                                    break

        return doc_created

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
                match = re.search(r"(\d+)\s+passed", output, re.IGNORECASE)
                if match:
                    count = int(match.group(1))
                    if count >= MIN_SHORTCUT_USAGE_COUNT:
                        return True

        return False

    def _check_unrelated_changes(self, transcript: list[dict], session_id: str) -> bool:
        """Check if there are unrelated changes in PR.

        Detects scope creep by checking if files span too many unrelated
        top-level directories. A focused change should touch files in 1-3
        related directories. Touching 6+ distinct top-level directories
        suggests scope creep.

        Previous heuristic (>20 files = scope creep) was replaced because
        file count has no correlation with relatedness — a legitimate refactor
        can touch 50 files in one module while a 5-file change can span
        unrelated areas.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if changes appear focused, False if too scattered
        """
        # Collect distinct top-level project directories of modified files
        top_dirs = set()
        project_root_str = str(self.project_root)

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") in ["Write", "Edit"]:
                                file_path = block.get("input", {}).get("file_path", "")
                                if not file_path:
                                    continue
                                # Convert to project-relative path
                                try:
                                    rel = os.path.relpath(file_path, project_root_str)
                                except ValueError:
                                    continue  # Different drives on Windows
                                parts = rel.split(os.sep)
                                # Skip paths outside project (.. prefix)
                                if parts and parts[0] != ".." and len(parts) >= 2:
                                    top_dirs.add(parts[0])

        # 6+ distinct top-level project directories suggests scattered changes
        if len(top_dirs) >= 6:
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

    def _check_pr_description(self, transcript: list[dict], session_id: str) -> bool:
        """Check if PR description is clear and complete.

        Verifies PR has summary, test plan, and context.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if PR description adequate, False if missing or incomplete
        """
        # Look for PR creation (gh pr create)
        pr_created = False
        pr_body = ""

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "Bash":
                                command = block.get("input", {}).get("command", "")
                                if "gh pr create" in command:
                                    pr_created = True
                                    pr_body = command.lower()

        if not pr_created:
            return True  # No PR, check not applicable

        # Check PR body for required sections
        required_sections = ["summary", "test", "plan"]
        has_all_sections = all(section in pr_body for section in required_sections)

        return has_all_sections

    def _check_review_responses(self, transcript: list[dict], session_id: str) -> bool:
        """Check if PR review comments were addressed.

        Only triggers when there is concrete evidence of actual PR review activity
        (gh pr review, gh api for PR comments, reviewer requested changes). Does NOT
        trigger on the generic word 'review' in user messages, which caused widespread
        false positives.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if reviews addressed or no PR reviews exist, False if unaddressed
        """
        # Look for concrete PR review signals in tool calls, not generic keywords.
        # These indicate actual GitHub PR review comments exist.
        pr_review_command_patterns = [
            "gh pr review",
            "requested changes",
            "changes_requested",
            "reviewer comment",
            "review comment",
        ]
        has_pr_reviews = False

        for msg in transcript:
            # Check Bash tool calls for PR review commands
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "Bash":
                                command = block.get("input", {}).get("command", "").lower()
                                if any(p in command for p in pr_review_command_patterns):
                                    has_pr_reviews = True
                                    break
                                # Narrow gh api match: only review/comment endpoints
                                if "gh api repos/" in command and (
                                    "/reviews" in command or "/comments" in command
                                ):
                                    has_pr_reviews = True
                                    break
            # Check tool results for review-related output
            if msg.get("type") == "tool_result":
                output = str(msg.get("message", {}).get("content", "")).lower()
                if "requested changes" in output or "changes_requested" in output:
                    has_pr_reviews = True

        if not has_pr_reviews:
            return True  # No PR reviews to address

        # Look for response indicators showing reviews were handled
        response_keywords = ["addressed", "fixed", "updated", "resolved", "pushed"]
        for msg in transcript:
            if msg.get("type") == "assistant":
                content = msg.get("message", {}).get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = str(block.get("text", "")).lower()
                            if any(keyword in text for keyword in response_keywords):
                                return True

        return False

    def _check_branch_rebase(self, transcript: list[dict], session_id: str) -> bool:
        """Check if branch needs rebase on main.

        Verifies branch is up to date with main.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if branch is current, False if needs rebase
        """
        # Look for git status or branch checks
        for msg in transcript:
            if msg.get("type") == "tool_result":
                output = str(msg.get("message", {}).get("content", "")).lower()

                # Check for "behind" indicators
                if "behind" in output or "diverged" in output:
                    return False

                # Check for "up to date" indicators
                if "up to date" in output or "up-to-date" in output:
                    return True

        # Default to satisfied if no information
        return True

    def _check_ci_precommit_mismatch(self, transcript: list[dict], session_id: str) -> bool:
        """Check for CI failures contradicting passing pre-commit.

        Identifies divergence between local pre-commit and CI checks.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if no mismatch, False if divergence detected
        """
        # Look for pre-commit passing
        precommit_passed = False
        ci_failed = False

        for msg in transcript:
            if msg.get("type") in ["assistant", "tool_result"]:
                content_str = str(msg.get("message", {})).lower()

                # Check for pre-commit success
                if "pre-commit" in content_str or "precommit" in content_str:
                    if "passed" in content_str or "success" in content_str:
                        precommit_passed = True

                # Check for CI failure
                if "ci" in content_str or "github actions" in content_str:
                    if "failed" in content_str or "failing" in content_str:
                        ci_failed = True

        # If both conditions met, there's a mismatch
        if precommit_passed and ci_failed:
            return False

        return True
