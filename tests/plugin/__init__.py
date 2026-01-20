"""
Tests for amplihack plugin architecture.

This package contains TDD tests written before implementation (red phase).
Tests are organized by module and testing level:

- test_installer.py: PluginInstaller unit and integration tests
- test_settings_merger.py: SettingsMerger unit and integration tests
- test_variable_substitutor.py: VariableSubstitutor unit and security tests
- test_lsp_detector.py: LSPDetector unit and integration tests
- test_migration_helper.py: MigrationHelper unit and E2E tests
- test_integration.py: Complete system integration and E2E tests

Test Ratio Target: 0.62:1 (test lines to implementation lines)
Testing Pyramid: 60% unit, 30% integration, 10% E2E
"""
