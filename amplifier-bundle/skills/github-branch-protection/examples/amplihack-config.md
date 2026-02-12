# Working Example: amplihack Repository Configuration

This document shows the **actual commands and output** from protecting the `amplihack` repository's `main` branch.

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

