# Analyze Command

## Input Validation

@.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/analyze <PATH>`

## Purpose

Comprehensive code analysis and philosophy compliance review.

## Process

1. **Read Philosophy**
   - Review `.claude/context/PHILOSOPHY.md`
   - Check `.claude/context/PATTERNS.md`
   - Understand project principles

2. **Analyze Code**
   - Read specified files/directories
   - Follow import chains
   - Map dependencies
   - Assess architecture

3. **Philosophy Check**
   - Simplicity assessment
   - Modularity verification
   - Zero-BS compliance
   - Pattern alignment

4. **Generate Report**

## Report Format

### Executive Summary

- Overall compliance score
- Key strengths
- Critical issues

### Detailed Analysis

- **Simplicity**: Score and findings
- **Modularity**: Brick boundaries assessment
- **Patterns**: Alignment with known patterns
- **Improvements**: Specific recommendations

### Action Items

1. High priority fixes
2. Refactoring opportunities
3. Pattern applications

## Review Criteria

### Good Signs

- Clear module boundaries
- Simple implementations
- Working code (no stubs)
- Self-contained modules
- Good documentation

### Red Flags

- Unnecessary complexity
- Leaky abstractions
- Stub code/TODOs
- Tight coupling
- Missing tests

## Example Output

```markdown
## Analysis Report for /src/module

**Philosophy Compliance**: 7/10

### Strengths

- Clear module boundaries
- Simple error handling

### Issues

- Over-engineered cache layer
- Unnecessary abstractions in utils

### Recommendations

1. Simplify cache to use dict
2. Inline single-use utilities
3. Add contract documentation
```

Remember: Analysis guides improvement, not criticism.
