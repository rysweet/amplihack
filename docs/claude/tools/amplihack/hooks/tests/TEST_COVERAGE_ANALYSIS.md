# Test Coverage Analysis: Session Classification (Issue #1492)

## Test Coverage Summary

### Total Tests: 31

- **Session Type Detection**: 12 tests
- **Selective Consideration Application**: 6 tests
- **Edge Cases**: 5 tests
- **Environment Overrides**: 2 tests
- **Backward Compatibility**: 2 tests
- **Heuristics**: 4 tests

## Coverage by Session Type

### 1. DEVELOPMENT Sessions (5 tests)

✓ With PR and CI
✓ Without PR
✓ Mixed session (Q&A + development)
✓ Code file extensions
✓ Full workflow checks applied

**Critical Paths Covered**:

- PR creation detected
- Code changes detected (Write/Edit on .py, .js, etc.)
- Test execution detected
- CI checks applied
- All considerations active

**Edge Cases**:

- Development without PR yet
- Development with incomplete TODOs (should block)

### 2. INFORMATIONAL Sessions (6 tests)

✓ Q&A only (no tools)
✓ Q&A with Read tools
✓ Single Read tool
✓ High question density
✓ Skips PR checks
✓ Skips CI checks
✓ Skips testing checks

**Critical Paths Covered**:

- Pure Q&A detection
- Read-only exploration
- No workflow checks applied
- Approval without development requirements

**Edge Cases**:

- Empty transcript defaults to INFORMATIONAL
- Single tool use is INFORMATIONAL

### 3. MAINTENANCE Sessions (4 tests)

✓ Documentation updates only
✓ Configuration file changes
✓ Git commit cleanup
✓ Minimal checks applied

**Critical Paths Covered**:

- .md, .txt, .yml file modifications
- Git operations without code changes
- Documentation and organization checks only

**Edge Cases**:

- Git commits for cleanup

### 4. INVESTIGATION Sessions (3 tests)

✓ Read-only exploration
✓ Multiple Grep/search operations
✓ Documentation checks applied

**Critical Paths Covered**:

- Multiple Read/Grep tools
- Analysis without modification
- Investigation docs required

**Edge Cases**:

- Multiple reads triggers INVESTIGATION

## Coverage by Feature

### Session Type Detection

- ✓ Development indicators (code files, tests, PR)
- ✓ Informational indicators (questions, no tools)
- ✓ Maintenance indicators (docs, config only)
- ✓ Investigation indicators (read-only, search)
- ✓ Mixed session prioritization
- ✓ Empty transcript handling

### Selective Consideration Application

- ✓ PR checks skipped for INFORMATIONAL
- ✓ CI checks skipped for INFORMATIONAL
- ✓ Testing checks skipped for INFORMATIONAL
- ✓ All checks applied for DEVELOPMENT
- ✓ Minimal checks for MAINTENANCE
- ✓ Investigation docs for INVESTIGATION

### Environment Overrides

- ✓ AMPLIHACK_SESSION_TYPE env var
- ✓ Invalid override handling

### Backward Compatibility

- ✓ Existing \_is_qa_session still works
- ✓ Missing detect_session_type doesn't crash

### Consideration Mapping

- ✓ DEVELOPMENT gets all considerations
- ✓ INFORMATIONAL gets minimal set
- ✓ MAINTENANCE gets docs + organization
- ✓ INVESTIGATION gets investigation docs

## Coverage Gaps Identified

### Missing Tests (To Add Later)

1. **Session Type Transitions**
   - Session that starts as INFORMATIONAL and becomes DEVELOPMENT
   - How to handle mid-session type changes

2. **Multiple PR Workflow**
   - Session with multiple PR operations
   - PR review cycle detection

3. **Complex Tool Patterns**
   - Bash commands that are neither tests nor git
   - Write operations that aren't code (data files)

4. **Consideration Enabling/Disabling**
   - Session type with disabled considerations
   - Custom consideration mapping

5. **Performance**
   - Large transcripts (1000+ messages)
   - Timeout handling for classification

### Not Covered (Out of Scope)

- LLM-based classification (future enhancement)
- User feedback learning
- Session type statistics
- Classification confidence scores

## Test Quality Metrics

### Boundary Coverage

- ✓ Empty transcripts
- ✓ Single message transcripts
- ✓ Mixed session types
- ✓ Invalid data handling

### Error Handling

- ✓ Missing methods (backward compatibility)
- ✓ Invalid environment variables
- ✓ Malformed transcripts (handled by existing loader)

### State Coverage

- ✓ Fresh session (no prior state)
- ✓ Session with redirects (handled by existing tests)

## Implementation Guidance

### Required Methods (From Tests)

1. `detect_session_type(transcript: List[Dict]) -> str`
   - Returns: "DEVELOPMENT", "INFORMATIONAL", "MAINTENANCE", "INVESTIGATION"
   - Must check AMPLIHACK_SESSION_TYPE env var first
   - Falls back to heuristic detection

2. `get_applicable_considerations(session_type: str) -> List[Dict]`
   - Returns filtered list of considerations for session type
   - Maps considerations to applicable session types

### Required Logic

1. **Session Type Detection Heuristics**:

   ```python
   # DEVELOPMENT indicators
   - Write/Edit to code files (.py, .js, .ts, etc.)
   - Test execution (pytest, npm test, etc.)
   - PR operations (gh pr create, etc.)

   # INFORMATIONAL indicators
   - No tool usage OR only Read tools
   - High question density (>50% messages with ?)
   - Short sessions (<5 messages)

   # MAINTENANCE indicators
   - Only doc/config file changes (.md, .txt, .yml)
   - Git operations without code changes

   # INVESTIGATION indicators
   - Multiple Read/Grep operations
   - No Write/Edit operations
   - Analysis keywords in messages
   ```

2. **Consideration Filtering**:

   ```python
   CONSIDERATION_MAPPING = {
       "DEVELOPMENT": ["*"],  # All considerations
       "INFORMATIONAL": [
           "objective_completion",
           "agent_unnecessary_questions",
       ],
       "MAINTENANCE": [
           "objective_completion",
           "documentation_updates",
           "docs_organization",
           "philosophy_compliance",
       ],
       "INVESTIGATION": [
           "objective_completion",
           "investigation_docs",
           "documentation_updates",
       ],
   }
   ```

3. **Integration Points**:
   - Modify `_analyze_considerations()` to call `get_applicable_considerations()`
   - Add `detect_session_type()` call at start of `check()`
   - Store session type in analysis for logging

## Expected Test Results (TDD)

### Current State (Before Implementation)

All tests should FAIL with:

- `AttributeError: 'PowerSteeringChecker' has no attribute 'detect_session_type'`
- `AttributeError: 'PowerSteeringChecker' has no attribute 'get_applicable_considerations'`

### After Implementation

All 31 tests should PASS, validating:

- Session type detection works correctly
- Considerations are selectively applied
- False positives eliminated for INFORMATIONAL sessions
- Backward compatibility maintained

## Test Execution

### Run All Tests

```bash
python3 -m pytest .claude/tools/amplihack/hooks/tests/test_session_classification.py -v
```

### Run Specific Test Class

```bash
python3 -m pytest .claude/tools/amplihack/hooks/tests/test_session_classification.py::TestSessionClassification -v
```

### Run Single Test

```bash
python3 -m pytest .claude/tools/amplihack/hooks/tests/test_session_classification.py::TestSessionClassification::test_detect_informational_session_qa_only -v
```

## Success Criteria

### All Tests Pass

- Session type detection: 12/12
- Consideration application: 6/6
- Edge cases: 5/5
- Environment: 2/2
- Backward compatibility: 2/2
- Heuristics: 4/4

### No Regressions

- Existing power_steering_checker tests still pass
- Q&A detection still works
- Fail-open behavior maintained

### Issue #1492 Resolved

- INFORMATIONAL sessions no longer blocked
- PR checks skipped when no PR exists
- CI checks skipped when no code changes
- Testing checks skipped when no tests needed
