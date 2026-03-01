# Smart Context Inference: Environment-Based Configuration

**Diátaxis category**: Explanation

This document explains how the recipe runner's smart context inference works, why it was implemented, and how it improves the user experience when running recipes.

## Contents

- [The Problem: Verbose Context Flags](#the-problem-verbose-context-flags)
- [The Solution: Environment Variable Inference](#the-solution-environment-variable-inference)
- [How It Works](#how-it-works)
- [Design Decisions](#design-decisions)
- [Use Cases](#use-cases)
- [Backward Compatibility](#backward-compatibility)

## The Problem: Verbose Context Flags

### Before Smart Inference

Running a recipe required explicitly passing every context variable via `--context` flags:

```bash
amplihack recipe run default-workflow \
  --context task_description="Add user authentication" \
  --context repo_path="." \
  --context branch_name="feat/user-auth" \
  --context base_branch="main" \
  --context run_tests="true"
```

### Issues

1. **Verbose**: Long command lines for recipes with many context variables
2. **Repetitive**: Same values repeated across multiple recipe runs
3. **Error-Prone**: Easy to forget required variables or mistype values
4. **CI/CD Friction**: Scripts must construct complex command lines
5. **Session State**: No way to share context across multiple recipe runs in a session

## The Solution: Environment Variable Inference

### After Smart Inference

The same recipe run can now be simplified:

```bash
# Set context once
export AMPLIHACK_CONTEXT_TASK_DESCRIPTION="Add user authentication"
export AMPLIHACK_REPO_PATH="."
export AMPLIHACK_CONTEXT_BRANCH_NAME="feat/user-auth"

# Run without explicit --context (values inferred automatically)
amplihack recipe run default-workflow
```

### Benefits

1. **Concise**: Shorter command lines
2. **Reusable**: Set once, use across multiple recipe runs
3. **CI/CD Friendly**: Environment variables are native to CI systems
4. **Session State**: Context persists across commands in a session
5. **Explicit Override**: Can still use `--context` to override env vars

## How It Works

### Inference Priority (Highest to Lowest)

When the recipe runner needs a context variable value, it searches in this order:

1. **Explicit `--context` flags** (highest priority)
   ```bash
   amplihack recipe run my-recipe --context key=value
   ```

2. **`AMPLIHACK_CONTEXT_<KEY>` environment variables**
   ```bash
   export AMPLIHACK_CONTEXT_QUESTION="What is amplihack?"
   amplihack recipe run qa-workflow
   # question inferred automatically
   ```

3. **Well-known environment variables**
   - `AMPLIHACK_TASK_DESCRIPTION` → `task_description`
   - `AMPLIHACK_REPO_PATH` → `repo_path`
   ```bash
   export AMPLIHACK_TASK_DESCRIPTION="Add rate limiting"
   amplihack recipe run default-workflow
   ```

4. **Recipe YAML defaults** (lowest priority)
   ```yaml
   context:
     repo_path: "."  # Used if not provided via flags or env vars
   ```

### Example: Variable Resolution

Given this recipe definition:

```yaml
name: example-workflow
context:
  task_description: ""  # Required
  repo_path: "."        # Optional with default
  branch_name: ""       # Optional
```

And this environment:

```bash
export AMPLIHACK_CONTEXT_TASK_DESCRIPTION="Add caching"
export AMPLIHACK_REPO_PATH="/home/user/myproject"
```

When you run:

```bash
amplihack recipe run example-workflow --context branch_name="feat/caching"
```

The recipe runner resolves:
- `task_description` = `"Add caching"` (from `AMPLIHACK_CONTEXT_TASK_DESCRIPTION`)
- `repo_path` = `"/home/user/myproject"` (from `AMPLIHACK_REPO_PATH`)
- `branch_name` = `"feat/caching"` (from explicit `--context` flag)

## Design Decisions

### Why Two Prefixes: `AMPLIHACK_CONTEXT_*` and Well-Known Vars?

**Decision**: Support both generic `AMPLIHACK_CONTEXT_<KEY>` pattern and well-known variables like `AMPLIHACK_TASK_DESCRIPTION`.

**Rationale**:

1. **Generic prefix (`AMPLIHACK_CONTEXT_*`)**: Handles any context variable
   - Works for custom recipes with unique variables
   - Clear namespace (all context variables use same prefix)
   - Example: `AMPLIHACK_CONTEXT_CUSTOM_VAR` → `custom_var`

2. **Well-known variables**: Common values used across many recipes
   - Shorter names for frequently used variables
   - More natural for CI/CD systems
   - Examples: `AMPLIHACK_TASK_DESCRIPTION`, `AMPLIHACK_REPO_PATH`

### Why Not Just Use `--context-file`?

**Considered**: Users could create a JSON file with all context variables:

```bash
cat > context.json <<EOF
{
  "task_description": "Add caching",
  "repo_path": ".",
  "branch_name": "feat/caching"
}
EOF

amplihack recipe run my-recipe --context-file context.json
```

**Why This Isn't Enough**:

1. **File Management**: Users must create, track, and clean up context files
2. **CI/CD Integration**: CI systems naturally use environment variables, not files
3. **Session State**: Files don't persist across multiple commands in a shell session
4. **Override Friction**: Overriding one variable requires editing the file or using both `--context-file` and `--context` flags

Environment variables solve all these issues while `--context-file` remains available for complex scenarios.

### Why Highest Priority for `--context` Flags?

**Decision**: Explicit `--context` flags always win, even if environment variables are set.

**Rationale**:

1. **Principle of Least Surprise**: Explicit always beats implicit
2. **Override Mechanism**: Users can temporarily override env vars without unsetting them
3. **Debugging**: Easy to test different values without changing environment

**Example**:

```bash
# Set default in environment
export AMPLIHACK_CONTEXT_TASK_DESCRIPTION="Add auth"

# Override for one run
amplihack recipe run my-recipe --context task_description="Add logging"
# Uses "Add logging", not "Add auth"

# Next run uses environment value again
amplihack recipe run my-recipe
# Uses "Add auth"
```

## Use Cases

### CI/CD Pipelines

**Scenario**: GitHub Actions workflow runs multiple recipes with shared context.

**Before**:

```yaml
- name: Run default workflow
  run: |
    amplihack recipe run default-workflow \
      --context task_description="${{ github.event.pull_request.title }}" \
      --context repo_path="${{ github.workspace }}" \
      --context pr_number="${{ github.event.pull_request.number }}"

- name: Run verification workflow
  run: |
    amplihack recipe run verification-workflow \
      --context repo_path="${{ github.workspace }}" \
      --context pr_number="${{ github.event.pull_request.number }}"
```

**After**:

```yaml
- name: Set context
  run: |
    echo "AMPLIHACK_TASK_DESCRIPTION=${{ github.event.pull_request.title }}" >> $GITHUB_ENV
    echo "AMPLIHACK_REPO_PATH=${{ github.workspace }}" >> $GITHUB_ENV
    echo "AMPLIHACK_CONTEXT_PR_NUMBER=${{ github.event.pull_request.number }}" >> $GITHUB_ENV

- name: Run default workflow
  run: amplihack recipe run default-workflow

- name: Run verification workflow
  run: amplihack recipe run verification-workflow
```

**Benefits**: Context set once, reused across multiple steps.

### Interactive Development

**Scenario**: Developer working on a feature, running multiple recipes during development.

**Before**:

```bash
# Run investigation
amplihack recipe run investigation \
  --context task_description="Understand auth flow" \
  --context repo_path="."

# Run implementation
amplihack recipe run default-workflow \
  --context task_description="Add OAuth support" \
  --context repo_path="." \
  --context branch_name="feat/oauth"

# Run verification
amplihack recipe run verification-workflow \
  --context repo_path="."
```

**After**:

```bash
# Set once at start of session
export AMPLIHACK_REPO_PATH="."
export AMPLIHACK_CONTEXT_BRANCH_NAME="feat/oauth"

# Concise commands
amplihack recipe run investigation \
  --context task_description="Understand auth flow"

amplihack recipe run default-workflow \
  --context task_description="Add OAuth support"

amplihack recipe run verification-workflow
```

**Benefits**: Less typing, less repetition, faster iteration.

### Docker/Container Environments

**Scenario**: Recipe runs inside a container with context passed via environment variables.

**Before**:

```bash
docker run --rm \
  -v $(pwd):/workspace \
  amplihack/recipe-runner \
  amplihack recipe run default-workflow \
  --context task_description="Add caching" \
  --context repo_path="/workspace"
```

**After**:

```bash
docker run --rm \
  -v $(pwd):/workspace \
  -e AMPLIHACK_CONTEXT_TASK_DESCRIPTION="Add caching" \
  -e AMPLIHACK_REPO_PATH="/workspace" \
  amplihack/recipe-runner \
  amplihack recipe run default-workflow
```

**Benefits**: Standard Docker pattern, no need to pass complex `--context` strings.

### Multi-Recipe Batch Execution

**Scenario**: Running multiple recipes in sequence with shared context.

**Before**:

```bash
for recipe in investigation default-workflow verification-workflow; do
  amplihack recipe run $recipe \
    --context repo_path="." \
    --context branch_name="feat/new-feature" \
    --context task_description="Add new feature"
done
```

**After**:

```bash
export AMPLIHACK_REPO_PATH="."
export AMPLIHACK_CONTEXT_BRANCH_NAME="feat/new-feature"
export AMPLIHACK_CONTEXT_TASK_DESCRIPTION="Add new feature"

for recipe in investigation default-workflow verification-workflow; do
  amplihack recipe run $recipe
done
```

**Benefits**: Clean loop, no repeated context flags.

## Backward Compatibility

### Fully Backward Compatible

The smart context inference feature is **100% backward compatible**:

1. **Explicit `--context` flags still work**: Existing scripts and commands continue to function exactly as before.

   ```bash
   # This still works exactly as before
   amplihack recipe run my-recipe --context key=value
   ```

2. **No behavior changes if env vars are not set**: If environment variables are not defined, the recipe runner falls back to YAML defaults (same as before).

3. **Explicit flags override env vars**: If both are set, explicit flags win (principle of least surprise).

### Migration Path

Users can adopt smart context inference gradually:

**Phase 1**: Continue using explicit `--context` flags
```bash
amplihack recipe run my-recipe --context key=value
```

**Phase 2**: Move common values to environment variables
```bash
export AMPLIHACK_CONTEXT_KEY=value
amplihack recipe run my-recipe
```

**Phase 3**: Fully adopt environment-based configuration
```bash
# .env file or shell startup
export AMPLIHACK_REPO_PATH="."
export AMPLIHACK_CONTEXT_DEFAULT_BRANCH="main"

# All recipe runs use inferred values
amplihack recipe run recipe1
amplihack recipe run recipe2
```

No breaking changes at any phase.

## Conclusion

Smart context inference improves the recipe runner user experience by:

1. **Reducing Verbosity**: Shorter commands, less typing
2. **Improving Reusability**: Set once, use multiple times
3. **CI/CD Integration**: Native environment variable support
4. **Maintaining Backward Compatibility**: Existing scripts continue to work

The implementation follows the principle of least surprise: explicit always beats implicit, and users can adopt the feature gradually without changing existing workflows.

---

**Related Documentation**:
- [Recipe CLI How-To Guide](../howto/recipe-cli-commands.md) - Task-oriented examples
- [Recipe CLI Reference](../reference/recipe-cli-reference.md) - Complete command documentation
- [Dev Orchestrator Tutorial](../tutorials/dev-orchestrator-tutorial.md) - Using `/dev` with recipes
