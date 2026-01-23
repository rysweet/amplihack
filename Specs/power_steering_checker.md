# Module: power_steering_checker.py

## Purpose

Analyzes session transcript against 21 considerations to determine if work is truly complete. Blocks session stop if work is incomplete and provides actionable continuation prompt.

## Contract

### Input

```python
def check(
    transcript_path: Path,
    session_id: str
) -> PowerSteeringResult
```

- `transcript_path`: Path to session transcript JSONL file
- `session_id`: Unique session identifier

### Output

```python
@dataclass
class PowerSteeringResult:
    decision: Literal["approve", "block"]
    reasons: List[str]  # Which considerations triggered block/approve
    continuation_prompt: Optional[str]  # What to do next (if blocked)
    summary: Optional[str]  # Session summary (if approved)
```

### Side Effects

- Reads transcript JSONL file
- Checks semaphore files in `~/.amplihack/.claude/runtime/power-steering/`
- Writes session summary to `~/.amplihack/.claude/runtime/power-steering/{session_id}/summary.md`
- Creates completion semaphore at `~/.amplihack/.claude/runtime/power-steering/.{session_id}_completed`

## Class Structure

```python
class PowerSteeringChecker:
    """Analyzes session completeness using 21 considerations."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.runtime_dir = project_root / ".claude" / "runtime" / "power-steering"
        self.config = self._load_config()
        self.considerations = self._load_considerations()

    def check(self, transcript_path: Path, session_id: str) -> PowerSteeringResult:
        """Main entry point - analyze transcript and make decision."""

        # 1. Check if disabled
        if self._is_disabled():
            return PowerSteeringResult("approve", ["disabled"], None, None)

        # 2. Check semaphore (prevent recursion)
        if self._already_ran(session_id):
            return PowerSteeringResult("approve", ["already_ran"], None, None)

        # 3. Detect Q&A session (skip if true)
        transcript = self._load_transcript(transcript_path)
        if self._is_qa_session(transcript):
            return PowerSteeringResult("approve", ["qa_session"], None, None)

        # 4. Analyze against 21 considerations
        analysis = self._analyze_considerations(transcript, session_id)

        # 5. Make decision
        if analysis.has_blockers:
            return PowerSteeringResult(
                decision="block",
                reasons=analysis.failed_considerations,
                continuation_prompt=self._generate_continuation_prompt(analysis),
                summary=None
            )
        else:
            # 6. Generate summary and mark complete
            summary = self._generate_summary(transcript, analysis)
            self._mark_complete(session_id)
            self._write_summary(session_id, summary)

            return PowerSteeringResult(
                decision="approve",
                reasons=["all_considerations_satisfied"],
                continuation_prompt=None,
                summary=summary
            )

    # Configuration
    def _load_config(self) -> Dict:
        """Load .power_steering_config (JSON)."""
        pass

    def _is_disabled(self) -> bool:
        """Check if power-steering is disabled via config/env/semaphore."""
        # Check 1: Config file
        if not self.config.get("enabled", True):
            return True

        # Check 2: Environment variable
        if os.getenv("AMPLIHACK_SKIP_POWER_STEERING"):
            return True

        # Check 3: Semaphore file
        disabled_file = self.runtime_dir / ".disabled"
        if disabled_file.exists():
            return True

        return False

    # Semaphore Management
    def _already_ran(self, session_id: str) -> bool:
        """Check if power-steering already ran for this session."""
        semaphore = self.runtime_dir / f".{session_id}_completed"
        return semaphore.exists()

    def _mark_complete(self, session_id: str):
        """Create semaphore to prevent re-running."""
        semaphore = self.runtime_dir / f".{session_id}_completed"
        semaphore.parent.mkdir(parents=True, exist_ok=True)
        semaphore.touch()

    # Transcript Analysis
    def _load_transcript(self, transcript_path: Path) -> List[Dict]:
        """Load transcript from JSONL file."""
        messages = []
        with open(transcript_path) as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
        return messages

    def _is_qa_session(self, transcript: List[Dict]) -> bool:
        """Detect if session is interactive Q&A (skip power-steering)."""
        # Heuristics:
        # 1. No tool calls (no file operations)
        # 2. High question count in user messages
        # 3. Short assistant responses (< 500 chars avg)
        # 4. No code blocks in responses

        tool_calls = sum(1 for msg in transcript if msg.get("role") == "assistant"
                        and msg.get("content", [{}])[0].get("type") == "tool_use")

        if tool_calls == 0:
            # Count questions
            user_messages = [msg for msg in transcript if msg.get("role") == "user"]
            questions = sum(1 for msg in user_messages
                          if "?" in str(msg.get("content", "")))

            # If >50% of user messages are questions and no tool calls, likely Q&A
            if len(user_messages) > 0 and questions / len(user_messages) > 0.5:
                return True

        return False

    # Consideration Analysis
    def _load_considerations(self) -> List[Dict]:
        """Load 21 considerations (Phase 1: hardcoded, Phase 2: from file)."""
        # Phase 1: Return hardcoded list
        # Phase 2: Load from .claude/tools/amplihack/considerations/default.json
        pass

    def _analyze_considerations(self, transcript: List[Dict], session_id: str) -> ConsiderationAnalysis:
        """Analyze transcript against all considerations."""
        analysis = ConsiderationAnalysis()

        for consideration in self.considerations:
            result = self._check_consideration(consideration, transcript, session_id)
            analysis.add_result(consideration, result)

        return analysis

    def _check_consideration(self, consideration: Dict, transcript: List[Dict], session_id: str) -> bool:
        """Check single consideration against transcript."""
        # Each consideration has:
        # - id: unique identifier
        # - category: one of 5 categories
        # - question: the check to perform
        # - checker: function name to call
        # - severity: "blocker" or "warning"

        checker_func = getattr(self, f"_check_{consideration['id']}", None)
        if not checker_func:
            # Log warning and skip
            return True  # Don't block on missing checker

        return checker_func(transcript, session_id)

    # Individual Consideration Checkers (21 total)
    # These analyze transcript and return True (satisfied) or False (blocker)

    def _check_autonomous_question(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if agent stopping to ask question that could be answered autonomously."""
        # Look at last assistant message
        # If it's asking a question, check if answer could be found via:
        # - Reading existing files
        # - Checking documentation
        # - Running tests
        # - Using web search
        pass

    def _check_objective_complete(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if session completed user's objective."""
        # Compare first user message (objective) with last assistant message
        # Look for completion indicators:
        # - "Done", "Completed", "Finished"
        # - All requested files created/modified
        # - Tests passing
        pass

    def _check_todos_complete(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if all TODO items completed."""
        # Look for TodoWrite tool calls
        # Check last TodoWrite - are all todos status="completed"?
        pass

    def _check_docs_updated(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if documentation updates needed."""
        # Look for code changes (Edit/Write tool calls)
        # Check if corresponding docs were updated
        # Look for README, API docs, CHANGELOG updates
        pass

    def _check_tutorial_needed(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if tutorial needed for large feature."""
        # If >10 files changed, suggest tutorial
        # Check if tutorial exists in docs/
        pass

    def _check_powerpoint_needed(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if PowerPoint overview needed for large feature."""
        # If >20 files changed or new major feature, suggest PPT
        # Check if overview exists
        pass

    def _check_next_steps_scope(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if 'next steps' are actually part of original request."""
        # Look for "Next steps", "Future work", "TODO" in last message
        # Compare with original user request
        # Block if next steps should be current steps
        pass

    def _check_docs_organized(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if doc updates are organized and linked."""
        # If multiple doc files updated, check for index/TOC
        # Verify cross-references exist
        pass

    def _check_investigation_workflow(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if investigation workflow needs final docs phase."""
        # Look for investigation-related tool calls
        # Check if documentation was generated
        pass

    def _check_dev_workflow_complete(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if full DEFAULT_WORKFLOW followed (including review)."""
        # Look for workflow steps in transcript
        # Verify all workflow steps executed
        pass

    def _check_philosophy_adherence(self, transcript: List[Dict], session_id: str) -> bool:
        """Check for PHILOSOPHY adherence (zero-BS, quality over speed)."""
        # Look for stub implementations
        # Check for TODOs in code
        # Verify no dead code
        pass

    def _check_no_shortcuts(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if any pre-commit/CI checks or tests disabled."""
        # Search for "skip", "disable", "ignore" in git commits
        # Check for --no-verify, SKIP env vars
        pass

    def _check_local_testing(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if agent tested locally."""
        # Look for Bash tool calls with pytest, npm test, etc.
        # Verify tests passed
        pass

    def _check_ui_testing(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if UI feature tested interactively."""
        # Look for UI-related changes (React, HTML, CSS)
        # Check for manual testing mentions
        pass

    def _check_no_unrelated_changes(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if PR has unrelated changes."""
        # Look at git diff
        # Compare changed files with objective
        pass

    def _check_no_root_files(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if PR dropping files in repo root."""
        # Look at git status for new files in /
        pass

    def _check_pr_description_current(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if PR description up to date with test results."""
        # Look for PR creation (gh pr create)
        # Check if description includes test results
        pass

    def _check_review_addressed(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if code review response addressed all concerns."""
        # Look for PR review comments
        # Verify all addressed
        pass

    def _check_branch_current(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if branch up to date (need rebase?)."""
        # Look for git status output
        # Check for "behind" main
        pass

    def _check_precommit_ci_match(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if CI failing but pre-commit didn't - check match?"""
        # Compare pre-commit results with CI results
        # Look for discrepancies
        pass

    def _check_ci_status(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if CI still running or PR mergeable."""
        # Look for CI status checks
        # Verify all green or explain why waiting
        pass

    # Output Generation
    def _generate_continuation_prompt(self, analysis: ConsiderationAnalysis) -> str:
        """Generate actionable continuation prompt based on failed considerations."""
        prompt_parts = [
            "The session appears incomplete. Please address the following:",
            ""
        ]

        # Group by category
        by_category = analysis.group_by_category()

        for category, failed in by_category.items():
            prompt_parts.append(f"**{category}**")
            for consideration in failed:
                prompt_parts.append(f"- {consideration.question}")
            prompt_parts.append("")

        prompt_parts.append("Once these are addressed, you may stop the session.")

        return "\n".join(prompt_parts)

    def _generate_summary(self, transcript: List[Dict], analysis: ConsiderationAnalysis) -> str:
        """Generate session summary for successful completion."""
        summary_parts = [
            "# Session Summary",
            "",
            f"**Session ID**: {session_id}",
            f"**Completed**: {datetime.now().isoformat()}",
            "",
            "## Objective",
            self._extract_objective(transcript),
            "",
            "## What Was Done",
            self._extract_actions(transcript),
            "",
            "## Files Changed",
            self._extract_files_changed(transcript),
            "",
            "## Tests",
            self._extract_test_results(transcript),
            "",
            "## All Considerations Satisfied ✓",
            ""
        ]

        return "\n".join(summary_parts)

    def _write_summary(self, session_id: str, summary: str):
        """Write summary to file."""
        summary_path = self.runtime_dir / session_id / "summary.md"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(summary)

    # Helper extraction methods
    def _extract_objective(self, transcript: List[Dict]) -> str:
        """Extract original user objective from first message."""
        pass

    def _extract_actions(self, transcript: List[Dict]) -> str:
        """Extract key actions from tool calls."""
        pass

    def _extract_files_changed(self, transcript: List[Dict]) -> str:
        """Extract list of files modified."""
        pass

    def _extract_test_results(self, transcript: List[Dict]) -> str:
        """Extract test execution results."""
        pass


@dataclass
class ConsiderationAnalysis:
    """Results of analyzing all considerations."""
    results: Dict[str, bool] = field(default_factory=dict)
    failed_considerations: List[Dict] = field(default_factory=list)

    @property
    def has_blockers(self) -> bool:
        """True if any blocker consideration failed."""
        return len(self.failed_considerations) > 0

    def add_result(self, consideration: Dict, satisfied: bool):
        """Add result for a consideration."""
        self.results[consideration['id']] = satisfied
        if not satisfied and consideration.get('severity') == 'blocker':
            self.failed_considerations.append(consideration)

    def group_by_category(self) -> Dict[str, List[Dict]]:
        """Group failed considerations by category."""
        grouped = {}
        for consideration in self.failed_considerations:
            category = consideration['category']
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(consideration)
        return grouped
```

## Dependencies

- Standard library: `json`, `pathlib`, `os`, `datetime`, `dataclasses`
- Internal: `hook_processor.py` (for logging patterns, though not inheriting)

## Implementation Notes

### Phase 1 (MVP)

- Hardcode 21 considerations in `_load_considerations()`
- Implement top 10 most critical checkers first
- Simple heuristics for Q&A detection
- Basic summary generation

### Phase 2 (Enhancement)

- Move considerations to external JSON file
- Add more sophisticated transcript analysis
- ML-based Q&A detection
- Rich summary with metrics

### Performance Considerations

- Transcript files can be large (>10MB for long sessions)
- Load transcript once, pass to all checkers
- Cache analysis results
- Timeout after 30 seconds (fail-safe: approve)

### Error Handling

- Missing transcript file: approve (fail-open)
- Malformed transcript: log warning, approve
- Checker exception: log error, treat as satisfied (don't block on bugs)
- Config file missing: use defaults (enabled=true)

## Test Requirements

### Unit Tests

- Each consideration checker with mock transcript data
- Semaphore file handling (creation, detection)
- Q&A session detection with various transcript patterns
- Continuation prompt generation
- Summary generation

### Integration Tests

- Full flow with real transcript file
- Disabled state checks (all 3 methods)
- Recursive prevention
- Summary file writing

### Edge Case Tests

- Empty transcript
- Very large transcript (>10MB)
- Malformed JSONL
- Missing session_id
- Concurrent runs (race conditions)
