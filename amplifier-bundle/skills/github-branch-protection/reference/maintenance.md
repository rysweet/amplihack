# Maintenance Guide - Branch Protection Skill

How to keep this skill up-to-date as GitHub's API and features evolve.

## When to Update This Skill

Update this skill when:

1. **GitHub changes the branch protection API**
   - Monitor: https://github.blog/ for API announcements
   - Monitor: https://docs.github.com/en/rest/branches/branch-protection/changelog

2. **New protection settings become available**
   - Example: New security features like "Require deployments to succeed"
   - Example: New workflow requirement options

3. **GitHub CLI (`gh`) introduces new branch protection commands**
   - Monitor: https://github.com/cli/cli/releases
   - Test: `gh api --help` for new options

4. **GitHub UI changes significantly**
   - Settings page reorganization
   - New UI elements or workflows

5. **User feedback identifies gaps or errors**
   - Troubleshooting section needs new entries
   - Commands produce unexpected output

## How to Update This Skill

### Step 1: Verify Current State

```bash
# Test the current skill instructions
gh auth login
gh api repos/test-org/test-repo/branches/main/protection

# Verify examples still work
# Follow cli-walkthrough.md step-by-step
```

### Step 2: Identify What Changed

Compare:
- Current API documentation: https://docs.github.com/en/rest/branches/branch-protection
- Current GitHub UI: Settings > Branches in any repository
- Previous version of this skill (check git history)

### Step 3: Update Relevant Files

| File | What to Update |
|------|----------------|
| `SKILL.md` | Only if core workflow changes (keep under 1000 words!) |
| `reference/cli-walkthrough.md` | New `gh` commands or API endpoints |
| `reference/ui-walkthrough.md` | UI changes, new buttons/fields |
| `reference/settings-reference.md` | New protection settings or options |
| `reference/troubleshooting.md` | New error messages or solutions |
| `examples/amplihack-config.md` | If amplihack repo configuration changes |

### Step 4: Update Version and Metadata

Edit `SKILL.md` frontmatter:

```yaml
---
name: github-branch-protection
version: 2.1.0  # Bump appropriately (see versioning guide below)
last_updated: 2026-XX-XX  # Today's date
---
```

### Step 5: Test Changes

```bash
# Test skill loads correctly
# (If using amplihack skill loader)
python -c "from amplihack.skills import load_skill; print(load_skill('github-branch-protection'))"

# Test auto-activation keywords still work
# Try: "I want to protect my main branch"

# Test all commands in cli-walkthrough.md on a test repository
# Test UI walkthrough on a test repository
```

### Step 6: Update Examples

If API or settings change, update `examples/amplihack-config.md`:

```bash
# Re-run the protection configuration
# Capture new output
# Update examples/amplihack-config.md with actual current output
```

## Versioning Guide

Use semantic versioning:

- **Major (3.0.0)**: Breaking changes
  - API endpoints changed (old commands no longer work)
  - Required settings added/removed
  - Workflow fundamentally different

- **Minor (2.1.0)**: New features, backward-compatible
  - New protection settings added
  - New troubleshooting entries
  - Enhanced examples
  - New sections in reference docs

- **Patch (2.0.1)**: Bug fixes, clarifications
  - Typo corrections
  - Clearer wording
  - Updated error messages
  - Fixed examples

## External Links to Monitor

Update these links if they change:

### GitHub Official Documentation
- Main docs: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches
- API reference: https://docs.github.com/en/rest/branches/branch-protection
- `gh` CLI manual: https://cli.github.com/manual/gh_api

### Test These Links Quarterly
```bash
# Verify all external links are still valid
curl -I https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
curl -I https://docs.github.com/en/rest/branches/branch-protection
```

If a link returns 404, find the new URL and update all references.

## Progressive Disclosure Compliance

This skill follows Anthropic's progressive disclosure architecture:

- **Level 1 (Metadata)**: SKILL.md frontmatter (~30 tokens)
- **Level 2 (Main guidance)**: SKILL.md body (~450 words, loaded when activated)
- **Level 3 (Deep reference)**: reference/*.md files (loaded only when linked/needed)

**When updating, maintain this structure:**

- Keep SKILL.md concise (~50 lines main content, <1000 words total)
- Move detailed content to reference/ directory
- Link from SKILL.md to reference files
- Examples go in examples/ directory

## Changelog Template

When making updates, document them in git commit messages:

```
feat(skill): update github-branch-protection for new API v2024-02

- Updated cli-walkthrough.md for new `gh protection` subcommand
- Added troubleshooting entry for new "Require deployments" setting
- Updated settings-reference.md with deployment protection details
- Bumped version to 2.1.0

Refs: https://github.blog/changelog/2024-02-branch-protection-api-v2
```

## Testing Checklist

Before marking an update as complete:

- [ ] All `gh api` commands tested on a real repository
- [ ] UI walkthrough verified in current GitHub interface
- [ ] Examples produce expected output
- [ ] External links return 200 OK
- [ ] Skill file under 1000 words
- [ ] Version bumped appropriately
- [ ] `last_updated` date is current
- [ ] Git commit follows conventional commits format

## Questions or Issues?

If you discover an issue with this skill:

1. Check if it's already in `reference/troubleshooting.md`
2. Test the issue on a clean test repository
3. Document the issue with exact commands and error messages
4. Add to troubleshooting or create a GitHub issue
5. Update the skill with the fix and bump version

---

**Last maintenance check**: 2026-02-12  
**Next recommended check**: 2026-05-12 (quarterly)
