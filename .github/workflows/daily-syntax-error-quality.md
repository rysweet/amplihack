---
name: Daily Syntax Error Quality Check
description: Tests compiler error message quality by introducing syntax errors in workflows, evaluating error clarity, and suggesting improvements for amplihack4
on:
  schedule: daily
  workflow_dispatch:
permissions:
  contents: read
  issues: read
  pull-requests: read
tracker-id: daily-syntax-error-quality
engine: copilot
tools:
  github:
    lockdown: false
    toolsets:
      - default
  bash:
    - "find .github/workflows -name '*.md' -type f ! -name 'daily-*.md' ! -name '*-test.md'"
    - "./gh-aw compile"
    - "cat .github/workflows/*.md"
    - "head -n * .github/workflows/*.md"
    - "cp .github/workflows/*.md /tmp/*.md"
    - "cat /tmp/*.md"
safe-outputs:
  create-issue:
    expires: 3d
    title-prefix: "[syntax-error-quality] "
    labels: [dx, error-messages, automated-analysis]
    max: 1
    close-older-issues: true
timeout-minutes: 20
strict: true
steps:
  - name: Set up Go
    uses: actions/setup-go@v5
    with:
      go-version-file: go.mod
      cache: true
  - name: Build gh-aw
    run: |
      make build
  - name: Verify gh-aw installation
    run: |
      ./gh-aw --version
      echo "gh-aw binary is ready at ./gh-aw"
imports:
  - shared/mood.md
  - shared/reporting.md
---

# Daily Syntax Error Quality Check Workflow

## Purpose

This workflow is a **developer experience specialist** that systematically evaluates the quality of compiler error messages in amplihack4's gh-aw workflows. By introducing controlled syntax errors and assessing how well error messages guide developers toward solutions, we continuously improve the developer experience.

## Schedule

Runs **daily** at a scheduled time, with manual trigger support via `workflow_dispatch`.

## Methodology

### Phase 1: Workflow Selection

Select 3 diverse test workflows for quality assessment.

**Selection Criteria:**

- Exclude daily workflows (daily-\*.md)
- Exclude test workflows (\*-test.md)
- Prioritize diversity in complexity levels
- Prefer workflows with different engine configurations

### Phase 2: Error Injection

Introduce **one error type per workflow** across three categories.

### Phase 3: Compilation & Error Capture

Compile modified workflows and capture error outputs.

### Phase 4: Error Message Evaluation

Score each error message across **5 dimensions** (100 points total):

- Clarity (25 points)
- Actionability (25 points)
- Context (20 points)
- Examples (15 points)
- Consistency (15 points)

### Phase 5: Generate Evaluation Report

Create structured JSON reports and store in repo-memory.

### Phase 6: Quality Assessment & Issue Creation

**Quality Thresholds:**

- **85-100**: Exemplary
- **70-84**: Good
- **55-69**: Acceptable
- **40-54**: Poor
- **0-39**: Critical

**Issue Creation Triggers:**

- Average score below 70
- Individual test below 55
- Critical pattern issues

## Integration with repo-memory

Store historical data for trend analysis in `.claude/memory/syntax-error-quality/`.

## Success Metrics

- Average score consistently above 70
- No individual tests scoring below 55
- Trend showing improvement over time
- Reduced issue creation frequency
