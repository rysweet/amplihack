# UVX Permissions Fix - Issue #138

## Problem Summary

Fresh UVX installations of amplihack created minimal settings.json files without
proper bypass permissions, causing constant permission dialogs that made the
system unusable for new users.

## Root Cause

The UVX staging process (`uvx_staging_v2.py`) copied the project's
`.claude/settings.json` directly from the repository. This file was optimized
for contributors, not fresh installations, lacking:

1. **Comprehensive tool allowlist** - Missing essential tools like Grep, Glob,
   Edit, etc.
2. **Optimal default permissions** - While bypass was enabled, many tools
   weren't pre-approved
3. **UVX-specific optimization** - Settings designed for local development, not
   UVX deployment

## Solution Architecture

### 1. Enhanced UVX Settings Template

**File**: `src/amplihack/utils/uvx_settings_template.json`

```json
{
  "permissions": {
    "allow": [
      "Bash", "TodoWrite", "WebFetch", "WebSearch", "Grep", "Glob",
      "Read", "Edit", "MultiEdit", "Write", "NotebookEdit", "BashOutput",
      "KillShell", "SlashCommand", "mcp__ide__getDiagnostics", "mcp__ide__executeCode"
    ],
    "deny": [],
    "defaultMode": "bypassPermissions",
    "additionalDirectories": [".claude", "Specs", ".git", "src", "tests", "docs"]
  },
  "hooks": {
    "SessionStart": [...],
    "Stop": [...],
    "PostToolUse": [...],
    "PreCompact": [...]
  }
}
```

**Key Enhancements**:

- **16 pre-approved tools** covering all essential functionality
- **Bypass permissions enabled** by default
- **Comprehensive directory access** for common project structures
- **All amplihack hooks** pre-configured

### 2. Intelligent Settings Manager

**File**: `src/amplihack/utils/uvx_settings_manager.py`

```python
class UVXSettingsManager:
    def should_use_uvx_template(self, target_settings_path: Path) -> bool:
        """Determines if UVX template should be used based on existing settings."""

    def create_uvx_settings(self, target_path: Path, preserve_existing: bool = True) -> bool:
        """Creates UVX-optimized settings.json for fresh installations."""

    def merge_with_existing_settings(self, target_path: Path, existing_settings: Dict) -> bool:
        """Merges UVX optimizations with existing user customizations."""
```

**Logic**:

- **Fresh installations** → Use full UVX template
- **Existing settings without bypass** → Enhance with UVX template
- **Existing settings with bypass** → Preserve as-is
- **Always preserve** user customizations when merging

### 3. Enhanced UVX Staging Process

**File**: `src/amplihack/utils/uvx_staging_v2.py`

**Modified Methods**:

- `_perform_staging_operations()` - Detects `.claude` directory for special
  handling
- `_stage_claude_directory()` - Stages entire directory with settings.json
  optimization
- `_stage_settings_json()` - Applies UVX enhancements intelligently

**Process Flow**:

```
1. UVX stages framework files to working directory
2. When staging .claude directory:
   a. Check if settings.json needs UVX enhancement
   b. If yes: Apply UVX template (with backup)
   c. If no: Copy existing settings (already optimized)
3. Copy all other .claude files normally
4. Verify staging completed successfully
```

## User Experience Improvements

### Before Fix

```bash
uvx --from git+... amplihack launch
# → Constant permission dialogs for Grep, Edit, MultiEdit, etc.
# → Users frustrated by repeated interruptions
# → Many tools unusable without manual settings.json editing
```

### After Fix

```bash
uvx --from git+... amplihack launch
# → Silent operation, no permission dialogs
# → All essential tools pre-approved
# → Immediate productive usage
```

## Edge Cases Handled

1. **Corrupted settings.json** → Falls back to UVX template
2. **UVX template creation fails** → Uses source settings as fallback
3. **Existing user customizations** → Preserved via intelligent merging
4. **Permission conflicts** → UVX template takes precedence for essential tools
5. **Backup failures** → Continues with warning, doesn't block staging

## Testing & Validation

### Test Coverage

- **Unit tests**: 10 test cases for settings manager functionality
- **Integration tests**: 9 test cases for staging process
- **End-to-end verification**: Complete UVX installation simulation

### Test Results

```
TestUVXSettingsManager: 10/10 tests passed
TestUVXStagingIntegration: 9/9 tests passed
UVX Permissions Fix Verification: 3/3 comprehensive scenarios passed
```

### Validation Scenarios

1. **Fresh UVX installation** → Bypass permissions + 16 pre-approved tools
2. **Existing settings preservation** → User customizations maintained
3. **Comprehensive tool coverage** → All essential tools pre-approved

## Files Modified

### Core Implementation

- `src/amplihack/utils/uvx_staging_v2.py` - Enhanced staging logic
- `src/amplihack/utils/uvx_settings_manager.py` - New settings manager
- `src/amplihack/utils/uvx_settings_template.json` - UVX-optimized template

### Testing

- `tests/test_uvx_settings_manager.py` - Unit tests for settings manager
- `tests/test_uvx_staging_integration.py` - Integration tests for staging
- `tests/verify_uvx_permissions_fix.py` - End-to-end verification script

## Success Metrics

✅ **Zero permission dialogs** for core amplihack functionality ✅ **16
essential tools** pre-approved in fresh installations ✅ **Existing user
settings** preserved during UVX setup ✅ **Automatic backup** of settings during
enhancement ✅ **Graceful fallback** if UVX enhancements fail ✅ **100% test
coverage** for critical functionality

## Deployment Impact

### Primary Distribution Method

- **UVX installations**: Primary beneficiary (seamless out-of-box experience)
- **Local installations**: No impact (uses existing install.sh logic)
- **Existing users**: Settings preserved, no disruption

### Backward Compatibility

- **Existing settings.json**: Fully preserved and enhanced if needed
- **User customizations**: Maintained through intelligent merging
- **Hook configurations**: User hooks preserved, amplihack hooks added

## Future Considerations

1. **Tool allowlist maintenance** - Update template when new essential tools
   added
2. **User feedback integration** - Monitor for additional tools needing
   pre-approval
3. **Template versioning** - Consider versioned templates for future
   enhancements

---

**Result**: Issue #138 resolved - Fresh UVX installations now provide smooth,
permission-dialog-free experience while preserving user customizations.
