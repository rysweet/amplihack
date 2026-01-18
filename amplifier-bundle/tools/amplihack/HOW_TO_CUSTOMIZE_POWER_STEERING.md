# How to Customize Power-Steering Mode

This guide explains how to customize power-steering mode considerations to match your team's specific workflow and requirements.

## Table of Contents

1. [Overview](#overview)
2. [Understanding Considerations](#understanding-considerations)
3. [YAML File Format](#yaml-file-format)
4. [Customization Examples](#customization-examples)
5. [Adding Custom Considerations](#adding-custom-considerations)
6. [Troubleshooting](#troubleshooting)

## Overview

Power-steering mode uses a YAML configuration file to define the 21 considerations that verify session completeness. You can:

- **Modify existing considerations**: Change questions, severity, or enable/disable checks
- **Add custom considerations**: Define team-specific requirements
- **Use generic or specific checkers**: Simple keyword matching or dedicated analysis functions

**Configuration File Location:**

```
.claude/tools/amplihack/considerations.yaml
```

## Understanding Considerations

Each consideration checks a specific aspect of your work:

### Consideration Structure

```yaml
- id: unique_identifier # Unique ID for this consideration
  category: Category Name # One of 6 categories
  question: Human-readable question? # Natural language prompt
  description: What this checks # Detailed explanation
  severity: blocker # "blocker" or "warning"
  checker: method_name # Checker method or "generic"
  enabled: true # true/false to enable/disable
```

### Categories

1. **Session Completion & Progress** - TODOs, objectives, documentation
2. **Workflow Process Adherence** - DEFAULT_WORKFLOW, investigations
3. **Code Quality & Philosophy Compliance** - Zero-BS, no shortcuts
4. **Testing & Local Validation** - Test execution, interactive testing
5. **PR Content & Quality** - Description, related changes, root pollution
6. **CI/CD & Mergeability Status** - CI passing, rebase, pre-commit/CI sync

### Severity Levels

- **blocker**: Blocks session end if check fails (red light)
- **warning**: Advisory only, doesn't block (yellow light)

### Checker Types

- **Specific checker**: Named method like `_check_todos_complete`
  - Uses sophisticated analysis logic
  - Highly accurate for specific scenarios

- **generic**: Simple keyword matching
  - Extracts keywords from question
  - Searches transcript for matches
  - Defaults to satisfied (fail-open)
  - Good for custom considerations

## YAML File Format

### Basic Structure

The YAML file contains a list of consideration objects:

```yaml
# Comment lines start with #

- id: first_consideration
  category: Session Completion & Progress
  question: Is the first thing done?
  description: Checks if first thing completed
  severity: blocker
  checker: _check_first_thing
  enabled: true

- id: second_consideration
  category: Code Quality & Philosophy Compliance
  question: Is the second thing done?
  description: Checks if second thing completed
  severity: warning
  checker: generic
  enabled: true
```

### Required Fields

All considerations MUST have these fields:

1. `id` - Unique identifier (string)
2. `category` - Category name (string)
3. `question` - Human-readable question (string)
4. `description` - What this checks (string)
5. `severity` - Either "blocker" or "warning"
6. `checker` - Method name or "generic"
7. `enabled` - Boolean (true/false)

### Validation Rules

- **id**: Must be unique across all considerations
- **severity**: Only "blocker" or "warning" allowed
- **enabled**: Must be boolean (not "yes", "1", etc.)
- **checker**: Must be valid method name or "generic"

## Customization Examples

### Example 1: Disable a Consideration

To skip a check you don't need:

```yaml
- id: presentation_needed
  category: Session Completion & Progress
  question: Does work need presentation deck?
  description: Detects high-impact work for stakeholders
  severity: warning
  checker: _check_presentation_needed
  enabled: false # Changed from true to false
```

### Example 2: Change Severity

Make a warning into a blocker (or vice versa):

```yaml
- id: documentation_updates
  category: Session Completion & Progress
  question: Were relevant documentation files updated?
  description: Verifies README, docs reflect changes
  severity: blocker # Changed from "warning" to "blocker"
  checker: _check_documentation_updates
  enabled: true
```

### Example 3: Modify Question Text

Customize the prompt text:

```yaml
- id: local_testing
  category: Testing & Local Validation
  question: Did you run and verify all tests locally? # Customized
  description: Verifies tests were executed and passed locally
  severity: blocker
  checker: _check_local_testing
  enabled: true
```

### Example 4: Add Team-Specific Consideration

Add a custom consideration with generic checker:

```yaml
# At the end of the file, add:

- id: security_scan
  category: Security & Compliance
  question: Was security scanning performed?
  description: Ensures security tools were run on code changes
  severity: blocker
  checker: generic # Uses simple keyword matching
  enabled: true
```

### Example 5: Add Multiple Custom Checks

```yaml
# Custom security consideration
- id: security_review
  category: Security & Compliance
  question: Was security review completed?
  description: Verifies security team reviewed changes
  severity: blocker
  checker: generic
  enabled: true

# Custom performance consideration
- id: performance_impact
  category: Performance & Optimization
  question: Was performance impact assessed?
  description: Checks if performance implications were analyzed
  severity: warning
  checker: generic
  enabled: true

# Custom compliance consideration
- id: gdpr_compliance
  category: Legal & Compliance
  question: Were GDPR requirements verified?
  description: Ensures data privacy regulations followed
  severity: blocker
  checker: generic
  enabled: true
```

## Adding Custom Considerations

### Step 1: Identify the Requirement

Ask yourself:

- What should be checked before ending this session?
- Is this a blocker or a warning?
- Can I use the generic checker, or do I need custom logic?

### Step 2: Write the YAML Entry

Add to the end of `considerations.yaml`:

```yaml
# CUSTOM CONSIDERATIONS
# Add team-specific checks below

- id: my_custom_check
  category: Custom Category
  question: Is my custom requirement satisfied?
  description: Checks for team-specific requirement
  severity: blocker
  checker: generic
  enabled: true
```

### Step 3: Test the Consideration

1. Save the YAML file
2. Start a new session (changes take effect next session)
3. Trigger the consideration by including relevant keywords in your work
4. Verify the check appears in power-steering output

### Step 4: Refine as Needed

- Adjust severity if too strict/lenient
- Modify question text for clarity
- Disable if creating false positives

## Generic Checker Behavior

The generic checker is simple but effective:

### How It Works

1. **Extract keywords** from the question
   - Removes common words ("is", "the", "are")
   - Keeps meaningful terms (>3 characters)

2. **Search transcript** for keywords
   - Looks in user and assistant messages
   - Case-insensitive matching

3. **Default to satisfied** (fail-open)
   - Avoids false positives
   - Only flags if clear violation detected

### Example: Generic Checker in Action

```yaml
question: Were security scans performed?
# Keywords extracted: "security", "scans", "performed"
# Searches transcript for these terms
# If found: likely satisfied
# If not found: may still be satisfied (fail-open)
```

### Limitations

- **Simple keyword matching**: Not context-aware
- **Fail-open default**: Conservative to avoid false positives
- **No complex logic**: For sophisticated checks, use specific checkers

### When to Use Generic

✅ **Good for:**

- Team-specific requirements
- Workflow reminders
- Documentation checks
- Simple presence/absence checks

❌ **Not good for:**

- Complex logic (multiple conditions)
- Code analysis (AST parsing)
- Statistical analysis (coverage, performance)
- External API checks

## Available Specific Checkers

These checkers have sophisticated logic built-in:

### Session Completion

- `_check_todos_complete` - All TodoWrite items completed
- `_check_objective_completion` - Original user goal achieved
- `_check_documentation_updates` - Docs updated with code changes
- `_check_next_steps` - Follow-up tasks documented

### Workflow & Process

- `_check_dev_workflow_complete` - DEFAULT_WORKFLOW followed
- `_check_investigation_docs` - Investigation findings captured
- `_check_docs_organization` - Docs in correct directories

### Code Quality

- `_check_philosophy_compliance` - Zero-BS (no TODOs, stubs)
- `_check_shortcuts` - No quality compromises
- `_check_root_pollution` - No inappropriate root files

### Testing

- `_check_local_testing` - Tests executed and passed
- `_check_interactive_testing` - Manual verification done

### PR & CI/CD

- `_check_ci_status` - CI checks passing
- `_check_pr_description` - PR has summary and test plan
- `_check_review_responses` - Review feedback addressed
- `_check_branch_rebase` - Branch up to date with main
- `_check_ci_precommit_mismatch` - CI and pre-commit aligned
- `_check_unrelated_changes` - No scope creep

### Miscellaneous

- `_check_agent_unnecessary_questions` - Agent not asking obvious questions
- `_check_tutorial_needed` - New features have examples
- `_check_presentation_needed` - High-impact work has presentation

## Troubleshooting

### Problem: YAML File Not Loading

**Symptoms:**

- Warning in logs: "Considerations YAML not found"
- Falls back to Phase 1 (5 checkers)

**Solutions:**

1. Verify file exists: `.claude/tools/amplihack/considerations.yaml`
2. Check file permissions (must be readable)
3. Look for typos in filename

### Problem: YAML Parse Error

**Symptoms:**

- Error in logs: "Invalid YAML structure"
- Falls back to Phase 1

**Solutions:**

1. Validate YAML syntax (use online validator)
2. Check indentation (must use spaces, not tabs)
3. Ensure all strings are properly quoted if needed
4. Look for unmatched brackets or quotes

### Problem: Consideration Not Running

**Symptoms:**

- Consideration defined but not appearing in results

**Solutions:**

1. Check `enabled: true` in YAML
2. Verify not disabled in config file (`.power_steering_config`)
3. Confirm consideration meets validation rules
4. Check logs for validation errors

### Problem: False Positives

**Symptoms:**

- Consideration fails when it shouldn't
- Blocks sessions incorrectly

**Solutions:**

1. **For generic checkers:**
   - Refine question keywords
   - Consider changing to specific checker
   - Change severity from "blocker" to "warning"

2. **For specific checkers:**
   - Review checker logic (may need code changes)
   - Temporarily disable the consideration
   - Report issue if checker has bugs

### Problem: False Negatives

**Symptoms:**

- Consideration passes when it should fail
- Doesn't catch issues

**Solutions:**

1. **For generic checkers:**
   - Generic checkers are fail-open by default
   - Consider implementing a specific checker
   - Add more detailed keywords to question

2. **For specific checkers:**
   - Review checker heuristics
   - May need to enhance checker logic

### Problem: Too Many Blockers

**Symptoms:**

- Can't end session even when work is complete
- Multiple false positives

**Solutions:**

1. Review severity levels - change blockers to warnings
2. Disable non-critical considerations
3. Adjust checker sensitivity
4. Use `export AMPLIHACK_SKIP_POWER_STEERING=1` temporarily

## Configuration File Reference

### Minimal Valid Consideration

```yaml
- id: minimal
  category: Test
  question: Test?
  description: Test
  severity: warning
  checker: generic
  enabled: true
```

### Complete Example File

```yaml
# Power-Steering Considerations Configuration
# See HOW_TO_CUSTOMIZE_POWER_STEERING.md for details

# Session Completion
- id: todos_complete
  category: Session Completion & Progress
  question: Were all TODO items completed?
  description: Verifies all TodoWrite items are marked as completed
  severity: blocker
  checker: _check_todos_complete
  enabled: true

# Add more considerations...

# CUSTOM CONSIDERATIONS
- id: custom_team_check
  category: Team Process
  question: Was team process followed?
  description: Team-specific requirement
  severity: warning
  checker: generic
  enabled: true
```

### Validation Checklist

Before saving your YAML file, verify:

- ✅ Valid YAML syntax (no parse errors)
- ✅ All required fields present
- ✅ Unique IDs for all considerations
- ✅ Severity is "blocker" or "warning"
- ✅ Enabled is boolean (true/false)
- ✅ Checker is valid method or "generic"
- ✅ Proper indentation (2 spaces per level)

## Best Practices

### Do's

✅ **Start conservative**: Begin with warnings, upgrade to blockers after testing
✅ **Test incrementally**: Add one consideration at a time
✅ **Use generic for simple checks**: Don't over-engineer
✅ **Document custom considerations**: Add comments explaining why
✅ **Review periodically**: Remove considerations that aren't useful
✅ **Share with team**: Keep team's YAML in version control

### Don'ts

❌ **Don't block too aggressively**: Too many blockers frustrate users
❌ **Don't skip testing**: Always test new considerations
❌ **Don't forget to enable**: `enabled: false` means it won't run
❌ **Don't ignore false positives**: Tune or disable problematic checks
❌ **Don't use tabs**: YAML requires spaces for indentation
❌ **Don't duplicate IDs**: Each consideration needs unique ID

## Getting Help

### Check Logs

Power-steering logs are in:

```
.claude/runtime/power-steering/power_steering.log
```

Look for:

- YAML loading messages
- Validation errors
- Checker execution details

### Enable Debug Logging

(Future enhancement - not yet implemented)

### Disable Power-Steering

Power-steering can be disabled using three control mechanisms (in priority order):

```bash
# Method 1: Runtime disable (highest priority)
# Creates semaphore file to disable power-steering immediately
mkdir -p .claude/runtime/power-steering && touch .claude/runtime/power-steering/.disabled

# Method 2: Session disable (medium priority)
# Affects sessions started after setting this variable
export AMPLIHACK_SKIP_POWER_STEERING=1

# Method 3: Startup disable (lowest priority)
# Sets default behavior at startup - config file should be JSON
echo '{"enabled": false}' > .claude/tools/amplihack/.power_steering_config
```

**To re-enable power-steering:**

```bash
# Remove the semaphore file
rm .claude/runtime/power-steering/.disabled

# Or unset the environment variable
unset AMPLIHACK_SKIP_POWER_STEERING
```

### Report Issues

If you find bugs in specific checkers or need help:

1. Check existing documentation
2. Review logs for error messages
3. Create minimal reproduction case
4. Report issue with YAML configuration and transcript excerpt

## Advanced Topics

### Creating Custom Specific Checkers

For complex requirements, you may want to implement a custom specific checker.

**Requirements:**

- Python programming knowledge
- Understanding of transcript structure
- Ability to modify `power_steering_checker.py`

**Steps:**

1. Add method to `PowerSteeringChecker` class
2. Method signature: `def _check_my_thing(self, transcript: List[Dict], session_id: str) -> bool`
3. Return `True` if satisfied, `False` if failed
4. Use fail-open error handling (catch exceptions, return True)
5. Reference method in YAML: `checker: _check_my_thing`

**Example:**

```python
def _check_custom_requirement(self, transcript: List[Dict], session_id: str) -> bool:
    """Check custom team requirement.

    Returns:
        True if requirement met, False otherwise
    """
    try:
        # Your custom logic here
        requirement_met = False

        for msg in transcript:
            if msg.get("type") == "user":
                content = str(msg.get("message", {}).get("content", ""))
                if "custom keyword" in content.lower():
                    requirement_met = True
                    break

        return requirement_met
    except Exception:
        # Fail-open: return True on any error
        return True
```

### Performance Considerations

- **YAML loading**: Happens once at initialization (< 50ms)
- **Consideration analysis**: All checkers run sequentially
- **Target**: < 5 seconds total for all 21 checkers
- **Optimization**: Disable unused checkers to reduce overhead

### Integration with CI/CD

You can version control `considerations.yaml` for consistency:

```bash
# Add to git
git add .claude/tools/amplihack/considerations.yaml
git commit -m "Add team power-steering configuration"

# Share with team
git push origin main
```

Team members will automatically use the shared configuration.

## Appendix: Complete Default Configuration

The full default `considerations.yaml` with all 21 considerations is located at:

```
.claude/tools/amplihack/considerations.yaml
```

To restore defaults:

```bash
# Backup your customizations
cp .claude/tools/amplihack/considerations.yaml considerations.yaml.backup

# Restore from source
# (Re-copy from original file or reinstall)
```

---

**Version:** Phase 2 (v2.0)
**Last Updated:** 2025
**Author:** Power-Steering Mode Team
