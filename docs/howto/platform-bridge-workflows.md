# Platform Bridge - Common Workflows

Practical guides fer usin' the platform bridge in common scenarios.

## Complete Feature Development Workflow

This workflow shows the complete cycle from issue creation to PR merge, workin' on both GitHub and Azure DevOps.

### Step 1: Create Issue/Work Item

```python
from claude.tools.platform_bridge import PlatformBridge

bridge = PlatformBridge()

# Create issue fer yer feature
issue = bridge.create_issue(
    title="Add user authentication",
    body="""## Requirements
- JWT token authentication
- Refresh token support
- Password reset flow

## Acceptance Criteria
- [ ] Users can log in
- [ ] Tokens expire after 1 hour
- [ ] Password reset emails sent
"""
)

print(f"Created issue #{issue['number']}: {issue['url']}")
# Output: Created issue #42: https://github.com/owner/repo/issues/42
```

### Step 2: Create Feature Branch

```bash
git checkout -b feat/issue-42-authentication
```

### Step 3: Implement the Feature

```bash
# Make yer code changes
git add .
git commit -m "feat: Implement JWT authentication

Implements issue #42

- Add JWT token generation
- Add refresh token support
- Add password reset flow"
```

### Step 4: Push Branch

```bash
git push -u origin feat/issue-42-authentication
```

### Step 5: Create Draft PR

```python
# Create draft PR fer early feedback
pr = bridge.create_draft_pr(
    title="feat: Add user authentication",
    body=f"""## Summary

Implements JWT authentication as specified in issue #{issue['number']}.

## Changes
- JWT token generation and validation
- Refresh token support
- Password reset email flow

## Test Plan
- [ ] Unit tests fer token generation
- [ ] Integration tests fer login flow
- [ ] Manual testing of password reset

## Related Issues
Closes #{issue['number']}
""",
    source_branch="feat/issue-42-authentication",
    target_branch="main"
)

print(f"Draft PR created: {pr['url']}")
```

### Step 6: Add Progress Comments

```python
# Update PR with progress
bridge.add_pr_comment(
    pr_number=pr['number'],
    comment="All unit tests implemented and passin'! 🎯"
)
```

### Step 7: Check CI Status

```python
import time

# Wait fer CI to run
time.sleep(60)

status = bridge.check_ci_status(pr_number=pr['number'])

if status['all_passing']:
    print("All CI checks passed!")
elif status['pending'] > 0:
    print(f"Waitin' on {status['pending']} checks...")
else:
    print("Some checks failed:")
    for check in status['checks']:
        if check['status'] == 'failure':
            print(f"  ❌ {check['name']}: {check['url']}")
```

### Step 8: Mark PR Ready

```python
# After all checks pass and ye be ready fer review
result = bridge.mark_pr_ready(pr_number=pr['number'])

if result['success']:
    print(f"PR #{pr['number']} be ready fer review!")

    # Add final comment
    bridge.add_pr_comment(
        pr_number=pr['number'],
        comment="""## Ready fer Review! 🚢

All tests be passin' and the feature be complete.

### What to Review
- JWT implementation in `auth/jwt.py`
- Integration tests in `tests/test_auth.py`
- Password reset flow in `auth/reset.py`
"""
    )
```

---

## Handling CI Failures

When CI checks fail, use this workflow to diagnose and fix:

### Check Which Tests Failed

```python
status = bridge.check_ci_status(pr_number=123)

# Print detailed failure information
print(f"Total checks: {status['total_checks']}")
print(f"Passed: {status['passed']}")
print(f"Failed: {status['failed']}")

for check in status['checks']:
    if check['status'] == 'failure':
        print(f"\n❌ {check['name']} failed")
        print(f"   View logs: {check['url']}")
```

### Add Comment with Fix Plan

```python
bridge.add_pr_comment(
    pr_number=123,
    comment="""## CI Failure Analysis

Failed checks:
- ❌ unit-tests: Timeout in test_authentication
- ❌ linting: Missing type hints

### Fix Plan
1. Increase timeout in test configuration
2. Add type hints to auth module
3. Re-run CI

Expected fix time: 15 minutes
"""
)
```

### After Fixin' Issues

```python
# Push yer fixes
# git add . && git commit -m "fix: CI issues" && git push

# Wait a bit, then check again
time.sleep(30)
status = bridge.check_ci_status(pr_number=123)

if status['all_passing']:
    bridge.add_pr_comment(
        pr_number=123,
        comment="✅ All CI checks now passin'!"
    )
```

---

## Workin' with Multiple PRs

Manage several PRs simultaneously:

```python
from claude.tools.platform_bridge import PlatformBridge

bridge = PlatformBridge()

# Track multiple PRs
prs = [
    {"number": 100, "feature": "authentication"},
    {"number": 101, "feature": "authorization"},
    {"number": 102, "feature": "user-profile"}
]

# Check status of all PRs
for pr_info in prs:
    status = bridge.check_ci_status(pr_number=pr_info['number'])

    state = "✅ Ready" if status['all_passing'] else "⏳ Pending"
    print(f"PR #{pr_info['number']} ({pr_info['feature']}): {state}")

    if not status['all_passing'] and status['pending'] == 0:
        # Has failures, not just pending
        print(f"  ❌ {status['failed']} checks failed")
```

---

## Cross-Platform Development

Switch between GitHub and Azure DevOps projects seamlessly:

```python
from claude.tools.platform_bridge import PlatformBridge, Platform

# Project A: GitHub
bridge_github = PlatformBridge("/path/to/github/project")
print(f"Project A platform: {bridge_github.platform}")
# Output: Project A platform: Platform.GITHUB

gh_issue = bridge_github.create_issue(
    title="GitHub feature",
    body="Feature description"
)

# Project B: Azure DevOps
bridge_azdo = PlatformBridge("/path/to/azdo/project")
print(f"Project B platform: {bridge_azdo.platform}")
# Output: Project B platform: Platform.AZDO

azdo_issue = bridge_azdo.create_issue(
    title="Azure DevOps feature",
    body="Feature description"
)

# Same code, different platforms!
```

---

## Automated Release Workflow

Create release PRs automatically:

```python
from claude.tools.platform_bridge import PlatformBridge
import datetime

bridge = PlatformBridge()

# Get current date fer release version
today = datetime.date.today()
version = f"v{today.year}.{today.month}.{today.day}"

# Create release PR
pr = bridge.create_draft_pr(
    title=f"Release {version}",
    body=f"""## Release {version}

This release includes:
- Feature A
- Feature B
- Bugfix C

## Checklist
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Version bumped
""",
    source_branch="release/preparation",
    target_branch="main"
)

print(f"Release PR created: {pr['url']}")

# Wait fer CI
time.sleep(120)

# Check if ready to release
status = bridge.check_ci_status(pr_number=pr['number'])

if status['all_passing']:
    bridge.mark_pr_ready(pr_number=pr['number'])
    bridge.add_pr_comment(
        pr_number=pr['number'],
        comment=f"🚀 Release {version} be ready to ship!"
    )
```

---

## Handlin' Platform-Specific Features

Some features only work on certain platforms:

```python
from claude.tools.platform_bridge import PlatformBridge, Platform

bridge = PlatformBridge()

# Labels only supported on GitHub
if bridge.platform == Platform.GITHUB:
    issue = bridge.create_issue(
        title="Feature request",
        body="Description",
        labels=["enhancement", "help-wanted"]  # GitHub-specific
    )
else:
    # Azure DevOps doesn't support labels in creation
    issue = bridge.create_issue(
        title="Feature request",
        body="Description"
    )
    print("Note: Azure DevOps labels must be added through web UI")
```

---

## Batch Operations

Process multiple issues or PRs efficiently:

```python
from claude.tools.platform_bridge import PlatformBridge

bridge = PlatformBridge()

# Create multiple related issues
features = [
    "User authentication",
    "User authorization",
    "User profile management"
]

created_issues = []

for feature in features:
    issue = bridge.create_issue(
        title=f"Implement {feature}",
        body=f"## Task\n\nImplement {feature} functionality\n\n## Requirements\nTBD"
    )
    created_issues.append(issue)
    print(f"Created: {issue['url']}")

# Create epic issue that links to all
epic_body = "## Related Issues\n\n"
for issue in created_issues:
    epic_body += f"- #{issue['number']}: {issue['title']}\n"

epic = bridge.create_issue(
    title="Epic: User Management System",
    body=epic_body
)

print(f"\nEpic created: {epic['url']}")
```

---

## Error Recovery

Handle errors gracefully:

```python
from claude.tools.platform_bridge import (
    PlatformBridge,
    CLIToolMissingError,
    PRNotFoundError,
    PlatformDetectionError
)

try:
    bridge = PlatformBridge()

except PlatformDetectionError as e:
    print(f"Could not detect platform: {e}")
    print("\nSolutions:")
    print("1. Add git remote: git remote add origin <url>")
    print("2. Ensure remote URL contains github.com or dev.azure.com")
    exit(1)

try:
    pr = bridge.create_draft_pr(
        title="Test PR",
        body="Description",
        source_branch="feat/test",
        target_branch="main"
    )

except CLIToolMissingError as e:
    print(f"Missing CLI tool: {e.tool_name}")
    print(f"Install with: {e.install_command}")
    exit(1)

try:
    result = bridge.mark_pr_ready(pr_number=999)

except PRNotFoundError as e:
    print(f"PR #{e.pr_number} doesn't exist")
    print("Check PR number and try again")
```

---

## Integration with DEFAULT_WORKFLOW

Use platform bridge in automated workflows:

```python
from claude.tools.platform_bridge import PlatformBridge

def workflow_step_3_create_issue(title: str, body: str):
    """Step 3: Create Issue/Work Item (platform-agnostic)"""
    bridge = PlatformBridge()
    issue = bridge.create_issue(title=title, body=body)

    # Store issue number fer later steps
    with open(".workflow_state", "w") as f:
        f.write(f"issue_number={issue['number']}\n")

    return issue

def workflow_step_15_create_pr(title: str, body: str, branch: str):
    """Step 15: Create Draft PR (platform-agnostic)"""
    bridge = PlatformBridge()
    pr = bridge.create_draft_pr(
        title=title,
        body=body,
        source_branch=branch,
        target_branch="main"
    )

    # Store PR number fer later steps
    with open(".workflow_state", "a") as f:
        f.write(f"pr_number={pr['number']}\n")

    return pr

def workflow_step_21_check_ci():
    """Step 21: Check CI Status (platform-agnostic)"""
    # Read PR number from workflow state
    with open(".workflow_state") as f:
        state = dict(line.strip().split("=") for line in f)

    bridge = PlatformBridge()
    status = bridge.check_ci_status(pr_number=int(state['pr_number']))

    return status['all_passing']
```

---

## See Also

- [Platform Bridge Overview](../platform-bridge/README.md) - Complete feature documentation
- [API Reference](../reference/platform-bridge-api.md) - Detailed API documentation
- [Security Guide](../security/platform-bridge-security.md) - Security best practices
