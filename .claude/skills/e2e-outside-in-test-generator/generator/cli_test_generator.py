"""CLI test scenario generator.

Generates gadugi-agentic-test YAML scenarios for CLI applications
based on detected commands, arguments, and flags.
"""

from pathlib import Path

from .models import CLIConfig, GeneratedTest, TestCategory
from .template_manager import TemplateManager
from .utils import ensure_directory, write_file


def generate_cli_tests(
    config: CLIConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate all CLI test scenarios.

    Args:
        config: CLI application configuration
        template_mgr: Template manager
        output_dir: Output directory for generated test files

    Returns:
        List of GeneratedTest objects
    """
    generated = []
    generated.extend(_generate_cli_smoke_tests(config, template_mgr, output_dir))
    generated.extend(_generate_cli_command_tests(config, template_mgr, output_dir))
    generated.extend(_generate_cli_error_tests(config, template_mgr, output_dir))
    generated.extend(_generate_cli_integration_tests(config, template_mgr, output_dir))
    return generated


def _generate_cli_smoke_tests(
    config: CLIConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate CLI smoke tests (help, version)."""
    tests_dir = output_dir / "cli-smoke"
    ensure_directory(tests_dir)

    context = {
        "app_name": config.binary_path.split("/")[-1] if "/" in config.binary_path else config.binary_path,
        "binary_path": config.binary_path,
        "help_pattern": "(usage|help|commands|options)",
        "version_pattern": r"(\\d+\\.\\d+|version)",
    }

    content = template_mgr.render("cli_smoke", context)
    test_file = tests_dir / "smoke.yaml"
    write_file(test_file, content)

    return [
        GeneratedTest(
            category=TestCategory.CLI_SMOKE,
            file_path=test_file,
            test_count=3,
            description="CLI smoke tests (help, version, startup)",
        )
    ]


def _generate_cli_command_tests(
    config: CLIConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate test scenarios for each CLI command."""
    tests_dir = output_dir / "cli-commands"
    ensure_directory(tests_dir)

    generated = []
    for cmd in config.commands:
        # Build command args string
        args_list = [f'"{cmd.name}"']
        for arg in cmd.args:
            args_list.append(f'"<{arg}>"')

        extra_steps = ""
        if cmd.flags:
            # Add a test step for a flag
            flag = cmd.flags[0]
            extra_steps = f"""    - action: launch
      target: "{config.binary_path}"
      args: ["{cmd.name}", "{flag}"]
      description: "Run {cmd.name} with {flag} flag"
      timeout: 15s

    - action: verify_exit_code
      expected: 0
      description: "Command with flag should succeed"
"""

        context = {
            "app_name": config.binary_path.split("/")[-1] if "/" in config.binary_path else config.binary_path,
            "binary_path": config.binary_path,
            "command_name": cmd.name,
            "command_args": ", ".join(args_list),
            "success_pattern": f"(.+)",  # Any output is success for now
            "extra_steps": extra_steps,
        }

        content = template_mgr.render("cli_command", context)
        test_file = tests_dir / f"{cmd.name}.yaml"
        write_file(test_file, content)

        generated.append(
            GeneratedTest(
                category=TestCategory.CLI_COMMANDS,
                file_path=test_file,
                test_count=2 + (1 if cmd.flags else 0),
                description=f"CLI command tests for '{cmd.name}'",
            )
        )

    return generated


def _generate_cli_error_tests(
    config: CLIConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate CLI error handling test scenarios."""
    tests_dir = output_dir / "cli-errors"
    ensure_directory(tests_dir)

    # Build missing arg steps
    missing_arg_steps = ""
    if config.commands:
        cmd = config.commands[0]
        if cmd.required_args:
            missing_arg_steps = f"""    - action: launch
      target: "{config.binary_path}"
      args: ["{cmd.name}"]
      description: "Run {cmd.name} without required arguments"
      timeout: 10s

    - action: verify_output
      matches: "(error|missing|required)"
      case_sensitive: false
      timeout: 5s
      description: "Should indicate missing arguments"

    - action: verify_exit_code
      expected: 1
      description: "Should exit with error code"
"""

    # Build invalid arg steps
    invalid_arg_steps = ""
    if config.commands:
        cmd = config.commands[0]
        invalid_arg_steps = f"""    - action: launch
      target: "{config.binary_path}"
      args: ["{cmd.name}", "--invalid-flag-xyz"]
      description: "Run with invalid flag"
      timeout: 10s

    - action: verify_output
      matches: "(error|unknown|unrecognized|invalid)"
      case_sensitive: false
      timeout: 5s
      description: "Should reject unknown flag"
"""

    context = {
        "app_name": config.binary_path.split("/")[-1] if "/" in config.binary_path else config.binary_path,
        "binary_path": config.binary_path,
        "missing_arg_steps": missing_arg_steps,
        "invalid_arg_steps": invalid_arg_steps,
    }

    content = template_mgr.render("cli_error_handling", context)
    test_file = tests_dir / "error-handling.yaml"
    write_file(test_file, content)

    return [
        GeneratedTest(
            category=TestCategory.CLI_ERROR_HANDLING,
            file_path=test_file,
            test_count=3,
            description="CLI error handling tests",
        )
    ]


def _generate_cli_integration_tests(
    config: CLIConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate CLI integration test scenarios (command pipelines)."""
    tests_dir = output_dir / "cli-integration"
    ensure_directory(tests_dir)

    generated = []
    if len(config.commands) >= 2:
        # Create a multi-command workflow test
        steps = []
        for i, cmd in enumerate(config.commands):
            args = [f'"{cmd.name}"'] + [f'"test-arg-{j}"' for j in range(min(len(cmd.args), 2))]
            steps.append(f"""    - action: launch
      target: "{config.binary_path}"
      args: [{", ".join(args)}]
      description: "Step {i+1}: Run {cmd.name}"
      timeout: 15s

    - action: verify_exit_code
      expected: 0
      description: "{cmd.name} should succeed"
""")

        content = f"""# CLI Integration Test - Multi-Command Workflow
# Auto-generated outside-in test scenario

scenario:
  name: "CLI Integration - Multi-Command Workflow"
  description: |
    Verifies that multiple CLI commands can be executed in sequence
    as part of a typical workflow.
  type: cli
  level: 2
  tags: [cli, integration, workflow, auto-generated]

  prerequisites:
    - "{config.binary_path} binary exists and is executable"

  steps:
{"".join(steps)}
  cleanup:
    - action: stop_application
      force: true
      description: "Ensure process is terminated"
"""
        test_file = tests_dir / "multi-command-workflow.yaml"
        write_file(test_file, content)

        generated.append(
            GeneratedTest(
                category=TestCategory.CLI_INTEGRATION,
                file_path=test_file,
                test_count=len(config.commands) * 2,
                description="CLI multi-command integration test",
            )
        )

    return generated
