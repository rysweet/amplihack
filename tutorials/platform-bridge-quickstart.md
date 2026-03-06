# Platform Bridge - Quick Start Tutorial

Learn to use the platform bridge in 10 minutes. This tutorial works fer both GitHub and Azure DevOps repositories.

## What You'll Learn

By the end of this tutorial, ye'll be able to:

- Use platform bridge to create issues
- Create draft pull requests
- Check CI status
- All without worryin' about which platform yer on

## Prerequisites

Before startin', make sure ye have:

- Git repository with a remote (GitHub or Azure DevOps)
- Appropriate CLI tool installed:
  - **GitHub**: `gh` CLI ([install guide](https://cli.github.com/manual/installation))
  - **Azure DevOps**: `az` CLI ([install guide](https://learn.microsoft.com/cli/azure/install-azure-cli))
- CLI authenticated (run `gh auth login` or `az login`)

**Time needed**: 10 minutes

---

## Step 1: Verify Your Setup (2 minutes)

First, let's make sure everything be ready.

### Check Git Remote

```bash
git remote -v
```

Ye should see output like:

```
origin  https://github.com/owner/repo.git (fetch)
origin  https://github.com/owner/repo.git (push)
```

or

```
origin  https://dev.azure.com/org/project/_git/repo (fetch)
origin  https://dev.azure.com/org/project/_git/repo (push)
```

**What if there be no output?**

```bash
# Add a remote
git remote add origin https://github.com/owner/repo.git
```

### Verify CLI Tool

**For GitHub:**

```bash
gh --version
gh auth status
```

Should show:

```
✓ Logged in to github.com as username
```

**For Azure DevOps:**

```bash
az --version
az account show
```

Should show yer account information.

**If authentication fails**, run:

```bash
gh auth login  # For GitHub
# OR
az login       # For Azure DevOps
```

---

## Step 2: Create Your First Issue (2 minutes)

Now let's use the platform bridge to create an issue. The code be identical fer both platforms!

### Create a Python Script

Create a file called `create_issue.py`:

```python
from claude.tools.platform_bridge import PlatformBridge

# Automatically detects platform from git remote
bridge = PlatformBridge()

# Create an issue - works on both GitHub and Azure DevOps
issue = bridge.create_issue(
    title="Platform Bridge Tutorial Test",
    body="""## Purpose

This issue was created as part of the Platform Bridge tutorial.

## Tasks
- [x] Learn platform bridge basics
- [ ] Create issues programmatically
- [ ] Create pull requests
- [ ] Check CI status

Feel free to close this issue after the tutorial.
"""
)

print(f"Created issue #{issue['number']}")
print(f"View it at: {issue['url']}")
```

### Run It

```bash
python create_issue.py
```

**Output:**

```
Created issue #42
View it at: https://github.com/owner/repo/issues/42
```

**What just happened?**

1. Bridge detected yer platform from git remote
2. Called appropriate CLI tool (gh or az)
3. Created issue using platform-specific command
4. Returned normalized result

**Open the URL** in yer browser to see the created issue!

---

## Step 3: Create a Feature Branch (1 minute)

Let's create a branch fer our tutorial PR:

```bash
git checkout -b tutorial/platform-bridge-test
```

Create a simple change:

```bash
echo "# Platform Bridge Test" > TUTORIAL.md
git add TUTORIAL.md
git commit -m "docs: Add platform bridge tutorial test file"
git push -u origin tutorial/platform-bridge-test
```

---

## Step 4: Create a Draft Pull Request (2 minutes)

Now create a draft PR programmatically.

### Create PR Script

Create `create_pr.py`:

```python
from claude.tools.platform_bridge import PlatformBridge

bridge = PlatformBridge()

# Get the issue number from previous step
issue_number = 42  # Replace with yer actual issue number

# Create draft PR
pr = bridge.create_draft_pr(
    title=f"Tutorial: Platform Bridge Test (Issue #{issue_number})",
    body=f"""## Summary

This PR tests the platform bridge functionality from the tutorial.

## Changes
- Added TUTORIAL.md test file

## Related Issues
Closes #{issue_number}

## Notes
This be a test PR fer the tutorial - safe to close.
""",
    source_branch="tutorial/platform-bridge-test",
    target_branch="main"
)

print(f"Created draft PR #{pr['number']}")
print(f"View it at: {pr['url']}")
print(f"State: {pr['state']}")
```

### Run It

```bash
python create_pr.py
```

**Output:**

```
Created draft PR #123
View it at: https://github.com/owner/repo/pull/123
State: draft
```

**Check yer PR** in the browser - it should be marked as "Draft"!

---

## Step 5: Add a Comment to Your PR (1 minute)

Let's add a comment to the PR.

### Create Comment Script

Create `add_comment.py`:

```python
from claude.tools.platform_bridge import PlatformBridge

bridge = PlatformBridge()

pr_number = 123  # Replace with yer actual PR number

# Add comment
comment = bridge.add_pr_comment(
    pr_number=pr_number,
    comment="""## Tutorial Progress

✅ Issue created successfully
✅ Branch pushed
✅ Draft PR created
✅ Comment added

Next step: Check CI status!
"""
)

print(f"Added comment to PR #{pr_number}")
print(f"View at: {comment['url']}")
```

### Run It

```bash
python add_comment.py
```

**Refresh yer PR** in the browser to see the comment!

---

## Step 6: Check CI Status (2 minutes)

Finally, let's check if CI be runnin'.

### Create CI Check Script

Create `check_ci.py`:

```python
from claude.tools.platform_bridge import PlatformBridge
import time

bridge = PlatformBridge()

pr_number = 123  # Replace with yer actual PR number

# Wait a bit fer CI to start
print("Waitin' 10 seconds fer CI to start...")
time.sleep(10)

# Check CI status
status = bridge.check_ci_status(pr_number=pr_number)

print(f"\n=== CI Status fer PR #{pr_number} ===")
print(f"Total checks: {status['total_checks']}")
print(f"Passed: {status['passed']}")
print(f"Failed: {status['failed']}")
print(f"Pending: {status['pending']}")
print(f"All passing: {status['all_passing']}")

print("\nIndividual checks:")
for check in status['checks']:
    emoji = "✅" if check['status'] == 'success' else "❌" if check['status'] == 'failure' else "⏳"
    print(f"  {emoji} {check['name']}: {check['status']}")
    if check.get('url'):
        print(f"     {check['url']}")
```

### Run It

```bash
python check_ci.py
```

**Output:**

```
Waitin' 10 seconds fer CI to start...

=== CI Status fer PR #123 ===
Total checks: 3
Passed: 2
Failed: 0
Pending: 1
All passing: False

Individual checks:
  ✅ build: success
  ✅ test: success
  ⏳ lint: pending
```

---

## Step 7: Mark PR Ready (Optional)

If all CI checks pass, ye can mark the PR as ready:

```python
from claude.tools.platform_bridge import PlatformBridge

bridge = PlatformBridge()

result = bridge.mark_pr_ready(pr_number=123)

if result['success']:
    print(f"PR #{result['number']} be ready fer review!")
```

---

## Cleanup

After the tutorial, clean up yer test artifacts:

1. **Close the PR** (don't merge it - it be just a test)
2. **Close the issue**
3. **Delete the branch**:
   ```bash
   git checkout main
   git branch -D tutorial/platform-bridge-test
   git push origin --delete tutorial/platform-bridge-test
   ```

---

## What You Learned

Congratulations! Ye now know how to:

✅ Detect platform automatically
✅ Create issues on both GitHub and Azure DevOps
✅ Create draft pull requests
✅ Add comments to PRs
✅ Check CI status
✅ Mark PRs ready fer review

**Key Insight**: The exact same code works on both platforms! The bridge handles all platform-specific differences.

---

## Next Steps

Now that ye understand the basics:

1. **Learn workflows**: Read [Platform Bridge Workflows](../howto/platform-bridge-workflows.md)
2. **Explore API**: See [API Reference](../reference/platform-bridge-api.md)
3. **Handle errors**: Check [Troubleshooting Guide](../troubleshooting/platform-bridge.md)
4. **Security**: Review [Security Best Practices](../security/platform-bridge-security.md)

---

## Common Issues

### "Platform could not be detected"

Make sure ye have a git remote:

```bash
git remote -v
```

If empty, add one:

```bash
git remote add origin <your-repo-url>
```

### "CLI tool not found"

Install the required CLI:

- GitHub: `brew install gh`
- Azure DevOps: `brew install azure-cli`

### "Authentication failed"

Run authentication:

```bash
gh auth login     # GitHub
az login          # Azure DevOps
```

---

## Tutorial Complete!

Ye've successfully learned the platform bridge basics. The same code works across GitHub and Azure DevOps with zero configuration changes.

**Ready fer more?** Check out the [complete documentation](../platform-bridge/README.md).
