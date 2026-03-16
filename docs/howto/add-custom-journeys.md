---
type: howto
skill: code-atlas
updated: 2026-03-16
---

# How to Add Custom User Journeys

Custom journeys define named end-to-end paths through your system for Pass 2 bug hunting and Layer 5 sequence diagrams.

---

## Why add custom journeys?

By default, the atlas auto-derives journeys from Layer 3 routes. Custom journeys let you:

- Name business-critical paths explicitly (e.g., "enterprise-checkout", "admin-export-report")
- Ensure Pass 2 traces the paths most likely to harbor bugs
- Document non-obvious multi-service flows that route-based derivation misses

**Rule:** One journey per significant business operation. Do not create a journey per route.

---

## Inline (via invocation)

Pass a journey definition directly:

```
/code-atlas journeys="user-checkout: POST /api/orders, admin-export: GET /api/reports/csv"
```

Format: `journey-name: entry-route` pairs, comma-separated.

---

## YAML file (for persistent journeys)

Create `docs/atlas/journeys.yaml` in your repository:

```yaml
# docs/atlas/journeys.yaml
# Defines named user journeys for Layer 5 and Pass 2 bug hunting.
# One entry per significant business flow.

journeys:
  - name: user-registration
    entry: "POST /api/auth/register"
    description: "New user registers, verifies email, and logs in for the first time"

  - name: user-checkout
    entry: "POST /api/orders"
    description: "Authenticated user adds items to cart, checks out, and receives confirmation"

  - name: admin-export-orders
    entry: "GET /api/admin/orders/export"
    description: "Admin downloads CSV export of all orders for a date range"

  - name: worker-process-payment
    entry: "kafka:PaymentRequested"
    description: "Worker consumes PaymentRequested event, calls Stripe, updates order status"
```

When this file exists, the atlas reads it automatically on each build.

---

## Journey schema

| Field         | Required | Description                                                                      |
| ------------- | -------- | -------------------------------------------------------------------------------- |
| `name`        | Yes      | Slug identifier — used in Layer 5 file names (e.g., `journey-user-checkout.mmd`) |
| `entry`       | Yes      | Route or event that starts the journey: `POST /api/orders` or `kafka:EventName`  |
| `description` | Yes      | One sentence — used as the sequence diagram title                                |

---

## What Pass 2 does with your journeys

For each journey, Pass 2:

1. Traces the entry point through Layer 3 (find the handler)
2. Follows the handler through Layer 4 (data transformations and persistence)
3. Crosses Layer 1 service boundaries (inter-service calls)
4. Checks Layer 2 dependencies (are all required packages present?)
5. Reports any contradiction found along the trace

A contradiction means a step in the journey either can't be executed (missing route, missing DTO field) or produces unexpected results (wrong data shape, missing side effect).

---

## Good and bad journey examples

**Good — traces a complete business operation:**

```yaml
- name: user-checkout
  entry: "POST /api/orders"
  description: "User completes purchase: validates cart, charges payment, confirms order"
```

**Bad — too granular (this is a route, not a journey):**

```yaml
- name: get-user-by-id # This is a route, not a journey
  entry: "GET /api/users/:id"
  description: "Get a user"
```

**Good — event-driven journey:**

```yaml
- name: email-verification
  entry: "kafka:UserRegistered"
  description: "Worker picks up UserRegistered event and sends verification email"
```

---

## Verifying your journeys appear in Layer 5

After adding journeys, rebuild Layer 5:

```
/code-atlas rebuild layer5
```

Check that each journey has a corresponding sequence diagram:

```bash
ls docs/atlas/layer5-journeys/
# journey-user-registration.mmd
# journey-user-checkout.mmd
# journey-admin-export-orders.mmd
# journey-worker-process-payment.mmd
# README.md
```

Each file contains a complete `sequenceDiagram` with actors, services, and database calls traced from the entry point.
