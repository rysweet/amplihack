# E2E Outside-In Test Generator - Usage Examples

This document provides real-world usage examples for the E2E Outside-In Test Generator skill.

## Example 1: Basic Usage - Next.js E-commerce App

### Project Structure

```
my-ecommerce-app/
├── app/
│   ├── page.tsx                 # Homepage
│   ├── login/page.tsx           # Login page
│   ├── products/
│   │   ├── page.tsx             # Product list
│   │   └── [id]/page.tsx        # Product detail
│   └── checkout/page.tsx        # Checkout flow
├── lib/
│   ├── api.ts                   # API client
│   └── db.ts                    # Database client
├── api/
│   ├── auth.ts                  # Auth endpoints
│   ├── products.ts              # Product endpoints
│   └── orders.ts                # Order endpoints
└── package.json
```

### Invoking the Skill

```bash
$ claude

> add e2e tests for my Next.js e-commerce app
```

### Generated Output

The skill generates a complete test suite:

```
e2e/
├── playwright.config.ts
├── test-helpers/
│   ├── auth.ts
│   ├── navigation.ts
│   ├── assertions.ts
│   └── data-setup.ts
├── fixtures/
│   ├── users.json
│   ├── products.json
│   └── seed.sql
├── happy-path/
│   ├── user-registration.spec.ts      # 1 test
│   ├── user-login.spec.ts             # 2 tests
│   ├── product-browsing.spec.ts       # 3 tests
│   └── checkout-flow.spec.ts          # 4 tests
├── edge-cases/
│   ├── invalid-email.spec.ts          # 2 tests
│   ├── out-of-stock.spec.ts           # 2 tests
│   ├── invalid-quantity.spec.ts       # 2 tests
│   └── duplicate-order.spec.ts        # 2 tests
├── error-handling/
│   ├── network-failures.spec.ts       # 3 tests
│   ├── api-errors.spec.ts             # 2 tests
│   └── validation-errors.spec.ts      # 2 tests
├── performance/
│   ├── page-load-times.spec.ts        # 3 tests
│   └── api-response-times.spec.ts     # 2 tests
├── security/
│   ├── unauthorized-access.spec.ts    # 3 tests
│   ├── xss-protection.spec.ts         # 2 tests
│   └── csrf-protection.spec.ts        # 1 test
├── accessibility/
│   ├── keyboard-navigation.spec.ts    # 3 tests
│   └── screen-reader.spec.ts          # 2 tests
└── integration/
    ├── database-persistence.spec.ts   # 2 tests
    └── payment-gateway.spec.ts        # 2 tests

Total: 44 tests
```

### Sample Generated Test

**File: `e2e/happy-path/checkout-flow.spec.ts`**

```typescript
import { test, expect } from "@playwright/test";
import { login, logout } from "../test-helpers/auth";
import { addToCart, getCartTotal } from "../test-helpers/cart";

test.describe("Checkout Flow", () => {
  test.beforeEach(async ({ page }) => {
    // Login with test user
    await login(page, "test@example.com", "Test123!");
  });

  test("user can complete full checkout flow", async ({ page }) => {
    // Navigate to products
    await page.goto("/products");
    await expect(page.getByRole("heading", { name: /products/i })).toBeVisible();

    // Add product to cart
    await page.getByRole("link", { name: /laptop/i }).click();
    await expect(page).toHaveURL(/\/products\/\d+/);
    await page.getByRole("button", { name: /add to cart/i }).click();
    await expect(page.getByText(/added to cart/i)).toBeVisible();

    // Go to checkout
    await page.getByRole("link", { name: /cart/i }).click();
    await expect(page).toHaveURL("/cart");
    await page.getByRole("button", { name: /checkout/i }).click();

    // Fill shipping info
    await page.getByRole("textbox", { name: /address/i }).fill("123 Main St");
    await page.getByRole("textbox", { name: /city/i }).fill("San Francisco");
    await page.getByRole("textbox", { name: /zip/i }).fill("94102");

    // Fill payment info
    await page.getByRole("textbox", { name: /card number/i }).fill("4242424242424242");
    await page.getByRole("textbox", { name: /expiry/i }).fill("12/25");
    await page.getByRole("textbox", { name: /cvv/i }).fill("123");

    // Submit order
    await page.getByRole("button", { name: /place order/i }).click();

    // Verify success
    await expect(page).toHaveURL(/\/orders\/\d+/);
    await expect(page.getByText(/order confirmed/i)).toBeVisible();
    const orderNumber = await page.getByText(/order #\d+/).textContent();
    expect(orderNumber).toMatch(/order #\d+/);
  });

  test("checkout calculates correct total with tax", async ({ page }) => {
    await page.goto("/products/1");
    await page.getByRole("button", { name: /add to cart/i }).click();
    await page.goto("/cart");

    const subtotal = await page.getByTestId("subtotal").textContent();
    const tax = await page.getByTestId("tax").textContent();
    const total = await page.getByTestId("total").textContent();

    // Verify tax calculation (assuming 8.5% tax rate)
    const subtotalNum = parseFloat(subtotal!.replace("$", ""));
    const expectedTax = subtotalNum * 0.085;
    const taxNum = parseFloat(tax!.replace("$", ""));

    expect(taxNum).toBeCloseTo(expectedTax, 2);
    expect(parseFloat(total!.replace("$", ""))).toBeCloseTo(subtotalNum + taxNum, 2);
  });
});
```

### Execution Results

```bash
$ npx playwright test

Running 44 tests using 1 worker

  ✓  e2e/happy-path/user-registration.spec.ts:4:3 › user can register (2.1s)
  ✓  e2e/happy-path/user-login.spec.ts:4:3 › user can login (1.5s)
  ✓  e2e/happy-path/checkout-flow.spec.ts:8:3 › complete checkout (3.2s)
  ✓  e2e/edge-cases/invalid-email.spec.ts:4:3 › rejects invalid email (0.8s)
  ...
  ✓  e2e/integration/database-persistence.spec.ts:4:3 › order persists (2.4s)

  44 passed (1.8m)
```

### Bug Discovery Report

```markdown
## Bugs Found During Test Generation

### Bug 1: SQL Injection Vulnerability [CRITICAL]

- **Location**: `app/login/page.tsx:45`
- **Description**: Login form vulnerable to SQL injection via email field
- **Test**: `e2e/security/sql-injection.spec.ts`
- **Evidence**:
```

Input: admin'--
Result: Authenticated as admin without password

```
- **Fix Required**: Use parameterized queries

### Bug 2: Cart Total Calculation Error [HIGH]
- **Location**: `lib/cart.ts:23`
- **Description**: Tax calculation uses wrong precision, causing cent-level errors
- **Test**: `e2e/happy-path/checkout-flow.spec.ts:32`
- **Evidence**:
```

Subtotal: $99.99
Expected tax (8.5%): $8.50
Actual tax: $8.49

```
- **Fix Required**: Use proper decimal arithmetic
```

## Example 2: Advanced Usage - Custom Locators

### Scenario

Your application uses a custom data attribute `data-qa` for test identification.

### Custom Configuration

**File: `e2e/playwright.config.ts`** (manually edit after generation)

```typescript
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: "http://localhost:3000",
    testIdAttribute: "data-qa", // Use custom attribute
  },
  // ... rest of config
});
```

### Custom Test Helper

**File: `e2e/test-helpers/locators.ts`** (create after generation)

```typescript
import { Page, Locator } from "@playwright/test";

/**
 * Find element by data-qa attribute
 */
export function findByQA(page: Page, qa: string): Locator {
  return page.locator(`[data-qa="${qa}"]`);
}

/**
 * Find button by data-qa and click
 */
export async function clickByQA(page: Page, qa: string): Promise<void> {
  await findByQA(page, qa).click();
}

/**
 * Find input by data-qa and fill
 */
export async function fillByQA(page: Page, qa: string, value: string): Promise<void> {
  await findByQA(page, qa).fill(value);
}
```

### Using Custom Locators

**File: `e2e/happy-path/custom-login.spec.ts`** (update after generation)

```typescript
import { test, expect } from "@playwright/test";
import { findByQA, clickByQA, fillByQA } from "../test-helpers/locators";

test("login with custom locators", async ({ page }) => {
  await page.goto("/login");

  // Use custom locator helpers
  await fillByQA(page, "email-input", "test@example.com");
  await fillByQA(page, "password-input", "Test123!");
  await clickByQA(page, "login-button");

  await expect(findByQA(page, "welcome-message")).toBeVisible();
});
```

## Example 3: Integration with test-gap-analyzer

### Workflow

First, analyze existing test coverage, then generate E2E tests to fill gaps.

```bash
$ claude

> analyze test gaps and generate e2e tests to fill them
```

### Process

1. **test-gap-analyzer runs first**:

   ```
   Test Coverage Analysis:
   - User registration: 45% coverage (missing edge cases)
   - Product search: 20% coverage (missing pagination)
   - Checkout flow: 60% coverage (missing payment errors)
   - Admin panel: 0% coverage (completely untested)
   ```

2. **E2E generator prioritizes gaps**:

   ```
   Prioritized Test Generation:
   1. Admin panel tests (HIGH priority - 0% coverage)
   2. Product search edge cases (MEDIUM priority - 20% coverage)
   3. Payment error handling (MEDIUM priority - missing)
   4. User registration edge cases (LOW priority - 45% coverage)
   ```

3. **Generated tests focus on gaps**:
   ```
   e2e/
   ├── admin/                      # NEW - fills 0% gap
   │   ├── user-management.spec.ts
   │   ├── product-management.spec.ts
   │   └── analytics.spec.ts
   ├── search/                     # EXPANDED - fills 20% gap
   │   ├── pagination.spec.ts      # NEW
   │   ├── sorting.spec.ts         # NEW
   │   └── filters.spec.ts         # NEW
   └── payment/                    # EXPANDED - fills missing scenarios
       ├── declined-card.spec.ts   # NEW
       ├── expired-card.spec.ts    # NEW
       └── insufficient-funds.spec.ts # NEW
   ```

### Results

```
Gap Analysis Before:
- Overall coverage: 42%
- High-risk uncovered: 8 flows

Gap Analysis After:
- Overall coverage: 78%
- High-risk uncovered: 1 flow

Improvement: +36% coverage, 7 high-risk flows now covered
```

## Example 4: Custom Seed Data

### Scenario

Your application requires specific test data scenarios (bulk orders, loyalty points, etc).

### Custom Fixture

**File: `e2e/fixtures/custom-scenarios.json`** (create after generation)

```json
{
  "scenarios": [
    {
      "name": "bulk-order",
      "description": "User placing bulk order with discount",
      "user": {
        "email": "bulk@example.com",
        "password": "Test123!", // pragma: allowlist secret
        "accountType": "business"
      },
      "cart": [
        { "productId": 1, "quantity": 50 },
        { "productId": 3, "quantity": 30 }
      ],
      "expectedDiscount": 0.15,
      "expectedShipping": "free"
    },
    {
      "name": "loyalty-redemption",
      "description": "User redeeming loyalty points",
      "user": {
        "email": "loyal@example.com",
        "password": "Test123!", // pragma: allowlist secret
        "loyaltyPoints": 5000
      },
      "cart": [{ "productId": 2, "quantity": 1 }],
      "pointsToRedeem": 1000,
      "expectedDiscount": 10.0
    }
  ]
}
```

### Custom Test Using Scenarios

**File: `e2e/business-logic/bulk-order.spec.ts`** (create after generation)

```typescript
import { test, expect } from "@playwright/test";
import { login } from "../test-helpers/auth";
import scenarios from "../fixtures/custom-scenarios.json";

test.describe("Bulk Order Discount", () => {
  test("applies 15% discount for orders over 50 units", async ({ page }) => {
    const scenario = scenarios.scenarios.find((s) => s.name === "bulk-order")!;

    // Login with business account
    await login(page, scenario.user.email, scenario.user.password);

    // Add items to cart
    for (const item of scenario.cart) {
      await page.goto(`/products/${item.productId}`);
      await page.getByRole("spinbutton", { name: /quantity/i }).fill(item.quantity.toString());
      await page.getByRole("button", { name: /add to cart/i }).click();
    }

    // Go to cart and verify discount
    await page.goto("/cart");
    const subtotal = await page.getByTestId("subtotal").textContent();
    const discount = await page.getByTestId("discount").textContent();
    const total = await page.getByTestId("total").textContent();

    const subtotalNum = parseFloat(subtotal!.replace("$", ""));
    const expectedDiscount = subtotalNum * scenario.expectedDiscount;
    const discountNum = parseFloat(discount!.replace("$", ""));

    expect(discountNum).toBeCloseTo(expectedDiscount, 2);
    expect(await page.getByText(/free shipping/i).isVisible()).toBe(true);
  });
});
```

## Example 5: Troubleshooting Common Issues

### Issue 1: Flaky Tests Due to Animation

**Problem**: Test fails intermittently because it clicks element during CSS animation.

**Original Test** (generated):

```typescript
test("modal closes on button click", async ({ page }) => {
  await page.getByRole("button", { name: /open modal/i }).click();
  await page.getByRole("button", { name: /close/i }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible(); // FLAKY
});
```

**Fix**: Wait for animation to complete.

```typescript
test("modal closes on button click", async ({ page }) => {
  await page.getByRole("button", { name: /open modal/i }).click();

  // Wait for modal to be fully visible (animation complete)
  const modal = page.getByRole("dialog");
  await expect(modal).toBeVisible();
  await page.waitForTimeout(300); // Wait for animation

  await page.getByRole("button", { name: /close/i }).click();

  // Wait for closing animation
  await expect(modal).not.toBeVisible();
});
```

### Issue 2: Test Data Conflicts

**Problem**: Tests fail in CI because database state is polluted from previous test.

**Original Test** (generated):

```typescript
test("user can register with email", async ({ page }) => {
  await page.goto("/register");
  await page.getByRole("textbox", { name: /email/i }).fill("test@example.com");
  await page.getByRole("textbox", { name: /password/i }).fill("Test123!");
  await page.getByRole("button", { name: /register/i }).click();
  await expect(page).toHaveURL("/dashboard"); // FAILS if email exists
});
```

**Fix**: Use unique email per test run.

```typescript
test("user can register with email", async ({ page }) => {
  const uniqueEmail = `test-${Date.now()}@example.com`;

  await page.goto("/register");
  await page.getByRole("textbox", { name: /email/i }).fill(uniqueEmail);
  await page.getByRole("textbox", { name: /password/i }).fill("Test123!");
  await page.getByRole("button", { name: /register/i }).click();
  await expect(page).toHaveURL("/dashboard");
});
```

### Issue 3: Locator Not Found

**Problem**: Test fails because element selector is too specific.

**Original Test** (generated):

```typescript
test("submits form", async ({ page }) => {
  await page.goto("/contact");
  await page.locator("#submit-button").click(); // BRITTLE - ID may change
});
```

**Fix**: Use role-based locator.

```typescript
test("submits form", async ({ page }) => {
  await page.goto("/contact");
  await page.getByRole("button", { name: /submit/i }).click(); // ROBUST
});
```

## Example 6: CI/CD Integration

### GitHub Actions Workflow

**File: `.github/workflows/e2e.yml`**

```yaml
name: E2E Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  e2e:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: testdb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-node@v3
        with:
          node-version: "18"
          cache: "npm"

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright browsers
        run: npx playwright install --with-deps

      - name: Setup database
        run: |
          npm run db:migrate
          npm run db:seed:test
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/testdb # pragma: allowlist secret

      - name: Build application
        run: npm run build

      - name: Run E2E tests
        run: npm run test:e2e
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/testdb # pragma: allowlist secret
          NODE_ENV: test

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 30

      - name: Upload screenshots on failure
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: screenshots
          path: e2e/test-results/
          retention-days: 7
```

### Running Tests Locally

```bash
# Run all tests
npm run test:e2e

# Run specific category
npm run test:e2e -- e2e/happy-path

# Run in headed mode
npm run test:e2e -- --headed

# Run with debugging
npm run test:e2e -- --debug

# Generate HTML report
npx playwright show-report
```

## Example 7: Performance Profiling

### Generated Performance Test

**File: `e2e/performance/api-response-times.spec.ts`**

```typescript
import { test, expect } from "@playwright/test";

test.describe("API Performance", () => {
  test("product list API responds in under 500ms", async ({ page }) => {
    const startTime = Date.now();

    const response = await page.request.get("/api/products");
    const endTime = Date.now();

    expect(response.ok()).toBeTruthy();
    expect(endTime - startTime).toBeLessThan(500);
  });

  test("search API responds in under 1 second", async ({ page }) => {
    const startTime = Date.now();

    const response = await page.request.get("/api/search?q=laptop");
    const endTime = Date.now();

    expect(response.ok()).toBeTruthy();
    expect(endTime - startTime).toBeLessThan(1000);
  });
});
```

### Enhanced with Detailed Metrics

```typescript
test("product list API performance metrics", async ({ page }) => {
  const metrics = {
    requests: [] as number[],
  };

  // Run 10 requests to get average
  for (let i = 0; i < 10; i++) {
    const start = Date.now();
    const response = await page.request.get("/api/products");
    const duration = Date.now() - start;

    expect(response.ok()).toBeTruthy();
    metrics.requests.push(duration);
  }

  // Calculate statistics
  const avg = metrics.requests.reduce((a, b) => a + b) / metrics.requests.length;
  const max = Math.max(...metrics.requests);
  const min = Math.min(...metrics.requests);

  console.log(`Average: ${avg}ms, Min: ${min}ms, Max: ${max}ms`);

  expect(avg).toBeLessThan(500);
  expect(max).toBeLessThan(1000);
});
```

---

**See also:**

- [SKILL.md](./SKILL.md) - Complete skill documentation
- [README.md](./README.md) - Developer documentation
- [reference.md](./reference.md) - API reference
- [patterns.md](./patterns.md) - Common patterns
