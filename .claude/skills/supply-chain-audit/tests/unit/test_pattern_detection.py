"""
Unit tests — Pattern Detection (per-dimension)
TDD: Tests define what each dimension's checker must detect.
All tests FAIL until supply_chain_audit.checkers.* are implemented.
"""

from supply_chain_audit.checkers import (
    check_action_sha_pinning,  # Dim 1
    check_cache_poisoning,  # Dim 4
    check_cargo_supply_chain,  # Dim 9
    check_container_image_pinning,  # Dim 5
    check_credential_hygiene,  # Dim 6
    check_docker_build_chain,  # Dim 12
    check_go_module_integrity,  # Dim 11
    check_node_integrity,  # Dim 10
    check_nuget_lock,  # Dim 7
    check_python_integrity,  # Dim 8
    check_secret_exposure,  # Dim 3
    check_workflow_permissions,  # Dim 2
)

# ─── Dimension 1: Action SHA Pinning ────────────────────────────────────────


class TestDim1ActionShaPinning:
    def test_semver_tag_detected_as_high(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        findings = check_action_sha_pinning(tmp_path)
        assert len(findings) >= 1
        f = findings[0]
        assert f.severity == "High"
        assert "checkout@v4" in f.current_value
        assert f.offline_detectable is True

    def test_branch_ref_detected_as_high(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: my-org/my-action@main\n"
        )
        findings = check_action_sha_pinning(tmp_path)
        assert any("@main" in f.current_value for f in findings)

    def test_full_sha_with_comment_is_clean(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\npermissions: read-all\njobs:\n  build:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2\n"
        )
        findings = check_action_sha_pinning(tmp_path)
        assert findings == []

    def test_pull_request_target_with_unpinned_action_is_critical(self, tmp_path):
        """pull_request_target + unpinned action elevates severity to Critical."""
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push, pull_request_target]\njobs:\n  test:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@v4\n"
        )
        findings = check_action_sha_pinning(tmp_path)
        critical = [f for f in findings if f.severity == "Critical"]
        assert len(critical) >= 1

    def test_sha_without_version_comment_flagged_as_info(self, tmp_path):
        """Full SHA but no comment — still acceptable but Info-level advisory."""
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\npermissions: read-all\njobs:\n  build:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683\n"
        )
        findings = check_action_sha_pinning(tmp_path)
        # No High/Critical — SHA is pinned even without comment
        high_or_critical = [f for f in findings if f.severity in ("High", "Critical")]
        assert high_or_critical == []

    def test_multiple_workflows_checked(self, tmp_path):
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        (wf_dir / "release.yml").write_text(
            "name: Release\non: [push]\njobs:\n  release:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/upload-artifact@v3\n"
        )
        findings = check_action_sha_pinning(tmp_path)
        files_found = {f.file for f in findings}
        assert any("ci.yml" in p for p in files_found)
        assert any("release.yml" in p for p in files_found)

    def test_finding_includes_sha_lookup_url(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        findings = check_action_sha_pinning(tmp_path)
        assert findings[0].fix_url is not None
        assert "github.com" in findings[0].fix_url


# ─── Dimension 2: Workflow Permissions ──────────────────────────────────────


class TestDim2WorkflowPermissions:
    def test_missing_permissions_key_is_high(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - run: echo hello\n"
        )
        findings = check_workflow_permissions(tmp_path)
        assert any(f.severity == "High" for f in findings)

    def test_permissions_write_all_is_high(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\npermissions: write-all\njobs:\n  build:\n"
            "    runs-on: ubuntu-latest\n    steps:\n      - run: echo hello\n"
        )
        findings = check_workflow_permissions(tmp_path)
        assert any(f.severity == "High" for f in findings)
        assert any("write-all" in f.current_value for f in findings)

    def test_pull_request_target_without_permissions_is_critical(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push, pull_request_target]\njobs:\n  test:\n"
            "    runs-on: ubuntu-latest\n    steps:\n      - run: echo hello\n"
        )
        findings = check_workflow_permissions(tmp_path)
        critical = [f for f in findings if f.severity == "Critical"]
        assert len(critical) >= 1

    def test_permissions_read_all_is_clean(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\npermissions: read-all\njobs:\n  build:\n"
            "    runs-on: ubuntu-latest\n    steps:\n      - run: echo hello\n"
        )
        findings = check_workflow_permissions(tmp_path)
        assert findings == []


# ─── Dimension 3: Secret Exposure ───────────────────────────────────────────


class TestDim3SecretExposure:
    def test_echo_secret_is_critical(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
            '    steps:\n      - run: echo "Token=${{ secrets.API_TOKEN }}"\n'
        )
        findings = check_secret_exposure(tmp_path)
        assert any(f.severity == "Critical" for f in findings)

    def test_print_secret_is_critical(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - run: python -c \"print('${{ secrets.KEY }}')\"\n"
        )
        findings = check_secret_exposure(tmp_path)
        assert any(f.severity == "Critical" for f in findings)

    def test_secret_not_echoed_is_clean(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\npermissions: read-all\njobs:\n  test:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: some/action@<sha>  # v1\n"
            "        with:\n          token: ${{ secrets.GITHUB_TOKEN }}\n"
        )
        findings = check_secret_exposure(tmp_path)
        assert findings == []

    def test_secret_in_cache_key_is_high(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\npermissions: read-all\njobs:\n  test:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/cache@<sha>  # v3\n"
            "        with:\n"
            "          key: ${{ runner.os }}-${{ secrets.CACHE_SECRET }}\n"
        )
        findings = check_secret_exposure(tmp_path)
        assert any(f.severity == "High" for f in findings)


# ─── Dimension 4: Cache Poisoning ───────────────────────────────────────────


class TestDim4CachePoisoning:
    def test_cache_key_without_hashfiles_is_medium(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/cache@v3\n"
            "        with:\n"
            "          key: ${{ runner.os }}-pip\n"
            "          path: ~/.cache/pip\n"
        )
        findings = check_cache_poisoning(tmp_path)
        assert any(f.dimension == 4 and f.severity == "Medium" for f in findings)

    def test_cache_key_with_hashfiles_is_clean(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/cache@v3\n"
            "        with:\n"
            "          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}\n"
            "          path: ~/.cache/pip\n"
        )
        findings = check_cache_poisoning(tmp_path)
        assert not any(f.dimension == 4 and f.severity == "Medium" for f in findings)

    def test_no_workflows_returns_empty(self, tmp_path):
        findings = check_cache_poisoning(tmp_path)
        assert findings == []


# ─── Dimension 5: Container Image Pinning ───────────────────────────────────


class TestDim5ContainerImagePinning:
    def test_latest_tag_is_critical(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM alpine:latest\nRUN echo hello\n")
        findings = check_container_image_pinning(tmp_path)
        assert any(f.severity == "Critical" for f in findings)
        assert any(":latest" in f.current_value for f in findings)

    def test_semver_tag_is_high(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM golang:1.22-alpine AS builder\n")
        findings = check_container_image_pinning(tmp_path)
        assert any(f.severity == "High" for f in findings)

    def test_sha_digest_is_clean(self, tmp_path):
        (tmp_path / "Dockerfile").write_text(
            "FROM ubuntu@sha256:a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2\n"
        )
        findings = check_container_image_pinning(tmp_path)
        assert findings == []

    def test_multi_stage_all_stages_checked(self, tmp_path):
        """All FROM statements in multi-stage builds are checked."""
        (tmp_path / "Dockerfile").write_text(
            "FROM golang:1.22-alpine AS builder\n"
            "FROM alpine:latest\n"
            "COPY --from=builder /app /app\n"
        )
        findings = check_container_image_pinning(tmp_path)
        # Both lines should generate findings
        assert len(findings) >= 2

    def test_scratch_base_is_clean(self, tmp_path):
        """FROM scratch is a valid base with no pinning requirement."""
        (tmp_path / "Dockerfile").write_text(
            "FROM golang:1.22@sha256:abc123 AS builder\n"
            "FROM scratch\n"
            "COPY --from=builder /app /app\n"
        )
        findings = check_container_image_pinning(tmp_path)
        # scratch should not generate a finding; only golang may (semver)
        scratch_findings = [f for f in findings if "scratch" in f.current_value]
        assert scratch_findings == []


# ─── Dimension 8: Python Dependency Integrity ───────────────────────────────


class TestDim8PythonIntegrity:
    def test_requirements_without_hashes_is_high(self, tmp_path):
        (tmp_path / "requirements.txt").write_text(
            "requests==2.31.0\nflask==3.0.3\ngunicorn==22.0.0\n"
        )
        findings = check_python_integrity(tmp_path)
        assert any(f.severity == "High" for f in findings)

    def test_requirements_with_hashes_is_clean(self, tmp_path):
        (tmp_path / "requirements.txt").write_text(
            "requests==2.31.0 \\\n"
            "    --hash=sha256:58cd2187423839c35a28f8b84a8f7db7e6bd2c9d\\\n"
            "    --hash=sha256:fc7f50f5c0e5d7b2a1c3e7e08e6f7f3b2a1c3e7e\n"
        )
        findings = check_python_integrity(tmp_path)
        high_or_critical = [f for f in findings if f.severity in ("High", "Critical")]
        assert high_or_critical == []

    def test_extra_index_url_is_high(self, tmp_path):
        (tmp_path / "requirements.txt").write_text(
            "--extra-index-url https://pypi.evil.com/simple/\nrequests==2.31.0\n"
        )
        findings = check_python_integrity(tmp_path)
        assert any("extra-index-url" in f.current_value for f in findings)
        assert any(f.severity in ("High", "Critical") for f in findings)

    def test_pip_install_without_require_hashes_in_workflow_is_medium(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\npermissions: read-all\njobs:\n  test:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - run: pip install -r requirements.txt\n"
        )
        findings = check_python_integrity(tmp_path)
        medium = [f for f in findings if f.severity == "Medium"]
        assert len(medium) >= 1
        assert any(
            "--require-hashes" in f.rationale or "require-hashes" in f.expected_value
            for f in medium
        )


# ─── Dimension 10: Node.js Integrity ────────────────────────────────────────


class TestDim10NodeIntegrity:
    def test_npm_install_in_workflow_is_high(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\npermissions: read-all\njobs:\n  build:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - run: npm install\n"
        )
        (tmp_path / "package.json").write_text('{"name": "app"}\n')
        findings = check_node_integrity(tmp_path)
        assert any("npm install" in f.current_value for f in findings)
        assert any(f.severity == "High" for f in findings)

    def test_npm_ci_is_clean(self, tmp_path):
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\npermissions: read-all\njobs:\n  build:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - run: npm ci\n"
        )
        (tmp_path / "package.json").write_text('{"name": "app"}\n')
        (tmp_path / "package-lock.json").write_text('{"lockfileVersion": 3}\n')
        findings = check_node_integrity(tmp_path)
        high_or_critical = [f for f in findings if f.severity in ("High", "Critical")]
        assert high_or_critical == []

    def test_missing_lock_file_is_high(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name": "app"}\n')
        # No package-lock.json
        findings = check_node_integrity(tmp_path)
        assert any(f.severity == "High" for f in findings)
        assert any(f.line == 0 for f in findings)  # file-level finding

    def test_unversioned_npx_is_high(self, tmp_path):
        (tmp_path / "package.json").write_text(
            '{"name": "app", "scripts": {"build": "npx webpack --config webpack.config.js"}}\n'
        )
        findings = check_node_integrity(tmp_path)
        assert any("npx webpack" in f.current_value for f in findings)
        assert any(f.severity == "High" for f in findings)

    def test_versioned_npx_is_clean(self, tmp_path):
        (tmp_path / "package.json").write_text(
            '{"name": "app", "scripts": {"build": "npx webpack@5.91.0 --config webpack.config.js"}}\n'
        )
        findings = check_node_integrity(tmp_path)
        npx_findings = [
            f for f in findings if "npx" in f.current_value and f.severity in ("High", "Critical")
        ]
        assert npx_findings == []


# ─── Dimension 11: Go Module Integrity ──────────────────────────────────────


class TestDim11GoModuleIntegrity:
    def test_missing_go_sum_is_high(self, tmp_path):
        (tmp_path / "go.mod").write_text(
            "module github.com/org/app\n\ngo 1.22\n\nrequire github.com/pkg/errors v0.9.1\n"
        )
        findings = check_go_module_integrity(tmp_path)
        assert any(f.severity == "High" for f in findings)

    def test_go_sum_present_is_clean(self, tmp_path):
        (tmp_path / "go.mod").write_text(
            "module github.com/org/app\n\ngo 1.22\n\nrequire github.com/pkg/errors v0.9.1\n"
        )
        (tmp_path / "go.sum").write_text(
            "github.com/pkg/errors v0.9.1 h1:sIXre2Sh2E82tnWo9BZFQ3NZ48ZVKYSV94FtHI/r8+Q=\n"
        )
        findings = check_go_module_integrity(tmp_path)
        high_or_critical = [f for f in findings if f.severity in ("High", "Critical")]
        assert high_or_critical == []

    def test_replace_with_mutable_branch_is_medium(self, tmp_path):
        (tmp_path / "go.mod").write_text(
            "module github.com/org/app\n\ngo 1.22\n\n"
            "require github.com/some/package v1.0.0\n\n"
            "replace github.com/some/package => github.com/myorg/fork main\n"
        )
        (tmp_path / "go.sum").write_text("# empty\n")
        findings = check_go_module_integrity(tmp_path)
        assert any(f.severity == "Medium" for f in findings)
        assert any("replace" in f.current_value for f in findings)

    def test_gonosumcheck_bypass_is_high(self, tmp_path):
        (tmp_path / "go.mod").write_text("module github.com/org/app\n\ngo 1.22\n")
        (tmp_path / "go.sum").write_text("# empty\n")
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\npermissions: read-all\njobs:\n  test:\n"
            "    runs-on: ubuntu-latest\n    env:\n      GONOSUMCHECK: '*'\n"
            "    steps:\n      - run: go build ./...\n"
        )
        findings = check_go_module_integrity(tmp_path)
        assert any("GONOSUMCHECK" in f.current_value for f in findings)


# ─── Dimension 9: Cargo Supply Chain ────────────────────────────────────────


class TestDim9CargoSupplyChain:
    def test_cargo_lock_in_gitignore_for_binary_is_medium(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text(
            "[package]\nname = 'mytool'\nversion = '0.1.0'\n"
            "[[bin]]\nname = 'mytool'\npath = 'src/main.rs'\n"
        )
        (tmp_path / ".gitignore").write_text("target/\nCargo.lock\n")
        findings = check_cargo_supply_chain(tmp_path)
        assert any(f.severity == "Medium" for f in findings)
        assert any("Cargo.lock" in f.current_value or "Cargo.lock" in f.rationale for f in findings)

    def test_cargo_lock_committed_for_binary_is_clean(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text(
            "[package]\nname = 'mytool'\nversion = '0.1.0'\n"
            "[[bin]]\nname = 'mytool'\npath = 'src/main.rs'\n"
        )
        (tmp_path / "Cargo.lock").write_text("# Cargo.lock\n")
        # No .gitignore that excludes Cargo.lock
        findings = check_cargo_supply_chain(tmp_path)
        lock_findings = [
            f
            for f in findings
            if "Cargo.lock" in f.current_value and f.severity in ("High", "Critical")
        ]
        assert lock_findings == []

    def test_build_rs_present_triggers_info_finding(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'app'\nversion = '0.1.0'\n")
        (tmp_path / "Cargo.lock").write_text("# Cargo.lock\n")
        (tmp_path / "build.rs").write_text(
            'fn main() { println!("cargo:rerun-if-changed=build.rs"); }\n'
        )
        findings = check_cargo_supply_chain(tmp_path)
        build_rs_findings = [f for f in findings if "build.rs" in f.file]
        # build.rs presence should at least generate an Info finding for review
        assert len(build_rs_findings) >= 1

    def test_patch_section_with_git_source_is_medium(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text(
            "[package]\nname = 'app'\nversion = '0.1.0'\n"
            "[patch.crates-io]\nserde = { git = 'https://github.com/serde-rs/serde', branch = 'master' }\n"
        )
        (tmp_path / "Cargo.lock").write_text("# Cargo.lock\n")
        findings = check_cargo_supply_chain(tmp_path)
        assert any(
            "patch" in f.current_value.lower() or "patch" in f.rationale.lower() for f in findings
        )


# ─── Dimension 7: NuGet Lock and Audit ──────────────────────────────────────


class TestDim7NuGetLock:
    def test_csproj_without_lock_file_is_high(self, tmp_path):
        proj = tmp_path / "App.csproj"
        proj.write_text(
            '<Project Sdk="Microsoft.NET.Sdk">\n'
            "  <PropertyGroup>\n"
            "    <TargetFramework>net8.0</TargetFramework>\n"
            "  </PropertyGroup>\n"
            "</Project>\n"
        )
        findings = check_nuget_lock(tmp_path)
        assert any(f.severity == "High" for f in findings)
        assert any(f.line == 0 for f in findings)  # file-level

    def test_nuget_config_without_package_source_mapping_is_high(self, tmp_path):
        (tmp_path / "NuGet.Config").write_text(
            "<configuration>\n"
            "  <packageSources>\n"
            "    <add key='internal' value='https://pkgs.dev.azure.com/org/feed/nuget/v3/index.json' />\n"
            "    <add key='nuget.org' value='https://api.nuget.org/v3/index.json' />\n"
            "  </packageSources>\n"
            "</configuration>\n"
        )
        findings = check_nuget_lock(tmp_path)
        assert any(
            "packageSourceMapping" in f.rationale or "packageSourceMapping" in f.expected_value
            for f in findings
        )
        assert any(f.severity == "High" for f in findings)

    def test_nuget_config_with_clear_and_mapping_is_clean(self, tmp_path):
        (tmp_path / "NuGet.Config").write_text(
            "<configuration>\n"
            "  <packageSources>\n"
            "    <clear />\n"
            "    <add key='internal' value='https://pkgs.dev.azure.com/org/feed/nuget/v3/index.json' />\n"
            "  </packageSources>\n"
            "  <packageSourceMapping>\n"
            "    <packageSource key='internal'>\n"
            "      <package pattern='*' />\n"
            "    </packageSource>\n"
            "  </packageSourceMapping>\n"
            "</configuration>\n"
        )
        findings = check_nuget_lock(tmp_path)
        high_or_critical = [f for f in findings if f.severity in ("High", "Critical")]
        assert high_or_critical == []


# ─── Dimension 6: Credential Hygiene ────────────────────────────────────────


class TestDim6CredentialHygiene:
    def test_workflow_with_hardcoded_aws_keys_is_high(self, tmp_path):
        """Hardcoded AWS static access keys should produce a High finding."""
        wf = tmp_path / ".github" / "workflows" / "deploy.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: Deploy\non: [push]\njobs:\n  deploy:\n    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: aws-actions/configure-aws-credentials@v4\n"
            "        with:\n"
            "          aws-access-key-id: ${{ secrets.AWS_KEY }}\n"
            "          aws-secret-access-key: ${{ secrets.AWS_SECRET }}\n"
        )
        findings = check_credential_hygiene(tmp_path)
        assert any(f.severity == "High" for f in findings)
        assert any("AWS" in f.current_value for f in findings)

    def test_workflow_using_oidc_is_clean(self, tmp_path):
        """Workflow using OIDC (role-to-assume) without static keys is clean."""
        wf = tmp_path / ".github" / "workflows" / "deploy.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: Deploy\non: [push]\npermissions:\n  id-token: write\n"
            "jobs:\n  deploy:\n    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: aws-actions/configure-aws-credentials@v4\n"
            "        with:\n"
            "          role-to-assume: arn:aws:iam::123456789:role/deploy\n"
        )
        findings = check_credential_hygiene(tmp_path)
        high_or_critical = [f for f in findings if f.severity in ("High", "Critical")]
        assert high_or_critical == []

    def test_workflow_with_azure_static_creds_is_high(self, tmp_path):
        """Azure static creds (service principal JSON) should be flagged."""
        wf = tmp_path / ".github" / "workflows" / "deploy.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: Deploy\non: [push]\njobs:\n  deploy:\n    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: azure/login@v2\n"
            "        with:\n"
            "          creds: ${{ secrets.AZURE_CREDENTIALS }}\n"
        )
        findings = check_credential_hygiene(tmp_path)
        assert any(f.severity == "High" for f in findings)


# ─── Dimension 12: Docker Build Chain ───────────────────────────────────────


class TestDim12DockerBuildChain:
    def test_multi_stage_no_user_in_final_stage_is_high(self, tmp_path):
        """Multi-stage Dockerfile with no USER in final stage → High finding."""
        (tmp_path / "Dockerfile").write_text(
            "FROM golang:1.22-alpine AS builder\n"
            "WORKDIR /app\n"
            "RUN go build -o /app/main .\n"
            "FROM alpine:3.19\n"
            "COPY --from=builder /app/main /main\n"
            'ENTRYPOINT ["/main"]\n'
        )
        findings = check_docker_build_chain(tmp_path)
        assert any(f.severity == "High" for f in findings)
        assert any("USER" in f.rationale or "root" in f.rationale for f in findings)

    def test_dockerfile_with_user_in_final_stage_is_clean(self, tmp_path):
        """Dockerfile with USER in final stage → clean."""
        (tmp_path / "Dockerfile").write_text(
            "FROM golang:1.22-alpine AS builder\n"
            "WORKDIR /app\n"
            "RUN go build -o /app/main .\n"
            "FROM alpine:3.19\n"
            "RUN addgroup -S appgroup && adduser -S appuser -G appgroup\n"
            "USER appuser\n"
            "COPY --from=builder /app/main /main\n"
            'ENTRYPOINT ["/main"]\n'
        )
        findings = check_docker_build_chain(tmp_path)
        high_or_critical = [f for f in findings if f.severity in ("High", "Critical")]
        assert high_or_critical == []

    def test_single_stage_no_user_is_high(self, tmp_path):
        """Single-stage Dockerfile with no USER → High finding."""
        (tmp_path / "Dockerfile").write_text(
            'FROM python:3.12-slim\nWORKDIR /app\nCOPY . .\nCMD ["python", "app.py"]\n'
        )
        findings = check_docker_build_chain(tmp_path)
        assert any(f.severity == "High" for f in findings)
