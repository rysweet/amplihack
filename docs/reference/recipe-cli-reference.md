# Recipe CLI Reference

Complete command-line reference for the `amplihack recipe` subcommand group. All recipe commands execute workflow recipes using code-enforced step progression.

## Contents

- [Global Options](#global-options)
- [amplihack recipe list](#amplihack-recipe-list)
- [amplihack recipe run](#amplihack-recipe-run)
- [amplihack recipe validate](#amplihack-recipe-validate)
- [amplihack recipe show](#amplihack-recipe-show)
- [Exit Codes](#exit-codes)
- [Environment Variables](#environment-variables)

## Global Options

Options that apply to all `amplihack recipe` commands.

```bash
amplihack recipe [GLOBAL_OPTIONS] <command> [OPTIONS]
```

| Option            | Description                | Default |
| ----------------- | -------------------------- | ------- |
| `--help`, `-h`    | Show help message and exit | -       |
| `--version`       | Show recipe runner version | -       |
| `--verbose`, `-v` | Enable verbose output      | `false` |
| `--quiet`, `-q`   | Suppress non-error output  | `false` |

**Examples**:

```bash
# Show recipe subcommand help
amplihack recipe --help

# Check recipe runner version
amplihack recipe --version
# Output: amplihack recipe runner 1.0.0

# Verbose mode shows detailed step execution
amplihack recipe --verbose list
```

## amplihack recipe list

List all available workflow recipes discovered from standard recipe directories.

### Synopsis

```bash
amplihack recipe list [OPTIONS]
```

### Description

Scans recipe discovery paths and displays all available recipes with their descriptions. Recipe discovery order (later paths override earlier):

1. `amplifier-bundle/recipes/` - Bundled recipes from Microsoft Amplifier
2. `src/amplihack/amplifier-bundle/recipes/` - Package-embedded recipes
3. `~/.amplihack/.claude/recipes/` - User-installed recipes
4. `.claude/recipes/` - Project-specific recipes

### Options

| Option              | Description                                    | Default |
| ------------------- | ---------------------------------------------- | ------- |
| `--format <format>` | Output format: `text`, `json`, `yaml`, `table` | `text`  |
| `--long`, `-l`      | Show extended details (path, steps, version)   | `false` |

### Examples

```bash
# List all recipes (default format)
amplihack recipe list
```

**Output**:

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

**Long format**:

```bash
amplihack recipe list --long
```

**Output**:

```
Available recipes:

default-workflow (version 1.0)
  Description: 22-step development workflow (requirements through merge)
  Steps: 22
  Path: /home/user/.amplihack/.claude/recipes/default-workflow.yaml

verification-workflow (version 1.0)
  Description: Post-implementation verification and testing
  Steps: 8
  Path: /home/user/.amplihack/.claude/recipes/verification-workflow.yaml

...
```

**JSON format**:

```bash
amplihack recipe list --format json
```

**Output**:

```json
{
  "recipes": [
    {
      "name": "default-workflow",
      "description": "22-step development workflow (requirements through merge)",
      "version": "1.0",
      "steps": 22,
      "path": "/home/user/.amplihack/.claude/recipes/default-workflow.yaml"
    },
    {
      "name": "verification-workflow",
      "description": "Post-implementation verification and testing",
      "version": "1.0",
      "steps": 8,
      "path": "/home/user/.amplihack/.claude/recipes/verification-workflow.yaml"
    }
  ]
}
```

**Table format**:

```bash
amplihack recipe list --format table
```

**Output**:

```
NAME                    DESCRIPTION                                              STEPS
default-workflow        22-step development workflow (requirements through merge)   22
verification-workflow   Post-implementation verification and testing                 8
investigation           Deep codebase analysis and understanding                    12
code-review             Multi-perspective code review                                6
security-audit          Security-focused analysis pipeline                           9
refactor                Systematic refactoring with safety checks                   10
bug-triage              Bug investigation and root cause analysis                    7
ddd-workflow            Document-driven development (6 phases)                      18
ci-diagnostic           CI failure diagnosis and fix loop                            5
quick-fix               Lightweight fix for simple issues                            4
```

### Exit Codes

| Code | Meaning                                |
| ---- | -------------------------------------- |
| `0`  | Success - recipes found and listed     |
| `1`  | No recipes found in any discovery path |

## amplihack recipe run

Execute a workflow recipe with runtime context. Steps execute sequentially with code-enforced progression (models cannot skip steps).

### Synopsis

```bash
amplihack recipe run <recipe> [OPTIONS]
```

### Arguments

| Argument   | Description                             | Required |
| ---------- | --------------------------------------- | -------- |
| `<recipe>` | Recipe name or path to recipe YAML file | Yes      |

### Description

Loads a recipe and executes each step in order:

- Agent steps call AI agents via SDK adapter
- Bash steps execute shell commands
- Template variables in prompts/commands expand from context
- Step outputs store in context for later steps
- Steps with conditions may skip based on previous results

Execution continues until:

- All steps complete successfully (exit 0)
- A step fails (exit > 0)
- User interrupts with Ctrl+C (exit 130)

### Options

| Option                  | Description                             | Default     |
| ----------------------- | --------------------------------------- | ----------- |
| `--context <json>`      | Runtime context as JSON string          | `{}`        |
| `--context-file <path>` | Load context from JSON file             | -           |
| `--adapter <name>`      | SDK adapter: `claude`, `copilot`, `cli` | Auto-detect |
| `--dry-run`             | Show steps without executing            | `false`     |
| `--resume-from <step>`  | Resume from specific step ID            | -           |
| `--stop-at <step>`      | Stop after specific step ID             | -           |
| `--output <path>`       | Write execution log to file             | -           |
| `--interactive`         | Prompt for approval before each step    | `false`     |

### Examples

**Basic execution**:

```bash
amplihack recipe run default-workflow \
  --context '{"task_description": "Add user authentication", "repo_path": "."}'
```

**Output**:

```
[Recipe] default-workflow (22 steps)
[Step 1/22] clarify-requirements (agent: prompt-writer)
  Running: Analyze and clarify task requirements...
  ✓ Completed in 3.2s
  Output: context.clarified_requirements

[Step 2/22] design (agent: architect)
  Running: Design solution architecture...
  ✓ Completed in 8.7s
  Output: context.design_spec

[Step 3/22] create-branch (type: bash)
  Running: git checkout -b feat/user-auth
  ✓ Completed in 0.3s

...

[Step 22/22] merge (type: bash)
  Running: git merge --ff-only feat/user-auth
  ✓ Completed in 0.5s

Recipe completed successfully in 18m 32s
```

**Load context from file**:

```bash
# Create context file
cat > context.json <<EOF
{
  "task_description": "Add JWT authentication to API",
  "repo_path": "/home/user/myproject",
  "branch_name": "feat/jwt-auth"
}
EOF

# Run with context file
amplihack recipe run default-workflow --context-file context.json
```

**Dry run mode**:

```bash
amplihack recipe run verification-workflow --dry-run
```

**Output**:

```
[DRY RUN] verification-workflow (8 steps)
[Step 1/8] run-tests (type: bash)
  Would execute: cd . && python -m pytest tests/ -v
[Step 2/8] check-coverage (type: bash)
  Would execute: cd . && pytest --cov=. --cov-report=term
[Step 3/8] lint-check (agent: reviewer)
  Would run agent: amplihack:reviewer
  Prompt: Review code for style violations...

No changes made (dry run mode)
```

**Resume from checkpoint**:

```bash
# Initial run fails at step 15
amplihack recipe run default-workflow \
  --context '{"task_description": "Add rate limiting"}'
# ... fails at step 15: implement-logic

# Fix the issue, then resume from step 15
amplihack recipe run default-workflow \
  --context '{"task_description": "Add rate limiting"}' \
  --resume-from implement-logic
```

**Partial execution**:

```bash
# Run only steps 1-5 (stop before step 6)
amplihack recipe run default-workflow \
  --context '{"task_description": "Add caching"}' \
  --stop-at write-tests
```

**Interactive mode**:

```bash
amplihack recipe run security-audit --interactive
```

**Output**:

```
[Step 1/8] scan-dependencies (agent: security)
  Prompt: Scan package.json for vulnerable dependencies...

Continue? [y/n]: y
  ✓ Completed in 4.1s

[Step 2/8] check-auth (agent: security)
  Prompt: Review authentication implementation...

Continue? [y/n]: n
  Aborted by user

Recipe stopped at step 2/8
```

**Save execution log**:

```bash
amplihack recipe run default-workflow \
  --context '{"task_description": "Add webhooks"}' \
  --output execution-log.json
```

**Log format**:

```json
{
  "recipe": "default-workflow",
  "start_time": "2026-02-14T10:30:00Z",
  "end_time": "2026-02-14T10:48:32Z",
  "duration_seconds": 1112,
  "status": "completed",
  "steps": [
    {
      "id": "clarify-requirements",
      "type": "agent",
      "agent": "amplihack:prompt-writer",
      "start_time": "2026-02-14T10:30:01Z",
      "duration_seconds": 3.2,
      "status": "completed",
      "output": "Store in context.clarified_requirements"
    }
  ]
}
```

**Specify adapter**:

```bash
# Force Claude Agent SDK
amplihack recipe run default-workflow --adapter claude \
  --context '{"task_description": "Add monitoring"}'

# Use GitHub Copilot SDK
amplihack recipe run default-workflow --adapter copilot \
  --context '{"task_description": "Add monitoring"}'

# Generic CLI adapter (fallback)
amplihack recipe run default-workflow --adapter cli \
  --context '{"task_description": "Add monitoring"}'
```

**Run recipe from file path**:

```bash
# Absolute path
amplihack recipe run /home/user/custom-recipes/my-workflow.yaml \
  --context '{"target": "src/api"}'

# Relative path
amplihack recipe run ../shared-recipes/api-workflow.yaml \
  --context '{"target": "src/api"}'
```

### Exit Codes

| Code  | Meaning                           |
| ----- | --------------------------------- |
| `0`   | Success - all steps completed     |
| `1`   | Recipe validation failed          |
| `2`   | Missing required context variable |
| `3`   | Step execution failed             |
| `4`   | Agent not found                   |
| `5`   | Adapter not available             |
| `130` | Interrupted by user (Ctrl+C)      |

## amplihack recipe validate

Validate a recipe YAML file without executing it. Checks syntax, structure, agent references, and template variables.

### Synopsis

```bash
amplihack recipe validate <file> [OPTIONS]
```

### Arguments

| Argument | Description              | Required |
| -------- | ------------------------ | -------- |
| `<file>` | Path to recipe YAML file | Yes      |

### Description

Performs comprehensive validation:

1. **YAML syntax** - Parses file as valid YAML
2. **Required fields** - Checks `name` and `steps` are present
3. **Step structure** - Validates each step has required fields
4. **Unique IDs** - Ensures step IDs are unique within recipe
5. **Agent references** - Verifies agents exist in agent directories
6. **Template variables** - Checks `{{variables}}` are defined in context
7. **Conditions** - Validates step conditions are valid Python expressions
8. **Dependencies** - Detects circular dependencies in step conditions

### Options

| Option              | Description                   | Default |
| ------------------- | ----------------------------- | ------- |
| `--strict`          | Treat warnings as errors      | `false` |
| `--format <format>` | Output format: `text`, `json` | `text`  |

### Examples

**Valid recipe**:

```bash
amplihack recipe validate my-workflow.yaml
```

**Output**:

```
Validating my-workflow.yaml...
  [OK] Valid YAML syntax
  [OK] Required fields present (name, steps)
  [OK] All step IDs unique
  [OK] Template variables resolve against context
  [OK] Agent references valid (architect, builder, tester)
  [OK] No circular dependencies

Recipe "my-workflow" is valid (5 steps)
```

**Invalid recipe**:

```bash
amplihack recipe validate broken-recipe.yaml
```

**Output**:

```
Validating broken-recipe.yaml...
  [OK] Valid YAML syntax
  [OK] Required fields present
  [FAIL] Step ID "test" appears 2 times (must be unique)
  [FAIL] Agent reference "amplihack:unknown-agent" not found
  [WARN] Context variable "{{missing_var}}" used but not defined

Recipe validation failed with 2 errors, 1 warning
```

**Strict mode**:

```bash
amplihack recipe validate my-recipe.yaml --strict
```

Warnings become errors in strict mode. Returns exit code 1 if any warnings or errors found.

**JSON output**:

```bash
amplihack recipe validate my-recipe.yaml --format json
```

**Output**:

```json
{
  "valid": false,
  "errors": [
    {
      "type": "duplicate_step_id",
      "step_id": "test",
      "message": "Step ID 'test' appears 2 times (must be unique)"
    },
    {
      "type": "invalid_agent",
      "agent": "amplihack:unknown-agent",
      "message": "Agent reference 'amplihack:unknown-agent' not found"
    }
  ],
  "warnings": [
    {
      "type": "undefined_variable",
      "variable": "missing_var",
      "message": "Context variable '{{missing_var}}' used but not defined"
    }
  ]
}
```

### Exit Codes

| Code | Meaning                          |
| ---- | -------------------------------- |
| `0`  | Success - recipe is valid        |
| `1`  | Validation failed (errors found) |
| `2`  | File not found or not readable   |

## amplihack recipe show

Display detailed information about a recipe including metadata, context variables, and step-by-step breakdown.

### Synopsis

```bash
amplihack recipe show <recipe> [OPTIONS]
```

### Arguments

| Argument   | Description                             | Required |
| ---------- | --------------------------------------- | -------- |
| `<recipe>` | Recipe name or path to recipe YAML file | Yes      |

### Description

Shows complete recipe details:

- Metadata (name, description, version, author)
- File path
- Context variable definitions
- Full step list with prompts, agents, commands
- Step dependencies and outputs

### Options

| Option              | Description                                    | Default |
| ------------------- | ---------------------------------------------- | ------- |
| `--format <format>` | Output format: `text`, `json`, `yaml`, `table` | `text`  |
| `--steps-only`      | Show only step list (omit metadata)            | `false` |

### Examples

**Show full recipe details**:

```bash
amplihack recipe show default-workflow
```

**Output**:

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
     Prompt: |
       Analyze and clarify the following task:
       {{task_description}}

       Rewrite as unambiguous, testable requirements.
     Output: clarified_requirements

  2. design (agent: architect)
     Prompt: |
       Design a solution for:
       {{task_description}}

       Requirements:
       {{clarified_requirements}}
     Uses: clarified_requirements
     Output: design_spec

  3. create-branch (type: bash)
     Command: git checkout -b {{branch_name}}

  ...

  22. merge (type: bash)
      Command: git merge --ff-only {{branch_name}}
      Condition: tests_pass && ci_success
```

**Show steps only**:

```bash
amplihack recipe show default-workflow --steps-only
```

**Output**:

```
Steps (22):
  1. clarify-requirements (agent: prompt-writer)
  2. design (agent: architect)
  3. create-branch (type: bash)
  4. write-tests (agent: tester)
  ...
  22. merge (type: bash)
```

**JSON format**:

```bash
amplihack recipe show default-workflow --format json
```

**Output**:

```json
{
  "name": "default-workflow",
  "description": "22-step development workflow (requirements through merge)",
  "version": "1.0",
  "author": "amplihack",
  "path": "/home/user/.amplihack/.claude/recipes/default-workflow.yaml",
  "context": {
    "task_description": {
      "required": true,
      "default": "",
      "description": "Description of what to implement"
    },
    "repo_path": {
      "required": false,
      "default": ".",
      "description": "Repository root path"
    },
    "branch_name": {
      "required": false,
      "default": null,
      "description": "Override branch name"
    }
  },
  "steps": [
    {
      "id": "clarify-requirements",
      "type": "agent",
      "agent": "amplihack:prompt-writer",
      "prompt": "Analyze and clarify the following task:\n{{task_description}}\n\nRewrite as unambiguous, testable requirements.",
      "output": "clarified_requirements"
    }
  ]
}
```

**YAML format**:

```bash
amplihack recipe show default-workflow --format yaml
```

Returns the original recipe YAML content.

**Table format**:

```bash
amplihack recipe show default-workflow --format table
```

**Output**:

```
STEP  ID                      TYPE   AGENT/COMMAND                     OUTPUT
1     clarify-requirements    agent  amplihack:prompt-writer           clarified_requirements
2     design                  agent  amplihack:architect               design_spec
3     create-branch           bash   git checkout -b {{branch_name}}   -
4     write-tests             agent  amplihack:tester                  test_files
5     implement-logic         agent  amplihack:builder                 implementation
6     review-code             agent  amplihack:reviewer                review_feedback
7     run-tests               bash   pytest tests/ -v                  test_results
8     commit-changes          bash   git commit -m "..."               -
...
```

### Exit Codes

| Code | Meaning                              |
| ---- | ------------------------------------ |
| `0`  | Success - recipe found and displayed |
| `1`  | Recipe not found                     |

## Exit Codes

Summary of all exit codes used by recipe CLI commands.

| Code  | Meaning                           | Commands          |
| ----- | --------------------------------- | ----------------- |
| `0`   | Success                           | All commands      |
| `1`   | General error                     | All commands      |
| `2`   | Invalid arguments or missing file | `validate`, `run` |
| `3`   | Step execution failed             | `run`             |
| `4`   | Agent not found                   | `run`             |
| `5`   | Adapter not available             | `run`             |
| `130` | Interrupted by user (Ctrl+C)      | `run`             |

**Check exit code in shell**:

```bash
amplihack recipe run my-recipe --context '{...}'
echo $?  # Prints exit code
```

**Use exit codes in scripts**:

```bash
#!/bin/bash
set -e  # Exit on any error

if amplihack recipe run default-workflow --context '{...}'; then
  echo "Recipe succeeded"
  notify-user "Deployment complete"
else
  exit_code=$?
  echo "Recipe failed with code: $exit_code"
  notify-user "Deployment failed"
  exit $exit_code
fi
```

## Environment Variables

Environment variables that affect recipe CLI behavior.

### AMPLIHACK_RECIPE_PATH

Additional directories to search for recipes (colon-separated list).

```bash
export AMPLIHACK_RECIPE_PATH="/opt/company-recipes:/home/user/my-recipes"
amplihack recipe list  # Includes recipes from both directories
```

Discovery order with `AMPLIHACK_RECIPE_PATH`:

1. Built-in recipes
2. User recipes (`~/.amplihack/.claude/recipes/`)
3. Directories in `AMPLIHACK_RECIPE_PATH` (left to right)
4. Project recipes (`.claude/recipes/`)

### AMPLIHACK_ADAPTER

Default SDK adapter when `--adapter` is not specified.

```bash
export AMPLIHACK_ADAPTER=copilot
amplihack recipe run default-workflow --context '{...}'  # Uses copilot adapter
```

Valid values: `claude`, `copilot`, `cli`, `auto`

### AMPLIHACK_VERBOSE

Enable verbose output for all recipe commands.

```bash
export AMPLIHACK_VERBOSE=1
amplihack recipe list  # Shows detailed discovery process
```

Equivalent to passing `--verbose` flag to each command.

### AMPLIHACK_DRY_RUN

Enable dry-run mode by default.

```bash
export AMPLIHACK_DRY_RUN=1
amplihack recipe run my-recipe --context '{...}'  # Previews without executing
```

Override with explicit flag:

```bash
export AMPLIHACK_DRY_RUN=1
amplihack recipe run my-recipe --dry-run=false --context '{...}'  # Actually executes
```

---

**See also**:

- [Recipe CLI How-To Guide](../howto/recipe-cli-commands.md) - Task-oriented usage examples
- [Recipe Runner Overview](../recipes/README.md) - Architecture and YAML format
- [Creating Custom Recipes](../recipes/README.md#creating-custom-recipes) - Recipe development guide
