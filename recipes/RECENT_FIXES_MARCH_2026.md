# Recent Recipe Runner & Skills Fixes - March 2026

This document tracks recent bug fixes and improvements to the Recipe Runner and Skills systems following the Diátaxis framework.

## Recipe Runner Fixes

### Recipe Discovery from Installed Packages (PR #2813)

**Problem**: Recipe discovery failed when amplihack was pip-installed and users ran commands from directories outside the amplihack repository.

**Root Cause**: `discover_recipes()` used only CWD-relative paths:
- `Path("amplifier-bundle") / "recipes"` — relative to current directory
- `Path("src") / "amplihack" / "amplifier-bundle" / "recipes"` — also CWD-relative

Neither path resolved to the installed package location (`site-packages/amplihack/amplifier-bundle/recipes/`).

**Solution**: Added two absolute paths resolved via `Path(__file__)`:
1. `_PACKAGE_BUNDLE_DIR` — installed package's bundled recipes (wheel installs)
2. `_REPO_ROOT_BUNDLE_DIR` — repo root's bundle dir (editable installs)

**Impact**:
- All 16 bundled recipes now discoverable from any working directory
- Works correctly after `pip install amplihack`
- Verified: `cd /tmp && python -c 'from amplihack.recipes import list_recipes; print(len(list_recipes()))'` → 16 recipes (was 0)

**Tests Added**:
- `test_discovers_from_installed_package_path`: Verifies discovery works from temp directory
- `test_package_bundle_dir_is_absolute`: Ensures package path is absolute, not CWD-relative

**Documentation Updated**:
- [Recipe Discovery](./README.md#recipe-discovery)
- [Recipe Discovery Troubleshooting](./recipe-discovery-troubleshooting.md)

### Bash Step Timeout Removal (PR #2807)

**Problem**: Bash steps had hardcoded 120-second timeout that killed long-running operations silently.

**Root Cause**: All bash steps defaulted to `timeout=120` in 6 files:
- `models.py` (step model)
- `parser.py` (YAML parser)
- `adapters/base.py`, `adapters/cli_subprocess.py`, `adapters/nested_session.py`, `adapters/claude_sdk.py`

**Solution**: Changed all `timeout: int = 120` → `timeout: int | None = None`

**Impact**:
- Bash steps now have no timeout by default (same as agent steps)
- Recipe authors can still set per-step timeouts in YAML if needed
- Complex operations (Python helpers, git operations) no longer killed prematurely

**Example Usage**:
```yaml
steps:
  - id: run-tests
    type: bash
    command: "pytest tests/"
    timeout: 300  # Optional: 5-minute timeout

  - id: git-rebase
    type: bash
    command: "git rebase origin/main"
    # No timeout = runs until completion
```

**Documentation Updated**:
- [Recipe YAML Format](./README.md#bash-step-timeouts)

### Recipe Runner Adapter Auto-Detection (PR #2804)

**Problem**: Smart-orchestrator recipe hardcoded `ClaudeSDKAdapter()` which used wrong async API.

**Root Cause**: Dev-orchestrator skill doc called `ClaudeSDKAdapter()` directly instead of using adapter auto-detection.

**Solution**: Changed to `get_adapter()` which auto-selects `NestedSessionAdapter` when `CLAUDECODE` env is set.

**Impact**:
- Recipe runner works correctly inside Claude Code sessions
- Adapter selection now context-aware
- All 20 smart-orchestrator steps complete successfully

**Additional Fixes in Same PR**:
1. **Bash heredoc quoting** (#2764): Template variables like `{{decomposition_json}}` broke bash when Claude's output contained single quotes. Fixed using `<<'EOFDECOMP'` (quoted delimiter prevents special char interpretation).

2. **Condition expression eval**: Conditions used `int(str(workstream_count).strip() or '1')` which safe evaluator rejects. Fixed to simple string comparison: `workstream_count == '1'`.

3. **Stdout pollution**: Removed box-drawing warning message that corrupted downstream template variables.

**Verification**:
```
classify-and-decompose: COMPLETED
parse-decomposition: COMPLETED
activate-workflow: COMPLETED
setup-session: COMPLETED
execute-single-round-1: COMPLETED
reflect-round-1: COMPLETED
reflect-final: COMPLETED
summarize: COMPLETED
complete-session: COMPLETED
```

**Documentation Updated**:
- [SDK Adapters Guide](../SDK_ADAPTERS_GUIDE.md)

## Skills System Fixes

### Skill Frontmatter Validation (PR #2811)

**Problem**: 12 skills failed to load with "missing or malformed YAML frontmatter" errors. Each skill appeared 3× (from `.claude/skills/`, `.github/skills/`, `~/.copilot/skills/`).

**Affected Skills**:
- `azure-admin`, `azure-devops-cli`, `github`, `silent-degradation-audit`

**Root Causes**:

| Skill | Issue | Fix |
|---|---|---|
| `azure-admin` | Metadata in ````yaml` code block, no frontmatter | Replaced with proper `---` frontmatter |
| `azure-devops-cli` | Title before frontmatter, HTML comments in YAML | Moved frontmatter to file start, cleaned YAML |
| `github` | Same as azure-devops-cli | Same fix |
| `silent-degradation-audit` | No frontmatter at all | Added `---` frontmatter with name + description |

**Solution**:
1. Fixed YAML frontmatter in all 4 skills
2. Removed duplicate `.github/skills` symlink (was symlink to `../.claude/skills`)

**Impact**:
- All skills now load correctly without duplicates
- Skill loading reduced from 3× to 2× per skill
- Verified via `yaml.safe_load()` parsing

**YAML Frontmatter Requirements** (documented):
1. Start at **first line** of SKILL.md (no title or content before `---`)
2. Use proper `---` delimiters (not code blocks)
3. No HTML comments within YAML section
4. Minimum fields: `name` and `description`

**Documentation Updated**:
- [Skill Catalog](../skills/SKILL_CATALOG.md#yaml-frontmatter-requirements)

## Version History

All fixes released in **amplihack v0.9.0** (March 2026):

- **Recipe Discovery** (PR #2813) - Installed package path support
- **Bash Timeouts** (PR #2807) - Removed hardcoded 120s limit
- **Adapter Selection** (PR #2804) - Auto-detection for Claude Code
- **Skill Frontmatter** (PR #2811) - Fixed YAML validation issues

## See Also

- [Recipe Runner Documentation](./README.md)
- [Recipe Discovery Troubleshooting](./recipe-discovery-troubleshooting.md)
- [Skill Catalog](../skills/SKILL_CATALOG.md)
- [SDK Adapters Guide](../SDK_ADAPTERS_GUIDE.md)
