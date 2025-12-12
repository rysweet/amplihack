# Investigation Summary Template

Use this template to document comprehensive investigation results that include both success paths AND failure scenarios.

## Why This Template Exists

**Problem**: Previous investigations focused on "how it works" without addressing "what could go wrong", edge cases, error handling, or limitations. This led to incomplete investigations requiring follow-up questions.

**Solution**: This template mandates comprehensive coverage of both architecture AND robustness, ensuring one-and-done investigations that users can rely on for production decisions.

## Quick Reference Template

Copy this structure and fill in each section:

```markdown
# Investigation: [System/Feature Name]

## 1. Architecture Overview

[High-level system design, components, data flow]

## 2. Key Components Deep Dive

[Detailed analysis of each component]

## 3. Integration Points

[How system connects to other systems]

## 4. Edge Cases & Error Handling ⭐

[What happens when things go wrong]

## 5. Known Limitations

[What system doesn't do or constraints]

## 6. Verification Results

[Testing performed and confidence level]
```

---

## Section 1: Architecture Overview

**Purpose**: Provide high-level understanding of how the system works without getting lost in details.

**Required Content**:

- System purpose and goals (1-2 sentences)
- Component diagram (mermaid, ASCII art, or bullet list)
- Data flow visualization (how information moves through the system)
- Key abstractions and patterns used

**Example**:

```markdown
## 1. Architecture Overview

### Purpose

The user preferences system enforces MANDATORY user preferences across all Claude Code interactions using a two-layer hook-based injection architecture.

### Component Diagram
```

Storage Layer (.claude/context/USER_PREFERENCES.md)
↓
Hook Layer (.claude/tools/amplihack/hooks/)
├─ session_start.py (loads FULL preferences at init)
└─ user_prompt_submit.py (re-injects concise preferences per message)
↓
Injection Layer (Claude Code context)
↓
Enforcement Layer (All agents and responses)

```

### Data Flow
1. Session starts → SessionStart hook reads USER_PREFERENCES.md
2. Hook extracts preferences using regex patterns
3. Hook returns JSON with additionalContext containing full preferences
4. Claude Code adds context to conversation (5,237 characters)
5. Every user message → UserPromptSubmit re-injects concise reminder
6. All agents receive preferences in their context

### Key Patterns
- **Hook-based injection**: Uses Claude Code's native hook system
- **Multi-strategy path resolution**: 4 fallback locations for file discovery
- **Graceful degradation**: System continues even if preferences unavailable
```

**Why This Matters**: Users need to understand the big picture before diving into details. A clear architecture overview prevents getting lost in implementation complexity.

---

## Section 2: Key Components Deep Dive

**Purpose**: Provide detailed understanding of each major component for troubleshooting and modification.

**Required Content (for each component)**:

- Component name and file location (absolute paths)
- Responsibility (what it does in one sentence)
- Contract: inputs, outputs, side effects
- Dependencies (what it relies on)
- Implementation approach (key algorithms or patterns)

**Example**:

````markdown
## 2. Key Components Deep Dive

### Component: SessionStart Hook

**File**: `.claude/tools/amplihack/hooks/session_start.py`

**Responsibility**: Load and inject user preferences at session initialization.

**Contract**:

- **Input**: JSON via stdin with `session_id`, `hook_event_name`, `cwd`
- **Output**: JSON via stdout with `hookSpecificOutput.additionalContext` containing full preferences
- **Side Effects**: Reads USER_PREFERENCES.md from disk, writes to session log

**Dependencies**:

- `FrameworkPathResolver`: Multi-strategy file path resolution
- `HookProcessor` base class: Standard hook interface
- `USER_PREFERENCES.md`: Preferences storage file

**Implementation**:

1. Receives hook trigger event from Claude Code
2. Uses FrameworkPathResolver to find USER_PREFERENCES.md (tries 4 locations)
3. Reads file content
4. Extracts preferences using regex patterns
5. Formats as structured context with MANDATORY header
6. Returns JSON response with additionalContext
7. Logs execution to `.claude/runtime/logs/session_start.log`

**Key Code Pattern**:

```python
preferences_path = resolver.find_file("USER_PREFERENCES.md")
if preferences_path and preferences_path.exists():
    content = preferences_path.read_text()
    return {"hookSpecificOutput": {"additionalContext": format_preferences(content)}}
else:
    return {}  # Graceful degradation
```
````

### Component: FrameworkPathResolver

**File**: `.claude/tools/amplihack/hooks/framework_path_resolver.py`

**Responsibility**: Find framework files using multi-strategy path resolution.

**Contract**:

- **Input**: Filename (e.g., "USER_PREFERENCES.md"), starting directory
- **Output**: Path object if found, None otherwise
- **Side Effects**: Traverses filesystem upward looking for `.claude/` directories

**Implementation**:
Four-strategy fallback approach:

1. Direct path: `{cwd}/.claude/context/{filename}`
2. Parent traversal: Walk up directories looking for `.claude/context/{filename}`
3. Framework root: Find `.claude/` dir and search from there
4. Absolute fallback: Try known absolute paths

**Why Four Strategies**: Handles various execution contexts (worktrees, subdirectories, CI environments).

````

**Why This Matters**: When debugging or modifying the system, users need to know exactly what each component does, where it lives, and how it works. This section provides the "implementation manual" for the system.

---

## Section 3: Integration Points

**Purpose**: Understand how the system connects to other systems and where coupling exists.

**Required Content**:
- List of all external systems/components this system interacts with
- Data exchange formats (JSON, API calls, files, etc.)
- Coupling points (tight vs. loose coupling)
- API contracts (if applicable)
- Configuration dependencies

**Example**:

```markdown
## 3. Integration Points

### Integration: Claude Code Hook System

**Connection Type**: Subprocess execution via stdin/stdout

**Data Exchange Format**:
- **Input** (Claude Code → Hook): JSON object via stdin
  ```json
  {
    "session_id": "string",
    "hook_event_name": "SessionStart",
    "cwd": "/absolute/path",
    "additional_context": {}
  }
````

- **Output** (Hook → Claude Code): JSON object via stdout
  ```json
  {
    "hookSpecificOutput": {
      "additionalContext": "markdown formatted preferences with MANDATORY header"
    }
  }
  ```

**Coupling**: Loose coupling through JSON interface, but depends on specific hook event names defined in `.claude/settings.json`.

**Error Handling**: Claude Code ignores hooks that return non-zero exit codes or malformed JSON.

### Integration: USER_PREFERENCES.md File

**Connection Type**: Direct file system access (read-only)

**Data Exchange Format**: Markdown file with YAML-style key-value pairs

```markdown
## User Preferences

**communication_style**: pirate
**verbosity**: detailed
**collaboration_style**: interactive
```

**Coupling**: Tight coupling to file location and format. Uses regex parsing, not YAML parser.

**Path Resolution**: Multi-strategy approach tries 4 locations (see FrameworkPathResolver).

**Error Handling**: Missing file → returns empty dict, system continues with defaults.

### Integration: Session Logs

**Connection Type**: File system writes

**Data Exchange Format**: Plain text log files in `.claude/runtime/logs/`

**Coupling**: Loose coupling - logs are informational only, not read by system.

**Purpose**: Debugging and auditing hook execution.

### Integration: /amplihack:customize Command

**Connection Type**: Claude Code native Read/Edit/Write tools

**Data Exchange Format**: Direct markdown file manipulation

**Coupling**: Shared file dependency on USER_PREFERENCES.md but no runtime coupling.

**Interaction**: Command modifies preferences file, hooks read it on next session.

````

**Why This Matters**: Integration points are where systems break. Understanding these connections helps debug issues, plan changes, and assess impact of modifications.

---

## Section 4: Edge Cases & Error Handling ⭐

**Purpose**: Understand what happens when things go wrong - the most critical section for production reliability.

**Required Content (test each scenario)**:
- **Malformed Input Handling**: How does system handle corrupted/invalid data?
- **Missing Dependencies**: What if required files/services don't exist?
- **Timeout Scenarios**: What happens if operations take too long?
- **Concurrent Access**: How are race conditions handled?
- **Resource Constraints**: Behavior under low memory/disk/network conditions?
- **Validation Failures**: What if data doesn't meet expected format?

**For Each Edge Case**:
- Scenario description
- Current handling approach
- Recovery mechanism (if any)
- Verification method (how you tested/confirmed)

**Example**:

```markdown
## 4. Edge Cases & Error Handling ⭐

### Malformed USER_PREFERENCES.md

**Scenario**: Preferences file contains invalid markdown, corrupted YAML, or unparseable content.

**Handling**:
- Hook attempts regex extraction on malformed content
- Invalid patterns don't match → sections come through as empty
- No exceptions thrown - graceful degradation
- Returns partial preferences (whatever could be parsed)
- Logs warning to `.claude/runtime/logs/session_start.log`

**Recovery**: System continues with defaults for unparseable preferences.

**Verified**: Examined hook_processor.py lines 67-89, regex patterns use try/except blocks implicitly through re.search() returning None on failure.

**Example Log Entry**:
````

2025-11-05 05:43:21 WARNING: Could not parse communication_style preference, using default

```

### Missing USER_PREFERENCES.md File

**Scenario**: File doesn't exist at any of the 4 fallback locations.

**Handling**:
1. FrameworkPathResolver tries all 4 strategies
2. All return None
3. Hook returns empty JSON: `{}`
4. Claude Code receives no additionalContext
5. Session continues with system defaults
6. No error shown to user

**Recovery**: Automatic fallback to defaults, system fully functional.

**Verified**:
- Tested by temporarily renaming USER_PREFERENCES.md
- Checked session_start.py lines 45-60 for None handling
- Confirmed session started successfully without file

**Log Output**:
```

INFO: USER_PREFERENCES.md not found, continuing with defaults

````

### Hook Execution Timeout (>10 seconds)

**Scenario**: SessionStart hook takes longer than 10-second timeout defined in `.claude/settings.json`.

**Handling**:
1. Claude Code kills hook process after 10 seconds
2. Logs timeout error to system logs
3. Treats as hook failure - no context injection
4. Session continues without preferences
5. User sees system-reminder about hook timeout

**Recovery**: Manual - investigate why hook is slow, fix underlying issue.

**Verified**:
- Examined `.claude/settings.json`: `"hook_timeout_seconds": 10`
- Confirmed timeout behavior in Claude Code documentation
- Did NOT test with artificial delay (would require code modification)

**Risk**: Hook should never take 10 seconds (typical execution: 50-100ms). If it does, indicates:
- File system performance issues
- Infinite loop in hook code
- Disk I/O bottleneck

### Concurrent Preference File Access

**Scenario**: Multiple Claude Code sessions (or /amplihack:customize command) access USER_PREFERENCES.md simultaneously.

**Handling**:
- **Read Operations**: Multiple concurrent reads are safe (read-only file access)
- **Write Operations**: No file locking mechanism exists
- **Race Condition**: If /amplihack:customize runs during session start, one operation may see incomplete file

**Recovery**: None - last write wins, potential for corrupted preferences.

**Verified**:
- Examined session_start.py and customize command code
- No file locking (fcntl, FileLock) present
- Standard Python read_text() / write_text() used

**Risk Level**: LOW - Concurrent writes are rare in practice (user must manually trigger /amplihack:customize during session init, which is < 1 second window).

**Mitigation**: Could add advisory file locking if this becomes an issue.

### Regex Pattern Extraction Failure

**Scenario**: Preferences use unexpected format that doesn't match regex patterns.

**Example**:
```markdown
communication_style=pirate  # No colon, different format
verbosity :: detailed        # Double colon
````

**Handling**:

- Regex patterns in hook use specific format: `\*\*key\*\*:\s*value`
- Non-matching lines are ignored silently
- Partial preferences returned (only what matched)
- No validation of preference values

**Recovery**: User sees default behavior for unmatched preferences.

**Verified**: Examined regex patterns in session_start.py lines 72-85.

**Risk**: Users could have invalid preferences active without knowing. Recommendation: Add validation in /amplihack:customize to prevent writing invalid formats.

### Resource Exhaustion: Large Preferences File

**Scenario**: USER_PREFERENCES.md is extremely large (>1MB) due to accumulated learned patterns or manual edits.

**Handling**:

- Python read_text() loads entire file into memory
- No size limit check
- Large context injection could exceed Claude Code context limits
- May cause performance degradation

**Recovery**: None - would require manual file cleanup or size limits.

**Verified**:

- No size checks in code
- Current file is ~2KB (typical)
- Claude Code context has soft limits (~100K tokens)

**Risk Level**: VERY LOW - preferences file would need to be 50x+ larger than current size to cause issues.

**Mitigation**: Could add size check (warn if >100KB) or truncate learned patterns section.

### Disk Full / Write Failure to Logs

**Scenario**: Session log directory doesn't exist or disk is full when hook tries to write logs.

**Handling**:

- Hook uses standard Python logging
- If log write fails, exception is swallowed by logging handler
- Hook continues execution
- Returns preferences successfully even if logging fails

**Recovery**: Automatic - logging failure doesn't impact core functionality.

**Verified**: Python logging module behavior - write failures don't raise exceptions by default.

**Risk**: Debugging becomes harder if logs aren't written, but core functionality unaffected.

````

**Why This Matters**: Understanding failure modes is as important as understanding success paths. This section ensures users can:
- Predict system behavior under adverse conditions
- Debug issues when they occur
- Assess production readiness
- Make informed architectural decisions

---

## Section 5: Known Limitations

**Purpose**: Set clear expectations about what the system doesn't do, can't do, or does poorly.

**Required Content**:
- Explicitly state what's out of scope
- Known bugs or quirks (with issue numbers if tracked)
- Performance limitations (throughput, latency, scale)
- Scalability constraints
- Compatibility requirements (versions, platforms, dependencies)
- Design trade-offs and their implications

**Example**:

```markdown
## 5. Known Limitations

### Preference Change Latency

**Limitation**: Preferences are loaded only at session start.

**Impact**:
- Changes to USER_PREFERENCES.md don't affect current session
- Must start new session to pick up changes
- No "reload preferences" command

**Workaround**: End session and start new one (stop → start).

**Why**: SessionStart hook only runs once. UserPromptSubmit hook is disabled (see `.claude/settings.json`).

**Could Be Fixed**: Enable UserPromptSubmit hook to re-read preferences on every message (performance trade-off: +50ms per message).

### No Validation on Preference Values

**Limitation**: Hook doesn't validate that preference values are from allowed enum.

**Impact**:
- Users can set invalid values: `communication_style: dinosaur`
- Invalid preferences get injected into context
- Claude Code tries to honor them (may behave unexpectedly)

**Workaround**: Use /amplihack:customize command which does basic validation.

**Why**: Hook focuses on speed (< 100ms), validation would add complexity.

**Could Be Fixed**: Add enum validation in hook with default fallback for invalid values.

### File System Dependency

**Limitation**: System requires local file system access for USER_PREFERENCES.md.

**Impact**:
- Doesn't support remote preference stores (database, API, cloud config)
- No synchronization between multiple machines
- No backup/restore mechanism
- Manual file management required

**Workaround**: Use version control (git) to sync preferences file across machines.

**Why**: Design prioritized simplicity over distributed configuration.

**Could Be Fixed**: Add plugin system for preference providers (file, database, API). Significant complexity increase.

### No Preference Inheritance or Profiles

**Limitation**: Single flat preferences file, no profiles or context-specific settings.

**Impact**:
- Can't have different preferences for different projects
- Can't have "work mode" vs "personal mode" profiles
- All projects share same communication style, verbosity, etc.

**Workaround**: Manually edit USER_PREFERENCES.md when switching contexts.

**Why**: Ruthless simplicity - profiles add significant complexity.

**Could Be Fixed**: Add profile system with selector in settings. Would require:
- Profile storage structure
- Profile switching mechanism
- Default profile selection
- 3-5x complexity increase

**Trade-off Decision**: Current design favors simplicity over flexibility. 80/20 rule: single preference set covers 80% of use cases.

### Hook Execution in Subprocess Context

**Limitation**: Hooks run in separate Python subprocess, not main Claude Code process.

**Impact**:
- Can't directly access Claude Code internal state
- Can't modify session state beyond context injection
- Limited to stdin/stdout JSON communication
- No shared memory or direct API access

**Workaround**: Use context injection to pass all needed information.

**Why**: Architectural isolation for security and stability.

**Cannot Be Fixed**: Fundamental design of Claude Code hook system.

### Performance: Regex-Based Parsing

**Limitation**: Uses regex patterns to parse preferences instead of proper YAML/TOML parser.

**Impact**:
- Fragile parsing - format must exactly match regex patterns
- No support for nested structures
- No support for comments mid-line
- Error-prone for complex preference values

**Workaround**: Keep preferences simple, one per line, clear format.

**Why**: Avoided external dependencies (yaml, toml libraries), kept hook lightweight.

**Could Be Fixed**: Switch to proper YAML parser. Trade-off: add dependency + 10-20ms parsing time.

### No Encryption or Access Control

**Limitation**: Preferences stored in plain text, no encryption or permission checks.

**Impact**:
- Anyone with file system access can read preferences
- Sensitive preferences (API keys, if stored) are exposed
- No audit trail of preference changes

**Workaround**: Don't store sensitive data in preferences file. Use environment variables or secure storage for secrets.

**Why**: Preferences are meant for behavior configuration, not secret storage.

**Best Practice**: USER_PREFERENCES.md should contain only non-sensitive behavioral preferences.
````

**Why This Matters**: Understanding limitations helps users:

- Set realistic expectations
- Avoid unsupported use cases
- Plan workarounds or alternatives
- Decide if the system meets their needs
- Understand design trade-offs

---

## Section 6: Verification Results

**Purpose**: Document what testing was performed and establish confidence level in findings.

**Required Content**:

- **Automated Tests**: Which test suites ran, results, coverage
- **Manual Verification**: Commands executed, files examined, results observed
- **Code Review**: Files analyzed, patterns confirmed
- **Log Analysis**: Log files examined, entries confirmed
- **Confidence Level**: Overall assessment (Low/Medium/High) with justification

**Example**:

````markdown
## 6. Verification Results

### Automated Tests

✅ **Test Suite**: `tests/test_user_prompt_submit_integration.py`

- **Test Count**: 12 test cases
- **Result**: All passing
- **Coverage**:
  - Preference injection on every message
  - Pirate style detection and application
  - Cache performance validation
  - Error handling with malformed files
  - Missing file graceful degradation
  - Concurrent access patterns

✅ **Test Suite**: `tests/test_session_start_hook.py`

- **Test Count**: 8 test cases
- **Result**: All passing
- **Coverage**:
  - Hook execution and JSON output
  - Path resolution with all 4 strategies
  - Preferences parsing and formatting
  - Log file creation

**Test Execution**:

```bash
cd /home/azureuser/src/MicrosoftHackathon2025-AgenticCoding
pytest tests/test_user_prompt_submit_integration.py -v
pytest tests/test_session_start_hook.py -v
# Output: 20 passed, 0 failed
```
````

### Manual Verification

✅ **Hook Execution Test** (Message 36-37)

**Command**:

```bash
echo '{"session_id":"test","hook_event_name":"SessionStart","cwd":"'$(pwd)'"}' | \
  .claude/tools/amplihack/hooks/session_start.py
```

**Result**:

- Returned valid JSON with additionalContext
- Preferences contained MANDATORY header
- Content size: 5,237 characters
- Execution time: ~85ms

**Verified**: Hook executes successfully and returns expected format.

✅ **Log Analysis** (Message 26-27)

**File**: `.claude/runtime/logs/session_start.log`

**Findings**:

```
2025-11-05 18:10:16 INFO: SessionStart hook triggered for session: 20251105_181016
2025-11-05 18:10:16 INFO: Successfully read preferences from: /home/azureuser/src/.claude/context/USER_PREFERENCES.md
2025-11-05 18:10:16 INFO: Injected 5237 characters of preference context
```

**Verified**:

- Hook ran today at expected time
- Found preferences file at correct location
- Injected expected amount of context

✅ **Code Review**

**Files Analyzed**:

- `.claude/tools/amplihack/hooks/session_start.py` (127 lines)
- `.claude/tools/amplihack/hooks/user_prompt_submit.py` (95 lines)
- `.claude/tools/amplihack/hooks/framework_path_resolver.py` (156 lines)
- `.claude/tools/amplihack/hooks/hook_processor.py` (89 lines)

**Patterns Confirmed**:

- Multi-strategy path resolution (4 fallback locations)
- Graceful degradation on missing files
- Regex-based preference extraction
- JSON stdin/stdout communication
- Logging to session-specific files

**Code Quality**: Well-structured, clear separation of concerns, appropriate error handling.

✅ **Configuration Verification**

**File**: `.claude/settings.json`

**Findings**:

```json
{
  "hooks": {
    "SessionStart": {
      "script": ".claude/tools/amplihack/hooks/session_start.py",
      "timeout_seconds": 10,
      "enabled": true
    },
    "UserPromptSubmit": {
      "script": ".claude/tools/amplihack/hooks/user_prompt_submit.py",
      "timeout_seconds": 10,
      "enabled": false
    }
  }
}
```

**Verified**:

- SessionStart hook enabled and configured
- UserPromptSubmit hook exists but disabled (explains no per-message re-injection)
- Timeout correctly set to 10 seconds

✅ **Path Resolution Test**

**Test**: Temporarily moved USER_PREFERENCES.md to test fallback strategies.

**Results**:

1. Strategy 1 (direct path): ✅ Found immediately
2. Strategy 2 (parent traversal): ✅ Found after moving to parent
3. Strategy 3 (framework root): ✅ Found when in .claude/context
4. Strategy 4 (absolute fallback): Not tested (would require code modification)

**Verified**: First 3 fallback strategies work correctly.

### Confidence Level

**OVERALL: HIGH (9/10)**

**Justification**:

- ✅ Automated test coverage for critical paths (20 tests passing)
- ✅ Manual verification of hook execution
- ✅ Log analysis confirms runtime behavior
- ✅ Code review of all 4 key components
- ✅ Configuration verification
- ✅ Path resolution testing with 3/4 strategies
- ⚠️ Not tested: Timeout scenario (would require artificial delay)
- ⚠️ Not tested: Concurrent write race condition (rare edge case)
- ⚠️ Not tested: Resource exhaustion with >1MB file (not realistic)

**What Would Increase Confidence to 10/10**:

- Test timeout scenario with mock sleep
- Test concurrent writes with threading
- Performance testing with various file sizes
- End-to-end integration test in live session

**Current Confidence Sufficient For**:

- Production use (with monitoring)
- Documentation and training
- Architectural decisions
- Troubleshooting common issues

**Not Sufficient For**:

- Formal verification or security audit
- Guarantees about untested edge cases
- Performance at extreme scale

````

**Why This Matters**: Verification results establish credibility and help users assess how much to trust the investigation. Clear documentation of what was and wasn't tested prevents over-confidence and guides future validation work.

---

## Template Usage Instructions

### When to Use This Template

Use this template for:
- ✅ System architecture investigations
- ✅ Feature deep-dives requiring production assessment
- ✅ Troubleshooting complex issues
- ✅ Onboarding documentation
- ✅ Design review preparation
- ✅ "How does X work?" questions where robustness matters

Do NOT use this template for:
- ❌ Trivial "how do I" questions
- ❌ Simple bug reports
- ❌ Quick code explanations
- ❌ Brainstorming sessions

### How to Use This Template

**Step 1: Copy Template Structure**
Copy the quick reference template at the top of this file.

**Step 2: Fill Sections Sequentially**
Complete sections in order 1→6. Early sections inform later ones.

**Step 3: Focus on Section 4**
Section 4 (Edge Cases & Error Handling) is the most critical. Spend 40% of investigation time here.

**Step 4: Be Specific with Examples**
Use real file paths, actual code snippets, concrete examples. Avoid generic descriptions.

**Step 5: Document Verification**
As you investigate, document how you verified each finding (tests run, files examined, commands executed).

**Step 6: Assess Confidence**
Be honest about confidence level and what wasn't tested. Users need to know limitations of the investigation itself.

### Quality Checklist

Before considering an investigation complete, verify:

- [ ] All 6 sections present and filled out
- [ ] Section 4 includes at least 4 edge cases tested
- [ ] Real examples used throughout (not placeholders)
- [ ] File paths are absolute, not relative
- [ ] Verification method documented for each major finding
- [ ] Known limitations explicitly stated
- [ ] Confidence level justified with evidence
- [ ] Investigation answers "does it actually work?" question
- [ ] No TODOs or unfinished sections

### Integration with Investigation Workflows

If using INVESTIGATION_WORKFLOW.md (Issue #1095), this template should be used during the final **Synthesis Phase**:

```markdown
## Phase 4: Synthesis and Documentation

**Objective**: Synthesize findings into comprehensive documentation.

**Activities**:
1. Use INVESTIGATION_SUMMARY_TEMPLATE.md to structure findings
2. Ensure all 6 sections completed
3. Emphasize Section 4 (Edge Cases & Error Handling)
4. Document verification methods and confidence level
5. Create final investigation report
````

### Philosophy Alignment

This template aligns with project philosophy:

**Ruthless Simplicity**:

- 6 sections, no more needed
- Each section has clear purpose
- No bureaucratic overhead

**Zero-BS Implementation**:

- No placeholders or TODOs allowed
- Every claim must be verified
- Confidence level must be justified

**Trust in Emergence**:

- Comprehensive template enables emergent understanding
- Users can trust investigations for production decisions

### Common Pitfalls to Avoid

**Pitfall 1: Skipping Section 4**
Section 4 is the most important. Don't treat it as optional or rush through it.

**Pitfall 2: Generic Examples**
"System handles errors gracefully" is useless. Specific: "When USER_PREFERENCES.md is missing, hook returns {} and logs warning to session_start.log".

**Pitfall 3: Untested Claims**
Don't claim something works unless you verified it. If you didn't test it, say so.

**Pitfall 4: Hiding Limitations**
Known limitations aren't failures - they're honest engineering. Document them clearly.

**Pitfall 5: Over-Confidence**
Be honest about what wasn't tested and what confidence level is appropriate.

---

## Meta: This Template Itself

**Created**: 2025-11-05
**Issue**: #1099
**Author**: Architect + Builder agents
**Status**: Initial version
**Feedback**: Please report issues or suggestions to improve this template

**Improvement Ideas for Future Versions**:

- Add mermaid diagram examples for Section 1
- Provide more edge case categories in Section 4
- Include performance testing guidance in Section 6
- Add template for comparing multiple approaches
