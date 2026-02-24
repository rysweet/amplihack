# Silent Degradation Audit

Multi-wave audit system for detecting code that fails silently in production.

## Quick Start

```bash
# Audit your codebase
/silent-degradation-audit ./src

# Review findings
cat .silent-degradation-report.md
cat .silent-degradation-findings.json
```

## What It Detects

6 categories of silent degradation:

1. **Dependency Failures**: Import errors, missing modules, API fallbacks
2. **Config Errors**: Missing env vars, bad defaults, silent config failures
3. **Background Work**: Async task failures, queue processing errors
4. **Test Effectiveness**: Happy path tests that miss error cases
5. **Operator Visibility**: Missing logs, metrics, alerts
6. **Functional Stubs**: Empty implementations, ignored parameters

## How It Works

**Multi-Wave Progressive Audit:**

- Wave 1: Finds obvious issues (40-50% of total)
- Wave 2-3: Deeper analysis (30-40%)
- Wave 4+: Edge cases (10-20%)
- Stops when < 10 new findings or < 5% of Wave 1

**Multi-Agent Validation:**

- 3 agents review each finding (Security, Architect, Builder)
- 2/3 consensus required to validate
- Prevents false positives

## Output

**Report** (`.silent-degradation-report.md`):

- Summary statistics
- Convergence progress plot
- Findings by category and severity

**Findings** (`.silent-degradation-findings.json`):

- Detailed findings with location, description, impact
- Validation results and votes
- Fix recommendations

## Configuration

Create `.silent-degradation-config.json`:

```json
{
  "convergence": {
    "absolute_threshold": 10,
    "relative_threshold": 0.05
  },
  "max_waves": 6
}
```

## Exclusions

Add to `.silent-degradation-exclusions.json`:

```json
[
  {
    "pattern": "*.test.*",
    "reason": "Test files",
    "category": "*"
  }
]
```

## Integration Modes

**Standalone:**

```bash
/silent-degradation-audit path/to/code
```

**Sub-loop in quality-audit-workflow:**

```
quality-audit-workflow → Phase 2 → silent-degradation-audit
```

## Supported Languages

Python, JavaScript, TypeScript, Rust, Go, Java, C#, Ruby, PHP

## Battle-Tested

Used on CyberGym codebase, found ~250 bugs across all 6 categories.

## Documentation

- `SKILL.md` - Complete documentation
- `reference.md` - Technical reference
- `examples.md` - Usage examples
- `patterns.md` - Language-specific patterns
- `category_agents/` - Category agent specs
- `validation_panel/` - Validation panel docs

## Requirements

- Claude Code with agent support
- Recipe Runner enabled
- Python 3.8+ (for utility tools)

## Example Output

```
Wave 1: ██████████████████████████████████████████████████ 120
Wave 2: ███████████████████████████ 65 (54.2% of Wave 1)
Wave 3: ████████ 18 (15.0% of Wave 1)
Wave 4: ██ 5 (4.2% of Wave 1)

Status: ✓ CONVERGED
Reason: Relative threshold met: 4.2% < 5.0%

Findings:
- dependency-failures: 42 (High: 15, Medium: 20, Low: 7)
- config-errors: 28 (High: 8, Medium: 12, Low: 8)
- background-work: 19 (High: 6, Medium: 9, Low: 4)
- test-effectiveness: 23 (High: 2, Medium: 15, Low: 6)
- operator-visibility: 18 (High: 9, Medium: 7, Low: 2)
- functional-stubs: 7 (High: 1, Medium: 4, Low: 2)

Total: 137 findings validated by panel
```

## License

Part of the amplihack agentic coding framework
