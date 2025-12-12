"""Basic usage examples for Session Management Toolkit.

This module demonstrates the fundamental usage patterns of the Session Management Toolkit,
following amplihack's ruthless simplicity philosophy.
"""

import time
from pathlib import Path

from ..claude_session import SessionConfig
from ..session_toolkit import SessionToolkit, quick_session


def example_basic_session():
    """Basic session usage example."""
    print("=== Basic Session Usage ===")

    # Create toolkit instance
    toolkit = SessionToolkit(
        runtime_dir=Path("./examples_runtime"), auto_save=True, log_level="INFO"
    )

    # Use session with context manager
    with toolkit.session("basic_example") as session:
        # Get logger for this session
        logger = toolkit.get_logger("basic_example")

        logger.info("Starting basic session example")

        # Execute some commands
        result1 = session.execute_command("list_files", directory="/tmp")
        logger.info(f"Command result: {result1['status']}")

        result2 = session.execute_command("analyze_data", format="json")
        logger.info(f"Analysis complete: {result2['status']}")

        # Check session statistics
        stats = session.get_statistics()
        logger.info(f"Session stats: {stats['command_count']} commands executed")

        logger.success("Basic session example completed")

    print("Session saved automatically on exit")


def example_quick_session():
    """Quick session helper example."""
    print("\n=== Quick Session Helper ===")

    # Quick session for simple tasks
    with quick_session("quick_task") as session:
        print(f"Quick session ID: {session.state.session_id}")

        # Execute a simple command
        result = session.execute_command("quick_operation", param="value")
        print(f"Operation result: {result['status']}")

        # Get command history
        history = session.get_command_history()
        print(f"Commands executed: {len(history)}")


def example_session_persistence():
    """Session persistence and resume example."""
    print("\n=== Session Persistence & Resume ===")

    toolkit = SessionToolkit(runtime_dir=Path("./examples_runtime"))

    # Create a session and do some work
    session_id = toolkit.create_session(
        "persistent_session", metadata={"project": "example", "version": "1.0"}
    )

    print(f"Created session: {session_id}")

    # First session usage
    with toolkit.session(session_id) as session:
        logger = toolkit.get_logger("persistence")

        logger.info("First session usage - initializing")
        session.execute_command("initialize_project")
        session.execute_command("setup_environment")

        # Save a checkpoint
        session.save_checkpoint()
        logger.info("Checkpoint saved")

    print("Session saved and closed")

    # Later... resume the same session
    with toolkit.session(session_id, resume=True) as resumed_session:
        logger = toolkit.get_logger("persistence")

        logger.info("Resumed session - continuing work")

        # Check previous work
        history = resumed_session.get_command_history()
        print(f"Previous commands: {len(history)}")

        # Continue with new work
        resumed_session.execute_command("process_data")
        resumed_session.execute_command("generate_report")

        logger.success("Session work completed")

    print("Session persistence example completed")


def example_multiple_sessions():
    """Multiple concurrent sessions example."""
    print("\n=== Multiple Concurrent Sessions ===")

    toolkit = SessionToolkit(runtime_dir=Path("./examples_runtime"))

    # Create multiple sessions for different tasks
    sessions = {
        "data_analysis": toolkit.create_session("data_analysis"),
        "report_generation": toolkit.create_session("report_generation"),
        "system_monitoring": toolkit.create_session("system_monitoring"),
    }

    print(f"Created {len(sessions)} sessions")

    # Work with each session
    for name, session_id in sessions.items():
        with toolkit.session(session_id) as session:
            logger = toolkit.get_logger(name)

            logger.info(f"Working on {name}")
            session.execute_command(f"start_{name}")
            session.execute_command(f"process_{name}")

            # Simulate some work time
            time.sleep(0.1)

            logger.success(f"Completed {name}")

    # List all sessions
    all_sessions = toolkit.list_sessions()
    print(f"\nTotal sessions: {len(all_sessions)}")
    for session_info in all_sessions:
        print(f"  - {session_info['name']}: {session_info['status']}")


def example_error_handling():
    """Error handling and recovery example."""
    print("\n=== Error Handling & Recovery ===")

    toolkit = SessionToolkit(runtime_dir=Path("./examples_runtime"))

    with toolkit.session("error_handling") as session:
        logger = toolkit.get_logger("error_handling")

        logger.info("Starting error handling example")

        # Successful operation
        session.execute_command("successful_operation")

        # Simulate error handling
        try:
            # This would normally fail in real usage
            # For demo, we'll simulate the pattern
            logger.warning("Simulating error scenario")
            session.state.error_count += 1
            session.state.last_error = "Simulated error"

        except Exception as e:
            logger.error(f"Operation failed: {e}")

        # Recovery operation
        session.execute_command("recovery_operation")
        logger.info("Recovery completed")

        # Check final statistics
        stats = session.get_statistics()
        logger.info(
            f"Final stats - Commands: {stats['command_count']}, Errors: {stats['error_count']}"
        )


def example_advanced_logging():
    """Advanced logging features example."""
    print("\n=== Advanced Logging Features ===")

    toolkit = SessionToolkit(runtime_dir=Path("./examples_runtime"))

    with toolkit.session("advanced_logging") as session:
        logger = toolkit.get_logger("advanced_logging")

        logger.info("Starting advanced logging example")

        # Operation tracking with context manager
        with logger.operation("data_processing"):
            session.execute_command("load_data")
            logger.info("Data loaded successfully")

            # Nested operation
            with logger.operation("data_transformation"):
                session.execute_command("transform_data")
                logger.info("Data transformation completed")

            session.execute_command("save_data")

        logger.success("Data processing pipeline completed")

        # Child logger for sub-components
        child_logger = logger.create_child_logger("validator")
        child_logger.info("Running validation checks")

        with child_logger.operation("validation"):
            session.execute_command("validate_output")
            child_logger.success("Validation passed")

        logger.info("Advanced logging example completed")


def example_session_configuration():
    """Custom session configuration example."""
    print("\n=== Custom Session Configuration ===")

    # Custom configuration
    config = SessionConfig(
        timeout=60.0,  # 1 minute timeout
        max_retries=5,  # More retry attempts
        heartbeat_interval=5.0,  # Faster heartbeat
        auto_save_interval=30.0,  # Save every 30 seconds
    )

    toolkit = SessionToolkit(runtime_dir=Path("./examples_runtime"))

    session_id = toolkit.create_session(
        "configured_session", config=config, metadata={"environment": "testing", "priority": "high"}
    )

    with toolkit.session(session_id) as session:
        logger = toolkit.get_logger("configured")

        logger.info("Using custom configuration")
        logger.info(f"Timeout: {session.config.timeout}s")
        logger.info(f"Max retries: {session.config.max_retries}")

        # This session will use the custom settings
        session.execute_command("configured_operation")

        logger.success("Custom configuration example completed")


def example_session_export_import():
    """Session export and import example."""
    print("\n=== Session Export & Import ===")

    toolkit = SessionToolkit(runtime_dir=Path("./examples_runtime"))

    # Create and populate a session
    original_id = toolkit.create_session("export_example")

    with toolkit.session(original_id) as session:
        logger = toolkit.get_logger("export")

        logger.info("Creating session for export")
        session.execute_command("prepare_export_data")
        session.execute_command("generate_export_summary")

    # Export the session
    export_file = Path("./session_export.json")
    success = toolkit.export_session_data(original_id, export_file)

    if success:
        print(f"Session exported to: {export_file}")

        # Import to create a new session
        imported_id = toolkit.import_session_data(export_file)

        if imported_id:
            print(f"Session imported as: {imported_id}")

            # Verify the imported session
            with toolkit.session(imported_id) as imported_session:
                history = imported_session.get_command_history()
                print(f"Imported session has {len(history)} commands")

        # Cleanup export file
        export_file.unlink(missing_ok=True)


def example_cleanup_operations():
    """Cleanup operations example."""
    print("\n=== Cleanup Operations ===")

    toolkit = SessionToolkit(runtime_dir=Path("./examples_runtime"))

    # Create some test sessions
    test_sessions = []
    for i in range(3):
        session_id = toolkit.create_session(f"cleanup_test_{i}")
        test_sessions.append(session_id)

        # Use each session briefly
        with toolkit.session(session_id) as session:
            session.execute_command(f"test_command_{i}")

    print(f"Created {len(test_sessions)} test sessions")

    # Get current statistics
    stats = toolkit.get_toolkit_stats()
    print(f"Current sessions: {stats['total_sessions']}")

    # Run cleanup (with very permissive settings for demo)
    cleanup_results = toolkit.cleanup_old_data(
        session_age_days=0,  # Clean all sessions immediately
        log_age_days=0,  # Clean all logs
        temp_age_hours=0,  # Clean all temp files
    )

    print("Cleanup results:")
    for operation, count in cleanup_results.items():
        print(f"  {operation}: {count} files processed")


def run_all_examples():
    """Run all examples in sequence."""
    print("Session Management Toolkit - Examples")
    print("=" * 50)

    examples = [
        example_basic_session,
        example_quick_session,
        example_session_persistence,
        example_multiple_sessions,
        example_error_handling,
        example_advanced_logging,
        example_session_configuration,
        example_session_export_import,
        example_cleanup_operations,
    ]

    for example in examples:
        try:
            example()
            time.sleep(0.5)  # Brief pause between examples
        except Exception as e:
            print(f"Example {example.__name__} failed: {e}")

    print("\n" + "=" * 50)
    print("All examples completed!")


if __name__ == "__main__":
    run_all_examples()
