"""
Unit tests — Ecosystem Scope Detection
TDD: Tests define the scope-detection logic from SKILL.md Ecosystem Detection table.
All tests FAIL until supply_chain_audit.detector is implemented.
"""

import pytest
from supply_chain_audit.detector import detect_ecosystems


class TestEcosystemDetection:
    """Detect which dimensions apply based on files present in the repo root."""

    def test_no_files_returns_empty_scope(self, tmp_path):
        scope = detect_ecosystems(tmp_path)
        assert scope.active_dimensions == []
        assert scope.skipped_dimensions == list(range(1, 13))

    def test_github_workflows_triggers_dims_1_to_4(self, tmp_path):
        wf = tmp_path / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "ci.yml").write_text("name: CI\n")
        scope = detect_ecosystems(tmp_path)
        assert 1 in scope.active_dimensions
        assert 2 in scope.active_dimensions
        assert 3 in scope.active_dimensions
        assert 4 in scope.active_dimensions

    def test_dockerfile_triggers_dims_5_and_12(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM ubuntu:22.04\n")
        scope = detect_ecosystems(tmp_path)
        assert 5 in scope.active_dimensions
        assert 12 in scope.active_dimensions

    def test_docker_compose_triggers_dims_5_and_12(self, tmp_path):
        (tmp_path / "docker-compose.yml").write_text("version: '3'\n")
        scope = detect_ecosystems(tmp_path)
        assert 5 in scope.active_dimensions
        assert 12 in scope.active_dimensions

    def test_workflow_with_secrets_triggers_dim_6(self, tmp_path):
        wf = tmp_path / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "deploy.yml").write_text("name: Deploy\nsteps:\n  - run: echo ${{ secrets.TOKEN }}\n")
        scope = detect_ecosystems(tmp_path)
        assert 6 in scope.active_dimensions

    def test_csproj_triggers_dim_7(self, tmp_path):
        (tmp_path / "App.csproj").write_text("<Project />\n")
        scope = detect_ecosystems(tmp_path)
        assert 7 in scope.active_dimensions

    def test_nuget_config_triggers_dim_7(self, tmp_path):
        (tmp_path / "NuGet.Config").write_text("<configuration />\n")
        scope = detect_ecosystems(tmp_path)
        assert 7 in scope.active_dimensions

    def test_requirements_txt_triggers_dim_8(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
        scope = detect_ecosystems(tmp_path)
        assert 8 in scope.active_dimensions

    def test_pyproject_toml_triggers_dim_8(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'app'\n")
        scope = detect_ecosystems(tmp_path)
        assert 8 in scope.active_dimensions

    def test_setup_cfg_triggers_dim_8(self, tmp_path):
        (tmp_path / "setup.cfg").write_text("[metadata]\nname = app\n")
        scope = detect_ecosystems(tmp_path)
        assert 8 in scope.active_dimensions

    def test_cargo_toml_triggers_dim_9(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'app'\n")
        scope = detect_ecosystems(tmp_path)
        assert 9 in scope.active_dimensions

    def test_package_json_triggers_dim_10(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name": "app"}\n')
        scope = detect_ecosystems(tmp_path)
        assert 10 in scope.active_dimensions

    def test_package_lock_json_triggers_dim_10(self, tmp_path):
        (tmp_path / "package-lock.json").write_text('{"lockfileVersion": 3}\n')
        scope = detect_ecosystems(tmp_path)
        assert 10 in scope.active_dimensions

    def test_go_mod_triggers_dim_11(self, tmp_path):
        (tmp_path / "go.mod").write_text("module github.com/org/repo\n\ngo 1.22\n")
        scope = detect_ecosystems(tmp_path)
        assert 11 in scope.active_dimensions

    def test_go_sum_triggers_dim_11(self, tmp_path):
        (tmp_path / "go.sum").write_text("# empty\n")
        scope = detect_ecosystems(tmp_path)
        assert 11 in scope.active_dimensions

    def test_multiple_ecosystems_trigger_all_dimensions(self, tmp_path):
        """Polyglot repo triggers all dimensions simultaneously."""
        (tmp_path / "Dockerfile").write_text("FROM ubuntu:22.04\n")
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
        (tmp_path / "package.json").write_text('{"name": "app"}\n')
        (tmp_path / "go.mod").write_text("module github.com/org/app\n\ngo 1.22\n")
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'app'\n")
        wf = tmp_path / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "ci.yml").write_text("name: CI\n")
        scope = detect_ecosystems(tmp_path)
        assert set(range(1, 13)) == set(scope.active_dimensions)


class TestScopeFiltering:
    """--scope flag restricts dimensions to the specified subset."""

    def test_scope_gha_restricts_to_dims_1_to_4(self, tmp_path):
        wf = tmp_path / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "ci.yml").write_text("name: CI\n")
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
        scope = detect_ecosystems(tmp_path, scope="gha")
        assert set(scope.active_dimensions) == {1, 2, 3, 4}
        assert 8 not in scope.active_dimensions

    def test_scope_containers_restricts_to_dims_5_12(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM ubuntu:22.04\n")
        scope = detect_ecosystems(tmp_path, scope="containers")
        assert set(scope.active_dimensions) == {5, 12}

    def test_scope_all_enables_all_detected_dimensions(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
        scope = detect_ecosystems(tmp_path, scope="all")
        assert 8 in scope.active_dimensions

    def test_invalid_scope_raises_invalid_scope_error(self, tmp_path):
        from supply_chain_audit.errors import InvalidScopeError

        with pytest.raises(InvalidScopeError) as exc_info:
            detect_ecosystems(tmp_path, scope="terraform")
        assert "INVALID_SCOPE" in str(exc_info.value)
        assert "terraform" in str(exc_info.value)

    def test_scope_enum_injection_via_semicolon_rejected(self, tmp_path):
        """Semicolon injection attempt must produce INVALID_SCOPE not shell exec."""
        from supply_chain_audit.errors import InvalidScopeError

        with pytest.raises(InvalidScopeError):
            detect_ecosystems(tmp_path, scope="gha; rm -rf /")

    def test_scope_enum_injection_via_pipe_rejected(self, tmp_path):
        from supply_chain_audit.errors import InvalidScopeError

        with pytest.raises(InvalidScopeError):
            detect_ecosystems(tmp_path, scope="gha | cat /etc/passwd")


class TestSkippedDimensionReporting:
    """Skipped dimensions must be explicitly listed in the report."""

    def test_skipped_dimensions_annotated_with_reason(self, tmp_path):
        wf = tmp_path / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "ci.yml").write_text("name: CI\n")
        scope = detect_ecosystems(tmp_path)
        # Dims 5, 7, 8, 9, 10, 11, 12 should be skipped (no relevant files)
        assert 5 in scope.skipped_dimensions
        skipped_info = scope.get_skip_reason(5)
        assert "Dockerfile" in skipped_info or "docker" in skipped_info.lower()

    def test_empty_repo_lists_all_12_as_skipped(self, tmp_path):
        scope = detect_ecosystems(tmp_path)
        assert len(scope.skipped_dimensions) == 12
        assert len(scope.active_dimensions) == 0
