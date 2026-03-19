# Code Atlas Diagram Examples

Per-layer Mermaid and DOT examples with recommended diagram types.

## runtime-topology

**Recommended**: DOT digraph with subgraph clusters (handles complex multi-service layouts).

### Graphviz DOT

```dot
digraph runtime {
    rankdir=LR
    node [shape=box style=filled]

    subgraph cluster_frontend {
        label="Frontend"
        web [label="web-app\n:3000" fillcolor="#AED6F1"]
    }
    subgraph cluster_backend {
        label="Backend"
        api [label="api-service\n:8080" fillcolor="#A9DFBF"]
        auth [label="auth-service\n:8081" fillcolor="#A9DFBF"]
    }
    subgraph cluster_data {
        label="Data"
        pg [label="PostgreSQL\n:5432" shape=cylinder fillcolor="#FAD7A0"]
        redis [label="Redis\n:6379" shape=cylinder fillcolor="#FAD7A0"]
    }

    web -> api [label="HTTP/REST"]
    api -> auth [label="gRPC"]
    api -> pg [label="SQL"]
    api -> redis [label="cache"]
    auth -> pg [label="SQL"]
}
```

### Mermaid

```mermaid
flowchart LR
    subgraph frontend["Frontend"]
        web["web-app :3000"]
    end
    subgraph backend["Backend"]
        api["api-service :8080"]
        auth["auth-service :8081"]
    end
    subgraph data["Data"]
        pg[("PostgreSQL :5432")]
        redis[("Redis :6379")]
    end

    web -->|HTTP/REST| api
    api -->|gRPC| auth
    api -->|SQL| pg
    api -->|cache| redis
    auth -->|SQL| pg
```

---

## compile-deps

**Recommended**: DOT digraph (handles large dependency trees better than Mermaid).

### Mermaid

```mermaid
flowchart TD
    subgraph services["Services"]
        api["api-service"]
        auth["auth-service"]
        worker["worker"]
    end
    subgraph shared["Shared Libraries"]
        models["@org/models"]
        utils["@org/utils"]
        proto["@org/proto"]
    end
    subgraph external["External"]
        express["express ^4.18"]
        grpc["@grpc/grpc-js ^1.9"]
        pg["pg ^8.11"]
    end

    api --> models
    api --> proto
    api --> express
    api --> pg
    auth --> models
    auth --> proto
    auth --> grpc
    worker --> models
    worker --> utils
    models --> utils
```

### Inventory Table (required companion)

| Package       | Version   | Consumers                         | Direct? | License    |
| ------------- | --------- | --------------------------------- | ------- | ---------- |
| express       | ^4.18     | api-service                       | Yes     | MIT        |
| @grpc/grpc-js | ^1.9      | auth-service                      | Yes     | Apache-2.0 |
| pg            | ^8.11     | api-service                       | Yes     | MIT        |
| @org/models   | workspace | api-service, auth-service, worker | Yes     | Internal   |

---

## api-contracts

**Recommended**: Mermaid `flowchart TD` (route hierarchies render cleanly).

### Mermaid

```mermaid
flowchart TD
    subgraph public["Public Routes"]
        POST_login["POST /api/auth/login"]
        POST_register["POST /api/auth/register"]
        GET_health["GET /health"]
    end
    subgraph protected["Protected Routes (JWT Required)"]
        GET_users["GET /api/users"]
        GET_user["GET /api/users/:id"]
        PUT_user["PUT /api/users/:id"]
        DELETE_user["DELETE /api/users/:id"]
        POST_orders["POST /api/orders"]
        GET_orders["GET /api/orders"]
    end

    subgraph middleware["Middleware Chain"]
        cors["CORS"]
        ratelimit["RateLimit"]
        jwt["JWTValidate"]
        audit["AuditLog"]
    end

    POST_login --> UserController
    GET_users --> jwt --> UserController
    POST_orders --> jwt --> ratelimit --> OrderController
```

### Inventory Table (required companion)

| Method | Path            | Handler                | Auth | DTO In             | DTO Out          | Middleware           |
| ------ | --------------- | ---------------------- | ---- | ------------------ | ---------------- | -------------------- |
| POST   | /api/auth/login | AuthController.login   | None | LoginRequest       | TokenResponse    | cors                 |
| GET    | /api/users      | UserController.list    | JWT  | --                 | UserListResponse | cors, jwt, audit     |
| POST   | /api/orders     | OrderController.create | JWT  | CreateOrderRequest | OrderResponse    | cors, jwt, ratelimit |

---

## data-flow

**Recommended**: Mermaid `flowchart LR` (left-to-right matches request flow intuition).

### Mermaid

```mermaid
flowchart LR
    req["HTTP Request\nCreateOrderRequest"] --> validate["Validate DTO"]
    validate -->|valid| enrich["Enrich with\nuser context"]
    validate -->|invalid| err["400 Bad Request"]
    enrich --> business["Apply business rules\n(pricing, inventory)"]
    business --> db["INSERT orders\n+ INSERT order_items"]
    business --> event["Publish OrderCreated\nevent to Kafka"]
    db --> resp["OrderResponse DTO"]
    event --> worker["Worker: send\nconfirmation email"]
    resp --> client["HTTP 201 Response"]
```

---

## service-components

**Recommended**: Mermaid `graph TD` (one diagram per service).

### Mermaid (per service)

```mermaid
graph TD
    subgraph api_service["api-service"]
        handler["handlers/"]
        service["services/"]
        repo["repositories/"]
        dto["dto/"]
        mid["middleware/"]
    end

    handler -->|"uses"| service
    handler -->|"reads/writes"| dto
    service -->|"calls"| repo
    mid -->|"wraps"| handler

    subgraph exports["Key Exported Symbols"]
        OrderHandler["OrderHandler"]
        UserService["UserService"]
        PostgresRepo["PostgresRepository"]
    end

    handler --> OrderHandler
    service --> UserService
    repo --> PostgresRepo
```

---

## user-journeys

**Recommended**: Mermaid `sequenceDiagram` (natural fit for request flow tracing).

### Mermaid

```mermaid
sequenceDiagram
    actor User
    participant Web as Web App
    participant API as api-service
    participant Auth as auth-service
    participant DB as PostgreSQL
    participant Queue as Kafka

    User->>Web: Fill registration form
    Web->>API: POST /api/auth/register {email, password, name}
    API->>API: Validate RegisterRequest DTO
    API->>Auth: gRPC HashPassword(password)
    Auth-->>API: hashedPassword
    API->>DB: INSERT users (email, hashedPassword, name)
    DB-->>API: userId
    API->>Queue: Publish UserRegistered {userId, email}
    Queue-->>API: ack
    API-->>Web: 201 {userId, email}
    Web-->>User: "Check email for verification"
    Note over Queue: Worker picks up UserRegistered
    Queue->>Worker: UserRegistered event
    Worker->>EmailSvc: Send verification email
```

---

## ast-lsp-bindings

**Recommended**: Mermaid `flowchart LR` or DOT digraph (for symbol reference graphs).

### Dead Code Report (table format)

```markdown
# Dead Code Report

**Mode:** static-approximation
**Date:** 2026-03-16

| Symbol                        | File                      | Line | Last Referenced         | Notes                        |
| ----------------------------- | ------------------------- | ---- | ----------------------- | ---------------------------- |
| `LegacyUserExporter.export()` | `src/exporters/legacy.ts` | 45   | Never (static analysis) | Candidate for removal        |
| `calculateTaxV1()`            | `src/billing/tax.go`      | 102  | Never (static analysis) | Superseded by calculateTaxV2 |
```

### Interface Mismatch Report (table format)

```markdown
# Interface Mismatch Report

**Mode:** lsp-assisted
**Date:** 2026-03-16

| Symbol                | Definition                                       | Call Site                      | Mismatch                        |
| --------------------- | ------------------------------------------------ | ------------------------------ | ------------------------------- |
| `OrderService.create` | `(ctx, dto: CreateOrderRequest): Promise<Order>` | `src/api/handlers/order.ts:67` | Called with 1 arg (missing ctx) |
```

---

## repo-surface

**Recommended**: Mermaid `flowchart TD` (directory tree overview).

Typically the simplest layer -- a top-level directory tree diagram showing project structure,
build entry points, and configuration files. Not every file is shown; group by directory.

---

## Language-Agnostic Discovery Commands

These commands are used across layers to explore any codebase:

### Go

```bash
find . -name "main.go" | head -10
grep -r "\.Get\|\.Post\|\.Handle" --include="*.go" . | grep -v _test.go
grep -r "type.*struct {" --include="*.go" . | grep -i "request\|response\|dto"
```

### TypeScript / Node.js

```bash
cat package.json | jq '.main, .scripts.start'
grep -r "\.get\|\.post\|router\.\|@Controller" --include="*.ts" src/ | head -30
find . -name "*.dto.ts" -o -name "*.schema.ts" | grep -v node_modules
```

### Python (FastAPI, Django, Flask)

```bash
find . -name "app.py" -o -name "main.py" -o -name "wsgi.py" -o -name "asgi.py"
grep -r "@app\.\|@router\." --include="*.py" . | grep -v test
grep -r "class.*BaseModel\|class.*Serializer" --include="*.py" .
```

### .NET (ASP.NET Core)

```bash
find . -name "Program.cs" -o -name "Startup.cs"
find . -name "*Controller.cs" | xargs grep "\[Http\|MapGet\|MapPost"
find . -name "*Dto.cs" -o -name "*Request.cs" -o -name "*Response.cs"
```

### Rust (Axum, Actix-web)

```bash
find . -name "main.rs" | head -5
grep -r "Router::new\|\.route\|get!\|post!" --include="*.rs" src/
grep -r "#\[derive.*Deserialize\|#\[derive.*Serialize\]" --include="*.rs" src/
```
