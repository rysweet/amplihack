#!/usr/bin/env python
"""Basic tests to verify amplihack modules load correctly."""

import os
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_imports():
    """Test that all modules can be imported."""
    try:
        # Test main module
        import amplihack  # noqa: F401

        print("✓ amplihack module imported")

        # Test CLI
        from amplihack.cli import create_parser, launch_command  # noqa: F401

        print("✓ CLI module imported")

        # Test proxy modules
        from amplihack.proxy import ProxyConfig, ProxyManager  # noqa: F401
        from amplihack.proxy.env import ProxyEnvironment  # noqa: F401

        print("✓ Proxy modules imported")

        # Test launcher modules
        from amplihack.launcher import ClaudeDirectoryDetector, ClaudeLauncher  # noqa: F401

        print("✓ Launcher modules imported")

        # Test utility modules
        from amplihack.utils import PathResolver, ProcessManager  # noqa: F401

        print("✓ Utility modules imported")

        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_detector():
    """Test the Claude directory detector."""
    from amplihack.launcher.detector import ClaudeDirectoryDetector

    detector = ClaudeDirectoryDetector()

    # Test finding .claude directory
    claude_dir = detector.find_claude_directory()
    if claude_dir:
        print(f"✓ Found .claude directory at: {claude_dir}")
    else:
        print("✓ No .claude directory found (expected in test environment)")

    return True


def test_proxy_config():
    """Test proxy configuration parsing."""
    import tempfile

    from amplihack.proxy.config import ProxyConfig

    # Create a test .env file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("ANTHROPIC_API_KEY=test-key-123\n")  # pragma: allowlist secret
        f.write("AZURE_ENDPOINT=https://test.azure.com\n")
        f.write("# Comment line\n")
        f.write("LOG_LEVEL=debug\n")
        temp_path = f.name

    try:
        config = ProxyConfig(Path(temp_path))
        assert config.get("ANTHROPIC_API_KEY") == "test-key-123"
        assert config.get("AZURE_ENDPOINT") == "https://test.azure.com"
        assert config.get("LOG_LEVEL") == "debug"
        assert config.validate()
        print("✓ Proxy configuration parsing works")
        return True
    finally:
        os.unlink(temp_path)


def test_path_resolver():
    """Test path resolution utilities."""
    from amplihack.utils.paths import PathResolver

    resolver = PathResolver

    # Test resolve_path
    resolved = resolver.resolve_path("~/test")
    assert resolved.is_absolute()
    print(f"✓ Path resolution works: ~/test -> {resolved}")

    # Test find_file_upward
    current_file = resolver.find_file_upward("README.md")
    if current_file:
        print(f"✓ Found README.md at: {current_file}")
    else:
        print("✓ find_file_upward works (no README.md found)")

    return True


def test_process_manager():
    """Test process management utilities."""
    from amplihack.utils.process import ProcessManager

    pm = ProcessManager

    # Test platform detection
    is_windows = pm.is_windows()
    is_unix = pm.is_unix()
    assert is_windows != is_unix, "Platform must be either Windows or Unix"
    print(f"✓ Platform detection: {'Windows' if is_windows else 'Unix-like'}")

    # Test command existence check
    git_exists = pm.check_command_exists("git")
    print(f"✓ Command check: git {'exists' if git_exists else 'not found'}")

    return True


def test_cli_parser():
    """Test CLI argument parser."""
    from amplihack.cli import create_parser

    parser = create_parser()

    # Test install command
    args = parser.parse_args(["install"])
    assert args.command == "install"
    print("✓ Parser handles 'install' command")

    # Test launch command with options
    args = parser.parse_args(["launch", "--with-proxy-config", "test.env"])
    assert args.command == "launch"
    assert args.with_proxy_config == "test.env"
    print("✓ Parser handles 'launch' command with options")

    return True


def main():
    """Run all tests."""
    print("Testing amplihack modules...\n")

    tests = [
        test_imports,
        test_detector,
        test_proxy_config,
        test_path_resolver,
        test_process_manager,
        test_cli_parser,
    ]

    results = []
    for test in tests:
        print(f"\nRunning {test.__name__}...")
        try:
            success = test()
            results.append(success)
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
            results.append(False)

    print(f"\n{'=' * 50}")
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")

    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
