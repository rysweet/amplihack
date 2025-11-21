# PM Architect - Usage Examples

This document provides real-world examples of using PM Architect for different project types.

## Example 1: CLI Tool Development

**Scenario**: Building a new CLI tool for file processing.

### Step 1: Initialize

```bash
/pm:init
```

**Responses:**

```
Project name [my-cli]: file-processor
Project type:
  1. cli-tool
Select [1]: 1

Primary goals (one per line, empty line to finish):
  Goal 1: Fast file processing
  Goal 2: Simple, intuitive commands
  Goal 3: Excellent error messages
  Goal 4:

Quality bar:
  1. strict
  2. balanced
  3. relaxed
Select [2]: 2

✅ PM INITIALIZED: file-processor
```

### Step 2: Add Backlog Items

```bash
/pm:add "Implement core file parser" --priority HIGH --estimated-hours 6
/pm:add "Add command-line argument parsing" --priority HIGH --estimated-hours 4
/pm:add "Implement batch processing" --priority MEDIUM --estimated-hours 8
/pm:add "Add progress bar for long operations" --priority MEDIUM --estimated-hours 3
/pm:add "Write user documentation" --priority LOW --estimated-hours 4
/pm:add "Add shell completion scripts" --priority LOW --estimated-hours 2
```

**Result:**

```
✅ Added BL-001: Implement core file parser [HIGH]
✅ Added BL-002: Add command-line argument parsing [HIGH]
✅ Added BL-003: Implement batch processing [MEDIUM]
✅ Added BL-004: Add progress bar for long operations [MEDIUM]
✅ Added BL-005: Write user documentation [LOW]
✅ Added BL-006: Add shell completion scripts [LOW]
```

### Step 3: Check Status

```bash
/pm:status
```

**Output:**

```
════════════════════════════════════════════════════════════
PROJECT: file-processor [cli-tool]
════════════════════════════════════════════════════════════

⚡ ACTIVE WORKSTREAMS: None

📋 BACKLOG (6 items ready):
  • BL-001: Implement core file parser [HIGH] - READY
  • BL-002: Add command-line argument parsing [HIGH] - READY
  • BL-003: Implement batch processing [MEDIUM] - READY
  • BL-004: Add progress bar for long operations [MEDIUM] - READY
  • BL-005: Write user documentation [LOW] - READY
  ... and 1 more

📊 PROJECT HEALTH: 🟡 IDLE
   Quality Bar: balanced
   Active: 0 workstream
```

### Step 4: Start First Workstream

```bash
/pm:start BL-001 --agent builder
```

**Process:**

```
PM: Preparing delegation package...
    Title: Implement core file parser
    Priority: HIGH
    Agent: builder
    Estimated: 6 hours

Start workstream? [y/N]: y

PM: Starting builder agent for workstream ws-001
PM: Title: Implement core file parser
PM: Log: .pm/logs/pm-builder-ws-001.log

[Agent begins work...]

PM: Agent completed (exit code: 0)
PM: Duration: 45.2s

✅ Workstream ws-001 started
   Title: Implement core file parser
   Agent: builder
   Estimated: 6 hours

Monitor: /pm:status ws-001
```

### Step 5: Monitor Progress

```bash
/pm:status ws-001
```

**Output:**

```
════════════════════════════════════════════════════════════
WORKSTREAM: ws-001
════════════════════════════════════════════════════════════

Title: Implement core file parser
Backlog: BL-001
Status: COMPLETED
Agent: builder
Started: 2025-11-20T14:30:00Z
Elapsed: 45 minutes
Progress: 100%
Completed: 2025-11-20T15:15:00Z

Progress Notes:
  • Generated module spec
  • Implemented core parser logic
  • Added comprehensive tests
  • Updated documentation

Process ID: pm-builder-ws-001
Log: .pm/logs/pm-builder-ws-001.log
```

---

## Example 2: Web Service Development

**Scenario**: Building a REST API service.

### Step 1: Initialize

```bash
/pm:init
```

**Responses:**

```
Project name: api-service
Project type: 2 (web-service)
Primary goals:
  - RESTful API design
  - High performance
  - Comprehensive tests

Quality bar: 1 (strict)
```

### Step 2: Add Initial Features

```bash
/pm:add "Set up FastAPI project structure" --priority HIGH --estimated-hours 2
/pm:add "Implement authentication endpoints" --priority HIGH --estimated-hours 8 --tags "auth,security"
/pm:add "Create user management API" --priority HIGH --estimated-hours 6 --tags "users,crud"
/pm:add "Add request validation middleware" --priority MEDIUM --estimated-hours 4
/pm:add "Implement rate limiting" --priority MEDIUM --estimated-hours 5 --tags "security,middleware"
```

### Step 3: Start with Structure

```bash
/pm:start BL-001
```

### Step 4: Review Before Implementation

After structure is complete, use reviewer agent:

```bash
/pm:start BL-002 --agent reviewer
```

**Reviewer checks:**

- Security best practices
- Code organization
- Test coverage
- Documentation quality

### Step 5: Implement After Review

Once review passes, implement with builder:

```bash
/pm:start BL-002 --agent builder
```

---

## Example 3: Library Development

**Scenario**: Creating a reusable Python library.

### Step 1: Initialize

```bash
/pm:init
```

**Responses:**

```
Project name: data-utils
Project type: 3 (library)
Primary goals:
  - Clean public API
  - Comprehensive documentation
  - High test coverage

Quality bar: 1 (strict)
```

### Step 2: Design-First Approach

```bash
/pm:add "Design public API" --priority HIGH --estimated-hours 3 --tags "design,api"
/pm:add "Write API documentation" --priority HIGH --estimated-hours 4 --tags "docs"
/pm:add "Implement core data structures" --priority HIGH --estimated-hours 8 --tags "core"
/pm:add "Add utility functions" --priority MEDIUM --estimated-hours 6
/pm:add "Write comprehensive tests" --priority HIGH --estimated-hours 10 --tags "tests"
/pm:add "Add usage examples" --priority MEDIUM --estimated-hours 3 --tags "docs,examples"
```

### Step 3: Architecture First

Start with design work:

```bash
/pm:start BL-001 --agent builder
```

Document the API before implementing.

### Step 4: Test-Driven Development

After API is designed, write tests:

```bash
/pm:start BL-005 --agent tester
```

Create comprehensive test suite based on API design.

### Step 5: Implement

With tests in place, implement:

```bash
/pm:start BL-003 --agent builder
```

Tests guide the implementation.

---

## Example 4: Iterative Development

**Scenario**: Building feature incrementally with multiple review cycles.

### Complete Cycle

```bash
# 1. Add feature to backlog
/pm:add "Add caching layer" --priority HIGH --estimated-hours 8

# 2. Design phase (builder creates spec)
/pm:start BL-001 --agent builder

# 3. Review design (reviewer checks spec)
/pm:start BL-001 --agent reviewer

# 4. Implement (builder codes feature)
/pm:start BL-001 --agent builder

# 5. Test (tester adds test coverage)
/pm:start BL-001 --agent tester

# 6. Final review (reviewer checks everything)
/pm:start BL-001 --agent reviewer
```

**Note**: In Phase 1, each step must complete before the next begins (single workstream limitation).

---

## Example 5: Bug Fixing Workflow

**Scenario**: Tracking and fixing bugs.

### Step 1: Add Bug Reports

```bash
/pm:add "Fix null pointer in parser" --priority HIGH --estimated-hours 2 --tags "bug,parser"
/pm:add "Memory leak in batch processor" --priority HIGH --estimated-hours 4 --tags "bug,performance"
/pm:add "UI rendering issue on mobile" --priority MEDIUM --estimated-hours 3 --tags "bug,ui"
```

### Step 2: Fix High-Priority Bugs First

```bash
/pm:start BL-001 --agent builder
```

Builder investigates and fixes the bug.

### Step 3: Add Regression Tests

```bash
/pm:start BL-001 --agent tester
```

Tester adds tests to prevent regression.

---

## Example 6: Documentation Sprint

**Scenario**: Focus on documentation improvement.

### Step 1: Add Documentation Tasks

```bash
/pm:add "Update API reference docs" --priority HIGH --estimated-hours 6 --tags "docs"
/pm:add "Write getting started guide" --priority HIGH --estimated-hours 4 --tags "docs,tutorial"
/pm:add "Add code examples to README" --priority MEDIUM --estimated-hours 2 --tags "docs"
/pm:add "Create architecture diagram" --priority MEDIUM --estimated-hours 3 --tags "docs,design"
/pm:add "Write troubleshooting guide" --priority LOW --estimated-hours 3 --tags "docs"
```

### Step 2: Work Through Documentation

```bash
/pm:start BL-001 --agent builder
```

Builder agent updates documentation, following best practices.

---

## Example 7: Refactoring Project

**Scenario**: Improving existing codebase.

### Step 1: Identify Refactoring Needs

```bash
/pm:add "Extract config module" --priority HIGH --estimated-hours 4 --tags "refactor"
/pm:add "Simplify error handling" --priority HIGH --estimated-hours 6 --tags "refactor,cleanup"
/pm:add "Remove dead code" --priority MEDIUM --estimated-hours 2 --tags "cleanup"
/pm:add "Improve test organization" --priority MEDIUM --estimated-hours 4 --tags "tests,refactor"
```

### Step 2: Review First

Before refactoring, understand current code:

```bash
/pm:start BL-001 --agent reviewer
```

Reviewer analyzes code and suggests improvements.

### Step 3: Refactor

```bash
/pm:start BL-001 --agent builder
```

Builder implements refactoring safely.

### Step 4: Verify

```bash
/pm:start BL-001 --agent tester
```

Tester ensures no regressions.

---

## Tips and Best Practices

### Estimation Accuracy

Start with rough estimates:

```bash
--estimated-hours 4   # Small task (few hours)
--estimated-hours 8   # Medium task (day)
--estimated-hours 16  # Large task (2 days)
```

Refine estimates based on actual elapsed time from completed workstreams.

### Priority Guidelines

**HIGH**: Must-have features, critical bugs

```bash
/pm:add "Fix security vulnerability" --priority HIGH
```

**MEDIUM**: Should-have features, important improvements

```bash
/pm:add "Add pagination" --priority MEDIUM
```

**LOW**: Nice-to-have features, minor improvements

```bash
/pm:add "Update logo" --priority LOW
```

### Tag Organization

Use tags for filtering and organization:

```bash
--tags "core,api"           # Core API work
--tags "bug,critical"       # Critical bugs
--tags "docs,user-facing"   # User documentation
--tags "refactor,cleanup"   # Code cleanup
```

### Agent Selection

**builder**: For implementation work

- New features
- Bug fixes
- Refactoring

**reviewer**: For quality checks

- Code review
- Design review
- Philosophy compliance

**tester**: For test coverage

- Writing tests
- Test refactoring
- Coverage improvement

---

## Common Patterns

### Feature Development

```bash
1. /pm:add "Feature name" --priority HIGH
2. /pm:start BL-XXX --agent builder     # Implement
3. /pm:start BL-XXX --agent tester      # Test
4. /pm:start BL-XXX --agent reviewer    # Review
```

### Bug Fix

```bash
1. /pm:add "Fix bug description" --priority HIGH --tags "bug"
2. /pm:start BL-XXX --agent builder     # Fix
3. /pm:start BL-XXX --agent tester      # Add regression test
```

### Documentation

```bash
1. /pm:add "Update docs" --priority MEDIUM --tags "docs"
2. /pm:start BL-XXX --agent builder     # Write docs
```

### Refactoring

```bash
1. /pm:add "Refactor module" --priority MEDIUM --tags "refactor"
2. /pm:start BL-XXX --agent reviewer    # Review current code
3. /pm:start BL-XXX --agent builder     # Refactor
4. /pm:start BL-XXX --agent tester      # Verify no regressions
```

---

For more information, see `README.md`.
