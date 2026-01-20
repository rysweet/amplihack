"""Integration tests for the complete Session Management Toolkit."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ..claude_session import SessionConfig
from ..session_toolkit import SessionToolkit, quick_session


class TestSessionToolkitIntegration:
    """Integration tests for SessionToolkit."""

    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def toolkit(self, temp_dir):
        """Test toolkit instance."""
        return SessionToolkit(runtime_dir=temp_dir / "runtime", auto_save=True, log_level="DEBUG")

    def test_toolkit_initialization(self, toolkit, temp_dir):
        """Test toolkit initialization and directory creation."""
        assert toolkit.runtime_dir == temp_dir / "runtime"
        assert toolkit.auto_save is True
        assert toolkit.log_level == "DEBUG"

        # Check that session manager is initialized
        assert toolkit.session_manager is not None
        assert toolkit.session_manager.runtime_dir.exists()

    def test_complete_session_lifecycle(self, toolkit):
        """Test complete session lifecycle with all components."""
        session_name = "integration_test_session"

        # Create and use session
        with toolkit.session(session_name) as session:
            # Check session is active
            assert session.state.is_active is True
            assert toolkit.get_current_session() == session

            # Get logger and log some events
            logger = toolkit.get_logger("test_component")
            assert logger is not None

            logger.info("Starting integration test")

            # Execute some commands
            with logger.operation("test_operation"):
                session.execute_command("command1", param="value1")
                session.execute_command("command2", param="value2")

            logger.success("Integration test completed")

            # Check command history
            history = session.get_command_history()
            assert len(history) == 2
            assert history[0]["command"] == "command1"
            assert history[1]["command"] == "command2"

            # Save checkpoint
            session.save_checkpoint()

            # Get session statistics
            stats = toolkit.get_session_stats()
            assert stats["command_count"] == 2
            assert stats["is_active"] is True

        # Session should be auto-saved after context exit
        sessions = toolkit.list_sessions()
        session_found = any(s["name"] == session_name for s in sessions)
        assert session_found is True

    def test_session_persistence_and_resume(self, toolkit):
        """Test session persistence and resume functionality."""
        session_name = "persistence_test"
        test_metadata = {"project": "test", "version": "1.0"}

        # Create session with metadata
        session_id = toolkit.create_session(session_name, metadata=test_metadata)

        # Use session and execute commands
        with toolkit.session(session_id) as session:
            session.execute_command("init_command")
            session.execute_command("setup_command")

        # Resume session in new context
        with toolkit.session(session_id, resume=True) as resumed_session:
            # Check command history is preserved
            history = resumed_session.get_command_history()
            assert len(history) == 2
            assert history[0]["command"] == "init_command"
            assert history[1]["command"] == "setup_command"

            # Execute more commands
            resumed_session.execute_command("resumed_command")

        # Verify final state
        final_session = toolkit.get_session(session_id)
        if final_session:
            assert len(final_session.get_command_history()) == 3

    def test_multiple_concurrent_sessions(self, toolkit):
        """Test handling multiple concurrent sessions."""
        session_names = ["session_1", "session_2", "session_3"]
        session_ids = []

        # Create multiple sessions
        for name in session_names:
            session_id = toolkit.create_session(name)
            session_ids.append(session_id)

        # List sessions
        sessions = toolkit.list_sessions(active_only=True)
        assert len(sessions) >= 3

        # Use each session
        for i, session_id in enumerate(session_ids):
            session = toolkit.get_session(session_id)
            assert session is not None

            with session:
                session.execute_command(f"command_for_session_{i}")

        # Verify each session has its own history
        for i, session_id in enumerate(session_ids):
            session = toolkit.get_session(session_id)
            if session:
                history = session.get_command_history()
                assert len(history) == 1
                assert f"session_{i}" in history[0]["command"]

    def test_error_handling_and_recovery(self, toolkit):
        """Test error handling and recovery scenarios."""
        session_name = "error_test"

        with toolkit.session(session_name) as session:
            logger = toolkit.get_logger("error_component")

            # Execute successful command
            session.execute_command("good_command")

            # Mock a failing command
            with patch.object(session, "_simulate_command_execution") as mock_exec:
                mock_exec.side_effect = RuntimeError("Simulated error")

                try:
                    session.execute_command("failing_command")
                except RuntimeError:
                    logger.error("Command failed as expected")

            # Check error is tracked
            stats = session.get_statistics()
            assert stats["error_count"] == 1
            assert stats["command_count"] == 2  # Both commands counted

            # Continue with successful commands
            session.execute_command("recovery_command")

        # Verify session was saved despite errors
        sessions = toolkit.list_sessions()
        error_session = next((s for s in sessions if s["name"] == session_name), None)
        assert error_session is not None

    def test_logging_integration(self, toolkit):
        """Test integrated logging functionality."""
        session_name = "logging_test"

        with toolkit.session(session_name) as session:
            logger = toolkit.get_logger("logging_component")

            # Test different log levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")

            # Test operation logging
            with logger.operation("test_operation"):
                session.execute_command("logged_command")
                logger.info("Operation in progress")

            logger.success("Operation completed successfully")

            # Test child logger
            child_logger = logger.create_child_logger("sub_component")
            child_logger.info("Child logger message")

        # Verify logs exist (implementation dependent)
        log_dir = toolkit.runtime_dir / "logs"
        assert log_dir.exists()

    def test_session_export_import(self, toolkit, temp_dir):
        """Test session export and import functionality."""
        session_name = "export_import_test"
        export_file = temp_dir / "session_export.json"

        # Create and populate session
        session_id = toolkit.create_session(session_name)
        with toolkit.session(session_id) as session:
            session.execute_command("export_command_1")
            session.execute_command("export_command_2")

        # Export session
        success = toolkit.export_session_data(session_id, export_file)
        assert success is True
        assert export_file.exists()

        # Verify export content
        with open(export_file) as f:
            export_data = json.load(f)

        assert export_data["session_id"] == session_id
        assert len(export_data["command_history"]) == 2
        assert "statistics" in export_data

        # Import session
        new_session_id = toolkit.import_session_data(export_file)
        assert new_session_id is not None
        assert new_session_id != session_id  # Should be new session

        # Verify imported session
        imported_session = toolkit.get_session(new_session_id)
        if imported_session:
            history = imported_session.get_command_history()
            assert len(history) == 2

    def test_cleanup_functionality(self, toolkit):
        """Test cleanup operations."""
        # Create some sessions
        session_ids = []
        for i in range(3):
            session_id = toolkit.create_session(f"cleanup_test_{i}")
            session_ids.append(session_id)

        # Use sessions briefly
        for session_id in session_ids:
            with toolkit.session(session_id) as session:
                session.execute_command("test_command")

        # Run cleanup
        cleanup_results = toolkit.cleanup_old_data(
            session_age_days=0,  # Clean all sessions
            log_age_days=0,  # Clean all logs
            temp_age_hours=0,  # Clean all temp files
        )

        assert isinstance(cleanup_results, dict)
        assert "sessions_cleaned" in cleanup_results
        assert "log_files_cleaned" in cleanup_results
        assert "temp_files_cleaned" in cleanup_results

    def test_toolkit_statistics(self, toolkit):
        """Test toolkit-wide statistics."""
        # Create some sessions
        for i in range(2):
            toolkit.create_session(f"stats_test_{i}")

        # Get toolkit stats
        stats = toolkit.get_toolkit_stats()

        assert "total_sessions" in stats
        assert "active_sessions" in stats
        assert "runtime_dir" in stats
        assert "auto_save_enabled" in stats
        assert stats["total_sessions"] >= 2

    def test_session_configuration(self, toolkit):
        """Test session creation with custom configuration."""
        config = SessionConfig(timeout=120.0, max_retries=5, heartbeat_interval=10.0)

        session_id = toolkit.create_session("configured_session", config=config)

        session = toolkit.get_session(session_id)
        assert session.config.timeout == 120.0
        assert session.config.max_retries == 5
        assert session.config.heartbeat_interval == 10.0

    def test_session_archival(self, toolkit):
        """Test session archival functionality."""
        session_id = toolkit.create_session("archival_test")

        # Use session
        with toolkit.session(session_id) as session:
            session.execute_command("archive_command")

        # Archive session
        success = toolkit.delete_session(session_id)
        assert success is True

        # Verify session is no longer in active list
        active_sessions = toolkit.list_sessions(active_only=True)
        archived_session = any(s["session_id"] == session_id for s in active_sessions)
        assert archived_session is False


class TestQuickSessionHelper:
    """Test quick session helper function."""

    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_quick_session_usage(self, temp_dir):
        """Test quick session helper function."""
        with quick_session("quick_test", runtime_dir=temp_dir / "runtime") as session:
            assert session.state.is_active is True
            result = session.execute_command("quick_command")
            assert result is not None

    def test_quick_session_with_config(self, temp_dir):
        """Test quick session with custom configuration."""
        config = SessionConfig(timeout=60.0)

        with quick_session(
            "quick_configured", runtime_dir=temp_dir / "runtime", config=config
        ) as session:
            assert session.config.timeout == 60.0


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.fixture
    def toolkit(self):
        """Test toolkit for real-world scenarios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SessionToolkit(runtime_dir=Path(tmpdir) / "runtime", auto_save=True)

    def test_code_analysis_workflow(self, toolkit):
        """Test a realistic code analysis workflow."""
        with toolkit.session("code_analysis") as session:
            logger = toolkit.get_logger("analyzer")

            # Initialize analysis
            with logger.operation("initialization"):
                session.execute_command("scan_directory", path="/project/src")
                logger.info("Directory scan completed")

            # Analyze each file type
            with logger.operation("python_analysis"):
                session.execute_command("analyze_python_files")
                logger.info("Python analysis completed")

            with logger.operation("javascript_analysis"):
                session.execute_command("analyze_js_files")
                logger.info("JavaScript analysis completed")

            # Generate report
            with logger.operation("report_generation"):
                session.execute_command("generate_report")
                logger.success("Analysis workflow completed")

            # Verify workflow completion
            history = session.get_command_history()
            assert len(history) == 4
            assert any("scan_directory" in cmd["command"] for cmd in history)
            assert any("generate_report" in cmd["command"] for cmd in history)

    def test_debugging_session_workflow(self, toolkit):
        """Test a debugging session workflow."""
        with toolkit.session("debugging_session") as session:
            logger = toolkit.get_logger("debugger")

            # Set up debugging environment
            session.execute_command("setup_debug_environment")
            session.save_checkpoint()  # Save state before debugging

            # Attempt problematic operation
            try:
                with patch.object(session, "_simulate_command_execution") as mock:
                    mock.side_effect = RuntimeError("Bug reproduction")
                    session.execute_command("reproduce_bug")
            except RuntimeError:
                logger.error("Bug reproduced successfully")

            # Restore to checkpoint and try fix
            session.restore_checkpoint()
            session.execute_command("apply_fix")
            session.execute_command("verify_fix")

            logger.success("Debugging session completed")

            # Verify debugging workflow
            stats = session.get_statistics()
            assert stats["error_count"] == 1  # One expected error
            assert stats["command_count"] >= 3  # Multiple commands executed

    def test_batch_processing_workflow(self, toolkit):
        """Test a batch processing workflow."""
        with toolkit.session("batch_processing") as session:
            logger = toolkit.get_logger("batch_processor")

            # Process multiple batches
            batch_count = 5
            for i in range(batch_count):
                with logger.operation(f"batch_{i}"):
                    session.execute_command(f"process_batch_{i}", size=100)
                    logger.info(f"Processed batch {i}")

            # Final aggregation
            with logger.operation("aggregation"):
                session.execute_command("aggregate_results")
                logger.success("Batch processing completed")

            # Verify batch processing
            history = session.get_command_history()
            assert len(history) == batch_count + 1  # Batches + aggregation

            batch_commands = [cmd for cmd in history if "process_batch" in cmd["command"]]
            assert len(batch_commands) == batch_count
