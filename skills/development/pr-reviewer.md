# PR Reviewer

Structured pull request review methodology with GitHub CLI integration.

## When to Use

- Reviewing pull requests from team members
- Providing structured, actionable feedback
- Maintaining code quality standards
- Approving or requesting changes
- Learning effective review practices

## Structured Feedback Format

### The SBI Framework

```
Situation: Where in the code (file:line)
Behavior: What the code does
Impact: Why it matters (positive or negative)

Example:
"In `auth.py:45`, the password comparison uses `==` instead of 
constant-time comparison. This could allow timing attacks to 
guess passwords character by character."
```

### Comment Types

```markdown
## Critical (Blocking)
Must be fixed before merge. Security issues, bugs, broken functionality.
Prefix: **[BLOCKING]** or **[CRITICAL]**

## Suggestion (Should Fix)
Strong recommendation, but PR can merge without.
Prefix: **[SUGGESTION]** or **[SHOULD FIX]**

## Nit (Optional)
Style preference, minor improvement, optional.
Prefix: **[NIT]** or **[OPTIONAL]**

## Question
Need clarification, not necessarily a change.
Prefix: **[QUESTION]** or **?**

## Praise
Positive feedback for good work.
Prefix: **[NICE]** or **[GOOD]**
```

## Priority Categorization

### Blocking Issues (Must Fix)

```markdown
**[BLOCKING]** Security vulnerability

`src/api/auth.py:67`
```python
password_hash = hashlib.md5(password).hexdigest()
```

MD5 is cryptographically broken. Use bcrypt or argon2:
```python
from passlib.hash import bcrypt
password_hash = bcrypt.hash(password)
```
```

### Should Fix Issues

```markdown
**[SUGGESTION]** N+1 query pattern

`src/api/orders.py:34`
```python
for user in users:
    orders = db.query(Order).filter_by(user_id=user.id).all()
```

This will execute N+1 queries. Consider eager loading:
```python
users = db.query(User).options(joinedload(User.orders)).all()
```
```

### Nits (Optional)

```markdown
**[NIT]** Naming could be clearer

`src/utils/helpers.py:12`
```python
def proc(d):
```

Consider a more descriptive name like `process_data()` or specific to what it does.
```

### Questions

```markdown
**[QUESTION]** Intentional behavior?

`src/services/payment.py:89`
```python
if amount <= 0:
    return None  # Silent failure
```

Should this raise an exception or log a warning? Returning None silently might hide bugs.
```

## GitHub CLI Commands

### Basic Review Commands

```bash
# View PR details
gh pr view 123

# View PR diff
gh pr diff 123

# Check out PR locally
gh pr checkout 123

# List open PRs
gh pr list

# List PRs by author
gh pr list --author="username"

# List PRs for review
gh pr list --reviewer=@me
```

### Adding Comments

```bash
# Add general comment
gh pr comment 123 --body "Overall looks good! A few suggestions below."

# Add review comment on specific line
# (Best done through web interface or gh pr review)

# Start a review (collects comments)
gh pr review 123

# Submit review with approval
gh pr review 123 --approve --body "LGTM! Ship it."

# Request changes
gh pr review 123 --request-changes --body "Please address the security issues."

# Comment only (no approval/rejection)
gh pr review 123 --comment --body "Some suggestions, but not blocking."
```

### Multi-line Comments

```bash
# Create review comment file
cat > review.md << 'EOF'
## Overall Assessment

Good work on this feature! The implementation is clean and well-tested.

### Must Address
- [ ] Fix the SQL injection in `query.py:45`
- [ ] Add input validation for user_id

### Suggestions
- Consider extracting the retry logic into a utility
- The error messages could be more specific

### Nice Work
- Great test coverage
- Clean separation of concerns
EOF

# Submit review with file
gh pr review 123 --request-changes --body-file review.md
```

### Review Workflow Script

```bash
#!/bin/bash
# review-pr.sh - Comprehensive PR review workflow

PR_NUMBER=$1

echo "=== PR $PR_NUMBER Review ==="

# Fetch PR info
echo "--- PR Details ---"
gh pr view $PR_NUMBER

# Check CI status
echo "--- CI Status ---"
gh pr checks $PR_NUMBER

# View changed files
echo "--- Changed Files ---"
gh pr diff $PR_NUMBER --stat

# Checkout for local testing
echo "--- Checking Out ---"
gh pr checkout $PR_NUMBER

# Run tests
echo "--- Running Tests ---"
pytest tests/

# Run linting
echo "--- Running Linting ---"
ruff check .

echo "=== Review Complete ==="
```

## Review Templates

### Standard Review Template

```markdown
## PR Review: #[NUMBER]

### Summary
[One-line summary of what this PR does]

### Review Checklist
- [ ] Code follows project style guidelines
- [ ] Tests added/updated for changes
- [ ] Documentation updated if needed
- [ ] No security vulnerabilities introduced
- [ ] Performance impact considered

### Findings

#### Critical Issues
[None / List issues]

#### Suggestions
[None / List suggestions]

#### Questions
[None / List questions]

### Verdict
[ ] Approved
[ ] Approved with suggestions
[ ] Request changes
[ ] Need more information
```

### Security-Focused Review

```markdown
## Security Review: PR #[NUMBER]

### Security Checklist
- [ ] Input validation present
- [ ] Output encoding/escaping
- [ ] Authentication checked
- [ ] Authorization verified
- [ ] No sensitive data in logs
- [ ] No hardcoded secrets
- [ ] SQL injection prevented
- [ ] XSS prevented
- [ ] CSRF protection (if applicable)

### Findings
[Security-related issues]

### Risk Assessment
- **Risk Level**: [Low/Medium/High/Critical]
- **Attack Surface**: [What could be exploited]
- **Mitigation**: [How to fix]
```

### Quick Review Template

```markdown
## Quick Review: #[NUMBER]

**Status**: [LGTM / Changes Requested / Questions]

### Key Points
- [Point 1]
- [Point 2]

### Action Items
- [ ] [Required change]
```

## Review Best Practices

### Do

```
- Review promptly (within 24 hours)
- Understand the context before commenting
- Focus on the code, not the author
- Explain WHY, not just WHAT
- Suggest specific fixes when possible
- Acknowledge good work
- Ask questions instead of assuming
- Test the changes locally when needed
- Prioritize feedback clearly
```

### Don't

```
- Block on style (let linters handle it)
- Nitpick endlessly
- Be condescending or harsh
- Demand changes for preferences
- Leave vague comments
- Ignore context/requirements
- Review too quickly without understanding
- Request rewrites of working code
```

## Review Checklist by Change Type

### New Feature

```
[ ] Feature matches requirements
[ ] Tests cover happy path and errors
[ ] API design is consistent
[ ] Documentation added
[ ] Performance acceptable
[ ] Security considered
[ ] Error handling present
[ ] Logging appropriate
```

### Bug Fix

```
[ ] Root cause identified correctly
[ ] Fix addresses root cause (not symptoms)
[ ] Regression test added
[ ] No new bugs introduced
[ ] Related areas checked
[ ] Fix is minimal and focused
```

### Refactoring

```
[ ] Behavior preserved (tests pass)
[ ] No functional changes mixed in
[ ] Code is actually simpler
[ ] Tests updated if signatures changed
[ ] No performance regression
```

### Dependency Update

```
[ ] Breaking changes reviewed
[ ] Security advisories checked
[ ] License compatible
[ ] Tests pass
[ ] Changelog reviewed
```

## Efficiency Tips

### Review Order

```
1. Read PR description and linked issues
2. Review test changes first (understand intent)
3. Review implementation
4. Check CI results
5. Test locally if complex
6. Write consolidated feedback
```

### Batch Comments

```bash
# Instead of multiple small comments, create one comprehensive review
gh pr review 123 --comment --body "$(cat << 'EOF'
## Review Comments

### src/auth.py
- **Line 45**: [BLOCKING] Use constant-time comparison
- **Line 67**: [SUGGESTION] Consider extracting to helper

### src/api.py  
- **Line 12**: [NIT] Unused import
- **Line 89**: [QUESTION] Why this timeout value?

### Overall
Good progress! Please address the security issue before merge.
EOF
)"
```

### Follow-up

```bash
# Check if changes were made
gh pr diff 123

# Re-review after changes
gh pr review 123 --approve --body "Issues addressed, LGTM!"

# Or request more changes
gh pr review 123 --request-changes --body "Still seeing the issue on line 45"
```
