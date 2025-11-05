# Workflow Phase Announcement Examples

This document provides comprehensive examples of workflow phase announcements for different task types, demonstrating how to communicate workflow execution transparently.

## Purpose

Phase announcements serve multiple critical functions:

- **Transparency**: Users know which workflow phase is active at any moment
- **Auditability**: Reflection analysis can verify systematic workflow adherence
- **Progress Tracking**: Users understand completion status (Step N of 15)
- **Trust Building**: Demonstrates that UltraThink follows the structured workflow

## Announcement Format

**Standard Format**: 🎯 **STEP [N]: [PHASE NAME]** - [One-sentence purpose]

**Guidelines**:

- Keep announcements concise (< 100 characters)
- Use active, descriptive language
- Place announcement at the start of each workflow step
- Include in todo lists for progress visibility

## Task Type 1: Implementation Tasks

**Scenario**: Adding a new feature like authentication, API endpoint, or UI component

### Example Announcements

```
🎯 **STEP 1: REQUIREMENTS CLARIFICATION** - Defining authentication feature requirements and constraints
🎯 **STEP 2: GITHUB ISSUE CREATION** - Creating tracking issue for user authentication
🎯 **STEP 3: WORKTREE & BRANCH SETUP** - Creating isolated environment for auth feature
🎯 **STEP 4: RESEARCH & DESIGN** - Architecting authentication module with security review
🎯 **STEP 5: IMPLEMENTATION** - Building JWT-based authentication system
🎯 **STEP 6: REFACTOR & SIMPLIFY** - Simplifying auth code while preserving security
🎯 **STEP 7: TESTS & PRE-COMMIT** - Validating authentication tests and code quality
🎯 **STEP 8: LOCAL TESTING** - Testing auth flow with real login scenarios
🎯 **STEP 9: COMMIT & PUSH** - Saving authentication implementation to remote
🎯 **STEP 10: PULL REQUEST CREATION** - Opening PR with security testing documentation
🎯 **STEP 11: PR REVIEW** - Security and code quality review of authentication
🎯 **STEP 12: REVIEW FEEDBACK** - Addressing security concerns from review
🎯 **STEP 13: PHILOSOPHY COMPLIANCE** - Verifying auth module follows simplicity principles
🎯 **STEP 14: PR MERGEABLE CHECK** - Ensuring all security checks pass
🎯 **STEP 15: FINAL CLEANUP** - Removing temporary auth test fixtures
```

## Task Type 2: Investigation Tasks

**Scenario**: Understanding how a system works, exploring codebase, or researching a problem

### Workflow Adaptation Announcement

```
🗺️ **WORKFLOW ADAPTATION** - Adapting development workflow for investigation task:
- STEP 1: Requirements Clarification → Investigation Scope Definition
- STEP 2: GitHub Issue Creation → (Skipped - exploratory task)
- STEP 3: Worktree Setup → (Skipped - read-only investigation)
- STEP 4: Research & Design → Multi-Agent Exploration Strategy
- STEP 5: Implementation → System Verification & Testing
- STEP 6-14: (Adapted as needed for investigation)
- STEP 15: Final Cleanup → Synthesis & Documentation

Following DEFAULT_WORKFLOW.md structure with investigation-appropriate adaptations.
```

### Example Announcements

```
🎯 **STEP 1: SCOPE DEFINITION** - Defining investigation objectives and success criteria
🎯 **STEP 4: EXPLORATION STRATEGY** - Deploying parallel agents to investigate codebase
🎯 **STEP 5: VERIFICATION & TESTING** - Testing system behavior through experimentation
🎯 **STEP 15: SYNTHESIS & DOCUMENTATION** - Compiling findings into comprehensive report
```

## Task Type 3: Debugging Tasks

**Scenario**: Fixing bugs, resolving test failures, or addressing production issues

### Example Announcements

```
🎯 **STEP 1: PROBLEM ANALYSIS** - Understanding test failure symptoms and scope
🎯 **STEP 2: GITHUB ISSUE CREATION** - Creating bug report with reproduction steps
🎯 **STEP 3: WORKTREE & BRANCH SETUP** - Creating isolated environment for bug fix
🎯 **STEP 4: ROOT CAUSE INVESTIGATION** - Deploying analyzer agents to identify bug source
🎯 **STEP 5: FIX IMPLEMENTATION** - Applying fix with builder agent
🎯 **STEP 6: FIX VERIFICATION** - Simplifying fix while ensuring correctness
🎯 **STEP 7: TESTS & PRE-COMMIT** - Confirming all tests pass with fix
🎯 **STEP 8: LOCAL TESTING** - Testing fix against original reproduction case
🎯 **STEP 9: COMMIT & PUSH** - Saving bug fix with detailed explanation
🎯 **STEP 10: PULL REQUEST CREATION** - Opening PR with before/after test results
🎯 **STEP 11: PR REVIEW** - Reviewing fix for side effects and edge cases
🎯 **STEP 12: REVIEW FEEDBACK** - Adding suggested test coverage
🎯 **STEP 13: PHILOSOPHY COMPLIANCE** - Ensuring fix follows simplicity principles
🎯 **STEP 14: PR MERGEABLE CHECK** - Verifying all regression tests pass
🎯 **STEP 15: FINAL CLEANUP** - Removing debug code and temporary logging
```

## Task Type 4: Refactoring Tasks

**Scenario**: Code cleanup, architecture improvements, or technical debt reduction

### Example Announcements

```
🎯 **STEP 1: REQUIREMENTS CLARIFICATION** - Defining refactoring scope and non-regression goals
🎯 **STEP 2: GITHUB ISSUE CREATION** - Creating refactoring proposal with benefits
🎯 **STEP 3: WORKTREE & BRANCH SETUP** - Creating isolated environment for refactoring
🎯 **STEP 4: RESEARCH & DESIGN** - Analyzing current code and designing improvements
🎯 **STEP 5: IMPLEMENTATION** - Refactoring module structure incrementally
🎯 **STEP 6: REFACTOR & SIMPLIFY** - Applying ruthless simplification principles
🎯 **STEP 7: TESTS & PRE-COMMIT** - Ensuring all existing tests still pass
🎯 **STEP 8: LOCAL TESTING** - Verifying no behavioral changes introduced
🎯 **STEP 9: COMMIT & PUSH** - Saving refactoring with detailed rationale
🎯 **STEP 10: PULL REQUEST CREATION** - Opening PR with before/after comparisons
🎯 **STEP 11: PR REVIEW** - Reviewing for improved maintainability
🎯 **STEP 12: REVIEW FEEDBACK** - Addressing suggestions for further simplification
🎯 **STEP 13: PHILOSOPHY COMPLIANCE** - Confirming adherence to bricks & studs pattern
🎯 **STEP 14: PR MERGEABLE CHECK** - Ensuring zero performance degradation
🎯 **STEP 15: FINAL CLEANUP** - Removing deprecated code references
```

## Task Type 5: Documentation Tasks

**Scenario**: Writing guides, updating READMEs, or creating specifications

### Example Announcements

```
🎯 **STEP 1: REQUIREMENTS CLARIFICATION** - Defining documentation scope and audience
🎯 **STEP 2: GITHUB ISSUE CREATION** - Creating documentation task with outline
🎯 **STEP 3: WORKTREE & BRANCH SETUP** - Creating isolated environment for docs
🎯 **STEP 4: RESEARCH & DESIGN** - Analyzing existing docs and planning structure
🎯 **STEP 5: IMPLEMENTATION** - Writing comprehensive documentation with examples
🎯 **STEP 6: REFACTOR & SIMPLIFY** - Simplifying language and improving clarity
🎯 **STEP 7: TESTS & PRE-COMMIT** - Validating markdown formatting and links
🎯 **STEP 8: LOCAL TESTING** - Reading docs from user perspective for clarity
🎯 **STEP 9: COMMIT & PUSH** - Saving documentation updates
🎯 **STEP 10: PULL REQUEST CREATION** - Opening PR with documentation preview
🎯 **STEP 11: PR REVIEW** - Reviewing for accuracy and completeness
🎯 **STEP 12: REVIEW FEEDBACK** - Adding suggested examples and clarifications
🎯 **STEP 13: PHILOSOPHY COMPLIANCE** - Ensuring docs reflect project philosophy
🎯 **STEP 14: PR MERGEABLE CHECK** - Verifying all links and formatting pass
🎯 **STEP 15: FINAL CLEANUP** - Removing draft notes and temporary content
```

## Task Type 6: Configuration Changes

**Scenario**: Updating CI/CD, modifying workflows, or adjusting environment settings

### Example Announcements

```
🎯 **STEP 1: REQUIREMENTS CLARIFICATION** - Defining CI/CD configuration requirements
🎯 **STEP 2: GITHUB ISSUE CREATION** - Creating config change proposal with justification
🎯 **STEP 3: WORKTREE & BRANCH SETUP** - Creating isolated environment for config changes
🎯 **STEP 4: RESEARCH & DESIGN** - Analyzing current config and planning improvements
🎯 **STEP 5: IMPLEMENTATION** - Updating workflow files and environment settings
🎯 **STEP 6: REFACTOR & SIMPLIFY** - Removing redundant configuration
🎯 **STEP 7: TESTS & PRE-COMMIT** - Validating YAML syntax and configuration schema
🎯 **STEP 8: LOCAL TESTING** - Testing workflow changes with dry-run
🎯 **STEP 9: COMMIT & PUSH** - Saving configuration changes
🎯 **STEP 10: PULL REQUEST CREATION** - Opening PR with config testing strategy
🎯 **STEP 11: PR REVIEW** - Reviewing for security and best practices
🎯 **STEP 12: REVIEW FEEDBACK** - Adjusting timeout values per feedback
🎯 **STEP 13: PHILOSOPHY COMPLIANCE** - Ensuring config follows simplicity principles
🎯 **STEP 14: PR MERGEABLE CHECK** - Verifying CI passes with new configuration
🎯 **STEP 15: FINAL CLEANUP** - Removing test configuration and comments
```

## Todo List Integration

Always include workflow step numbers in todo lists for visibility:

### Example Todo List Format

```markdown
## Current Progress

- [completed] 🎯 STEP 1: Requirements Clarification
- [completed] 🎯 STEP 2: GitHub Issue Creation
- [completed] 🎯 STEP 3: Worktree & Branch Setup
- [completed] 🎯 STEP 4: Research & Design
- [in_progress] 🎯 STEP 5: Implementation
- [pending] 🎯 STEP 6: Refactor & Simplify
- [pending] 🎯 STEP 7: Tests & Pre-Commit
- [pending] 🎯 STEP 8: Local Testing
- [pending] 🎯 STEP 9: Commit & Push
- [pending] 🎯 STEP 10: Pull Request Creation
- [pending] 🎯 STEP 11: PR Review
- [pending] 🎯 STEP 12: Review Feedback
- [pending] 🎯 STEP 13: Philosophy Compliance
- [pending] 🎯 STEP 14: PR Mergeable Check
- [pending] 🎯 STEP 15: Final Cleanup

**Progress**: Step 5 of 15 (33% complete)
```

## Benefits of Phase Announcements

### For Users

1. **Clear Progress Tracking**: Always know "We're on step 7 of 15"
2. **Workflow Transparency**: See the systematic approach in action
3. **Time Estimation**: Understand how much work remains
4. **Trust Building**: Verify UltraThink follows the documented workflow

### For Reflection Analysis

1. **Auditability**: Easy to verify "Did Claude follow the workflow?"
2. **Phase Correlation**: Map actions to specific workflow steps
3. **Quality Metrics**: Measure time spent per phase
4. **Improvement Insights**: Identify bottleneck phases

### For System Behavior

1. **Consistent Communication**: Standardized format across all tasks
2. **Workflow Flexibility**: Adaptations are explicitly announced
3. **Progress Visibility**: Users never wonder "What's happening?"
4. **Documentation Integration**: Announcements match workflow documentation

## Anti-Patterns to Avoid

### ❌ Vague Announcements

```
❌ Working on the feature now...
❌ Doing some analysis...
❌ Making changes...
```

### ✅ Clear Announcements

```
✅ 🎯 **STEP 5: IMPLEMENTATION** - Building authentication module
✅ 🎯 **STEP 4: RESEARCH & DESIGN** - Architecting solution with TDD
✅ 🎯 **STEP 6: REFACTOR & SIMPLIFY** - Applying ruthless simplicity
```

### ❌ Missing Step Numbers

```
❌ Starting implementation phase...
❌ Now reviewing the code...
```

### ✅ Include Step Numbers

```
✅ 🎯 **STEP 5: IMPLEMENTATION** - Building solution
✅ 🎯 **STEP 11: PR REVIEW** - Conducting code review
```

### ❌ Overly Verbose

```
❌ 🎯 **STEP 5: IMPLEMENTATION** - Now I'm going to build the authentication module using the architect's design, making sure to follow TDD principles and write tests first, then implement the code iteratively...
```

### ✅ Concise Purpose

```
✅ 🎯 **STEP 5: IMPLEMENTATION** - Building authentication module following TDD
```

## Customization for Different Workflows

If you've customized `.claude/workflow/DEFAULT_WORKFLOW.md`, adapt these examples to match your workflow steps:

1. **Read your workflow file**: Understand your custom steps
2. **Adapt announcements**: Match your step names and purposes
3. **Maintain format**: Keep the 🎯 **STEP N: NAME** - purpose pattern
4. **Document examples**: Add examples to this file for your workflow

## Related Documentation

- **Workflow Definition**: `.claude/workflow/DEFAULT_WORKFLOW.md`
- **UltraThink Command**: `.claude/commands/amplihack/ultrathink.md`
- **User Preferences**: `.claude/context/USER_PREFERENCES.md`
- **Project Philosophy**: `.claude/context/PHILOSOPHY.md`

---

**Last Updated**: 2025-11-05
**Maintained By**: Amplihack Framework Team
**Purpose**: Standardize workflow phase communication for transparency and trust
