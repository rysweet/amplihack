# Branch Protection Settings Reference

Comprehensive explanation of all branch protection settings, their purpose, trade-offs, and recommended configurations.

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
