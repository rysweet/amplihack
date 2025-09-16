# Implementation Philosophy Requirements

## Purpose
Ensure the system embodies and enforces the core implementation philosophy of ruthless simplicity, emergent architecture, and pragmatic development practices throughout all components and workflows.

## Core Philosophy Requirements

### Ruthless Simplicity Enforcement

#### FR-PH-001: Simplicity Detection and Enforcement
- MUST detect and reject unnecessary abstractions during code review
- MUST identify over-engineering patterns automatically
- MUST flag generic "future-proof" code that solves non-existent problems
- MUST enforce that every layer of abstraction justifies its existence
- MUST prefer direct implementation over wrapper patterns unless justified

#### FR-PH-002: Zero-BS Principle
- MUST detect and reject code containing NotImplementedError (except in abstract base classes)
- MUST identify and flag TODO comments without accompanying working implementation
- MUST reject placeholder/mock/fake functions that don't work
- MUST enforce that every function either works completely or doesn't exist
- MUST distinguish legitimate framework patterns and abstract base classes from stubs

#### FR-PH-003: Present-Moment Focus
- MUST resist building for hypothetical future requirements
- MUST handle what's needed now rather than anticipating scenarios
- MUST question additions that don't serve current needs
- MUST track and flag premature optimization attempts
- MUST enforce YAGNI (You Aren't Gonna Need It) principle

### Architectural Philosophy

#### FR-PH-004: Trust in Emergence
- MUST build complex behaviors from simple, composable components
- MUST avoid central orchestration in favor of emergent patterns
- MUST prefer message passing over shared state
- MUST allow patterns to emerge from usage rather than being prescribed
- MUST resist adding coordination layers until proven necessary

#### FR-PH-005: Wabi-Sabi and Occam's Razor
- MUST embrace simplicity and the essential in all designs
- MUST ensure each line of code serves a clear purpose
- MUST make solutions as simple as possible, but no simpler
- MUST value clarity over cleverness in implementation
- MUST favor readable code over premature optimization

### Development Approach

#### FR-PH-006: Analysis-First Development
- MUST enforce analysis phase before implementation for complex tasks
- MUST generate structured analysis with problem decomposition
- MUST document 2-3 approach options with trade-offs
- MUST refuse to implement without completed analysis
- MUST track whether analysis was performed for each task

#### FR-PH-007: Vertical Slice Implementation
- MUST implement complete end-to-end features before horizontal expansion
- MUST validate data flow through all layers before adding features
- MUST prioritize working vertical slices over partial implementations
- MUST get core user journeys working first
- MUST resist adding features until core flows are solid

#### FR-PH-008: 80/20 Principle Application
- MUST focus on high-value, low-effort features first
- MUST prioritize one working feature over multiple partial features
- MUST validate with real usage before enhancing
- MUST track effort vs value for feature decisions
- MUST defer complex edge cases until core cases work

### Library vs Custom Code Decisions

#### FR-PH-009: Library Decision Framework
- MUST track library vs custom code decisions with rationale
- MUST detect when fighting against library constraints
- MUST flag excessive monkey-patching or wrapper code
- MUST evaluate library alignment with actual needs
- MUST identify when simple custom code could replace complex libraries

#### FR-PH-010: Library Evolution Management
- MUST support evolution from custom to library as needs grow
- MUST support evolution from library to custom when hitting limits
- MUST minimize library integration points for easy replacement
- MUST document library assumptions and constraints
- MUST track library misalignment indicators

### Configuration Management

#### FR-PH-011: Single Source of Truth
- MUST maintain single authoritative location for each configuration
- MUST detect and flag duplicate configuration values
- MUST read configuration from authoritative sources at runtime
- MUST reject hardcoded values that duplicate configuration
- MUST derive all configuration from a single authoritative project configuration file when possible

#### FR-PH-012: Configuration Hierarchy
- MUST establish clear configuration precedence with project configuration taking priority over tool-specific settings
- MUST validate configuration consistency across files
- MUST warn when configuration drift is detected
- MUST provide configuration validation tools
- MUST document configuration dependencies

## Quality Enforcement Requirements

### Code Quality Philosophy

#### FR-PH-013: Simplicity Metrics
- MUST measure abstraction depth in code
- MUST track cyclomatic complexity
- MUST identify simplification opportunities
- MUST report unnecessary complexity trends
- MUST enforce complexity thresholds

#### FR-PH-014: Working Code Validation
- MUST validate all code paths are implemented
- MUST detect incomplete implementations
- MUST enforce test coverage for claimed functionality
- MUST reject code that doesn't do what it claims
- MUST validate error handling is complete

### Decision Documentation

#### FR-PH-015: Decision Tracking
- MUST document significant architectural decisions
- MUST track rationale for complexity when added
- MUST record why simpler approaches were rejected
- MUST maintain decision history for context
- MUST link decisions to requirements

#### FR-PH-016: Discovery Documentation
- MUST prompt for DISCOVERIES.md updates when problems are solved
- MUST search DISCOVERIES.md before attempting complex solutions
- MUST format discoveries with Date, Issue, Root Cause, Solution, Prevention
- MUST detect when similar problems recur without consulting discoveries
- MUST track discovery consultation rates

## Areas of Managed Complexity

### FR-PH-017: Justified Complexity Areas
- MUST embrace necessary complexity for security fundamentals
- MUST ensure data integrity even if it adds complexity
- MUST prioritize core user experience over simplicity
- MUST make errors obvious and diagnosable
- MUST document why complexity is justified in these areas

### FR-PH-018: Aggressive Simplification Areas
- MUST minimize internal abstraction layers
- MUST resist generic solutions for specific problems
- MUST handle common cases simply before edge cases
- MUST use only needed framework features
- MUST keep state management explicit and simple

## Philosophy Validation Requirements

### FR-PH-019: Continuous Philosophy Enforcement
- MUST validate all code against philosophy principles
- MUST run philosophy checks in CI/CD pipeline
- MUST report philosophy violations in code review
- MUST track philosophy compliance metrics
- MUST educate on philosophy through tooling

### FR-PH-020: Philosophy Evolution
- MUST track philosophy effectiveness metrics
- MUST identify where philosophy helps or hinders
- MUST support philosophy refinement based on experience
- MUST maintain philosophy documentation current
- MUST ensure philosophy serves practical goals