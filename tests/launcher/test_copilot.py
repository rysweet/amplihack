"""Tests for Copilot CLI launcher update functionality."""

import platform
import subprocess
from unittest.mock import Mock, patch

import pytest

from amplihack.launcher.copilot import (
    check_copilot,
    check_for_update,
    detect_install_method,
    execute_update,
    generate_copilot_instructions,
    prompt_user_to_update,
    stage_agents,
    stage_directory,
)


class TestCheckForUpdate:
    """Tests for check_for_update function."""

    @patch("subprocess.run")
    def test_update_available(self, mock_run):
        """Test when a newer version is available."""
        # Mock current version check
        mock_current = Mock()
        mock_current.returncode = 0
        mock_current.stdout = "@github/copilot/1.0.0 linux-x64 node-v20.10.0"

        # Mock latest version check
        mock_latest = Mock()
        mock_latest.returncode = 0
        mock_latest.stdout = "1.1.0"

        mock_run.side_effect = [mock_current, mock_latest]

        result = check_for_update()
        assert result == "1.1.0"

    @patch("subprocess.run")
    def test_no_update_available(self, mock_run):
        """Test when current version is latest."""
        # Mock current version check
        mock_current = Mock()
        mock_current.returncode = 0
        mock_current.stdout = "@github/copilot/1.1.0 linux-x64 node-v20.10.0"

        # Mock latest version check
        mock_latest = Mock()
        mock_latest.returncode = 0
        mock_latest.stdout = "1.1.0"

        mock_run.side_effect = [mock_current, mock_latest]

        result = check_for_update()
        assert result is None

    @patch("subprocess.run")
    def test_version_check_fails(self, mock_run):
        """Test when version check fails."""
        mock_run.side_effect = FileNotFoundError()

        result = check_for_update()
        assert result is None


class TestDetectInstallMethod:
    """Tests for detect_install_method function."""

    @patch("subprocess.run")
    def test_npm_installation(self, mock_run):
        """Test npm installation detection."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "/usr/local/lib/node_modules/@github/copilot"

        mock_run.return_value = mock_result

        result = detect_install_method()
        assert result == "npm"

    @patch("subprocess.run")
    def test_uvx_installation(self, mock_run):
        """Test uvx installation detection."""
        # First call (npm check) fails
        mock_npm = Mock()
        mock_npm.returncode = 1

        # Second call (uvx check) succeeds
        mock_uvx = Mock()
        mock_uvx.returncode = 0
        mock_uvx.stdout = "copilot installed"

        mock_run.side_effect = [mock_npm, mock_uvx]

        result = detect_install_method()
        assert result == "uvx"

    @patch("subprocess.run")
    def test_uvx_via_npm_path(self, mock_run):
        """Test uvx detection via uv/tools in npm path."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "/home/user/.local/share/uv/tools/@github/copilot"

        mock_run.return_value = mock_result

        result = detect_install_method()
        assert result == "uvx"


class TestPromptUserToUpdate:
    """Tests for prompt_user_to_update function."""

    @patch("builtins.input", return_value="y")
    def test_user_says_yes(self, mock_input):
        """Test when user confirms update."""
        result = prompt_user_to_update("1.1.0", "npm")
        assert result is True

    @patch("builtins.input", return_value="n")
    def test_user_says_no(self, mock_input):
        """Test when user declines update."""
        result = prompt_user_to_update("1.1.0", "npm")
        assert result is False

    @patch("builtins.input", return_value="")
    def test_user_presses_enter(self, mock_input):
        """Test when user just presses enter (default No)."""
        result = prompt_user_to_update("1.1.0", "npm")
        assert result is False

    @patch("builtins.input", side_effect=EOFError())
    def test_eof_error(self, mock_input):
        """Test EOFError handling (non-interactive)."""
        result = prompt_user_to_update("1.1.0", "npm")
        assert result is False

    @patch("builtins.input")
    @patch("threading.Thread")
    def test_timeout_windows(self, mock_thread, mock_input):
        """Test timeout on Windows platform."""
        if platform.system() != "Windows":
            pytest.skip("Windows-specific test")

        # Simulate thread timeout by making it never complete
        mock_thread_instance = Mock()
        mock_thread_instance.is_alive.return_value = True
        mock_thread.return_value = mock_thread_instance

        result = prompt_user_to_update("1.1.0", "npm")
        assert result is False

    @patch("builtins.input")
    @patch("signal.signal")
    @patch("signal.alarm")
    def test_timeout_unix(self, mock_alarm, mock_signal, mock_input):
        """Test timeout on Unix platform."""
        if platform.system() == "Windows":
            pytest.skip("Unix-specific test")

        # Simulate timeout by raising TimeoutError
        mock_input.side_effect = TimeoutError()

        result = prompt_user_to_update("1.1.0", "npm")
        assert result is False


class TestExecuteUpdate:
    """Tests for execute_update function."""

    @patch("subprocess.run")
    def test_npm_update_success(self, mock_run):
        """Test successful npm update."""
        # Mock pre-version check
        mock_pre = Mock()
        mock_pre.returncode = 0
        mock_pre.stdout = "@github/copilot/1.0.0 linux-x64 node-v20.10.0"

        # Mock update command
        mock_update = Mock()
        mock_update.returncode = 0
        mock_update.stdout = "updated @github/copilot"
        mock_update.stderr = ""

        # Mock post-version check
        mock_post = Mock()
        mock_post.returncode = 0
        mock_post.stdout = "@github/copilot/1.1.0 linux-x64 node-v20.10.0"

        mock_run.side_effect = [mock_pre, mock_update, mock_post]

        result = execute_update("npm")
        assert result is True

    @patch("subprocess.run")
    def test_uvx_update_success(self, mock_run):
        """Test successful uvx update."""
        # Mock pre-version check
        mock_pre = Mock()
        mock_pre.returncode = 0
        mock_pre.stdout = "@github/copilot/1.0.0 linux-x64 node-v20.10.0"

        # Mock update command (uvx runs copilot --version with latest)
        mock_update = Mock()
        mock_update.returncode = 0
        mock_update.stdout = "@github/copilot/1.1.0 linux-x64 node-v20.10.0"
        mock_update.stderr = ""

        # Mock post-version check
        mock_post = Mock()
        mock_post.returncode = 0
        mock_post.stdout = "@github/copilot/1.1.0 linux-x64 node-v20.10.0"

        mock_run.side_effect = [mock_pre, mock_update, mock_post]

        result = execute_update("uvx")
        assert result is True

    @patch("subprocess.run")
    def test_update_command_fails(self, mock_run):
        """Test when update command fails."""
        # Mock pre-version check
        mock_pre = Mock()
        mock_pre.returncode = 0
        mock_pre.stdout = "@github/copilot/1.0.0 linux-x64 node-v20.10.0"

        # Mock update command failure
        mock_update = Mock()
        mock_update.returncode = 1
        mock_update.stderr = "Error: Permission denied"

        mock_run.side_effect = [mock_pre, mock_update]

        result = execute_update("npm")
        assert result is False

    @patch("subprocess.run")
    def test_update_timeout(self, mock_run):
        """Test when update command times out."""
        # Mock pre-version check
        mock_pre = Mock()
        mock_pre.returncode = 0
        mock_pre.stdout = "@github/copilot/1.0.0 linux-x64 node-v20.10.0"

        # Mock update timeout
        mock_run.side_effect = [mock_pre, subprocess.TimeoutExpired("npm", 60)]

        result = execute_update("npm")
        assert result is False

    @patch("subprocess.run")
    def test_update_tool_not_found(self, mock_run):
        """Test when update tool is not found."""
        # Mock pre-version check
        mock_pre = Mock()
        mock_pre.returncode = 0
        mock_pre.stdout = "@github/copilot/1.0.0 linux-x64 node-v20.10.0"

        # Mock update tool not found
        mock_run.side_effect = [mock_pre, FileNotFoundError()]

        result = execute_update("npm")
        assert result is False

    @patch("subprocess.run")
    def test_version_verification_success(self, mock_run):
        """Test update success with version verification."""
        # Mock pre-version check
        mock_pre = Mock()
        mock_pre.returncode = 0
        mock_pre.stdout = "@github/copilot/1.0.0 linux-x64 node-v20.10.0"

        # Mock update command
        mock_update = Mock()
        mock_update.returncode = 0
        mock_update.stdout = ""
        mock_update.stderr = ""

        # Mock post-version check with new version
        mock_post = Mock()
        mock_post.returncode = 0
        mock_post.stdout = "@github/copilot/1.1.0 linux-x64 node-v20.10.0"

        mock_run.side_effect = [mock_pre, mock_update, mock_post]

        result = execute_update("npm")
        assert result is True

    @patch("subprocess.run")
    def test_update_without_version_change(self, mock_run):
        """Test when update succeeds but version doesn't change (already latest)."""
        # Mock pre-version check
        mock_pre = Mock()
        mock_pre.returncode = 0
        mock_pre.stdout = "@github/copilot/1.0.0 linux-x64 node-v20.10.0"

        # Mock update command
        mock_update = Mock()
        mock_update.returncode = 0
        mock_update.stdout = ""
        mock_update.stderr = ""

        # Mock post-version check with same version
        mock_post = Mock()
        mock_post.returncode = 0
        mock_post.stdout = "@github/copilot/1.0.0 linux-x64 node-v20.10.0"

        mock_run.side_effect = [mock_pre, mock_update, mock_post]

        result = execute_update("npm")
        # Should still return True if update command succeeded
        assert result is True


class TestCheckCopilot:
    """Tests for check_copilot function."""

    @patch("subprocess.run")
    def test_check_copilot_installed(self, mock_run):
        """Test check_copilot when copilot is installed."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = check_copilot()
        assert result is True
        mock_run.assert_called_once_with(
            ["copilot", "--version"], capture_output=True, timeout=5, check=False
        )

    @patch("subprocess.run")
    def test_check_copilot_not_found(self, mock_run):
        """Test check_copilot when copilot is not installed."""
        mock_run.side_effect = FileNotFoundError()

        result = check_copilot()
        assert result is False

    @patch("subprocess.run")
    def test_check_copilot_permission_error(self, mock_run):
        """Test check_copilot handles PermissionError (WSL bug fix #2210)."""
        mock_run.side_effect = PermissionError("Permission denied")

        result = check_copilot()
        assert result is False

    @patch("subprocess.run")
    def test_check_copilot_timeout(self, mock_run):
        """Test check_copilot handles timeout gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired("copilot", 5)

        result = check_copilot()
        assert result is False


class TestStageAgents:
    """Tests for agent staging to ~/.copilot/agents/ (issue #2241)."""

    def test_stages_agents_to_user_copilot_dir(self, tmp_path):
        """Agents must be staged to ~/.copilot/agents/, not project-local."""
        # Create fake source agents
        source_dir = tmp_path / "source" / ".claude" / "agents" / "amplihack"
        core_dir = source_dir / "core"
        core_dir.mkdir(parents=True)
        (core_dir / "architect.md").write_text("# Architect agent")
        (core_dir / "builder.md").write_text("# Builder agent")
        specialized_dir = source_dir / "specialized"
        specialized_dir.mkdir(parents=True)
        (specialized_dir / "security.md").write_text("# Security agent")

        # Create fake copilot home
        copilot_home = tmp_path / "copilot_home"

        result = stage_agents(source_dir, copilot_home)

        # Agents should be in copilot_home/agents/amplihack/ (flattened, namespaced)
        agents_dir = copilot_home / "agents" / "amplihack"
        assert agents_dir.exists()
        assert (agents_dir / "architect.md").exists()
        assert (agents_dir / "builder.md").exists()
        assert (agents_dir / "security.md").exists()
        assert result == 3

    def test_stages_agents_flattened(self, tmp_path):
        """Agent subdirectory structure should be flattened."""
        source_dir = tmp_path / "source"
        core_dir = source_dir / "core"
        core_dir.mkdir(parents=True)
        (core_dir / "architect.md").write_text("# Architect")
        workflows_dir = source_dir / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "improvement.md").write_text("# Improvement")

        copilot_home = tmp_path / "copilot_home"

        stage_agents(source_dir, copilot_home)

        agents_dir = copilot_home / "agents" / "amplihack"
        # All files flattened to single directory
        assert (agents_dir / "architect.md").exists()
        assert (agents_dir / "improvement.md").exists()
        # No subdirectories under amplihack/
        subdirs = [p for p in agents_dir.iterdir() if p.is_dir()]
        assert len(subdirs) == 0

    def test_cleans_stale_agents(self, tmp_path):
        """Stale agents should be cleaned from amplihack namespace only."""
        source_dir = tmp_path / "source" / "core"
        source_dir.mkdir(parents=True)
        (source_dir / "architect.md").write_text("# Architect")

        copilot_home = tmp_path / "copilot_home"
        agents_dir = copilot_home / "agents" / "amplihack"
        agents_dir.mkdir(parents=True)
        # Pre-existing stale agent in amplihack namespace
        (agents_dir / "old-removed-agent.md").write_text("# Old agent")
        
        # User agent outside amplihack namespace
        user_agents_dir = copilot_home / "agents"
        (user_agents_dir / "user-custom-agent.md").write_text("# User agent")

        stage_agents(source_dir.parent, copilot_home)

        assert (agents_dir / "architect.md").exists()
        # Stale amplihack agent should be removed
        assert not (agents_dir / "old-removed-agent.md").exists()
        # User agent should be preserved
        assert (user_agents_dir / "user-custom-agent.md").exists()

    def test_handles_missing_source_dir(self, tmp_path):
        """Returns 0 if source directory doesn't exist."""
        source_dir = tmp_path / "nonexistent"
        copilot_home = tmp_path / "copilot_home"

        result = stage_agents(source_dir, copilot_home)
        assert result == 0

    def test_creates_agents_dir_if_missing(self, tmp_path):
        """Creates ~/.copilot/agents/amplihack/ if it doesn't exist."""
        source_dir = tmp_path / "source" / "core"
        source_dir.mkdir(parents=True)
        (source_dir / "test.md").write_text("# Test")

        copilot_home = tmp_path / "copilot_home"
        assert not copilot_home.exists()

        stage_agents(source_dir.parent, copilot_home)

        assert (copilot_home / "agents" / "amplihack").exists()


class TestStageDirectory:
    """Tests for generic directory staging (workflows, context, commands)."""

    def test_stages_workflow_files(self, tmp_path):
        """Workflow .md files must be staged to ~/.copilot/workflow/amplihack/."""
        source = tmp_path / "workflow"
        source.mkdir()
        (source / "DEFAULT_WORKFLOW.md").write_text("# 23 steps")
        (source / "INVESTIGATION_WORKFLOW.md").write_text("# 6 phases")

        copilot_home = tmp_path / "copilot"
        result = stage_directory(source, copilot_home, "workflow")

        assert (copilot_home / "workflow" / "amplihack" / "DEFAULT_WORKFLOW.md").exists()
        assert (copilot_home / "workflow" / "amplihack" / "INVESTIGATION_WORKFLOW.md").exists()
        assert result == 2

    def test_stages_context_files(self, tmp_path):
        """Context .md files must be staged to ~/.copilot/context/amplihack/."""
        source = tmp_path / "context"
        source.mkdir()
        (source / "PHILOSOPHY.md").write_text("# Ruthless Simplicity")
        (source / "PATTERNS.md").write_text("# Brick & Studs")

        copilot_home = tmp_path / "copilot"
        result = stage_directory(source, copilot_home, "context")

        assert (copilot_home / "context" / "amplihack" / "PHILOSOPHY.md").exists()
        content = (copilot_home / "context" / "amplihack" / "PHILOSOPHY.md").read_text()
        assert "Ruthless Simplicity" in content
        assert result == 2

    def test_stages_commands_flattened(self, tmp_path):
        """Commands from subdirectories must be flattened to ~/.copilot/commands/amplihack/."""
        source = tmp_path / "commands" / "amplihack"
        source.mkdir(parents=True)
        (source / "ultrathink.md").write_text("# Ultra-Think")
        (source / "analyze.md").write_text("# Analyze")

        copilot_home = tmp_path / "copilot"
        result = stage_directory(source.parent, copilot_home, "commands")

        assert (copilot_home / "commands" / "amplihack" / "ultrathink.md").exists()
        assert (copilot_home / "commands" / "amplihack" / "analyze.md").exists()
        assert result == 2

    def test_handles_missing_source(self, tmp_path):
        """Returns 0 if source directory doesn't exist."""
        copilot_home = tmp_path / "copilot"
        result = stage_directory(tmp_path / "nonexistent", copilot_home, "workflow")
        assert result == 0

    def test_cleans_stale_files(self, tmp_path):
        """Old files in amplihack namespace should be cleaned, user files preserved."""
        source = tmp_path / "workflow"
        source.mkdir()
        (source / "NEW.md").write_text("# New")

        copilot_home = tmp_path / "copilot"
        dest = copilot_home / "workflow" / "amplihack"
        dest.mkdir(parents=True)
        (dest / "OLD_REMOVED.md").write_text("# Gone")
        
        # User file outside amplihack namespace
        user_dest = copilot_home / "workflow"
        (user_dest / "USER_WORKFLOW.md").write_text("# User workflow")

        stage_directory(source, copilot_home, "workflow")

        assert (dest / "NEW.md").exists()
        # Stale amplihack file should be removed
        assert not (dest / "OLD_REMOVED.md").exists()
        # User file should be preserved
        assert (user_dest / "USER_WORKFLOW.md").exists()


class TestGenerateCopilotInstructions:
    """Tests for copilot-instructions.md generation."""

    def test_generates_instructions_file(self, tmp_path):
        """Must create ~/.copilot/copilot-instructions.md."""
        copilot_home = tmp_path / "copilot"
        copilot_home.mkdir()

        generate_copilot_instructions(copilot_home)

        instructions = copilot_home / "copilot-instructions.md"
        assert instructions.exists()

    def test_instructions_reference_workflow_path(self, tmp_path):
        """Instructions must tell copilot where workflows are."""
        copilot_home = tmp_path / "copilot"
        copilot_home.mkdir()

        generate_copilot_instructions(copilot_home)

        content = (copilot_home / "copilot-instructions.md").read_text()
        assert "workflow" in content.lower()
        assert "DEFAULT_WORKFLOW" in content

    def test_instructions_reference_context_path(self, tmp_path):
        """Instructions must tell copilot where context files are."""
        copilot_home = tmp_path / "copilot"
        copilot_home.mkdir()

        generate_copilot_instructions(copilot_home)

        content = (copilot_home / "copilot-instructions.md").read_text()
        assert "context" in content.lower()
        assert "PHILOSOPHY" in content

    def test_instructions_reference_commands(self, tmp_path):
        """Instructions must tell copilot about available commands."""
        copilot_home = tmp_path / "copilot"
        copilot_home.mkdir()

        generate_copilot_instructions(copilot_home)

        content = (copilot_home / "copilot-instructions.md").read_text()
        assert "command" in content.lower()
        assert "ultrathink" in content.lower()

    def test_preserves_existing_user_content(self, tmp_path):
        """Must NOT overwrite user's existing instructions."""
        copilot_home = tmp_path / "copilot"
        copilot_home.mkdir()
        instructions = copilot_home / "copilot-instructions.md"
        instructions.write_text("# My Custom Instructions\nAlways use TypeScript.\n")

        generate_copilot_instructions(copilot_home)

        content = instructions.read_text()
        # User content preserved
        assert "My Custom Instructions" in content
        assert "Always use TypeScript" in content
        # Amplihack section added
        assert "Amplihack Framework" in content
        assert "DEFAULT_WORKFLOW" in content

    def test_updates_existing_amplihack_section(self, tmp_path):
        """Must replace old amplihack section, not duplicate it."""
        copilot_home = tmp_path / "copilot"
        copilot_home.mkdir()
        instructions = copilot_home / "copilot-instructions.md"
        # Simulate file with user content + old amplihack section
        instructions.write_text(
            "# User stuff\n\n"
            "<!-- AMPLIHACK_INSTRUCTIONS_START -->\nOLD CONTENT\n<!-- AMPLIHACK_INSTRUCTIONS_END -->\n"
        )

        generate_copilot_instructions(copilot_home)

        content = instructions.read_text()
        assert "User stuff" in content
        assert "OLD CONTENT" not in content
        assert "DEFAULT_WORKFLOW" in content
        # Only one amplihack section
        assert content.count("AMPLIHACK_INSTRUCTIONS_START") == 1

    def test_auto_derives_workflow_step_count(self, tmp_path):
        """Must auto-derive workflow step count from DEFAULT_WORKFLOW.md."""
        copilot_home = tmp_path / "copilot"
        workflow_dir = copilot_home / "workflow" / "amplihack"
        workflow_dir.mkdir(parents=True)
        
        # Create workflow with known number of steps (including decimal steps)
        workflow_content = """
name: DEFAULT_WORKFLOW

### Step 0: First step
### Step 1: Second step
### Step 2: Third step
### Step 2.5: Decimal step
### Step 3: Fourth step
"""
        (workflow_dir / "DEFAULT_WORKFLOW.md").write_text(workflow_content)
        
        generate_copilot_instructions(copilot_home)
        
        content = (copilot_home / "copilot-instructions.md").read_text()
        # Should contain auto-derived count (5 steps: 0, 1, 2, 2.5, 3)
        assert "(5 steps)" in content
        assert "(23 steps)" not in content  # Should not hard-code

    def test_handles_missing_workflow_for_step_count(self, tmp_path):
        """Must handle missing DEFAULT_WORKFLOW.md gracefully."""
        copilot_home = tmp_path / "copilot"
        copilot_home.mkdir()
        
        generate_copilot_instructions(copilot_home)
        
        content = (copilot_home / "copilot-instructions.md").read_text()
        # Should fall back to generic description
        assert "Standard development workflow" in content
        # Should not crash or include step count if file missing
        assert "DEFAULT_WORKFLOW" in content
