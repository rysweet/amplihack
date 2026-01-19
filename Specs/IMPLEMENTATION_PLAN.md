# Implementation Plan: Issue #1948 Plugin Architecture

## Overview

Complete implementation plan fer th' 6 remainin' gaps in Issue #1948 plugin architecture migration. This plan consolidates all module specifications into a coordinated execution strategy.

## Executive Summary

**Current State (60% Complete):**
- ✅ Plugin infrastructure at `~/.amplihack/.claude/`
- ✅ Plugin manifest (`.claude-plugin/plugin.json`)
- ✅ Hooks using `${CLAUDE_PLUGIN_ROOT}` (4/6-7 hooks verified)
- ✅ PluginManager backend (install, uninstall, validate)
- ✅ LSP auto-detection
- ✅ Settings generator
- ✅ Test coverage (45 tests, 1,084 lines)

**Remaining Gaps (40%):**
1. ❌ CLI command integration (~200 lines, 3-5 hours)
2. ❌ Marketplace configuration (~30 lines, 1-2 hours)
3. ⚠️  Hook registration audit (0-50 lines, 1-2 hours)
4. ❌ Cross-tool compatibility (0 lines code, 7-18 hours research)
5. ❌ Backward compatibility (~300 lines, 4-6 hours)
6. ❌ Documentation updates (~1000 lines docs, 2-3 hours)

**Total Remaining Effort:** 18-36 hours (2.5-4.5 days)

## Implementation Order (Recommended)

### Phase 1: Core Functionality (Priority 1)

**Goal:** Make plugin fully functional fer Claude Code

1. **Hook Registration Audit** (1-2 hours)
   - Spec: `Specs/HOOK_REGISTRATION_AUDIT.md`
   - Verify all hooks in directory are registered
   - Update `hooks.json` with missing hooks
   - Test hook loading

2. **CLI Command Integration** (3-5 hours)
   - Spec: `Specs/PLUGIN_CLI_COMMANDS.md`
   - Implement `plugin install|uninstall|verify` commands
   - Create `cli_handlers.py` and `verifier.py`
   - Wire commands to CLI
   - Test end-to-end workflow

3. **Marketplace Configuration** (1-2 hours)
   - Spec: `Specs/PLUGIN_MARKETPLACE_CONFIG.md`
   - Add marketplace section t' `plugin.json`
   - Update `SettingsGenerator` t' include marketplace
   - Test plugin discoverability

**Phase 1 Total:** 5-9 hours

**Deliverables:**
- ✅ All hooks registered and verified
- ✅ `amplihack plugin` commands working
- ✅ Plugin discoverable in Claude Code `/plugin`

### Phase 2: Compatibility & Migration (Priority 2)

**Goal:** Ensure backward compatibility and research cross-tool support

4. **Backward Compatibility** (4-6 hours)
   - Spec: `Specs/BACKWARD_COMPATIBILITY.md`
   - Implement `ModeDetector` and `MigrationHelper`
   - Add `amplihack mode` commands
   - Test local vs plugin mode detection
   - Test migration workflows

5. **Cross-Tool Compatibility** (7-18 hours)
   - Spec: `Specs/CROSS_TOOL_COMPATIBILITY.md`
   - Research Copilot plugin format (3-6 hours)
   - Research Codex plugin format (3-6 hours)
   - Document compatibility matrix (1-2 hours)
   - Create tool-specific configs if needed (0-4 hours)

**Phase 2 Total:** 11-24 hours

**Deliverables:**
- ✅ Per-project installations still work
- ✅ Migration commands functional
- ✅ Cross-tool compatibility documented

### Phase 3: Documentation (Priority 3)

**Goal:** Provide clear documentation fer users

6. **Documentation Updates** (2-3 hours)
   - Spec: `Specs/DOCUMENTATION_UPDATES.md`
   - Update README.md with plugin installation
   - Update PROJECT.md with architecture
   - Create MIGRATION_GUIDE.md
   - Create PLUGIN_ARCHITECTURE.md
   - Update CHANGELOG.md
   - Update CLI help text

**Phase 3 Total:** 2-3 hours

**Deliverables:**
- ✅ README has plugin installation instructions
- ✅ Migration guide complete
- ✅ Architecture documented

## Detailed Specifications

### Gap 1: CLI Command Integration

**Spec:** `Specs/PLUGIN_CLI_COMMANDS.md`

**Modules:**
- `src/amplihack/plugin_manager/cli_handlers.py` (NEW, ~80 lines)
- `src/amplihack/plugin_manager/verifier.py` (NEW, ~100 lines)
- `src/amplihack/cli.py` (MODIFIED, ~20 lines)

**Commands:**
```bash
amplihack plugin install <source> [--force]
amplihack plugin uninstall <plugin_name>
amplihack plugin verify <plugin_name>
```

**Testing:**
- Unit: 5 test functions
- Integration: 2 test functions
- E2E: 1 workflow test

**Complexity:** Simple (200 lines, 3-5 hours, low risk)

### Gap 2: Marketplace Configuration

**Spec:** `Specs/PLUGIN_MARKETPLACE_CONFIG.md`

**Changes:**
- `.claude-plugin/plugin.json` (MODIFIED, +8 lines)
- `src/amplihack/settings_generator/generator.py` (MODIFIED, +15 lines)
- `src/amplihack/cli.py` (MODIFIED, +7 lines for UVX mode)

**Configuration:**
```json
{
  "marketplace": {
    "name": "amplihack",
    "url": "https://github.com/rysweet/amplihack",
    "type": "github"
  }
}
```

**Testing:**
- Unit: 3 test functions
- Integration: 1 test function

**Complexity:** Simple (30 lines, 1-2 hours, low risk)

### Gap 3: Hook Registration Audit

**Spec:** `Specs/HOOK_REGISTRATION_AUDIT.md`

**Actions:**
1. Read hook files: `pre_tool_use.py`, `user_prompt_submit.py`, `power_steering_checker.py`, `agent_memory_hook.py`
2. Determine which are executable hooks
3. Update `hooks.json` with verified hooks
4. Verify all paths use `${CLAUDE_PLUGIN_ROOT}`

**Configuration:**
- `.claude/tools/amplihack/hooks/hooks.json` (MODIFIED, 0-50 lines)

**Testing:**
- Verification: 3 bash commands
- Runtime: 2 test functions

**Complexity:** Trivial (configuration only, 1-2 hours, low risk)

### Gap 4: Cross-Tool Compatibility

**Spec:** `Specs/CROSS_TOOL_COMPATIBILITY.md`

**Research Questions:**
- Does Copilot support plugins?
- Does Codex support plugins?
- What are manifest format differences?
- Do hooks work across tools?

**Deliverables:**
- `docs/COPILOT_COMPATIBILITY.md` (research findings)
- `docs/CODEX_COMPATIBILITY.md` (research findings)
- Tool-specific configs (if needed)
- Compatibility matrix in README

**Testing:**
- Research-based documentation tests
- Integration tests (if tools support plugins)

**Complexity:** Medium (research-heavy, 7-18 hours, medium risk)

### Gap 5: Backward Compatibility

**Spec:** `Specs/BACKWARD_COMPATIBILITY.md`

**Modules:**
- `src/amplihack/mode_detector/detector.py` (NEW, ~150 lines)
- `src/amplihack/mode_detector/migrator.py` (NEW, ~100 lines)
- `src/amplihack/cli.py` (MODIFIED, ~50 lines)

**Commands:**
```bash
amplihack mode status
amplihack mode migrate-to-plugin
amplihack mode migrate-to-local
```

**Mode Detection:**
```python
LOCAL > PLUGIN > NONE  # Precedence order
```

**Testing:**
- Unit: 5 test functions
- Integration: 2 test functions

**Complexity:** Medium (300 lines, 4-6 hours, medium risk)

### Gap 6: Documentation Updates

**Spec:** `Specs/DOCUMENTATION_UPDATES.md`

**Files:**
1. `README.md` (MODIFIED, installation section)
2. `.claude/context/PROJECT.md` (MODIFIED, architecture section)
3. `docs/MIGRATION_GUIDE.md` (NEW, ~400 lines)
4. `docs/PLUGIN_ARCHITECTURE.md` (NEW, ~500 lines)
5. `CHANGELOG.md` (MODIFIED, +30 lines)
6. CLI help text in `cli.py` (MODIFIED, +50 lines)

**Testing:**
- Documentation tests: 5 test functions

**Complexity:** Simple (documentation only, 2-3 hours, low risk)

## Testing Strategy

### Unit Tests (Add 20 tests)

**New Test Files:**
- `tests/unit/test_cli_handlers.py` (5 tests)
- `tests/unit/test_verifier.py` (3 tests)
- `tests/unit/test_mode_detector.py` (5 tests)
- `tests/unit/test_migrator.py` (3 tests)
- `tests/unit/test_documentation.py` (5 tests)

**Existing Modified:**
- `tests/unit/test_settings_generator.py` (+3 marketplace tests)

### Integration Tests (Add 8 tests)

**New Test Files:**
- `tests/integration/test_plugin_cli_integration.py` (2 tests)
- `tests/integration/test_marketplace_config.py` (1 test)
- `tests/integration/test_mode_migration.py` (2 tests)
- `tests/integration/test_compatibility.py` (3 tests)

### E2E Tests (Add 4 tests)

**Existing Modified:**
- `tests/e2e/test_plugin_manager_e2e.py` (+4 workflow tests)

**Total New Tests:** 32 tests

## Dependencies

### Internal Dependencies

All gaps depend on existing implementation:
- `PluginManager` (already exists)
- `SettingsGenerator` (already exists)
- Plugin directory structure (already exists)
- Test fixtures (already exists)

### External Dependencies

- Claude Code (fer testing plugin)
- GitHub Copilot (fer compatibility research)
- Codex (fer compatibility research)

## Risk Assessment

### Low Risk (Can implement immediately)

- ✅ Hook Registration Audit (configuration only)
- ✅ CLI Command Integration (wraps existing backend)
- ✅ Marketplace Configuration (additive change)
- ✅ Documentation Updates (no code changes)

### Medium Risk (Requires testing)

- ⚠️  Backward Compatibility (affects existing workflows)
- ⚠️  Cross-Tool Compatibility (external dependencies)

### Mitigation Strategies

**Backward Compatibility:**
- Implement detection before migration
- Test with existing projects
- Provide rollback mechanism
- Document clearly

**Cross-Tool Compatibility:**
- Start with documentation research
- Test in isolated environments
- Provide fallback mode if unsupported
- Set realistic expectations

## Success Criteria (From Issue #1948)

Progress against acceptance criteria:

- [x] `amplihack plugin install` installs to `~/.amplihack/.claude/` (Backend ready, need CLI)
- [x] All hooks, agents, commands, skills present in plugin directory (✅ Complete)
- [x] Hooks use `${CLAUDE_PLUGIN_ROOT}` instead of hardcoded paths (✅ Complete, need audit)
- [ ] `settings.json` generated with LSP configuration for detected languages (Need testing)
- [ ] Plugin loads successfully in Claude Code (Need testing)
- [ ] Plugin works with GitHub Copilot (Research needed)
- [ ] Plugin works with Codex (Research needed)
- [ ] Marketplace source configured: `github.com/rysweet/amplihack` (Need implementation)
- [ ] `amplihack plugin uninstall` removes plugin cleanly (Backend ready, need CLI)
- [ ] Existing per-project `.claude` installations continue working (Need implementation)
- [x] Test coverage > 80% for plugin management code (✅ Complete, need +32 tests)
- [ ] Documentation updated with plugin installation instructions (Need implementation)

**Current:** 4/12 complete
**After Phase 1:** 7/12 complete (58%)
**After Phase 2:** 10/12 complete (83%)
**After Phase 3:** 12/12 complete (100%)

## Timeline

### Optimistic (18 hours / 2.5 days)

- Day 1: Phase 1 (5 hours) + Phase 2 Backward Compat (4 hours)
- Day 2: Phase 2 Cross-Tool Research (7 hours)
- Day 3: Phase 3 Documentation (2 hours)

### Realistic (27 hours / 3.5 days)

- Day 1: Phase 1 (7 hours)
- Day 2: Phase 2 Backward Compat (5 hours)
- Day 3: Phase 2 Cross-Tool Research (12 hours)
- Day 4: Phase 3 Documentation (3 hours)

### Pessimistic (36 hours / 4.5 days)

- Day 1: Phase 1 (9 hours)
- Day 2: Phase 2 Backward Compat (6 hours)
- Day 3-4: Phase 2 Cross-Tool Research (18 hours)
- Day 5: Phase 3 Documentation (3 hours)

## Next Actions

1. **Immediate (Phase 1):**
   ```bash
   # Start with Hook Audit (1 hour)
   Read .claude/tools/amplihack/hooks/pre_tool_use.py
   Read .claude/tools/amplihack/hooks/user_prompt_submit.py
   Update hooks.json

   # Then CLI Commands (3 hours)
   Implement cli_handlers.py
   Implement verifier.py
   Wire to cli.py

   # Then Marketplace (1 hour)
   Update plugin.json
   Update settings_generator/generator.py
   Test
   ```

2. **Follow-Up (Phase 2):**
   - Implement mode detection
   - Research Copilot/Codex compatibility
   - Test migration workflows

3. **Finalize (Phase 3):**
   - Update all documentation
   - Test documentation accuracy
   - Update CHANGELOG

## References

- **Main Issue:** Issue #1948
- **Requirements Analysis:** `ISSUE_1948_REQUIREMENTS.md`
- **Individual Specs:**
  - `Specs/PLUGIN_CLI_COMMANDS.md`
  - `Specs/PLUGIN_MARKETPLACE_CONFIG.md`
  - `Specs/HOOK_REGISTRATION_AUDIT.md`
  - `Specs/CROSS_TOOL_COMPATIBILITY.md`
  - `Specs/BACKWARD_COMPATIBILITY.md`
  - `Specs/DOCUMENTATION_UPDATES.md`

---

**This plan provides complete specifications fer all remainin' implementation gaps with clear contracts, testing requirements, and effort estimates following ruthless simplicity and zero-BS principles.**
