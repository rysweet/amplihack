# Answer: Auto-Increment Version on Merge

## Question
> @copilot - is there a way to make the version bump ci check auto update the version to a number that is always incremental on merge?

## Answer: YES! ✅

This has been implemented with a new workflow system that guarantees version is always incremented on merge.

## How It Works

### Two-Layer Approach

1. **PR-Level Auto-Fix** (Convenience)
   - `version-check.yml` runs when you open a PR
   - If you forgot to bump version, it auto-bumps patch version in your PR
   - You can still manually override for minor/major bumps

2. **Merge-Level Auto-Bump** (Safety Net) - **NEW!**
   - `auto-version-on-merge.yml` runs when PR is merged to main
   - Checks if the merge included a version bump
   - If NOT bumped → auto-increments patch version and commits to main
   - If already bumped → does nothing (idempotent)

### Result

**Every merge to `main` ALWAYS increments the version**, regardless of whether:
- The developer remembered to bump it
- The PR auto-fix ran successfully  
- Someone manually bumped to a specific version

## Example Flows

### Flow 1: Developer Forgets Version Bump

```
1. Developer creates PR without version bump
2. PR auto-fix bumps patch version in PR (0.5.7 → 0.5.8)
3. PR merged to main
4. Merge auto-bump sees version already bumped → skips
5. Tag created: v0.5.8 ✅
```

### Flow 2: PR Auto-Fix Disabled/Skipped

```
1. Developer creates PR without version bump
2. PR auto-fix somehow doesn't run or is skipped
3. PR merged to main (version still 0.5.7)
4. Merge auto-bump detects no bump → bumps to 0.5.8
5. Tag created: v0.5.8 ✅
```

### Flow 3: Developer Manually Bumps to Major Version

```
1. Developer creates PR and manually bumps 0.5.7 → 1.0.0
2. PR auto-fix sees version bump → skips
3. PR merged to main
4. Merge auto-bump sees version bumped → skips
5. Tag created: v1.0.0 ✅
```

## Files Changed

### New Files

1. **`.github/workflows/auto-version-on-merge.yml`**
   - New workflow that runs on push to main
   - Automatically bumps version if not already done
   - Commits with `[skip ci]` to prevent recursion

2. **`.github/workflows/VERSION_WORKFLOWS.md`**
   - Comprehensive documentation of the version management system
   - Explains all three workflows and how they interact
   - Troubleshooting guide

### Modified Files

1. **`.github/workflows/version-check.yml`**
   - Updated comments to clarify it's a convenience feature
   - Works with new merge-level workflow

2. **`.github/workflows/version-tag.yml`**
   - Updated to run after auto-version-on-merge completes
   - Uses `workflow_run` trigger for proper sequencing

## Key Features

✅ **Guaranteed Increment**: Version ALWAYS bumps on merge  
✅ **Idempotent**: Won't double-bump if already incremented  
✅ **No Recursion**: Uses `[skip ci]` flag to prevent loops  
✅ **Manual Override**: Supports manual minor/major bumps  
✅ **Git Tags**: Auto-creates tags and GitHub releases  
✅ **Safe**: Two-layer approach ensures no version is skipped

## Testing

The implementation includes comprehensive tests:
- ✅ Version parsing logic
- ✅ Version comparison logic  
- ✅ Auto-bump logic
- ✅ Skip CI pattern validation
- ✅ Workflow simulation with git operations
- ✅ Edge cases (first commit, manual bumps, etc.)

All tests pass successfully.

## Usage

### For Developers

**You don't need to do anything!** The system handles version bumping automatically:

1. Create your PR with your changes
2. If you forget to bump version → auto-fixed in PR
3. Merge when ready
4. Version guaranteed to increment on merge
5. Git tag automatically created

### For Manual Version Bumps

If you need a specific version (not just patch):

```bash
# Edit the version field in pyproject.toml
version = "0.6.0"  # or "1.0.0" for major

# Commit and push
git add pyproject.toml
git commit -m "chore: Bump to 0.6.0"
git push
```

The workflows will detect your manual bump and respect it.

## Documentation

See `.github/workflows/VERSION_WORKFLOWS.md` for complete documentation including:
- Detailed workflow descriptions
- Sequence diagrams
- Troubleshooting guide
- Design decisions and rationale

## Summary

**Yes**, the version bump CI check now auto-updates the version to always be incremental on merge! 

The new `auto-version-on-merge.yml` workflow is a safety net that runs after every merge to `main`, ensuring the version is ALWAYS bumped even if the PR-level check was skipped or failed. This guarantees monotonically increasing version numbers.
