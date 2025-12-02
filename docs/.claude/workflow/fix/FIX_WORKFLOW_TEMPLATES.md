# Fix Workflow Templates

This file contains pre-built templates for the most common fix patterns identified in claude-trace analysis. These templates provide quick, standardized approaches to frequent fix scenarios.

## Template Usage

Each template follows the format:

- **Problem Pattern**: How to identify when this template applies
- **Quick Assessment**: Rapid diagnosis steps
- **Solution Steps**: Standardized fix process
- **Validation**: How to verify the fix
- **Integration**: Connection points with main workflow

## Template Categories

### Category 1: Code Quality Fixes (25% of fixes)

- Linting violations
- Type errors
- Formatting issues
- Style guide compliance

### Category 2: CI/CD Problems (20% of fixes)

- Pipeline configuration
- Dependency conflicts
- Build environment issues
- Deployment failures

### Category 3: Test Failures (18% of fixes)

- Assertion errors
- Mock setup issues
- Test data problems
- Coverage issues

### Category 4: Import Errors (15% of fixes)

- Missing imports
- Circular dependencies
- Path resolution issues
- Module not found

### Category 5: Configuration Issues (12% of fixes)

- Environment variables
- Config file syntax
- Missing settings
- Version conflicts

### Category 6: Logic Errors (10% of fixes)

- Algorithm bugs
- Edge case handling
- State management
- Business logic

## Available Templates

1. [Import Fix Template](./import-fix-template.md)
2. [CI Fix Template](./ci-fix-template.md)
3. [Test Fix Template](./test-fix-template.md)
4. [Config Fix Template](./config-fix-template.md)
5. [Code Quality Fix Template](./code-quality-fix-template.md)
6. [Logic Fix Template](./logic-fix-template.md)

## Template Selection Guide

### Quick Decision Tree

```
Is it a clear error message?
├─ Yes → Use specific template (Import, Config, etc.)
└─ No → Start with diagnostic approach

Is it affecting CI/build?
├─ Yes → Use CI Fix Template
└─ No → Continue assessment

Are tests failing?
├─ Yes → Use Test Fix Template
└─ No → Continue assessment

Is it code quality/linting?
├─ Yes → Use Code Quality Fix Template
└─ No → Use Logic Fix Template or full workflow
```

## Integration with Fix Agent

These templates are designed to work seamlessly with the fix agent modes:

- **QUICK Mode**: Uses templates 1-5 for rapid resolution
- **DIAGNOSTIC Mode**: Uses diagnostic portions of all templates
- **COMPREHENSIVE Mode**: Escalates to full workflow when templates insufficient

## Customization

To add new templates:

1. Identify recurring fix pattern (3+ occurrences)
2. Create template file in this directory
3. Follow template format
4. Add to this index
5. Update fix agent pattern recognition

## Success Metrics

- **Template Hit Rate**: % of fixes that use templates
- **Resolution Time**: Average time with vs without templates
- **Success Rate**: % of successful fixes using templates
- **User Adoption**: Frequency of template usage

## Template Evolution

Templates evolve based on:

- Usage patterns from claude-trace
- Success/failure rates
- User feedback
- New fix patterns discovered

Remember: Templates accelerate common fixes but don't replace thoughtful problem-solving for complex issues.
