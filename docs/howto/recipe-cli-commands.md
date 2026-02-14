# Recipe CLI Commands - How-To Guide

Task-oriented guide for executing, validating, and managing workflow recipes using the `amplihack recipe` CLI commands.

## Contents

- [List Available Recipes](#list-available-recipes)
- [Execute a Recipe](#execute-a-recipe)
- [Validate Recipe Files](#validate-recipe-files)
- [Show Recipe Details](#show-recipe-details)
- [Common Workflows](#common-workflows)
- [Troubleshooting](#troubleshooting)

## List Available Recipes

**Task**: See all available workflow recipes on your system.

```bash
amplihack recipe list
```

**Expected output**:

```
Available recipes:
  default-workflow        22-step development workflow (requirements through merge)
  verification-workflow   Post-implementation verification and testing
  investigation           Deep codebase analysis and understanding
  code-review             Multi-perspective code review
  security-audit          Security-focused analysis pipeline
  refactor                Systematic refactoring with safety checks
  bug-triage              Bug investigation and root cause analysis
  ddd-workflow            Document-driven development (6 phases)
  ci-diagnostic           CI failure diagnosis and fix loop
  quick-fix               Lightweight fix for simple issues
```

The list includes:

- Built-in recipes from `amplifier-bundle/recipes/`
- User-installed recipes in `~/.amplihack/.claude/recipes/`
- Project-specific recipes in `.claude/recipes/`

**Filter by pattern**:

```bash
# Show only recipes containing "workflow"
amplihack recipe list | grep workflow
```

## Execute a Recipe

**Task**: Run a workflow recipe with your task context.

### Basic Execution

```bash
amplihack recipe run default-workflow \
  --context '{"task_description": "Add user authentication", "repo_path": "."}'
```

**What happens**:

1. Recipe Runner loads `default-workflow.yaml`
2. Parses the 22 workflow steps
3. Executes each step sequentially
4. Agents cannot skip steps (code-enforced)
5. Outputs progress after each step

**Expected output**:

```
[Recipe] default-workflow (22 steps)
[Step 1/22] clarify-requirements (agent: prompt-writer)
  Running: Analyze and clarify task requirements...
  Output: Stored in context.clarified_requirements
[Step 2/22] design (agent: architect)
  Running: Design solution architecture...
  Output: Stored in context.design_spec
...
[Step 22/22] merge (type: bash)
  Running: git merge --ff-only...
  Success: PR #123 merged to main

Recipe completed successfully in 18m 32s
```

### Dry Run Mode

**Task**: Preview what a recipe will do without executing anything.

```bash
amplihack recipe run verification-workflow --dry-run
```

**Expected output**:

```
[DRY RUN] verification-workflow (8 steps)
[Step 1/8] run-tests (type: bash)
  Would execute: cd . && python -m pytest tests/ -v
[Step 2/8] check-coverage (type: bash)
  Would execute: cd . && pytest --cov=. --cov-report=term
[Step 3/8] lint-check (agent: reviewer)
  Would run agent: amplihack:reviewer
  Prompt: Review code for style violations...
...

No changes made (dry run mode)
```

Use dry run to:

- Verify recipe loads correctly
- Preview step order
- Check template variable expansion
- Ensure agent references are valid

### Pass Runtime Context

**Task**: Provide values for recipe context variables.

```bash
amplihack recipe run bug-triage \
  --context '{
    "issue_number": "456",
    "repo_path": "/home/user/myproject",
    "branch_name": "fix/issue-456"
  }'
```

Context variables:

- Defined in recipe YAML `context:` block
- Passed via `--context` JSON string
- Injected into prompts with `{{variable}}` syntax
- Available to all steps in the recipe

**Required vs optional context**:

```yaml
# Recipe defines these context variables
context:
  task_description: "" # Required (empty default)
  repo_path: "." # Optional (has default)
  branch_name: "" # Optional
```

The recipe will fail with a clear error if required context is missing:

```
Error: Missing required context variable: task_description
```

### Select SDK Adapter

**Task**: Run a recipe using a specific AI backend.

```bash
# Use Claude Agent SDK (default)
amplihack recipe run default-workflow --adapter claude \
  --context '{"task_description": "Add rate limiting"}'

# Use GitHub Copilot SDK
amplihack recipe run default-workflow --adapter copilot \
  --context '{"task_description": "Add rate limiting"}'

# Use CLI subprocess adapter (generic fallback)
amplihack recipe run default-workflow --adapter cli \
  --context '{"task_description": "Add rate limiting"}'
```

**Adapter auto-detection**:

When `--adapter` is omitted, the Recipe Runner automatically selects:

1. Claude Agent SDK if `claude` CLI is available
2. GitHub Copilot SDK if `copilot` CLI is available
3. CLI subprocess adapter (always works)

**When to override**:

- Testing recipe with different agents
- Team uses multiple SDKs
- Debugging adapter-specific issues

## Validate Recipe Files

**Task**: Check a recipe YAML file for errors before running it.

```bash
amplihack recipe validate my-workflow.yaml
```

**Expected output (valid recipe)**:

```
Validating my-workflow.yaml...
  [OK] Valid YAML syntax
  [OK] Required fields present (name, steps)
  [OK] All step IDs unique
  [OK] Template variables resolve against context
  [OK] Agent references valid (architect, builder, tester)
  [OK] No circular dependencies in step conditions

Recipe "my-workflow" is valid (5 steps)
```

**Expected output (invalid recipe)**:

```
Validating broken-recipe.yaml...
  [OK] Valid YAML syntax
  [OK] Required fields present
  [FAIL] Step ID "test" appears 2 times (must be unique)
  [FAIL] Agent reference "amplihack:unknown-agent" not found
  [WARN] Context variable "{{missing_var}}" not defined in context block

Recipe validation failed with 2 errors, 1 warning
```

**What validation checks**:

- YAML syntax is correct
- Required fields (`name`, `steps`) present
- Step IDs are unique
- Agent references resolve to real agents
- Template variables defined in context
- Step conditions are valid Python expressions
- No circular dependencies in conditions

**Validate during development**:

```bash
# Edit recipe
vim ~/.amplihack/.claude/recipes/custom-workflow.yaml

# Validate after each change
amplihack recipe validate custom-workflow.yaml

# Run when validation passes
amplihack recipe run custom-workflow --dry-run
```

## Show Recipe Details

**Task**: Display full recipe metadata and step breakdown.

```bash
amplihack recipe show default-workflow
```

**Expected output**:

```
Recipe: default-workflow
Description: 22-step development workflow (requirements through merge)
Version: 1.0
Author: amplihack
Path: /home/user/.amplihack/.claude/recipes/default-workflow.yaml

Context Variables:
  task_description (required): Description of what to implement
  repo_path (optional, default="."): Repository root path
  branch_name (optional): Override branch name

Steps (22):
  1. clarify-requirements (agent: prompt-writer)
     → Output: clarified_requirements

  2. design (agent: architect)
     → Uses: clarified_requirements
     → Output: design_spec

  3. create-branch (type: bash)
     → Command: git checkout -b {{branch_name}}

  4. write-tests (agent: tester)
     → Uses: design_spec
     → Output: test_code

  ...

  22. merge (type: bash)
      → Command: git merge --ff-only
      → Condition: tests_pass && ci_success
```

**Use cases**:

- Understand what a recipe does before running it
- See exact agent order
- Check context variable requirements
- Review step dependencies

**Show with filtering**:

```bash
# Show only steps using the architect agent
amplihack recipe show default-workflow | grep "agent: architect"

# Count total steps
amplihack recipe show default-workflow | grep -c "^  [0-9]"
```

## Common Workflows

### Full Development Cycle

**Task**: Implement a complete feature from requirements to merge.

```bash
# 1. Start with the full 22-step workflow
amplihack recipe run default-workflow \
  --context '{
    "task_description": "Add JWT authentication to API",
    "repo_path": ".",
    "branch_name": "feat/jwt-auth"
  }'
```

This executes:

- Requirements clarification (prompt-writer)
- Architecture design (architect)
- Git branch creation
- Test-first development (tester → builder)
- Code review (reviewer)
- CI/CD integration
- PR creation and merge

### Quick Bug Fix

**Task**: Fix a simple, well-understood bug.

```bash
# Use the lightweight quick-fix recipe (4 steps)
amplihack recipe run quick-fix \
  --context '{
    "task_description": "Fix null pointer in user profile handler",
    "repo_path": "."
  }'
```

Steps:

1. Analyze the bug (analyzer)
2. Generate fix (builder)
3. Run tests (bash)
4. Commit changes (bash)

### Code Investigation

**Task**: Understand how an existing system works.

```bash
amplihack recipe run investigation \
  --context '{
    "task_description": "How does the authentication system work?",
    "repo_path": ".",
    "focus_area": "src/auth/"
  }'
```

The investigation recipe:

- Maps code structure
- Analyzes data flow
- Documents findings
- Generates persistent documentation

### Security Review

**Task**: Run a comprehensive security audit.

```bash
amplihack recipe run security-audit \
  --context '{
    "repo_path": ".",
    "focus_modules": "auth,api,database"
  }'
```

Security audit steps:

- Scan for common vulnerabilities (security agent)
- Check dependency versions
- Review authentication logic
- Test input validation
- Generate security report

### CI Failure Recovery

**Task**: Diagnose and fix CI failures.

```bash
amplihack recipe run ci-diagnostic \
  --context '{
    "pr_number": "123",
    "repo_path": ".",
    "ci_log_url": "https://github.com/org/repo/actions/runs/456"
  }'
```

CI diagnostic workflow:

- Fetch CI logs
- Parse failures
- Diagnose root cause
- Apply fixes
- Push and rerun CI (iterates until passing)

## Troubleshooting

### Recipe Not Found

**Problem**: `amplihack recipe run my-recipe` fails with "Recipe not found".

**Solution**: Check recipe discovery paths.

```bash
# List available recipes
amplihack recipe list

# Check recipe file locations
ls ~/.amplihack/.claude/recipes/*.yaml
ls .claude/recipes/*.yaml
```

If your recipe is in a different location:

```bash
# Specify absolute path
amplihack recipe run /path/to/my-recipe.yaml \
  --context '{"task_description": "..."}'
```

### Missing Context Variables

**Problem**: Recipe fails with "Missing required context variable".

**Solution**: Show recipe details to see what context it needs.

```bash
# See required context
amplihack recipe show my-recipe

# Provide all required variables
amplihack recipe run my-recipe \
  --context '{
    "required_var1": "value1",
    "required_var2": "value2"
  }'
```

### Agent Not Found

**Problem**: Recipe validation fails with "Agent reference not found".

**Solution**: Check agent name matches an actual agent file.

```bash
# List available agents
ls ~/.amplihack/.claude/agents/amplihack/*.md

# Agent references use filename without .md
# amplihack:architect → architect.md
# amplihack:security → security.md
```

Fix the recipe to use a valid agent reference:

```yaml
# Wrong
agent: amplihack:unknown-agent

# Right
agent: amplihack:architect
```

### Step Skipped Unexpectedly

**Problem**: A step shows "Skipped" in the output.

**Explanation**: Steps skip when their `condition` evaluates to false.

```yaml
steps:
  - id: design
    agent: amplihack:architect
    prompt: "Design solution..."
    output: design_spec

  - id: implement
    agent: amplihack:builder
    prompt: "Build from {{design_spec}}"
    condition: "design_spec" # Skips if design_spec is empty/None
```

**Solution**: Check previous step outputs and conditions.

```bash
# Run with verbose output to see why steps skip
amplihack recipe run my-recipe --verbose \
  --context '{"task_description": "..."}'
```

### Recipe Runs Too Slowly

**Problem**: Large recipes take a long time to complete.

**Solutions**:

**1. Use faster recipes for simple tasks**:

```bash
# Instead of full 22-step workflow for a small fix
amplihack recipe run default-workflow  # ❌ Slow

# Use the quick-fix recipe
amplihack recipe run quick-fix  # ✅ Fast (4 steps)
```

**2. Create custom recipes with fewer steps**:

```yaml
name: minimal-test-fix
description: Just fix tests, nothing else
steps:
  - id: fix-tests
    agent: amplihack:tester
    prompt: "Fix failing tests in {{test_file}}"

  - id: run-tests
    type: bash
    command: "pytest {{test_file}}"
```

**3. Use dry-run to verify before full execution**:

```bash
# Quick preview (< 1 second)
amplihack recipe run large-workflow --dry-run

# Only run if dry-run looks correct
amplihack recipe run large-workflow --context '...'
```

### Adapter Selection Issues

**Problem**: Recipe fails with "Adapter not available" or uses wrong adapter.

**Solution**: Explicitly specify adapter.

```bash
# Check which CLIs are installed
which claude copilot

# Force specific adapter
amplihack recipe run my-recipe --adapter claude \
  --context '{"task_description": "..."}'
```

**Adapter requirements**:

- `claude` adapter: Requires Claude Agent SDK installed
- `copilot` adapter: Requires GitHub Copilot CLI installed
- `cli` adapter: Always available (generic fallback)

---

**See also**:

- [Recipe Runner Overview](../recipes/README.md) - Architecture and design
- [Recipe CLI Reference](../reference/recipe-cli-reference.md) - Complete command documentation
- [Creating Custom Recipes](../recipes/README.md#creating-custom-recipes) - Recipe YAML format guide
