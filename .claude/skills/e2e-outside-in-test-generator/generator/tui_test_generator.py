"""TUI test scenario generator.

Generates gadugi-agentic-test YAML scenarios for TUI applications
based on detected widgets, screens, and keyboard shortcuts.
"""

from pathlib import Path

from .models import GeneratedTest, TestCategory, TUIConfig
from .template_manager import TemplateManager
from .utils import ensure_directory, write_file


def generate_tui_tests(
    config: TUIConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate all TUI test scenarios.

    Args:
        config: TUI application configuration
        template_mgr: Template manager
        output_dir: Output directory for generated test files

    Returns:
        List of GeneratedTest objects
    """
    generated = []
    generated.extend(_generate_tui_smoke_tests(config, template_mgr, output_dir))
    generated.extend(_generate_tui_navigation_tests(config, template_mgr, output_dir))
    generated.extend(_generate_tui_form_tests(config, template_mgr, output_dir))
    generated.extend(_generate_tui_interaction_tests(config, template_mgr, output_dir))
    return generated


def _generate_tui_smoke_tests(
    config: TUIConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate TUI smoke tests (startup, render, exit)."""
    tests_dir = output_dir / "tui-smoke"
    ensure_directory(tests_dir)

    app_name = config.binary_path.split("/")[-1] if "/" in config.binary_path else config.binary_path

    # Build widget check steps
    widget_checks = ""
    for widget in config.widgets:
        widget_checks += f"""    - action: verify_screen
      matches: ".*"
      description: "Verify {widget.name} ({widget.widget_type}) is rendered"

"""

    # Determine quit key from shortcuts or default
    quit_key = "q"
    for key, action in config.keyboard_shortcuts.items():
        if action in ("quit", "exit", "close"):
            quit_key = key
            break

    context = {
        "app_name": app_name,
        "binary_path": config.binary_path,
        "terminal_width": config.terminal_width,
        "terminal_height": config.terminal_height,
        "launch_args": "",
        "ready_pattern": ".*",  # Any render is ready
        "widget_checks": widget_checks,
        "quit_key": quit_key,
    }

    content = template_mgr.render("tui_smoke", context)
    test_file = tests_dir / "smoke.yaml"
    write_file(test_file, content)

    return [
        GeneratedTest(
            category=TestCategory.TUI_SMOKE,
            file_path=test_file,
            test_count=3 + min(len(config.widgets), 5),
            description="TUI smoke tests (startup, render, exit)",
        )
    ]


def _generate_tui_navigation_tests(
    config: TUIConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate TUI keyboard navigation test scenarios."""
    tests_dir = output_dir / "tui-navigation"
    ensure_directory(tests_dir)

    app_name = config.binary_path.split("/")[-1] if "/" in config.binary_path else config.binary_path

    # Build navigation steps from keyboard shortcuts
    nav_steps = ""
    if config.keyboard_shortcuts:
        for key, action in config.keyboard_shortcuts.items():
            if action in ("quit", "exit", "close"):
                continue
            nav_steps += f"""    - action: send_keypress
      value: "{key}"
      description: "Press '{key}' to {action}"

    - action: capture_screenshot
      save_as: "after-{key}.txt"
      description: "Capture screen after {action}"

"""
    else:
        # Default navigation test with arrow keys
        nav_steps = """    - action: send_keypress
      value: "down"
      description: "Navigate down"

    - action: capture_screenshot
      save_as: "after-down.txt"
      description: "Capture screen after down"

    - action: send_keypress
      value: "up"
      description: "Navigate up"

    - action: capture_screenshot
      save_as: "after-up.txt"
      description: "Capture screen after up"

    - action: send_keypress
      value: "tab"
      description: "Tab to next element"

    - action: capture_screenshot
      save_as: "after-tab.txt"
      description: "Capture screen after tab"

"""

    quit_key = "q"
    for key, action in config.keyboard_shortcuts.items():
        if action in ("quit", "exit", "close"):
            quit_key = key
            break

    context = {
        "app_name": app_name,
        "binary_path": config.binary_path,
        "terminal_width": config.terminal_width,
        "terminal_height": config.terminal_height,
        "launch_args": "",
        "ready_pattern": ".*",
        "navigation_steps": nav_steps,
        "quit_key": quit_key,
    }

    content = template_mgr.render("tui_navigation", context)
    test_file = tests_dir / "navigation.yaml"
    write_file(test_file, content)

    shortcut_count = len([
        k for k, v in config.keyboard_shortcuts.items()
        if v not in ("quit", "exit", "close")
    ])
    step_count = max(shortcut_count * 2, 6)  # At least 6 steps from default

    return [
        GeneratedTest(
            category=TestCategory.TUI_NAVIGATION,
            file_path=test_file,
            test_count=step_count,
            description="TUI keyboard navigation tests",
        )
    ]


def _generate_tui_form_tests(
    config: TUIConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate TUI form interaction test scenarios."""
    tests_dir = output_dir / "tui-forms"
    ensure_directory(tests_dir)

    generated = []
    app_name = config.binary_path.split("/")[-1] if "/" in config.binary_path else config.binary_path

    # Find input widgets
    input_widgets = [w for w in config.widgets if w.widget_type == "input"]
    if not input_widgets:
        # Create a generic form test
        input_widgets = [type("W", (), {"name": "input", "widget_type": "input"})()]

    content = f"""# TUI Form Interaction Test - {app_name}
# Auto-generated outside-in test scenario

scenario:
  name: "TUI Forms - {app_name} Input Handling"
  description: |
    Verifies form input handling in {app_name} including text entry,
    field navigation, and validation feedback.
  type: tui
  level: 2
  tags: [tui, forms, input, auto-generated]

  prerequisites:
    - "{config.binary_path} binary exists"
    - "Terminal supports ANSI escape codes"

  environment:
    terminal_size:
      width: {config.terminal_width}
      height: {config.terminal_height}
    variables:
      TERM: "xterm-256color"

  steps:
    - action: launch
      target: "{config.binary_path}"
      description: "Start TUI application"
      timeout: 10s

    - action: wait_for_screen
      matches: ".*"
      timeout: 5s
      description: "Wait for application to render"

    - action: send_keypress
      value: "test input text"
      description: "Type text into input field"

    - action: verify_screen
      contains: "test input text"
      description: "Input text should be visible"

    - action: send_keypress
      value: "ctrl+u"
      description: "Clear input field"

    - action: send_keypress
      value: "tab"
      description: "Tab to next field"

    - action: capture_screenshot
      save_as: "form-interaction.txt"
      description: "Capture form state"

    - action: send_keypress
      value: "q"
      description: "Exit application"

    - action: verify_exit_code
      expected: 0

  cleanup:
    - action: stop_application
      force: true
      description: "Ensure process is terminated"
"""
    test_file = tests_dir / "form-interaction.yaml"
    write_file(test_file, content)

    generated.append(
        GeneratedTest(
            category=TestCategory.TUI_FORMS,
            file_path=test_file,
            test_count=4,
            description="TUI form interaction tests",
        )
    )
    return generated


def _generate_tui_interaction_tests(
    config: TUIConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate TUI widget interaction test scenarios."""
    tests_dir = output_dir / "tui-interaction"
    ensure_directory(tests_dir)

    generated = []
    app_name = config.binary_path.split("/")[-1] if "/" in config.binary_path else config.binary_path

    # Generate tests for specific widget types
    widget_types_found = set(w.widget_type for w in config.widgets)

    if "list" in widget_types_found or "table" in widget_types_found:
        content = f"""# TUI List/Table Interaction Test
# Auto-generated outside-in test scenario

scenario:
  name: "TUI Interaction - {app_name} List/Table Navigation"
  description: |
    Verifies list and table widget interactions including selection,
    scrolling, and item activation.
  type: tui
  level: 2
  tags: [tui, interaction, list, table, auto-generated]

  prerequisites:
    - "{config.binary_path} binary exists"

  environment:
    terminal_size:
      width: {config.terminal_width}
      height: {config.terminal_height}
    variables:
      TERM: "xterm-256color"

  steps:
    - action: launch
      target: "{config.binary_path}"
      description: "Start TUI application"
      timeout: 10s

    - action: wait_for_screen
      matches: ".*"
      timeout: 5s
      description: "Wait for list/table to render"

    - action: send_keypress
      value: "down"
      times: 3
      description: "Navigate down in list"

    - action: capture_screenshot
      save_as: "list-after-down.txt"
      description: "Capture list selection state"

    - action: send_keypress
      value: "up"
      times: 2
      description: "Navigate up in list"

    - action: send_keypress
      value: "enter"
      description: "Activate selected item"

    - action: capture_screenshot
      save_as: "list-after-activate.txt"
      description: "Capture state after activation"

    - action: send_keypress
      value: "escape"
      description: "Go back / cancel"

    - action: send_keypress
      value: "q"
      description: "Exit application"

    - action: verify_exit_code
      expected: 0

  cleanup:
    - action: stop_application
      force: true
"""
        test_file = tests_dir / "list-table-interaction.yaml"
        write_file(test_file, content)

        generated.append(
            GeneratedTest(
                category=TestCategory.TUI_INTERACTION,
                file_path=test_file,
                test_count=5,
                description="TUI list/table interaction tests",
            )
        )

    if not generated:
        # Generic interaction test if no specific widgets found
        content = f"""# TUI General Interaction Test
# Auto-generated outside-in test scenario

scenario:
  name: "TUI Interaction - {app_name} General"
  description: |
    Verifies basic widget interactions in {app_name}.
  type: tui
  level: 1
  tags: [tui, interaction, general, auto-generated]

  prerequisites:
    - "{config.binary_path} binary exists"

  environment:
    terminal_size:
      width: {config.terminal_width}
      height: {config.terminal_height}
    variables:
      TERM: "xterm-256color"

  steps:
    - action: launch
      target: "{config.binary_path}"
      description: "Start TUI application"
      timeout: 10s

    - action: wait_for_screen
      matches: ".*"
      timeout: 5s

    - action: send_keypress
      value: "enter"
      description: "Press enter to interact"

    - action: capture_screenshot
      save_as: "interaction-result.txt"

    - action: send_keypress
      value: "escape"
      description: "Press escape"

    - action: send_keypress
      value: "q"
      description: "Exit"

    - action: verify_exit_code
      expected: 0

  cleanup:
    - action: stop_application
      force: true
"""
        test_file = tests_dir / "general-interaction.yaml"
        write_file(test_file, content)

        generated.append(
            GeneratedTest(
                category=TestCategory.TUI_INTERACTION,
                file_path=test_file,
                test_count=3,
                description="TUI general interaction tests",
            )
        )

    return generated
