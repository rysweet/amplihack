"""Quick verification script for Copilot auto mode integration.

Run this to verify all components are properly integrated.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def verify_imports():
    """Verify all imports work."""
    print("Verifying imports...")

    try:
        from amplihack.launcher.auto_mode_copilot import (
            CopilotAutoMode,
            CopilotAgentLibrary,
        )
        print("✓ auto_mode_copilot imports")
    except ImportError as e:
        print(f"✗ auto_mode_copilot import failed: {e}")
        return False

    try:
        from amplihack.copilot.session_manager import (
            CopilotSessionManager,
            SessionRegistry,
            SessionState,
        )
        print("✓ session_manager imports")
    except ImportError as e:
        print(f"✗ session_manager import failed: {e}")
        return False

    try:
        from amplihack.launcher.auto_mode import AutoMode
        print("✓ main auto_mode imports")
    except ImportError as e:
        print(f"✗ main auto_mode import failed: {e}")
        return False

    return True


def verify_agent_library():
    """Verify agent library works."""
    print("\nVerifying agent library...")

    from amplihack.launcher.auto_mode_copilot import CopilotAgentLibrary

    # Test each agent
    agents = [
        ("architect", CopilotAgentLibrary.get_architect_agent),
        ("builder", CopilotAgentLibrary.get_builder_agent),
        ("tester", CopilotAgentLibrary.get_tester_agent),
        ("reviewer", CopilotAgentLibrary.get_reviewer_agent),
    ]

    for name, getter in agents:
        agent = getter()
        if agent.name != name:
            print(f"✗ {name} agent name mismatch")
            return False
        if not agent.system_prompt:
            print(f"✗ {name} agent missing system prompt")
            return False
        if not agent.tools:
            print(f"✗ {name} agent missing tools")
            return False
        print(f"✓ {name} agent")

    # Test agent selection
    for task_type in ["feature", "bug", "refactor", "test"]:
        agents = CopilotAgentLibrary.select_agents(task_type)
        if not agents:
            print(f"✗ Agent selection failed for {task_type}")
            return False
        print(f"✓ Agent selection for {task_type}: {[a.name for a in agents]}")

    return True


def verify_session_manager():
    """Verify session manager works."""
    print("\nVerifying session manager...")

    import tempfile
    from amplihack.copilot.session_manager import CopilotSessionManager

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create session manager
        manager = CopilotSessionManager(tmpdir, "test_session")
        print("✓ Session manager created")

        # Check state file exists
        state_file = tmpdir / ".claude" / "runtime" / "copilot_sessions" / "test_session.json"
        if not state_file.exists():
            print("✗ State file not created")
            return False
        print("✓ State file created")

        # Test phase update
        manager.update_phase("testing")
        if manager.state.phase != "testing":
            print("✗ Phase update failed")
            return False
        print("✓ Phase update works")

        # Test context update
        manager.update_context("test_key", "test_value")
        if manager.get_context("test_key") != "test_value":
            print("✗ Context update failed")
            return False
        print("✓ Context update works")

        # Test fork
        fork_id = manager.fork_session({"test": "data"})
        if manager.state.fork_count != 1:
            print("✗ Fork count not incremented")
            return False
        print(f"✓ Session fork works (fork_id: {fork_id})")

    return True


def verify_auto_mode_routing():
    """Verify auto mode routing works."""
    print("\nVerifying auto mode routing...")

    from amplihack.launcher.auto_mode import AutoMode

    # Create AutoMode instance with enhanced Copilot flag
    auto_mode = AutoMode(
        sdk="copilot",
        prompt="test task",
        max_turns=3,
        use_enhanced_copilot=True,
    )

    if not hasattr(auto_mode, "use_enhanced_copilot"):
        print("✗ use_enhanced_copilot attribute missing")
        return False

    if not auto_mode.use_enhanced_copilot:
        print("✗ use_enhanced_copilot not set")
        return False

    print("✓ Auto mode routing configured")

    # Verify routing method exists
    if not hasattr(auto_mode, "_run_enhanced_copilot_mode"):
        print("✗ _run_enhanced_copilot_mode method missing")
        return False

    print("✓ Enhanced Copilot mode method exists")

    return True


def main():
    """Run all verifications."""
    print("=" * 70)
    print("Copilot Auto Mode Integration Verification")
    print("=" * 70)

    results = []

    # Run verifications
    results.append(("Imports", verify_imports()))
    results.append(("Agent Library", verify_agent_library()))
    results.append(("Session Manager", verify_session_manager()))
    results.append(("Auto Mode Routing", verify_auto_mode_routing()))

    # Summary
    print("\n" + "=" * 70)
    print("Verification Summary")
    print("=" * 70)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n✓ All verifications passed!")
        print("\nPhase 7: Enhanced Auto Mode - Complete")
        return 0
    else:
        print("\n✗ Some verifications failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
