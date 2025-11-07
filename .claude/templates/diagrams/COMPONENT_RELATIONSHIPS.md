# Component Relationships Template

## When to Use This Template

Use this template when investigating or explaining:

- System architecture and module interactions
- Microservice dependencies
- Component communication patterns
- Class/object relationships
- Service integration architecture
- Plugin and extension systems

**Trigger Conditions:**

- System has multiple interacting components
- Need to show dependencies between modules
- Explaining how services communicate
- Documenting integration points

**Examples:**

- Microservice architecture diagrams
- Module dependency graphs
- Plugin system architectures
- Frontend/backend integration
- Service mesh topologies
- Class hierarchy and interactions

## Template Diagram

```mermaid
graph TD
    A[Component A<br/>Primary Service] -->|Uses| B[Component B<br/>Supporting Service]
    A -->|Depends On| C[Component C<br/>Data Layer]
    B -->|Calls| D[Component D<br/>External API]
    C -->|Stores| E[Component E<br/>Database]
    D -->|Returns| B
    E -->|Queries| C

    F[Component F<br/>Monitoring] -.->|Observes| A
    F -.->|Observes| B
    F -.->|Observes| C

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333
    style C fill:#bbf,stroke:#333
    style D fill:#ddd,stroke:#333
    style E fill:#bfb,stroke:#333
    style F fill:#ff9,stroke:#333
```

## Customization Guide

Replace these placeholders with your specific components:

1. **Component A** → Your primary component (e.g., "API Gateway", "Frontend App")
2. **Component B** → Supporting component (e.g., "Auth Service", "Business Logic")
3. **Component C** → Data layer (e.g., "Data Access Layer", "Repository")
4. **Component D** → External component (e.g., "Third-party API", "Payment Gateway")
5. **Component E** → Storage component (e.g., "PostgreSQL", "Redis Cache")
6. **Component F** → Cross-cutting concern (e.g., "Logging", "Monitoring")

**Edge Labels:** Use specific verbs:

- "Uses", "Calls", "Depends On", "Queries", "Publishes", "Subscribes", "Stores", "Retrieves"

**Optional Components:**

- Cross-cutting concerns (monitoring, logging) - use dotted lines
- External systems (grayed out style)

### Example: Microservice Architecture

```mermaid
graph TD
    A[API Gateway<br/>Entry Point] -->|Routes| B[User Service<br/>User Management]
    A -->|Routes| C[Order Service<br/>Order Processing]
    A -->|Routes| D[Product Service<br/>Catalog Management]

    B -->|Queries| E[User DB<br/>PostgreSQL]
    C -->|Queries| F[Order DB<br/>PostgreSQL]
    D -->|Queries| G[Product DB<br/>PostgreSQL]

    C -->|Calls| B
    C -->|Calls| D

    H[Message Queue<br/>RabbitMQ] -.->|Publishes| C
    B -.->|Subscribes| H
    D -.->|Subscribes| H

    I[Service Registry<br/>Consul] -.->|Discovers| A

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333
    style C fill:#bbf,stroke:#333
    style D fill:#bbf,stroke:#333
    style E fill:#bfb,stroke:#333
    style F fill:#bfb,stroke:#333
    style G fill:#bfb,stroke:#333
    style H fill:#ff9,stroke:#333
    style I fill:#ddd,stroke:#333
```

## Layered Architecture Variation

For systems with clear architectural layers:

```mermaid
graph TD
    subgraph Presentation Layer
    A[Web UI]
    B[Mobile App]
    end

    subgraph Business Logic Layer
    C[Service A]
    D[Service B]
    E[Service C]
    end

    subgraph Data Access Layer
    F[Repository A]
    G[Repository B]
    end

    subgraph Persistence Layer
    H[Database A]
    I[Database B]
    J[Cache]
    end

    A -->|Calls| C
    A -->|Calls| D
    B -->|Calls| C
    B -->|Calls| E

    C -->|Uses| F
    D -->|Uses| F
    D -->|Uses| G
    E -->|Uses| G

    F -->|Queries| H
    F -->|Caches| J
    G -->|Queries| I
    G -->|Caches| J

    style A fill:#f9f,stroke:#333
    style B fill:#f9f,stroke:#333
    style C fill:#bbf,stroke:#333
    style D fill:#bbf,stroke:#333
    style E fill:#bbf,stroke:#333
    style H fill:#bfb,stroke:#333
    style I fill:#bfb,stroke:#333
    style J fill:#ff9,stroke:#333
```

## Hub-and-Spoke Variation

For systems with a central coordinator:

```mermaid
graph TD
    A[Central Hub<br/>Orchestrator] -->|Coordinates| B[Service 1]
    A -->|Coordinates| C[Service 2]
    A -->|Coordinates| D[Service 3]
    A -->|Coordinates| E[Service 4]

    B -->|Reports| A
    C -->|Reports| A
    D -->|Reports| A
    E -->|Reports| A

    F[Configuration<br/>Central Config] -.->|Configures| A

    style A fill:#f9f,stroke:#333,stroke-width:3px
    style B fill:#bbf,stroke:#333
    style C fill:#bbf,stroke:#333
    style D fill:#bbf,stroke:#333
    style E fill:#bbf,stroke:#333
    style F fill:#ff9,stroke:#333
```

## Quality Checklist

Before using this diagram, verify:

- [ ] **All major components shown** - No critical pieces missing
- [ ] **Relationships are clear** - Edge labels describe interactions
- [ ] **Direction is correct** - Arrows show dependency/call direction
- [ ] **External systems distinguished** - Different styling for third-party
- [ ] **Layers are logical** - If using layers, they're correctly organized
- [ ] **Cross-cutting concerns shown** - Monitoring, logging, etc. (dotted lines)
- [ ] **Not too cluttered** - If >15 components, consider grouping
- [ ] **Labels match codebase** - Use actual component names

## Common Variations

### Variation 1: Simple Client-Server

```mermaid
graph LR
    A[Client<br/>Frontend] -->|HTTP| B[Server<br/>Backend]
    B -->|Queries| C[Database]

    style A fill:#f9f,stroke:#333
    style B fill:#bbf,stroke:#333
    style C fill:#bfb,stroke:#333
```

### Variation 2: Event-Driven Architecture

```mermaid
graph TD
    A[Service A] -->|Publishes| E[Event Bus]
    B[Service B] -->|Publishes| E
    C[Service C] -->|Publishes| E

    E -->|Subscribes| F[Service D]
    E -->|Subscribes| G[Service E]
    E -->|Subscribes| H[Service F]

    style E fill:#ff9,stroke:#333,stroke-width:2px
    style A fill:#bbf,stroke:#333
    style B fill:#bbf,stroke:#333
    style C fill:#bbf,stroke:#333
    style F fill:#bfb,stroke:#333
    style G fill:#bfb,stroke:#333
    style H fill:#bfb,stroke:#333
```

### Variation 3: Plugin Architecture

```mermaid
graph TD
    A[Core System<br/>Plugin Host] -->|Loads| B[Plugin A]
    A -->|Loads| C[Plugin B]
    A -->|Loads| D[Plugin C]

    B -.->|Extends| A
    C -.->|Extends| A
    D -.->|Extends| A

    E[Plugin Registry] -.->|Discovers| A

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333
    style C fill:#bbf,stroke:#333
    style D fill:#bbf,stroke:#333
    style E fill:#ff9,stroke:#333
```

### Variation 4: Dependency Injection

```mermaid
graph TD
    A[Container<br/>DI Container] -->|Injects| B[Service A]
    A -->|Injects| C[Service B]
    A -->|Injects| D[Service C]

    B -->|Depends On| E[Interface X]
    C -->|Depends On| F[Interface Y]
    D -->|Depends On| E

    A -.->|Resolves| E
    A -.->|Resolves| F

    style A fill:#ff9,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333
    style C fill:#bbf,stroke:#333
    style D fill:#bbf,stroke:#333
```

## Usage Tips

**When to use this template:**

- User asks "how do these components interact?"
- Explaining system architecture
- Documenting dependencies
- Showing integration points

**What to emphasize:**

- Primary components and their roles
- Critical dependencies (who depends on whom)
- External integrations (third-party services)
- Communication patterns (sync/async, pub/sub)
- Cross-cutting concerns (monitoring, security)

**What to avoid:**

- Internal class details (keep component-level)
- Every possible relationship (show critical paths)
- Too many layers (simplify if possible)
- Unclear dependency direction (always explicit arrows)

## Real-World Example: Claude Code Agent System

```mermaid
graph TD
    A[Claude Code<br/>Main CLI] -->|Invokes| B[UltraThink<br/>Orchestrator]
    B -->|Delegates| C[Architect Agent<br/>Design]
    B -->|Delegates| D[Builder Agent<br/>Implementation]
    B -->|Delegates| E[Reviewer Agent<br/>Quality Check]

    A -->|Reads| F[Workflow Files<br/>.claude/workflow/]
    A -->|Reads| G[Agent Definitions<br/>.claude/agents/]
    A -->|Executes| H[Hooks<br/>.claude/tools/hooks/]

    H -->|Loads| I[User Preferences<br/>USER_PREFERENCES.md]
    I -->|Injects| A

    C -->|Produces| J[Architecture Spec]
    J -->|Input to| D
    D -->|Produces| K[Implementation]
    K -->|Input to| E

    L[GitHub API] -.->|Used by| A
    M[Git Operations] -.->|Used by| A

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333
    style C fill:#bbf,stroke:#333
    style D fill:#bbf,stroke:#333
    style E fill:#bbf,stroke:#333
    style F fill:#bfb,stroke:#333
    style G fill:#bfb,stroke:#333
    style I fill:#bfb,stroke:#333
    style L fill:#ddd,stroke:#333
    style M fill:#ddd,stroke:#333
```

**Caption:** Claude Code's agent system showing how the main CLI orchestrates specialized agents (architect, builder, reviewer) using workflow definitions and agent files. Hooks load user preferences at runtime and inject them into the session. Agents follow a pipeline: architect designs, builder implements, reviewer validates. External integrations with GitHub API and Git provide version control capabilities.

## Related Templates

- **EXECUTION_SEQUENCE.md** - For showing detailed interaction sequences
- **DATA_FLOW.md** - For showing data movement between components
- **HOOK_SYSTEM_FLOW.md** - For showing hook integration with components

## Anti-Patterns

**Too Shallow:**

```
Frontend → Backend → Database
```

(Not helpful - too generic, no detail about components)

**Too Deep:**

```
UserController → UserService → UserValidator → UserMapper → UserRepository → DatabaseConnection → PostgreSQL → Disk
```

(Too granular - combine related components)

**Unclear Direction:**

```
A --- B --- C --- D
```

(Use arrows to show dependency/call direction)

**Better:**

```
A -->|Calls| B -->|Uses| C -->|Queries| D
```

**No Context:**

```
ServiceA → ServiceB → ServiceC
```

(What do these services do? Add descriptions)

**Better:**

```
ServiceA<br/>User Auth → ServiceB<br/>Order Processing → ServiceC<br/>Payment Gateway
```

## Advanced Example: Multi-Tier Web Application

```mermaid
graph TD
    subgraph Client Tier
    A[Browser]
    B[Mobile App]
    end

    subgraph Web Tier
    C[Load Balancer<br/>Nginx]
    D[Web Server 1<br/>Node.js]
    E[Web Server 2<br/>Node.js]
    end

    subgraph Application Tier
    F[API Gateway]
    G[Auth Service<br/>OAuth2]
    H[Business Logic<br/>Microservices]
    I[Background Jobs<br/>Workers]
    end

    subgraph Data Tier
    J[Primary DB<br/>PostgreSQL]
    K[Read Replica<br/>PostgreSQL]
    L[Cache<br/>Redis]
    M[Message Queue<br/>RabbitMQ]
    end

    A -->|HTTPS| C
    B -->|HTTPS| C
    C -->|Proxy| D
    C -->|Proxy| E

    D -->|REST| F
    E -->|REST| F

    F -->|Authenticate| G
    F -->|Process| H
    H -->|Enqueue| M
    M -->|Consume| I

    H -->|Write| J
    H -->|Read| K
    H -->|Cache| L
    I -->|Write| J

    J -.->|Replicate| K

    style C fill:#f9f,stroke:#333,stroke-width:2px
    style F fill:#bbf,stroke:#333
    style G fill:#bbf,stroke:#333
    style H fill:#bbf,stroke:#333
    style J fill:#bfb,stroke:#333
    style L fill:#ff9,stroke:#333
    style M fill:#ff9,stroke:#333
```

**Caption:** Multi-tier web application showing client tier (browser/mobile), web tier (load balancer + servers), application tier (API gateway, auth, business logic, workers), and data tier (primary DB, read replica, cache, message queue). Load balancer distributes traffic, API gateway routes requests, business logic writes to primary DB and reads from replica, with Redis caching and RabbitMQ for async jobs.

## Circular Dependency Detection

For identifying problematic circular dependencies:

```mermaid
graph TD
    A[Service A] -->|Depends| B[Service B]
    B -->|Depends| C[Service C]
    C -->|Depends| A

    style A fill:#fbb,stroke:#333,stroke-width:2px
    style B fill:#fbb,stroke:#333,stroke-width:2px
    style C fill:#fbb,stroke:#333,stroke-width:2px
```

**Caption:** ANTI-PATTERN - Circular dependency detected. Services A, B, C form a dependency cycle that should be broken by introducing an interface or refactoring responsibilities.
