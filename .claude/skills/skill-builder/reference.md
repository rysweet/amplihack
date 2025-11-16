# Skill Builder Reference Documentation

This file contains comprehensive documentation about Claude Code skills, built from official sources and research. Updated: 2025-11-15

---

## Table of Contents

1. [How Claude Code Skills Work](#how-claude-code-skills-work)
2. [Skill Architecture](#skill-architecture)
3. [YAML Frontmatter Specification](#yaml-frontmatter-specification)
4. [Progressive Disclosure Pattern](#progressive-disclosure-pattern)
5. [File Structure & Organization](#file-structure--organization)
6. [Best Practices](#best-practices)
7. [Validation Guidelines](#validation-guidelines)
8. [Common Patterns](#common-patterns)
9. [Agent SDK Integration](#agent-sdk-integration)
10. [Documentation Sources](#documentation-sources)

---

## How Claude Code Skills Work

**Source**: https://code.claude.com/docs/en/skills, https://docs.claude.com/en/docs/agent-sdk/skills

### Core Concept

Skills are **prompt-based conversation and execution context modifiers** that inject specialized instructions and dynamically adjust tool permissions within scoped execution contexts.

Unlike traditional tools or function calling, skills:
- Modify Claude's behavior through instruction injection
- Load progressively (metadata → instructions → resources)
- Activate autonomously via description matching
- Scope permissions to specific tool subsets

### Three-Tier Progressive Disclosure

**Tier 1: Metadata (~100 tokens)**
- YAML frontmatter with `name` and `description`
- Pre-loaded at startup for all available skills
- Enables discovery without loading full content
- Embedded in `<available_skills>` section

**Tier 2: Core Instructions (<5,000 tokens)**
- Full SKILL.md content loaded when skill deemed relevant
- All .md files in root directory load together
- Provides complete instructions and workflows
- Token budget critical for efficiency

**Tier 3: Modular Resources (unbounded)**
- Supporting files: scripts/, templates/, data/
- Loaded on-demand during execution
- Can include any file type
- Accessed via filesystem when needed

### Autonomous Invocation

**No Algorithmic Routing** - Pure LLM reasoning for selection:

1. All skill descriptions formatted into natural language
2. Embedded in Skill tool's prompt (~15K character budget)
3. Claude's transformer decides relevance
4. No regex, keyword matching, or ML classification

**What This Means**:
- Description quality is CRITICAL for discovery
- Must include trigger keywords users naturally say
- Provide contextual usage scenarios
- Test with real user prompts

### Execution Context Modification

Skills yield a `contextModifier` callback that:
- Dynamically adjusts tool permissions during execution
- Creates scoped privilege elevation pattern
- Pre-approves tools to bypass permission prompts
- Persists only during skill execution

**Example**:
```yaml
---
name: read-only-analyzer
description: Analyzes code patterns without modifications
allowed-tools: Read, Grep, Glob  # Restricts to read-only operations
---
```

During execution:
- Only Read, Grep, Glob available
- Write, Bash blocked
- Permissions revert after skill completes

---

## Skill Architecture

**Source**: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills

### Design Philosophy

**Progressive Disclosure**: Reveal information only as needed
- Optimizes token usage
- Scales to many skills without context bloat
- Flexible through filesystem access

**Autonomous Discovery**: Let LLM decide relevance
- No external systems required
- Natural language interface
- Adaptable to new use cases

**Modular Composition**: Combine multiple skills
- Each skill focused on single responsibility
- Skills work together for complex tasks
- Easier maintenance and testing

### Key Innovations

**Dual-Message Communication**:
- Visible metadata: User-facing status in conversation
- Hidden prompt (`isMeta: true`): API-sent instructions not rendered in UI
- Solves transparency-vs-clarity tension

**Token-Efficient Discovery**:
- ~15K character budget for all skill descriptions
- Forces concise, meaningful descriptions
- Strategic prioritization required

**Scoped Permissions**:
- Skills restrict tool access for safety
- Read-only workflows prevent accidents
- Reduces risk surface area

---

## YAML Frontmatter Specification

**Source**: https://code.claude.com/docs/en/skills

### Required Fields

```yaml
---
name: skill-identifier           # Required
description: Brief capability summary  # Required
---
```

**name**:
- Lowercase alphanumeric with hyphens only
- Max 64 characters
- Pattern: `^[a-z0-9]+(-[a-z0-9]+)*$`
- Example: `analyzing-financial-data`, `pdf-form-filler`

**description**:
- Max 1,024 characters (recommend 50-200)
- Most critical field for discovery
- Must combine: capabilities + triggers + context
- Good: "Calculate financial ratios (ROE, P/E, debt-to-equity) and interpret against industry benchmarks. Use for income statements or balance sheets."
- Bad: "Helps with data" (too vague)

### Optional Fields

```yaml
---
name: skill-name
description: Capability description
allowed-tools: Read, Write, Grep  # Optional: Restrict available tools
disableModelInvocation: false     # Optional: Opt-out of auto-activation
when_to_use: Alternative trigger   # Optional: Additional trigger text
---
```

**allowed-tools**:
- Comma-separated list of tool names
- Security-critical for restricted workflows
- Example: `Read, Grep, Glob` for read-only skills

**disableModelInvocation**:
- Set to `true` to prevent automatic activation
- Skill must be explicitly requested
- Useful for experimental or dangerous skills

**when_to_use**:
- Alternative to description for activation
- Can be more verbose than description
- Provides additional context clues

### Validation Rules

From https://github.com/anthropics/claude-cookbooks/tree/main/skills:

1. **YAML Syntax**: Must parse correctly with yaml.safe_load()
2. **Required Fields**: Both name and description must be present
3. **Name Format**: Lowercase letters, numbers, hyphens only
4. **Description Length**: Between 10 and 1,024 characters
5. **No Duplicates**: Name must be unique across all skills

---

## Progressive Disclosure Pattern

**Source**: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills

### Why Progressive Disclosure

**Problem**: Skills compete for limited context window
**Solution**: Load information incrementally as needed

**Benefits**:
- Token efficiency (skills don't compete)
- Scalable (can have many skills)
- Flexible (unbounded resources via filesystem)

### Implementation Strategy

**SKILL.md** (Core - <5K tokens):
- YAML frontmatter
- Purpose statement (2-3 sentences)
- When to use (trigger scenarios)
- Basic workflow (5-10 steps)
- High-level instructions
- Reference to supporting files

**reference.md** (Details - <3K tokens each):
- API references
- Configuration options
- Error handling
- Advanced usage
- Internals/architecture
- Troubleshooting

**examples.md** (Usage - <3K tokens):
- Basic examples
- Common patterns
- Advanced scenarios
- Edge cases
- Real-world usage

**scripts/** (Executable):
- Deterministic operations
- Mathematical calculations
- Data parsing/validation
- API integrations
- Offload computation from LLM

### Loading Behavior

**All .md files in root load together** when skill activates:
- SKILL.md (always)
- reference.md, examples.md, etc.
- Enables modular documentation
- Each file focused on specific aspect

**Supporting files load on-demand**:
- Scripts execute when referenced
- Templates read when needed
- Resources accessed during processing

---

## File Structure & Organization

**Source**: https://github.com/anthropics/skills (official examples)

### Standard Skill Directory

```
skill-name/
├── SKILL.md          # REQUIRED: Primary instructions with YAML frontmatter
├── reference.md      # Optional: Detailed documentation
├── examples.md       # Optional: Usage examples and sample outputs
├── scripts/          # Optional: Executable utilities
│   ├── process.py
│   ├── validate.js
│   └── helpers.sh
├── templates/        # Optional: Reusable templates
│   ├── report.md
│   └── config.json
└── resources/        # Optional: Data files and assets
    ├── benchmarks.csv
    └── schemas.json
```

### Storage Locations

**Personal Skills** (`~/.claude/skills/`):
- Available across all projects
- User-specific workflows
- Experimental capabilities
- Installation: `git clone <repo> ~/.claude/skills/skill-name`

**Project Skills** (`.claude/skills/`):
- Shared with team via git
- Project-specific expertise
- Automatically available when team pulls updates
- Committed to version control

**Plugin Skills**:
- Bundled with Claude Code plugins
- Install automatically with parent plugin
- Managed by plugin system

### Multi-File Organization

From https://github.com/anthropics/claude-cookbooks/tree/main/skills:

**Why Split Across Files**:
- **Maintainability**: Easier to update specific sections
- **Token Efficiency**: Load only what's needed
- **Readability**: Focused, scannable documentation
- **Versioning**: Track changes to specific aspects

**When to Split**:
- SKILL.md > 5,000 tokens → Move details to reference.md
- Many examples → Separate examples.md
- Complex logic → Scripts in scripts/
- Reusable patterns → Templates in templates/

---

## Best Practices

**Source**: https://docs.claude.com/en/docs/agent-sdk/skills (Best Practices section)

### Description Quality (MOST CRITICAL)

**Effective descriptions combine specificity + triggers + context**:

✅ Good: "Analyze Excel spreadsheets, generate pivot tables, create charts. Use when working with .xlsx files or data analysis requests."

✅ Good: "Calculate financial ratios (ROE, P/E, current ratio, debt-to-equity) and interpret against industry benchmarks. Use for income statements, balance sheets, or financial analysis."

❌ Bad: "Helps with data" (too vague)
❌ Bad: "Document processor" (no trigger keywords)
❌ Bad: "Analysis tool" (lacks context)

**Description Checklist**:
- [ ] Specific capabilities listed (verbs: analyze, generate, calculate)
- [ ] Trigger keywords users naturally say
- [ ] File extensions or formats mentioned (.xlsx, .pdf, JSON)
- [ ] Use case context provided
- [ ] Under 1,024 characters (ideally 50-200)

### Single Responsibility Principle

**Focus on ONE expertise area**:

✅ Good: Separate skills for different domains
- `analyzing-financial-statements` (financial ratios only)
- `filling-pdf-forms` (PDF form processing only)
- `analyzing-excel-data` (Excel analysis only)

❌ Bad: Monolithic skill
- `document-processing` (tries to handle all document types)

**Benefits**:
- Better discovery (precise descriptions)
- Easier maintenance
- Composable (combine multiple skills)
- Clearer token budget

### Token Budget Management

**Recommended limits** (from Anthropic engineering):
- Frontmatter description: <500 chars (ideal), 1,024 max
- SKILL.md total: <5,000 tokens
- Supporting .md files: <3,000 tokens each
- Total skill context: <15,000 tokens

**Optimization strategies**:
1. Move detailed documentation to reference.md
2. Extract code to scripts/ directory
3. Use examples.md for sample outputs
4. Reference external resources by URL
5. Progressive disclosure through multiple files

### Security Safeguards

**Critical security practices**:
- ⚠️ Never hardcode API keys, credentials, or secrets
- ⚠️ Exclude sensitive data from skill documentation
- ⚠️ Sanitize all inputs in scripts
- ⚠️ Use `allowed-tools` to restrict capabilities
- ⚠️ Maintain audit trails for compliance
- ⚠️ Only install skills from trusted sources

**Example: Read-only skill**
```yaml
---
name: analyzing-code
description: Analyze code patterns and architecture
allowed-tools: Read, Grep, Glob  # Cannot modify files
---
```

---

## Validation Guidelines

### Pre-Creation Validation

**Name Validation**:
```python
import re

def validate_skill_name(name):
    """Validate skill name follows conventions"""
    pattern = r'^[a-z0-9]+(-[a-z0-9]+)*$'
    if not re.match(pattern, name):
        return False, "Name must be kebab-case"
    if len(name) < 3:
        return False, "Name too short (minimum 3 characters)"
    if len(name) > 64:
        return False, "Name too long (maximum 64 characters)"
    return True, "Name is valid"
```

**YAML Validation**:
```python
import yaml

def validate_yaml_frontmatter(content):
    """Validate YAML frontmatter in skill content"""
    try:
        parts = content.split('---', 2)
        if len(parts) < 3:
            return False, "Missing YAML frontmatter delimiters"

        frontmatter = yaml.safe_load(parts[1])

        # Check required fields
        required = ['name', 'description']
        missing = [f for f in required if f not in frontmatter]
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"

        # Validate description length
        desc_len = len(frontmatter['description'])
        if desc_len < 10:
            return False, f"Description too short ({desc_len} chars, min 10)"
        if desc_len > 1024:
            return False, f"Description too long ({desc_len} chars, max 1024)"

        return True, "YAML frontmatter is valid"

    except yaml.YAMLError as e:
        return False, f"YAML syntax error: {e}"
```

### Token Budget Validation

```python
import tiktoken

def validate_token_budget(skill_path):
    """Validate skill stays within token budget"""
    encoding = tiktoken.encoding_for_model("claude-sonnet-4-5")

    skill_md = (skill_path / "SKILL.md").read_text()
    tokens = len(encoding.encode(skill_md))

    if tokens > 20000:
        return False, f"Exceeds maximum ({tokens} tokens > 20,000)"
    if tokens > 5000:
        return True, f"Warning: High token count ({tokens} tokens > 5,000)"
    return True, f"Token budget appropriate ({tokens} tokens)"
```

### Structure Validation

**File Checklist**:
- [ ] SKILL.md exists with valid YAML frontmatter
- [ ] All required sections present (Purpose, Usage, Instructions)
- [ ] No broken links or missing references
- [ ] Scripts (if any) are executable
- [ ] Examples are clear and working
- [ ] No TODO/FIXME markers (zero-BS principle)

---

## Common Patterns

**Source**: https://github.com/anthropics/claude-cookbooks/blob/main/skills/notebooks/03_skills_custom_development.ipynb

### Pattern 1: Read-Process-Write

**Use Case**: File transformations, data processing

**Tools**: Read, Write, code_execution

**Template**:
```yaml
---
name: processing-csv-reports
description: Transform CSV data into formatted reports with calculations
allowed-tools: Read, Write, code_execution
---

# CSV Report Processor

## Purpose
Transforms raw CSV data into formatted analytical reports.

## Instructions
1. Read CSV file using Read tool
2. Parse and validate data structure
3. Execute calculations via code_execution
4. Generate formatted report
5. Write output using Write tool
```

### Pattern 2: Search-Analyze-Report

**Use Case**: Codebase introspection, pattern detection

**Tools**: Grep, Glob, Read

**Template**:
```yaml
---
name: analyzing-dependencies
description: Analyze project dependencies and identify version conflicts
allowed-tools: Grep, Glob, Read
---

# Dependency Analyzer

## Purpose
Identifies and analyzes project dependencies, detecting conflicts.

## Instructions
1. Use Glob to find dependency files (package.json, requirements.txt)
2. Use Grep to extract version information
3. Use Read for detailed dependency inspection
4. Analyze conflicts and compatibility
5. Generate report with recommendations
```

### Pattern 3: Wizard-Style Multi-Step

**Use Case**: Interactive processes requiring user confirmation

**Tools**: AskUserQuestion, Read, Write

**Template**:
```yaml
---
name: configuring-systems
description: Interactive system configuration with validation checkpoints
allowed-tools: AskUserQuestion, Read, Write
---

# System Configurator

## Purpose
Guides users through system configuration with validation.

## Instructions
1. Use AskUserQuestion for preferences
2. Read existing configuration
3. Validate choices against constraints
4. Ask for confirmation
5. Write updated configuration
```

---

## Agent SDK Integration

**Source**: https://docs.claude.com/en/docs/agent-sdk/skills

### Configuration Requirements

To use skills with the SDK, you MUST configure filesystem loading:

**Python**:
```python
from anthropic import Anthropic

options = ClaudeAgentOptions(
    cwd="/path/to/project",
    setting_sources=["user", "project"],  # CRITICAL: Enables skill loading
    allowed_tools=["Skill", "Read", "Write", "Bash"]  # Must include "Skill"
)

async for message in query(prompt="Help process this PDF", options=options):
    print(message)
```

**TypeScript**:
```typescript
const options = {
  cwd: "/path/to/project",
  settingSources: ['user', 'project'],  // CRITICAL
  allowedTools: ['Skill', 'Read', 'Write', 'Bash']
};
```

### Common Pitfall

**Most common SDK issue**: Not configuring `setting_sources`/`settingSources`

Without this, the SDK doesn't load any filesystem settings including skills.

### Tool Restrictions

**Claude Code vs SDK**:
- In Claude Code CLI: `allowed-tools` in YAML frontmatter restricts tools
- In SDK: Tool access controlled by `allowedTools` option only
- YAML `allowed-tools` has no effect in SDK applications

---

## Documentation Sources

### Official Anthropic Documentation

1. **Claude Code Skills**: https://code.claude.com/docs/en/skills
   - Primary reference for CLI skills
   - File structure and organization
   - Discovery and invocation

2. **Agent SDK Skills**: https://docs.claude.com/en/docs/agent-sdk/skills
   - SDK-specific configuration
   - setting_sources requirement
   - TypeScript/Python integration

3. **Agent Skills Engineering Blog**: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
   - Architecture and design philosophy
   - Progressive disclosure pattern
   - Autonomous invocation model
   - Execution context modification

4. **Claude Cookbooks**: https://github.com/anthropics/claude-cookbooks/tree/main/skills
   - Three progressive Jupyter notebooks
   - Financial analysis examples
   - Custom skill development tutorial
   - Sample data and templates

5. **Anthropic Skills Repository**: https://github.com/anthropics/skills
   - 14 official skill examples
   - Source-available document skills
   - Meta skills (skill-creator, template-skill)
   - Best practice implementations

### Community Resources

6. **metaskills/skill-builder**: https://github.com/metaskills/skill-builder
   - Meta-skill for creating skills
   - Opinionated guidance (gerund naming, Node.js, CLI-first)
   - Self-referential teaching approach
   - Excellent progressive scaffolding

7. **obra/superpowers**: https://github.com/obra/superpowers
   - 20+ battle-tested skills
   - TDD, debugging, collaboration patterns
   - Production-proven implementations

8. **Awesome Claude Skills Collections**:
   - travisvn/awesome-claude-skills
   - ComposioHQ/awesome-claude-skills
   - BehiSecc/awesome-claude-skills

### Deep Dives

9. **First Principles Analysis**: https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/
   - Architectural decisions explained
   - Progressive disclosure pattern deep-dive
   - Dual-message communication model
   - Execution context modification

10. **Simon Willison Blog**: https://simonwillison.net/2025/Oct/16/claude-skills/
    - "Skills are maybe a bigger deal than MCP"
    - Comparison with other systems
    - Practical implications

---

## Skill Builder Meta-Documentation

### How to Keep This Updated

**Manual Sync Process**:
1. Check official docs quarterly: https://code.claude.com/docs/en/skills
2. Review Agent SDK changes: https://docs.claude.com/en/docs/agent-sdk/skills
3. Monitor Anthropic engineering blog for updates
4. Track community skill examples for new patterns
5. Update this file when changes detected

**Automated Sync** (Future Enhancement):
- Could use web scraping to detect doc changes
- Compare current content vs source
- Flag outdated sections
- Generate update PRs

### Version History

**v1.0.0** (2025-11-15):
- Initial comprehensive research compilation
- 10 primary documentation sources
- All core patterns documented
- Agent SDK integration included
- Best practices from official guides

**Update Protocol**:
When official documentation changes:
1. Note change in version history
2. Update relevant section
3. Increment version number
4. Add changelog entry

---

## Token Budget Optimization Tips

**From Anthropic Engineering**:

1. **Defer to Scripts**: Offload deterministic operations
   - Sorting algorithms → Python/JS scripts
   - Mathematical calculations → code_execution
   - Data parsing → dedicated parsers
   - API calls → script wrappers

2. **Use External References**: Link instead of embedding
   - Industry benchmarks → URL references
   - Long examples → examples.md
   - API docs → external links
   - Detailed specs → reference.md

3. **Semantic Compression**: Say more with less
   - Use bullet points over paragraphs
   - Prefer concise examples
   - Remove redundant explanations
   - Consolidate similar sections

4. **Progressive Disclosure**: Structure strategically
   - SKILL.md: Core workflow only
   - reference.md: Deep details
   - examples.md: Usage patterns
   - Scripts: Implementation logic

---

**Last Updated**: 2025-11-15
**Maintainer**: amplihack framework
**Sources**: 10 official and community references
