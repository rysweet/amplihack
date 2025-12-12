# Execution Sequence Template

## When to Use This Template

Use this template when investigating or explaining:

- Request/response flows
- API call sequences
- User interaction workflows
- Multi-step processes
- Actor interactions
- System lifecycle events

**Trigger Conditions:**

- Process has specific sequence of steps
- Multiple actors/systems interact
- Time-based flow is important
- Request/response pattern exists

**Examples:**

- API request/response flows
- User authentication sequences
- Database transaction flows
- Multi-service orchestration
- Login workflows
- Payment processing flows

## Template Diagram

```mermaid
sequenceDiagram
    participant User
    participant System
    participant ServiceA
    participant ServiceB

    User->>System: Request
    System->>ServiceA: Process Step 1
    ServiceA->>ServiceB: Delegate
    ServiceB-->>ServiceA: Result
    ServiceA-->>System: Processed
    System-->>User: Response
```

## Customization Guide

Replace these placeholders with your specific actors and actions:

1. **Participants** → Your actual actors/systems (e.g., "Browser", "API Gateway", "Database")
2. **Request** → The initiating action (e.g., "Login Request", "Place Order")
3. **Process Steps** → Specific operations (e.g., "Validate Token", "Check Inventory")
4. **Results** → Return values (e.g., "User Details", "Order Confirmation")

**Arrow Types:**

- `->>` : Synchronous call (waits for response)
- `-->>` : Return/response
- `--)` : Asynchronous call (fire and forget)

### Example: User Authentication Flow

```mermaid
sequenceDiagram
    participant Browser
    participant API Gateway
    participant Auth Service
    participant User DB
    participant Token Service

    Browser->>API Gateway: POST /login<br/>{username, password}
    API Gateway->>Auth Service: Authenticate User
    Auth Service->>User DB: Query User by Username
    User DB-->>Auth Service: User Record
    Auth Service->>Auth Service: Verify Password Hash
    Auth Service->>Token Service: Generate JWT
    Token Service-->>Auth Service: JWT Token
    Auth Service-->>API Gateway: {token, user_id}
    API Gateway-->>Browser: 200 OK<br/>{token, user}
```

## Alternative Format: Flowchart Style

For simpler sequences without multiple participants:

```mermaid
graph TD
    A[User Action<br/>Click Submit] -->|Step 1| B[Validate Form]
    B -->|Valid| C[Send Request]
    B -->|Invalid| D[Show Errors]
    C -->|Step 2| E[Process on Server]
    E -->|Step 3| F[Save to Database]
    F -->|Step 4| G[Send Confirmation]
    G -->|Complete| H[Show Success]
    D -->|Fix| A

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#ff9,stroke:#333
    style H fill:#bfb,stroke:#333,stroke-width:2px
    style D fill:#fbb,stroke:#333
```

## Error Handling Variation

For sequences with error paths:

```mermaid
sequenceDiagram
    participant Client
    participant Server
    participant Database

    Client->>Server: Request
    Server->>Database: Query
    alt Success
        Database-->>Server: Data
        Server-->>Client: 200 OK
    else Database Error
        Database-->>Server: Error
        Server-->>Client: 500 Internal Error
    else Validation Error
        Server-->>Client: 400 Bad Request
    end
```

## Loop Variation

For sequences with repetitive operations:

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Service

    Client->>API: Start Batch Process
    loop For each item
        API->>Service: Process Item
        Service-->>API: Result
    end
    API-->>Client: Batch Complete
```

## Quality Checklist

Before using this diagram, verify:

- [ ] **Participants are clear** - All actors/systems listed
- [ ] **Actions are specific** - Not just "request"/"response"
- [ ] **Order is correct** - Follows actual execution sequence
- [ ] **Return values shown** - Response arrows with data
- [ ] **Error paths included** - What happens on failure
- [ ] **Not too detailed** - High-level steps, not every function call
- [ ] **Labels are descriptive** - Clear action descriptions
- [ ] **Response direction correct** - Always back to caller

## Common Variations

### Variation 1: Simple Request/Response

```mermaid
sequenceDiagram
    participant Client
    participant Server

    Client->>Server: GET /data
    Server-->>Client: 200 OK {data}
```

### Variation 2: Multi-Service Call

```mermaid
sequenceDiagram
    participant Client
    participant Gateway
    participant ServiceA
    participant ServiceB

    Client->>Gateway: Request
    Gateway->>ServiceA: Call A
    ServiceA-->>Gateway: Response A
    Gateway->>ServiceB: Call B
    ServiceB-->>Gateway: Response B
    Gateway-->>Client: Combined Response
```

### Variation 3: Asynchronous Processing

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Queue
    participant Worker

    Client->>API: Submit Job
    API->>Queue: Enqueue
    API-->>Client: 202 Accepted<br/>{job_id}
    Queue--)Worker: Process Job
    Worker--)Client: Webhook Notification
```

### Variation 4: Conditional Flow

```mermaid
sequenceDiagram
    participant User
    participant System
    participant Cache
    participant Database

    User->>System: Get Data
    System->>Cache: Check Cache
    alt Cache Hit
        Cache-->>System: Cached Data
    else Cache Miss
        System->>Database: Query
        Database-->>System: Fresh Data
        System->>Cache: Update Cache
    end
    System-->>User: Return Data
```

## Usage Tips

**When to use this template:**

- User asks "what happens when I do X?"
- Explaining API call flows
- Documenting user workflows
- Showing multi-step processes

**What to emphasize:**

- Actor/participant roles
- Order of operations (critical for sequences)
- Request and response data
- Error handling (alternative paths)
- Asynchronous operations (fire-and-forget)

**What to avoid:**

- Too many participants (>5-6 becomes cluttered)
- Every internal function call (keep high-level)
- Missing return arrows (always show responses)
- Unclear labels (be specific about actions)

## Real-World Example: OAuth2 Authorization Code Flow

```mermaid
sequenceDiagram
    participant User
    participant Client App
    participant Auth Server
    participant Resource Server

    User->>Client App: Click Login
    Client App->>Auth Server: GET /authorize?<br/>client_id, redirect_uri, scope
    Auth Server->>User: Login Page
    User->>Auth Server: Submit Credentials
    Auth Server->>Auth Server: Validate User
    Auth Server-->>Client App: Redirect with<br/>authorization_code
    Client App->>Auth Server: POST /token<br/>code, client_secret
    Auth Server-->>Client App: {access_token, refresh_token}
    Client App->>Resource Server: GET /api/user<br/>Authorization: Bearer token
    Resource Server-->>Client App: User Data
    Client App-->>User: Show Protected Content
```

**Caption:** OAuth2 authorization code flow showing how a client app obtains user authorization. User logs in via auth server, which redirects back with authorization code. Client exchanges code for access token, then uses token to access protected resources. This flow ensures client never sees user credentials.

## Related Templates

- **HOOK_SYSTEM_FLOW.md** - For showing how hooks integrate with sequences
- **DATA_FLOW.md** - For showing data transformations (less actor-focused)
- **COMPONENT_RELATIONSHIPS.md** - For showing static relationships (not sequential)

## Anti-Patterns

**Missing Responses:**

```
Client->>Server: Request
Server->>Database: Query
Database->>Server: Data
Server->>Client: Response
```

(Use `-->>` for responses, not `->>`)

**Better:**

```
Client->>Server: Request
Server->>Database: Query
Database-->>Server: Data
Server-->>Client: Response
```

**Too Generic:**

```
A->>B: Do Something
B-->>A: Result
```

(What is being done? Be specific)

**Better:**

```
Client->>API: POST /orders {items, address}
API-->>Client: 201 Created {order_id}
```

**Too Detailed:**

```
Client->>Server: Request
Server->>Parser: Parse JSON
Parser->>Validator: Validate
Validator->>Controller: Route
Controller->>Service: Process
Service->>Repository: Query
Repository->>Database: SQL
Database->>Repository: Rows
Repository->>Service: Entities
Service->>Controller: Result
Controller->>Serializer: Format
Serializer->>Server: JSON
Server->>Client: Response
```

(Too many internal steps - group into logical phases)

**Better:**

```
Client->>Server: Request
Server->>Server: Validate & Route
Server->>Database: Query
Database-->>Server: Data
Server-->>Client: Response
```

## Advanced Example: Distributed Transaction (Saga Pattern)

```mermaid
sequenceDiagram
    participant Client
    participant Orchestrator
    participant ServiceA
    participant ServiceB
    participant ServiceC

    Client->>Orchestrator: Start Transaction
    Orchestrator->>ServiceA: Execute Step 1
    ServiceA-->>Orchestrator: Success

    Orchestrator->>ServiceB: Execute Step 2
    ServiceB-->>Orchestrator: Success

    Orchestrator->>ServiceC: Execute Step 3
    ServiceC-->>Orchestrator: Failure

    Note over Orchestrator: Compensate!

    Orchestrator->>ServiceB: Compensate Step 2
    ServiceB-->>Orchestrator: Compensated

    Orchestrator->>ServiceA: Compensate Step 1
    ServiceA-->>Orchestrator: Compensated

    Orchestrator-->>Client: Transaction Failed<br/>(All Compensated)
```

**Caption:** Saga pattern for distributed transactions. Orchestrator coordinates steps across services. When ServiceC fails, orchestrator executes compensating transactions in reverse order to rollback changes in ServiceB and ServiceA, ensuring consistency without distributed locks.

## Timing and Performance

For showing performance-critical sequences with timing:

```mermaid
sequenceDiagram
    participant Client
    participant CDN
    participant API
    participant DB

    Client->>CDN: GET /page
    Note over CDN: 50ms
    CDN-->>Client: HTML

    Client->>API: GET /data
    Note over API,DB: 200ms
    API->>DB: Query
    DB-->>API: Result
    API-->>Client: JSON

    Note over Client: Total: 250ms
```

**Caption:** Request timing breakdown showing CDN serving static content in 50ms, while API + DB query takes 200ms for dynamic data. Total page load time is 250ms.

## Complex Example: E-commerce Checkout Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Gateway
    participant Cart
    participant Inventory
    participant Payment
    participant Order
    participant Notification

    User->>Frontend: Click Checkout
    Frontend->>Gateway: POST /checkout
    Gateway->>Cart: Get Cart Items
    Cart-->>Gateway: Items

    Gateway->>Inventory: Reserve Items
    alt Items Available
        Inventory-->>Gateway: Reserved
        Gateway->>Payment: Process Payment
        alt Payment Success
            Payment-->>Gateway: Charged
            Gateway->>Order: Create Order
            Order-->>Gateway: Order Created
            Gateway->>Inventory: Confirm Reservation
            Gateway->>Notification: Send Confirmation Email
            Notification--)User: Email
            Gateway-->>Frontend: 200 OK {order_id}
            Frontend-->>User: Order Confirmation
        else Payment Failed
            Payment-->>Gateway: Declined
            Gateway->>Inventory: Release Reservation
            Gateway-->>Frontend: 402 Payment Required
            Frontend-->>User: Payment Error
        end
    else Items Unavailable
        Inventory-->>Gateway: Out of Stock
        Gateway-->>Frontend: 409 Conflict
        Frontend-->>User: Items Unavailable
    end
```

**Caption:** E-commerce checkout flow showing cart validation, inventory reservation, payment processing, and order creation. Includes error handling for out-of-stock items and payment failures, with compensation logic to release inventory reservations on failure.
