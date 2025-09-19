#!/usr/bin/env python
"""Example usage of amplihack modules."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from amplihack.launcher import ClaudeDirectoryDetector, ClaudeLauncher
from amplihack.proxy import ProxyConfig
from amplihack.utils import PathResolver


def example_proxy_configuration():
    """Example of setting up proxy configuration."""
    print("=== Proxy Configuration Example ===")

    # Create a proxy configuration
    config_path = Path("proxy-config.env.example")
    if config_path.exists():
        config = ProxyConfig(config_path)
        print(f"Loaded configuration from: {config_path}")
        print(f"API Key present: {bool(config.get('ANTHROPIC_API_KEY'))}")
        print(f"Valid configuration: {config.validate()}")
    else:
        print(f"No configuration file found at: {config_path}")


def example_directory_detection():
    """Example of detecting .claude directory."""
    print("\n=== Directory Detection Example ===")

    detector = ClaudeDirectoryDetector()
    claude_dir = detector.find_claude_directory()

    if claude_dir:
        print(f"Found .claude directory: {claude_dir}")
        project_root = detector.get_project_root(claude_dir)
        print(f"Project root: {project_root}")
    else:
        print("No .claude directory found in hierarchy")


def example_path_utilities():
    """Example of using path utilities."""
    print("\n=== Path Utilities Example ===")

    # Resolve home directory path
    home_path = PathResolver.resolve_path("~/amplihack")
    print(f"Resolved ~/amplihack to: {home_path}")

    # Find file upward
    readme = PathResolver.find_file_upward("README.md")
    if readme:
        print(f"Found README.md at: {readme}")

    # Get relative path
    if readme:
        rel_path = PathResolver.get_relative_path(readme)
        print(f"Relative path from cwd: {rel_path}")


def example_launcher_setup():
    """Example of setting up the launcher (without actually launching)."""
    print("\n=== Launcher Setup Example ===")

    # Create a launcher with no proxy (dry run)
    launcher = ClaudeLauncher()

    # Build command that would be executed
    command = launcher.build_claude_command()
    print(f"Would execute: {' '.join(command)}")

    # With system prompt
    prompt_path = Path("prompts/azure_persistence.md")
    if prompt_path.exists():
        launcher_with_prompt = ClaudeLauncher(append_system_prompt=prompt_path)
        command = launcher_with_prompt.build_claude_command()
        print(f"With prompt: {' '.join(command)}")


def main():
    """Run all examples."""
    print("Amplihack Module Usage Examples\n")

    examples = [
        example_proxy_configuration,
        example_directory_detection,
        example_path_utilities,
        example_launcher_setup,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"Error in {example.__name__}: {e}")

    print("\n" + "=" * 50)
    print("Examples completed. Use 'amplihack launch' to actually launch Claude.")


if __name__ == "__main__":
    main()
