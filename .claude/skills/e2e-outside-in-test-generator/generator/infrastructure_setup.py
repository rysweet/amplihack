"""Infrastructure setup for E2E testing.

Generates Playwright config, test helpers, and seed data.
ENFORCES workers=1 in all generated configs.
"""

from pathlib import Path

from .models import InfrastructureSetupError, StackConfig
from .utils import ensure_directory, write_file, write_json_file


def setup_infrastructure(stack: StackConfig, output_dir: Path) -> None:
    """Create complete testing infrastructure.

    Args:
        stack: Detected stack configuration
        output_dir: Directory to create infrastructure in (e2e/)

    Raises:
        InfrastructureSetupError: If setup fails
    """
    try:
        ensure_directory(output_dir)

        # Generate playwright.config.ts
        config_content = create_playwright_config(stack)
        write_file(output_dir.parent / "playwright.config.ts", config_content)

        # Generate test helpers
        helpers_dir = output_dir / "test-helpers"
        ensure_directory(helpers_dir)

        helpers = create_test_helpers(stack)
        for filename, content in helpers.items():
            write_file(helpers_dir / filename, content)

        # Generate seed data
        fixtures_dir = output_dir / "fixtures"
        ensure_directory(fixtures_dir)

        seed_data = create_seed_data(stack)
        for filename, data in seed_data.items():
            write_json_file(fixtures_dir / filename, data)

    except Exception as e:
        raise InfrastructureSetupError(f"Infrastructure setup failed: {e}")


def create_playwright_config(stack: StackConfig) -> str:
    """Generate playwright.config.ts with workers=1.

    Args:
        stack: Stack configuration

    Returns:
        Playwright config file content
    """
    config = """import {{ defineConfig, devices }} from '@playwright/test';

export default defineConfig({{
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // MANDATORY: Must be 1 for deterministic execution
  reporter: 'html',
  use: {{
    baseURL: '{base_url}',
    trace: 'on-first-retry',
  }},

  projects: [
    {{
      name: 'chromium',
      use: {{ ...devices['Desktop Chrome'] }},
    }},
  ],

  webServer: {{
    command: '{dev_command}',
    url: '{base_url}',
    reuseExistingServer: !process.env.CI,
  }},
}});
"""

    # Determine dev command based on framework
    dev_command = "npm run dev"
    if stack.frontend_framework == "nextjs" or stack.frontend_framework in ["react", "vue"]:
        dev_command = "npm run dev"

    # Use api_base_url from stack
    base_url = stack.api_base_url

    return config.format(base_url=base_url, dev_command=dev_command)


def create_test_helpers(stack: StackConfig) -> dict[str, str]:
    """Generate helper functions for tests.

    Args:
        stack: Stack configuration

    Returns:
        Dict of filename -> content
    """
    helpers = {}

    # Authentication helper
    auth_helper = """import {{ Page }} from '@playwright/test';

export async function login(page: Page, email: string, password: string) {{
  await page.goto('/login');
  await page.getByRole('textbox', {{ name: /email/i }}).fill(email);
  await page.getByRole('textbox', {{ name: /password/i }}).fill(password);
  await page.getByRole('button', {{ name: /sign in/i }}).click();
  await page.waitForURL('/dashboard');
}}

export async function logout(page: Page) {{
  await page.getByRole('button', {{ name: /logout/i }}).click();
  await page.waitForURL('/login');
}}
"""
    helpers["auth.ts"] = auth_helper

    # Navigation helper
    nav_helper = """import {{ Page }} from '@playwright/test';

export async function navigateTo(page: Page, route: string) {{
  await page.goto(route);
  await page.waitForLoadState('networkidle');
}}

export async function clickLink(page: Page, linkText: string) {{
  await page.getByRole('link', {{ name: new RegExp(linkText, 'i') }}).click();
}}
"""
    helpers["navigation.ts"] = nav_helper

    # Assertions helper
    assertions_helper = """import {{ Page, expect }} from '@playwright/test';

export async function assertPageTitle(page: Page, title: string) {{
  await expect(page).toHaveTitle(new RegExp(title, 'i'));
}}

export async function assertElementVisible(page: Page, role: string, name: string) {{
  await expect(page.getByRole(role as any, {{ name: new RegExp(name, 'i') }})).toBeVisible();
}}

export async function assertNoConsoleErrors(page: Page) {{
  const errors: string[] = [];
  page.on('console', msg => {{
    if (msg.type() === 'error') {{
      errors.push(msg.text());
    }}
  }});
  return errors;
}}
"""
    helpers["assertions.ts"] = assertions_helper

    # Data setup helper
    data_setup_helper = """import {{ Page }} from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

export async function loadFixture(name: string): Promise<any> {{
  const fixturePath = path.join(__dirname, '../fixtures', `${{name}}.json`);
  const data = fs.readFileSync(fixturePath, 'utf-8');
  return JSON.parse(data);
}}

export async function seedDatabase(page: Page, fixture: string) {{
  const data = await loadFixture(fixture);
  // POST to /api/test/seed endpoint
  await page.request.post('/api/test/seed', {{ data }});
}}

export async function clearDatabase(page: Page) {{
  await page.request.post('/api/test/clear');
}}
"""
    helpers["data-setup.ts"] = data_setup_helper

    return helpers


def create_seed_data(stack: StackConfig) -> dict[str, dict]:
    """Generate small deterministic seed datasets.

    Creates 10-20 records max per fixture.

    Args:
        stack: Stack configuration

    Returns:
        Dict of filename -> data
    """
    seed_data = {}

    # Users fixture (10 users)
    users = {
        "users": [
            {"id": i, "email": f"user{i}@example.com", "name": f"User {i}", "role": "user"}
            for i in range(1, 11)
        ]
    }
    seed_data["users.json"] = users

    # Products fixture (15 products)
    products = {
        "products": [
            {
                "id": i,
                "name": f"Product {i}",
                "price": 10.00 + i,
                "category": ["Electronics", "Clothing", "Books"][i % 3],
                "inStock": i % 2 == 0,
            }
            for i in range(1, 16)
        ]
    }
    seed_data["products.json"] = products

    # Orders fixture (20 orders)
    orders = {
        "orders": [
            {
                "id": i,
                "userId": (i % 10) + 1,
                "productId": (i % 15) + 1,
                "quantity": i % 5 + 1,
                "status": ["pending", "shipped", "delivered"][i % 3],
                "createdAt": f"2024-01-{(i % 28) + 1:02d}T00:00:00Z",
            }
            for i in range(1, 21)
        ]
    }
    seed_data["orders.json"] = orders

    return seed_data
