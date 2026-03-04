# Changelog - 2026-03-04

Daily changelog of merged pull requests and their impact on amplihack4.

## Features

### Recipe Composition System (#2862)

**Added RECIPE step type for sub-recipe composition**

The recipe runner now supports composing recipes from sub-recipes using a new `RECIPE` step type.

**What Changed:**
- New `StepType.RECIPE` enum value in recipe models
- `Step` dataclass extended with `recipe` and `sub_context` fields
- `RecipeRunner` now includes `_execute_sub_recipe()` method for recursive execution
- Maximum recursion depth enforced via `MAX_RECIPE_DEPTH = 3` constant

**Use Cases:**
- Break complex workflows into reusable sub-recipes
- Create modular recipe libraries
- Compose workflows from building blocks

**Example:**
```yaml
steps:
  - type: RECIPE
    recipe: common/setup-environment
    sub_context:
      env_vars:
        DEBUG: "true"
```

**Reference:** See [Recipe System Reference](reference/recipes.md) for complete syntax.

---

### Configuration Persistence (#2860)

**NODE_OPTIONS memory settings now persist across sessions**

User memory configuration preferences are now saved to `~/.amplihack/config` (JSON format).

**What Changed:**
- First run prompts for NODE_OPTIONS consent, then persists to config file
- Returning users skip prompt, see informational message with saved settings
- Simple JSON format: `node_options_consent` (bool) + `node_options_limit_mb` (int)
- Other config keys preserved on write

**Benefits:**
- No repeated prompts after first configuration
- Clear visibility of current settings
- Easy to modify via config file

**Configuration File Location:**
```
~/.amplihack/config
```

**Format:**
```json
{
  "node_options_consent": true,
  "node_options_limit_mb": 8192
}
```

---

## Enhancements

### Azure DevOps Skill Auto-Activation (#2868)

**Improved auto-activation with keyword-rich descriptions**

The `azure-devops` and `azure-devops-cli` skills now activate more reliably through natural language.

**What Changed:**
- `azure-devops` skill: expanded description with keywords (ADO, work items, user stories, bugs, sprints, builds, releases)
- `azure-devops-cli` skill: added explicit `auto_activate_keywords` (az devops, az pipelines, az repos)

**Impact:**
- Better skill discovery in natural conversations
- More reliable activation without explicit slash commands

**Example Triggers:**
- "Show me ADO work items"
- "Run az devops pipeline"
- "Check sprint progress"

---

### Quality Audit Workflow (#2861)

**Fix-all-per-cycle enforcement + structured inputs**

The quality-audit recipe now enforces fixing all findings per cycle and supports structured configuration.

**What Changed:**
- **Fix-all-per-cycle rule**: Every confirmed finding must be fixed before next cycle
- New `verify-fixes` bash step validates fixes
- Strengthened fix step prompt with clearer expectations
- Recurse decision checks for NEW findings only
- **Structured inputs**: `severity_threshold`, `module_loc_limit`, `fix_all_per_cycle`, `categories`
- Recipe version bumped to v4.0.0

**Benefits:**
- More reliable audit completion
- Reproducible, configurable audits
- Better tracking of fix progress

**Configuration Example:**
```yaml
inputs:
  severity_threshold: medium
  module_loc_limit: 500
  fix_all_per_cycle: true
  categories: ["security", "performance"]
```

**Reference:** See [Quality Audit Guide](how-to/quality-audit.md) for usage.

---

## Documentation

### README/CONTRIBUTING Improvements (#2865)

**Filled documentation gaps identified by new-user review**

Multiple documentation improvements based on user feedback:

**What Changed:**
- (#2777) Explain what interactive session does after install
- (#2778) Clarify `uv sync` installs all deps into local `.venv`
- (#2780) Add "install prerequisites first" before install options
- (#2781) Expand first `/dev` mention with workflow explanation

**Impact:**
- Clearer onboarding experience
- Better understanding of installation process
- Reduced confusion about `/dev` command

---

## Diátaxis Framework Alignment

This changelog follows the [Diátaxis framework](https://diataxis.fr/) for documentation:

### Changes by Category

| Category | PRs | Documentation Type |
|----------|-----|-------------------|
| **Reference** | #2862, #2860, #2861, #2868 | Technical specifications, API details |
| **How-to** | #2862, #2860, #2861 | Task-oriented guides |
| **Tutorial** | #2865 | Learning-oriented guides |
| **Explanation** | - | Understanding-oriented articles |

### Documentation Updates Required

1. **Reference Updates:**
   - Recipe system reference (RECIPE step type)
   - Configuration reference (persistent config file)
   - Quality audit reference (v4.0.0 inputs)
   - Skills reference (auto-activation keywords)

2. **How-to Guides:**
   - How to compose sub-recipes
   - How to configure memory settings
   - How to run quality audits with structured inputs

3. **Tutorial Updates:**
   - Already completed in PR #2865

---

## Related Issues

- #2850: ADO skill auto-activation improvements
- #2821: Recipe composition feature request
- #2842: Quality audit fix-all-per-cycle rule
- #2843: Quality audit structured inputs
- #2777, #2778, #2780, #2781: Documentation gaps

---

## Contributors

All PRs generated with [Claude Code](https://claude.com/claude-code)

---

## Next Steps

1. Update recipe system reference documentation
2. Create how-to guide for recipe composition
3. Update configuration reference with persistence details
4. Document quality audit v4.0.0 features
5. Update skills reference with auto-activation improvements
