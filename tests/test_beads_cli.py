"""
Test beads CLI integration.

Verifies that the beads CLI commands are properly wired up and function correctly.
"""

from unittest.mock import Mock, patch
import argparse
import json

from amplihack.cli import handle_beads_command


class TestBeadsCLIIntegration:
    """Test beads CLI command integration."""

    def test_beads_status_command(self):
        """Test beads status command."""
        args = argparse.Namespace(command="beads", beads_command="status")

        with patch("amplihack.memory.BeadsPrerequisites") as mock_prereqs:
            mock_prereqs.verify_setup.return_value = {
                "beads_available": False,
                "beads_initialized": False,
                "version": None,
                "version_compatible": False,
                "errors": [],
            }

            result = handle_beads_command(args)
            assert result == 0
            mock_prereqs.verify_setup.assert_called_once()

    def test_beads_init_command_not_installed(self, capsys):
        """Test beads init when beads not installed."""
        args = argparse.Namespace(command="beads", beads_command="init")

        with patch("amplihack.memory.BeadsPrerequisites") as mock_prereqs:
            # Mock Result class
            mock_result = Mock()
            mock_result.is_ok = True
            mock_result.value = False
            mock_prereqs.check_installed.return_value = mock_result

            result = handle_beads_command(args)
            assert result == 1

            captured = capsys.readouterr()
            assert "Beads not installed" in captured.out

    def test_beads_init_command_success(self, capsys):
        """Test successful beads init."""
        args = argparse.Namespace(command="beads", beads_command="init")

        with patch("amplihack.memory.BeadsPrerequisites") as mock_prereqs:
            # Mock check_installed to return True
            mock_check = Mock()
            mock_check.is_ok = True
            mock_check.value = True
            mock_prereqs.check_installed.return_value = mock_check

            # Mock initialize to return success
            mock_init = Mock()
            mock_init.is_ok = True
            mock_init.value = True
            mock_prereqs.initialize.return_value = mock_init

            result = handle_beads_command(args)
            assert result == 0

            captured = capsys.readouterr()
            assert "Beads initialized successfully" in captured.out

    def test_beads_create_command(self, capsys):
        """Test beads create command."""
        args = argparse.Namespace(
            command="beads",
            beads_command="create",
            title="Test Issue",
            description="Test description",
            labels="test,cli",
            assignee="testuser",
            status="open",
            json=False,
        )

        with patch("amplihack.memory.BeadsAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.is_available.return_value = True
            mock_adapter.check_init.return_value = True
            mock_adapter_class.return_value = mock_adapter

            with patch("amplihack.memory.BeadsMemoryProvider") as mock_provider_class:
                mock_provider = Mock()
                mock_provider.create_issue.return_value = "test-issue-id"
                mock_provider_class.return_value = mock_provider

                result = handle_beads_command(args)
                assert result == 0

                mock_provider.create_issue.assert_called_once_with(
                    title="Test Issue",
                    description="Test description",
                    status="open",
                    labels=["test", "cli"],
                    assignee="testuser",
                )

                captured = capsys.readouterr()
                assert "Created issue: test-issue-id" in captured.out
                assert "Test Issue" in captured.out

    def test_beads_create_command_json_output(self, capsys):
        """Test beads create command with JSON output."""
        args = argparse.Namespace(
            command="beads",
            beads_command="create",
            title="Test Issue",
            description="Test description",
            labels=None,
            assignee=None,
            status="open",
            json=True,
        )

        with patch("amplihack.memory.BeadsAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.is_available.return_value = True
            mock_adapter.check_init.return_value = True
            mock_adapter_class.return_value = mock_adapter

            with patch("amplihack.memory.BeadsMemoryProvider") as mock_provider_class:
                mock_provider = Mock()
                mock_provider.create_issue.return_value = "test-issue-id"
                mock_provider_class.return_value = mock_provider

                result = handle_beads_command(args)
                assert result == 0

                captured = capsys.readouterr()
                output = json.loads(captured.out)
                assert output["id"] == "test-issue-id"
                assert output["title"] == "Test Issue"

    def test_beads_ready_command(self, capsys):
        """Test beads ready command."""
        args = argparse.Namespace(
            command="beads",
            beads_command="ready",
            labels="test",
            assignee="testuser",
            limit=5,
            json=False,
        )

        mock_issues = [
            {
                "id": "issue-1",
                "title": "Ready Issue 1",
                "labels": ["test"],
                "assignee": "testuser",
                "description": "Test description",
            },
            {
                "id": "issue-2",
                "title": "Ready Issue 2",
                "labels": ["test"],
                "assignee": "testuser",
                "description": "Another test",
            },
        ]

        with patch("amplihack.memory.BeadsAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.is_available.return_value = True
            mock_adapter.check_init.return_value = True
            mock_adapter_class.return_value = mock_adapter

            with patch("amplihack.memory.BeadsMemoryProvider") as mock_provider_class:
                mock_provider = Mock()
                mock_provider.get_ready_work.return_value = mock_issues
                mock_provider_class.return_value = mock_provider

                result = handle_beads_command(args)
                assert result == 0

                mock_provider.get_ready_work.assert_called_once_with(
                    assignee="testuser", labels=["test"]
                )

                captured = capsys.readouterr()
                assert "Ready Work (2 issues)" in captured.out
                assert "issue-1" in captured.out
                assert "Ready Issue 1" in captured.out

    def test_beads_list_command(self, capsys):
        """Test beads list command."""
        args = argparse.Namespace(
            command="beads",
            beads_command="list",
            status="open",
            labels=None,
            assignee=None,
            limit=None,
            json=False,
        )

        mock_issues = [
            {"id": "issue-1", "title": "Open Issue", "status": "open", "labels": ["test"]}
        ]

        with patch("amplihack.memory.BeadsAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.is_available.return_value = True
            mock_adapter.check_init.return_value = True
            mock_adapter.query_issues.return_value = mock_issues
            mock_adapter_class.return_value = mock_adapter

            with patch("amplihack.memory.BeadsMemoryProvider") as mock_provider_class:
                mock_provider_class.return_value = Mock()

                result = handle_beads_command(args)
                assert result == 0

                mock_adapter.query_issues.assert_called_once_with(status="open")

                captured = capsys.readouterr()
                assert "Issues (1)" in captured.out
                assert "issue-1" in captured.out

    def test_beads_get_command(self, capsys):
        """Test beads get command."""
        args = argparse.Namespace(
            command="beads", beads_command="get", id="test-issue-id", json=False
        )

        mock_issue = {
            "id": "test-issue-id",
            "title": "Test Issue",
            "status": "open",
            "description": "Test description",
            "labels": ["test"],
            "assignee": "testuser",
            "created_at": "2024-01-01T00:00:00Z",
        }

        with patch("amplihack.memory.BeadsAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.is_available.return_value = True
            mock_adapter.check_init.return_value = True
            mock_adapter_class.return_value = mock_adapter

            with patch("amplihack.memory.BeadsMemoryProvider") as mock_provider_class:
                mock_provider = Mock()
                mock_provider.get_issue.return_value = mock_issue
                mock_provider_class.return_value = mock_provider

                result = handle_beads_command(args)
                assert result == 0

                captured = capsys.readouterr()
                assert "test-issue-id" in captured.out
                assert "Test Issue" in captured.out

    def test_beads_update_command(self, capsys):
        """Test beads update command."""
        args = argparse.Namespace(
            command="beads",
            beads_command="update",
            id="test-issue-id",
            status="in_progress",
            title=None,
            description=None,
            assignee=None,
            labels=None,
            json=False,
        )

        with patch("amplihack.memory.BeadsAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.is_available.return_value = True
            mock_adapter.check_init.return_value = True
            mock_adapter_class.return_value = mock_adapter

            with patch("amplihack.memory.BeadsMemoryProvider") as mock_provider_class:
                mock_provider = Mock()
                mock_provider.update_issue.return_value = True
                mock_provider_class.return_value = mock_provider

                result = handle_beads_command(args)
                assert result == 0

                mock_provider.update_issue.assert_called_once()
                captured = capsys.readouterr()
                assert "Updated issue: test-issue-id" in captured.out

    def test_beads_close_command(self, capsys):
        """Test beads close command."""
        args = argparse.Namespace(
            command="beads",
            beads_command="close",
            id="test-issue-id",
            resolution="completed",
            json=False,
        )

        with patch("amplihack.memory.BeadsAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.is_available.return_value = True
            mock_adapter.check_init.return_value = True
            mock_adapter_class.return_value = mock_adapter

            with patch("amplihack.memory.BeadsMemoryProvider") as mock_provider_class:
                mock_provider = Mock()
                mock_provider.close_issue.return_value = True
                mock_provider_class.return_value = mock_provider

                result = handle_beads_command(args)
                assert result == 0

                mock_provider.close_issue.assert_called_once_with(
                    "test-issue-id", resolution="completed"
                )
                captured = capsys.readouterr()
                assert "Closed issue: test-issue-id" in captured.out

    def test_beads_command_not_available(self, capsys):
        """Test beads commands when CLI not available."""
        args = argparse.Namespace(
            command="beads", beads_command="ready", labels=None, assignee=None, limit=10, json=False
        )

        with patch("amplihack.memory.BeadsAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.is_available.return_value = False
            mock_adapter_class.return_value = mock_adapter

            result = handle_beads_command(args)
            assert result == 1

            captured = capsys.readouterr()
            assert "Beads CLI not found" in captured.out

    def test_beads_command_not_initialized(self, capsys):
        """Test beads commands when not initialized."""
        args = argparse.Namespace(
            command="beads", beads_command="ready", labels=None, assignee=None, limit=10, json=False
        )

        with patch("amplihack.memory.BeadsAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.is_available.return_value = True
            mock_adapter.check_init.return_value = False
            mock_adapter_class.return_value = mock_adapter

            result = handle_beads_command(args)
            assert result == 1

            captured = capsys.readouterr()
            assert "Beads not initialized" in captured.out

    def test_beads_no_subcommand(self, capsys):
        """Test beads command without subcommand."""
        args = argparse.Namespace(command="beads", beads_command=None)

        result = handle_beads_command(args)
        assert result == 1

        captured = capsys.readouterr()
        assert "No beads subcommand specified" in captured.out

    def test_beads_error_handling_value_error(self, capsys):
        """Test error handling for ValueError."""
        args = argparse.Namespace(
            command="beads",
            beads_command="create",
            title="Test",
            description="Test",
            labels=None,
            assignee=None,
            status="open",
            json=False,
        )

        with patch("amplihack.memory.BeadsAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.is_available.return_value = True
            mock_adapter.check_init.return_value = True
            mock_adapter_class.return_value = mock_adapter

            with patch("amplihack.memory.BeadsMemoryProvider") as mock_provider_class:
                mock_provider = Mock()
                mock_provider.create_issue.side_effect = ValueError("Invalid input")
                mock_provider_class.return_value = mock_provider

                result = handle_beads_command(args)
                assert result == 1

                captured = capsys.readouterr()
                assert "Invalid input" in captured.out
