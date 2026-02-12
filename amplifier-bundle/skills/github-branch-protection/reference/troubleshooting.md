# Troubleshooting Guide - Branch Protection

Common errors and solutions when configuring GitHub branch protection.

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

