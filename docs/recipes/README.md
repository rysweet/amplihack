# Recipe Runner

A code-enforced workflow execution engine that reads declarative YAML recipe files and executes them step-by-step using AI agents. Unlike prompt-based workflow instructions that models can interpret loosely or skip, the Recipe Runner controls the execution loop in compiled code — making it physically impossible to skip steps.

**Standalone repo & docs**: [github.com/rysweet/amplihack-recipe-runner](https://github.com/rysweet/amplihack-recipe-runner) · [rysweet.github.io/amplihack-recipe-runner](https://rysweet.github.io/amplihack-recipe-runner/)

## Engine Selection

The recipe runner supports two engines. Set `RECIPE_RUNNER_ENGINE` to choose explicitly:

| Value       | Engine                                                                 | Notes                                                     |
| ----------- | ---------------------------------------------------------------------- | --------------------------------------------------------- |
| `rust`      | [recipe-runner-rs](https://github.com/rysweet/amplihack-recipe-runner) | Standalone binary, ~5ms startup, comprehensive test suite |
| `python`    | Built-in Python runner                                                 | No extra install needed                                   |
| _(not set)_ | Auto-detect                                                            | Uses Rust if binary found in PATH, Python otherwise       |

```bash
# Install the Rust binary
cargo install --git https://github.com/rysweet/amplihack-recipe-runner

# Or set path explicitly
export RECIPE_RUNNER_RS_PATH=/path/to/recipe-runner-rs

# Force a specific engine
export RECIPE_RUNNER_ENGINE=rust   # or python
```

The Rust binary is automatically installed during `amplihack install` if `cargo` is available. To check or manually trigger installation:

```python
from amplihack.recipes import ensure_rust_recipe_runner

ensure_rust_recipe_runner()  # Installs if missing, no-op if present
```

## Engine Feature Comparison

The Rust engine supports additional features not available in the Python engine:

| Feature                     | Rust | Python |
| --------------------------- | ---- | ------ |
| `parallel_group`            | ✅   | ❌     |
| `continue_on_error`         | ✅   | ❌     |
| `when_tags`                 | ✅   | ❌     |
| `hooks` (pre/post/on_error) | ✅   | ❌     |
| `extends` (inheritance)     | ✅   | ❌     |
| `recursion` config          | ✅   | ❌     |

Set `RECIPE_RUNNER_ENGINE=rust` to use the full feature set.

## Environment Variables

| Variable                        | Default       | Description                                   |
| ------------------------------- | ------------- | --------------------------------------------- |
| `RECIPE_RUNNER_ENGINE`          | (auto-detect) | Engine selection: `rust`, `python`, or unset  |
| `RECIPE_RUNNER_RS_PATH`         | (auto)        | Custom path to Rust binary                    |
| `RECIPE_RUNNER_INSTALL_TIMEOUT` | 300           | Cargo install timeout (seconds)               |
| `RECIPE_RUNNER_RUN_TIMEOUT`     | 3600          | Recipe execution timeout (seconds)            |
| `RUST_LOG`                      | (unset)       | Rust binary log level (e.g., `debug`, `info`) |

## Contents

- [Why It Exists](#why-it-exists)
- [Quick Start](#quick-start)
- [Recipe YAML Format](#recipe-yaml-format)
- [SDK Adapters](#sdk-adapters)
- [Available Recipes](#available-recipes)
- [Creating Custom Recipes](#creating-custom-recipes)
- [Integration with Amplihack](#integration-with-amplihack)
- [UltraThink Recipe Runner Integration](./RECIPE_RUNNER_ULTRATHINK_INTEGRATION.md) - How ultrathink uses Recipe Runner for code-enforced workflow execution

## Documentation

Complete documentation for using the Recipe Runner:

- **[Recipe CLI Quick Reference](quick-reference.md)** - One-page cheat sheet (start here for quick lookup)
- **[Recipe CLI Commands How-To](../howto/recipe-cli-commands.md)** - Task-oriented guide for using recipe commands
- **[Recipe CLI Reference](../reference/recipe-cli-reference.md)** - Complete command-line reference with all options and exit codes
- **[Recipe CLI Examples](cli-examples.md)** - Real-world usage scenarios (development, testing, CI/CD, team workflows)

## Why It Exists

Models frequently skip workflow steps when enforcement is purely prompt-based. A markdown file that says "you MUST follow all 22 steps" still relies on the model choosing to comply. The Recipe Runner moves enforcement from prompts to compiled code — a deterministic loop iterates over each step and calls the agent SDK, so the model never decides which step to run next.

**Prompt-based enforcement (before)**:

```markdown
## Step 7: Write Failing Tests

You MUST write tests before implementation. Do NOT skip this step.
```

The model can read this instruction and still jump to implementation.

**Code-enforced execution (after)**:

```
for step in recipe.steps:
    result = adapter.run(step.agent, step.prompt)
    // The next step literally cannot start until this one completes
```

The model executes within a single step. The execution loop controls progression.

## Quick Start

```bash
# List available recipes (discovers from all standard locations)
amplihack recipe list

# Execute a workflow recipe with context
amplihack recipe run default-workflow \
  --context task_description="Add user authentication" \
  --context repo_path="."

# Dry run -- see what would execute without running anything
amplihack recipe run verification-workflow --dry-run

# Validate a recipe file without executing it
amplihack recipe validate my-recipe.yaml

# Run with a specific SDK adapter
amplihack recipe run default-workflow \
  --adapter copilot \
  --context task_description="Fix login bug" \
  --context repo_path="."
```

**Expected output from `amplihack recipe list`**:

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

## Recipe YAML Format

A recipe is a YAML file with a flat structure: metadata at the top, then a list of steps.

### Minimal Example

```yaml
name: hello-recipe
description: Minimal recipe demonstrating the format
version: "1.0"

steps:
  - id: greet
    agent: amplihack:builder
    prompt: "Print 'Hello from Recipe Runner' to stdout"
```

### Full Schema

```yaml
name: default-workflow # Unique recipe identifier
description: "22-step development workflow" # Human-readable summary
version: "1.0" # Semver for the recipe
author: amplihack # Optional

# Context variables -- passed at runtime via --context JSON
context:
  task_description: "" # Required: what to build
  repo_path: "." # Optional: repository root
  branch_name: "" # Optional: override branch name

# Steps execute sequentially, top to bottom
steps:
  - id: clarify-requirements # Step identifier (required, unique within recipe)
    agent: amplihack:prompt-writer # Which agent handles this step (namespace:name)
    prompt: |
      Analyze and clarify the following task:
      {{task_description}}

      Rewrite as unambiguous, testable requirements.
    output: clarified_requirements # Store result in context under this key

  - id: run-tests
    type: bash # Shell command instead of agent call
    command: "cd {{repo_path}} && python -m pytest tests/ -x"
    output: test_output

  - id: design
    agent: amplihack:architect
    prompt: |
      Design a solution for:
      {{task_description}}

      Requirements:
      {{clarified_requirements}}
    condition: "clarified_requirements" # Skip if previous step output is falsy
    output: design_spec

  - id: parse-test-results
    type: bash
    command: "cd {{repo_path}} && python -m pytest --json-report tests/"
    parse_json: true # Parse stdout as JSON and store as dict in context
    output: test_results
```

### Step Fields

| Field        | Type        | Required | Description                                                                    |
| ------------ | ----------- | -------- | ------------------------------------------------------------------------------ |
| `id`         | string      | Yes      | Unique step identifier within the recipe                                       |
| `agent`      | string      | No       | Agent reference in `namespace:name` format                                     |
| `type`       | string      | No       | `agent` (default when `agent`/`prompt` present), `bash`, or `recipe`           |
| `prompt`     | string      | No       | Prompt template sent to the agent                                              |
| `command`    | string      | No       | Shell command (when `type: bash`)                                              |
| `recipe`     | string      | No       | Sub-recipe name to invoke (when `type: recipe`)                                |
| `context`    | dict        | No       | Extra context key/value pairs merged into the sub-recipe (when `type: recipe`) |
| `output`     | string      | No       | Context key to store step result under                                         |
| `condition`  | string      | No       | Python expression; step skips when false                                       |
| `parse_json` | bool        | No       | Parse stdout as JSON and store as dict in context                              |
| `mode`       | string      | No       | Agent mode hint (e.g. `ANALYZE`, `DESIGN`)                                     |
| `timeout`    | int or None | No       | Timeout in seconds for bash steps (default: None = no timeout)                 |

### Recipe Step (`type: recipe`)

A `recipe` step invokes another recipe as a sub-step, enabling composition of complex workflows from simpler building blocks.

```yaml
steps:
  - id: run-quality-audit
    type: recipe
    recipe: quality-audit-cycle
    context:
      target_path: src/amplihack
    output: quality_audit_results
```

**Recursion guard**: Sub-recipes can themselves contain `recipe` steps (up to a maximum depth of 3). Deeper nesting raises an error to prevent infinite loops.

**Context merging**: The sub-recipe starts with a copy of the current context, then the step-level `context` dict is merged on top. Mutations inside the sub-recipe do not propagate back to the parent recipe.

### Bash Step Timeouts

Bash steps have no timeout by default (timeout: None), allowing long-running operations to complete naturally. Optionally specify a timeout in seconds:

```yaml
steps:
  - id: run-tests
    type: bash
    command: "cd {{repo_path}} && python -m pytest tests/ -x"
    timeout: 300 # 5-minute timeout for long test suites
    output: test_output

  - id: git-operations
    type: bash
    command: "git fetch origin && git rebase origin/main"
    # No timeout specified = runs until completion
```

**Note**: Agent steps have never had timeouts and continue to run until the agent completes.

### Template Variables

Use `{{variable}}` to inject context values or previous step outputs into prompts and commands.

- `{{task_description}}` -- from the `context` block or `--context` CLI flag
- `{{repo_path}}` -- from context
- `{{clarified_requirements}}` -- output from a prior step stored via `output` field
- `{{nested.key}}` -- dot notation for nested dict values (from `parse_json` steps)

## SDK Adapters

The Recipe Runner uses an adapter pattern to execute agent steps across different AI backends. The adapter interface has two methods: `execute_agent_step(prompt, ...)` and `execute_bash_step(command, ...)`.

### Claude Agent SDK (Default)

Used when the Claude Agent SDK is installed. Calls agents as Claude Code subprocesses with full tool access.

```bash
amplihack recipe run default-workflow --adapter claude \
  --context '{"task_description": "Add rate limiting"}'
```

### GitHub Copilot SDK

For teams using GitHub Copilot CLI as their primary coding agent.

```bash
amplihack recipe run default-workflow --adapter copilot \
  --context '{"task_description": "Add rate limiting"}'
```

### CLI Subprocess (Fallback)

Generic adapter that shells out to any CLI tool. Works with any agent runtime that accepts prompts via stdin or arguments.

```bash
amplihack recipe run default-workflow --adapter cli \
  --context '{"task_description": "Add rate limiting"}'
```

### Adapter Selection

The runner selects an adapter automatically based on what is installed:

1. Claude Agent SDK -- if `claude` CLI is available
2. GitHub Copilot SDK -- if `copilot` CLI is available
3. CLI Subprocess -- always available as fallback

Override with `--adapter <name>`.

## Available Recipes

amplihack ships with recipes covering the most common development workflows.

| Recipe                  | Steps | Description                                             |
| ----------------------- | ----- | ------------------------------------------------------- |
| `default-workflow`      | 22    | Full development lifecycle: requirements through merge  |
| `verification-workflow` | 8     | Post-implementation testing and validation              |
| `investigation`         | 6     | Deep codebase analysis using knowledge-archaeologist    |
| `code-review`           | 5     | Multi-perspective review (security, performance, style) |
| `security-audit`        | 7     | Security-focused analysis pipeline                      |
| `refactor`              | 9     | Systematic refactoring with regression safety checks    |
| `bug-triage`            | 6     | Bug investigation and root cause analysis               |
| `ddd-workflow`          | 12    | Document-driven development (all 6 DDD phases)          |
| `ci-diagnostic`         | 5     | CI failure diagnosis and iterative fix loop             |
| `quick-fix`             | 4     | Lightweight fix for simple, well-understood issues      |

Recipes live in `~/.amplihack/.claude/recipes/`. Run `amplihack recipe list` to see all available recipes including any custom ones you have added.

### Recipe Discovery

The Recipe Runner automatically discovers recipes from these standard directories (in priority order):

1. **Installed Package Path** — `site-packages/amplihack/amplifier-bundle/recipes/` (absolute, works from any directory)
2. **Repository Root** — repo-root `amplifier-bundle/recipes/` (resolved via `Path(__file__)`, for editable installs)
3. **User-Installed** — `~/.amplihack/.claude/recipes/` (custom user recipes)
4. **CWD Bundle** — `amplifier-bundle/recipes/` (CWD-relative, legacy compatibility)
5. **CWD Source** — `src/amplihack/amplifier-bundle/recipes/` (CWD-relative, development)
6. **Project-Specific** — `.claude/recipes/` (project-local recipes, can override)

Later directories override earlier ones when recipe names collide. All bundled recipes are automatically available after pip install without additional configuration.

**Key Feature (v0.9.0)**: Recipe discovery now includes the installed package's absolute path, resolved via `Path(__file__)`. This ensures all 16 bundled recipes are discoverable when you run amplihack from any working directory, not just from the amplihack repository itself.

```python
from amplihack.recipes import list_recipes, find_recipe

# List all discovered recipes
for recipe_info in list_recipes():
    print(f"{recipe_info.name}: {recipe_info.step_count} steps")

# Find a specific recipe by name
path = find_recipe("default-workflow")
if path:
    print(f"Found at: {path}")
```

### Tracking Upstream Changes

The `amplifier-bundle/recipes/` directory contains recipes from Microsoft's upstream repository. To stay in sync with upstream and detect local modifications:

**Create baseline manifest:**

```python
from amplihack.recipes import update_manifest

# Records SHA-256 hash of each recipe file
manifest_path = update_manifest()
print(f"Manifest: {manifest_path}")
```

**Check for local modifications:**

```python
from amplihack.recipes import check_upstream_changes

changes = check_upstream_changes()
for change in changes:
    print(f"{change['name']}: {change['status']}")  # modified/new/deleted
```

**Sync from upstream:**

```python
from amplihack.recipes import sync_upstream

# Fetches latest from microsoft/amplifier-bundle-recipes
result = sync_upstream()
print(f"Added: {result['added']}, Updated: {result['updated']}")
```

This downloads the latest recipes from `https://github.com/microsoft/amplifier-bundle-recipes`, compares against local files, and copies any changes. The manifest is automatically updated after sync.

**Recommended workflow:**

```bash
# 1. Create initial manifest (do once)
python -c "from amplihack.recipes import update_manifest; update_manifest()"

# 2. Check periodically for upstream updates
python -c "from amplihack.recipes import sync_upstream; print(sync_upstream())"

# 3. Check for local modifications before committing
python -c "from amplihack.recipes import check_upstream_changes; print(check_upstream_changes())"
```

You can also add this to a git pre-commit hook or CI job to automatically stay in sync.

## Creating Custom Recipes

1. Create a YAML file in `~/.amplihack/.claude/recipes/`:

```yaml
# ~/.amplihack/.claude/recipes/my-workflow.yaml
name: my-workflow
description: "Custom workflow for frontend components"
version: "1.0"

context:
  component_name: ""
  repo_path: "."

steps:
  - id: scaffold
    type: bash
    command: "mkdir -p {{repo_path}}/src/components/{{component_name}}"

  - id: design-api
    agent: amplihack:api-designer
    prompt: |
      Design the public API for a React component named {{component_name}}.
      Follow the project's existing component patterns.
    output: api_design

  - id: implement
    agent: amplihack:builder
    prompt: |
      Implement the {{component_name}} component based on this API design:
      {{api_design}}
    output: implementation

  - id: write-tests
    agent: amplihack:tester
    prompt: |
      Write tests for {{component_name}} covering:
      - Rendering
      - User interactions
      - Edge cases

  - id: run-tests
    type: bash
    command: "cd {{repo_path}} && npm test -- --testPathPattern={{component_name}}"
```

2. Validate the recipe:

```bash
amplihack recipe validate my-workflow.yaml
```

Expected output:

```
Validating my-workflow.yaml...
  [OK] Valid YAML syntax
  [OK] Required fields present (name, steps)
  [OK] All step names unique
  [OK] Template variables resolve against context
  [OK] Agent references valid (api-designer, builder, tester)
  [OK] No circular dependencies

Recipe "my-workflow" is valid (5 steps).
```

3. Run it:

```bash
amplihack recipe run my-workflow \
  --context component_name="UserAvatar" \
  --context repo_path="."
```

## Troubleshooting

### Recipe Discovery Issues

**Problem**: `amplihack recipe list` shows no recipes or missing expected recipes.

**Solution**: Recipe discovery automatically searches standard locations. Verify bundled recipes exist:

```bash
# Check bundled recipe locations
ls amplifier-bundle/recipes/*.yaml
ls src/amplihack/amplifier-bundle/recipes/*.yaml

# Check user-installed recipes
ls ~/.amplihack/.claude/recipes/*.yaml

# Check project-specific recipes
ls .claude/recipes/*.yaml
```

All bundled recipes (default-workflow, investigation, etc.) are automatically discovered. No manual installation required.

### Context Validation Errors

**Problem**: Recipe fails with "Invalid context format" or "Missing required context variable".

**Solution**: Use clear `key=value` format with fail-fast validation:

```bash
# Correct format (key=value pairs)
amplihack recipe run default-workflow \
  --context task_description="Add authentication" \
  --context repo_path="."

# Wrong format (will fail with clear error)
amplihack recipe run default-workflow \
  --context '{"task_description": "Add auth"}'  # ❌ JSON format not supported
```

Context validation now provides immediate, actionable error messages indicating which variables are missing or malformed.

### Agent Reference Errors

**Problem**: Recipe validation fails with "Agent not found" for `amplihack:agent-name`.

**Solution**: All recipes use correct `amplihack:` namespace for agents:

```yaml
# Correct agent reference
steps:
  - id: design
    agent: amplihack:architect  # ✅ Includes namespace
    prompt: "Design solution..."

# Wrong agent reference
steps:
  - id: design
    agent: architect  # ❌ Missing namespace (older format)
    prompt: "Design solution..."
```

All bundled recipes have been updated to use proper `amplihack:` namespace references.

### Dry-Run JSON Issues

**Problem**: Dry-run mode with conditional steps or `parse_json=true` produces invalid output.

**Solution**: Dry-run now outputs valid mock JSON for conditional steps:

```bash
# Dry-run with JSON parsing steps
amplihack recipe run default-workflow --dry-run

# Expected output for parse_json steps
[Step 5/22] parse-test-results (type: bash, parse_json: true)
  Would execute: pytest --json-report
  Would parse as JSON: {"mock": "data", "status": "dry-run"}
  → Output: test_results

# Conditional steps show evaluation
[Step 10/22] deploy (condition: tests_pass)
  Would evaluate condition: tests_pass = {"mock": "data"}
  Condition would evaluate to: true
  Would run agent: amplihack:deployment
```

Dry-run mode now handles all step types including bash commands with JSON parsing and conditional execution.

### YAML Syntax Errors

**Problem**: Recipe validation fails with YAML parse errors.

**Solution**: All recipe YAML files have been validated and parse successfully:

```bash
# Validate before running
amplihack recipe validate my-recipe.yaml

# Expected successful validation output
Validating my-recipe.yaml...
  [OK] Valid YAML syntax
  [OK] Required fields present (name, steps)
  [OK] All step IDs unique
  [OK] Agent references valid
  [OK] Template variables resolve

Recipe "my-recipe" is valid (5 steps)
```

All bundled recipes pass YAML validation without errors.

## Integration with Amplihack

### UltraThink

When `/ultrathink` is invoked, it reads `DEFAULT_WORKFLOW.md` and orchestrates agents through each step. The Recipe Runner replaces this orchestration with code-enforced execution. The `default-workflow` recipe encodes the same 22 steps from `DEFAULT_WORKFLOW.md` in YAML, so the process stays identical while enforcement moves from prompts to code.

```bash
# Before: prompt-based enforcement
/ultrathink "Add user authentication"

# After: code-enforced execution (same 22 steps)
amplihack recipe run default-workflow \
  --context task_description="Add user authentication"
```

Both approaches produce the same result. The difference is that the recipe version cannot skip steps.

### Existing Agents

Recipes reference agents by their filename (without `.md`) from `~/.amplihack/.claude/agents/amplihack/`. All 38 agents work with the Recipe Runner:

- Core agents: `architect`, `builder`, `reviewer`, `tester`
- Specialized agents: `security`, `database`, `optimizer`, `cleanup`, `analyzer`
- Workflow agents: `prompt-writer`, `ambiguity`, `patterns`

### Workflow Files

The `default-workflow` recipe is a direct translation of `~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md` into executable YAML. If you edit the workflow markdown, re-generate the recipe to keep them in sync:

```bash
amplihack recipe sync default-workflow
```

### CLI Integration

Recipe Runner commands are available under the `amplihack recipe` subcommand group:

```
amplihack recipe list                    # List available recipes
amplihack recipe run <name> [options]    # Execute a recipe
amplihack recipe validate <file>         # Validate recipe YAML
amplihack recipe sync <name>             # Sync recipe from workflow markdown
amplihack recipe show <name>             # Print recipe steps and metadata
```

## Resilience, Idempotency & Known Fixes

These documents explain bugs that caused hollow-success failures and the rules
introduced to prevent recurrence:

- **[Recent Fixes — April 2026](RECENT_FIXES_APRIL_2026.md)** — eval async/sync boundary bugs, LLM provider env override, code-visualizer multi-language support (PRs #4471, #4472, #4477, #4480)
- **[Recent Fixes — March 2026](RECENT_FIXES_MARCH_2026.md)** — worktree execution context, hook reinjection suppression, pre-commit retry, checkpoint commits, context validation
- **[Worktree Reattach & Prune Fix](step-04-worktree-reattach-prune.md)** — why `git worktree prune` must follow every `rm -rf` before `git worktree add`
