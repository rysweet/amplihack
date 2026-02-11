# Recipe Runner

A code-enforced workflow execution engine that reads declarative YAML recipe files and executes them step-by-step using AI agents. Unlike prompt-based workflow instructions that models can interpret loosely or skip, the Recipe Runner controls the execution loop in Python code -- making it physically impossible to skip steps.

## Contents

- [Why It Exists](#why-it-exists)
- [Quick Start](#quick-start)
- [Recipe YAML Format](#recipe-yaml-format)
- [SDK Adapters](#sdk-adapters)
- [Available Recipes](#available-recipes)
- [Creating Custom Recipes](#creating-custom-recipes)
- [Integration with Amplihack](#integration-with-amplihack)

## Why It Exists

Models frequently skip workflow steps when enforcement is purely prompt-based. A markdown file that says "you MUST follow all 22 steps" still relies on the model choosing to comply. The Recipe Runner moves enforcement from prompts to code: a Python `for` loop iterates over each step and calls the agent SDK, so the model never decides which step to run next.

**Prompt-based enforcement (before)**:

```markdown
## Step 7: Write Failing Tests

You MUST write tests before implementation. Do NOT skip this step.
```

The model can read this instruction and still jump to implementation.

**Code-enforced execution (after)**:

```python
for step in recipe.steps:
    result = adapter.run(step.agent, step.prompt)
    # The next step literally cannot start until this one completes
```

The model executes within a single step. The Python loop controls progression.

## Quick Start

```bash
# List available recipes
amplihack recipe list

# Execute a workflow recipe
amplihack recipe run default-workflow \
  --context '{"task_description": "Add user authentication", "repo_path": "."}'

# Dry run -- see what would execute without running anything
amplihack recipe run verification-workflow --dry-run

# Validate a recipe file without executing it
amplihack recipe validate my-recipe.yaml

# Run with a specific SDK adapter
amplihack recipe run default-workflow \
  --adapter copilot \
  --context '{"task_description": "Fix login bug", "repo_path": "."}'
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

| Field        | Type   | Required | Description                                                  |
| ------------ | ------ | -------- | ------------------------------------------------------------ |
| `id`         | string | Yes      | Unique step identifier within the recipe                     |
| `agent`      | string | No       | Agent reference in `namespace:name` format                   |
| `type`       | string | No       | `agent` (default when `agent` or `prompt` present) or `bash` |
| `prompt`     | string | No       | Prompt template sent to the agent                            |
| `command`    | string | No       | Shell command (when `type: bash`)                            |
| `output`     | string | No       | Context key to store step result under                       |
| `condition`  | string | No       | Python expression; step skips when false                     |
| `parse_json` | bool   | No       | Parse stdout as JSON and store as dict in context            |
| `mode`       | string | No       | Agent mode hint (e.g. `ANALYZE`, `DESIGN`)                   |

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

amplihack ships with 10 recipes covering the most common development workflows.

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
  --context '{"component_name": "UserAvatar", "repo_path": "."}'
```

## Integration with Amplihack

### UltraThink

When `/ultrathink` is invoked, it reads `DEFAULT_WORKFLOW.md` and orchestrates agents through each step. The Recipe Runner replaces this orchestration with code-enforced execution. The `default-workflow` recipe encodes the same 22 steps from `DEFAULT_WORKFLOW.md` in YAML, so the process stays identical while enforcement moves from prompts to code.

```bash
# Before: prompt-based enforcement
/ultrathink "Add user authentication"

# After: code-enforced execution (same 22 steps)
amplihack recipe run default-workflow \
  --context '{"task_description": "Add user authentication"}'
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
