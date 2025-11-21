# PM:Prepare - Rich Delegation Package

Create AI-enhanced delegation package with comprehensive context for a backlog item.

## What This Command Does

Phase 2 AI assistance: Analyzes a backlog item and codebase to create a rich delegation package that helps agents work more effectively.

**Generated Context:**
- **Relevant Files**: Files agent should examine (based on item keywords)
- **Similar Patterns**: Patterns in codebase to follow
- **Test Requirements**: Specific tests needed (category-based)
- **Architectural Notes**: Design guidance and constraints
- **Dependencies**: Other items this depends on
- **Complexity Assessment**: Simple/medium/complex with rationale

## Usage

```bash
/pm:prepare <backlog-id> [agent]
```

**Arguments:**
- `backlog-id`: Item ID (e.g., BL-001)
- `agent`: Optional agent role (default: builder)
  - `builder` - Implementation focus
  - `reviewer` - Quality checks
  - `tester` - Test coverage

## Example Output

```
🤖 Analyzing backlog item and codebase...
   This may take a moment...

============================================================
📦 RICH DELEGATION PACKAGE: BL-003
============================================================

Item: BL-003 - Add authentication API
Agent: builder
Priority: HIGH
Complexity: medium (4h estimated)

Description:
  Implement JWT-based authentication API with login/logout endpoints

📂 Relevant Files to Examine:
  • src/api/endpoints.py
  • src/auth/jwt.py
  • tests/test_auth.py
  • .claude/tools/amplihack/pm/state.py

🔍 Similar Patterns in Codebase:
  • Look for similar feature implementations in src/
  • Check existing tests for pattern examples
  • Follow existing code organization patterns
  • Match current naming conventions

✅ Test Requirements:
  • Unit tests for new functions/classes
  • Integration tests for feature workflow
  • Edge case coverage (empty inputs, invalid data)
  • Test success and error paths

🏗️  Architectural Notes:
  - Follow existing patterns in codebase
  - Consider extension points for future needs
  - Good quality bar - reasonable speed

⚠️  Dependencies:
  This item depends on: BL-001, BL-002

============================================================
💡 TIP: Use /pm:start BL-003 to begin work with this package
```

## How It Works

**Analysis Steps:**

1. **Categorize Item**: feature, bug, refactor, test, or doc
2. **Find Relevant Files**: Keyword-based file search in src/, tests/
3. **Identify Patterns**: Category-specific pattern guidance
4. **Detect Dependencies**: Explicit (BL-xxx) and implicit (blocking keywords)
5. **Estimate Complexity**: Hours + technical signals (API/DB/UI changes)
6. **Generate Tests**: Category-specific test requirements
7. **Create Arch Notes**: Complexity and quality bar guidance

**Intelligence Modules:**

- `BacklogAnalyzer` - Categorization, technical signals, business value
- `ProjectAnalyzer` - File finding, pattern identification, codebase metrics
- `DependencyAnalyzer` - Dependency detection, blocking relationships
- `ComplexityEstimator` - Complexity and confidence estimation

## When to Use

**Use /pm:prepare when:**
- Starting complex work (medium/complex items)
- Need codebase context (what files to look at)
- Want test guidance (what tests to write)
- Unclear about patterns (how to structure code)

**Skip /pm:prepare when:**
- Simple, well-understood items
- Just want quick recommendations (use `/pm:suggest`)
- Item has clear, detailed description already

## Workflow Integration

**Typical Flow:**

1. Get recommendations: `/pm:suggest`
2. Prepare package: `/pm:prepare BL-003`
3. Review package details (files, tests, notes)
4. Start work: `/pm:start BL-003`
5. Agent uses rich package context automatically

## Implementation

Implemented in: `.claude/tools/amplihack/pm/cli.py::cmd_prepare()`

Uses:
- `intelligence.py::RecommendationEngine` - Package creation
- `intelligence.py::ProjectAnalyzer` - File and pattern finding
- `intelligence.py::BacklogAnalyzer` - Categorization and signals
- `intelligence.py::DependencyAnalyzer` - Dependency detection
- `intelligence.py::ComplexityEstimator` - Complexity assessment

Data model: `intelligence.py::RichDelegationPackage`

## Philosophy

**Practical AI Assistance:**
- Real codebase analysis (not generic advice)
- Actionable guidance (specific files and tests)
- Transparent reasoning (explain recommendations)
- Fast execution (< 2 seconds)

**Ruthless Simplicity:**
- No complex ML models
- Keyword-based file search
- Rule-based test generation
- Simple pattern matching

**Agent-Friendly:**
- Everything agent needs in one place
- Clear, structured information
- No ambiguity or vagueness
- Ready-to-use context

## Phase 2 Integration

Part of PM Architect Phase 2 (AI Assistance):
- `/pm:suggest` - Smart recommendations
- `/pm:prepare` - This command (rich packages)
- Enhanced workstream context

See Phase 1 commands: `/pm:init`, `/pm:add`, `/pm:start`, `/pm:status`
