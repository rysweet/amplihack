"""
Real End-to-End Test for Agent Bundle Generator.

This test performs REAL operations with minimal mocking:
- Real file operations (create, read, write, delete)
- Real bundle generation (actual file structure)
- Real script execution (run repackage.sh)
- Real git operations (init, add, commit)

Only mocked: gh CLI network calls (gh repo create, gh api)

Mark with @pytest.mark.skip to prevent running in CI by default.
Run manually with: pytest tests/test_bundle_generator_real_e2e.py -v
"""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Import bundle generator components
from amplihack.bundle_generator import (
    AgentGenerator,
    BundleBuilder,
    IntentExtractor,
    PromptParser,
)
from amplihack.bundle_generator.filesystem_packager import FilesystemPackager
from amplihack.bundle_generator.repository_creator import RepositoryCreator


@pytest.mark.skip(reason="Real E2E test - run manually")
def test_real_e2e_complete_workflow():
    """
    Real end-to-end test with actual file operations and minimal mocking.

    Workflow:
    1. Generate bundle (real file operations)
    2. Create complete filesystem package (real directories/files)
    3. Execute repackage script (real script execution)
    4. Create GitHub repo (mocked network only)

    Only mocked:
    - gh repo create (network call)
    - gh api calls (network call)
    """
    # Use real temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "test-bundles"
        output_dir.mkdir()

        print(f"\n[REAL E2E] Using temporary directory: {output_dir}")

        # =====================================================================
        # Stage 1: Generate Bundle (REAL operations)
        # =====================================================================
        print("\n[Stage 1/4] Generating bundle with REAL file operations...")

        prompt = "Create a monitoring agent that tracks API performance and sends alerts"
        parser = PromptParser()
        extractor = IntentExtractor(parser)
        generator = AgentGenerator()
        builder = BundleBuilder(output_dir)

        # Parse and generate
        parsed = parser.parse(prompt)
        assert parsed.confidence > 0.0, "Parsing should succeed"

        intent = extractor.extract(parsed)
        assert len(intent.agent_requirements) >= 1, "Should extract at least one agent"

        agents = generator.generate(intent)
        assert len(agents) >= 1, "Should generate at least one agent"

        bundle = builder.build(agents, intent)
        assert bundle.name, "Bundle should have a name"

        # Write bundle to REAL filesystem
        bundle_path = builder.write_bundle(bundle)
        assert bundle_path.exists(), "Bundle directory should exist on real filesystem"
        assert bundle_path.is_dir(), "Bundle path should be a directory"

        print(f"   ✓ Bundle created at: {bundle_path}")
        print(f"   ✓ Files created: {len(list(bundle_path.rglob('*')))}")

        # =====================================================================
        # Stage 2: Create Filesystem Package (REAL operations)
        # =====================================================================
        print("\n[Stage 2/4] Creating complete filesystem package with REAL files...")

        # Create filesystem package with repackage scripts and instructions
        fs_packager = FilesystemPackager(output_dir)
        complete_bundle_path = fs_packager.create_package(bundle, build_uvx=False)

        # Verify REAL files exist
        assert complete_bundle_path.exists(), "Complete bundle should exist"
        assert (complete_bundle_path / "INSTRUCTIONS.md").exists(), "INSTRUCTIONS.md should exist"
        assert (complete_bundle_path / "repackage.sh").exists(), "repackage.sh should exist"
        assert (complete_bundle_path / "pyproject.toml").exists(), "pyproject.toml should exist"

        # Verify repackage script is executable (REAL permission check)
        repackage_script = complete_bundle_path / "repackage.sh"
        assert repackage_script.stat().st_mode & 0o111, "repackage.sh should be executable"

        print(f"   ✓ Complete package created at: {complete_bundle_path}")
        print(
            f"   ✓ INSTRUCTIONS.md: {(complete_bundle_path / 'INSTRUCTIONS.md').stat().st_size} bytes"
        )
        print(f"   ✓ repackage.sh: executable={repackage_script.stat().st_mode & 0o111}")

        # =====================================================================
        # Stage 3: Execute Repackage Script (REAL execution)
        # =====================================================================
        print("\n[Stage 3/4] Executing repackage script with REAL subprocess...")

        # REAL script execution
        result = subprocess.run(
            [str(repackage_script)],
            cwd=complete_bundle_path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Check execution result
        print(f"   ✓ Script executed with return code: {result.returncode}")
        if result.stdout:
            print(f"   ✓ stdout: {result.stdout[:200]}")
        if result.stderr:
            print(f"   ✓ stderr: {result.stderr[:200]}")

        assert result.returncode == 0, f"Repackage script should succeed: {result.stderr}"

        # =====================================================================
        # Stage 4: Create GitHub Repository (MOCKED network only)
        # =====================================================================
        print("\n[Stage 4/4] Creating GitHub repository with MOCKED network calls...")

        # Mock only the network calls to gh CLI
        def mock_subprocess_run(*args, **kwargs):
            """Mock subprocess.run for gh CLI network calls only."""
            cmd = args[0] if args else kwargs.get("args", [])
            text_mode = kwargs.get("text", False)

            # Mock gh repo create (network call)
            if "gh" in cmd and "repo" in cmd and "create" in cmd:
                url = "https://github.com/testuser/test-monitoring-bundle\n"
                return subprocess.CompletedProcess(
                    args=cmd,
                    returncode=0,
                    stdout=url if text_mode else url.encode(),
                    stderr="" if text_mode else b"",
                )

            # Mock gh api user (network call)
            if "gh" in cmd and "api" in cmd and "user" in cmd:
                username = "testuser\n"
                return subprocess.CompletedProcess(
                    args=cmd,
                    returncode=0,
                    stdout=username if text_mode else username.encode(),
                    stderr="" if text_mode else b"",
                )

            # Mock gh --version (check)
            if "gh" in cmd and "--version" in cmd:
                version = "gh version 2.0.0\n"
                return subprocess.CompletedProcess(
                    args=cmd,
                    returncode=0,
                    stdout=version if text_mode else version.encode(),
                    stderr="" if text_mode else b"",
                )

            # Mock gh auth status (check)
            if "gh" in cmd and "auth" in cmd and "status" in cmd:
                status = "Logged in to github.com\n"
                return subprocess.CompletedProcess(
                    args=cmd,
                    returncode=0,
                    stdout=status if text_mode else status.encode(),
                    stderr="" if text_mode else b"",
                )

            # REAL git operations - let them execute normally
            if "git" in cmd:
                # Execute REAL git command
                return subprocess.run(*args, **kwargs)

            # Default for other commands
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="" if text_mode else b"",
                stderr="" if text_mode else b"",
            )

        # Patch subprocess.run for this stage only
        with patch("subprocess.run", side_effect=mock_subprocess_run):
            creator = RepositoryCreator()

            # Create repository (mocked network, real git)
            result = creator.create_repository(
                bundle_path=complete_bundle_path,
                repo_name="test-monitoring-bundle",
                private=True,
                push=False,
            )

            # Verify result
            assert result.success, f"Repository creation should succeed: {result.error}"
            assert result.url, "Repository URL should be returned"
            assert "github.com" in result.url, "Should be a GitHub URL"

            print(f"   ✓ Repository created: {result.url}")

        # =====================================================================
        # Final Verification: Check all REAL files
        # =====================================================================
        print("\n[Final Verification] Checking all REAL files created...")

        # Verify manifest
        manifest_path = complete_bundle_path / "manifest.json"
        assert manifest_path.exists(), "manifest.json should exist"
        manifest_data = json.loads(manifest_path.read_text())
        assert "bundle" in manifest_data, "manifest should have bundle section"
        assert "agents" in manifest_data, "manifest should have agents section"
        print(f"   ✓ manifest.json: {len(manifest_data['agents'])} agent(s)")

        # Verify agents directory
        agents_dir = complete_bundle_path / "agents"
        assert agents_dir.exists(), "agents/ directory should exist"
        agent_files = list(agents_dir.glob("*.md"))
        assert len(agent_files) >= 1, "Should have at least one agent file"
        print(f"   ✓ agents/: {len(agent_files)} agent file(s)")

        # Verify README
        readme_path = complete_bundle_path / "README.md"
        assert readme_path.exists(), "README.md should exist"
        print(f"   ✓ README.md: {readme_path.stat().st_size} bytes")

        # Verify git was initialized (real .git directory)
        git_dir = complete_bundle_path / ".git"
        assert git_dir.exists(), ".git directory should exist from real git operations"
        print("   ✓ .git/: directory exists (real git repository)")

        # =====================================================================
        # Summary
        # =====================================================================
        print("\n" + "=" * 70)
        print("REAL E2E TEST SUMMARY")
        print("=" * 70)
        print(f"Bundle Name: {bundle.name}")
        print(f"Bundle Path: {complete_bundle_path}")
        print(f"Total Files: {len(list(complete_bundle_path.rglob('*')))}")
        print(f"Agents: {len(agent_files)}")
        print("Git Repository: Initialized")
        print("Repackage Script: Executed successfully")
        print("GitHub Repo: Created (mocked network)")
        print("=" * 70)
        print("✅ REAL E2E TEST PASSED")
        print("=" * 70)


@pytest.mark.skip(reason="Real E2E test - run manually")
def test_real_e2e_repackage_workflow():
    """
    Test the complete edit → repackage workflow with REAL operations.

    1. Generate bundle
    2. Edit an agent file (real file modification)
    3. Run repackage script (real execution)
    4. Verify package is updated
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "test-bundles"
        output_dir.mkdir()

        print(f"\n[REAL E2E REPACKAGE] Using directory: {output_dir}")

        # Generate bundle
        prompt = "Create a simple notification agent"
        parser = PromptParser()
        extractor = IntentExtractor(parser)
        generator = AgentGenerator()
        builder = BundleBuilder(output_dir)

        parsed = parser.parse(prompt)
        intent = extractor.extract(parsed)
        agents = generator.generate(intent)
        bundle = builder.build(agents, intent)
        builder.write_bundle(bundle)

        # Create complete package
        fs_packager = FilesystemPackager(output_dir)
        complete_bundle_path = fs_packager.create_package(bundle, build_uvx=False)

        print(f"   ✓ Bundle created: {complete_bundle_path}")

        # =====================================================================
        # Edit an agent file (REAL file modification)
        # =====================================================================
        print("\n[Step 1/3] Editing agent file with REAL file operations...")

        agents_dir = complete_bundle_path / "agents"
        agent_files = list(agents_dir.glob("*.md"))
        assert len(agent_files) >= 1, "Should have at least one agent file"

        # Edit the first agent file
        agent_file = agent_files[0]
        original_content = agent_file.read_text()
        print(f"   Original size: {len(original_content)} bytes")

        # Add a new section to the agent
        edited_content = (
            original_content + "\n\n## Custom Edit\n\nThis section was added during testing.\n"
        )
        agent_file.write_text(edited_content)
        print(f"   Edited size: {len(edited_content)} bytes")

        # Verify edit
        assert agent_file.read_text() == edited_content, "Edit should persist to disk"
        print(f"   ✓ Agent file edited: {agent_file.name}")

        # =====================================================================
        # Run repackage script (REAL execution)
        # =====================================================================
        print("\n[Step 2/3] Running repackage script with REAL execution...")

        repackage_script = complete_bundle_path / "repackage.sh"
        result = subprocess.run(
            [str(repackage_script)],
            cwd=complete_bundle_path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        print(f"   Return code: {result.returncode}")
        if result.stdout:
            print(f"   stdout: {result.stdout[:200]}")

        assert result.returncode == 0, f"Repackage should succeed after edit: {result.stderr}"
        print("   ✓ Repackage script executed successfully")

        # =====================================================================
        # Verify package is updated (REAL file checks)
        # =====================================================================
        print("\n[Step 3/3] Verifying package update with REAL checks...")

        # Verify edited content persists
        current_content = agent_file.read_text()
        assert "Custom Edit" in current_content, "Edit should still be present after repackage"
        print("   ✓ Edited content persists after repackage")

        # Verify manifest is still valid
        manifest_path = complete_bundle_path / "manifest.json"
        manifest_data = json.loads(manifest_path.read_text())
        assert "bundle" in manifest_data, "manifest should still be valid"
        print("   ✓ Manifest still valid after repackage")

        print("\n✅ REAL E2E REPACKAGE TEST PASSED")
