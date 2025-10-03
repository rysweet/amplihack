"""
Comprehensive integration tests for UVX working directory staging flow.

Tests the complete end-to-end workflow including detection, path resolution,
staging operations, and validation that no temp directories are used.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.amplihack.utils.uvx_detection import detect_uvx_deployment, resolve_framework_paths
from src.amplihack.utils.uvx_models import UVXConfiguration
from src.amplihack.utils.uvx_staging_v2 import UVXStager, create_uvx_session, stage_uvx_framework


class TestUVXWorkingDirectoryIntegration:
    """Integration tests for complete UVX working directory staging workflow."""

    def test_full_uvx_workflow_working_directory_staging(self):
        """Test complete UVX workflow with working directory staging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create realistic UVX package structure
            site_packages = Path(temp_dir) / "site-packages"
            site_packages.mkdir()

            amplihack_package = site_packages / "amplihack"
            amplihack_package.mkdir()

            # Create comprehensive .claude structure
            claude_dir = amplihack_package / ".claude"
            claude_dir.mkdir()

            # Context files
            context_dir = claude_dir / "context"
            context_dir.mkdir()
            (context_dir / "PHILOSOPHY.md").write_text("# Philosophy\nRuthless simplicity")
            (context_dir / "PROJECT.md").write_text("# Project\nUVX Framework")
            (context_dir / "PATTERNS.md").write_text("# Patterns\nBricks and studs")

            # Agents
            agents_dir = claude_dir / "agents"
            agents_dir.mkdir()
            amplihack_agents = agents_dir / "amplihack"
            amplihack_agents.mkdir()
            (amplihack_agents / "architect.md").write_text("# Architect Agent")
            (amplihack_agents / "builder.md").write_text("# Builder Agent")

            # Tools and commands
            tools_dir = claude_dir / "tools"
            tools_dir.mkdir()
            (tools_dir / "test_tool.py").write_text("# Test tool")

            commands_dir = claude_dir / "commands"
            commands_dir.mkdir()
            (commands_dir / "test_command.py").write_text("# Test command")

            # Settings
            settings_content = {
                "version": "1.0",
                "features": {"working_directory_staging": True, "temp_directory_usage": False},
                "uvx_optimizations": True,
            }
            (claude_dir / "settings.json").write_text(json.dumps(settings_content, indent=2))

            # Create user project directory
            user_project = Path(temp_dir) / "my_awesome_project"
            user_project.mkdir()

            # Add some user files
            (user_project / "main.py").write_text("print('Hello from my project!')")
            (user_project / "requirements.txt").write_text("requests>=2.25.0")
            user_subdir = user_project / "src"
            user_subdir.mkdir()
            (user_subdir / "utils.py").write_text("def helper(): pass")

            original_cwd = os.getcwd()

            try:
                # Simulate user working in their project directory
                os.chdir(str(user_project))

                # Mock UVX environment
                with patch.dict(
                    os.environ,
                    {"UV_PYTHON": "/home/user/.cache/uv/python", "PYTHONPATH": str(site_packages)},
                ):
                    with patch("sys.executable", "/home/user/.cache/uv/python"):
                        with patch("sys.path", [str(site_packages)]):
                            # Configure for working directory staging
                            config = UVXConfiguration(
                                use_working_directory_staging=True,
                                working_directory_subdir=".claude",
                                handle_existing_claude_dir="backup",
                                allow_staging=True,
                                debug_enabled=True,
                            )

                            # Test 1: Detection
                            detection_state = detect_uvx_deployment(config)
                            assert detection_state.is_uvx_deployment
                            assert "UV cache" in " ".join(detection_state.detection_reasons)

                            # Test 2: Path Resolution
                            resolution_result = resolve_framework_paths(detection_state, config)
                            assert resolution_result.is_successful
                            assert resolution_result.requires_staging
                            assert (
                                resolution_result.location.strategy.name
                                == "WORKING_DIRECTORY_STAGING"
                            )

                            # Test 3: Staging
                            stager = UVXStager(config)
                            staging_result = stager.stage_framework_files()

                            assert staging_result.is_successful
                            assert len(staging_result.successful) > 0
                            assert len(staging_result.failed) == 0

                            # Test 4: Verify staged structure
                            staged_claude = user_project / ".claude"
                            assert staged_claude.exists() and staged_claude.is_dir()

                            # Verify all directories staged
                            assert (staged_claude / "context").exists()
                            assert (staged_claude / "agents" / "amplihack").exists()
                            assert (staged_claude / "tools").exists()
                            assert (staged_claude / "commands").exists()

                            # Verify all files staged with correct content
                            assert (
                                staged_claude / "context" / "PHILOSOPHY.md"
                            ).read_text() == "# Philosophy\nRuthless simplicity"
                            assert (
                                staged_claude / "agents" / "amplihack" / "architect.md"
                            ).read_text() == "# Architect Agent"
                            assert (
                                staged_claude / "tools" / "test_tool.py"
                            ).read_text() == "# Test tool"

                            # Verify settings.json handled correctly
                            staged_settings = staged_claude / "settings.json"
                            assert staged_settings.exists()
                            settings_data = json.loads(staged_settings.read_text())
                            assert settings_data["version"] == "1.0"
                            assert settings_data["features"]["working_directory_staging"] is True

                            # Test 5: Verify user files preserved
                            assert (user_project / "main.py").exists()
                            assert (user_project / "requirements.txt").exists()
                            assert (user_project / "src" / "utils.py").exists()
                            assert (
                                user_project / "main.py"
                            ).read_text() == "print('Hello from my project!')"

                            # Test 6: Verify working directory unchanged
                            assert Path.cwd() == user_project

                            # Test 7: Verify no temp directories created
                            if Path("/tmp").exists():
                                temp_dirs = [
                                    p
                                    for p in Path("/tmp").iterdir()
                                    if p.is_dir() and ("amplihack" in str(p) or "uvx" in str(p))
                                ]
                                assert len(temp_dirs) == 0, f"Found temp directories: {temp_dirs}"

            finally:
                os.chdir(original_cwd)

    def test_create_uvx_session_integration(self):
        """Test create_uvx_session function with working directory staging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup UVX environment
            site_packages = Path(temp_dir) / "site-packages"
            site_packages.mkdir()

            amplihack_package = site_packages / "amplihack"
            amplihack_package.mkdir()

            claude_dir = amplihack_package / ".claude"
            claude_dir.mkdir()
            (claude_dir / "test_file.txt").write_text("session test")

            user_project = Path(temp_dir) / "session_test_project"
            user_project.mkdir()

            original_cwd = os.getcwd()

            try:
                os.chdir(str(user_project))

                with patch.dict(os.environ, {"UV_PYTHON": "/cache/uv/python"}):
                    with patch("sys.executable", "/cache/uv/python"):
                        with patch("sys.path", [str(site_packages)]):
                            with patch("pathlib.Path.cwd", return_value=user_project):
                                # Create UVX session
                                session = create_uvx_session()

                                # Verify session state
                                assert session.initialized is True
                                assert session.session_id is not None
                                assert session.detection_state.is_uvx_deployment
                                assert session.path_resolution.is_successful
                                assert session.staging_result.is_successful

                                # Verify files staged to working directory
                                assert (user_project / ".claude" / "test_file.txt").exists()
                                assert (
                                    user_project / ".claude" / "test_file.txt"
                                ).read_text() == "session test"

            finally:
                os.chdir(original_cwd)

    def test_stage_uvx_framework_convenience_function(self):
        """Test stage_uvx_framework convenience function integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup environment
            site_packages = Path(temp_dir) / "site-packages"
            site_packages.mkdir()

            amplihack_package = site_packages / "amplihack"
            amplihack_package.mkdir()

            claude_dir = amplihack_package / ".claude"
            claude_dir.mkdir()
            (claude_dir / "convenience_test.txt").write_text("convenience function test")

            user_project = Path(temp_dir) / "convenience_project"
            user_project.mkdir()

            original_cwd = os.getcwd()

            try:
                os.chdir(str(user_project))

                with patch.dict(os.environ, {"UV_PYTHON": "/cache/uv/python"}):
                    with patch("sys.executable", "/cache/uv/python"):
                        with patch("sys.path", [str(site_packages)]):
                            with patch("pathlib.Path.cwd", return_value=user_project):
                                # Use convenience function
                                config = UVXConfiguration(use_working_directory_staging=True)
                                success = stage_uvx_framework(config)

                                assert success is True

                                # Verify staging occurred
                                staged_file = user_project / ".claude" / "convenience_test.txt"
                                assert staged_file.exists()
                                assert staged_file.read_text() == "convenience function test"

            finally:
                os.chdir(original_cwd)

    def test_integration_with_existing_claude_directory(self):
        """Test integration when user already has .claude directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup framework source
            site_packages = Path(temp_dir) / "site-packages"
            site_packages.mkdir()

            amplihack_package = site_packages / "amplihack"
            amplihack_package.mkdir()

            source_claude = amplihack_package / ".claude"
            source_claude.mkdir()
            (source_claude / "new_file.txt").write_text("new framework content")
            (source_claude / "shared_file.txt").write_text("updated framework content")

            # Setup user project with existing .claude
            user_project = Path(temp_dir) / "existing_claude_project"
            user_project.mkdir()

            existing_claude = user_project / ".claude"
            existing_claude.mkdir()
            (existing_claude / "user_file.txt").write_text("user content")
            (existing_claude / "shared_file.txt").write_text("original user content")

            original_cwd = os.getcwd()

            try:
                os.chdir(str(user_project))

                with patch.dict(os.environ, {"UV_PYTHON": "/cache/uv/python"}):
                    with patch("sys.executable", "/cache/uv/python"):
                        with patch("sys.path", [str(site_packages)]):
                            with patch("pathlib.Path.cwd", return_value=user_project):
                                # Test backup strategy
                                config = UVXConfiguration(
                                    use_working_directory_staging=True,
                                    handle_existing_claude_dir="backup",
                                )

                                stager = UVXStager(config)
                                result = stager.stage_framework_files()

                                assert result.is_successful

                                # Verify backup was created
                                backup_dirs = [
                                    d
                                    for d in user_project.iterdir()
                                    if d.name.startswith(".claude.backup.")
                                ]
                                assert len(backup_dirs) == 1

                                backup_dir = backup_dirs[0]
                                assert (backup_dir / "user_file.txt").read_text() == "user content"
                                assert (
                                    backup_dir / "shared_file.txt"
                                ).read_text() == "original user content"

                                # Verify new .claude directory has framework content
                                new_claude = user_project / ".claude"
                                assert (
                                    new_claude / "new_file.txt"
                                ).read_text() == "new framework content"
                                assert (
                                    new_claude / "shared_file.txt"
                                ).read_text() == "updated framework content"

            finally:
                os.chdir(original_cwd)

    def test_integration_performance_with_large_framework(self):
        """Test integration performance with large framework structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create large framework structure
            site_packages = Path(temp_dir) / "site-packages"
            site_packages.mkdir()

            amplihack_package = site_packages / "amplihack"
            amplihack_package.mkdir()

            claude_dir = amplihack_package / ".claude"
            claude_dir.mkdir()

            # Create realistic large structure
            categories = ["agents", "context", "tools", "commands", "workflows", "templates"]
            for category in categories:
                category_dir = claude_dir / category
                category_dir.mkdir()

                if category == "agents":
                    # Nested agent structure
                    for agent_type in ["amplihack", "specialized", "experimental"]:
                        agent_subdir = category_dir / agent_type
                        agent_subdir.mkdir()
                        for i in range(20):
                            (agent_subdir / f"agent_{i}.md").write_text(
                                f"# Agent {i}\nContent for agent {i}"
                            )

                else:
                    # Regular files
                    for i in range(50):
                        (category_dir / f"{category}_file_{i}.txt").write_text(
                            f"Content for {category} file {i}"
                        )

            user_project = Path(temp_dir) / "performance_project"
            user_project.mkdir()

            original_cwd = os.getcwd()

            try:
                os.chdir(str(user_project))

                with patch.dict(os.environ, {"UV_PYTHON": "/cache/uv/python"}):
                    with patch("sys.executable", "/cache/uv/python"):
                        with patch("sys.path", [str(site_packages)]):
                            with patch("pathlib.Path.cwd", return_value=user_project):
                                import time

                                start_time = time.time()

                                config = UVXConfiguration(use_working_directory_staging=True)
                                success = stage_uvx_framework(config)

                                end_time = time.time()
                                staging_time = end_time - start_time

                                # Verify performance and success
                                assert success is True
                                assert staging_time < 60  # Should complete within 1 minute

                                # Verify all content staged
                                staged_claude = user_project / ".claude"
                                for category in categories:
                                    category_dir = staged_claude / category
                                    assert category_dir.exists()

                                # Sample verification
                                assert (
                                    staged_claude / "agents" / "amplihack" / "agent_0.md"
                                ).exists()
                                assert (staged_claude / "context" / "context_file_0.txt").exists()

                                print(
                                    f"✅ Large framework staging completed in {staging_time:.2f} seconds"
                                )

            finally:
                os.chdir(original_cwd)


class TestUVXIntegrationErrorHandling:
    """Integration tests for error handling scenarios."""

    def test_integration_with_permission_errors(self):
        """Test integration handles permission errors gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup framework
            site_packages = Path(temp_dir) / "site-packages"
            site_packages.mkdir()

            amplihack_package = site_packages / "amplihack"
            amplihack_package.mkdir()

            claude_dir = amplihack_package / ".claude"
            claude_dir.mkdir()
            (claude_dir / "test_file.txt").write_text("test content")

            user_project = Path(temp_dir) / "permission_test"
            user_project.mkdir()

            original_cwd = os.getcwd()

            try:
                os.chdir(str(user_project))

                with patch.dict(os.environ, {"UV_PYTHON": "/cache/uv/python"}):
                    with patch("sys.executable", "/cache/uv/python"):
                        with patch("sys.path", [str(site_packages)]):
                            with patch("pathlib.Path.cwd", return_value=user_project):
                                # Mock permission error during file creation
                                with patch(
                                    "shutil.copy2", side_effect=PermissionError("Access denied")
                                ):
                                    config = UVXConfiguration(use_working_directory_staging=True)
                                    success = stage_uvx_framework(config)

                                    # Should fail gracefully
                                    assert success is False

            finally:
                os.chdir(original_cwd)

    def test_integration_with_missing_source_framework(self):
        """Test integration when source framework is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            user_project = Path(temp_dir) / "missing_source_test"
            user_project.mkdir()

            original_cwd = os.getcwd()

            try:
                os.chdir(str(user_project))

                with patch.dict(os.environ, {"UV_PYTHON": "/cache/uv/python"}):
                    with patch("sys.executable", "/cache/uv/python"):
                        with patch("sys.path", ["/nonexistent/path"]):  # No valid framework source
                            with patch("pathlib.Path.cwd", return_value=user_project):
                                config = UVXConfiguration(use_working_directory_staging=True)
                                success = stage_uvx_framework(config)

                                # Should fail gracefully when source not found
                                assert success is False

                                # Should not create any directories
                                claude_dir = user_project / ".claude"
                                assert not claude_dir.exists()

            finally:
                os.chdir(original_cwd)

    def test_integration_with_corrupted_framework_source(self):
        """Test integration with corrupted framework source."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup corrupted framework (missing .claude directory)
            site_packages = Path(temp_dir) / "site-packages"
            site_packages.mkdir()

            amplihack_package = site_packages / "amplihack"
            amplihack_package.mkdir()
            # Note: No .claude directory created - this is the corruption

            user_project = Path(temp_dir) / "corrupted_test"
            user_project.mkdir()

            original_cwd = os.getcwd()

            try:
                os.chdir(str(user_project))

                with patch.dict(os.environ, {"UV_PYTHON": "/cache/uv/python"}):
                    with patch("sys.executable", "/cache/uv/python"):
                        with patch("sys.path", [str(site_packages)]):
                            with patch("pathlib.Path.cwd", return_value=user_project):
                                config = UVXConfiguration(use_working_directory_staging=True)
                                success = stage_uvx_framework(config)

                                # Should fail gracefully with corrupted source
                                assert success is False

            finally:
                os.chdir(original_cwd)


class TestUVXIntegrationCleanup:
    """Integration tests for cleanup functionality."""

    def test_integration_staging_with_cleanup(self):
        """Test integration staging with cleanup enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup framework
            site_packages = Path(temp_dir) / "site-packages"
            site_packages.mkdir()

            amplihack_package = site_packages / "amplihack"
            amplihack_package.mkdir()

            claude_dir = amplihack_package / ".claude"
            claude_dir.mkdir()
            (claude_dir / "cleanup_test.txt").write_text("cleanup test content")

            user_project = Path(temp_dir) / "cleanup_project"
            user_project.mkdir()

            original_cwd = os.getcwd()

            try:
                os.chdir(str(user_project))

                with patch.dict(os.environ, {"UV_PYTHON": "/cache/uv/python"}):
                    with patch("sys.executable", "/cache/uv/python"):
                        with patch("sys.path", [str(site_packages)]):
                            with patch("pathlib.Path.cwd", return_value=user_project):
                                config = UVXConfiguration(
                                    use_working_directory_staging=True, cleanup_on_exit=True
                                )

                                stager = UVXStager(config)
                                staging_result = stager.stage_framework_files()

                                assert staging_result.is_successful

                                # Verify files staged
                                staged_file = user_project / ".claude" / "cleanup_test.txt"
                                assert staged_file.exists()

                                # Test cleanup
                                cleaned_count = stager.cleanup_staged_files(staging_result)

                                # Verify cleanup
                                assert cleaned_count > 0
                                assert not staged_file.exists()
                                assert not (user_project / ".claude").exists()

            finally:
                os.chdir(original_cwd)

    def test_integration_staging_cleanup_disabled(self):
        """Test integration staging with cleanup disabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup framework
            site_packages = Path(temp_dir) / "site-packages"
            site_packages.mkdir()

            amplihack_package = site_packages / "amplihack"
            amplihack_package.mkdir()

            claude_dir = amplihack_package / ".claude"
            claude_dir.mkdir()
            (claude_dir / "no_cleanup_test.txt").write_text("no cleanup test")

            user_project = Path(temp_dir) / "no_cleanup_project"
            user_project.mkdir()

            original_cwd = os.getcwd()

            try:
                os.chdir(str(user_project))

                with patch.dict(os.environ, {"UV_PYTHON": "/cache/uv/python"}):
                    with patch("sys.executable", "/cache/uv/python"):
                        with patch("sys.path", [str(site_packages)]):
                            with patch("pathlib.Path.cwd", return_value=user_project):
                                config = UVXConfiguration(
                                    use_working_directory_staging=True, cleanup_on_exit=False
                                )

                                stager = UVXStager(config)
                                staging_result = stager.stage_framework_files()

                                assert staging_result.is_successful

                                # Verify files staged
                                staged_file = user_project / ".claude" / "no_cleanup_test.txt"
                                assert staged_file.exists()

                                # Test cleanup (should be disabled)
                                cleaned_count = stager.cleanup_staged_files(staging_result)

                                # Verify no cleanup occurred
                                assert cleaned_count == 0
                                assert staged_file.exists()

            finally:
                os.chdir(original_cwd)


@pytest.mark.integration
class TestRealWorldUVXScenarios:
    """Real-world scenario tests for UVX integration."""

    def test_real_world_python_project_structure(self):
        """Test with realistic Python project structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create realistic framework
            site_packages = Path(temp_dir) / "site-packages"
            site_packages.mkdir()

            amplihack_package = site_packages / "amplihack"
            amplihack_package.mkdir()

            # Real framework structure
            claude_dir = amplihack_package / ".claude"
            claude_dir.mkdir()

            # Realistic context files
            context_dir = claude_dir / "context"
            context_dir.mkdir()
            (context_dir / "PHILOSOPHY.md").write_text("""
# Philosophy

## Ruthless Simplicity
- Start with the simplest solution that works
- Add complexity only when justified

## Modular Design
- Brick = Self-contained module with ONE responsibility
- Stud = Public contract others connect to
""")

            # Agent definitions
            agents_dir = claude_dir / "agents"
            agents_dir.mkdir()
            amplihack_agents = agents_dir / "amplihack"
            amplihack_agents.mkdir()

            (amplihack_agents / "architect.md").write_text("""
# Architect Agent

You design system architecture and module boundaries.

## Responsibilities
- System design specifications
- Module boundary definitions
- Interface contracts
""")

            # Settings with real configuration
            settings_content = {
                "model": "claude-3-5-sonnet-20241022",
                "tools": {
                    "bash": {"enabled": True},
                    "read": {"enabled": True},
                    "edit": {"enabled": True},
                },
                "uvx_settings": {
                    "working_directory_staging": True,
                    "cleanup_on_exit": False,
                    "handle_existing_claude_dir": "backup",
                },
            }
            (claude_dir / "settings.json").write_text(json.dumps(settings_content, indent=2))

            # Create realistic Python project
            user_project = Path(temp_dir) / "my_ai_assistant"
            user_project.mkdir()

            # Project structure
            (user_project / "README.md").write_text("# My AI Assistant\nA Claude-powered assistant")
            (user_project / "requirements.txt").write_text("""
anthropic>=0.25.0
requests>=2.31.0
pydantic>=2.0.0
""")

            src_dir = user_project / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").write_text("")
            (src_dir / "main.py").write_text("""
import anthropic

def main():
    client = anthropic.Anthropic()
    # Application logic here
    pass

if __name__ == "__main__":
    main()
""")

            tests_dir = user_project / "tests"
            tests_dir.mkdir()
            (tests_dir / "__init__.py").write_text("")
            (tests_dir / "test_main.py").write_text("# Tests go here")

            original_cwd = os.getcwd()

            try:
                os.chdir(str(user_project))

                with patch.dict(
                    os.environ, {"UV_PYTHON": "/home/user/.cache/uv/installations/python"}
                ):
                    with patch("sys.executable", "/home/user/.cache/uv/installations/python"):
                        with patch("sys.path", [str(site_packages)]):
                            with patch("pathlib.Path.cwd", return_value=user_project):
                                # Real-world configuration
                                config = UVXConfiguration(
                                    use_working_directory_staging=True,
                                    working_directory_subdir=".claude",
                                    handle_existing_claude_dir="backup",
                                    cleanup_on_exit=False,  # Preserve for development
                                    debug_enabled=False,
                                )

                                success = stage_uvx_framework(config)

                                # Verify real-world scenario works
                                assert success is True

                                # Verify framework integration
                                staged_claude = user_project / ".claude"
                                assert staged_claude.exists()

                                # Verify specific files
                                philosophy_file = staged_claude / "context" / "PHILOSOPHY.md"
                                assert philosophy_file.exists()
                                assert "Ruthless Simplicity" in philosophy_file.read_text()

                                architect_file = (
                                    staged_claude / "agents" / "amplihack" / "architect.md"
                                )
                                assert architect_file.exists()
                                assert "system architecture" in architect_file.read_text()

                                settings_file = staged_claude / "settings.json"
                                assert settings_file.exists()
                                settings_data = json.loads(settings_file.read_text())
                                assert (
                                    settings_data["uvx_settings"]["working_directory_staging"]
                                    is True
                                )

                                # Verify user project preserved
                                assert (user_project / "src" / "main.py").exists()
                                assert (user_project / "tests" / "test_main.py").exists()
                                assert "anthropic" in (user_project / "src" / "main.py").read_text()

                                # Verify project can continue development
                                assert Path.cwd() == user_project
                                assert (user_project / "requirements.txt").exists()

            finally:
                os.chdir(original_cwd)

    def test_real_world_multiple_projects_isolation(self):
        """Test that multiple projects are properly isolated."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Single framework source
            site_packages = Path(temp_dir) / "site-packages"
            site_packages.mkdir()

            amplihack_package = site_packages / "amplihack"
            amplihack_package.mkdir()

            claude_dir = amplihack_package / ".claude"
            claude_dir.mkdir()
            (claude_dir / "shared_framework.txt").write_text("shared framework content")

            # Multiple user projects
            project_names = ["web_app", "data_analysis", "ai_research"]
            projects = {}

            for project_name in project_names:
                project_dir = Path(temp_dir) / project_name
                project_dir.mkdir()
                (project_dir / f"{project_name}_main.py").write_text(
                    f"# {project_name} application"
                )
                projects[project_name] = project_dir

            original_cwd = os.getcwd()

            try:
                # Test each project independently
                for project_name, project_dir in projects.items():
                    os.chdir(str(project_dir))

                    with patch.dict(os.environ, {"UV_PYTHON": "/cache/uv/python"}):
                        with patch("sys.executable", "/cache/uv/python"):
                            with patch("sys.path", [str(site_packages)]):
                                with patch("pathlib.Path.cwd", return_value=project_dir):
                                    config = UVXConfiguration(use_working_directory_staging=True)
                                    success = stage_uvx_framework(config)

                                    assert success is True

                                    # Verify each project has its own .claude directory
                                    project_claude = project_dir / ".claude"
                                    assert project_claude.exists()
                                    assert (project_claude / "shared_framework.txt").exists()

                                    # Verify project-specific files preserved
                                    project_main = project_dir / f"{project_name}_main.py"
                                    assert project_main.exists()
                                    assert project_name in project_main.read_text()

                # Verify isolation - each project has independent .claude
                for project_name, project_dir in projects.items():
                    project_claude = project_dir / ".claude"
                    assert project_claude.exists()

                    # Verify other projects don't interfere
                    for other_name, other_dir in projects.items():
                        if other_name != project_name:
                            # Other projects' files should not be in this project's .claude
                            other_main_name = f"{other_name}_main.py"
                            assert not (project_claude / other_main_name).exists()

            finally:
                os.chdir(original_cwd)
