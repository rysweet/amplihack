# Power Steering SDK-First Refactoring Design

**Date**: 2025-11-26
**Status**: Design Phase
**Philosophy**: Ruthless Simplicity, Fail-Open, Zero-BS

## Executive Summary

Arr, we be refactorin' the power steerin' checker to use Claude Agent SDK as the PRIMARY analysis method, eliminatin' brittle regex/keyword matchin' in favor o' intelligent LLM-based consideration analysis. The current implementation has BACKWARDS LOGIC that skips SDK fer the very checkers that need it most!

## Current Problems

### 1. Backwards Logic in `_check_single_consideration_async`

**Current Code (Lines 1898-1902)**:

```python
use_sdk = (
    SDK_AVAILABLE
    and checker_name != "generic"  # Skip SDK for generic checkers
    and checker_name.startswith("_check_")  # Only use SDK for specific checkers
)
```

**The Problem**: This logic be INVERTED, matey!

- Specific checkers like `_check_todos_complete` use heuristics INSTEAD of SDK
- Only "generic" checkers use SDK (which makes no sense)
- Result: Most powerful checkers use weakest methods

### 2. Brittle Heuristic Patterns

**`_check_todos_complete` (Line 2003)**:

- Searches for last TodoWrite tool call
- Manually parses todo status
- Fragile to tool format changes

**`_check_philosophy_compliance` (Line 2176)**:

- Regex searches for "TODO", "FIXME", "XXX"
- Hardcoded anti-patterns
- False positives on legitimate comments

**`_check_local_testing` (Line 2227)**:

- Keyword matching for "pytest", "PASSED", "OK"
- Exit code checking
- Misses non-standard test frameworks

**`_generic_analyzer` (Line 2355)**:

- Keyword extraction from question
- Simple token matching
- No semantic understanding

## Architecture Decision: SDK-First

**DECISION**: SDK-first with graceful fallback to heuristics

### Rationale

1. **Primary Goal**: Use LLM intelligence for ALL considerations
2. **Fail-Open**: Never block users when SDK unavailable
3. **Progressive Enhancement**: Keep heuristics as fallback-only
4. **Simple Implementation**: Minimal code changes, maximum benefit

### Design Choice Matrix

| Approach                        | Pros                | Cons                        | Decision                       |
| ------------------------------- | ------------------- | --------------------------- | ------------------------------ |
| SDK-only (remove heuristics)    | Simplest code       | Breaks when SDK unavailable | ❌ Rejects fail-open principle |
| SDK-first (heuristics fallback) | Best of both worlds | Slightly more code          | ✅ **SELECTED**                |
| Heuristics-first (SDK optional) | Always works        | Defeats purpose of refactor | ❌ No improvement              |

## Implementation Design

### Phase 1: Fix Backwards Logic

**File**: `power_steering_checker.py`

**Change 1: Invert SDK detection logic**

```python
async def _check_single_consideration_async(
    self,
    consideration: dict[str, Any],
    transcript: list[dict],
    session_id: str,
) -> CheckerResult:
    """Check a single consideration asynchronously.

    Phase 5 (SDK-First): Use Claude SDK as PRIMARY method
    - ALL considerations analyzed by SDK first (when available)
    - Specific checkers (_check_*) used ONLY as fallback
    - Fail-open when SDK unavailable
    """
    try:
        # SDK-FIRST: Try SDK for ALL considerations (when available)
        if SDK_AVAILABLE:
            try:
                # Use async SDK function directly (already awaitable)
                satisfied = await analyze_consideration(
                    conversation=transcript,
                    consideration=consideration,
                    project_root=self.project_root,
                )

                # SDK succeeded - return result
                return CheckerResult(
                    consideration_id=consideration["id"],
                    satisfied=satisfied,
                    reason=(
                        "SDK analysis: satisfied"
                        if satisfied
                        else f"SDK analysis: {consideration['question']} not met"
                    ),
                    severity=consideration["severity"],
                )
            except Exception as e:
                # SDK failed - log and fall through to fallback
                self._log(
                    f"SDK analysis failed for '{consideration['id']}': {e}",
                    "DEBUG",
                )
                # Continue to fallback methods below

        # FALLBACK: Use heuristic checkers when SDK unavailable or failed
        checker_name = consideration["checker"]

        # Dispatch to specific checker or generic analyzer
        if hasattr(self, checker_name) and callable(getattr(self, checker_name)):
            checker_func = getattr(self, checker_name)
            satisfied = checker_func(transcript, session_id)
        else:
            # Generic analyzer for considerations without specific checker
            satisfied = self._generic_analyzer(transcript, session_id, consideration)

        return CheckerResult(
            consideration_id=consideration["id"],
            satisfied=satisfied,
            reason=(
                f"Heuristic fallback: {'satisfied' if satisfied else 'not met'}"
            ),
            severity=consideration["severity"],
        )

    except Exception as e:
        # Fail-open: Never block on errors
        self._log(
            f"Checker error for '{consideration['id']}': {e}",
            "WARNING",
        )
        return CheckerResult(
            consideration_id=consideration["id"],
            satisfied=True,  # Fail-open
            reason=f"Error (fail-open): {e}",
            severity=consideration["severity"],
        )
```

**Key Changes**:

1. **SDK-FIRST**: Try SDK for ALL considerations when available
2. **Graceful Fallback**: Use heuristics only when SDK fails
3. **Clear Logging**: Distinguish SDK vs fallback results
4. **Fail-Open**: Always allow stop on errors

### Phase 2: Enhance SDK Prompts

**File**: `claude_power_steering.py`

**Current Prompt (Line 160-181)**: Generic, one-size-fits-all

**Enhancement Strategy**: Consideration-type-specific prompts

```python
def _format_consideration_prompt(consideration: Dict, conversation: List[Dict]) -> str:
    """Format analysis prompt for a consideration.

    Uses consideration-type-specific prompts for better accuracy.

    Args:
        consideration: Consideration dictionary
        conversation: Session conversation messages

    Returns:
        Formatted prompt string tailored to consideration type
    """
    # Format conversation summary
    conv_summary = _format_conversation_summary(conversation)

    # Get consideration type from ID or category
    consideration_id = consideration.get("id", "")
    category = consideration.get("category", "General")

    # Select prompt template based on consideration type
    if "todos" in consideration_id or "todo" in consideration_id.lower():
        return _prompt_todos_complete(consideration, conv_summary)
    elif "philosophy" in consideration_id or "zero-bs" in consideration_id.lower():
        return _prompt_philosophy_compliance(consideration, conv_summary)
    elif "test" in consideration_id or "testing" in consideration_id.lower():
        return _prompt_testing_verification(consideration, conv_summary)
    elif "ci" in consideration_id or "workflow" in consideration_id.lower():
        return _prompt_workflow_complete(consideration, conv_summary)
    else:
        # Generic prompt for unmatched types
        return _prompt_generic_consideration(consideration, conv_summary)


def _prompt_todos_complete(consideration: Dict, conv_summary: str) -> str:
    """Specialized prompt for TODO completion checking."""
    return f"""You are analyzing a Claude Code session to verify TODO list completion.

**Consideration**: {consideration["question"]}
**Description**: {consideration.get("description", "")}

**Session Conversation**:
{conv_summary}

## Analysis Instructions

Check if all TODO items in the session are marked as completed:

1. **Find TodoWrite tool calls**: Look for messages where TodoWrite tool was used
2. **Check status**: Examine the "status" field of each todo item
3. **Completion criteria**: All items must have status="completed"
4. **Ignore empty lists**: If no todos were created, consider SATISFIED

**Evidence to look for**:
- TodoWrite tool calls with todos array
- Status fields showing "completed" vs "pending" vs "in_progress"
- Explicit discussion about completing remaining work

**Respond with ONE of:**
- "SATISFIED: All todo items marked completed [cite specific evidence]"
- "NOT SATISFIED: Found incomplete todos [cite specific items]"

Be specific - reference actual todo items and their status from the conversation."""


def _prompt_philosophy_compliance(consideration: Dict, conv_summary: str) -> str:
    """Specialized prompt for philosophy compliance (Zero-BS) checking."""
    return f"""You are analyzing a Claude Code session for philosophy compliance.

**Consideration**: {consideration["question"]}
**Description**: Verify adherence to "Zero-BS Implementation" - no stubs, TODOs, or placeholder code

**Session Conversation**:
{conv_summary}

## Analysis Instructions

Check for anti-patterns that violate Zero-BS philosophy:

**RED FLAGS** (indicate NOT SATISFIED):
- TODO comments in code (except in test fixtures)
- FIXME, XXX, or similar markers
- NotImplementedError or pass-only functions
- Stub implementations (functions that don't work)
- Placeholder comments like "// Implement this later"

**GREEN FLAGS** (indicate SATISFIED):
- Working implementations (even simple ones)
- Tests for implemented functionality
- No incomplete code markers

**Context matters**:
- TODOs in documentation/README are OK
- "TODO" in string literals or test data is OK
- Temporary debug TODOs removed before commit are OK

**Respond with ONE of:**
- "SATISFIED: No anti-patterns found [cite evidence of working code]"
- "NOT SATISFIED: Found stubs/TODOs [cite specific violations]"

Be specific - reference actual code snippets and file names."""


def _prompt_testing_verification(consideration: Dict, conv_summary: str) -> str:
    """Specialized prompt for local testing verification."""
    return f"""You are analyzing a Claude Code session to verify local testing.

**Consideration**: {consideration["question"]}
**Description**: {consideration.get("description", "")}

**Session Conversation**:
{conv_summary}

## Analysis Instructions

Check if the agent ran tests locally and verified they pass:

**Evidence to look for**:
1. **Test execution**: Bash tool calls with test commands (pytest, npm test, cargo test, etc.)
2. **Test results**: Tool output showing test results
3. **Success indicators**: Exit code 0, "PASSED", "OK", "✓", green checkmarks
4. **Failure handling**: If tests failed, were they fixed and re-run?

**Common test patterns**:
- Python: pytest, unittest, python -m pytest
- JavaScript: npm test, yarn test, jest
- Rust: cargo test
- Go: go test
- Make: make test

**Respond with ONE of:**
- "SATISFIED: Tests run locally and passed [cite specific test commands and results]"
- "NOT SATISFIED: No evidence of local testing [explain what's missing]"

Be specific - reference actual tool calls, commands, and output."""


def _prompt_workflow_complete(consideration: Dict, conv_summary: str) -> str:
    """Specialized prompt for workflow/CI completion checking."""
    return f"""You are analyzing a Claude Code session to verify workflow completion.

**Consideration**: {consideration["question"]}
**Description**: {consideration.get("description", "")}

**Session Conversation**:
{conv_summary}

## Analysis Instructions

Check if the development workflow was followed completely:

**Workflow checkpoints**:
1. **Git operations**: Branch creation, commits, push
2. **CI/CD**: GitHub Actions triggered and passing
3. **Code review**: PR created (if applicable)
4. **Testing**: Local and CI tests passing
5. **Documentation**: Updated if needed

**Evidence to look for**:
- Bash tool calls with git commands (commit, push, etc.)
- CI status checks or GitHub API calls
- Discussion of workflow steps
- Explicit confirmation of completion

**Respond with ONE of:**
- "SATISFIED: Workflow completed [cite specific steps taken]"
- "NOT SATISFIED: Workflow incomplete [cite missing steps]"

Be specific - reference actual git commands, CI checks, and completion statements."""


def _prompt_generic_consideration(consideration: Dict, conv_summary: str) -> str:
    """Generic prompt for considerations without specific type."""
    # Current implementation (lines 160-181)
    return f"""You are analyzing a Claude Code session to determine if the following consideration is satisfied:

**Consideration**: {consideration["question"]}
**Description**: {consideration.get("description", consideration.get("question", ""))}
**Category**: {consideration.get("category", "General")}

**Session Conversation** ({len(conversation)} messages):
{conv_summary}

## Your Task

Analyze the conversation and determine if this consideration is satisfied.

**Respond with ONE of:**
- "SATISFIED: [brief reason]" if the consideration is met
- "NOT SATISFIED: [brief reason]" if the consideration is not met

Be direct and specific. Reference actual events from the conversation.
Focus on evidence - what tools were used, what actions were taken, what the user and assistant discussed.

If the consideration is not applicable to this session (e.g., no relevant work was done), respond with SATISFIED."""
```

**Key Enhancements**:

1. **Type-Specific Prompts**: Tailored instructions for each consideration type
2. **Concrete Examples**: Shows what evidence to look for
3. **Clear Criteria**: Explicit success/failure conditions
4. **Context Awareness**: Handles edge cases and exceptions

### Phase 3: Update Heuristic Methods to Document Fallback Role

**File**: `power_steering_checker.py`

**Change**: Update docstrings to clarify these are FALLBACK ONLY

```python
def _check_todos_complete(self, transcript: list[dict], session_id: str) -> bool:
    """Check if all TODO items completed (FALLBACK HEURISTIC).

    NOTE: This method is FALLBACK ONLY for when SDK unavailable.
    Primary analysis uses analyze_consideration() from claude_power_steering.py

    Heuristic approach:
    - Finds last TodoWrite tool call
    - Checks if all todos have status="completed"
    - Fails open (returns True) on any ambiguity

    Args:
        transcript: List of message dictionaries
        session_id: Session identifier

    Returns:
        True if all TODOs completed or ambiguous, False if clear incomplete todos
    """
    # ... existing implementation ...


def _check_philosophy_compliance(self, transcript: list[dict], session_id: str) -> bool:
    """Check for PHILOSOPHY adherence (FALLBACK HEURISTIC).

    NOTE: This method is FALLBACK ONLY for when SDK unavailable.
    Primary analysis uses analyze_consideration() from claude_power_steering.py

    Heuristic approach:
    - Searches for anti-patterns (TODO, FIXME, XXX, NotImplementedError)
    - Checks Write/Edit tool calls for stub code
    - Fails open (returns True) if no clear violations

    Args:
        transcript: List of message dictionaries
        session_id: Session identifier

    Returns:
        True if compliant or ambiguous, False if clear violations found
    """
    # ... existing implementation ...


def _check_local_testing(self, transcript: list[dict], session_id: str) -> bool:
    """Check if agent tested locally (FALLBACK HEURISTIC).

    NOTE: This method is FALLBACK ONLY for when SDK unavailable.
    Primary analysis uses analyze_consideration() from claude_power_steering.py

    Heuristic approach:
    - Searches for test commands in Bash tool calls
    - Checks exit codes and output for success indicators
    - Fails open (returns True) if no clear test failures

    Args:
        transcript: List of message dictionaries
        session_id: Session identifier

    Returns:
        True if tests passed or ambiguous, False if clear test failures
    """
    # ... existing implementation ...


def _generic_analyzer(
    self, transcript: list[dict], session_id: str, consideration: dict[str, Any]
) -> bool:
    """Generic analyzer for considerations (FALLBACK HEURISTIC).

    NOTE: This method is FALLBACK ONLY for when SDK unavailable.
    Primary analysis uses analyze_consideration() from claude_power_steering.py

    Heuristic approach:
    - Extracts keywords from consideration question
    - Simple token matching in transcript
    - Fails open (returns True) on any ambiguity

    Args:
        transcript: List of message dictionaries
        session_id: Session identifier
        consideration: Consideration dictionary with question

    Returns:
        True (fail-open default) - heuristics are too weak for confident blocking
    """
    # ... existing implementation ...
```

**Key Changes**:

1. **Clear Labeling**: All heuristics marked as "FALLBACK ONLY"
2. **Documentation**: Explain when/why they're used
3. **Fail-Open Emphasis**: Highlight that heuristics fail-open liberally
4. **No Implementation Changes**: Just docstring updates

## Fail-Open Strategy

### Principle: Never Block Users on Errors

**Implementation Levels**:

1. **SDK Unavailable**: Fall back to heuristics gracefully
2. **SDK Call Fails**: Catch exception, log, use heuristic fallback
3. **Heuristic Fails**: Return True (fail-open) to allow stop
4. **Timeout**: Return True to allow stop after reasonable wait

**Code Pattern** (already in Phase 1 changes):

```python
# SDK-FIRST: Try SDK for ALL considerations
if SDK_AVAILABLE:
    try:
        satisfied = await analyze_consideration(...)
        return CheckerResult(...)  # SDK succeeded
    except Exception as e:
        self._log(f"SDK failed: {e}", "DEBUG")
        # Continue to fallback

# FALLBACK: Use heuristics
try:
    satisfied = checker_func(transcript, session_id)
    return CheckerResult(...)
except Exception as e:
    self._log(f"Fallback failed: {e}", "WARNING")
    return CheckerResult(satisfied=True, ...)  # Fail-open
```

### Testing Fail-Open Behavior

**Test Scenarios**:

1. SDK import fails → Heuristics used
2. SDK call raises exception → Heuristics used
3. Heuristic raises exception → Returns True (allow stop)
4. Timeout exceeded → Returns True (allow stop)

## Migration Path

### Step 1: Fix Backwards Logic (Immediate)

- Change `_check_single_consideration_async` logic
- Invert SDK detection condition
- Add logging to track SDK vs fallback usage

### Step 2: Enhance SDK Prompts (Quick Win)

- Add type-specific prompt functions
- Deploy to production
- Monitor effectiveness via logs

### Step 3: Update Documentation (Final)

- Update heuristic docstrings
- Add architecture decision record
- Update README/PATTERNS.md

### Step 4: Monitor and Iterate

- Track SDK success rate
- Identify poorly-performing prompts
- Refine prompts based on real usage

## Success Metrics

**Quantitative**:

- SDK usage rate: Target 95%+ when available
- False positive rate: < 5% (blocking when work complete)
- False negative rate: < 10% (allowing when work incomplete)

**Qualitative**:

- User feedback on accuracy
- Reduction in "override" usage
- Developer confidence in system

## Risk Analysis

| Risk                       | Probability | Impact | Mitigation                             |
| -------------------------- | ----------- | ------ | -------------------------------------- |
| SDK call latency           | Medium      | Medium | Parallel execution, 60s timeout        |
| SDK unavailable            | Low         | Low    | Heuristic fallback automatic           |
| Poor prompt quality        | Medium      | Medium | Iterative refinement, A/B testing      |
| Breaking existing behavior | Low         | High   | Comprehensive testing, gradual rollout |

## Testing Strategy

### Unit Tests

- Test SDK-first logic with mocked SDK
- Test heuristic fallback when SDK fails
- Test fail-open on all error paths

### Integration Tests

- Real transcript analysis with SDK
- Comparison with heuristic results
- Performance benchmarks (latency)

### End-to-End Tests

- Full power steering run with various session types
- Verify backwards compatibility
- Test edge cases (empty transcript, malformed data)

## Implementation Checklist

- [ ] Update `_check_single_consideration_async` (SDK-first logic)
- [ ] Add type-specific prompt functions to `claude_power_steering.py`
- [ ] Update heuristic docstrings (mark as fallback)
- [ ] Add comprehensive logging (SDK vs fallback tracking)
- [ ] Write unit tests for new logic
- [ ] Write integration tests with real transcripts
- [ ] Update PATTERNS.md with new pattern
- [ ] Update architecture docs
- [ ] Deploy and monitor

## Philosophy Compliance

**Ruthless Simplicity**:

- SDK-first is simpler than complex heuristics
- Single code path for all considerations
- Clear fallback strategy

**Fail-Open**:

- Never blocks users on errors
- Graceful degradation at every level
- Explicit fail-open documentation

**Zero-BS**:

- No stubs or placeholder prompts
- Every function works or doesn't exist
- Real implementation from day one

**Modular Design**:

- Clean separation: SDK analysis vs heuristics
- Self-contained prompt module
- Clear contracts and dependencies

## Appendix: Alternative Designs Considered

### Option A: SDK-Only (Rejected)

**Pros**: Simplest code
**Cons**: Breaks fail-open principle
**Why Rejected**: Must work when SDK unavailable

### Option B: Heuristics-First (Rejected)

**Pros**: Always works
**Cons**: Defeats purpose of refactor
**Why Rejected**: Doesn't improve accuracy

### Option C: Hybrid with Voting (Rejected)

**Pros**: Most accurate
**Cons**: Complex, slow, expensive
**Why Rejected**: Violates ruthless simplicity

### Option D: SDK-First with Fallback (SELECTED)

**Pros**: Best of both worlds, fail-open, simple
**Cons**: Slightly more code than SDK-only
**Why Selected**: Balances accuracy with reliability

---

**Design Status**: READY FOR IMPLEMENTATION
**Next Step**: Create PR with Phase 1 changes
**Owner**: Builder agent
**Reviewer**: Architect agent
