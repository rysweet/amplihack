---
name: DEFAULT_WORKFLOW
version: 1.1.0
description: Standard 22-step workflow (Steps 0-21) for feature development, bug fixes, and refactoring
steps: 22
phases:
  - requirements-clarification
  - design
  - implementation
  - testing
  - review
  - merge
success_criteria:
  - "All steps completed"
  - "PR is mergeable"
  - "CI passes"
  - "Philosophy compliant"
philosophy_alignment:
  - principle: Ruthless Simplicity
    application: Each step has single clear purpose
  - principle: Zero-BS Implementation
    application: No stubs or placeholders in deliverables
  - principle: Test-Driven Development
    application: Write tests before implementation
  - principle: Modular Design
    application: Clean module boundaries enforced through workflow
customizable: true
---

# Default Coding Workflow

This file defines the default workflow for all non-trivial code changes.

## The 22-Step Workflow

### Step 0: Workflow Preparation (MANDATORY)
- Read entire workflow file
- Create TodoWrite entries for ALL steps (0-21)
- Mark steps complete only when truly done

### Step 1: Prepare the Workspace
- Clean local environment, no unstashed changes, git fetch

### Step 2: Rewrite and Clarify Requirements
- Use prompt-writer agent to clarify task requirements
- Use analyzer agent to understand codebase context
- Use ambiguity agent if requirements unclear
- Define clear success criteria

### Step 3: Create GitHub Issue
- Create issue using gh issue create
- Include problem description, requirements, constraints
- Add success criteria and labels

### Step 4: Setup Worktree and Branch
- Use worktree-manager agent for worktree operations
- Create branch: feat/issue-{number}-{description}
- Push branch with tracking

### Step 5: Research and Design
- Use architect agent for solution architecture
- Use api-designer agent for API contracts (if applicable)
- Use database agent for data model (if applicable)
- Use security agent for security requirements
- Ask zen-architect to review, architect to consider feedback
- Document module specifications and implementation plan

### Step 6: Retcon Documentation Writing
- Use documentation-writer agent to write docs for feature as if complete
- Use architect agent to review alignment
- Revise based on feedback

### Step 7: Test Driven Development - Writing Tests First
- Use tester agent to write failing tests (TDD approach)

### Step 8: Implement the Solution
- Use builder agent to implement from specifications
- Use integration agent for external service connections
- Make failing tests pass iteratively

### Step 9: Refactor and Simplify
- Use cleanup agent for ruthless simplification
- Use optimizer agent for performance improvements
- Remove unnecessary abstractions
- Verify no placeholders remain (zero-BS principle)

### Step 10: Review Pass Before Commit
- Use reviewer agent for comprehensive code review
- Use security agent for security review
- Verify philosophy compliance with philosophy-guardian agent
- Ensure adequate test coverage

### Step 11: Incorporate Review Feedback
- Use architect agent to assess feedback
- Use builder agent to implement changes

### Step 12: Run Tests and Pre-commit Hooks
- Ensure pre-commit hooks installed
- Use pre-commit-diagnostic agent if hooks fail
- Run all unit tests
- Execute pre-commit run --all-files
- Fix all issues

### Step 13: Mandatory Local Testing
- Test simple and complex use cases
- Test integration points
- Verify no regressions
- Document test results

### Step 14: Commit and Push
- Stage all changes
- Write detailed commit message
- Reference issue number
- Push to remote

### Step 15: Open Pull Request as Draft
- Create PR as DRAFT using gh pr create --draft
- Link to GitHub issue
- Write comprehensive description
- Include test plan

### Step 16: Review the PR (MANDATORY)
- Use reviewer agent for comprehensive review
- Use security agent for security review
- Post review comments on PR

### Step 17: Implement Review Feedback (MANDATORY)
- Use builder agent to implement changes
- Address each review comment
- Push updates

### Step 18: Philosophy Compliance Check
- Use reviewer agent for final philosophy check
- Use patterns agent to verify pattern compliance
- Verify ruthless simplicity achieved

### Step 19: Final Cleanup and Verification
- Use cleanup agent for final quality pass
- Remove temporary artifacts
- Verify module boundaries

### Step 20: Convert PR to Ready for Review
- Convert draft to ready using gh pr ready
- Tag reviewers for final approval

### Step 21: Ensure PR is Mergeable
- Check CI status
- Use ci-diagnostic-workflow agent if CI fails
- Resolve merge conflicts
- Verify PR approved

## Referenced Agents

### Core Agents
- architect: System architecture and design
- builder: Primary implementation
- reviewer: Code review
- tester: Test writing
- optimizer: Performance improvements
- api-designer: API contract design

### Specialized Agents
- prompt-writer: Requirements clarification
- analyzer: Codebase analysis
- ambiguity: Ambiguity detection
- cleanup: Code simplification
- security: Security review
- documentation-writer: Documentation
- worktree-manager: Git worktree operations
- ci-diagnostic-workflow: CI failure diagnosis
- philosophy-guardian: Philosophy compliance
- patterns: Pattern verification
- pre-commit-diagnostic: Pre-commit hook issues
- integration: External service integration
- database: Data model design
- zen-architect: High-level architecture review
