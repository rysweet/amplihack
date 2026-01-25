# Considerations Format

## Purpose

Define structure for 21 considerations used by power-steering.

## Phase 1: Hardcoded

In MVP, considerations are hardcoded in `power_steering_checker.py`:

```python
CONSIDERATIONS = [
    {
        "id": "autonomous_question",
        "category": "Session Completion & Progress",
        "question": "Is agent stopping to ask question that could be answered autonomously?",
        "severity": "blocker",
        "checker": "_check_autonomous_question"
    },
    # ... 20 more
]
```

## Phase 2: External File

Move to `~/.amplihack/.claude/tools/amplihack/considerations/default.json`:

```json
{
  "version": "1.0",
  "considerations": [
    {
      "id": "autonomous_question",
      "category": "Session Completion & Progress",
      "order": 1,
      "question": "Is agent stopping to ask question that could be answered autonomously?",
      "description": "Check if agent is asking user for information that could be obtained by reading files, checking docs, running tests, or searching the web.",
      "severity": "blocker",
      "checker": "_check_autonomous_question",
      "hints": [
        "Look for question marks in last assistant message",
        "Check if answer could be in existing files",
        "Verify if documentation exists for question"
      ]
    },
    {
      "id": "objective_complete",
      "category": "Session Completion & Progress",
      "order": 2,
      "question": "Did session complete user's objective?",
      "description": "Compare original user request with what was actually done.",
      "severity": "blocker",
      "checker": "_check_objective_complete",
      "hints": [
        "Extract objective from first user message",
        "Check for completion indicators in last message",
        "Verify all requested files were created/modified"
      ]
    },
    {
      "id": "todos_complete",
      "category": "Session Completion & Progress",
      "order": 3,
      "question": "Were all TODO items completed?",
      "description": "Check if any TodoWrite todos remain incomplete.",
      "severity": "blocker",
      "checker": "_check_todos_complete",
      "hints": [
        "Find last TodoWrite tool call",
        "Check status of all todos",
        "Verify no pending or in_progress items"
      ]
    },
    {
      "id": "docs_updated",
      "category": "Session Completion & Progress",
      "order": 4,
      "question": "Documentation updates needed?",
      "description": "Check if code changes require doc updates.",
      "severity": "warning",
      "checker": "_check_docs_updated",
      "hints": [
        "Count files changed",
        "Check if README exists and was updated",
        "Look for API doc updates"
      ]
    },
    {
      "id": "tutorial_needed",
      "category": "Session Completion & Progress",
      "order": 5,
      "question": "Tutorial needed for large feature?",
      "description": "For features affecting >10 files, check if tutorial exists.",
      "severity": "warning",
      "checker": "_check_tutorial_needed",
      "hints": [
        "Count files modified",
        "Check docs/ directory for tutorials",
        "Look for HOW_TO guides"
      ]
    },
    {
      "id": "powerpoint_needed",
      "category": "Session Completion & Progress",
      "order": 6,
      "question": "PowerPoint overview for large feature?",
      "description": "For features affecting >20 files, suggest overview presentation.",
      "severity": "warning",
      "checker": "_check_powerpoint_needed",
      "hints": [
        "Count files modified",
        "Check for .pptx files in docs/",
        "Verify architecture diagrams exist"
      ]
    },
    {
      "id": "next_steps_scope",
      "category": "Session Completion & Progress",
      "order": 7,
      "question": "Are 'next steps' actually part of original request?",
      "description": "Check if agent is deferring work that should be done now.",
      "severity": "blocker",
      "checker": "_check_next_steps_scope",
      "hints": [
        "Look for 'Next steps', 'Future work' in last message",
        "Compare with original objective",
        "Check if deferred work is in scope"
      ]
    },
    {
      "id": "docs_organized",
      "category": "Session Completion & Progress",
      "order": 8,
      "question": "Are doc updates organized and linked?",
      "description": "Check if multiple doc updates have index/TOC.",
      "severity": "warning",
      "checker": "_check_docs_organized",
      "hints": ["Count doc files modified", "Check for index or TOC", "Verify cross-references"]
    },
    {
      "id": "investigation_workflow",
      "category": "Workflow Process Adherence",
      "order": 9,
      "question": "Investigation workflow - need final docs phase?",
      "description": "Check if investigation workflow completed documentation phase.",
      "severity": "blocker",
      "checker": "_check_investigation_workflow",
      "hints": [
        "Look for investigation-related tool calls",
        "Check if INVESTIGATION_*.md or ARCHITECTURE_*.md created",
        "Verify knowledge was captured"
      ]
    },
    {
      "id": "dev_workflow_complete",
      "category": "Workflow Process Adherence",
      "order": 10,
      "question": "Dev workflow - full DEFAULT_WORKFLOW followed (including review)?",
      "description": "Verify all 13 workflow steps were executed.",
      "severity": "blocker",
      "checker": "_check_dev_workflow_complete",
      "hints": [
        "Check for architect, builder, reviewer agent calls",
        "Verify tests were run",
        "Look for git commit and push"
      ]
    },
    {
      "id": "philosophy_adherence",
      "category": "Code Quality & Philosophy",
      "order": 11,
      "question": "PHILOSOPHY adherence (zero-BS, quality over speed)?",
      "description": "Check for stubs, TODOs, dead code.",
      "severity": "blocker",
      "checker": "_check_philosophy_adherence",
      "hints": [
        "Search for TODO, FIXME, XXX in code",
        "Check for stub implementations",
        "Look for dead/unreachable code"
      ]
    },
    {
      "id": "no_shortcuts",
      "category": "Code Quality & Philosophy",
      "order": 12,
      "question": "Any disabled pre-commit/CI checks or tests (shortcuts)?",
      "description": "Check for disabled quality gates.",
      "severity": "blocker",
      "checker": "_check_no_shortcuts",
      "hints": [
        "Look for --no-verify in git commits",
        "Check for SKIP environment variables",
        "Search for pytest.mark.skip"
      ]
    },
    {
      "id": "local_testing",
      "category": "Testing & Local Validation",
      "order": 13,
      "question": "Sure agent tested locally?",
      "description": "Verify tests were run and passed.",
      "severity": "blocker",
      "checker": "_check_local_testing",
      "hints": [
        "Look for pytest, npm test, cargo test calls",
        "Check exit codes",
        "Verify all tests passed"
      ]
    },
    {
      "id": "ui_testing",
      "category": "Testing & Local Validation",
      "order": 14,
      "question": "UI feature tested interactively?",
      "description": "For UI changes, check for manual testing.",
      "severity": "warning",
      "checker": "_check_ui_testing",
      "hints": [
        "Look for React, HTML, CSS changes",
        "Check for npm start, dev server runs",
        "Look for manual testing mentions"
      ]
    },
    {
      "id": "no_unrelated_changes",
      "category": "PR Content & Quality",
      "order": 15,
      "question": "PR has unrelated changes?",
      "description": "Check if PR includes changes outside objective scope.",
      "severity": "warning",
      "checker": "_check_no_unrelated_changes",
      "hints": [
        "Review git diff",
        "Compare files with objective",
        "Look for formatting-only changes"
      ]
    },
    {
      "id": "no_root_files",
      "category": "PR Content & Quality",
      "order": 16,
      "question": "PR dropping files in repo root?",
      "description": "Check for new files in repository root.",
      "severity": "warning",
      "checker": "_check_no_root_files",
      "hints": [
        "Look at git status",
        "Check for new files in /",
        "Verify files belong in subdirectories"
      ]
    },
    {
      "id": "pr_description_current",
      "category": "PR Content & Quality",
      "order": 17,
      "question": "PR description up to date with test results?",
      "description": "Check if PR description includes test outcomes.",
      "severity": "warning",
      "checker": "_check_pr_description_current",
      "hints": [
        "Look for gh pr create",
        "Check PR body for test results",
        "Verify description matches final state"
      ]
    },
    {
      "id": "review_addressed",
      "category": "PR Content & Quality",
      "order": 18,
      "question": "Code review response addressed all concerns?",
      "description": "Check if all PR review comments were addressed.",
      "severity": "blocker",
      "checker": "_check_review_addressed",
      "hints": [
        "Look for PR review comments",
        "Check for follow-up commits",
        "Verify all threads resolved"
      ]
    },
    {
      "id": "branch_current",
      "category": "CI/CD & Mergeability",
      "order": 19,
      "question": "Branch up to date? Need rebase?",
      "description": "Check if branch is behind main.",
      "severity": "blocker",
      "checker": "_check_branch_current",
      "hints": [
        "Look for git status output",
        "Check for 'behind' in status",
        "Verify no merge conflicts"
      ]
    },
    {
      "id": "precommit_ci_match",
      "category": "CI/CD & Mergeability",
      "order": 20,
      "question": "CI failing but pre-commit didn't - check match?",
      "description": "Verify pre-commit and CI are aligned.",
      "severity": "warning",
      "checker": "_check_precommit_ci_match",
      "hints": [
        "Compare pre-commit results with CI",
        "Look for discrepancies",
        "Check .pre-commit-config.yaml vs CI config"
      ]
    },
    {
      "id": "ci_status",
      "category": "CI/CD & Mergeability",
      "order": 21,
      "question": "CI still running or PR mergeable?",
      "description": "Check CI status and mergeability.",
      "severity": "blocker",
      "checker": "_check_ci_status",
      "hints": [
        "Look for CI status checks",
        "Check for green checkmarks",
        "Verify no blocking failures"
      ]
    }
  ]
}
```

## Field Definitions

### id

- **Type**: string
- **Required**: Yes
- **Description**: Unique identifier for consideration. Used as key in results.

### category

- **Type**: string
- **Required**: Yes
- **Description**: One of 5 categories:
  - "Session Completion & Progress"
  - "Workflow Process Adherence"
  - "Code Quality & Philosophy"
  - "Testing & Local Validation"
  - "PR Content & Quality"
  - "CI/CD & Mergeability"

### order

- **Type**: integer
- **Required**: Yes
- **Description**: Display order within category (1-21).

### question

- **Type**: string
- **Required**: Yes
- **Description**: The question to ask about session state.

### description

- **Type**: string
- **Required**: Yes
- **Description**: Detailed explanation of what this consideration checks.

### severity

- **Type**: string
- **Required**: Yes
- **Enum**: "blocker" | "warning"
- **Description**:
  - "blocker": Must be satisfied to allow stop
  - "warning": Inform user but don't block

### checker

- **Type**: string
- **Required**: Yes
- **Description**: Method name in PowerSteeringChecker that implements check.

### hints

- **Type**: array of strings
- **Required**: No
- **Description**: Implementation guidance for checker method.

## Loading Logic

```python
def _load_considerations(self) -> List[Dict]:
    """Load considerations from file or use hardcoded defaults."""

    # Phase 2: Load from external file
    considerations_file = self.config.get("considerations_file", "default.json")
    considerations_path = (
        self.project_root / ".claude" / "tools" / "amplihack"
        / "considerations" / considerations_file
    )

    if considerations_path.exists():
        try:
            with open(considerations_path) as f:
                data = json.load(f)
                return data["considerations"]
        except Exception as e:
            # Log warning and fall back to hardcoded
            logger.warning(f"Failed to load considerations from {considerations_path}: {e}")

    # Phase 1: Hardcoded fallback
    return HARDCODED_CONSIDERATIONS
```

## Validation

When loading external file, validate:

- All required fields present
- Severity is valid enum value
- Checker method exists in PowerSteeringChecker
- IDs are unique
- Orders are unique within category

If validation fails, log error and use hardcoded defaults.

## Extensibility

Users can create custom consideration files:

- Copy `default.json` to `custom.json`
- Modify considerations (add, remove, change severity)
- Update config: `"considerations_file": "custom.json"`
- Restart Claude Code

Note: Custom checkers require code changes - only metadata can be customized via file.
