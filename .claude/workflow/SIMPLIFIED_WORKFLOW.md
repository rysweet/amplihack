---
name: Simplified Workflow
description: Lightweight 17-step workflow for features, bugs, and refactoring
version: 1.1.0
steps: 17
applies_to:
  - features
  - bugs
  - refactoring
phases:
  - preparation
  - implementation
  - testing
  - review
  - merge
prerequisites:
  - Git repository initialized
  - GitHub CLI (gh) or Azure DevOps CLI (az) installed
  - Tests directory exists
success_criteria:
  - Changes merged to main branch
  - All tests passing
  - PR approved by reviewer
failure_modes:
  - Tests fail → fix tests or implementation
  - Review rejected → address feedback
  - Merge conflicts → resolve manually
philosophy_alignment:
  - principle: Ruthless Simplicity
    application: Lightweight 17-step process for clear requirements (1-10 files)
  - principle: Test-Driven Development
    application: Write tests before implementation (Step 6)
  - principle: Zero-BS Implementation
    application: No debug code or TODOs allowed (Step 10)
  - principle: Modular Design
    application: 1-10 files maximum scope enforces modularity
---

# Simplified Workflow

A lightweight 17-step workflow optimized for:
- ✅ **Small to medium changes** (1-10 files)
- ✅ **Clear requirements** (no research needed)
- ✅ **Standard patterns** (no architecture decisions)

For complex work requiring architecture design, use [DEFAULT_WORKFLOW.md](./DEFAULT_WORKFLOW.md) instead.

## When NOT to Use This Workflow

Use [DEFAULT_WORKFLOW.md](./DEFAULT_WORKFLOW.md) instead for:
- ❌ Changes requiring architecture decisions
- ❌ New system components or modules
- ❌ Complex refactoring across >10 files
- ❌ Features needing research or design phase

---

## Step 0: Workflow Preparation

⚠️ **DO NOT SKIP STEPS** - Each step has a specific purpose in ensuring quality.

**Actions**:
- ✅ Read this workflow completely before starting
- ✅ Verify you have all prerequisites (see below)
- ✅ Confirm this is the right workflow for your task (see "When NOT to Use" above)

---

## Step 1: Verify Prerequisites

**Actions**:
- ✅ Check Git: `git --version`
- ✅ Check GitHub CLI or Azure CLI: `gh --version` or `az --version`
- ✅ Verify git repository: `git status`

---

## Step 2: Create Issue/Work Item

**Actions**:
- ✅ Create issue: `gh issue create --title "Add user authentication" --body "Implement JWT-based authentication"`
- ✅ Note the issue number (e.g., #42) for branch name

---

## Step 3: Create Feature Branch

**Actions**:
- ✅ Create and switch to branch using appropriate prefix:
  - Features: `git checkout -b feature/issue-42-user-authentication`
  - Bugs: `git checkout -b fix/issue-42-authentication-bug`
  - Refactoring: `git checkout -b refactor/issue-42-auth-cleanup`
- ✅ Pattern: `<type>/issue-<number>-<description>` where type is `feature`, `fix`, or `refactor`

---

## Step 4: Review Requirements

**Actions**:
- ✅ Read issue description completely
- ✅ Identify success criteria and constraints

---

## Step 5: Identify Files to Change

**Actions**:
- ✅ List files to modify: `find . -name "*auth*" -type f`
- ✅ Plan scope: 1-10 files maximum

---

## Step 6: Write Failing Tests (TDD)

**Actions**:
- ✅ Write tests for new functionality
- ✅ Run tests to verify they fail: `pytest tests/`

**Example**:
```python
def test_user_authentication():
    auth = Authenticator()
    token = auth.authenticate("user", "password")
    assert auth.validate(token) is True
```

---

## Step 7: Implement Solution

**Actions**:
- ✅ Write code to make tests pass
- ✅ Follow existing code style
- ✅ Keep changes focused on the issue

---

## Step 8: Run Tests Until Green

**Actions**:
- ✅ Run full test suite: `pytest tests/ -v`
- ✅ Fix any failing tests
- ✅ Repeat until 100% pass rate

---

## Step 9: Manual Testing (If Needed)

**When manual testing is required**:
- ✅ UI changes visible to users
- ✅ CLI commands with interactive prompts
- ✅ Integration with external services
- ✅ Performance-sensitive operations

**Actions**:
- ✅ Test critical user paths manually
- ✅ Verify edge cases: `python -m myapp authenticate --username test`
- ✅ Document test scenarios if complex

---

## Step 10: Pre-Commit Review

**Actions**:
- ✅ Review changes: `git diff`
- ✅ Verify no debug code or TODOs remain
- ✅ Scan for secrets (see Security section below)

---

## Step 11: Commit Changes

**Actions**:
- ✅ Stage changes: `git add src/auth.py tests/test_auth.py`
- ✅ Commit with clear message:
  ```bash
  git commit -m "feat: add JWT authentication (#42)

  - Implement JWT token generation
  - Add token validation
  - Update tests for auth module"
  ```

**Format**: `<type>: <description> (#<issue-number>)`
**Types**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

---

## Step 12: Push to Remote

**Actions**:
- ✅ Push branch: `git push -u origin feature/issue-42-user-authentication`

---

## Step 13: Create Pull Request

**Actions**:
- ✅ Create PR: `gh pr create --title "Add user authentication (#42)" --body "Implements JWT-based authentication as described in #42" --reviewer teammate`
- ✅ Or use Azure DevOps: `az repos pr create --title "Add user authentication (#42)" --source-branch feature/issue-42-user-authentication`

---

## Step 14: Address Review Feedback

**Actions**:
- ✅ Respond to review comments
- ✅ Make requested changes
- ✅ Push updates: `git push`

---

## Step 15: Merge Pull Request

**Actions**:
- ✅ Ensure CI checks pass and approvals received
- ✅ Merge PR: `gh pr merge --squash --delete-branch`
- ✅ Or Azure: `az repos pr update --id 1234 --status completed --delete-source-branch true`

---

## Step 16: Clean Up Local Branch

**Actions**:
- ✅ Switch to main: `git checkout main`
- ✅ Pull latest: `git pull`
- ✅ Delete feature branch: `git branch -d feature/issue-42-user-authentication`

---

## 🔒 Security Best Practices

**Before committing**:
- ✅ Quote all variables in scripts: `"$branch_name"` not `$branch_name`
- ✅ Scan for secrets: `git diff --cached | grep -E '(password|token|secret|api[_-]?key|aws|gcp)'`
- ✅ Never commit credentials, API keys, or tokens
- ✅ Verify `.gitignore` includes: `*.env`, `*.key`, `secrets/`, `.env.*`

**Before merging PR**:
- ✅ Review full diff: `gh pr diff` or `az repos pr show --id 1234`
- ✅ Ensure no sensitive data in commit history
