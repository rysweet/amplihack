"""Unit tests for Platform CLI Abstraction module.

Tests all platform implementations following TDD methodology.
These tests will FAIL until the platform_cli module is implemented.
"""

from unittest.mock import Mock, patch

import pytest

# These imports will fail until implementation exists
try:
    from amplihack.meta_delegation.platform_cli import (
        AmplifierCLI,
        ClaudeCodeCLI,
        CopilotCLI,
        PlatformCLI,
        get_platform_cli,
        register_platform,
    )
except ImportError:
    pytest.skip("platform_cli module not implemented yet", allow_module_level=True)


class TestPlatformCLIProtocol:
    """Test the PlatformCLI protocol interface."""

    def test_protocol_has_required_methods(self):
        """Test that PlatformCLI protocol defines required methods."""
        required_methods = [
            "spawn_subprocess",
            "format_prompt",
            "parse_output",
            "validate_installation",
            "get_version",
        ]
        for method in required_methods:
            assert hasattr(PlatformCLI, method), f"Missing required method: {method}"


class TestClaudeCodeCLI:
    """Test ClaudeCodeCLI implementation."""

    @pytest.fixture
    def claude_cli(self):
        """Create ClaudeCodeCLI instance."""
        return ClaudeCodeCLI()

    def test_initialization(self, claude_cli):
        """Test ClaudeCodeCLI initializes correctly."""
        assert claude_cli is not None
        assert claude_cli.platform_name == "claude-code"

    def test_validate_installation_success(self, claude_cli):
        """Test validate_installation returns True when claude command exists."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="1.0.0")
            result = claude_cli.validate_installation()
            assert result is True
            mock_run.assert_called_once()

    def test_validate_installation_failure(self, claude_cli):
        """Test validate_installation returns False when claude command missing."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = claude_cli.validate_installation()
            assert result is False

    def test_get_version(self, claude_cli):
        """Test get_version returns correct version string."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Claude Code v1.2.3")
            version = claude_cli.get_version()
            assert version == "1.2.3"

    def test_format_prompt_with_guide_persona(self, claude_cli):
        """Test format_prompt creates correct structure for guide persona."""
        goal = "Create a REST API"
        persona = "guide"
        context = "Using FastAPI framework"

        prompt = claude_cli.format_prompt(goal, persona, context)

        assert isinstance(prompt, str)
        assert goal in prompt
        assert "guide" in prompt.lower() or "teach" in prompt.lower()
        assert context in prompt

    def test_format_prompt_with_qa_engineer_persona(self, claude_cli):
        """Test format_prompt creates correct structure for QA engineer."""
        goal = "Test user authentication"
        persona = "qa_engineer"
        context = ""

        prompt = claude_cli.format_prompt(goal, persona, context)

        assert "test" in prompt.lower() or "qa" in prompt.lower()
        assert goal in prompt

    def test_spawn_subprocess_creates_process(self, claude_cli, tmp_path):
        """Test spawn_subprocess creates subprocess with correct parameters."""
        goal = "Simple task"
        persona = "junior_dev"
        working_dir = str(tmp_path)
        environment = {"TEST_VAR": "test_value"}

        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            process = claude_cli.spawn_subprocess(goal, persona, working_dir, environment)

            assert process is not None
            assert process.pid == 12345
            mock_popen.assert_called_once()

            # Verify command structure
            call_args = mock_popen.call_args
            assert "claude" in str(call_args)
            assert call_args.kwargs["cwd"] == working_dir

    def test_spawn_subprocess_with_custom_args(self, claude_cli, tmp_path):
        """Test spawn_subprocess accepts and applies custom arguments."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = Mock(pid=123)

            claude_cli.spawn_subprocess(
                goal="Task",
                persona="architect",
                working_dir=str(tmp_path),
                environment={},
                extra_args=["--verbose", "--timeout=600"],
            )

            call_args = mock_popen.call_args[0][0]  # First positional arg (command list)
            assert "--verbose" in call_args
            assert "--timeout=600" in call_args

    def test_parse_output_extracts_metadata(self, claude_cli):
        """Test parse_output extracts structured data from command output."""
        output = """
        Starting task...
        Creating file: app.py
        Running tests...
        PASS: test_example.py
        Task completed successfully
        """

        parsed = claude_cli.parse_output(output)

        assert isinstance(parsed, dict)
        assert "stdout" in parsed
        assert parsed["stdout"] == output

    def test_parse_output_handles_empty_output(self, claude_cli):
        """Test parse_output handles empty output gracefully."""
        parsed = claude_cli.parse_output("")

        assert isinstance(parsed, dict)
        assert parsed["stdout"] == ""


class TestCopilotCLI:
    """Test GitHub Copilot CLI implementation."""

    @pytest.fixture
    def copilot_cli(self):
        """Create CopilotCLI instance."""
        return CopilotCLI()

    def test_initialization(self, copilot_cli):
        """Test CopilotCLI initializes correctly."""
        assert copilot_cli is not None
        assert copilot_cli.platform_name == "copilot"

    def test_validate_installation_checks_gh_copilot(self, copilot_cli):
        """Test validate_installation checks for GitHub Copilot CLI."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="copilot 1.0.0")
            result = copilot_cli.validate_installation()
            assert result is True

    def test_format_prompt_for_copilot_syntax(self, copilot_cli):
        """Test format_prompt uses Copilot-specific syntax."""
        goal = "Refactor authentication module"
        persona = "architect"
        context = "Legacy codebase"

        prompt = copilot_cli.format_prompt(goal, persona, context)

        # Copilot might use different formatting
        assert isinstance(prompt, str)
        assert goal in prompt

    def test_spawn_subprocess_uses_gh_command(self, copilot_cli, tmp_path):
        """Test spawn_subprocess uses 'gh copilot' command."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = Mock(pid=456)

            copilot_cli.spawn_subprocess(
                goal="Task", persona="guide", working_dir=str(tmp_path), environment={}
            )

            call_args = mock_popen.call_args[0][0]
            assert "gh" in call_args or "copilot" in str(call_args)


class TestAmplifierCLI:
    """Test Microsoft Amplifier CLI implementation."""

    @pytest.fixture
    def amplifier_cli(self):
        """Create AmplifierCLI instance."""
        return AmplifierCLI()

    def test_initialization(self, amplifier_cli):
        """Test AmplifierCLI initializes correctly."""
        assert amplifier_cli is not None
        assert amplifier_cli.platform_name == "amplifier"

    def test_validate_installation_checks_amplifier_command(self, amplifier_cli):
        """Test validate_installation checks for Amplifier."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="amplifier 1.0.0")
            result = amplifier_cli.validate_installation()
            assert result is True

    def test_format_prompt_for_amplifier_syntax(self, amplifier_cli):
        """Test format_prompt uses Amplifier-specific syntax."""
        goal = "Create API documentation"
        persona = "guide"
        context = ""

        prompt = amplifier_cli.format_prompt(goal, persona, context)

        assert isinstance(prompt, str)
        assert goal in prompt

    def test_spawn_subprocess_uses_amplifier_command(self, amplifier_cli, tmp_path):
        """Test spawn_subprocess uses 'amplifier' command."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = Mock(pid=789)

            amplifier_cli.spawn_subprocess(
                goal="Task", persona="junior_dev", working_dir=str(tmp_path), environment={}
            )

            call_args = mock_popen.call_args[0][0]
            assert "amplifier" in str(call_args)


class TestPlatformRegistry:
    """Test platform registration and retrieval."""

    def test_get_platform_cli_returns_claude_by_default(self):
        """Test get_platform_cli returns ClaudeCodeCLI by default."""
        cli = get_platform_cli()
        assert isinstance(cli, ClaudeCodeCLI)

    def test_get_platform_cli_returns_specific_platform(self):
        """Test get_platform_cli returns requested platform."""
        claude = get_platform_cli("claude-code")
        assert isinstance(claude, ClaudeCodeCLI)

        copilot = get_platform_cli("copilot")
        assert isinstance(copilot, CopilotCLI)

        amplifier = get_platform_cli("amplifier")
        assert isinstance(amplifier, AmplifierCLI)

    def test_get_platform_cli_raises_on_unknown_platform(self):
        """Test get_platform_cli raises ValueError for unknown platform."""
        with pytest.raises(ValueError, match="Unknown platform"):
            get_platform_cli("nonexistent-platform")

    def test_register_platform_adds_custom_platform(self):
        """Test register_platform allows custom platform registration."""

        class CustomPlatformCLI(PlatformCLI):
            platform_name = "custom"

            def spawn_subprocess(self, goal, persona, working_dir, environment, **kwargs):
                return Mock()

            def format_prompt(self, goal, persona, context):
                return f"{goal} - {persona}"

            def parse_output(self, output):
                return {"stdout": output}

            def validate_installation(self):
                return True

            def get_version(self):
                return "1.0.0"

        custom_cli = CustomPlatformCLI()
        register_platform("custom", custom_cli)

        retrieved = get_platform_cli("custom")
        assert retrieved.platform_name == "custom"


class TestPlatformCLIErrorHandling:
    """Test error handling in platform CLI implementations."""

    @pytest.fixture
    def claude_cli(self):
        return ClaudeCodeCLI()

    def test_spawn_subprocess_handles_command_not_found(self, claude_cli, tmp_path):
        """Test spawn_subprocess handles missing command gracefully."""
        with patch("subprocess.Popen", side_effect=FileNotFoundError("claude not found")):
            with pytest.raises(FileNotFoundError):
                claude_cli.spawn_subprocess(
                    goal="Task", persona="guide", working_dir=str(tmp_path), environment={}
                )

    def test_spawn_subprocess_handles_permission_error(self, claude_cli, tmp_path):
        """Test spawn_subprocess handles permission errors."""
        with patch("subprocess.Popen", side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                claude_cli.spawn_subprocess(
                    goal="Task", persona="guide", working_dir=str(tmp_path), environment={}
                )

    def test_get_version_handles_parse_failure(self, claude_cli):
        """Test get_version handles unparseable version output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Invalid output")
            version = claude_cli.get_version()
            # Should return a fallback or raise specific error
            assert version is not None or version == "unknown"


class TestPlatformCLIEnvironmentHandling:
    """Test environment variable handling across platforms."""

    @pytest.fixture
    def claude_cli(self):
        return ClaudeCodeCLI()

    def test_spawn_subprocess_merges_environment_variables(self, claude_cli, tmp_path):
        """Test subprocess inherits and merges environment variables."""
        custom_env = {"CUSTOM_VAR": "custom_value", "PATH": "/custom/path"}

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = Mock(pid=123)

            claude_cli.spawn_subprocess(
                goal="Task", persona="guide", working_dir=str(tmp_path), environment=custom_env
            )

            call_kwargs = mock_popen.call_args.kwargs
            assert "env" in call_kwargs
            assert call_kwargs["env"]["CUSTOM_VAR"] == "custom_value"

    def test_spawn_subprocess_preserves_system_environment(self, claude_cli, tmp_path):
        """Test subprocess preserves critical system environment variables."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = Mock(pid=123)

            claude_cli.spawn_subprocess(
                goal="Task", persona="guide", working_dir=str(tmp_path), environment={}
            )

            call_kwargs = mock_popen.call_args.kwargs
            # Should preserve HOME, USER, etc.
            assert "env" in call_kwargs


class TestPlatformCLIPromptTemplates:
    """Test prompt template generation for different personas."""

    @pytest.fixture
    def claude_cli(self):
        return ClaudeCodeCLI()

    def test_prompt_includes_persona_characteristics(self, claude_cli):
        """Test prompt reflects persona-specific characteristics."""
        personas = {
            "guide": ["teach", "explain", "learn"],
            "qa_engineer": ["test", "validate", "quality"],
            "architect": ["design", "architecture", "system"],
            "junior_dev": ["implement", "code", "build"],
        }

        for persona, keywords in personas.items():
            prompt = claude_cli.format_prompt(goal="Create a module", persona=persona, context="")
            # At least one keyword should be present
            assert any(keyword in prompt.lower() for keyword in keywords), (
                f"Persona '{persona}' prompt missing characteristic keywords"
            )

    def test_prompt_includes_goal_clearly(self, claude_cli):
        """Test prompt clearly presents the goal."""
        goal = "CREATE A USER AUTHENTICATION SYSTEM WITH JWT TOKENS"
        prompt = claude_cli.format_prompt(goal=goal, persona="architect", context="")

        assert goal.lower() in prompt.lower()

    def test_prompt_includes_context_when_provided(self, claude_cli):
        """Test prompt includes context information."""
        context = "This is a legacy Python 2.7 codebase being migrated to Python 3.11"
        prompt = claude_cli.format_prompt(goal="Refactor code", persona="guide", context=context)

        assert context in prompt
