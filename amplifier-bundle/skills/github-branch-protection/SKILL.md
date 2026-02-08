---
name: github-branch-protection
version: 1.0.0
description: Interactive walkthrough for configuring server-side GitHub branch protection rules
auto_activate_keywords:
  - branch protection
  - github protection
  - protect branch
  - require pull request
  - branch protection rules
  - protect main
  - require reviews
  - status checks
  - prevent force push
tags:
  - github
  - security
  - branch-protection
  - ci-cd
  - git
authors:
  - amplihack
last_updated: 2026-02-08
---

# GitHub Branch Protection Skill

## Purpose & Auto-Activation

This skill provides an interactive walkthrough for configuring **server-side GitHub branch protection rules** using both the GitHub CLI (`gh`) and the GitHub web UI. Branch protection is the third and final layer of defense-in-depth for protecting critical branches like `main`.

### Defense-in-Depth Strategy

amplihack implements a three-layer approach to prevent direct commits to `main`:

1. **Layer 1: Client-side hook** (`.git/hooks/pre-commit`)
   - Fast, local validation before commit
   - Can be bypassed with `--no-verify`
   - Documented in `docs/features/main-branch-protection.md`

2. **Layer 2: Agent-side hook** (`amplifier-bundle/hooks/pre_tool_use.py`)
   - Prevents AI agents from bypassing with `--no-verify`
   - Catches both direct commits and bypass attempts
   - Transparent to human workflow

3. **Layer 3: Server-side protection** (this skill)
   - **Cannot be bypassed** - enforced by GitHub servers
   - Requires pull requests with reviews
   - Enforces CI status checks
   - Prevents force pushes and branch deletion
   - Works even if local hooks are disabled

This skill helps you configure Layer 3, completing your repository's security posture.

### Auto-Activation

This skill automatically activates when you mention:
- "protect branch" or "branch protection"
- "require pull request" or "require reviews"
- "github protection" or "protect main"
- "status checks" in the context of GitHub

---

## Prerequisites & Quick Start

### Prerequisites

Before applying branch protection, ensure you have:

1. **GitHub CLI installed and authenticated**
   ```bash
   # Check gh CLI version
   gh --version
   
   # Verify authentication
   gh auth status
   
   # If not authenticated
   gh auth login
   ```

2. **Admin permissions on target repository**
   ```bash
   # Verify your permissions
   gh api repos/{owner}/{repo} | jq '.permissions.admin'
   # Should return: true
   ```

3. **CI workflows already configured and run at least once**
   - Status checks can only protect workflows that have executed
   - Check: `.github/workflows/` contains your CI configuration
   - Verify: Recent PRs show status check results

4. **Knowledge of your CI check names**
   ```bash
   # Discover check names from workflow files
   grep -r "name:" .github/workflows/
   
   # Or from a recent PR
   gh pr checks <PR_NUMBER>
   ```

### Quick Start (30 seconds)

⚠️ **IMPORTANT**: Verify you're in the correct repository before running these commands!

```bash
# 0. Verify repository (DO THIS FIRST!)
gh repo view
# Confirm: owner, name, and branch before proceeding
```

To protect your `main` branch with standard settings:

```bash
# 1. Create protection config file
cat > protection-config.json << 'EOF'
{
  "required_pull_request_reviews": {
    "required_approving_review_count": 1
  },
  "required_status_checks": {
    "strict": false,
    "contexts": ["CI / Validate Code"]
  },
  "enforce_admins": false,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF

# 2. Apply protection
gh api PUT repos/{owner}/{repo}/branches/main/protection \
  --input protection-config.json

# 3. Verify
gh api repos/{owner}/{repo}/branches/main/protection | jq '{
  reviews: .required_pull_request_reviews.required_approving_review_count,
  status_checks: .required_status_checks.contexts,
  force_push: .allow_force_pushes.enabled,
  deletions: .allow_deletions.enabled
}'
```

Replace `{owner}/{repo}` with your repository (e.g., `rysweet/amplihack`).

---

## Quick Reference Table

| Setting | Purpose | Recommended | Trade-off |
|---------|---------|-------------|-----------|
| **Require PR** | Force code review workflow | ✅ Always | Prevents quick hotfixes via direct push |
| **Require Reviews** | Mandate human approval (default: 1) | ✅ Always | Adds latency; balance with count |
| **Require Status Checks** | Enforce CI passing | ✅ Always | Cannot merge if CI broken |
| **Prevent Force Push** | Protect commit history | ✅ Always | Cannot rewrite history on main |
| **Prevent Deletion** | Protect branch existence | ✅ Always | Cannot delete main accidentally |
| **Enforce Admins** | Apply rules to admins too | ⚠️ Use cautiously | Can lock out during emergencies |
| **Strict Status Checks** | Require branch up-to-date | ⚠️ Optional | Forces rebase dance on busy repos |

---

## Method 1: GitHub CLI Walkthrough

### Step 1: Authenticate and Verify Permissions

```bash
# Authenticate with GitHub
gh auth login

# Verify authentication
gh auth status

# Check admin permissions on target repo
gh api repos/rysweet/amplihack | jq '.permissions.admin'
# Must return: true
```

⚠️ **SAFETY CHECK: Verify Repository Before Proceeding**

Before applying branch protection, confirm you're targeting the correct repository:

```bash
# 1. Verify current repository context
gh repo view
# Check: Owner, name, default branch

# 2. Confirm this is the repo you intend to protect
echo "About to protect: rysweet/amplihack"
echo "Continue? (Press Ctrl+C to abort, Enter to continue)"
read

# 3. Double-check branch name
gh api repos/rysweet/amplihack/branches | jq '.[].name'
# Verify 'main' exists before protecting it
```

**Why this matters:**
- Branch protection is **immediate and destructive** - no undo button
- Wrong repository = potentially blocking an entire team's workflow
- Wrong branch name = protection won't apply where intended
- 5 seconds of verification > hours of emergency fixes

### Step 2: View Current Protection Status

```bash
# Check if protection already exists
gh api repos/rysweet/amplihack/branches/main/protection 2>&1

# If protected, view current settings
gh api repos/rysweet/amplihack/branches/main/protection | jq '.'

# If not protected, you'll see:
# "Branch not protected"
```

### Step 3: Discover Your CI Check Names

**Critical**: You must use the exact check names from your workflows.

```bash
# Method 1: Search workflow files
grep -A 2 "^name:" .github/workflows/*.yml

# Method 2: Check recent PR
gh pr checks <PR_NUMBER>

# Method 3: View workflow run
gh run list --limit 5
gh run view <RUN_ID>
```

**Example output** (amplihack):
```
CI / Validate Code
Version Check / Check Version Bump
```

The format is: `{workflow-name} / {job-name}`

### Step 4: Create Protection Configuration

Create `protection-config.json` with your settings:

```json
{
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false,
    "require_last_push_approval": false
  },
  "required_status_checks": {
    "strict": false,
    "contexts": [
      "CI / Validate Code",
      "Version Check / Check Version Bump"
    ]
  },
  "enforce_admins": false,
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": false,
  "lock_branch": false
}
```

**Validate JSON syntax** before applying:
```bash
jq empty protection-config.json
# No output = valid JSON
```

### Step 5: Capture Current State (Audit Trail)

```bash
# Save current state for rollback
gh api repos/rysweet/amplihack/branches/main/protection > before.json 2>&1 || echo "No protection yet"
```

### Step 6: Apply Protection

```bash
# Apply the protection configuration
gh api PUT repos/rysweet/amplihack/branches/main/protection \
  --input protection-config.json

# If successful, you'll see JSON output with the new settings
```

**Common errors**:
- `404 Not Found`: Check repo owner/name spelling
- `403 Forbidden`: You lack admin permissions
- `422 Unprocessable Entity`: Invalid JSON or invalid status check name

### Step 7: Verify Protection Active

```bash
# Verify all settings applied
gh api repos/rysweet/amplihack/branches/main/protection | jq '{
  reviews_required: .required_pull_request_reviews.required_approving_review_count,
  status_checks: .required_status_checks.contexts,
  strict_checks: .required_status_checks.strict,
  enforce_admins: .enforce_admins.enabled,
  force_push_disabled: (.allow_force_pushes.enabled | not),
  deletion_disabled: (.allow_deletions.enabled | not)
}'
```

**Expected output**:
```json
{
  "reviews_required": 1,
  "status_checks": [
    "CI / Validate Code",
    "Version Check / Check Version Bump"
  ],
  "strict_checks": false,
  "enforce_admins": false,
  "force_push_disabled": true,
  "deletion_disabled": true
}
```

### Step 8: Test Protection (Verification)

```bash
# Test 1: Try to push directly to main (should fail)
git checkout main
echo "test" >> test.txt
git add test.txt
git commit -m "test direct push"
git push origin main
# Expected: remote: error: GH006: Protected branch update failed

# Test 2: Try force push (should fail)
git push --force origin main
# Expected: remote: error: GH006: Protected branch update failed

# Clean up test
git reset --hard HEAD~1
```

### Step 9: Clean Up Temporary Files

After applying and verifying protection, remove temporary configuration files:

```bash
# Remove the config file (protection is now server-side)
rm -f protection-config.json

# Remove audit trail files (optional - keep if you want rollback reference)
rm -f before.json

# These files are temporary and should NOT be committed to version control
# Protection configuration is stored on GitHub's servers, not in your repository
```

**Why clean up?**
- Config files are **one-time use only** - protection is stored on GitHub
- Leaving them creates confusion about the source of truth
- Files may contain security settings that shouldn't be in version control
- Clean repository = clear that protection is server-side, not file-based

**When to keep files:**
- `before.json`: Keep temporarily if you might need to rollback
- After confirming protection works, delete all temporary files

---

## Method 2: GitHub UI Walkthrough

### Navigate to Branch Protection Settings

1. **Open your repository** in a web browser: `https://github.com/{owner}/{repo}`

2. **Navigate to Settings**:
   - Click **Settings** tab (requires admin access)
   - If you don't see Settings, you lack admin permissions

3. **Access Branch Protection**:
   - In left sidebar, click **Branches** (under "Code and automation")
   - Find **Branch protection rules** section
   - Click **Add branch protection rule** button

4. **Specify Branch Name**:
   - In "Branch name pattern" field, enter: `main`
   - This creates a rule specifically for the `main` branch

### Configure Protection Settings

#### Setting 1: Require Pull Request Before Merging

5. **Enable PR requirement**:
   - ✅ Check **Require a pull request before merging**
   - This forces all changes through PR workflow

6. **Configure review requirements**:
   - ✅ Check **Require approvals**
   - Set **Required number of approvals before merging**: `1`
   - ⬜ Leave **Dismiss stale pull request approvals** unchecked (optional)
   - ⬜ Leave **Require review from Code Owners** unchecked (unless you use CODEOWNERS)
   - ⬜ Leave **Require approval of the most recent reviewable push** unchecked

#### Setting 2: Require Status Checks to Pass

7. **Enable status checks**:
   - ✅ Check **Require status checks to pass before merging**
   - A search box appears: "Search for status checks in the last week for this repository"

8. **Select status checks**:
   - ⬜ Leave **Require branches to be up to date before merging** unchecked (unless you want strict mode)
   - In the search box, type your CI check name (e.g., `CI / Validate Code`)
   - Click the check name when it appears to add it
   - Repeat for additional checks (e.g., `Version Check / Check Version Bump`)

   **If no checks appear**: Your workflows haven't run yet. Run your CI at least once, then return to add checks.

#### Setting 3: Additional Protections

9. **Prevent force pushes**:
   - Scroll to **Rules applied to everyone including administrators**
   - ✅ Check **Do not allow force pushes**
   - This prevents history rewriting on main

10. **Prevent deletion**:
    - ✅ Check **Do not allow deletions**
    - This prevents accidental branch deletion

11. **Enforce for administrators** (optional):
    - ⬜ Leave **Do not allow bypassing the above settings** unchecked
    - Recommended: Leave unchecked so admins can handle emergencies
    - If checked, even repository admins must follow all rules

### Save Configuration

12. **Review your settings**:
    - Scroll through the form to verify all checkboxes
    - Ensure status checks are listed under "Status checks that are required"

13. **Save protection rule**:
    - Click **Create** button at bottom of page
    - GitHub applies the rules immediately

### Verify in UI

14. **Confirm protection active**:
    - Go to **Code** tab
    - Look for branch dropdown above file list
    - You should see a small shield icon 🛡️ next to `main`
    - Hover over shield to see "Branch is protected"

15. **View protection details**:
    - Return to **Settings > Branches**
    - Your `main` rule now appears under "Branch protection rules"
    - Click **Edit** to review settings anytime

---

## Protection Settings Explained

### 1. Require Pull Request Before Merging

**What it does**: Prevents direct pushes to `main`. All changes must go through a pull request.

**Why important**: Enforces code review workflow, creates audit trail, enables discussion.

**Trade-offs**:
- ✅ Forces visibility and collaboration
- ✅ Creates merge history for auditing
- ❌ Prevents quick hotfixes via direct push
- ❌ Adds overhead for solo developers

**Configuration options**:
- `required_approving_review_count`: Number of approvals needed (recommend: 1)
- `dismiss_stale_reviews`: Reset approvals when new commits pushed (recommend: false)
- `require_code_owner_reviews`: Require approval from CODEOWNERS (optional)

### 2. Require Status Checks to Pass

**What it does**: Blocks PR merge until specified CI checks pass (green ✓).

**Why important**: Prevents merging broken code, enforces quality gates, automates validation.

**Trade-offs**:
- ✅ Guarantees CI passed before merge
- ✅ Catches test failures automatically
- ❌ Cannot merge if CI is broken (even for hotfixes)
- ❌ Can create merge bottlenecks on busy repos

**Configuration options**:
- `contexts`: Array of exact check names (e.g., `["CI / Validate Code"]`)
- `strict`: If `true`, branch must be up-to-date with base before merge
  - `strict: true` → Forces rebase dance on active repos (annoying but safer)
  - `strict: false` → Allows merge even if behind (faster but riskier)

**How to find check names**:
```bash
# From workflow files
grep "name:" .github/workflows/*.yml

# From recent PR
gh pr checks <PR_NUMBER>

# Format: "{workflow-name} / {job-name}"
```

**Critical**: Invalid check names pass validation but PRs will never be mergeable (waiting forever for non-existent check).

### 3. Prevent Force Push

**What it does**: Blocks `git push --force` and `git push --force-with-lease` to protected branch.

**Why important**: Prevents history rewriting, protects other developers' work, maintains audit trail.

**Trade-offs**:
- ✅ Guarantees immutable history on main
- ✅ Prevents accidental overwrites
- ❌ Cannot fix mistakes by rewriting main history
- ❌ Cannot squash commits after merge

**When to disable**: Almost never. Use `git revert` instead of rewriting history.

### 4. Prevent Deletion

**What it does**: Blocks `git push --delete` for protected branch.

**Why important**: Prevents accidental deletion of critical branch.

**Trade-offs**:
- ✅ Protects against `git push origin :main` accidents
- ✅ Prevents malicious branch deletion
- ❌ Cannot delete and recreate main (rarely needed)

**When to disable**: Almost never for `main` branch.

### 5. Enforce Admins (Optional, Use with Caution)

**What it does**: If enabled, repository administrators **must** follow all protection rules.

**Why important**: Ensures consistency, prevents privilege abuse.

**⚠️ Trade-offs**:
- ✅ Guarantees even admins follow review process
- ✅ Prevents emergency hotfix temptation
- ❌ **Can lock you out during CI failures**
- ❌ Prevents emergency overrides in outages
- ❌ Makes initial setup harder (catch-22)

**Recommendation**: 
- **Small teams / open source**: Set to `false` (allow admin flexibility)
- **Large teams / compliance-required**: Set to `true` (enforce consistency)
- **amplihack**: Uses `false` to allow repo owners setup flexibility

### 6. Strict Status Checks (Optional)

**What it does**: If enabled, branch must be up-to-date with base branch before merging.

**Why important**: Prevents "merge train" problems where multiple PRs pass CI individually but break when combined.

**Trade-offs**:
- ✅ Guarantees merged code tested against latest main
- ✅ Prevents integration bugs
- ❌ **Forces constant rebasing on active repos** (merge-rebase-merge-rebase cycle)
- ❌ Slows down development velocity significantly
- ❌ Frustrating for contributors (PR keeps falling behind)

**Recommendation**:
- **Active repos with many contributors**: `strict: false` (avoid rebase dance)
- **Low-traffic repos**: `strict: true` (extra safety with minimal friction)
- **amplihack**: Uses `false` to prioritize velocity

---

## Verification Commands

After applying protection, verify settings are active and working:

### Verify Configuration Applied

```bash
# View all protection settings
gh api repos/{owner}/{repo}/branches/main/protection | jq '.'

# View specific settings (formatted)
gh api repos/{owner}/{repo}/branches/main/protection | jq '{
  pr_reviews: {
    required_count: .required_pull_request_reviews.required_approving_review_count,
    dismiss_stale: .required_pull_request_reviews.dismiss_stale_reviews,
    code_owners: .required_pull_request_reviews.require_code_owner_reviews
  },
  status_checks: {
    strict: .required_status_checks.strict,
    contexts: .required_status_checks.contexts
  },
  enforce_admins: .enforce_admins.enabled,
  allow_force_pushes: .allow_force_pushes.enabled,
  allow_deletions: .allow_deletions.enabled
}'
```

### Test Direct Push Prevention

```bash
# Create a test branch
git checkout -b test-protection

# Make a change
echo "test" >> test.txt
git add test.txt
git commit -m "test direct push prevention"

# Try to push directly to main (should fail)
git push origin HEAD:main

# Expected output:
# remote: error: GH006: Protected branch update failed for refs/heads/main.
# remote: error: Required status check "CI / Validate Code" is expected.
# To github.com:{owner}/{repo}.git
#  ! [remote rejected] HEAD -> main (protected branch hook declined)
```

### Test Force Push Prevention

```bash
# Try to force push (should fail)
git push --force origin HEAD:main

# Expected output:
# remote: error: GH006: Protected branch update failed for refs/heads/main.
# To github.com:{owner}/{repo}.git
#  ! [remote rejected] HEAD -> main (protected branch hook declined)
```

### Test PR Workflow (Success Case)

```bash
# Push to feature branch (should succeed)
git push origin test-protection

# Create PR
gh pr create --base main --head test-protection --title "Test PR" --body "Testing protection"

# Check PR status
gh pr checks

# Merge via GitHub UI or CLI (after approval + CI passes)
gh pr merge --squash --delete-branch
```

### Verify Protection Visible in UI

```bash
# Open repo in browser
gh repo view --web

# Should see shield icon 🛡️ next to main branch
# Settings > Branches should show protection rule
```

---

## Working Example: amplihack Repository

This section documents the **actual commands used** to protect the `amplihack` repository's `main` branch.

### Repository Context

- **Repository**: `rysweet/amplihack`
- **Branch**: `main`
- **CI Workflows**: 
  - `.github/workflows/ci.yml` → Check name: `CI / Validate Code`
  - `.github/workflows/version-check.yml` → Check name: `Version Check / Check Version Bump`

### Step-by-Step Application

#### 1. Discovered CI Check Names

```bash
$ grep "^name:" .github/workflows/*.yml
.github/workflows/ci.yml:name: CI
.github/workflows/version-check.yml:name: Version Check

$ gh pr checks 2234
All checks were successful
1 successful check

✓  CI / Validate Code                      1m24s  https://github.com/rysweet/amplihack/...
✓  Version Check / Check Version Bump      35s    https://github.com/rysweet/amplihack/...
```

**Result**: Need to protect checks: `CI / Validate Code` and `Version Check / Check Version Bump`

#### 2. Created Protection Configuration

```bash
$ cat > protection-config.json << 'EOF'
{
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false,
    "require_last_push_approval": false
  },
  "required_status_checks": {
    "strict": false,
    "contexts": [
      "CI / Validate Code",
      "Version Check / Check Version Bump"
    ]
  },
  "enforce_admins": false,
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": false,
  "lock_branch": false
}
EOF

$ jq empty protection-config.json
# (no output = valid JSON)
```

#### 3. Captured Current State

```bash
$ gh api repos/rysweet/amplihack/branches/main/protection > before.json 2>&1
# If not yet protected, before.json will contain error message
```

#### 4. Applied Protection

```bash
$ gh api PUT repos/rysweet/amplihack/branches/main/protection \
  --input protection-config.json

{
  "url": "https://api.github.com/repos/rysweet/amplihack/branches/main/protection",
  "required_status_checks": {
    "url": "https://api.github.com/repos/rysweet/amplihack/branches/main/protection/required_status_checks",
    "strict": false,
    "contexts": [
      "CI / Validate Code",
      "Version Check / Check Version Bump"
    ],
    "contexts_url": "https://api.github.com/repos/rysweet/amplihack/branches/main/protection/required_status_checks/contexts",
    "checks": [
      {
        "context": "CI / Validate Code",
        "app_id": null
      },
      {
        "context": "Version Check / Check Version Bump",
        "app_id": null
      }
    ]
  },
  "required_pull_request_reviews": {
    "url": "https://api.github.com/repos/rysweet/amplihack/branches/main/protection/required_pull_request_reviews",
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1,
    "require_last_push_approval": false
  },
  "enforce_admins": {
    "url": "https://api.github.com/repos/rysweet/amplihack/branches/main/protection/enforce_admins",
    "enabled": false
  },
  "allow_force_pushes": {
    "enabled": false
  },
  "allow_deletions": {
    "enabled": false
  }
}
```

**Success!** Protection applied.

#### 5. Verified Protection Active

```bash
$ gh api repos/rysweet/amplihack/branches/main/protection | jq '{
  reviews_required: .required_pull_request_reviews.required_approving_review_count,
  status_checks: .required_status_checks.contexts,
  strict_checks: .required_status_checks.strict,
  enforce_admins: .enforce_admins.enabled,
  force_push_disabled: (.allow_force_pushes.enabled | not),
  deletion_disabled: (.allow_deletions.enabled | not)
}'

{
  "reviews_required": 1,
  "status_checks": [
    "CI / Validate Code",
    "Version Check / Check Version Bump"
  ],
  "strict_checks": false,
  "enforce_admins": false,
  "force_push_disabled": true,
  "deletion_disabled": true
}
```

**All settings confirmed!** ✅

#### 6. Tested Protection

```bash
# Test: Direct push to main
$ git checkout main
$ echo "test" >> test.txt
$ git add test.txt
$ git commit -m "test: direct push to main"
$ git push origin main

remote: error: GH006: Protected branch update failed for refs/heads/main.
remote: error: Required status check "CI / Validate Code" is expected.
To github.com:rysweet/amplihack.git
 ! [remote rejected] main -> main (protected branch hook declined)
error: failed to push some refs to 'github.com:rysweet/amplihack.git'
```

**Perfect!** Direct push rejected by GitHub. ✅

```bash
# Test: Force push to main
$ git push --force origin main

remote: error: GH006: Protected branch update failed for refs/heads/main.
To github.com:rysweet/amplihack.git
 ! [remote rejected] main -> main (protected branch hook declined)
error: failed to push some refs to 'github.com:rysweet/amplihack.git'
```

**Perfect!** Force push rejected by GitHub. ✅

```bash
# Cleanup
$ git reset --hard HEAD~1
```

### Configuration Rationale for amplihack

| Setting | Value | Rationale |
|---------|-------|-----------|
| **Review count** | 1 | Small team; one reviewer balances oversight with velocity |
| **Dismiss stale reviews** | false | Trust reviewers to re-review if concerned about new changes |
| **Status checks** | CI + Version Check | Core quality gates: tests pass + version bumped |
| **Strict checks** | false | Active repo; avoid rebase dance friction |
| **Enforce admins** | false | Allow repo owner flexibility for setup and emergencies |
| **Force push** | Disabled | Protect commit history integrity |
| **Deletions** | Disabled | Prevent accidental main branch deletion |

---

## Troubleshooting

### Error: "404 Not Found"

**Symptom**: `gh api` returns 404 when accessing branch protection.

**Causes**:
1. Branch doesn't exist yet
2. Repository owner/name typo
3. Not authenticated with correct account

**Solutions**:
```bash
# Verify branch exists
gh api repos/{owner}/{repo}/branches

# Verify repository accessible
gh repo view {owner}/{repo}

# Check authentication
gh auth status

# Verify account has access
gh api user
```

### Error: "403 Forbidden"

**Symptom**: `gh api` returns 403 when applying protection.

**Cause**: You lack admin permissions on the repository.

**Solutions**:
```bash
# Check your permissions
gh api repos/{owner}/{repo} | jq '.permissions'

# Should show: "admin": true

# If false, ask repository owner to grant admin access
```

### Error: "422 Unprocessable Entity"

**Symptom**: `gh api PUT` returns 422 with validation errors.

**Common causes**:
1. **Invalid JSON syntax**
   ```bash
   # Validate JSON
   jq empty protection-config.json
   ```

2. **Invalid status check name**
   ```bash
   # Check names are case-sensitive and exact
   gh pr checks <RECENT_PR_NUMBER>
   ```

3. **Status check never executed**
   - Workflow must run at least once before adding to protection
   - Solution: Run CI, then add check name

4. **Conflicting settings**
   - Example: `restrictions` requires specific push access setup
   - Solution: Set `"restrictions": null` for no restrictions

### PRs Cannot Merge (Waiting Forever)

**Symptom**: PR shows "Waiting for status checks" indefinitely, even after CI runs.

**Cause**: Protected status check name doesn't match actual CI job name.

**Diagnosis**:
```bash
# List protected check names
gh api repos/{owner}/{repo}/branches/main/protection | \
  jq '.required_status_checks.contexts'

# List actual check names from recent PR
gh pr checks <PR_NUMBER>

# Compare: names must match EXACTLY (case-sensitive)
```

**Solution**:
```bash
# Update protection with correct check names
# Edit protection-config.json with exact names
gh api PUT repos/{owner}/{repo}/branches/main/protection \
  --input protection-config.json
```

### Cannot Add Status Check in GitHub UI

**Symptom**: Search box in "Require status checks" shows no results.

**Cause**: Workflow hasn't executed yet, so GitHub doesn't know about the check.

**Solution**:
1. Run your CI workflow at least once:
   ```bash
   # Create and merge a test PR to trigger CI
   git checkout -b test-ci-trigger
   echo "# Test" >> README.md
   git add README.md
   git commit -m "test: trigger CI"
   git push origin test-ci-trigger
   gh pr create --fill
   ```

2. After CI completes, check names appear in GitHub UI search box

3. Return to Settings > Branches and add the checks

### Emergency: Need to Disable Protection

**Symptom**: Protection is blocking critical hotfix and you need emergency access.

**Solution (Admin only)**:
```bash
# Temporarily remove protection
gh api DELETE repos/{owner}/{repo}/branches/main/protection

# Push your hotfix
git push origin main

# Re-apply protection immediately
gh api PUT repos/{owner}/{repo}/branches/main/protection \
  --input protection-config.json
```

**Warning**: Only use in true emergencies. Document incident in commit message.

### How to Update Protection Settings

**Symptom**: Need to add/remove status checks or change review count.

**Solution**: Re-apply protection with updated configuration (PUT replaces all settings):
```bash
# Edit protection-config.json with new settings
nano protection-config.json

# Validate JSON
jq empty protection-config.json

# Re-apply (replaces all settings)
gh api PUT repos/{owner}/{repo}/branches/main/protection \
  --input protection-config.json

# Verify changes
gh api repos/{owner}/{repo}/branches/main/protection | jq '.required_status_checks.contexts'
```

### Settings Not Appearing in GitHub UI

**Symptom**: Applied protection via CLI but UI doesn't show settings.

**Causes**:
1. Browser cache
2. Viewing wrong branch
3. Settings propagation delay (rare)

**Solutions**:
```bash
# Verify via API (source of truth)
gh api repos/{owner}/{repo}/branches/main/protection

# Hard refresh browser: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)

# Check you're viewing correct branch in UI
```

---

## Related Resources

### Official Documentation

- [GitHub Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitHub CLI Manual: `gh api`](https://cli.github.com/manual/gh_api)
- [GitHub REST API: Branch Protection](https://docs.github.com/en/rest/branches/branch-protection)

### amplihack Documentation

- **Client-side hook**: `docs/features/main-branch-protection.md`
  - Documents `.git/hooks/pre-commit` (Layer 1)
  - Explains agent hook `pre_tool_use.py` (Layer 2)
  - References this skill for Layer 3

- **Related skills**:
  - `github-copilot-cli`: GitHub CLI usage and authentication
  - `creating-pull-requests`: PR workflow and best practices

### GitHub API Endpoints Used

```bash
# View branch protection
GET /repos/{owner}/{repo}/branches/{branch}/protection

# Apply/update protection
PUT /repos/{owner}/{repo}/branches/{branch}/protection

# Remove protection (emergency only)
DELETE /repos/{owner}/{repo}/branches/{branch}/protection

# List branches
GET /repos/{owner}/{repo}/branches
```

---

## Summary Checklist

Use this checklist when protecting a branch:

- [ ] **Prerequisites verified**
  - [ ] `gh` CLI installed and authenticated (`gh auth status`)
  - [ ] Admin permissions confirmed (`gh api repos/{owner}/{repo} | jq .permissions.admin`)
  - [ ] CI workflows configured and executed at least once

- [ ] **Configuration prepared**
  - [ ] Discovered exact CI check names (`gh pr checks` or `grep .github/workflows/`)
  - [ ] Created `protection-config.json` with correct settings
  - [ ] Validated JSON syntax (`jq empty protection-config.json`)
  - [ ] Captured current state for audit (`gh api GET > before.json`)

- [ ] **Protection applied**
  - [ ] Applied configuration (`gh api PUT --input protection-config.json`)
  - [ ] Verified all settings active (`gh api GET | jq`)
  - [ ] Captured new state for audit (`gh api GET > after.json`)

- [ ] **Verification completed**
  - [ ] Tested direct push rejection
  - [ ] Tested force push rejection
  - [ ] Tested PR workflow (create, approve, merge)
  - [ ] Verified UI shows shield icon on protected branch

- [ ] **Documentation updated**
  - [ ] Documented actual check names used
  - [ ] Recorded configuration rationale
  - [ ] Noted any troubleshooting discoveries

---

**Congratulations!** Your branch is now protected with server-side enforcement. Combined with client-side and agent-side hooks, you have complete defense-in-depth protection for your critical branches.
