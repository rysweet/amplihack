# Skill Builder Examples

Comprehensive examples of creating Claude Code skills using the skill-builder.

**Last Updated**: 2025-11-15

---

## Basic Examples

### Example 1: Simple Auto-Discovery Skill

**User Request**: "I need a skill for validating JSON schemas"

**Command**:

```bash
/amplihack:skill-builder json-validator skill "Validates JSON data against schemas with detailed error reporting"
```

**Expected Output**:

```
.claude/skills/json-validator/
└── SKILL.md
```

**Generated SKILL.md**:

```markdown
---
name: json-validator
description: Validates JSON data against schemas with detailed error reporting. Use for JSON validation, schema checking, or data quality assurance.
---

# JSON Validator

## Purpose

Validates JSON data against predefined schemas and provides detailed error reports.

## When I Activate

I automatically load when you mention:

- "validate JSON" or "check JSON schema"
- "JSON validation" or "schema validation"
- "verify JSON structure"

## What I Do

1. Accept JSON data and schema definition
2. Parse and validate structure
3. Check types, required fields, constraints
4. Generate detailed error reports
5. Suggest fixes for validation failures

## Usage Example
```

User: "Validate this JSON against the user schema"
Skill: _activates automatically_
"I'll validate that JSON for you..."

```

```

### Example 2: Command-Based Skill

**User Request**: "Create a command for analyzing test coverage"

**Command**:

```bash
/amplihack:skill-builder test-coverage command "Analyzes test coverage gaps and suggests improvements"
```

**Expected Output**:

```
.claude/commands/amplihack/test-coverage.md
```

**Generated File Structure**:

```markdown
---
description: Analyzes test coverage gaps and suggests improvements
argument-hint: [target-path]
---

# Test Coverage Analyzer

## Usage

`/amplihack:test-coverage [target-path]`

## Purpose

Identifies gaps in test coverage and recommends additional test cases.

## EXECUTION INSTRUCTIONS FOR CLAUDE

[Step-by-step workflow...]
```

### Example 3: Agent Skill

**User Request**: "Build an agent for dependency analysis"

**Command**:

```bash
/amplihack:skill-builder dependency-analyzer agent "Analyzes project dependencies and detects version conflicts"
```

**Expected Output**:

`.claude/agents/amplihack/specialized/dependency-analyzer.md`:

```markdown
---
role: dependency-analyzer
description: Analyzes project dependencies, detects version conflicts, and identifies security vulnerabilities across npm, pip, cargo, and other package managers
---

# Dependency Analyzer Agent

## Role

Specialized agent for comprehensive dependency analysis and conflict resolution.

## When to Invoke

- Dependency conflicts blocking development
- Security audit of dependencies required
- Version compatibility analysis needed
- License compliance checking
- Before major version upgrades

## Capabilities

1. **Conflict Detection**: Identifies version mismatches and incompatible requirements
2. **Security Scanning**: Checks for known CVEs and vulnerabilities
3. **License Analysis**: Validates license compatibility and compliance
4. **Update Recommendations**: Suggests safe upgrade paths
5. **Transitive Analysis**: Maps complete dependency trees

## Analysis Process

### Step 1: Discover Dependencies

Scan project for dependency files:

- package.json, package-lock.json (npm)
- requirements.txt, Pipfile, pyproject.toml (Python)
- Cargo.toml, Cargo.lock (Rust)
- go.mod, go.sum (Go)

### Step 2: Build Dependency Graph

Map direct and transitive dependencies with version constraints.

### Step 3: Detect Conflicts

Identify:

- Version mismatches between direct dependencies
- Incompatible transitive dependencies
- Circular dependencies
- Missing peer dependencies

### Step 4: Security Audit

Check each dependency against:

- npm audit / pip-audit / cargo audit
- Known CVE databases
- GitHub security advisories

### Step 5: Generate Report

Provide:

- Conflict summary with resolution suggestions
- Security vulnerabilities with severity ratings
- License compatibility matrix
- Safe upgrade path recommendations

## Output Format

**Conflict Report**:
```

CONFLICTS FOUND:

- package-a@1.0 requires foo@^2.0
- package-b@2.0 requires foo@^3.0
  RESOLUTION: Upgrade package-a to 2.0 (compatible with foo@^3.0)

```

**Security Report**:
```

VULNERABILITIES:

- axios@0.21.0: CVE-2021-3749 (HIGH)
  Fix: Upgrade to axios@0.21.2+

```

## Integration

Works with:
- ci-diagnostic-workflow (pre-push dependency checks)
- security agent (vulnerability assessment)
- pre-commit-diagnostic (local validation)
```

### Example 4: Scenario Tool Skill

**User Request**: "Create a production tool for code review automation"

**Command**:

```bash
/amplihack:skill-builder code-reviewer scenario "Automated code review with security and quality checks"
```

**Expected Output**:

`.claude/scenarios/code-reviewer/code_reviewer.py`:

```python
#!/usr/bin/env python3
"""Automated code review with security and quality checks."""

import argparse
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List


@dataclass
class ReviewResult:
    """Results from reviewing a single file."""

    file_path: Path
    issues: List[str]
    security_concerns: List[str]
    quality_score: float


def review_file(file_path: Path) -> ReviewResult:
    """Review a single file for security and quality issues."""
    issues = []
    security_concerns = []

    content = file_path.read_text()

    # Security checks
    if "eval(" in content:
        security_concerns.append("Code injection risk: eval() detected")
    if "exec(" in content:
        security_concerns.append("Code execution risk: exec() detected")

    # Quality checks
    lines = content.split("\n")
    if len(lines) > 500:
        issues.append(f"File too large: {len(lines)} lines (recommend < 500)")

    # Calculate quality score
    quality_score = 100.0
    quality_score -= len(issues) * 5
    quality_score -= len(security_concerns) * 10

    return ReviewResult(
        file_path=file_path,
        issues=issues,
        security_concerns=security_concerns,
        quality_score=max(0.0, quality_score),
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated code review with security and quality checks"
    )
    parser.add_argument("target", help="File or directory to review")
    parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )
    args = parser.parse_args()

    target = Path(args.target)
    if not target.exists():
        print(f"Error: {target} not found", file=sys.stderr)
        sys.exit(1)

    # Collect files to review
    files = [target] if target.is_file() else list(target.rglob("*.py"))

    # Review each file
    results = [review_file(f) for f in files]

    # Display results
    for result in results:
        print(f"\n{result.file_path}")
        print(f"Quality Score: {result.quality_score:.1f}/100")
        if result.security_concerns:
            print("Security Concerns:")
            for concern in result.security_concerns:
                print(f"  - {concern}")
        if result.issues:
            print("Issues:")
            for issue in result.issues:
                print(f"  - {issue}")


if __name__ == "__main__":
    main()
```

`.claude/scenarios/code-reviewer/README.md`:

````markdown
# Code Reviewer

Automated code review with security and quality checks.

## Features

- Security vulnerability detection (eval, exec, SQL injection patterns)
- Code quality metrics (file size, complexity, style)
- Multiple output formats (text, JSON)
- Recursive directory scanning

## Installation

```bash
# From amplihack repository root
pip install -e .
```
````

## Usage

```bash
# Review single file
python .claude/scenarios/code-reviewer/code_reviewer.py file.py

# Review directory
python .claude/scenarios/code-reviewer/code_reviewer.py ./src/

# JSON output
python .claude/scenarios/code-reviewer/code_reviewer.py ./src/ --format json
```

## Output

```
./src/module.py
Quality Score: 95.0/100
Issues:
  - Function too complex: calculate_metrics (20 branches)
```

## Integration

Add to Makefile:

```makefile
review-code:
	python .claude/scenarios/code-reviewer/code_reviewer.py $(TARGET)
```

```

---

## Advanced Examples

### Example 5: Multi-File Skill with Scripts

**User Request**: "Build a skill for financial analysis with calculations"

**Natural Language** (skill auto-activates):

```

User: "I need to build a skill that calculates financial ratios like ROE and P/E"
skill-builder: _activates automatically_
"I'll help you create that financial analysis skill..."

```

**Generated Structure**:

```

.claude/skills/financial-analyzer/
├── SKILL.md # Core instructions (<5K tokens)
├── reference.md # Detailed formulas and methodologies
├── examples.md # Sample analyses
└── scripts/
├── calculate.py # Ratio calculations
└── validate.py # Input validation

````

**SKILL.md** (Progressive Disclosure):

```markdown
---
name: financial-analyzer
description: Calculate and interpret financial ratios (ROE, P/E, debt-to-equity, current ratio) against industry benchmarks. Use for financial statements, balance sheets, or income statement analysis.
---

# Financial Analyzer

## Purpose

Calculates key financial ratios and interprets them against industry benchmarks.

## When I Activate

- "analyze financial statements"
- "calculate ROE" or "calculate P/E ratio"
- "financial ratio analysis"

## What I Do

1. Accept financial data (income statement, balance sheet)
2. Calculate ratios using scripts/calculate.py
3. Compare against industry benchmarks
4. Interpret results with context
5. Generate formatted analysis report

## Instructions

For detailed formulas and methodologies, see [reference.md](./reference.md).
For usage examples, see [examples.md](./examples.md).

[Core workflow steps...]
````

### Example 6: Read-Only Skill with Security

**User Request**: "Create a secure skill that only reads code, never modifies"

**Command**:

```bash
/amplihack:skill-builder code-auditor skill "Audits code for security vulnerabilities without making changes"
```

**Generated SKILL.md**:

```markdown
---
name: code-auditor
description: Audits code for security vulnerabilities without making changes. Read-only security analysis for OWASP top 10, injection flaws, and authentication issues.
allowed-tools: Read, Grep, Glob # Security restriction
---

# Code Auditor

## Purpose

Security-focused code auditing without modification capabilities.

## Security Features

- **Read-Only**: Cannot modify code (allowed-tools restriction)
- **No Execute**: Cannot run code
- **Safe Analysis**: Only inspection and reporting

[Rest of skill...]
```

---

## Validation Examples

### Valid Skill Names

✅ `data-transformer`
✅ `json-validator`
✅ `api-client-v2`
✅ `pdf-form-filler`
✅ `code-reviewer`

### Invalid Skill Names

❌ `DataTransformer` (not kebab-case)
❌ `data_transformer` (underscore not allowed)
❌ `dt` (too short, min 3 chars)
❌ `data transformer` (space not allowed)
❌ `ThisIsWayTooLongOfANameForASkillAndShouldBeRejected` (>64 chars)

### Valid Descriptions

✅ "Transforms data between JSON, YAML, and XML formats with validation"
✅ "Analyzes test coverage and identifies gaps in unit, integration, and E2E tests"
✅ "Generates Mermaid diagrams from text descriptions for flowcharts and sequence diagrams"

### Invalid Descriptions

❌ "Transform" (too short, no context)
❌ "Does stuff" (too vague, no specificity)
❌ "A really amazing and wonderful tool that does absolutely everything you could possibly imagine and more beyond your wildest dreams..." (too long, >1024 chars)

---

## Real-World Skill Building Session

### Session: Creating a Data Transformation Skill

**Step 1: User Request**

```
User: "I want to create a skill that transforms data between different formats"
```

**Step 2: Skill Builder Activates (Auto-Discovery)**

```
skill-builder: "I'll help you create that data transformation skill.
               Let me clarify the requirements..."
```

**Step 3: Requirements Clarification (prompt-writer)**

```
Questions asked:
- Which formats to support? (JSON, YAML, XML, CSV)
- Should it validate after transformation?
- Any specific transformation rules?
- Target complexity level?
```

**Step 4: Architecture Design (architect)**

```
Design decisions:
- Skill type: skill (for auto-discovery)
- Multi-file structure (SKILL.md + scripts/)
- Token budget: 4,500 tokens (within limit)
- Supporting scripts for deterministic parsing
```

**Step 5: Skill Generation (builder)**

```
Generated files:
.claude/skills/data-transformer/
├── SKILL.md           (core instructions)
└── scripts/
    ├── parse.py       (format parsing)
    └── transform.py   (transformation logic)
```

**Step 6: Validation (reviewer)**

```
Validation results:
- YAML frontmatter: ✅ Valid
- Token budget: ✅ 4,500 tokens (under 5K limit)
- Description quality: ✅ Keyword-rich for discovery
- Philosophy compliance: ✅ 92% (>85% threshold)
- Zero-BS check: ✅ No stubs or placeholders
```

**Step 7: Completion Report**

```
✅ Skill created successfully!

**Location**: .claude/skills/data-transformer/SKILL.md
**Type**: Claude Code Skill (auto-discovery)
**Token Budget**: 4,500 / 5,000 tokens (90%)
**Philosophy Score**: 92/100

**Next Steps**:
1. Restart Claude Code to load new skill
2. Test with: "Transform this JSON to YAML"
3. Skill should activate automatically
4. Verify transformation works correctly

**Usage**:
- Natural: "Transform this JSON to YAML"
- Explicit: Use /amplihack:skill-builder to invoke directly
```

---

## Testing Examples

### Test 1: Activation Testing

**Objective**: Verify skill activates on expected prompts

**Test Prompts**:

```
1. "Build a skill for PDF processing"
   → skill-builder should activate

2. "Create a new skill that analyzes logs"
   → skill-builder should activate

3. "Generate a skill for API testing"
   → skill-builder should activate

4. "Help me with my code"
   → skill-builder should NOT activate (irrelevant)
```

### Test 2: Validation Testing

**Objective**: Ensure validation catches errors

**Test Cases**:

```python
# Test invalid name
/amplihack:skill-builder DataTransformer skill "Description"
Expected: Error - "Name must be kebab-case"

# Test invalid type
/amplihack:skill-builder data-tool invalid "Description"
Expected: Error - "Type must be: skill, agent, command, scenario"

# Test short description
/amplihack:skill-builder data-tool skill "Short"
Expected: Warning - "Description too short (min 10 chars)"

# Test long description
/amplihack:skill-builder data-tool skill "..."  # 1500 chars
Expected: Error - "Description exceeds 1,024 character limit"
```

### Test 3: File Creation Testing

**Objective**: Verify correct file paths and structures

**Test Cases**:

```bash
# Skill type → creates directory with SKILL.md
/amplihack:skill-builder test-skill skill "Test skill"
Expected: .claude/skills/test-skill/SKILL.md

# Agent type → creates .md file directly
/amplihack:skill-builder test-agent agent "Test agent"
Expected: .claude/agents/amplihack/specialized/test-agent.md

# Command type → creates .md file in commands
/amplihack:skill-builder test-cmd command "Test command"
Expected: .claude/commands/amplihack/test-cmd.md

# Scenario type → creates directory with README.md
/amplihack:skill-builder test-scenario scenario "Test scenario"
Expected: .claude/scenarios/test-scenario/README.md
```

---

## Common Patterns from Community

### Pattern: Gerund Naming (metaskills/skill-builder)

**Convention**: Use gerund form (verb-ing) for skill names

✅ Preferred: `processing-data`, `analyzing-code`, `generating-reports`
❌ Avoid: `data-processor`, `code-analyzer`, `report-generator`

**Rationale**: Emphasizes action/capability over noun/object

### Pattern: CLI-First Approach (metaskills/skill-builder)

**Preference**: Use CLI tools over programmatic APIs

✅ Preferred: `gh`, `aws cli`, `npm`, `jq`, `curl`
❌ Avoid: Python SDKs, custom API wrappers

**Rationale**: Simpler, more portable, easier to debug

### Pattern: Intention-Revealing File Names

**Convention**: File names should clearly indicate purpose

✅ Good: `calculate_financial_ratios.py`, `validate_json_schema.py`
❌ Bad: `utils.py`, `helpers.py`, `functions.py`

---

## Edge Cases and Gotchas

### Edge Case 1: Name Collisions

**Problem**: Skill name already exists

**Detection**:

```python
def check_name_conflict(skill_name, skill_type):
    paths = {
        "skill": f".claude/skills/{skill_name}/SKILL.md",
        "agent": f".claude/agents/amplihack/specialized/{skill_name}.md",
        "command": f".claude/commands/amplihack/{skill_name}.md",
        "scenario": f".claude/scenarios/{skill_name}/README.md"
    }
    target_path = paths[skill_type]
    if Path(target_path).exists():
        return f"Conflict: {skill_type} '{skill_name}' already exists"
    return None
```

**Solution**: Prompt for different name or versioning (v2, v3, etc.)

### Edge Case 2: Token Budget Creep

**Problem**: Skill grows beyond budget over time

**Detection**: Regular health checks

**Prevention**:

- Monitor token count in CI
- Warn at 80% budget usage
- Auto-suggest reference.md split at 4,000 tokens
- Track version-to-version growth

### Edge Case 3: Description Too Generic

**Problem**: Skill never activates (poor description)

**Detection**: Usage analytics show 0 activations

**Fix**: Enhance description with specific keywords:

```yaml
# Before (too generic)
description: Analyzes data

# After (specific)
description: Analyzes CSV, Excel, and JSON data for patterns, outliers, and statistical insights. Use for data analysis, quality checks, or exploratory data analysis.
```

---

## Comparison: Skills vs Other Amplihack Constructs

### Skills vs Agents

**Skills**:

- Auto-discover based on description
- Token-efficient (load on-demand)
- Can restrict tools via allowed-tools
- Emphasis on user intent matching

**Agents**:

- Explicitly invoked by orchestrator
- Always loaded in agent system
- Full tool access
- Emphasis on specialization

**When to Use Each**:

- Skill: User-facing capabilities, auto-activation desired
- Agent: Internal orchestration, explicit delegation needed

### Skills vs Commands

**Skills**:

- Natural language invocation
- Auto-discovery
- Conversational interface

**Commands**:

- Slash command syntax
- Explicit parameters
- Structured invocation

**When to Use Each**:

- Skill: Conversational workflow, auto-activation
- Command: Power users, precise control, clear parameters

### Skills vs Scenarios

**Skills**:

- Lightweight documentation
- Fast activation
- Single SKILL.md (or multi-file)

**Scenarios**:

- Full production tools
- Complete with tests, docs, Makefile
- Python/JS implementations

**When to Use Each**:

- Skill: Quick capabilities, documentation-driven
- Scenario: Complex tools, code implementations, mature features

---

## Integration Examples

### Example: Skill + Command Dual Interface

Like the skill-builder itself:

**As Command** (explicit):

```bash
/amplihack:skill-builder my-skill skill "Description"
```

**As Skill** (auto-discovery):

```
User: "Help me build a new skill for parsing logs"
skill-builder: *activates automatically*
```

**Benefits**:

- Power users get control (command)
- Casual users get convenience (skill auto-activation)
- Same underlying workflow

### Example: Skill + Agent Coordination

**Skill loads** → **Delegates to agents**:

```
User: "Build a skill for API testing"

skill-builder skill activates
  ↓
Orchestrates agents:
  1. prompt-writer: Clarifies API testing requirements
  2. architect: Designs skill structure
  3. builder: Generates SKILL.md
  4. reviewer: Validates philosophy compliance
  5. tester: Creates test cases
  ↓
Delivers complete skill in .claude/skills/api-tester/
```

---

## Troubleshooting

### Issue: Skill Never Activates

**Symptoms**: Created skill doesn't load when expected

**Diagnosis**:

```python
# Check 1: Description keywords
skill_md = Path(".claude/skills/my-skill/SKILL.md").read_text()
frontmatter = parse_yaml_frontmatter(skill_md)
print(f"Description: {frontmatter['description']}")
# Does it include keywords users would say?

# Check 2: Claude Code restarted
# Skills load at startup - must restart after adding skill

# Check 3: YAML valid
import yaml
yaml.safe_load(frontmatter_text)  # Should not error
```

**Solutions**:

1. Enhance description with trigger keywords
2. Restart Claude Code
3. Fix YAML syntax errors
4. Check file location (~/.amplihack/.claude/skills/skill-name/SKILL.md)

### Issue: Token Budget Exceeded

**Symptoms**: Warning or error about token count

**Diagnosis**:

```python
import tiktoken

encoding = tiktoken.encoding_for_model("claude-sonnet-4-5")
skill_content = Path(".claude/skills/my-skill/SKILL.md").read_text()
tokens = len(encoding.encode(skill_content))
print(f"Token count: {tokens}")
```

**Solutions**:

1. Move details to reference.md
2. Extract examples to examples.md
3. Move code to scripts/
4. Remove redundant explanations
5. Use bullet points over paragraphs

### Issue: Skill Conflicts

**Symptoms**: Multiple skills activate for same request

**Diagnosis**: Descriptions overlap (both match user intent)

**Solutions**:

1. Make descriptions more specific
2. Add domain constraints
3. Use `disableModelInvocation: true` for one
4. Consolidate into single skill

---

## Best Practices from metaskills/skill-builder

**Source**: https://github.com/metaskills/skill-builder

### Opinionated Naming: Gerunds

```bash
# Preferred (action-oriented)
processing-data
analyzing-code
generating-reports

# Less preferred (object-oriented)
data-processor
code-analyzer
report-generator
```

### Technology Preferences

**Stated preferences** (you can choose differently):

- Node.js v24+ with ESM imports
- CLI-first (gh, aws, npm, jq over SDKs)
- Intention-revealing file names

### Self-Referential Teaching

The skill-builder skill itself demonstrates best practices:

- Multi-file organization (SKILL.md, reference.md, examples.md)
- Progressive disclosure (core < 5K tokens)
- Clear type distinctions (skill, agent, command, scenario)
- Comprehensive validation
- Philosophy alignment

---

## Reference Implementations

### Official Anthropic Skills

**Source**: https://github.com/anthropics/skills

**Document Skills** (source-available):

- `xlsx`: Excel workbooks with formulas, charts
- `pptx`: PowerPoint presentations
- `docx`: Word documents
- `pdf`: PDF extraction and form filling

**Creative Skills**:

- `algorithmic-art`: Generative art using p5.js
- `canvas-design`: Visual output
- `slack-gif-creator`: Optimized GIFs

**Development Skills**:

- `artifacts-builder`: React/Tailwind HTML
- `mcp-builder`: MCP server guide
- `webapp-testing`: Playwright UI testing

**Meta Skills**:

- `skill-creator`: Framework for developing skills
- `template-skill`: Starter template

### Community Skills

**obra/superpowers** (20+ skills):

- TDD workflow automation
- Debug session capture
- Collaborative problem-solving

**Patterns Worth Adopting**:

- Clear activation triggers
- Step-by-step workflows
- Error handling patterns
- Testing integration

---

## Progressive Maturity Example

Showing how a skill evolves:

### Stage 1: Experimental Skill

```markdown
---
name: experimental-parser
description: Parses log files (experimental)
maturity: experimental
---

# Log Parser (Experimental)

## Purpose

Basic log file parsing and analysis.

[Minimal implementation...]
```

### Stage 2: Beta Skill

```markdown
---
name: log-parser
description: Parses system logs (Apache, nginx, syslog) and extracts error patterns
maturity: beta
---

# Log Parser

## Purpose

Production-ready log parsing with error pattern detection.

[Enhanced implementation with validation...]
```

### Stage 3: Production Skill

```markdown
---
name: log-analyzer
description: Comprehensive log analysis for Apache, nginx, syslog formats with error detection, pattern recognition, and anomaly identification
maturity: stable
version: 2.0.0
---

# Log Analyzer

## Purpose

Enterprise-grade log analysis with ML-powered anomaly detection.

[Complete implementation + reference.md + examples.md + scripts/...]
```

---

## Updating Documentation

### When to Update This File

**Triggers for Updates**:

1. Official Anthropic documentation changes
2. New skill patterns emerge in community
3. Breaking changes to skill format
4. New best practices identified
5. Quarterly review cycle

### Update Process

1. **Check Sources**:

   ```bash
   # Visit each documentation source
   # Note changes since last update
   # Download updated examples
   ```

2. **Update Relevant Sections**:

   ```bash
   # Edit reference.md
   # Add version history entry
   # Update examples if needed
   ```

3. **Test Updated Skill**:

   ```bash
   # Create test skill with new patterns
   # Verify works correctly
   # Update examples.md with new patterns
   ```

4. **Commit Changes**:
   ```bash
   git add .claude/skills/skill-builder/
   git commit -m "docs: Update skill-builder reference documentation"
   ```

### Sync Mechanism (Manual for Now)

**Current Approach**:

- Manual quarterly reviews
- Check official docs for changes
- Update reference.md and examples.md
- Version history tracking

**Future Enhancement**:

- Automated doc scraping
- Change detection
- PR generation for updates
- CI-driven validation

---

**Maintainer**: amplihack framework
**Last Review**: 2025-11-15
**Next Review Due**: 2026-02-15 (Quarterly)
**Sources**: 10 official and community documentation links
