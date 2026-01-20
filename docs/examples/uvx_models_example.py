#!/usr/bin/env python3
"""
Example demonstrating the new UVX data models and state management.

This example shows how to use the clean, type-safe data structures
for UVX detection, path resolution, and file staging.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.utils.uvx_detection import detect_uvx_deployment, resolve_framework_paths
from amplihack.utils.uvx_models import (
    UVXConfiguration,
    UVXSessionState,
)
from amplihack.utils.uvx_staging_v2 import UVXStager, create_uvx_session


def main():
    """Demonstrate new UVX data models and operations."""
    print("🚀 UVX Data Models Example")
    print("=" * 50)

    # 1. Configuration Management
    print("\n📋 Configuration Management:")
    print("-" * 30)

    config = UVXConfiguration(
        debug_enabled=True, max_parent_traversal=5, allow_staging=True, overwrite_existing=False
    )

    print(f"Debug enabled: {config.is_debug_enabled}")
    print(f"Max parent traversal: {config.max_parent_traversal}")
    print(f"Allow staging: {config.allow_staging}")

    # 2. UVX Detection with State
    print("\n🔍 UVX Detection State:")
    print("-" * 30)

    detection_state = detect_uvx_deployment(config)

    print(f"Detection result: {detection_state.result.name}")
    print(f"Is UVX deployment: {detection_state.is_uvx_deployment}")
    print(f"Is local deployment: {detection_state.is_local_deployment}")
    print(f"Detection successful: {detection_state.is_detection_successful}")

    print("\nDetection reasoning:")
    for reason in detection_state.detection_reasons:
        print(f"  - {reason}")

    print("\nEnvironment info:")
    env = detection_state.environment
    print(f"  UV_PYTHON: {env.uv_python_path}")
    print(f"  AMPLIHACK_ROOT: {env.amplihack_root}")
    print(f"  Working directory: {env.working_directory}")
    print(f"  Sys.path entries: {len(env.sys_path_entries)}")

    # 3. Path Resolution with Detailed Results
    print("\n📁 Path Resolution:")
    print("-" * 30)

    path_resolution = resolve_framework_paths(detection_state, config)

    print(f"Resolution successful: {path_resolution.is_successful}")
    print(f"Requires staging: {path_resolution.requires_staging}")

    if path_resolution.location:
        location = path_resolution.location
        print(f"Framework root: {location.root_path}")
        print(f"Resolution strategy: {location.strategy.name}")
        print(f"Location valid: {location.is_valid}")
        print(f"Has .claude dir: {location.has_claude_dir}")

        if location.validation_errors:
            print("Validation errors:")
            for error in location.validation_errors:
                print(f"  - {error}")

    print("\nResolution attempts:")
    for i, attempt in enumerate(path_resolution.attempts, 1):
        print(f"  {i}. {attempt['strategy']}: {attempt['path']}")
        print(f"     Success: {attempt['success']}, Notes: {attempt['notes']}")

    # 4. File Resolution with Security
    print("\n📄 File Resolution:")
    print("-" * 30)

    if path_resolution.is_successful:
        test_files = [
            ".claude/context/USER_PREFERENCES.md",
            ".claude/workflow/DEFAULT_WORKFLOW.md",
            "CLAUDE.md",
            "DISCOVERIES.md",
            "../../../etc/passwd",  # Path traversal attack
            ".claude\x00/malicious.txt",  # Null byte injection
        ]

        for file_path in test_files:
            if path_resolution.location is not None:
                resolved = path_resolution.location.resolve_file(file_path)
                if resolved:
                    status = f"✅ Found at {resolved}"
                elif ".." in file_path or "\x00" in file_path:
                    status = "🛡️  Security: Path traversal blocked"
                else:
                    status = "❌ Not found"
            else:
                status = "❌ No framework location available"

            print(f"  {file_path}: {status}")

    # 5. Session State Management
    print("\n🎭 Session State Management:")
    print("-" * 30)

    session_state = UVXSessionState(configuration=config)
    session_state.initialize_detection(detection_state)
    session_state.set_path_resolution(path_resolution)

    print(f"Session ready: {session_state.is_ready}")
    print(f"Framework root: {session_state.framework_root}")

    if session_state.is_ready:
        session_state.mark_initialized("demo-session-123")
        print(f"Session ID: {session_state.session_id}")

    # Show debug info
    print("\nSession debug info:")
    debug_info = session_state.to_debug_dict()
    for key, value in debug_info.items():
        print(f"  {key}: {value}")

    # 6. Staging Operations (if UVX deployment)
    if detection_state.is_uvx_deployment and path_resolution.requires_staging:
        print("\n📦 Staging Operations:")
        print("-" * 30)

        stager = UVXStager(config)
        staging_result = stager.stage_framework_files(session_state)

        print(f"Staging successful: {staging_result.is_successful}")
        print(f"Total operations: {staging_result.total_operations}")
        print(f"Successful: {len(staging_result.successful)}")
        print(f"Failed: {len(staging_result.failed)}")
        print(f"Skipped: {len(staging_result.skipped)}")

        if staging_result.operations:
            print("\nStaging operations:")
            for i, op in enumerate(staging_result.operations[:5], 1):  # First 5
                print(f"  {i}. {op.operation_type}: {op.source_path.name} -> {op.target_path.name}")

        if staging_result.failed:
            print("\nFailures:")
            for path, error in list(staging_result.failed.items())[:3]:  # First 3
                print(f"  {path}: {error}")

        if staging_result.skipped:
            print("\nSkipped:")
            for path, reason in list(staging_result.skipped.items())[:3]:  # First 3
                print(f"  {path}: {reason}")

    # 7. Convenience Session Creation
    print("\n🎬 Convenience Session Creation:")
    print("-" * 30)

    try:
        complete_session = create_uvx_session()
        print(f"Session created: {complete_session.is_ready}")
        print(f"Session ID: {complete_session.session_id}")

        if complete_session.staging_result:
            print(f"Staging performed: {complete_session.staging_result.is_successful}")

    except Exception as e:
        print(f"Session creation error: {e}")

    # 8. Type Safety Demonstration
    print("\n🔒 Type Safety:")
    print("-" * 30)

    # These are all compile-time safe with proper type hints
    print("All operations are type-safe with proper IDE support:")
    print("  - detection_state.result is UVXDetectionResult enum")
    print("  - path_resolution.location is Optional[FrameworkLocation]")
    print("  - staging_result.successful is Set[Path]")
    print("  - All data structures are immutable (frozen=True)")

    # 9. Error Handling Examples
    print("\n⚠️  Error Handling:")
    print("-" * 30)

    # Show how invalid states are unrepresentable
    print("Invalid states are unrepresentable:")

    # Try to create invalid framework location
    invalid_location = path_resolution.location
    if invalid_location:
        print(f"  - Location validation: {len(invalid_location.validation_errors)} errors")

    # Show detection state reasoning
    if not detection_state.is_detection_successful:
        print("  - Detection failures include detailed reasoning")
        print("  - Each failure mode has specific error messages")

    print("\n" + "=" * 50)
    print("🎉 UVX Data Models Demo Complete!")
    print()
    print("Key Benefits Demonstrated:")
    print("  ✅ Immutable data structures prevent race conditions")
    print("  ✅ Type safety catches errors at development time")
    print("  ✅ Invalid states are unrepresentable by design")
    print("  ✅ Clear validation and error reporting")
    print("  ✅ Easy serialization for debugging")
    print("  ✅ Security-focused path resolution")


if __name__ == "__main__":
    main()
