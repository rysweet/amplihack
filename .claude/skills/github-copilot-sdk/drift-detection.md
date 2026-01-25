# GitHub Copilot SDK - Drift Detection

## Purpose

This document describes how this skill stays current with the official GitHub Copilot SDK documentation and API changes.

## Source URLs

This skill is based on the following official sources:

| Source           | URL                                                                            | Last Verified |
| ---------------- | ------------------------------------------------------------------------------ | ------------- |
| SDK Repository   | https://github.com/github/copilot-sdk                                          | 2025-01-25    |
| Getting Started  | https://github.com/github/copilot-sdk/blob/main/docs/getting-started.md        | 2025-01-25    |
| Node.js Cookbook | https://github.com/github/copilot-sdk/tree/main/cookbook/nodejs                | 2025-01-25    |
| Python Cookbook  | https://github.com/github/copilot-sdk/tree/main/cookbook/python                | 2025-01-25    |
| Go Cookbook      | https://github.com/github/copilot-sdk/tree/main/cookbook/go                    | 2025-01-25    |
| .NET Cookbook    | https://github.com/github/copilot-sdk/tree/main/cookbook/dotnet                | 2025-01-25    |
| Awesome Copilot  | https://github.com/github/awesome-copilot/blob/main/collections/copilot-sdk.md | 2025-01-25    |

## Drift Detection Process

### Automated Check

Run the drift detection script to check for source changes:

```bash
python .claude/skills/github-copilot-sdk/scripts/check_drift.py
```

**What it checks:**

1. GitHub API for repository commits since last update
2. README.md changes in the SDK repository
3. Cookbook directory changes
4. Getting started guide changes

**Output:**

- `CURRENT`: No changes detected since last update
- `DRIFT DETECTED`: Sources have changed, update needed
- `ERROR`: Could not check sources

### Manual Verification

Periodically verify these key documents:

1. **SDK README.md**: Check for new features, API changes, deprecations
2. **Getting Started Guide**: Verify examples still work
3. **Cookbook Examples**: Confirm patterns are current
4. **Language-specific READMEs**: Check for breaking changes

### Update Schedule

| Frequency      | Action                       |
| -------------- | ---------------------------- |
| Weekly         | Run automated drift check    |
| Monthly        | Manual source verification   |
| On SDK Release | Full skill review and update |

## Update Procedure

When drift is detected:

### 1. Identify Changes

```bash
# Check SDK commits since last update
gh api repos/github/copilot-sdk/commits \
  --jq '.[0:10] | .[] | "\(.sha[0:7]) \(.commit.message | split("\n")[0])"'
```

### 2. Categorize Impact

| Change Type     | Files to Update        | Priority |
| --------------- | ---------------------- | -------- |
| New API method  | reference.md           | High     |
| New example     | examples.md            | Medium   |
| New pattern     | patterns.md            | Medium   |
| Breaking change | All files              | Critical |
| Bug fix         | May not require update | Low      |
| Documentation   | SKILL.md, reference.md | Medium   |

### 3. Update Files

1. **SKILL.md**: Update overview, quick start if affected
2. **reference.md**: Update API documentation
3. **examples.md**: Add/update code examples
4. **patterns.md**: Add new production patterns
5. **README.md**: Update version info
6. **drift-detection.md**: Update "Last Verified" dates

### 4. Validate Updates

Run validation checks:

```bash
# Check YAML frontmatter
python scripts/check_drift.py --validate-yaml

# Count tokens (should be < 2000 for SKILL.md)
python scripts/check_drift.py --count-tokens

# Verify examples compile (basic syntax check)
python scripts/check_drift.py --check-examples
```

### 5. Document Update

Update the SKILL.md frontmatter:

```yaml
last_updated: YYYY-MM-DD
```

Update this file's verification dates.

## Validation Report

The `check_drift.py` script can generate a validation report:

```bash
python scripts/check_drift.py --report
```

**Report Contents:**

- Last source check date
- Files checked and results
- Token counts for each file
- Example syntax validation
- Recommendations

## Breaking Change Protocol

When a breaking SDK change is detected:

1. **IMMEDIATE**: Add deprecation notice to SKILL.md
2. **WITHIN 24H**: Update affected examples
3. **WITHIN 48H**: Update patterns if affected
4. **WITHIN 1 WEEK**: Complete skill update and validation

## Version Tracking

| Skill Version | SDK Version       | Date       |
| ------------- | ----------------- | ---------- |
| 1.0.0         | Technical Preview | 2025-01-25 |

## Self-Validation

This skill includes self-validation mechanisms:

### Token Budget Check

SKILL.md should stay under 2000 tokens:

```bash
python scripts/check_drift.py --count-tokens SKILL.md
```

### Example Syntax Check

Verify code examples are syntactically valid:

```bash
python scripts/check_drift.py --check-examples examples.md
```

### Link Validation

Verify source URLs are accessible:

```bash
python scripts/check_drift.py --check-links
```

## Integration with CI

Add to repository CI pipeline:

```yaml
# .github/workflows/skill-drift-check.yml
name: Skill Drift Check
on:
  schedule:
    - cron: "0 0 * * 0" # Weekly
  workflow_dispatch:

jobs:
  check-drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install requests tiktoken
      - run: python .github/skills/github-copilot-sdk/scripts/check_drift.py --report
```

## Contact

For questions about this skill or drift detection:

- **Repository Issues**: https://github.com/rysweet/amplihack/issues
- **Skill Label**: `skill:github-copilot-sdk`
