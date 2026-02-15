---
name: Duplicate Code Detector
description: Identifies duplicate code patterns across the codebase and suggests refactoring opportunities
on:
  workflow_dispatch:
  schedule:
    - cron: "0 0 * * 0" # Weekly on Sunday at midnight UTC
permissions:
  contents: read
  issues: write
  pull-requests: read
engine: codex
tools:
  bash: true
safe-outputs:
  create-issue:
    expires: 2d
    title-prefix: "[duplicate-code] "
    labels: [code-quality, automated-analysis]
    assignees: []
    group: false
    max: 3
timeout-minutes: 20
strict: true
---

# Duplicate Code Detection

Analyze code to identify duplicated patterns using pattern matching and semantic analysis. Report significant findings that require refactoring.

## Task

Detect and report code duplication by:

1. **Analyzing Recent Commits**: Review changes in the latest commits
2. **Detecting Duplicated Code**: Identify similar or duplicated code patterns using bash tools and pattern matching
3. **Reporting Findings**: Create a detailed issue if significant duplication is detected (threshold: >10 lines or 3+ similar patterns)

## Context

- **Repository**: ${{ github.repository }}
- **Ref**: ${{ github.ref }}
- **Triggered by**: @${{ github.actor }}

## Analysis Workflow

### 1. Project Setup

Prepare the analysis environment:

- Set working directory to `${{ github.workspace }}`
- Identify primary languages: **Python (.py)** and **Rust (.rs)**
- Verify bash tools are available for pattern matching

### 2. Changed Files Analysis

Identify and analyze modified files:

- Determine files changed in recent commits (last 7 days for scheduled runs, or specified commit range)
- **ONLY analyze .py and .rs files** - exclude all other file types
- **Exclude test files** from analysis (files matching patterns: `*_test.py`, `test_*.py`, `*_test.rs`, or located in directories named `test`, `tests`, `__tests__`, or `spec`)
- **Exclude workflow files** from analysis (files under `.github/workflows/*`)
- **Exclude build artifacts** (files under `target/`, `build/`, `dist/`, `__pycache__/`)
- Use bash commands to list and examine file contents

### 3. Duplicate Detection

Apply pattern matching to find duplicates:

**Function-Level Analysis**:

```bash
# Find Python function definitions
grep -r "^def " --include="*.py" --exclude-dir={test,tests,__tests__,__pycache__,target,build,dist} .

# Find Rust function definitions
grep -r "^fn " --include="*.rs" --exclude-dir={test,tests,target,build,dist} .
```

**Pattern Search**:

- Search for similar function signatures across files
- Identify repeated code blocks (>10 lines)
- Find similar import/use patterns
- Detect repeated error handling patterns
- Look for similar class/struct definitions

**Structural Analysis**:

```bash
# Find files with similar names
find . -type f \( -name "*.py" -o -name "*.rs" \) -not -path "*/test/*" -not -path "*/tests/*" -not -path "*/target/*"

# Count lines of code in functions
awk '/^def |^fn / { start=NR } /^$/ && start { print FILENAME":"start"-"NR":"(NR-start); start=0 }' file.{py,rs}
```

### 4. Duplication Evaluation

Assess findings to identify true code duplication:

**Duplication Types**:

- **Exact Duplication**: Identical code blocks in multiple locations
- **Structural Duplication**: Same logic with minor variations (different variable names, etc.)
- **Functional Duplication**: Different implementations of the same functionality
- **Copy-Paste Programming**: Similar code blocks that could be extracted into shared utilities

**Assessment Criteria**:

- **Severity**: Amount of duplicated code (lines of code, number of occurrences)
- **Impact**: Where duplication occurs (critical paths, frequently called code)
- **Maintainability**: How duplication affects code maintainability
- **Refactoring Opportunity**: Whether duplication can be easily refactored

**Bash Analysis Tools**:

```bash
# Compare similar functions
diff -u file1.py file2.py

# Find repeated patterns
grep -r "pattern" --include="*.py" --include="*.rs" .

# Count occurrences
grep -c "pattern" file.py
```

### 5. Issue Reporting

Create separate issues for each distinct duplication pattern found (maximum 3 patterns per run). Each pattern should get its own issue to enable focused remediation.

**When to Create Issues**:

- Only create issues if significant duplication is found (threshold: >10 lines of duplicated code OR 3+ instances of similar patterns)
- **Create one issue per distinct pattern** - do NOT bundle multiple patterns in a single issue
- Limit to the top 3 most significant patterns if more are found
- Use the `create_issue` tool from safe-outputs **once for each pattern**

**Issue Contents for Each Pattern**:

- **Executive Summary**: Brief description of this specific duplication pattern
- **Duplication Details**: Specific locations and code blocks for this pattern only
- **Severity Assessment**: Impact and maintainability concerns for this pattern
- **Refactoring Recommendations**: Suggested approaches to eliminate this pattern
- **Code Examples**: Concrete examples with file paths and line numbers for this pattern

## Detection Scope

### Report These Issues

- Identical or nearly identical functions in different files
- Repeated code blocks that could be extracted to utilities
- Similar classes/structs or modules with overlapping functionality
- Copy-pasted code with minor modifications
- Duplicated business logic across components
- Repeated error handling patterns
- Similar data structure definitions

### Skip These Patterns

- Standard boilerplate code (imports, use statements, etc.)
- Test setup/teardown code (acceptable duplication in tests)
- **All test files** (files matching: `*_test.py`, `test_*.py`, `*_test.rs`, or in `test/`, `tests/`, `__tests__/` directories)
- **All workflow files** (files under `.github/workflows/*`)
- **Build artifacts** (files under `target/`, `build/`, `dist/`, `__pycache__/`)
- Configuration files with similar structure
- Language-specific patterns (constructors, trait implementations)
- Small code snippets (<5 lines) unless highly repetitive

### Analysis Depth

- **File Type Restriction**: ONLY analyze .py and .rs files - ignore all other file types
- **Primary Focus**: All .py and .rs files changed in the analysis window (excluding test files and workflow files)
- **Secondary Analysis**: Check for duplication with existing .py and .rs codebase (excluding test files and workflow files)
- **Cross-Reference**: Look for patterns across Python and Rust files in the repository
- **Historical Context**: Consider if duplication is new or existing

## Issue Template

For each distinct duplication pattern found, create a separate issue using this structure:

````markdown
# 🔍 Duplicate Code Detected: [Pattern Name]

_Analysis of ${{ github.ref }}_

## Summary

[Brief overview of this specific duplication pattern]

## Duplication Details

### Pattern: [Description]

- **Severity**: High/Medium/Low
- **Language**: Python/Rust
- **Occurrences**: [Number of instances]
- **Locations**:
  - `path/to/file1.ext` (lines X-Y)
  - `path/to/file2.ext` (lines A-B)
- **Code Sample**:
  ```[language]
  [Example of duplicated code]
  ```
````

## Impact Analysis

- **Maintainability**: [How this affects code maintenance]
- **Bug Risk**: [Potential for inconsistent fixes]
- **Code Bloat**: [Impact on codebase size]

## Refactoring Recommendations

1. **[Recommendation 1]**
   - Extract common functionality to: `suggested/path/utility.ext`
   - Estimated effort: [hours/complexity]
   - Benefits: [specific improvements]

2. **[Recommendation 2]**
   [... additional recommendations ...]

## Implementation Checklist

- [ ] Review duplication findings
- [ ] Prioritize refactoring tasks
- [ ] Create refactoring plan
- [ ] Implement changes
- [ ] Update tests
- [ ] Verify no functionality broken

## Analysis Metadata

- **Analyzed Files**: [count]
- **Detection Method**: Bash pattern matching and semantic analysis
- **Ref**: ${{ github.ref }}
- **Analysis Date**: [timestamp]

````

## Operational Guidelines

### Security
- Never execute untrusted code or commands
- Only use safe bash commands for read-only analysis
- Do not modify files during analysis

### Efficiency
- Focus on recently changed files first
- Use pattern matching for meaningful duplication, not superficial matches
- Stay within timeout limits (balance thoroughness with execution time)
- Leverage bash tools efficiently (grep, awk, diff, find)

### Accuracy
- Verify findings before reporting
- Distinguish between acceptable patterns and true duplication
- Consider language-specific idioms and best practices
- Provide specific, actionable recommendations

### Issue Creation
- Create **one issue per distinct duplication pattern** - do NOT bundle multiple patterns in a single issue
- Limit to the top 3 most significant patterns if more are found
- Only create issues if significant duplication is found
- Include sufficient detail for engineers to understand and act on findings
- Provide concrete examples with file paths and line numbers
- Suggest practical refactoring approaches
- Use descriptive titles that clearly identify the specific pattern (e.g., "Duplicate Code: Error Handling Pattern in Parser Module")

## Bash Tool Usage Patterns

### File Discovery
```bash
# Find Python files (excluding tests and build artifacts)
find . -type f -name "*.py" \
  -not -path "*/test/*" \
  -not -path "*/tests/*" \
  -not -path "*/__pycache__/*" \
  -not -path "*/build/*" \
  -not -path "*/dist/*"

# Find Rust files (excluding tests and target)
find . -type f -name "*.rs" \
  -not -path "*/test/*" \
  -not -path "*/tests/*" \
  -not -path "*/target/*"
````

### Pattern Matching

```bash
# Find function definitions
grep -rn "^def \|^fn " --include="*.py" --include="*.rs" \
  --exclude-dir={test,tests,__pycache__,target,build,dist} .

# Find similar patterns
grep -rn "pattern_to_match" --include="*.py" --include="*.rs" .

# Count pattern occurrences
grep -rc "pattern" . --include="*.py" --include="*.rs" | grep -v ":0$"
```

### Code Comparison

```bash
# Show differences between similar files
diff -u file1.py file2.py

# Find files with similar content
for f in *.py; do wc -l "$f"; done | sort -n

# Extract function bodies for comparison
awk '/^def |^fn /,/^$/' file.py
```

**Objective**: Improve code quality by identifying and reporting meaningful code duplication that impacts maintainability. Focus on actionable findings that enable refactoring in Python and Rust codebases.
