# GitHub CLI Walkthrough - Branch Protection

This guide provides step-by-step instructions for configuring GitHub branch protection using the `gh` CLI tool.

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

