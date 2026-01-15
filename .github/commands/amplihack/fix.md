---
name: amplihack:fix
version: 2.0.0
description: Fix command that integrates with DEFAULT_WORKFLOW for quality-focused
  issue resolution
triggers:
- fix this error
- CI failing
- tests broken
- import error
- something's broken
invokes: DEFAULT_WORKFLOW
invokes_details:
- type: workflow
  path: .claude/workflow/DEFAULT_WORKFLOW.md
- type: subagent
  path: .claude/agents/amplihack/specialized/fix-agent.md
- type: subagent
  path: .claude/agents/amplihack/specialized/pre-commit-diagnostic.md
- type: subagent
  path: .claude/agents/amplihack/specialized/ci-diagnostic-workflow.md
philosophy:
- principle: Ruthless Simplicity
  application: Single workflow path - no branching logic
- principle: Quality Over Speed
  application: Follow all 22 steps of DEFAULT_WORKFLOW for robust fixes
dependencies:
  required:
  - .claude/workflow/DEFAULT_WORKFLOW.md
  optional:
  - .claude/tools/ci_status.py
examples:
- /fix
- /fix import
- /fix ci
- /fix test
---

# Fix Command

## Input Validation

@.github/context/AGENT_INPUT_VALIDATION.md

## Usage

`/fix [PATTERN]`

## Purpose

Intelligent fix workflow that executes all 22 steps of DEFAULT_WORKFLOW with pattern-specific context. No shortcuts - every fix follows the standard workflow to ensure quality, testing, and proper integration.

## Parameters

- **PATTERN** (optional): Error pattern type that provides context to specialized agents
  - `import` - Import and dependency issues
  - `ci` - CI/CD pipeline failures
  - `test` - Test failures and assertion errors
  - `config` - Configuration and environment issues
  - `quality` - Code quality, linting, formatting
  - `logic` - Algorithm bugs and business logic
  - `auto` - Automatic pattern detection (default)

## Core Philosophy

### Single Workflow Path

Following ruthless simplicity, there is ONE workflow path for all fixes:

```
/fix [pattern] → DEFAULT_WORKFLOW (Steps 0-21) → Complete, tested fix
```

No branching logic. Just the standard 22-step workflow executed with pattern-specific context.

### Patterns As Context (Not Modes)

Patterns don't create different workflows - they provide context:

- **Pattern detection** identifies the error type (import, ci, test, etc.)
- **Context** informs which specialized agents to invoke within workflow steps
- **Workflow** remains the same 22 steps regardless of pattern
- **Templates** are tools used in Step 8 (Mandatory Local Testing), not alternatives

## Process

### Pattern Detection

Automatic pattern recognition from error messages and context:

```bash
# Error pattern matching
ERROR_PATTERNS = {
    "ModuleNotFoundError": "import",
    "ImportError": "import",
    "build failed": "ci",
    "test failed": "test",
    "AssertionError": "test",
    "configuration file not found": "config",
    "environment variable not set": "config",
    "line too long": "quality",
    "missing type annotation": "quality",
    "unexpected result": "logic"
}
```

Pattern detection happens in Step 1 (Clarify Requirements) of DEFAULT_WORKFLOW.

### Workflow Execution

All fixes follow the complete DEFAULT_WORKFLOW:

1. **Step 0**: Prime UltraThink with workflow context
2. **Step 1**: Clarify requirements (includes pattern detection)
3. **Step 2**: Create GitHub issue
4. **Step 3**: Create feature branch
5. **Step 4**: Design solution (pattern-specific agent selection)
6. **Step 5**: Specify modules
7. **Step 6**: Implement changes
8. **Step 7**: Verify implementation
9. **Step 8**: Mandatory local testing (use fix templates here)
10. **Step 9**: Run tests
11. **Step 10**: Fix test failures
12. **Step 11**: Commit changes
13. **Step 12**: Push to remote
14. **Step 13**: Create pull request
15. **Step 14**: Monitor CI status
16. **Step 15**: Fix CI failures
17. **Step 16**: Code review
18. **Step 17**: Address feedback
19. **Step 18**: Verify standards
20. **Step 19**: Final validation
21. **Step 20**: Merge preparation
22. **Step 21**: Documentation updates

### Pattern-Specific Agent Selection

Patterns inform which specialized agents to invoke within workflow steps:

**Step 4 (Design Solution)**:

- `import` pattern → Invoke dependency analyzer
- `ci` pattern → Invoke ci-diagnostic-workflow agent
- `test` pattern → Invoke tester agent
- `config` pattern → Invoke environment agent
- `quality` pattern → Invoke reviewer agent
- `logic` pattern → Invoke architect agent

**Step 8 (Mandatory Local Testing)**:

- Use pattern-specific fix templates as validation tools
- Templates verify the fix works correctly
- Not shortcuts - verification tools within standard workflow

## Command Examples

### Basic Usage

```bash
# Automatic pattern detection
/fix

# Specific pattern for context
/fix import
/fix ci
/fix test
/fix config
/fix quality
/fix logic
```

All commands execute the same 22-step workflow with pattern-specific context.

### Context-Aware Examples

```bash
# Import error fix
/fix import
→ Step 1: Detects import pattern
→ Steps 2-3: GitHub issue + branch
→ Step 4: Dependency analyzer designs solution
→ Steps 5-7: Implement fix
→ Step 8: Use import-fix-template for validation
→ Steps 9-21: Complete standard workflow

# CI failure fix
/fix ci
→ Step 1: Detects CI pattern
→ Steps 2-3: GitHub issue + branch
→ Step 4: CI-diagnostic agent analyzes failure
→ Steps 5-7: Implement fix
→ Step 8: Use ci-fix-template for validation
→ Steps 9-21: Complete standard workflow
```

## Integration Points

### With Fix Agent

The fix-agent is the workflow orchestrator that:

- Reads DEFAULT_WORKFLOW.md
- Executes all 22 steps in order
- Uses pattern context to select specialized agents
- Ensures 100% workflow compliance

### With Specialized Agents

Pattern-specific agents are invoked within workflow steps:

- **pre-commit-diagnostic**: For pre-commit hook fixes (Step 4)
- **ci-diagnostic-workflow**: For CI failure analysis (Step 4/15)
- **tester**: For test-related fixes (Step 4/10)
- **reviewer**: For code quality issues (Step 4/18)
- **architect**: For complex logic fixes (Step 4)

### With Fix Templates

Templates are validation tools used in Step 8:

- **import-fix-template**: Validates import resolution
- **ci-fix-template**: Validates CI configuration
- **test-fix-template**: Validates test fixes
- **config-fix-template**: Validates configuration
- **quality-fix-template**: Validates code quality

Templates don't replace workflow steps - they're tools within Step 8.

## Success Criteria

Fix is complete when all 22 workflow steps execute successfully:

- GitHub issue created and tracked
- Feature branch created and pushed
- Solution designed by pattern-specific agents
- Implementation complete and verified
- Local tests pass (using fix templates)
- CI passes all checks
- Code review approved
- PR merged to main branch
- Documentation updated

## Remember

The fix command prioritizes quality over speed:

- **No shortcuts**: All 22 steps execute for every fix
- **Single workflow**: No mode branching or alternative paths
- **Pattern as context**: Informs agent selection, doesn't change workflow
- **Templates as tools**: Used in Step 8 for validation, not alternatives
- **Quality focus**: Robust, tested, documented fixes every time

The goal is not speed - it's reliable, high-quality fixes that follow best practices and integrate properly with the codebase.