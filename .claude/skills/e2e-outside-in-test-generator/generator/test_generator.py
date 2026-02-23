"""Test generation across 7 categories.

Generates ≥40 tests across all categories using templates.
Enforces locator priority: Role-based > User-visible text > Test ID > CSS.
"""

from pathlib import Path

from .models import (
    GeneratedTest,
    LocatorStrategy,
    StackConfig,
    TestCategory,
    TestGenerationError,
)
from .template_manager import TemplateManager
from .utils import ensure_directory, write_file


def generate_all_tests(
    stack: StackConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate all test categories.

    Generates ≥40 tests total across 7 categories.

    Args:
        stack: Stack configuration
        template_mgr: Template manager
        output_dir: Output directory (e2e/)

    Returns:
        List of GeneratedTest objects

    Raises:
        TestGenerationError: If generation fails
    """
    generated_tests = []

    try:
        # Generate ALL 7 categories (MANDATORY - explicit user requirement)
        generated_tests.extend(generate_smoke_tests(stack, template_mgr, output_dir))
        generated_tests.extend(generate_form_interaction_tests(stack, template_mgr, output_dir))
        generated_tests.extend(
            generate_component_interaction_tests(stack, template_mgr, output_dir)
        )
        generated_tests.extend(generate_keyboard_shortcut_tests(stack, template_mgr, output_dir))
        generated_tests.extend(generate_api_streaming_tests(stack, template_mgr, output_dir))
        generated_tests.extend(generate_responsive_tests(stack, template_mgr, output_dir))
        generated_tests.extend(generate_pwa_tests(stack, template_mgr, output_dir))

        # Verify minimum test count
        total_tests = sum(t.test_count for t in generated_tests)
        if total_tests < 40:
            raise TestGenerationError(f"Generated only {total_tests} tests, minimum is 40")

        return generated_tests

    except Exception as e:
        raise TestGenerationError(f"Test generation failed: {e}")


def generate_smoke_tests(
    stack: StackConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate smoke tests for critical user journeys.

    Args:
        stack: Stack configuration
        template_mgr: Template manager
        output_dir: Output directory

    Returns:
        List of GeneratedTest objects
    """
    tests_dir = output_dir / "smoke"
    ensure_directory(tests_dir)

    generated = []

    # Generate smoke test for each route
    for route in stack.routes[:5]:  # Max 5 routes
        context = {
            "feature_name": route.component.replace("/", " ").title(),
            "route": route.path,
            "title_pattern": route.component.replace("/", " ").title(),
            "key_element_role": "heading",
            "key_element_name": route.component.replace("/", " ").title(),
            "critical_flow_steps": "// Navigate through critical flow\n    await page.getByRole('button', { name: /get started/i }).click();",
            "success_element_role": "heading",
            "success_element_name": "Success",
        }

        test_content = template_mgr.render("smoke", context)
        test_file = tests_dir / f"smoke-{route.path.replace('/', '-').strip('-') or 'home'}.spec.ts"
        write_file(test_file, test_content)

        generated.append(
            GeneratedTest(
                category=TestCategory.SMOKE,
                file_path=test_file,
                test_count=3,  # 3 tests per file
                description=f"Smoke tests for {route.path}",
                locator_strategies=[LocatorStrategy.ROLE_BASED],
            )
        )

    return generated


def generate_form_interaction_tests(
    stack: StackConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate form interaction tests.

    Args:
        stack: Stack configuration
        template_mgr: Template manager
        output_dir: Output directory

    Returns:
        List of GeneratedTest objects
    """
    tests_dir = output_dir / "forms"
    ensure_directory(tests_dir)

    generated = []

    # Common form types
    forms = [
        {"name": "Login", "route": "/login", "fields": ["email", "password"]},
        {"name": "Registration", "route": "/register", "fields": ["name", "email", "password"]},
        {"name": "Contact", "route": "/contact", "fields": ["name", "email", "message"]},
    ]

    for form in forms:
        form_fill_steps = "\n".join(
            [
                f"    await page.getByRole('textbox', {{ name: /{field}/i }}).fill('test-{field}');"
                for field in form["fields"]
            ]
        )

        validation_checks = "\n".join(
            [
                f"    await expect(page.getByText(/{field} is required/i)).toBeVisible();"
                for field in form["fields"]
            ]
        )

        invalid_data_steps = f"    await page.getByRole('textbox', {{ name: /{form['fields'][0]}/i }}).fill('invalid-data');"

        context = {
            "form_name": form["name"],
            "route": form["route"],
            "form_fill_steps": form_fill_steps,
            "submit_button_text": "Submit",
            "success_message": "Success|Submitted|Thank you",
            "validation_checks": validation_checks,
            "invalid_data_steps": invalid_data_steps,
            "error_message": "Error|Invalid|Failed",
        }

        test_content = template_mgr.render("form_interaction", context)
        test_file = tests_dir / f"{form['name'].lower()}-form.spec.ts"
        write_file(test_file, test_content)

        generated.append(
            GeneratedTest(
                category=TestCategory.FORM_INTERACTION,
                file_path=test_file,
                test_count=3,
                description=f"{form['name']} form interaction tests",
                locator_strategies=[LocatorStrategy.ROLE_BASED, LocatorStrategy.USER_VISIBLE_TEXT],
            )
        )

    return generated


def generate_component_interaction_tests(
    stack: StackConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate component interaction tests.

    Args:
        stack: Stack configuration
        template_mgr: Template manager
        output_dir: Output directory

    Returns:
        List of GeneratedTest objects
    """
    tests_dir = output_dir / "components"
    ensure_directory(tests_dir)

    generated = []

    # Common interactive components
    components = [
        {"name": "Modal", "role": "dialog", "label": "Modal Dialog"},
        {"name": "Dropdown", "role": "combobox", "label": "Select Option"},
        {"name": "Tabs", "role": "tablist", "label": "Tabs"},
        {"name": "Accordion", "role": "button", "label": "Accordion Item"},
    ]

    for component in components:
        context = {
            "component_name": component["name"],
            "route": "/",
            "component_role": component["role"],
            "component_label": component["label"],
            "interaction_steps": "    await component.click();",
            "expected_result": "Opened|Visible|Active",
            "state_change_steps": f"    await page.getByRole('{component['role']}', {{ name: /{component['label']}/i }}).click();",
            "result_element_role": "status",
            "result_element_name": "Updated",
            "keyboard_navigation_steps": "    await page.keyboard.press('ArrowDown');",
            "focused_element_role": "option",
        }

        test_content = template_mgr.render("component_interaction", context)
        test_file = tests_dir / f"{component['name'].lower()}.spec.ts"
        write_file(test_file, test_content)

        generated.append(
            GeneratedTest(
                category=TestCategory.COMPONENT_INTERACTION,
                file_path=test_file,
                test_count=3,
                description=f"{component['name']} component interaction tests",
                locator_strategies=[LocatorStrategy.ROLE_BASED],
            )
        )

    return generated


def generate_keyboard_shortcut_tests(
    stack: StackConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate keyboard shortcut tests.

    Args:
        stack: Stack configuration
        template_mgr: Template manager
        output_dir: Output directory

    Returns:
        List of GeneratedTest objects
    """
    tests_dir = output_dir / "keyboard"
    ensure_directory(tests_dir)

    generated = []

    shortcuts = [
        {
            "name": "Open Search",
            "keys": "Control+K",
            "result_role": "searchbox",
            "result_name": "Search",
        },
        {"name": "Save", "keys": "Control+S", "result_role": "status", "result_name": "Saved"},
    ]

    for shortcut in shortcuts:
        context = {
            "feature_name": "Global Shortcuts",
            "route": "/",
            "shortcut_name": shortcut["name"],
            "shortcut_keys": shortcut["keys"],
            "result_element_role": shortcut["result_role"],
            "result_element_name": shortcut["result_name"],
            "first_focusable_role": "button",
            "escape_test_steps": "    await page.keyboard.press('Escape');",
            "enter_test_steps": "    await page.keyboard.press('Enter');",
            "accessibility_keyboard_steps": "    await page.keyboard.press('Space');",
            "aria_element_role": "button",
        }

        test_content = template_mgr.render("keyboard_shortcuts", context)
        test_file = tests_dir / f"{shortcut['name'].lower().replace(' ', '-')}.spec.ts"
        write_file(test_file, test_content)

        generated.append(
            GeneratedTest(
                category=TestCategory.KEYBOARD_SHORTCUTS,
                file_path=test_file,
                test_count=3,
                description=f"{shortcut['name']} keyboard shortcut tests",
                locator_strategies=[LocatorStrategy.ROLE_BASED],
            )
        )

    return generated


def generate_api_streaming_tests(
    stack: StackConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate API streaming tests.

    Args:
        stack: Stack configuration
        template_mgr: Template manager
        output_dir: Output directory

    Returns:
        List of GeneratedTest objects
    """
    tests_dir = output_dir / "streaming"
    ensure_directory(tests_dir)

    generated = []

    # Find streaming endpoints
    streaming_endpoints = [
        {"name": "Chat Stream", "endpoint": "/api/chat/stream", "route": "/chat"},
        {"name": "Data Feed", "endpoint": "/api/feed/stream", "route": "/feed"},
    ]

    for endpoint in streaming_endpoints:
        context = {
            "api_name": endpoint["name"],
            "endpoint": endpoint["endpoint"],
            "route": endpoint["route"],
            "api_endpoint": endpoint["endpoint"],
            "mock_stream_data": "data: chunk1\\ndata: chunk2\\ndata: [DONE]\\n",
            "trigger_steps": "    await page.getByRole('button', { name: /start/i }).click();",
            "first_chunk_pattern": "chunk|data|response",
            "completion_pattern": "done|complete|finished",
            "streaming_setup_steps": "    await page.getByRole('button', { name: /start/i }).click();",
            "partial_result_role": "status",
            "partial_text": "Loading|Processing",
            "error_message": "Error|Failed|Timeout",
        }

        test_content = template_mgr.render("api_streaming", context)
        test_file = tests_dir / f"{endpoint['name'].lower().replace(' ', '-')}.spec.ts"
        write_file(test_file, test_content)

        generated.append(
            GeneratedTest(
                category=TestCategory.API_STREAMING,
                file_path=test_file,
                test_count=3,
                description=f"{endpoint['name']} streaming tests",
                locator_strategies=[LocatorStrategy.ROLE_BASED, LocatorStrategy.USER_VISIBLE_TEXT],
            )
        )

    return generated


def generate_responsive_tests(
    stack: StackConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate responsive design tests.

    Args:
        stack: Stack configuration
        template_mgr: Template manager
        output_dir: Output directory

    Returns:
        List of GeneratedTest objects
    """
    tests_dir = output_dir / "responsive"
    ensure_directory(tests_dir)

    generated = []

    # Test main routes for responsiveness
    for route in stack.routes[:2]:  # Test first 2 routes
        context = {
            "feature_name": route.component.replace("/", " ").title(),
            "route": route.path,
            "mobile_element_role": "button",
            "mobile_element_name": "Menu",
            "mobile_nav_steps": "    await page.getByRole('button', { name: /menu/i }).click();",
            "tablet_element_role": "navigation",
            "tablet_element_name": "Navigation",
            "desktop_element_role": "navigation",
            "desktop_element_name": "Navigation",
        }

        test_content = template_mgr.render("responsive", context)
        test_file = (
            tests_dir / f"responsive-{route.path.replace('/', '-').strip('-') or 'home'}.spec.ts"
        )
        write_file(test_file, test_content)

        generated.append(
            GeneratedTest(
                category=TestCategory.RESPONSIVE,
                file_path=test_file,
                test_count=4,
                description=f"Responsive tests for {route.path}",
                locator_strategies=[LocatorStrategy.ROLE_BASED],
            )
        )

    return generated


def generate_pwa_tests(
    stack: StackConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate PWA basics tests.

    Args:
        stack: Stack configuration
        template_mgr: Template manager
        output_dir: Output directory

    Returns:
        List of GeneratedTest objects
    """
    tests_dir = output_dir / "pwa"
    ensure_directory(tests_dir)

    generated = []

    context = {
        "app_name": stack.frontend_framework.title() + " App",
        "route": "/",
        "main_element_role": "main",
        "main_element_name": "Content",
    }

    test_content = template_mgr.render("pwa_basics", context)
    test_file = tests_dir / "pwa-basics.spec.ts"
    write_file(test_file, test_content)

    generated.append(
        GeneratedTest(
            category=TestCategory.PWA_BASICS,
            file_path=test_file,
            test_count=4,
            description="PWA basics tests",
            locator_strategies=[LocatorStrategy.CSS_SELECTOR],  # PWA needs CSS selectors
        )
    )

    return generated
