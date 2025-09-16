# AI Context and Guidelines Requirements

## Purpose
Maintain comprehensive AI context files and enforce development guidelines that ensure AI assistants understand project philosophy, patterns, and requirements for effective collaboration.

## AI Context Management Requirements

### Context File Generation

#### FR-AC-001: AI Context File Building
- MUST generate comprehensive AI context documentation
- MUST build context files from project source
- MUST include philosophy and design documents
- MUST update context on significant changes
- MUST validate context completeness

#### FR-AC-002: Version History Collection
- MUST generate version control history context
- MUST extract patterns from commit history
- MUST identify code evolution patterns
- MUST document refactoring history
- MUST maintain decision rationale

#### FR-AC-003: Context File Organization
- MUST organize context by domain
- MUST maintain context file hierarchy
- MUST cross-reference related contexts
- MUST version context files
- MUST optimize for AI consumption

### Project Guidelines Documentation

#### FR-AC-004: AI Assistant Instructions Maintenance
- MUST maintain AI assistant-specific instructions
- MUST document working philosophy
- MUST track memory system guidelines
- MUST specify agent usage patterns
- MUST update based on learnings

#### FR-AC-005: AGENTS.md Guidelines
- MUST document agent catalog and usage
- MUST maintain agent best practices
- MUST track agent effectiveness
- MUST provide agent selection guidance
- MUST update agent capabilities

#### FR-AC-006: DISCOVERIES.md Management
- MUST track non-obvious problems and solutions
- MUST document root causes and preventions
- MUST maintain searchable format
- MUST prompt for updates on problem resolution
- MUST prevent repeated problem solving

## Response Guidelines Requirements

### Authenticity and Professionalism

#### FR-RG-001: Response Authenticity
- MUST avoid sycophantic language
- MUST provide honest technical assessment
- MUST disagree constructively when appropriate
- MUST focus on code and problems, not praise
- MUST maintain professional objectivity

#### FR-RG-002: Brevity and Directness
- MUST provide concise responses (< 4 lines by default)
- MUST minimize preamble and postamble
- MUST answer questions directly
- MUST avoid unnecessary explanations
- MUST respect command-line interface constraints

#### FR-RG-003: Tone and Style Guidelines
- MUST maintain professional tone
- MUST avoid emojis unless requested
- MUST use technical accuracy over validation
- MUST provide actionable feedback
- MUST focus on facts and problem-solving

### Development Practice Guidelines

#### FR-DG-001: Code Convention Following
- MUST understand file code conventions first
- MUST mimic existing code style
- MUST use existing libraries and utilities
- MUST follow established patterns
- MUST check neighboring files for context

#### FR-DG-002: Security Best Practices
- MUST never expose or log secrets
- MUST never commit sensitive data
- MUST validate input data
- MUST handle authentication properly
- MUST follow security guidelines

#### FR-DG-003: Dependency Management
- MUST use appropriate dependency management tools for the language
- MUST use recommended package managers for external libraries
- MUST check project dependency files before assuming library availability
- MUST verify library availability before use
- MUST manage dependency versions properly

## Analysis and Decision Guidelines

### Analysis-First Development

#### FR-AD-001: Problem Analysis Requirements
- MUST analyze before implementing
- MUST provide structured problem decomposition
- MUST list 2-3 approach options
- MUST document trade-offs clearly
- MUST create implementation plans

#### FR-AD-002: Analysis Output Format
- MUST include problem decomposition
- MUST provide approach comparisons
- MUST state clear recommendations
- MUST create step-by-step plans
- MUST identify blockers early

#### FR-AD-003: When to Analyze
- MUST analyze for new features
- MUST analyze for complex refactoring
- MUST analyze for performance issues
- MUST analyze for integration tasks
- MUST skip analysis only for trivial changes

### Decision Tracking

#### FR-DT-001: Decision Documentation
- MUST document architectural decisions
- MUST track decision rationale
- MUST record alternatives considered
- MUST identify review triggers
- MUST maintain decision history

#### FR-DT-002: Decision Review
- MUST consult existing decisions first
- MUST understand original rationale
- MUST justify decision changes
- MUST update decision records
- MUST prevent decision cycling

## Tool and Library Guidelines

### Tool Usage Patterns

#### FR-TG-001: Tool Selection
- MUST prefer appropriate specialized tools
- MUST use Task tool for complex searches
- MUST use specific tools over generic bash
- MUST batch tool calls when possible
- MUST handle tool results properly

#### FR-TG-002: Parallel Execution
- MUST identify parallelizable operations
- MUST batch independent tool calls
- MUST use single message for multiple calls
- MUST optimize for performance
- MUST handle parallel results correctly

### Library vs Custom Code

#### FR-LG-001: Library Decision Criteria
- MUST evaluate alignment with needs
- MUST detect when fighting libraries
- MUST identify over-wrapping patterns
- MUST track library effectiveness
- MUST document library decisions

#### FR-LG-002: Evolution Management
- MUST support custom to library migration
- MUST support library to custom migration
- MUST maintain clean integration points
- MUST document migration rationale
- MUST minimize lock-in

## Quality Enforcement Guidelines

### Code Quality Standards

#### FR-QG-001: Formatting Standards
- MUST use 120 character line length
- MUST organize imports properly
- MUST use descriptive names
- MUST include type hints
- MUST end files with newline

#### FR-QG-002: Testing Standards
- MUST follow 60/30/10 test pyramid
- MUST test critical paths 100%
- MUST write tests for complex logic
- MUST maintain test documentation
- MUST validate test effectiveness

### Philosophy Compliance

#### FR-PC-001: Simplicity Validation
- MUST check for unnecessary complexity
- MUST identify simplification opportunities
- MUST validate abstraction necessity
- MUST enforce YAGNI principle
- MUST track complexity metrics

#### FR-PC-002: Zero-BS Enforcement
- MUST reject placeholder code
- MUST require working implementations
- MUST detect incomplete features
- MUST validate functionality claims
- MUST enforce "works or doesn't exist"

## Performance Requirements

### PR-AC-001: Context Generation
- MUST generate context files in < 30 seconds
- MUST update incrementally when possible
- MUST optimize context file size
- MUST validate context quickly

### PR-AC-002: Guideline Checking
- MUST validate guidelines in real-time
- MUST provide immediate feedback
- MUST not slow development workflow
- MUST cache validation results