# Modular Build Command

## Input Validation

@.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/modular-build [MODE] [TARGET]`

## Purpose

Sophisticated modular build command that implements a Contract→Spec→Plan→Generate→Review pipeline with progressive validation gates and multiple execution modes. Creates self-contained modules following the bricks & studs philosophy with strict JSON validation at each phase transition.

## Parameters

- **MODE** (optional): Execution mode
  - `auto` - Fully automated execution through all phases (default)
  - `assist` - Interactive mode with user confirmation at each phase
  - `dry-run` - Validation-only mode that shows what would be done

- **TARGET** (optional): Module or feature to build
  - Module name (e.g., `user-auth`, `payment-processor`)
  - Feature description (e.g., "user authentication system")
  - `auto` - Automatic target detection from context (default)

## Progressive Pipeline Architecture

### Phase Flow with Validation Gates

```
┌─── CONTRACT Phase ───┐ → JSON Schema → ┌─── SPEC Phase ───┐
│ • Module interfaces  │   Validation    │ • Technical specs │
│ • Public contracts   │                 │ • Dependencies    │
│ • Boundary definition│                 │ • Implementation  │
└─────────────────────┘                 └──────────────────┘
          ↓                                       ↓
    JSON Validation                         JSON Validation
    (contract.schema.json)                  (spec.schema.json)
          ↓                                       ↓
┌─── PLAN Phase ───┐ → JSON Schema → ┌─── GENERATE Phase ───┐
│ • Implementation │   Validation    │ • Code generation     │
│   roadmap       │                 │ • File creation       │
│ • Dependencies  │                 │ • Test scaffolding    │
│ • Task ordering │                 │ • Integration setup   │
└─────────────────┘                 └───────────────────────┘
          ↓                                       ↓
    JSON Validation                         JSON Validation
    (plan.schema.json)                      (generate.schema.json)
          ↓                                       ↓
                    ┌─── REVIEW Phase ───┐
                    │ • Quality gates     │ → JSON Schema
                    │ • External tools    │   Validation
                    │ • Final approval    │   (review.schema.json)
                    │ • Success metrics   │
                    └─────────────────────┘
```

## Execution Modes

### Auto Mode (`/modular-build auto [target]`)

**Process**:

```bash
# Fully automated execution
1. CONTRACT Phase: Generate module contracts automatically
2. Validation Gate: Validate against contract.schema.json
3. SPEC Phase: Create detailed technical specifications
4. Validation Gate: Validate against spec.schema.json
5. PLAN Phase: Generate implementation roadmap
6. Validation Gate: Validate against plan.schema.json
7. GENERATE Phase: Build code, tests, and integration
8. Validation Gate: Validate against generate.schema.json
9. REVIEW Phase: Run all quality gates and external tools
10. Validation Gate: Validate against review.schema.json
11. SUCCESS: Module ready for use
```

**Auto-triggers when**:

- Clear target specification provided
- No user interaction preferences set
- Standard module patterns detected

### Assist Mode (`/modular-build assist [target]`)

**Process**:

```bash
# Interactive confirmation at each phase
1. CONTRACT Phase: Generate contracts → Show user → Confirm
2. Validation Gate: Show validation results → User approval required
3. SPEC Phase: Create specs → Show user → Confirm
4. Validation Gate: Show validation results → User approval required
5. PLAN Phase: Generate plan → Show user → Confirm
6. Validation Gate: Show validation results → User approval required
7. GENERATE Phase: Generate code → Show user → Confirm
8. Validation Gate: Show validation results → User approval required
9. REVIEW Phase: Run quality gates → Show results → Final approval
10. SUCCESS: Module ready with user validation at each step
```

**Auto-triggers when**:

- Complex or ambiguous target specification
- User preference for interactive mode
- Critical system components being built

### Dry-Run Mode (`/modular-build dry-run [target]`)

**Process**:

```bash
# Validation-only execution (no file creation)
1. CONTRACT Phase: Validate contract generation logic
2. Validation Gate: Test against contract.schema.json
3. SPEC Phase: Validate specification generation
4. Validation Gate: Test against spec.schema.json
5. PLAN Phase: Validate planning logic
6. Validation Gate: Test against plan.schema.json
7. GENERATE Phase: Validate code generation (no files written)
8. Validation Gate: Test against generate.schema.json
9. REVIEW Phase: Validate quality gate configuration
10. REPORT: Complete validation report with recommendations
```

**Auto-triggers when**:

- Testing new module patterns
- Validating configuration changes
- Pre-flight checks before major builds

## JSON Schema Validation System

### Contract Phase Schema (`contract.schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["module_name", "public_interface", "responsibilities", "dependencies"],
  "properties": {
    "module_name": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9-]*[a-z0-9]$"
    },
    "public_interface": {
      "type": "object",
      "required": ["functions", "classes", "exports"],
      "properties": {
        "functions": { "type": "array", "items": { "type": "string" } },
        "classes": { "type": "array", "items": { "type": "string" } },
        "exports": { "type": "array", "items": { "type": "string" } }
      }
    },
    "responsibilities": {
      "type": "array",
      "items": { "type": "string" },
      "minItems": 1,
      "maxItems": 3
    },
    "dependencies": {
      "type": "object",
      "properties": {
        "internal": { "type": "array", "items": { "type": "string" } },
        "external": { "type": "array", "items": { "type": "string" } }
      }
    },
    "contract_version": { "type": "string", "pattern": "^v[0-9]+\\.[0-9]+$" }
  }
}
```

### Spec Phase Schema (`spec.schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["technical_specs", "implementation_details", "testing_strategy"],
  "properties": {
    "technical_specs": {
      "type": "object",
      "required": ["architecture", "data_models", "api_contracts"],
      "properties": {
        "architecture": { "type": "string" },
        "data_models": { "type": "array", "items": { "type": "object" } },
        "api_contracts": { "type": "array", "items": { "type": "object" } }
      }
    },
    "implementation_details": {
      "type": "object",
      "required": ["file_structure", "key_algorithms", "error_handling"],
      "properties": {
        "file_structure": { "type": "object" },
        "key_algorithms": { "type": "array", "items": { "type": "string" } },
        "error_handling": { "type": "string" }
      }
    },
    "testing_strategy": {
      "type": "object",
      "required": ["unit_tests", "integration_tests", "coverage_target"],
      "properties": {
        "unit_tests": { "type": "array", "items": { "type": "string" } },
        "integration_tests": { "type": "array", "items": { "type": "string" } },
        "coverage_target": { "type": "number", "minimum": 0.8, "maximum": 1.0 }
      }
    }
  }
}
```

### Plan Phase Schema (`plan.schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["implementation_roadmap", "dependencies_order", "validation_checkpoints"],
  "properties": {
    "implementation_roadmap": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["step", "description", "estimated_time", "dependencies"],
        "properties": {
          "step": { "type": "integer", "minimum": 1 },
          "description": { "type": "string" },
          "estimated_time": { "type": "string", "pattern": "^[0-9]+[mh]$" },
          "dependencies": { "type": "array", "items": { "type": "integer" } }
        }
      }
    },
    "dependencies_order": {
      "type": "array",
      "items": { "type": "string" }
    },
    "validation_checkpoints": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["checkpoint", "criteria", "validation_method"],
        "properties": {
          "checkpoint": { "type": "string" },
          "criteria": { "type": "array", "items": { "type": "string" } },
          "validation_method": {
            "type": "string",
            "enum": ["automated", "manual", "external_tool"]
          }
        }
      }
    }
  }
}
```

### Generate Phase Schema (`generate.schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["generated_files", "test_coverage", "integration_points"],
  "properties": {
    "generated_files": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["file_path", "file_type", "size_bytes", "checksum"],
        "properties": {
          "file_path": { "type": "string" },
          "file_type": { "type": "string", "enum": ["source", "test", "config", "documentation"] },
          "size_bytes": { "type": "integer", "minimum": 0 },
          "checksum": { "type": "string", "pattern": "^[a-f0-9]{64}$" }
        }
      }
    },
    "test_coverage": {
      "type": "object",
      "required": ["percentage", "uncovered_lines", "test_files"],
      "properties": {
        "percentage": { "type": "number", "minimum": 0, "maximum": 100 },
        "uncovered_lines": { "type": "array", "items": { "type": "string" } },
        "test_files": { "type": "array", "items": { "type": "string" } }
      }
    },
    "integration_points": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["module", "interface", "status"],
        "properties": {
          "module": { "type": "string" },
          "interface": { "type": "string" },
          "status": { "type": "string", "enum": ["connected", "pending", "failed"] }
        }
      }
    }
  }
}
```

### Review Phase Schema (`review.schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["quality_gates", "external_validations", "final_status"],
  "properties": {
    "quality_gates": {
      "type": "object",
      "required": ["code_quality", "security_scan", "performance_check", "documentation"],
      "properties": {
        "code_quality": {
          "type": "object",
          "required": ["score", "issues"],
          "properties": {
            "score": { "type": "number", "minimum": 0, "maximum": 10 },
            "issues": { "type": "array", "items": { "type": "string" } }
          }
        },
        "security_scan": {
          "type": "object",
          "required": ["vulnerabilities", "status"],
          "properties": {
            "vulnerabilities": { "type": "array", "items": { "type": "object" } },
            "status": { "type": "string", "enum": ["clean", "warnings", "critical"] }
          }
        },
        "performance_check": {
          "type": "object",
          "required": ["benchmarks", "recommendations"],
          "properties": {
            "benchmarks": { "type": "object" },
            "recommendations": { "type": "array", "items": { "type": "string" } }
          }
        },
        "documentation": {
          "type": "object",
          "required": ["completeness", "accuracy"],
          "properties": {
            "completeness": { "type": "number", "minimum": 0, "maximum": 100 },
            "accuracy": { "type": "string", "enum": ["verified", "needs_review", "incomplete"] }
          }
        }
      }
    },
    "external_validations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["tool", "result", "output"],
        "properties": {
          "tool": { "type": "string" },
          "result": { "type": "string", "enum": ["pass", "fail", "warning"] },
          "output": { "type": "string" }
        }
      }
    },
    "final_status": {
      "type": "string",
      "enum": ["approved", "needs_fixes", "rejected"]
    }
  }
}
```

## Pipeline Phase Implementation

### Phase 1: Contract Generation

```markdown
**Purpose**: Define clear module contracts and interfaces

**Agent Integration**:

- Use architect agent for module design
- Use api-designer agent for interface contracts

**Process**:

1. Analyze target requirement and existing codebase
2. Generate module boundaries and responsibilities
3. Define public interface contracts (functions, classes, exports)
4. Specify internal and external dependencies
5. Create contract.json following contract.schema.json
6. Validate against schema and business rules

**Output**: contract.json validated against contract.schema.json
```

### Phase 2: Specification Creation

```markdown
**Purpose**: Generate detailed technical specifications

**Agent Integration**:

- Use architect agent for technical architecture
- Use database agent for data model design
- Use security agent for security requirements

**Process**:

1. Expand contracts into detailed technical specifications
2. Design data models and API contracts
3. Define file structure and key algorithms
4. Specify error handling and edge cases
5. Create testing strategy with coverage targets
6. Generate spec.json following spec.schema.json
7. Validate against schema and architectural principles

**Output**: spec.json validated against spec.schema.json
```

### Phase 3: Implementation Planning

```markdown
**Purpose**: Create implementation roadmap with dependencies

**Agent Integration**:

- Use tester agent for test planning
- Use integration agent for dependency analysis

**Process**:

1. Break specifications into implementation steps
2. Analyze dependencies and determine build order
3. Estimate implementation time for each step
4. Define validation checkpoints and criteria
5. Create dependency resolution strategy
6. Generate plan.json following plan.schema.json
7. Validate against schema and project constraints

**Output**: plan.json validated against plan.schema.json
```

### Phase 4: Code Generation

```markdown
**Purpose**: Build actual code modules and integration

**Agent Integration**:

- Use builder agent for code implementation
- Use tester agent for test generation
- Use integration agent for external connections

**Process**:

1. Generate source code following specifications
2. Create comprehensive test suites
3. Generate configuration and setup files
4. Create integration points with existing modules
5. Calculate test coverage and quality metrics
6. Generate generate.json following generate.schema.json
7. Validate against schema and code quality standards

**Output**:

- Complete module implementation
- Test suite with required coverage
- generate.json validated against generate.schema.json
```

### Phase 5: Quality Review

```markdown
**Purpose**: Comprehensive validation and quality gates

**Agent Integration**:

- Use reviewer agent for code quality review
- Use security agent for security scanning
- Use optimizer agent for performance analysis

**Process**:

1. Run code quality analysis (linting, complexity, maintainability)
2. Execute security vulnerability scanning
3. Perform performance benchmarking and analysis
4. Validate documentation completeness and accuracy
5. Execute external validation tools (if configured)
6. Generate review.json following review.schema.json
7. Determine final approval status

**Output**: review.json validated against review.schema.json
```

## External Tool Integration

### Supported External Validators

```yaml
# .claude/config/modular-build-validators.yaml
validators:
  code_quality:
    - tool: "pylint"
      command: "pylint --output-format=json {module_path}"
      schema: "pylint.result.schema.json"
    - tool: "eslint"
      command: "eslint --format json {module_path}"
      schema: "eslint.result.schema.json"

  security:
    - tool: "bandit"
      command: "bandit -f json -r {module_path}"
      schema: "bandit.result.schema.json"
    - tool: "safety"
      command: "safety check --json"
      schema: "safety.result.schema.json"

  performance:
    - tool: "pytest-benchmark"
      command: "pytest --benchmark-json={output_file} {test_path}"
      schema: "pytest-benchmark.result.schema.json"

  documentation:
    - tool: "pydocstyle"
      command: "pydocstyle --format=json {module_path}"
      schema: "pydocstyle.result.schema.json"
```

### External Tool Execution

```bash
# Automatic tool detection and execution
for validator in configured_validators:
    if tool_available(validator.tool):
        result = execute_command(validator.command)
        validate_result(result, validator.schema)
        integrate_into_review_phase(result)
```

## Command Examples

### Basic Usage

```bash
# Automatic mode with auto-detection
/modular-build

# Specific target with automatic mode
/modular-build auto user-authentication

# Interactive assistance mode
/modular-build assist payment-processor

# Validation dry-run
/modular-build dry-run order-management
```

### Advanced Usage

```bash
# Build complex module with assistance
/modular-build assist "user authentication system with OAuth2 and JWT"

# Validate existing module configuration
/modular-build dry-run existing-module-name

# Auto-build from architectural description
/modular-build auto "RESTful API for product catalog with search and filtering"
```

## Integration with Existing Agents

### Workflow Integration

```markdown
**With UltraThink**:

- `/modular-build` can be invoked as part of larger workflows
- Integrates with DEFAULT_WORKFLOW.md for complex projects

**With Fix Command**:

- Failed validation gates trigger `/fix` for issue resolution
- Quality gate failures escalate to appropriate fix patterns

**With Existing Agents**:

- Each phase leverages multiple specialized agents
- Parallel agent execution where dependencies allow
- Sequential execution for phase transitions
```

### Agent Coordination Pattern

```bash
# Phase execution with multiple agents
CONTRACT_PHASE:
  agents: [architect, api-designer]
  execution: parallel

SPEC_PHASE:
  agents: [architect, database, security]
  execution: parallel

PLAN_PHASE:
  agents: [tester, integration]
  execution: sequential (tester → integration)

GENERATE_PHASE:
  agents: [builder, tester, integration]
  execution: sequential (builder → tester → integration)

REVIEW_PHASE:
  agents: [reviewer, security, optimizer]
  execution: parallel
```

## Error Handling and Recovery

### Validation Gate Failures

```bash
# Contract phase validation fails
→ Show validation errors
→ Offer manual correction or auto-fix options
→ Re-run contract generation with fixes
→ Continue to next phase only after validation passes

# Spec phase validation fails
→ Identify specification gaps or conflicts
→ Suggest architectural improvements
→ Allow user refinement in assist mode
→ Re-generate specifications until valid

# Plan phase validation fails
→ Highlight dependency conflicts or timing issues
→ Suggest alternative implementation strategies
→ Allow plan adjustments and re-validation
→ Ensure implementable plan before generation

# Generate phase validation fails
→ Report code generation issues (syntax, logic, coverage)
→ Trigger automatic fixes where possible
→ Escalate to relevant fix patterns (/fix code, /fix test)
→ Re-generate until all quality gates pass

# Review phase validation fails
→ Provide detailed quality gate failure report
→ Suggest specific improvements for each failing area
→ Allow iterative fixes and re-validation
→ Require all quality gates to pass before approval
```

### Recovery Strategies

```bash
# Graceful degradation
if external_tool_unavailable:
    skip_external_validation()
    note_missing_validation_in_report()

if validation_timeout:
    prompt_for_manual_validation()
    allow_override_with_justification()

if agent_unavailable:
    fallback_to_simpler_implementation()
    document_reduced_capability()
```

## Performance Optimization

### Parallel Execution Strategy

```bash
# Phase-internal parallelization
CONTRACT_PHASE: Run architect + api-designer simultaneously
SPEC_PHASE: Run architect + database + security simultaneously
REVIEW_PHASE: Run reviewer + security + optimizer simultaneously

# Pipeline optimization
- Cache validation results to avoid re-computation
- Incremental builds for module updates
- Skip unchanged phases in iterative development
```

### Caching Strategy

```bash
# JSON schema validation caching
cache_key = hash(json_content + schema_version)
if cached_validation_result(cache_key):
    return cached_result
else:
    result = validate_json(content, schema)
    cache_validation_result(cache_key, result)
    return result
```

## Configuration Management

### Project-Specific Settings

```json
// .claude/config/modular-build.json
{
  "default_mode": "assist",
  "validation_strictness": "high",
  "external_tools": {
    "enable_security_scanning": true,
    "enable_performance_testing": true,
    "required_coverage_threshold": 0.85
  },
  "phase_timeouts": {
    "contract": 300,
    "spec": 600,
    "plan": 300,
    "generate": 1200,
    "review": 900
  },
  "quality_gates": {
    "min_code_quality_score": 8.0,
    "max_security_warnings": 0,
    "required_documentation_completeness": 90
  }
}
```

### Schema Versioning

```bash
# Schema evolution strategy
v1.0: Initial JSON schemas
v1.1: Add optional fields (backward compatible)
v2.0: Breaking changes (requires migration)

# Migration support
if schema_version < current_version:
    migrate_json_to_current_version(json_data)
```

## Success Metrics and Reporting

### Build Success Criteria

```yaml
success_criteria:
  all_phases_completed: true
  all_validations_passed: true
  quality_gates_satisfied: true
  external_tools_clean: true
  test_coverage_met: true
  documentation_complete: true
```

### Detailed Reporting

```bash
# Build completion report
=== MODULAR BUILD COMPLETE ===
Module: user-authentication
Mode: assist
Duration: 24m 15s

Phase Results:
✅ CONTRACT: Valid (2m 30s)
✅ SPEC: Valid (4m 45s)
✅ PLAN: Valid (3m 15s)
✅ GENERATE: Valid (11m 20s)
✅ REVIEW: Valid (2m 25s)

Quality Gates:
✅ Code Quality: 9.2/10
✅ Security: Clean (0 vulnerabilities)
✅ Performance: Meets benchmarks
✅ Documentation: 94% complete
✅ Test Coverage: 87%

External Tools:
✅ pylint: No issues
✅ bandit: Clean
✅ pytest-benchmark: All benchmarks pass

Generated Files: 23 files (Source: 12, Tests: 8, Config: 3)
Integration Points: 4 modules connected successfully

Status: ✅ APPROVED - Ready for integration
```

## Advanced Features

### Template System

```bash
# Pre-built module templates
templates:
  - rest_api_module
  - data_processing_module
  - authentication_module
  - notification_module
  - reporting_module

# Template usage
/modular-build auto rest_api_module --template
→ Uses pre-validated contract/spec patterns
→ Faster execution with proven patterns
→ Customizable template parameters
```

### Incremental Builds

```bash
# Module update workflow
/modular-build incremental user-auth
→ Detects changes since last build
→ Only re-runs affected phases
→ Maintains validation chain integrity
→ Updates integration points as needed
```

### Build Pipelines

```bash
# Multi-module builds
/modular-build pipeline auth,payments,notifications
→ Builds modules in dependency order
→ Validates inter-module contracts
→ Ensures system-wide consistency
→ Reports pipeline-level metrics
```

## Integration with CI/CD

### GitHub Actions Integration

```yaml
# .github/workflows/modular-build.yml
name: Modular Build Validation
on: [push, pull_request]

jobs:
  validate-modules:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Validate Module Builds
        run: |
          /modular-build dry-run --all-modules
          /modular-build validate --strict
```

### Pre-commit Hook Integration

```bash
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: modular-build-validate
        name: Validate modular build integrity
        entry: /modular-build dry-run --changed-modules
        language: system
        pass_filenames: false
```

## Security Considerations

### Input Validation

```bash
# All user inputs validated before processing
validate_module_name(target)  # Alphanumeric, hyphens only
validate_mode_parameter(mode)  # Only allowed modes
validate_file_paths(paths)    # No path traversal
validate_json_schemas(data)   # Schema compliance
```

### Execution Safety

```bash
# Safe execution environment
- No arbitrary code execution
- Sandboxed external tool execution
- Input sanitization for all external commands
- Validation of all generated files before writing
- Rollback capability for failed builds
```

## Troubleshooting Guide

### Common Issues

```bash
# Validation failures
ISSUE: "Contract validation failed - missing required field"
FIX: Check contract.schema.json requirements
     Ensure all required fields are populated

ISSUE: "External tool timeout"
FIX: Increase timeout in configuration
     Check tool availability and permissions

ISSUE: "Dependency resolution failed"
FIX: Verify module dependencies exist
     Check for circular dependencies
     Review dependency versions
```

### Debug Mode

```bash
# Enhanced debugging
/modular-build assist --debug user-auth
→ Shows detailed phase execution logs
→ Validates intermediate JSON at each step
→ Provides agent execution traces
→ Outputs detailed error diagnostics
```

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
