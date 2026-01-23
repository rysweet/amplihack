# Dependency Resolver Skill

Automated dependency conflict detection and resolution for local vs CI environment mismatches.

## Problem Solved

This skill addresses a 45-minute debug cycle problem documented in DISCOVERIES.md:

> "Environment mismatches: Local (Python 3.12.10, ruff 0.12.7) vs CI (Python 3.11, ruff 0.13.0) - 20-25 minute investigation overhead"

Existing tools fix problems AFTER they occur. This skill catches them BEFORE push.

## Usage

### Automatic Activation

The skill auto-activates when you mention:

- "dependency conflict"
- "version mismatch"
- "CI failing on linting"
- "works locally but fails in CI"

### Explicit Invocation

```
/amplihack:dependency-resolver
/fix dependency
/check-env
```

### Example Session

```
User: "My code works locally but CI fails on ruff errors"

Claude: [Activates dependency-resolver skill]

## Dependency Resolver Report

### Environment Comparison

| Component | Local | CI | Status |
|-----------|-------|-----|--------|
| Python | 3.12.10 | 3.11 | MISMATCH |
| ruff | 0.12.7 | 0.13.0 | MISMATCH |

### Quick Fix Commands

pip install ruff==0.13.0
pre-commit autoupdate
pre-commit run --all-files
```

## How It Works

1. **Collects local environment** - Python version, installed tools
2. **Reads CI configuration** - .github/workflows/ci.yml, pyproject.toml
3. **Compares versions** - Builds mismatch table
4. **Generates recommendations** - Actionable fixes with commands
5. **Auto-fixes (optional)** - Updates configs when requested

## Integration

Works with existing amplihack tools:

| Tool                       | Integration                                  |
| -------------------------- | -------------------------------------------- |
| **fix-agent**              | Uses Template 1 (import) and Template 4 (CI) |
| **pre-commit-diagnostic**  | Hand-off for hook failures                   |
| **ci-diagnostic-workflow** | Hand-off for post-push issues                |
| **ci_status.py**           | Checks CI status after fixes                 |

## Common Patterns Detected

### Python Version Drift

- Symptoms: Type errors, import issues in CI
- Fix: pyenv or update CI configuration

### Linter Version Drift

- Symptoms: "Works locally, fails in CI"
- Fix: `pre-commit autoupdate` or pin version

### Missing Dependencies

- Symptoms: ModuleNotFoundError in CI
- Fix: `pip install -e ".[dev]"`

## When to Use

**Good times:**

- Before pushing after long development
- After updating local Python or tools
- When onboarding to new project
- "CI is failing but it works locally"

**Not needed:**

- CI already passing
- Environment just synced
- Only editing docs

## Files

```
.claude/skills/dependency-resolver/
    SKILL.md    # Main skill definition (execution instructions)
    README.md   # This file (documentation)
```

## Related

- `~/.amplihack/.claude/context/DISCOVERIES.md` - CI Failure Resolution Process Analysis
- `~/.amplihack/.claude/agents/amplihack/specialized/fix-agent.md` - Fix templates
- `~/.amplihack/.claude/agents/amplihack/specialized/ci-diagnostic-workflow.md` - Post-push CI
- `.github/workflows/ci.yml` - CI configuration source of truth
