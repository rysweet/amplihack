# Recipe Runner Integration with UltraThink Orchestrator

**Document Type**: How-To Guide
**Audience**: Developers using amplihack
**Status**: [IMPLEMENTED] - Production Ready
**Last Updated**: 2026-02-15

## Overview

The UltraThink orchestrator now uses Recipe Runner as its primary execution path, providing code-enforced workflow execution with automatic fallback to prompt-based methods. This integration transforms workflows from suggestion-based prompts into deterministic, fail-fast Python code.

**What This Means:**

- Workflow steps execute via Python SDK adapters (not just LLM prompts)
- Failures stop execution immediately with clear error messages
- Context accumulates between steps automatically
- Conditional logic works reliably (skip steps based on runtime conditions)
- Full backward compatibility maintained (existing workflows unchanged)

## Quick Start

### Using Recipe Runner (Default Behavior)

```bash
# Recipe Runner is enabled by default
/ultrathink implement JWT authentication

# Recipe Runner automatically:
# 1. Detects this is a development task
# 2. Loads default-workflow recipe
# 3. Executes all 23 steps with code enforcement
# 4. Accumulates context between steps
# 5. Stops on first failure (fail-fast)
```

### Forcing Prompt-Based Execution (When Needed)

```bash
# Disable Recipe Runner for this session
export AMPLIHACK_USE_RECIPES=0

# Now uses workflow skills or markdown workflows
/ultrathink implement JWT authentication

# Use cases for disabling:
# - Debugging workflow issues
# - Testing prompt-based execution
# - Recipe Runner has bugs
# - Developing new workflow features
```

## Three-Tier Fallback System

The ultrathink command follows this execution hierarchy:

```
┌─────────────────────────────────────────────────────────────┐
│ TIER 1: Recipe Runner (Code-Enforced)                      │
│ ✓ Python SDK adapters execute each step                    │
│ ✓ Fail-fast on errors                                      │
│ ✓ Context accumulation automatic                           │
│ ✓ Conditional execution reliable                           │
│ ✗ Requires amplihack.recipes module                        │
└─────────────────────────────────────────────────────────────┘
                           ↓ Falls back to
┌─────────────────────────────────────────────────────────────┐
│ TIER 2: Workflow Skills (Prompt-Based + TodoWrite)         │
│ ✓ Structured prompts guide execution                       │
│ ✓ Agent orchestration defined                              │
│ ✓ TodoWrite tracks progress                                │
│ ✗ No code enforcement (relies on Claude following)         │
└─────────────────────────────────────────────────────────────┘
                           ↓ Falls back to
┌─────────────────────────────────────────────────────────────┐
│ TIER 3: Markdown Workflows (Baseline Prompt-Based)         │
│ ✓ Always available (.claude/workflow/*.md)                 │
│ ✓ Baseline workflow instructions                           │
│ ✗ No code enforcement (relies on Claude following)         │
│ ✗ No structured tracking                                   │
└─────────────────────────────────────────────────────────────┘
```

### When Each Tier Activates

**Recipe Runner (Tier 1):**

- `AMPLIHACK_USE_RECIPES` is unset or set to `1` (default)
- `amplihack.recipes` module is installed and importable
- Recipe for the workflow exists (default-workflow, investigation-workflow, qa-workflow)

**Workflow Skills (Tier 2):**

- Recipe Runner unavailable (ImportError when trying `from amplihack.recipes import run_recipe_by_name`)
- OR `AMPLIHACK_USE_RECIPES=0` is set
- Skill definition exists in `.claude/skills/` directory

**Markdown Workflows (Tier 3):**

- Recipe Runner unavailable
- Workflow skill unavailable or fails to load
- Always works (last resort - workflows always exist in `.claude/workflow/`)

## How Recipe Runner Works

### Architecture

```python
# Recipe Runner execution flow for ultrathink

from amplihack.recipes import run_recipe_by_name

# 1. Load recipe YAML (default-workflow.yaml)
# 2. Create SDK adapter (bridges Claude Code tools to Python)
# 3. Execute steps sequentially via adapter
# 4. Accumulate context between steps
# 5. Stop on first error (fail-fast)

result = run_recipe_by_name(
    "default-workflow",
    adapter=sdk_adapter,  # Claude Code SDK adapter
    user_context={
        "task": "implement JWT authentication",
        "user_requirements": "Use RS256 algorithm, store keys in vault"
    }
)

# Result contains:
# - success: bool (True if all steps passed)
# - context: dict (accumulated context from all steps)
# - errors: list (any errors that occurred)
# - steps_executed: int (number of steps completed)
```

### Step Execution

Each workflow step executes through a Python adapter:

```python
# Example: Step 5 (Research and Design) in default-workflow

# Recipe YAML defines:
# - step: research_and_design
#   action: invoke_agent
#   agent: architect
#   inputs:
#     task: "{{ user_context.task }}"
#     requirements: "{{ user_context.user_requirements }}"
#   outputs:
#     design: context.design
#     architecture: context.architecture

# Recipe Runner translates this to:
result = sdk_adapter.invoke_agent(
    agent_type="architect",
    prompt=f"Design: {user_context['task']}\nRequirements: {user_context['user_requirements']}"
)

# Output stored in context for next step:
context['design'] = result['design']
context['architecture'] = result['architecture']

# Next step (Step 6) can access context['design']
```

### Context Accumulation

Context flows automatically between steps:

```python
# Step 5: architect agent produces design
context['design'] = {
    'modules': ['auth', 'tokens', 'validation'],
    'contracts': {...}
}

# Step 6: builder agent receives design automatically
result = sdk_adapter.invoke_agent(
    agent_type="builder",
    prompt=f"Implement: {context['design']}"  # Design passed automatically
)

# Step 7: tester agent receives implementation automatically
result = sdk_adapter.invoke_agent(
    agent_type="tester",
    prompt=f"Test: {context['implementation']}"  # Implementation passed automatically
)
```

### Fail-Fast Behavior

Recipe Runner stops on first error:

```python
# Step 5: architect agent succeeds
# Step 6: builder agent fails (syntax error)

# Recipe Runner behavior:
# 1. Immediately stops execution
# 2. Returns error details
# 3. Provides context up to failure point
# 4. Does NOT continue to Step 7

# Error handling in ultrathink:
try:
    result = run_recipe_by_name("default-workflow", adapter=sdk_adapter, user_context={...})
except Exception as e:
    print(f"Recipe execution failed at step {e.step_number}: {e.message}")
    print("Falling back to workflow skills...")
    Skill(skill="default-workflow")  # Fall back to Tier 2
```

## Environment Variable Control

### AMPLIHACK_USE_RECIPES

Controls Recipe Runner activation:

```bash
# Enable Recipe Runner (DEFAULT)
export AMPLIHACK_USE_RECIPES=1
/ultrathink implement feature

# Or leave unset (also enables)
unset AMPLIHACK_USE_RECIPES
/ultrathink implement feature

# Disable Recipe Runner (force prompt-based)
export AMPLIHACK_USE_RECIPES=0
/ultrathink implement feature
```

### When to Set AMPLIHACK_USE_RECIPES=0

**Debugging Scenarios:**

```bash
# Recipe Runner is failing and you need to debug
export AMPLIHACK_USE_RECIPES=0
/ultrathink implement feature
# Now uses workflow skills - easier to see what's happening
```

**Testing Scenarios:**

```bash
# Testing changes to workflow markdown files
export AMPLIHACK_USE_RECIPES=0
/ultrathink test workflow changes
# Ensures markdown changes work before updating recipes
```

**Development Scenarios:**

```bash
# Developing new workflow features not yet in recipes
export AMPLIHACK_USE_RECIPES=0
/ultrathink experiment with new feature
# Uses markdown workflows where new features are prototyped
```

**Workaround Scenarios:**

```bash
# Recipe Runner has a bug in the current version
export AMPLIHACK_USE_RECIPES=0
/ultrathink implement feature
# Temporary workaround until Recipe Runner is fixed
```

## Usage Examples

### Example 1: Development Task (Recipe Runner Succeeds)

```bash
# User invokes ultrathink
/ultrathink implement user registration with email verification

# UltraThink execution:
1. Detects task type: Development (keyword "implement")
2. Checks environment: AMPLIHACK_USE_RECIPES not set to 0
3. Tries Recipe Runner:
   from amplihack.recipes import run_recipe_by_name  # SUCCESS
4. Executes via Recipe Runner:
   result = run_recipe_by_name(
       "default-workflow",
       adapter=sdk_adapter,
       user_context={
           "task": "implement user registration with email verification"
       }
   )
5. Recipe Runner automatically:
   - Step 1: Task clarification (code-enforced)
   - Step 2: Git branch creation (code-enforced)
   - Step 3: Problem decomposition (code-enforced via prompt-writer agent)
   - Step 4: Research check (code-enforced)
   - Step 5: Architecture design (code-enforced via architect agent)
   - Step 6-22: Implementation, testing, PR creation (all code-enforced)
6. Context accumulates between steps automatically
7. Fail-fast if any step errors
8. Success: Full workflow executed with code enforcement
```

### Example 2: Investigation Task (Recipe Runner Succeeds)

```bash
# User invokes ultrathink
/ultrathink investigate how the caching layer works

# UltraThink execution:
1. Detects task type: Investigation (keyword "investigate")
2. Checks environment: AMPLIHACK_USE_RECIPES not set to 0
3. Tries Recipe Runner:
   from amplihack.recipes import run_recipe_by_name  # SUCCESS
4. Executes via Recipe Runner:
   result = run_recipe_by_name(
       "investigation-workflow",
       adapter=sdk_adapter,
       user_context={
           "task": "investigate caching layer"
       }
   )
5. Recipe Runner automatically:
   - Phase 1: Scope Definition (code-enforced)
   - Phase 2: Exploration Strategy (code-enforced)
   - Phase 3: Parallel Deep Dives (code-enforced via knowledge-archaeologist)
   - Phase 4: Verification & Testing (code-enforced)
   - Phase 5: Synthesis (code-enforced)
   - Phase 6: Knowledge Capture (code-enforced - updates DISCOVERIES.md)
6. Investigation findings stored in context
7. Success: Full investigation with code enforcement
```

### Example 3: Recipe Runner Unavailable (Falls Back to Skills)

```bash
# User invokes ultrathink
/ultrathink implement feature X

# UltraThink execution:
1. Detects task type: Development
2. Checks environment: AMPLIHACK_USE_RECIPES not set to 0
3. Tries Recipe Runner:
   from amplihack.recipes import run_recipe_by_name  # ImportError: No module named 'amplihack.recipes'
4. Falls back to workflow skills:
   Skill(skill="default-workflow")
5. Skill loads workflow instructions
6. Claude follows workflow steps via prompts (not code-enforced)
7. TodoWrite tracks progress
8. Success: Workflow completed (prompt-based, not code-enforced)
```

### Example 4: Force Prompt-Based Execution (AMPLIHACK_USE_RECIPES=0)

```bash
# User sets environment variable
export AMPLIHACK_USE_RECIPES=0

# User invokes ultrathink
/ultrathink implement feature Y

# UltraThink execution:
1. Detects task type: Development
2. Checks environment: AMPLIHACK_USE_RECIPES=0 (skip Recipe Runner)
3. Skips Recipe Runner (forced by environment variable)
4. Uses workflow skills directly:
   Skill(skill="default-workflow")
5. Skill loads workflow instructions
6. Claude follows workflow steps via prompts (not code-enforced)
7. TodoWrite tracks progress
8. Success: Workflow completed (prompt-based, not code-enforced)
```

### Example 5: Recipe Runner Fails Mid-Execution (Falls Back to Skills)

```bash
# User invokes ultrathink
/ultrathink implement complex feature Z

# UltraThink execution:
1. Detects task type: Development
2. Checks environment: AMPLIHACK_USE_RECIPES not set to 0
3. Tries Recipe Runner:
   from amplihack.recipes import run_recipe_by_name  # SUCCESS
4. Executes via Recipe Runner:
   result = run_recipe_by_name("default-workflow", adapter=sdk_adapter, user_context={...})
5. Recipe Runner executes:
   - Step 1-10: SUCCESS (code-enforced)
   - Step 11: FAILS (adapter error - SDK tool unavailable)
6. Recipe Runner stops immediately (fail-fast)
7. Error message:
   "Recipe execution failed at Step 11 (Mandatory Local Testing): SDK adapter error - Bash tool unavailable in this context"
8. UltraThink falls back to workflow skills:
   Skill(skill="default-workflow")
9. Skill resumes from Step 11 (prompt-based)
10. Success: Workflow completed (hybrid: code-enforced for Steps 1-10, prompt-based for 11-22)
```

## Context Passing to Recipe Runner

Recipe Runner receives context from ultrathink via `user_context` parameter:

### Development Tasks

```python
result = run_recipe_by_name(
    "default-workflow",
    adapter=sdk_adapter,
    user_context={
        "task": "implement JWT authentication",
        "user_requirements": "Use RS256 algorithm, store keys in vault",
        "user_constraints": "Must pass CI within 30 minutes",
        "project_context": {
            "language": "Python",
            "framework": "FastAPI",
            "auth_system": "existing-basic-auth"
        }
    }
)
```

### Investigation Tasks

```python
result = run_recipe_by_name(
    "investigation-workflow",
    adapter=sdk_adapter,
    user_context={
        "task": "investigate caching layer",
        "focus_areas": ["Redis integration", "cache invalidation", "performance"],
        "depth": "deep",  # quick, standard, deep
        "output_format": "architecture-doc"  # or "investigation-report"
    }
)
```

### Q&A Tasks

```python
result = run_recipe_by_name(
    "qa-workflow",
    adapter=sdk_adapter,
    user_context={
        "question": "what is the purpose of the workflow system?",
        "context_needed": ["workflow types", "execution hierarchy"],
        "detail_level": "concise"  # concise, balanced, detailed
    }
)
```

### Context Available to Recipe Steps

Each recipe step can access:

```python
# user_context (provided by ultrathink)
user_context = {
    "task": "...",
    "user_requirements": "...",
    # ... etc
}

# context (accumulated from previous steps)
context = {
    "clarified_requirements": {...},  # From Step 1
    "design": {...},                  # From Step 5
    "implementation": {...},          # From Step 6
    # ... etc
}

# Recipe step can use both:
result = sdk_adapter.invoke_agent(
    agent_type="builder",
    prompt=f"Task: {user_context['task']}\nDesign: {context['design']}"
)
```

## Troubleshooting

### Problem: Recipe Runner Not Activating

**Symptoms:**

- `/ultrathink` uses workflow skills instead of Recipe Runner
- No "Using Recipe Runner for code-enforced execution" message

**Diagnosis:**

```bash
# Check if Recipe Runner module is installed
python3 -c "from amplihack.recipes import run_recipe_by_name; print('Recipe Runner available')"

# Check environment variable
echo $AMPLIHACK_USE_RECIPES
# Should be: (empty) or "1" for Recipe Runner
# Should NOT be: "0" (this disables Recipe Runner)
```

**Solution:**

```bash
# If module not installed:
pip install amplihack[recipes]

# If environment variable is 0:
unset AMPLIHACK_USE_RECIPES
# or
export AMPLIHACK_USE_RECIPES=1
```

### Problem: Recipe Runner Fails with ImportError

**Symptoms:**

- Error message: "ImportError: No module named 'amplihack.recipes'"
- Falls back to workflow skills

**Diagnosis:**

```bash
# Check Python path
python3 -c "import sys; print('\n'.join(sys.path))"

# Check if recipes module exists
find ~/.local/lib/python*/site-packages/amplihack -name "recipes" -type d
```

**Solution:**

```bash
# Reinstall amplihack with recipes support
pip install --upgrade amplihack[recipes]

# Or install recipes module separately
pip install amplihack-recipes
```

### Problem: Recipe Execution Fails Mid-Workflow

**Symptoms:**

- Recipe starts executing
- Fails at specific step with error message
- Falls back to workflow skills for remaining steps

**Diagnosis:**

```bash
# Check Recipe Runner logs
cat ~/.amplihack/.claude/runtime/logs/<session_id>/recipe_runner.log

# Look for error at specific step:
# "Recipe execution failed at Step 11 (Mandatory Local Testing): [error details]"
```

**Solution:**

```bash
# If adapter error (SDK tool unavailable):
# - This is expected in some contexts (e.g., restricted environments)
# - Recipe Runner will fall back to workflow skills
# - No action needed

# If recipe definition error:
# - Report bug to amplihack maintainers
# - Temporary workaround: export AMPLIHACK_USE_RECIPES=0

# If step logic error:
# - Check if workflow step has changed (recipe may be outdated)
# - Update recipe YAML to match current workflow
```

### Problem: Context Not Passing Between Steps

**Symptoms:**

- Recipe executes but later steps missing data from earlier steps
- Agents report "no design provided" when design was created in Step 5

**Diagnosis:**

```bash
# Check Recipe Runner context logs
cat ~/.amplihack/.claude/runtime/logs/<session_id>/recipe_context.json

# Look for context at each step:
# {
#   "step_1": {"clarified_requirements": {...}},
#   "step_5": {"design": {...}},
#   "step_6": {}  # MISSING implementation
# }
```

**Solution:**

```bash
# Context accumulation is automatic in Recipe Runner
# If context is missing:
# 1. Check recipe YAML outputs definition for the failing step
# 2. Check if adapter properly extracts outputs from agent responses
# 3. Report bug to amplihack maintainers if both are correct

# Temporary workaround:
export AMPLIHACK_USE_RECIPES=0  # Use prompt-based execution
```

### Problem: Force Prompt-Based Not Working

**Symptoms:**

- Set `AMPLIHACK_USE_RECIPES=0`
- Recipe Runner still activates

**Diagnosis:**

```bash
# Check environment variable in current shell
echo $AMPLIHACK_USE_RECIPES

# Check if variable is exported (available to subprocesses)
env | grep AMPLIHACK_USE_RECIPES
```

**Solution:**

```bash
# Ensure variable is exported
export AMPLIHACK_USE_RECIPES=0

# Verify:
echo $AMPLIHACK_USE_RECIPES  # Should print: 0

# Try ultrathink again:
/ultrathink implement feature
```

### Problem: Recipe Runner Too Slow

**Symptoms:**

- Recipe execution takes significantly longer than prompt-based
- Steps seem to pause between execution

**Diagnosis:**

```bash
# Check Recipe Runner timing logs
cat ~/.amplihack/.claude/runtime/logs/<session_id>/recipe_timing.log

# Look for slow steps:
# Step 5 (Research and Design): 45.2s  # Expected
# Step 6 (Implementation): 120.5s      # Expected
# Step 11 (Mandatory Local Testing): 180.3s  # TOO SLOW
```

**Solution:**

```bash
# Recipe Runner may be slower than prompt-based due to code enforcement overhead
# This is expected trade-off for reliability

# If unacceptably slow:
# Option 1: Use prompt-based for time-sensitive work
export AMPLIHACK_USE_RECIPES=0

# Option 2: Optimize recipe steps (advanced)
# - Check if steps can run in parallel
# - Check if conditional skips can reduce work
# - Report performance issues to amplihack maintainers
```

## Migration Guide

**No migration needed!** The Recipe Runner integration is fully backward compatible:

- Existing workflows continue to work unchanged
- No code changes required
- No configuration changes required
- Workflows automatically use Recipe Runner when available
- Automatic fallback to prompt-based if Recipe Runner unavailable

### What Changed Under the Hood

| Aspect           | Before (Prompt-Based)           | After (Recipe Runner)                                   |
| ---------------- | ------------------------------- | ------------------------------------------------------- |
| **Execution**    | Claude follows markdown prompts | Python SDK adapters execute steps                       |
| **Context**      | Claude remembers context        | Context accumulated in Python dict                      |
| **Errors**       | Claude continues on errors      | Recipe Runner stops immediately (fail-fast)             |
| **Conditionals** | Claude interprets conditions    | Python evaluates conditions                             |
| **Agents**       | Invoked via Task tool           | Invoked via SDK adapter                                 |
| **Fallback**     | None (always prompt-based)      | Falls back to prompt-based if Recipe Runner unavailable |

### What Stayed the Same

- Workflow markdown files (still authoritative source of truth)
- Agent definitions (unchanged)
- User commands (`/ultrathink` syntax unchanged)
- Output format (same results, different execution path)
- TodoWrite tracking (still used for progress visibility)

### Verifying Your Setup

```bash
# Check if Recipe Runner is active
/ultrathink implement small test feature

# Look for this message in output:
# "Using Recipe Runner for code-enforced execution"

# If you see this instead:
# "Recipe Runner unavailable, falling back to workflow skills"
# Then Recipe Runner is not installed or disabled

# To verify Recipe Runner installation:
python3 -c "from amplihack.recipes import run_recipe_by_name; print('Recipe Runner installed')"
```

## Benefits of Recipe Runner Integration

### For Developers

**Reliability:**

- Fail-fast prevents cascading errors
- Code enforcement ensures steps actually execute (not just suggested)
- Deterministic behavior (same inputs → same outputs)

**Debugging:**

- Clear error messages at exact step that failed
- Context preserved up to failure point
- Can fallback to prompt-based for comparison

**Performance:**

- Context accumulation more efficient (Python dict vs. LLM memory)
- Conditional skips work reliably (no ambiguity)
- Parallel execution where defined in recipe

### For Workflow Authors

**Maintainability:**

- Single source of truth (markdown workflows drive recipes)
- Recipe YAML is generated from markdown (not manual maintenance)
- Changes to markdown automatically update recipes

**Evolution:**

- Can prototype new features in markdown (prompt-based)
- Graduate to recipes when proven (code-enforced)
- Both modes work simultaneously (gradual migration)

**Testing:**

- Can test recipes independently (unit tests for workflow steps)
- Can test prompt-based mode independently (AMPLIHACK_USE_RECIPES=0)
- Can compare both modes for regression testing

## Advanced Topics

### Creating Custom Recipes

See `docs/recipes/README.md` for complete guide on creating custom recipes that integrate with ultrathink.

### SDK Adapter Development

See `docs/recipes/SDK_ADAPTER_GUIDE.md` for guide on developing SDK adapters that bridge Claude Code tools to Recipe Runner.

### Recipe Testing

See `docs/recipes/TESTING_RECIPES.md` for guide on testing recipes independently before integrating with ultrathink.

## Related Documentation

- [Recipe Runner Overview](./README.md) - Core Recipe Runner concepts
- [Workflow System](./../WORKFLOW_SYSTEM.md) - How workflows are structured
- [UltraThink Command](./../../.claude/commands/amplihack/ultrathink.md) - Full ultrathink reference
- [Agent Orchestration](./../../.claude/context/CLAUDE.md#agent-delegation-strategy) - How agents are invoked

## Feedback and Issues

If you encounter issues with Recipe Runner integration:

1. Check troubleshooting section above
2. Try forcing prompt-based mode: `export AMPLIHACK_USE_RECIPES=0`
3. Report bugs at: https://github.com/amplihack/amplihack/issues
4. Include Recipe Runner logs from: `~/.amplihack/.claude/runtime/logs/<session_id>/`

---

**Remember**: Recipe Runner is an enhancement, not a requirement. If it's not working, the system automatically falls back to proven prompt-based execution. You always have a working workflow system.
