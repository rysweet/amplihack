# Fix Command

## Input Validation

@.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/fix [PATTERN] [SCOPE]`

## Purpose

Intelligent fix workflow optimization that automatically selects the best fix approach based on error patterns, scope, and context. Integrates with UltraThink for complex issues and provides rapid resolution for common patterns.

## Parameters

- **PATTERN** (optional): Fix pattern type or error description
  - `import` - Import and dependency issues
  - `ci` - CI/CD pipeline failures
  - `test` - Test failures and assertion errors
  - `config` - Configuration and environment issues
  - `quality` - Code quality, linting, formatting
  - `logic` - Algorithm bugs and business logic
  - `auto` - Automatic pattern detection (default)

- **SCOPE** (optional): Fix scope and complexity
  - `quick` - Rapid fixes (< 5 minutes)
  - `diagnostic` - Root cause analysis
  - `comprehensive` - Full workflow integration
  - `auto` - Automatic scope detection (default)

## Process

### Step 1: Context Analysis

```bash
# Automatic context detection
- Check current error state (CI logs, test output, linting)
- Analyze recent commit history for regression patterns
- Scan for common error indicators in codebase
- Determine fix pattern and scope automatically
```

### Step 2: Pattern Recognition

**Automatic Pattern Detection**:

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

### Step 3: Fix Mode Selection

**Intelligent Mode Selection**:

```markdown
## QUICK Mode (Rapid Fixes)

**Auto-triggers when**:

- Single file/function affected
- Clear error message with obvious solution
- Standard linting/formatting issues
- Known pattern with template available

**Process**:

1. Apply relevant fix template
2. Validate fix works
3. Run minimal tests
4. Ready for commit

## DIAGNOSTIC Mode (Root Cause Analysis)

**Auto-triggers when**:

- Unclear error messages
- Multiple related failures
- Intermittent/flaky issues
- No obvious template match

**Process**:

1. Use fix-agent for investigation
2. Apply systematic debugging
3. Document findings
4. Implement targeted solution

## COMPREHENSIVE Mode (Full Workflow)

**Auto-triggers when**:

- Multiple components affected
- Architecture changes needed
- Breaking changes required
- Security vulnerabilities

**Process**:

1. Integrate with UltraThink workflow
2. Follow full DEFAULT_WORKFLOW.md process
3. Multi-agent coordination
4. Complete documentation and testing
```

### Step 4: Fix Execution

**Template-Based Execution**:

```bash
# Quick template application
if fix_pattern in ["import", "config", "quality"]:
    apply_fix_template(pattern=fix_pattern, context=error_context)
    validate_fix()

# Agent-based execution
elif scope == "diagnostic":
    delegate_to_fix_agent(mode="DIAGNOSTIC", context=full_context)

# Workflow integration
elif scope == "comprehensive":
    integrate_with_ultrathink(task=f"Fix {fix_pattern} issue", context=error_context)
```

## Command Examples

### Basic Usage

```bash
# Automatic detection and fixing
/fix

# Specific pattern
/fix import
/fix ci
/fix test

# Specific scope
/fix quick
/fix diagnostic
/fix comprehensive

# Combined
/fix import quick
/fix logic diagnostic
/fix ci comprehensive
```

### Context-Aware Examples

```bash
# When CI is failing
/fix ci
→ Automatically detects CI failure type
→ Applies ci-fix-template
→ Monitors CI re-run

# When tests are failing
/fix test
→ Analyzes test failure output
→ Applies test-fix-template
→ Validates test passes

# When imports are broken
/fix import
→ Identifies missing/incorrect imports
→ Applies import-fix-template
→ Verifies import resolution

# Complex logic issue
/fix logic diagnostic
→ Uses fix-agent DIAGNOSTIC mode
→ Systematic debugging approach
→ Documents root cause analysis
```

## Integration Points

### With Fix Agent

```markdown
The fix command automatically delegates to the fix-agent based on complexity:

**QUICK fixes** → Direct template application
**DIAGNOSTIC fixes** → fix-agent DIAGNOSTIC mode
**COMPREHENSIVE fixes** → fix-agent COMPREHENSIVE mode + UltraThink
```

### With UltraThink Workflow

```markdown
For comprehensive fixes, automatically integrates with UltraThink:

1. /fix comprehensive [pattern]
2. → Calls /ultrathink with fix task
3. → UltraThink reads DEFAULT_WORKFLOW.md
4. → Follows full 14-step process
5. → Uses fix-agent and templates as needed
```

### With Existing Agents

```markdown
**Pre-commit failures** → Integrates with pre-commit-diagnostic agent
**CI failures** → Integrates with ci-diagnostic-workflow agent
**Complex architecture** → Escalates to architect agent
**Security issues** → Involves security agent
```

## Workflow Integration

### Standard Development Workflow

```bash
# During development when issues arise:
/fix                    # Quick automatic fix
git add . && git commit # If fix successful

# During CI failures:
/fix ci                 # Target CI-specific issues
                        # Auto-monitors CI status

# During code review:
/fix quality           # Address review feedback
                       # Focus on code quality
```

### Emergency Fix Workflow

```bash
# Production issue detected:
/fix comprehensive     # Full workflow approach
                       # Includes rollback planning
                       # Complete testing required

# Critical security fix:
/fix security comprehensive
                       # Escalates to security agent
                       # Full vulnerability assessment
```

## Success Metrics

### Performance Tracking

- **Fix Success Rate**: % of issues resolved completely
- **Time to Resolution**: Average fix implementation time
- **Pattern Recognition Accuracy**: Correct pattern identification rate
- **Mode Selection Accuracy**: Optimal mode selection rate

### Usage Analytics

- **Most Common Patterns**: Track frequency of fix types
- **Template Effectiveness**: Success rate by template
- **Escalation Patterns**: When quick fixes escalate
- **User Satisfaction**: Fix quality and completeness

## Error Handling

### Graceful Degradation

```bash
# If automatic detection fails:
/fix → Prompts for manual pattern selection

# If template fails:
/fix pattern → Escalates to diagnostic mode

# If diagnostic fails:
/fix diagnostic → Escalates to comprehensive + UltraThink
```

### Fallback Strategies

```bash
# No clear pattern detected
→ Use analyzer agent for investigation
→ Present options to user

# Multiple patterns detected
→ Prioritize by impact and complexity
→ Show disambiguation options

# Fix attempt fails
→ Rollback changes
→ Escalate to next mode level
```

## Quick Reference

### Most Common Usage Patterns

```bash
/fix                 # Auto-detect and fix (90% of cases)
/fix import          # Import/dependency issues (15% of cases)
/fix ci              # CI/CD problems (20% of cases)
/fix test            # Test failures (18% of cases)
/fix quality         # Code quality issues (25% of cases)
```

### Escalation Path

```bash
/fix quick          # Template-based (< 5 min)
    ↓ (if fails)
/fix diagnostic     # Agent investigation (< 30 min)
    ↓ (if fails)
/fix comprehensive  # Full workflow (> 30 min)
```

## Advanced Features

### Context Learning

```markdown
The fix command learns from usage patterns:

- Tracks successful fix strategies
- Improves pattern recognition over time
- Suggests fixes based on historical success
- Adapts templates based on project specifics
```

### Integration with Claude-Trace

```markdown
When AMPLIHACK_USE_TRACE=1:

- Enhanced error context from trace analysis
- Pattern recognition from historical data
- Success rate tracking and optimization
- Detailed fix attempt logging
```

### Custom Fix Patterns

```markdown
Projects can define custom fix patterns:

1. Add pattern to .claude/workflow/fix/custom/
2. Follow template format
3. Register in fix command configuration
4. Automatically available via /fix custom_pattern
```

## Configuration

### Project-Specific Settings

```json
// .claude/config/fix-command.json
{
  "default_mode": "auto",
  "pattern_priorities": {
    "quality": 1,
    "test": 2,
    "import": 3,
    "ci": 4,
    "config": 5,
    "logic": 6
  },
  "escalation_timeout": 300,
  "enable_learning": true
}
```

### Environment Integration

```bash
# Pre-commit hook integration
export AMPLIHACK_FIX_MODE=quick

# CI environment detection
export CI=true  # Automatically prioritizes CI fixes
```

## Remember

The fix command is designed to be the primary entry point for issue resolution:

- Start with `/fix` for automatic detection
- Use specific patterns when you know the issue type
- Escalate complexity as needed
- Trust the automatic mode selection
- Let the system learn from your usage patterns

The goal is to resolve 80% of common issues in under 5 minutes, while providing clear escalation paths for complex problems.
