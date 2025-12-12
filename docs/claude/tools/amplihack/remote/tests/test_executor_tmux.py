"""Unit tests for Executor tmux functionality."""

import os
import unittest
from unittest.mock import Mock, patch

from ..errors import ExecutionError
from ..executor import Executor
from ..orchestrator import VM


class TestExecutorTmux(unittest.TestCase):
    """Test cases for Executor tmux methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.vm = VM(name="test-vm", size="Standard_D2s_v3", region="eastus")
        self.executor = Executor(vm=self.vm, timeout_minutes=60)
        self.test_session_id = "test-session-123"
        self.test_command = "auto"
        self.test_prompt = "Fix the bug in main.py"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-123"})  # pragma: allowlist secret
    @patch("subprocess.run")
    def test_execute_remote_tmux_success(self, mock_run):
        """Test successful tmux session creation."""
        mock_run.return_value = Mock(
            returncode=0, stdout="Tmux session test-session-123 started successfully\n", stderr=""
        )

        result = self.executor.execute_remote_tmux(
            session_id=self.test_session_id, command=self.test_command, prompt=self.test_prompt
        )

        self.assertTrue(result)
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], "azlin")
        self.assertEqual(call_args[1], "connect")
        self.assertEqual(call_args[2], "test-vm")

        # Verify tmux commands in script
        script = call_args[3]
        self.assertIn("tmux new-session -d -s test-session-123", script)
        self.assertIn("tmux send-keys -t test-session-123", script)
        self.assertIn("amplihack claude --auto --max-turns 10", script)
        # Prompt is base64 encoded for security
        self.assertIn("Rml4IHRoZSBidWcgaW4gbWFpbi5weQ==", script)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-123"})
    @patch("subprocess.run")
    def test_execute_remote_tmux_with_max_turns(self, mock_run):
        """Test tmux session with custom max_turns."""
        mock_run.return_value = Mock(returncode=0, stdout="Session started\n", stderr="")

        self.executor.execute_remote_tmux(
            session_id=self.test_session_id,
            command="ultrathink",
            prompt=self.test_prompt,
            max_turns=20,
        )

        script = mock_run.call_args[0][0][3]
        self.assertIn("--ultrathink --max-turns 20", script)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-123"})
    @patch("subprocess.run")
    def test_execute_remote_tmux_with_api_key_param(self, mock_run):
        """Test tmux session with API key parameter."""
        mock_run.return_value = Mock(returncode=0, stdout="Session started\n", stderr="")

        self.executor.execute_remote_tmux(
            session_id=self.test_session_id,
            command=self.test_command,
            prompt=self.test_prompt,
            api_key="custom-key",  # pragma: allowlist secret
        )

        script = mock_run.call_args[0][0][3]
        # API key is base64 encoded for security
        self.assertIn("Y3VzdG9tLWtleQ==", script)

    @patch.dict(os.environ, {}, clear=True)
    def test_execute_remote_tmux_no_api_key(self):
        """Test error when API key not provided."""
        with self.assertRaises(ExecutionError) as ctx:
            self.executor.execute_remote_tmux(
                session_id=self.test_session_id, command=self.test_command, prompt=self.test_prompt
            )

        self.assertIn("ANTHROPIC_API_KEY not found", str(ctx.exception))

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})  # pragma: allowlist secret
    def test_execute_remote_tmux_invalid_session_id(self):
        """Test error with invalid session ID."""
        invalid_ids = [
            "",  # Empty
            "session with spaces",  # Spaces
            "session/with/slashes",  # Slashes
            "session;dangerous",  # Semicolon
            "session$var",  # Shell variable
        ]

        for invalid_id in invalid_ids:
            with self.assertRaises(ExecutionError) as ctx:
                self.executor.execute_remote_tmux(
                    session_id=invalid_id, command=self.test_command, prompt=self.test_prompt
                )
            self.assertIn("Invalid session_id", str(ctx.exception))

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_execute_remote_tmux_valid_session_ids(self):
        """Test various valid session ID formats."""
        valid_ids = [
            "session123",
            "test-session",
            "session-with-many-dashes",
            "SessionWithCaps",
            "s123",
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Started\n", stderr="")

            for valid_id in valid_ids:
                result = self.executor.execute_remote_tmux(
                    session_id=valid_id, command=self.test_command, prompt=self.test_prompt
                )
                self.assertTrue(result)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("subprocess.run")
    def test_execute_remote_tmux_setup_failure(self, mock_run):
        """Test error when tmux setup fails."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="tmux: command not found\n")

        with self.assertRaises(ExecutionError) as ctx:
            self.executor.execute_remote_tmux(
                session_id=self.test_session_id, command=self.test_command, prompt=self.test_prompt
            )

        self.assertIn("Failed to start tmux session", str(ctx.exception))
        self.assertIn("tmux: command not found", str(ctx.exception))

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("subprocess.run")
    def test_execute_remote_tmux_timeout(self, mock_run):
        """Test timeout during tmux setup."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("azlin connect", 600)

        with self.assertRaises(ExecutionError) as ctx:
            self.executor.execute_remote_tmux(
                session_id=self.test_session_id, command=self.test_command, prompt=self.test_prompt
            )

        self.assertIn("Tmux session setup timed out", str(ctx.exception))

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("subprocess.run")
    def test_execute_remote_tmux_prompt_escaping(self, mock_run):
        """Test prompt with special characters is properly escaped."""
        mock_run.return_value = Mock(returncode=0, stdout="Started\n", stderr="")

        dangerous_prompt = "Fix the 'bug' with `command` and $variable"
        self.executor.execute_remote_tmux(
            session_id=self.test_session_id, command=self.test_command, prompt=dangerous_prompt
        )

        script = mock_run.call_args[0][0][3]
        # Prompt is base64 encoded, so special characters don't need escaping
        # Base64 encoding of: Fix the 'bug' with `command` and $variable
        self.assertIn(
            "Rml4IHRoZSAnYnVnJyB3aXRoIGBjb21tYW5kYCBhbmQgJHZhcmlhYmxl", script
        )  # pragma: allowlist secret

    @patch("subprocess.run")
    def test_check_tmux_status_running(self, mock_run):
        """Test checking status of running tmux session."""
        mock_run.return_value = Mock(returncode=0, stdout="running\n", stderr="")

        status = self.executor.check_tmux_status(self.test_session_id)

        self.assertEqual(status, "running")
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertIn("tmux has-session -t test-session-123", call_args[3])

    @patch("subprocess.run")
    def test_check_tmux_status_completed(self, mock_run):
        """Test checking status of completed tmux session."""
        mock_run.return_value = Mock(returncode=0, stdout="completed\n", stderr="")

        status = self.executor.check_tmux_status(self.test_session_id)

        self.assertEqual(status, "completed")

    @patch("subprocess.run")
    def test_check_tmux_status_unexpected_output(self, mock_run):
        """Test handling unexpected output from status check."""
        mock_run.return_value = Mock(returncode=0, stdout="unknown\n", stderr="")

        status = self.executor.check_tmux_status(self.test_session_id)

        # Unexpected output should be treated as completed
        self.assertEqual(status, "completed")

    def test_check_tmux_status_invalid_session_id(self):
        """Test error with invalid session ID in status check."""
        invalid_ids = ["", "session with spaces", "session/path", "session;cmd"]

        for invalid_id in invalid_ids:
            with self.assertRaises(ExecutionError) as ctx:
                self.executor.check_tmux_status(invalid_id)
            self.assertIn("Invalid session_id", str(ctx.exception))

    @patch("subprocess.run")
    def test_check_tmux_status_timeout(self, mock_run):
        """Test timeout during status check."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("azlin connect", 30)

        with self.assertRaises(ExecutionError) as ctx:
            self.executor.check_tmux_status(self.test_session_id)

        self.assertIn("Tmux status check timed out", str(ctx.exception))

    @patch("subprocess.run")
    def test_check_tmux_status_connection_error(self, mock_run):
        """Test error during status check connection."""
        mock_run.side_effect = Exception("Connection failed")

        with self.assertRaises(ExecutionError) as ctx:
            self.executor.check_tmux_status(self.test_session_id)

        self.assertIn("Failed to check tmux status", str(ctx.exception))
        self.assertIn("Connection failed", str(ctx.exception))

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("subprocess.run")
    def test_execute_remote_tmux_includes_tmux_installation(self, mock_run):
        """Test that setup script includes tmux installation."""
        mock_run.return_value = Mock(returncode=0, stdout="Started\n", stderr="")

        self.executor.execute_remote_tmux(
            session_id=self.test_session_id, command=self.test_command, prompt=self.test_prompt
        )

        script = mock_run.call_args[0][0][3]
        self.assertIn("if ! command -v tmux", script)
        self.assertIn("sudo apt-get install -y -qq tmux", script)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("subprocess.run")
    def test_execute_remote_tmux_workspace_setup(self, mock_run):
        """Test that workspace setup is included in tmux script."""
        mock_run.return_value = Mock(returncode=0, stdout="Started\n", stderr="")

        self.executor.execute_remote_tmux(
            session_id=self.test_session_id, command=self.test_command, prompt=self.test_prompt
        )

        script = mock_run.call_args[0][0][3]
        # Verify workspace setup
        self.assertIn("mkdir -p ~/workspace", script)
        self.assertIn("git clone ~/repo.bundle", script)
        self.assertIn("cp -r ~/.claude .", script)
        # Verify venv setup
        self.assertIn("python3.11 -m venv ~/.amplihack-venv", script)
        self.assertIn("pip install . --quiet", script)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("subprocess.run")
    def test_execute_remote_tmux_environment_variables(self, mock_run):
        """Test that environment variables are properly set in tmux."""
        mock_run.return_value = Mock(returncode=0, stdout="Started\n", stderr="")

        self.executor.execute_remote_tmux(
            session_id=self.test_session_id, command=self.test_command, prompt=self.test_prompt
        )

        script = mock_run.call_args[0][0][3]
        # Verify tmux sends environment variables
        self.assertIn("tmux send-keys -t test-session-123", script)
        self.assertIn("source ~/.amplihack-venv/bin/activate", script)
        self.assertIn("export ANTHROPIC_API_KEY=", script)


class TestExecutorTmuxIntegration(unittest.TestCase):
    """Integration tests for tmux functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.vm = VM(name="test-vm", size="Standard_D2s_v3", region="eastus")
        self.executor = Executor(vm=self.vm, timeout_minutes=60)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("subprocess.run")
    def test_tmux_workflow_start_then_check(self, mock_run):
        """Test complete workflow: start session then check status."""
        # First call: start tmux session
        mock_run.return_value = Mock(returncode=0, stdout="Started\n", stderr="")

        session_id = "workflow-test-123"
        started = self.executor.execute_remote_tmux(
            session_id=session_id, command="auto", prompt="Test task"
        )
        self.assertTrue(started)

        # Second call: check status (running)
        mock_run.return_value = Mock(returncode=0, stdout="running\n", stderr="")
        status = self.executor.check_tmux_status(session_id)
        self.assertEqual(status, "running")

        # Third call: check status (completed)
        mock_run.return_value = Mock(returncode=0, stdout="completed\n", stderr="")
        status = self.executor.check_tmux_status(session_id)
        self.assertEqual(status, "completed")

        # Verify all calls were made
        self.assertEqual(mock_run.call_count, 3)


if __name__ == "__main__":
    unittest.main()
