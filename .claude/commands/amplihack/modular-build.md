# Modular Build Command

## Input Validation

@.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/modular-build [MODE] [TARGET]`

## Purpose

Build self-contained modules using a progressive validation pipeline: Contract→Spec→Plan→Generate→Review. Each phase validates its output before proceeding. Follows bricks & studs philosophy with ruthless simplicity.

## Parameters

- **MODE** (optional): `auto`, `assist`, or `dry-run` (default: `assist`)
- **TARGET** (optional): Module name or feature description (default: auto-detect)

## Progressive Pipeline

```
CONTRACT → SPEC → PLAN → GENERATE → REVIEW
    ↓       ↓      ↓        ↓         ↓
  Define   Design  Plan   Build    Validate
```

Each phase produces validated output before proceeding to the next.

## Execution Modes

- **Auto**: Run all phases automatically
- **Assist**: Interactive confirmation at each phase (default)
- **Dry-run**: Validate pipeline without creating files

## Validation

Two schemas validate the pipeline:

- **Input Schema**: Validates command parameters and target specification
- **Output Schema**: Validates final module generation results

Each phase performs internal validation before proceeding.

## Phase Implementation

### 1. Contract

- **Agents**: architect, api-designer
- **Purpose**: Define module boundaries and public interfaces
- **Output**: Module contract specification

### 2. Spec

- **Agents**: architect, database, security
- **Purpose**: Detailed technical design
- **Output**: Implementation specification

### 3. Plan

- **Agents**: tester, integration
- **Purpose**: Implementation roadmap
- **Output**: Execution plan with dependencies

### 4. Generate

- **Agents**: builder, tester, integration
- **Purpose**: Build module code and tests
- **Output**: Working module with tests

### 5. Review

- **Agents**: reviewer, security, optimizer
- **Purpose**: Quality validation
- **Output**: Quality report and approval

## External Tools

Auto-detects and runs available quality tools:

- `pytest` - Testing (required)
- `coverage` - Coverage measurement
- `ruff` or `pylint` - Code quality
- `bandit` - Security scanning
- `safety` - Dependency vulnerabilities

Graceful degradation if tools are missing.

## Examples

```bash
# Interactive build (default)
/modular-build user-auth

# Automatic build
/modular-build auto payment-processor

# Validate pipeline only
/modular-build dry-run order-management
```

## Agent Integration

Each phase uses specialized agents in parallel where possible:

- CONTRACT: architect + api-designer (parallel)
- SPEC: architect + database + security (parallel)
- PLAN: tester → integration (sequential)
- GENERATE: builder → tester → integration (sequential)
- REVIEW: reviewer + security + optimizer (parallel)

Integrates with `/ultrathink` and `/fix` workflows.

## Error Handling

- **Validation Failures**: Show errors, suggest fixes, retry
- **External Tool Failures**: Continue with warnings
- **Agent Unavailable**: Fallback to simpler implementation
- **Timeouts**: Prompt for manual validation

## Performance

- Parallel agent execution within phases
- Basic caching for validation results
- Graceful timeout handling

## Configuration

Simplified configuration in `.claude/config/modular-build.json`:

- Phase agent assignments
- Quality gate thresholds
- Output directory
- External tool auto-detection

## Success Criteria

- All phases complete successfully
- Test coverage ≥ 85%
- Zero security warnings
- Module follows bricks & studs design

**Build Report**: Simple summary of phase results, quality metrics, and generated files.

## Remember

The modular build command embodies amplihack's core philosophy:

- **Ruthless Simplicity**: Each phase has one clear purpose
- **Bricks & Studs**: Modules are self-contained with clear contracts
- **Zero-BS Implementation**: Every generated component must work
- **Progressive Validation**: Catch issues early with JSON schema gates
- **Agent Orchestration**: Leverage specialized agents for best results

The goal is to build production-ready modules with comprehensive validation while maintaining the flexibility to handle diverse requirements through the three execution modes.

**Success Metrics**:

- 95%+ validation gate pass rate
- Sub-30 minute builds for standard modules
- Zero security vulnerabilities in generated code
- 85%+ test coverage requirement met
- Complete documentation generated automatically

Start with `/modular-build assist` for interactive learning, then graduate to `/modular-build auto` for production workflows.
