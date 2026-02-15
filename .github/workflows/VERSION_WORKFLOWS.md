# Version Management Workflows

This document explains the automated version management system for the amplihack repository.

## Overview

The repository uses a multi-layer approach to ensure that every merge to `main` increments the version number:

1. **PR-level auto-fix** (optional): `version-check.yml`
2. **Merge-level auto-bump** (safety net): `auto-version-on-merge.yml`
3. **Auto-tagging**: `version-tag.yml`

## Workflows

### 1. Version Check (version-check.yml)

**Trigger**: On pull request to `main`

**Purpose**: Encourage version bumping during PR development

**Behavior**:
- Checks if the PR has bumped the version compared to `main`
- If not bumped, automatically commits a patch version bump to the PR branch
- Comments on the PR to notify the author
- Allows manual override for minor/major version bumps

**Note**: This is a convenience feature to help developers remember to bump versions. Even if skipped, the merge-level workflow (below) will ensure version is bumped.

### 2. Auto Version on Merge (auto-version-on-merge.yml)

**Trigger**: On push to `main` (after merge)

**Purpose**: **Safety net** - Ensures version is ALWAYS incremented on merge

**Behavior**:
- Runs immediately after code is merged to `main`
- Checks if the merge included a version bump
- If version was NOT bumped, automatically increments patch version
- Commits the version bump directly to `main` with `[skip ci]` to avoid recursion

**Key Features**:
- Idempotent: Won't double-bump if version was already incremented
- Handles edge cases: First commit, manual bumps, etc.
- Uses `[skip ci]` flag to prevent triggering itself recursively

### 3. Auto Tag Version (version-tag.yml)

**Trigger**: 
- On push to `main` 
- After `auto-version-on-merge.yml` completes

**Purpose**: Create git tags and GitHub releases for each version

**Behavior**:
- Extracts version from `pyproject.toml`
- Creates an annotated git tag (e.g., `v0.5.8`)
- Creates a GitHub release with auto-generated notes
- Skips if tag already exists

## Version Bumping Logic

### Semantic Versioning

The repository follows [Semantic Versioning](https://semver.org/):

- **Patch** (0.5.7 → 0.5.8): Bug fixes, no API changes
- **Minor** (0.5.7 → 0.6.0): New features, backward-compatible
- **Major** (0.5.7 → 1.0.0): Breaking changes

### Automatic Bumping

By default, all automated bumps use **patch** version increments.

### Manual Version Bumps

To manually bump to a specific version:

1. Edit the `version` field in `pyproject.toml` to your desired version
2. Commit and push to your PR branch
3. The workflows will detect the manual bump and skip auto-bumping

**Examples**:

```bash
# For a minor version bump (new feature)
# Change: version = "0.5.7"
# To:     version = "0.6.0"

# For a major version bump (breaking change)
# Change: version = "0.5.7"
# To:     version = "1.0.0"
```

## Workflow Sequence

### Normal Merge Flow

```
1. Developer creates PR
2. version-check.yml runs
   ├─ If version bumped: ✅ Pass
   └─ If not bumped: Auto-bump patch in PR
3. PR merged to main
4. auto-version-on-merge.yml runs
   ├─ Check if version bumped in merge
   ├─ If yes: Skip (version already bumped)
   └─ If no: Auto-bump patch and commit to main
5. version-tag.yml runs
   └─ Create tag and GitHub release
```

### Developer Manual Bump Flow

```
1. Developer creates PR with manual version bump (e.g., 0.5.7 → 0.6.0)
2. version-check.yml runs
   └─ ✅ Detects version bump, passes
3. PR merged to main
4. auto-version-on-merge.yml runs
   └─ ✅ Detects version bump, skips auto-bump
5. version-tag.yml runs
   └─ Create tag v0.6.0 and GitHub release
```

## Key Design Decisions

### Why Both PR-level and Merge-level Workflows?

1. **PR-level** (`version-check.yml`): 
   - Developer convenience
   - Immediate feedback
   - Allows manual override before merge

2. **Merge-level** (`auto-version-on-merge.yml`):
   - Safety net - ensures version is ALWAYS bumped
   - Handles edge cases (direct pushes, bypassed checks, etc.)
   - Guarantees monotonically increasing versions

### Why `[skip ci]` in Auto-Bump Commit?

The `[skip ci]` flag prevents infinite recursion:
- Without it: version bump → triggers push → triggers workflow → version bump → ...
- With it: version bump → triggers push (skips workflows) → end

### Why `workflow_run` Trigger for Tagging?

The `version-tag.yml` uses both `push` and `workflow_run` triggers to ensure it runs after version bumping:
- If version was already bumped in PR → runs immediately on merge via `push` trigger
- If version was auto-bumped on merge → runs after auto-version-on-merge completes via `workflow_run` trigger

## Scripts

### check_version_bump.py

Compares version in PR branch vs. main branch.

**Exit Codes**:
- `0`: Version properly bumped
- `1`: Version not bumped or invalid

### auto_bump_version.py

Automatically increments patch version in `pyproject.toml`.

**Logic**:
```python
# Input:  version = "0.5.7"
# Output: version = "0.5.8"
```

### get_version.py

Extracts version string from `pyproject.toml`.

**Usage**:
```bash
# Read from default location (pyproject.toml)
python scripts/get_version.py

# Read from specific file
python scripts/get_version.py path/to/file.toml

# Read from stdin
cat file.toml | python scripts/get_version.py -
```

**Exit Codes**:
- `0`: Success, version printed to stdout
- `1`: Error (file not found or version not found)

**Used by**: All version-related workflows to eliminate code duplication.

## Testing

To test the workflows locally:

```bash
# Test version extraction
python scripts/get_version.py

# Test version check script
python scripts/check_version_bump.py

# Test auto-bump script
python scripts/auto_bump_version.py

# Verify version in pyproject.toml
grep "^version = " pyproject.toml
```

## Troubleshooting

### Version wasn't bumped after merge

Check the workflow run logs:
1. Go to Actions → Auto Version on Merge
2. Look for the "Check and Auto-Bump Version" job
3. Review the summary to see what happened

### Tag wasn't created

Check the workflow run logs:
1. Go to Actions → Auto Tag Version
2. Check if tag already exists or if there was an error

### How to force a specific version

1. Manually edit `pyproject.toml` with your desired version
2. Commit directly to `main` (if you have permissions) or via PR
3. The workflows will respect your manual version and skip auto-bumping

## Future Enhancements

Potential improvements:
- Support for pre-release versions (alpha, beta, rc)
- Configurable bump strategy (via labels like `bump:minor`, `bump:major`)
- Automatic changelog generation based on commits
- Version bump based on conventional commits
