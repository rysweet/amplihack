# Architecting Solutions

System design methodology for creating well-structured, maintainable software architectures.

## When to Use

- Starting a new project or major feature
- Redesigning an existing system
- Adding significant new functionality
- Facing complex integration requirements
- System is becoming difficult to maintain or extend

## The Analysis → Design → Validation Cycle

### Phase 1: Analysis (Understand)

**Goal**: Deeply understand the problem before proposing solutions.

```
1. REQUIREMENTS GATHERING
   - What problem are we solving?
   - Who are the users/consumers?
   - What are the constraints (time, budget, team)?
   - What are the non-functional requirements?

2. CONTEXT MAPPING
   - What systems already exist?
   - What are the integration points?
   - What data flows in and out?
   - What are the dependencies?

3. CONSTRAINT IDENTIFICATION
   - Performance requirements (latency, throughput)
   - Scale requirements (users, data volume)
   - Security requirements
   - Compliance requirements
   - Team capabilities
```

### Phase 2: Design (Propose)

**Goal**: Create a clear, implementable design.

```
1. BOUNDARY IDENTIFICATION
   - Draw system boundaries
   - Identify modules/services
   - Define clear interfaces
   - Minimize coupling between boundaries

2. COMPONENT DESIGN
   - Single responsibility per component
   - Clear input/output contracts
   - Error handling strategy
   - State management approach

3. INTEGRATION DESIGN
   - API contracts
   - Event/message formats
   - Data synchronization strategy
   - Failure handling
```

### Phase 3: Validation (Verify)

**Goal**: Ensure the design meets requirements before implementation.

```
1. REQUIREMENTS TRACEABILITY
   - Does each requirement map to a component?
   - Are all constraints addressed?
   - Are non-functional requirements achievable?

2. RISK ASSESSMENT
   - What are the technical risks?
   - What are the integration risks?
   - What are the performance risks?
   - How do we mitigate each?

3. IMPLEMENTATION FEASIBILITY
   - Can the team build this?
   - Do we have the necessary skills?
   - Is the timeline realistic?
   - What are the dependencies?
```

## Module Specification Template

```markdown
# Module: [Name]

## Purpose
[Single sentence describing what this module does]

## Responsibility
[One clear responsibility - if you need "and", split the module]

## Public Interface

### Functions/Methods
- `function_name(params) -> return_type`: Description
- `another_function(params) -> return_type`: Description

### Events Emitted
- `event.name`: When triggered, payload structure

### Events Consumed
- `event.name`: How handled, expectations

## Dependencies
- [Module/Service]: Why needed
- [External API]: Purpose

## Data Owned
- [Data entity]: Description, lifecycle

## Constraints
- Performance: [expectations]
- Scale: [limits]
- Security: [requirements]

## Error Handling
- [Error type]: How handled, recovery strategy

## Configuration
- `CONFIG_KEY`: Purpose, default value
```

## The 5-Question Decision Framework

Before any architectural decision, answer these questions:

### 1. What problem does this solve?

```
- Be specific about the problem
- Quantify if possible (latency, errors, development time)
- Ensure it's a real problem, not hypothetical
```

### 2. What are the alternatives?

```
- List at least 3 alternatives
- Include "do nothing" as an option
- Consider build vs. buy vs. adapt
```

### 3. What are the trade-offs?

```
For each alternative, assess:
- Complexity (implementation, operation)
- Cost (development, maintenance, infrastructure)
- Risk (technical, schedule, adoption)
- Flexibility (future changes, reversibility)
```

### 4. What's the blast radius?

```
- How many components are affected?
- How many teams are involved?
- What's the rollback strategy?
- What happens if it fails?
```

### 5. Is this reversible?

```
- Can we undo this decision?
- What's the cost of reversal?
- Should we timebox and evaluate?
- Can we start smaller?
```

## Boundary Identification

### Signs You Need a Boundary

```
- Different rates of change
- Different scaling requirements
- Different security requirements
- Different team ownership
- Different deployment schedules
- Different technology stacks
```

### Boundary Types

```
MODULE BOUNDARY (same process)
├── Shared memory, direct calls
├── Low overhead, high coupling risk
└── Use for: cohesive functionality

SERVICE BOUNDARY (different process)
├── Network calls, explicit contracts
├── Higher overhead, loose coupling
└── Use for: independent scaling/deployment

SYSTEM BOUNDARY (different organization)
├── APIs, contracts, SLAs
├── Highest overhead, maximum isolation
└── Use for: external integrations
```

### Boundary Checklist

```
[ ] Clear single responsibility
[ ] Well-defined public interface
[ ] Minimal dependencies on other boundaries
[ ] Own data/state (no shared databases)
[ ] Independent deployability
[ ] Independent testability
[ ] Clear error contracts
[ ] Documented integration points
```

## Architecture Patterns Quick Reference

### Layered Architecture
```
[Presentation] → [Business Logic] → [Data Access] → [Database]

Use when:
- Traditional CRUD applications
- Clear separation of concerns needed
- Team organized by technical skill
```

### Modular Monolith
```
[Module A] ←→ [Module B] ←→ [Module C]
     ↓              ↓              ↓
[         Shared Infrastructure         ]

Use when:
- Starting new project
- Team is small
- Domain boundaries unclear
- Want microservices benefits without complexity
```

### Event-Driven
```
[Producer] → [Event Bus] → [Consumer A]
                        → [Consumer B]

Use when:
- Loose coupling critical
- Async processing acceptable
- Multiple consumers for same events
- Audit trail needed
```

### Pipeline/Stages
```
[Stage 1] → [Stage 2] → [Stage 3] → [Output]

Use when:
- Data transformation workflows
- Each stage is independent
- Stages may need different scaling
```

## Anti-Patterns to Avoid

### Distributed Monolith
```
Problem: Services with tight coupling
Signs: Deploy together, fail together, change together
Fix: Merge back into monolith or properly decouple
```

### Premature Optimization
```
Problem: Optimizing before measuring
Signs: Complex caching, async everywhere, microservices day 1
Fix: Start simple, measure, optimize where needed
```

### Resume-Driven Development
```
Problem: Choosing tech for learning, not solving
Signs: Latest framework, unnecessary complexity
Fix: Boring technology that solves the problem
```

### Analysis Paralysis
```
Problem: Never deciding, always analyzing
Signs: Weeks of design, no code
Fix: Time-box decisions, build prototypes
```

## Deliverables Checklist

After architecting, you should have:

```
[ ] Problem statement document
[ ] System context diagram
[ ] Component/module diagram
[ ] Module specifications for each component
[ ] Interface contracts (API specs)
[ ] Data model overview
[ ] Decision log (what and why)
[ ] Risk assessment
[ ] Implementation roadmap
[ ] Success metrics
```

## Quick Start: Architecture Session

```bash
# 1. Gather context (30 min)
- Review requirements
- Map existing systems
- List constraints

# 2. Whiteboard session (60 min)
- Draw boundaries
- Identify components
- Define interfaces

# 3. Validate design (30 min)
- Walk through use cases
- Check requirements coverage
- Identify risks

# 4. Document (60 min)
- Create module specs
- Document decisions
- Plan implementation
```
