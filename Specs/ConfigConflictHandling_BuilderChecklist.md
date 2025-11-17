# Builder Checklist: Config Conflict Handling Implementation

This checklist guides the builder agent through implementing the config conflict handling system for Issue #1279.

## Pre-Implementation

- [ ] Review master specification: `Specs/ConfigConflictHandling.md`
- [ ] Review implementation guide: `Specs/ConfigConflictHandling_ImplementationGuide.md`
- [ ] Review architecture diagrams: `Specs/ConfigConflictHandling_Architecture.md`
- [ ] Understand existing CLI structure in `src/amplihack/cli.py`
- [ ] Create feature branch: `feat-issue-1279-config-conflicts`

## Phase 1: Core Modules (Est: 2-3 hours)

### Module 1: ConfigConflictDetector

**Spec**: `Specs/Modules/ConfigConflictDetector.md`

- [ ] Create `src/amplihack/installation/__init__.py`
- [ ] Create `src/amplihack/installation/conflict_detector.py`
- [ ] Implement `ConflictReport` dataclass
- [ ] Implement `detect_conflicts()` function
- [ ] Create `tests/installation/test_conflict_detector.py`
- [ ] Write unit tests:
  - [ ] test_detect_no_conflicts_empty_dir
  - [ ] test_detect_existing_claude_md
  - [ ] test_detect_conflicting_agents
  - [ ] test_detect_upgrade_scenario
  - [ ] test_handle_permission_errors
- [ ] Run tests: `pytest tests/installation/test_conflict_detector.py -v`
- [ ] Verify all tests pass

### Module 2: NamespaceInstaller

**Spec**: `Specs/Modules/NamespaceInstaller.md`

- [ ] Create `src/amplihack/installation/namespace_installer.py`
- [ ] Implement `InstallResult` dataclass
- [ ] Implement `install_to_namespace()` function
- [ ] Handle force flag properly
- [ ] Create `tests/installation/test_namespace_installer.py`
- [ ] Write unit tests:
  - [ ] test_install_to_empty_namespace
  - [ ] test_install_fails_without_force
  - [ ] test_install_with_force_overwrites
  - [ ] test_install_preserves_structure
  - [ ] test_install_handles_permission_errors
- [ ] Run tests: `pytest tests/installation/test_namespace_installer.py -v`
- [ ] Verify all tests pass

### Module 3: ClaudeMdIntegrator

**Spec**: `Specs/Modules/ClaudeMdIntegrator.md`

- [ ] Create `src/amplihack/installation/claude_md_integrator.py`
- [ ] Implement `IntegrationResult` dataclass
- [ ] Implement `integrate_import()` function
- [ ] Implement `remove_import()` function
- [ ] Implement backup creation with timestamp
- [ ] Implement backup rotation (keep last 3)
- [ ] Create `tests/installation/test_claude_md_integrator.py`
- [ ] Write unit tests:
  - [ ] test_add_import_to_existing_file
  - [ ] test_create_new_file_with_import
  - [ ] test_detect_existing_import
  - [ ] test_remove_import
  - [ ] test_backup_creation
  - [ ] test_dry_run_no_changes
  - [ ] test_backup_rotation
- [ ] Run tests: `pytest tests/installation/test_claude_md_integrator.py -v`
- [ ] Verify all tests pass

### Phase 1 Completion

- [ ] All Phase 1 modules implemented
- [ ] All Phase 1 tests pass
- [ ] Code follows module specifications exactly
- [ ] No lint errors or type errors
- [ ] Commit Phase 1: "feat: implement core config conflict modules"

## Phase 2: Orchestration (Est: 2-3 hours)

### Module 4: InstallationOrchestrator

**Spec**: `Specs/Modules/InstallationOrchestrator.md`

- [ ] Create `src/amplihack/installation/orchestrator.py`
- [ ] Implement `InstallMode` enum
- [ ] Implement `OrchestrationResult` dataclass
- [ ] Implement `orchestrate_installation()` function
- [ ] Implement mode detection (install vs UVX)
- [ ] Implement user prompts for integration
- [ ] Implement upgrade scenario handling
- [ ] Implement post-install messages
- [ ] Create `tests/installation/test_orchestrator.py`
- [ ] Write unit tests:
  - [ ] test_fresh_install_flow
  - [ ] test_upgrade_flow
  - [ ] test_conflict_resolution_flow
  - [ ] test_uvx_mode_flow
  - [ ] test_user_declines_integration
  - [ ] test_force_flag_skips_prompts
- [ ] Run tests: `pytest tests/installation/test_orchestrator.py -v`
- [ ] Verify all tests pass

### Update Existing Install Command

**File**: `src/amplihack/cli.py`

- [ ] Import `orchestrate_installation` and `InstallMode`
- [ ] Locate existing install command (or create if missing)
- [ ] Replace implementation with orchestrator call
- [ ] Add `--force` flag if not present
- [ ] Test manually: `amplihack install` in test project
- [ ] Test manually: `amplihack install --force` in test project
- [ ] Verify upgrade scenario works
- [ ] Verify prompts work correctly

### Phase 2 Completion

- [ ] Orchestrator implemented and tested
- [ ] Install command updated
- [ ] Manual testing completed
- [ ] All tests pass
- [ ] No lint errors or type errors
- [ ] Commit Phase 2: "feat: add installation orchestrator and update install command"

## Phase 3: CLI Commands (Est: 2-3 hours)

### Module 5: ConfigCLI

**Spec**: `Specs/Modules/ConfigCLI.md`

- [ ] Create `src/amplihack/installation/config_cli.py`
- [ ] Implement `config` command group with click
- [ ] Implement `config show` command
- [ ] Implement `config integrate` command with --force and --dry-run flags
- [ ] Implement `config remove` command with --keep-files flag
- [ ] Implement `config reset` command with required --force flag
- [ ] Add rich output formatting (with graceful fallback)
- [ ] Create `tests/installation/test_config_cli.py`
- [ ] Write unit tests:
  - [ ] test_show_command_displays_status
  - [ ] test_integrate_prompts_user
  - [ ] test_integrate_with_force
  - [ ] test_integrate_with_dry_run
  - [ ] test_remove_prompts_user
  - [ ] test_remove_with_keep_files
  - [ ] test_reset_requires_force
  - [ ] test_reset_without_force_fails
- [ ] Run tests: `pytest tests/installation/test_config_cli.py -v`
- [ ] Verify all tests pass

### Register Config Commands

**File**: `src/amplihack/cli.py` (or wherever main CLI is defined)

- [ ] Import `config` command group from `config_cli.py`
- [ ] Register config commands with main CLI
- [ ] Test commands manually:
  - [ ] `amplihack config show`
  - [ ] `amplihack config integrate`
  - [ ] `amplihack config integrate --dry-run`
  - [ ] `amplihack config integrate --force`
  - [ ] `amplihack config remove`
  - [ ] `amplihack config remove --keep-files`
  - [ ] `amplihack config reset --force`
- [ ] Verify help text: `amplihack config --help`
- [ ] Verify all commands work as expected

### Phase 3 Completion

- [ ] All config commands implemented
- [ ] All tests pass
- [ ] Manual testing completed
- [ ] Help text is clear
- [ ] No lint errors or type errors
- [ ] Commit Phase 3: "feat: add config CLI commands for manual control"

## Phase 4: Polish & Testing (Est: 1-2 hours)

### Integration Tests

- [ ] Create `tests/integration/test_config_conflict_integration.py`
- [ ] Test complete installation flow (fresh project)
- [ ] Test installation with existing config
- [ ] Test upgrade scenario
- [ ] Test config integrate and remove cycle
- [ ] Test config reset
- [ ] Test UVX mode installation
- [ ] Run all integration tests: `pytest tests/integration/test_config_conflict_integration.py -v`

### Error Handling Review

- [ ] Review all error messages for clarity
- [ ] Ensure all errors suggest fixes
- [ ] Test permission error handling
- [ ] Test disk space error handling
- [ ] Test invalid path handling
- [ ] Test concurrent operation detection

### Manual Testing Checklist

- [ ] Fresh install on empty project
- [ ] Install with existing CLAUDE.md
- [ ] Install with existing custom agents
- [ ] Upgrade from previous version
- [ ] Config show command accuracy
- [ ] Config integrate with confirmation
- [ ] Config integrate with --force
- [ ] Config integrate with --dry-run
- [ ] Config remove with cleanup
- [ ] Config remove with --keep-files
- [ ] Config reset with --force
- [ ] UVX mode installation (if applicable)
- [ ] Permission error handling
- [ ] Backup creation and restoration
- [ ] Import statement detection (exact match)
- [ ] Import statement detection (whitespace variations)

### Documentation

- [ ] Update main README.md with config conflict handling
- [ ] Update CLI help text if needed
- [ ] Add usage examples to docs
- [ ] Document backup/restore procedure
- [ ] Document upgrade path for existing users

### Code Quality

- [ ] Run pre-commit hooks: `pre-commit run --all-files`
- [ ] Fix any lint errors
- [ ] Fix any type errors
- [ ] Verify test coverage: `pytest --cov=src/amplihack/installation`
- [ ] Ensure coverage > 80% for all modules

### Phase 4 Completion

- [ ] All integration tests pass
- [ ] Manual testing completed
- [ ] Documentation updated
- [ ] Code quality checks pass
- [ ] Pre-commit hooks pass
- [ ] Commit Phase 4: "feat: add integration tests and polish config conflict handling"

## Final Review

### Functionality

- [ ] No user files overwritten without consent
- [ ] Installation works in both modes
- [ ] Upgrades are safe and reversible
- [ ] Users can manage integration manually
- [ ] All operations create backups
- [ ] Error messages are clear

### Testing

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Manual testing checklist completed
- [ ] Edge cases covered
- [ ] Error scenarios handled

### Code Quality

- [ ] Follows module specifications
- [ ] No lint errors
- [ ] No type errors
- [ ] Pre-commit hooks pass
- [ ] Code is simple and clear

### Documentation

- [ ] README updated
- [ ] Help text clear
- [ ] Usage examples provided
- [ ] Migration path documented

## Deployment

- [ ] Create PR with all changes
- [ ] PR description includes testing notes
- [ ] Link PR to Issue #1279
- [ ] Request review
- [ ] Address review feedback
- [ ] Merge when approved

## Post-Deployment

- [ ] Monitor for issues
- [ ] Gather user feedback
- [ ] Update DISCOVERIES.md with learnings
- [ ] Consider future enhancements

---

## Quick Reference

### File Locations

```
src/amplihack/installation/
├── __init__.py
├── conflict_detector.py
├── namespace_installer.py
├── claude_md_integrator.py
├── orchestrator.py
└── config_cli.py

tests/installation/
├── test_conflict_detector.py
├── test_namespace_installer.py
├── test_claude_md_integrator.py
├── test_orchestrator.py
└── test_config_cli.py

tests/integration/
└── test_config_conflict_integration.py

Specs/
├── ConfigConflictHandling.md
├── ConfigConflictHandling_ImplementationGuide.md
├── ConfigConflictHandling_Architecture.md
├── ConfigConflictHandling_SUMMARY.md
└── Modules/
    ├── ConfigConflictDetector.md
    ├── NamespaceInstaller.md
    ├── ClaudeMdIntegrator.md
    ├── InstallationOrchestrator.md
    └── ConfigCLI.md
```

### Test Commands

```bash
# Unit tests (fast)
pytest tests/installation/ -v

# Integration tests (slower)
pytest tests/integration/test_config_conflict_integration.py -v

# All tests
pytest tests/installation/ tests/integration/test_config_conflict_integration.py -v

# With coverage
pytest --cov=src/amplihack/installation tests/installation/ -v

# Pre-commit checks
pre-commit run --all-files
```

### Manual Test Commands

```bash
# Installation
amplihack install
amplihack install --force

# Config management
amplihack config show
amplihack config integrate
amplihack config integrate --dry-run
amplihack config integrate --force
amplihack config remove
amplihack config remove --keep-files
amplihack config reset --force

# Help
amplihack install --help
amplihack config --help
amplihack config show --help
```

---

**Remember**: Follow the specifications exactly. If you encounter questions, refer to the spec first, then apply the decision framework (simplest solution). Document any deviations or learnings.

Good luck with the implementation!
