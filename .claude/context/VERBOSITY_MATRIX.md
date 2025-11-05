# Verbosity Adjustment Matrix

## Overview

This document defines how user verbosity preferences dynamically adapt based on task complexity and type. It provides clear mappings that guide message frequency and update patterns during workflow execution.

## Purpose

- Prevent verbosity mismatch (e.g., 165 messages for "balanced" when 40-60 expected)
- Adapt message frequency to task context (complexity + type)
- Maintain user preference as foundation while adjusting intelligently
- Provide measurable targets for session message counts

## Task Complexity Levels

Complexity is assessed on a 1-13 scale based on quantitative criteria:

### Simple (1-4/13)

- **File count**: 1-2 files affected
- **Integration points**: 0-1 external dependencies
- **Architectural impact**: No architecture changes
- **Examples**: Single-file bug fix, documentation update, config change

### Moderate (5-8/13)

- **File count**: 3-7 files affected
- **Integration points**: 2-4 external dependencies
- **Architectural impact**: Minor module changes, no system redesign
- **Examples**: Multi-file feature, moderate refactoring, investigation tasks

### Complex (9-13/13)

- **File count**: 8+ files affected
- **Integration points**: 5+ external dependencies
- **Architectural impact**: System redesign, breaking changes, cross-module coordination
- **Examples**: Major features, architecture refactoring, complex debugging

## Task Type Definitions

Task types are identified by keyword analysis of the task description:

### Investigation

- **Keywords**: "investigate", "explain", "understand", "how does", "why", "analyze", "explore", "research"
- **Characteristics**: Read-heavy, analysis-focused, no implementation
- **Verbosity needs**: Summary-focused, findings over process

### Implementation

- **Keywords**: "add", "create", "build", "implement", "develop", "write", "code"
- **Characteristics**: Write-heavy, building new functionality
- **Verbosity needs**: Progress updates during long builds

### Debugging

- **Keywords**: "fix", "debug", "resolve", "error", "issue", "problem", "broken"
- **Characteristics**: Problem-solving, iterative diagnosis
- **Verbosity needs**: Discovery updates as issues are found

### Refactoring

- **Keywords**: "refactor", "restructure", "simplify", "cleanup", "reorganize", "improve"
- **Characteristics**: Transformative, code quality focus
- **Verbosity needs**: Phase updates, before/after summaries

## Verbosity Matrix

| User Preference | Task Type      | Complexity | Update Frequency | Message Target   | Notes                   |
| --------------- | -------------- | ---------- | ---------------- | ---------------- | ----------------------- |
| **Concise**     | Investigation  | Simple     | Minimal          | 10-15 messages   | Findings only           |
| **Concise**     | Investigation  | Moderate   | Minimal          | 15-25 messages   | Key discoveries         |
| **Concise**     | Investigation  | Complex    | Regular          | 30-40 messages   | Phase summaries         |
| **Concise**     | Implementation | Simple     | Minimal          | 12-18 messages   | Start/end only          |
| **Concise**     | Implementation | Moderate   | Regular          | 25-35 messages   | Major milestones        |
| **Concise**     | Implementation | Complex    | Regular          | 45-60 messages   | Component completion    |
| **Concise**     | Debugging      | Simple     | Regular          | 15-20 messages   | Problem + solution      |
| **Concise**     | Debugging      | Moderate   | Regular          | 25-35 messages   | Diagnostic steps        |
| **Concise**     | Debugging      | Complex    | Frequent         | 40-55 messages   | Iterative discoveries   |
| **Concise**     | Refactoring    | Simple     | Minimal          | 10-15 messages   | Before/after            |
| **Concise**     | Refactoring    | Moderate   | Regular          | 20-30 messages   | Phase transitions       |
| **Concise**     | Refactoring    | Complex    | Regular          | 35-50 messages   | Module completions      |
| **Balanced**    | Investigation  | Simple     | Minimal          | 15-20 messages   | Consolidated findings   |
| **Balanced**    | Investigation  | Moderate   | Regular          | 30-45 messages   | ← CURRENT ISSUE FIX     |
| **Balanced**    | Investigation  | Complex    | Regular          | 50-70 messages   | Comprehensive analysis  |
| **Balanced**    | Implementation | Simple     | Regular          | 18-25 messages   | Progress checkpoints    |
| **Balanced**    | Implementation | Moderate   | Regular          | 40-60 messages   | Standard progress       |
| **Balanced**    | Implementation | Complex    | Frequent         | 70-100 messages  | Detailed progress       |
| **Balanced**    | Debugging      | Simple     | Regular          | 18-25 messages   | Full diagnostic         |
| **Balanced**    | Debugging      | Moderate   | Regular          | 35-50 messages   | Iterative diagnosis     |
| **Balanced**    | Debugging      | Complex    | Frequent         | 60-85 messages   | Comprehensive debug     |
| **Balanced**    | Refactoring    | Simple     | Regular          | 15-22 messages   | Transformation steps    |
| **Balanced**    | Refactoring    | Moderate   | Regular          | 30-45 messages   | Phase details           |
| **Balanced**    | Refactoring    | Complex    | Frequent         | 55-80 messages   | Module-by-module        |
| **Detailed**    | Investigation  | Simple     | Regular          | 25-35 messages   | Full exploration        |
| **Detailed**    | Investigation  | Moderate   | Frequent         | 60-90 messages   | Detailed analysis       |
| **Detailed**    | Investigation  | Complex    | Verbose          | 100-150 messages | Comprehensive deep dive |
| **Detailed**    | Implementation | Simple     | Regular          | 30-40 messages   | All checkpoints         |
| **Detailed**    | Implementation | Moderate   | Frequent         | 70-100 messages  | All progress updates    |
| **Detailed**    | Implementation | Complex    | Verbose          | 120-180 messages | Full detail             |
| **Detailed**    | Debugging      | Simple     | Frequent         | 30-40 messages   | Every diagnostic step   |
| **Detailed**    | Debugging      | Moderate   | Frequent         | 60-85 messages   | Full investigation      |
| **Detailed**    | Debugging      | Complex    | Verbose          | 100-140 messages | Exhaustive debug log    |
| **Detailed**    | Refactoring    | Simple     | Regular          | 25-35 messages   | All transformation      |
| **Detailed**    | Refactoring    | Moderate   | Frequent         | 50-75 messages   | Detailed phases         |
| **Detailed**    | Refactoring    | Complex    | Verbose          | 90-130 messages  | Complete narration      |

## Update Frequency Definitions

### Minimal

**Message Pattern**: Milestone updates only

- Phase start announcements
- Phase completion summaries
- Final results presentation

**Characteristics**:

- No intermediate status messages
- Batch tool results into summaries
- Skip play-by-play narration

**Example Flow**:

1. "Starting investigation of codebase structure..."
2. [Multiple tool calls batched]
3. "Investigation complete. Key findings: [summary]"

**Typical Message Count**: 3-5 messages per phase

### Regular

**Message Pattern**: Phase updates with consolidated progress

- Phase start/end announcements
- Mid-phase progress for long-running operations
- Consolidated tool result summaries

**Characteristics**:

- Phase transition updates
- No individual tool invocation announcements
- Summaries instead of step-by-step

**Example Flow**:

1. "Beginning implementation phase..."
2. [Tool calls happen silently]
3. "Completed 3 of 5 modules. Continuing..."
4. [More tool calls]
5. "Implementation complete. All modules functional."

**Typical Message Count**: 5-8 messages per phase

### Frequent

**Message Pattern**: Sub-phase updates with progress indicators

- Phase and sub-phase transitions
- Progress indicators for multi-step operations
- Tool invocation summaries (batched, not individual)

**Characteristics**:

- More granular progress tracking
- Batch related tool calls together
- Provide context for long operations

**Example Flow**:

1. "Starting implementation phase (5 modules)..."
2. "Implementing Module 1: User Authentication..."
3. [Tool calls batched]
4. "Module 1 complete. Moving to Module 2..."
5. [Continue for each module]
6. "All modules implemented successfully."

**Typical Message Count**: 10-15 messages per phase

### Verbose

**Message Pattern**: Comprehensive play-by-play narration

- All phase and sub-phase transitions
- Individual significant tool invocations
- Detailed progress narration
- Comprehensive status updates

**Characteristics**:

- Maximum transparency
- User sees most operations
- Suitable for learning or debugging complex issues

**Example Flow**:

1. "Starting implementation phase..."
2. "Creating Module 1: User Authentication..."
3. "Reading existing auth patterns..." [Tool call]
4. "Found 3 existing patterns. Analyzing..."
5. "Implementing new auth flow..."
6. [Each significant step gets an update]
7. "Module 1 complete. Testing integration..."
8. "Tests passing. Moving to Module 2..."

**Typical Message Count**: 20-30 messages per phase

## Message Batching Rules

These rules help achieve target message counts without losing information quality.

### Rule 1: Batch Independent Tool Calls

**Anti-pattern** (5 messages):

```
Message 1: "Let me check the logs"
Message 2: [Bash: tail logs]
Message 3: "Let me check the metrics"
Message 4: [Bash: tail metrics]
Message 5: "The logs show X and metrics show Y"
```

**Optimized pattern** (1 message):

```
Message 1: "Let me check logs and metrics for verification..."
  [Bash call 1: tail logs]
  [Bash call 2: tail metrics]
  "Logs show X, metrics show Y"
```

**Savings**: 80% reduction (5 → 1 messages)

### Rule 2: Combine Status with Action

**Anti-pattern** (3 messages):

```
Message 1: "Now I'll analyze the codebase structure"
Message 2: [Read files, analyze]
Message 3: "Analysis complete. Found 3 key modules."
```

**Optimized pattern** (1-2 messages):

```
Message 1: "Analyzing codebase structure..."
  [Read files, analyze]
  "Found 3 key modules: [details]"
```

**Savings**: 33-50% reduction (3 → 1-2 messages)

### Rule 3: Summary Over Play-by-Play

**Anti-pattern** (5 messages):

```
Message 1: "Found session_start.py"
Message 2: "Reading session_start.py"
Message 3: "It loads preferences from USER_PREFERENCES.md"
Message 4: "Now checking if caching is used"
Message 5: "Yes, caching is implemented"
```

**Optimized pattern** (1-2 messages):

```
Message 1: "Analyzing session startup process..."
  [Analysis happens]
  "Key findings: Loads preferences from USER_PREFERENCES.md with caching for performance"
```

**Savings**: 60-80% reduction (5 → 1-2 messages)

## Task Complexity Assessment Algorithm

When starting a task (Step 1.5 of workflow):

```
1. Count affected files/components:
   - Read task description
   - Identify modules mentioned
   - Estimate file count

2. Identify integration points:
   - External APIs or services
   - Cross-module dependencies
   - Database or storage interactions

3. Evaluate architectural impact:
   - Breaking changes? +3 points
   - New modules? +2 points per module
   - Refactoring existing? +1-2 points

4. Calculate score (1-13):
   Simple: 1-4 points
   Moderate: 5-8 points
   Complex: 9-13 points
```

**Examples**:

- "Fix typo in README.md" → 1 file, 0 integration, 0 architecture = **1/13 (Simple)**
- "Add dark mode toggle to settings" → 3 files, 1 integration (theme system), minor architecture = **5/13 (Moderate)**
- "Migrate from REST to GraphQL" → 15+ files, 10+ integration points, major architecture = **12/13 (Complex)**

## Task Type Identification Algorithm

```
1. Extract keywords from task description:
   - Convert to lowercase
   - Tokenize into words
   - Match against keyword lists

2. Score by category:
   - Investigation: Count investigation keywords
   - Implementation: Count implementation keywords
   - Debugging: Count debugging keywords
   - Refactoring: Count refactoring keywords

3. Select highest-scoring category:
   - If tie, prefer in order: Debugging > Implementation > Investigation > Refactoring

4. Default: If no keywords match → Implementation
```

**Examples**:

- "Investigate why the auth system is slow" → **Investigation** (keywords: investigate, why)
- "Fix the broken login button" → **Debugging** (keywords: fix, broken)
- "Add user profile page" → **Implementation** (keyword: add)
- "Refactor database queries for clarity" → **Refactoring** (keyword: refactor)

## Integration with Workflow

### Step 1.5: Analyze Task for Verbosity Adjustment

(Added between Step 1 and Step 2 in DEFAULT_WORKFLOW.md)

Before proceeding with execution:

1. **Assess Task Complexity**:
   - Count affected files/components
   - Identify integration points
   - Evaluate architectural impact
   - Assign complexity score (1-13)

2. **Identify Task Type**:
   - Extract keywords from task description
   - Match against type definitions
   - Select primary task type

3. **Look Up Verbosity Setting**:
   - Read USER_PREFERENCES.md
   - Extract current verbosity value (concise/balanced/detailed)

4. **Calculate Target Message Count**:
   - Use Verbosity Matrix table
   - Look up [preference × complexity × type]
   - Note target message range and update frequency

5. **Log Decision**:
   - Record in session logs: "Verbosity target: 30-45 messages (balanced × moderate × investigation)"
   - Use target to guide batching throughout session

6. **Apply Throughout Session**:
   - Follow update frequency guidelines
   - Apply message batching rules
   - Aim for target range (some variance acceptable)

## Usage Examples

### Example 1: Moderate Investigation Task with Balanced Verbosity

**Task**: "Investigate how user preferences are loaded and cached"

**Step 1.5 Analysis**:

- Complexity: 5-6 files to examine, 2 integration points → **6/13 (Moderate)**
- Task Type: Keywords "investigate", "how" → **Investigation**
- User Preference: Read from USER_PREFERENCES.md → **Balanced**

**Matrix Lookup**: Balanced × Moderate × Investigation = **30-45 messages, Regular frequency**

**Expected Behavior**:

- Phase announcements (start investigation, complete investigation)
- Consolidated findings per module examined
- No play-by-play file reading narration
- Summary of key discoveries
- Target: 30-45 messages total

**Previous Baseline**: 165 messages (current issue)
**Improvement**: 70% reduction

### Example 2: Simple Implementation Task with Concise Verbosity

**Task**: "Add dark mode toggle to settings page"

**Step 1.5 Analysis**:

- Complexity: 3 files (settings.tsx, theme.ts, config.ts), 1 integration point → **4/13 (Simple)**
- Task Type: Keyword "add" → **Implementation**
- User Preference: **Concise**

**Matrix Lookup**: Concise × Simple × Implementation = **12-18 messages, Minimal frequency**

**Expected Behavior**:

- Start implementation announcement
- Milestone updates (component created, theme integrated, testing complete)
- Final confirmation
- Target: 12-18 messages total

### Example 3: Complex Debugging Task with Detailed Verbosity

**Task**: "Debug intermittent crashes in distributed worker system"

**Step 1.5 Analysis**:

- Complexity: 10+ files (workers, scheduler, network), 8+ integration points → **11/13 (Complex)**
- Task Type: Keyword "debug", "crashes" → **Debugging**
- User Preference: **Detailed**

**Matrix Lookup**: Detailed × Complex × Debugging = **100-140 messages, Verbose frequency**

**Expected Behavior**:

- Detailed diagnostic steps
- Each hypothesis tested gets an update
- Log analysis narration
- Discovery announcements as root cause emerges
- Comprehensive debugging trace
- Target: 100-140 messages total

## Testing and Validation

### Test Scenario 1: Simple Investigation + Balanced

- **Task**: "Explain how the lock system works"
- **Expected**: 15-20 messages with milestone updates only
- **Validation**: Count messages, verify no play-by-play, confirm key findings communicated

### Test Scenario 2: Moderate Investigation + Concise

- **Task**: Same user preferences investigation (baseline comparison)
- **Expected**: 15-25 messages with minimal updates
- **Validation**: Compare to 165-message baseline, measure reduction

### Test Scenario 3: Complex Implementation + Detailed

- **Task**: "Implement new consensus workflow with multi-agent coordination"
- **Expected**: 120-180 messages with comprehensive updates
- **Validation**: Ensure no important details lost, user can follow progress

## Success Metrics

### Immediate (First Month)

- Investigation sessions with "balanced" verbosity: **30-45 messages average** (from 165 baseline)
- Message count variance: **<20%** (consistent experience)
- User satisfaction: **"Verbosity matches expectation" >80%**
- Zero complaints about message spam

### Long-term (3 Months)

- Verbosity matrix refined based on actual usage patterns
- Session logs show consistent verbosity decision recording
- Preference system trust score increases
- Message batching becomes natural workflow behavior

## Maintenance and Evolution

### Updating the Matrix

- Review session logs monthly for message count patterns
- Adjust targets if consistent over/under-shooting
- Gather user feedback on verbosity experience
- Update matrix values based on data

### Adding New Task Types

1. Identify new task pattern from usage analysis
2. Define keywords for detection
3. Add rows to matrix for all complexity/verbosity combinations
4. Test with sample tasks
5. Update documentation

### Philosophy Alignment

- **Ruthless Simplicity**: Matrix is clear, measurable, easy to understand
- **User-Centric**: Respects user preferences as MANDATORY foundation
- **Measurable**: Concrete message targets, not vague guidance
- **Adaptive**: Intelligent adjustment without breaking user expectations

## Related Documentation

- `.claude/workflow/DEFAULT_WORKFLOW.md` - Workflow integration (Step 1.5)
- `.claude/context/USER_PREFERENCES.md` - User verbosity preference storage
- `.claude/runtime/logs/` - Session logs for verbosity decision tracking
- Issue #1100 - Original issue describing the problem

---

**Last Updated**: 2025-11-05
**Version**: 1.0
**Status**: Active
