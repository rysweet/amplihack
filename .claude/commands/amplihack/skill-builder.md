---
name: amplihack:skill-builder
version: 1.0.0
description: Build new Claude Code skills with guided workflow and agent orchestration
argument-hint: <skill-name> <skill-type> <description>
triggers:
  - "create a new skill"
  - "build a Claude Code skill"
  - "generate skill for"
invokes:
  - type: subagent
    path: .claude/agents/amplihack/specialized/prompt-writer.md
  - type: subagent
    path: .claude/agents/amplihack/core/architect.md
---

# Skill Builder Command

## Input Validation

@~/.amplihack/.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/amplihack:skill-builder <skill-name> <skill-type> <description>`

**Arguments:**

- `skill-name`: Name of the skill (kebab-case, e.g., "data-transformer")
- `skill-type`: Type of skill - one of: `agent`, `command`, `scenario`, `skill`
- `description`: Brief description of what the skill does (1-2 sentences)

**Examples:**

```bash
/amplihack:skill-builder data-transformer skill "Transforms data between different formats with validation"
/amplihack:skill-builder analyze-dependencies command "Analyzes project dependencies and generates report"
/amplihack:skill-builder code-reviewer scenario "Reviews code for quality, security, and best practices"
/amplihack:skill-builder api-client agent "Manages API client connections with retry logic"
```

## Purpose

Creates new Claude Code skills following the Amplihack framework patterns. Orchestrates multiple agents to ensure skills are:

- Properly structured with YAML frontmatter
- Philosophy-compliant (ruthless simplicity, zero-BS)
- Self-contained and regeneratable
- Documented with clear examples
- Validated for correctness

## Reference Documentation

This command implements patterns from:

- **Official Claude Code Skills**: https://code.claude.com/docs/en/skills
- **Claude Code Skills Best Practices**: https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices
- **Anthropic Agent SDK Skills**: https://docs.claude.com/en/docs/agent-sdk/skills
- **Agent Skills Blog Post**: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- **Claude Cookbooks Skills**: https://github.com/anthropics/claude-cookbooks/tree/main/skills
- **Skill Builder Reference**: https://github.com/metaskills/skill-builder

**Key Best Practices to Follow:**

- Keep SKILL.md under 500 lines (use progressive disclosure)
- Avoid deeply nested references (max 1 level deep)
- Use workflows and feedback loops for complex tasks
- Provide concrete examples with input/output pairs
- Test across Claude Haiku, Sonnet, and Opus models

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, execute the following workflow systematically:

### Step 1: Validate Input Arguments

Extract and validate the three required arguments:

```python
# Parse arguments from command invocation
skill_name = args[0]  # e.g., "data-transformer"
skill_type = args[1]  # e.g., "agent"
description = args[2] # e.g., "Transforms data between formats"
```

**Validation Rules:**

1. **skill-name**:
   - Must be kebab-case (lowercase with hyphens)
   - Length: 3-50 characters
   - Pattern: `^[a-z0-9]+(-[a-z0-9]+)*$`
   - Invalid examples: "DataTransformer", "data_transformer", "data transformer"
   - Valid examples: "data-transformer", "code-reviewer", "api-client"

2. **skill-type**:
   - Must be one of: `agent`, `command`, `scenario`, `skill`
   - Case-insensitive (normalize to lowercase)
   - Maps to output directories:
     - `skill` → `.claude/skills/{skill-name}/` (creates SKILL.md for auto-discovery)
     - `agent` → `.claude/agents/amplihack/specialized/` (creates agent .md file)
     - `command` → `.claude/commands/amplihack/` (creates command .md file)
     - `scenario` → `.claude/scenarios/{skill-name}/` (creates directory with README.md)

3. **description**:
   - Length: 10-200 characters
   - Must be clear and specific
   - Should describe WHAT the skill does, not HOW

**If validation fails:**

- Display error message explaining the issue
- Show correct usage examples
- Exit without creating files

### Step 2: Create Todo List

Use TodoWrite to create a comprehensive task list:

```markdown
- [ ] Validate input arguments
- [ ] Clarify requirements with prompt-writer agent
- [ ] Design skill structure with architect agent
- [ ] Generate skill file with builder agent
- [ ] Review for philosophy compliance with reviewer agent
- [ ] Validate YAML frontmatter and structure
- [ ] Create skill file in correct location
- [ ] Report completion with usage instructions
```

### Step 3: Requirements Clarification (prompt-writer)

**Agent**: `prompt-writer.md`

Invoke the prompt-writer agent to clarify and structure requirements:

```markdown
**Task for prompt-writer:**

Analyze this skill request and generate a structured specification:

- **Skill Name**: {skill_name}
- **Skill Type**: {skill_type}
- **Description**: {description}

Please provide:

1. Refined description (1-2 sentences, clear and specific)
2. Core responsibilities (3-5 bullet points)
3. Input/output specifications
4. Usage examples (2-3 scenarios)
5. Success criteria
6. Complexity assessment (Simple/Medium/Complex)
7. Token budget recommendation (based on complexity)

Use your template-based approach to ensure completeness.
```

**Output**: Structured specification ready for architecture design

### Step 4: Skill Architecture Design (architect)

**Agent**: `architect.md`

Invoke the architect agent to design the skill structure:

```markdown
**Task for architect:**

Design the architecture for this skill based on the specification:

{specification_from_prompt_writer}

**Skill Type**: {skill_type}

Please provide:

1. Skill structure (sections and organization)
2. YAML frontmatter fields (name, description, version, tags, etc.)
3. Required sections (Purpose, Usage, Instructions, Examples, etc.)
4. Integration points (what this skill interacts with)
5. Design decisions and rationale
6. Philosophy compliance notes

Follow the brick philosophy: self-contained, clear contracts, regeneratable.
```

**Output**: Detailed architecture specification

### Step 5: Skill Implementation (builder)

**Agent**: `builder.md`

Invoke the builder agent to generate the skill file:

```markdown
**Task for builder:**

Implement the skill file based on this architecture:

{architecture_from_architect}

**Requirements:**

- Generate complete, working skill (no stubs or placeholders)
- Include proper YAML frontmatter
- Follow the skill template structure (embedded below)
- Add 2-3 concrete usage examples
- Include clear instructions for execution
- Reference relevant documentation
- Ensure token budget is appropriate

**Output Location**: {output_path}

Use the SKILL TEMPLATE below as the foundation.
```

**Output**: Complete skill file content

### Step 6: Philosophy Review (reviewer)

**Agent**: `reviewer.md`

Invoke the reviewer agent to validate compliance:

```markdown
**Task for reviewer:**

Review this skill for philosophy compliance:

{skill_content_from_builder}

**Check for:**

1. Ruthless simplicity (no unnecessary complexity)
2. Zero-BS implementation (no stubs, placeholders, TODOs)
3. Clear contracts (inputs, outputs, side effects)
4. Self-contained (all necessary information present)
5. Regeneratable (can be rebuilt from specification)
6. Proper documentation (examples, references)
7. YAML frontmatter completeness
8. Token budget appropriateness

Provide:

- Compliance score (0-100%)
- Issues found (if any)
- Recommendations for improvement
- Approval status (approved/needs_revision)
```

**Output**: Review results with approval or revision requests

### Step 7: Validation and File Creation

After receiving reviewer approval, perform final validation:

**YAML Frontmatter Validation:**

```yaml
# Required fields for all skills
required:
  - name: string (matches skill-name argument)
  - description: string (clear, specific, 10-200 chars)
  - version: string (semver format, start with "1.0.0")

# Optional but recommended
optional:
  - tags: array[string] (categorization)
  - token_budget: integer (5000 default, warn if > 10000)
  - maturity: enum [experimental, beta, stable]
  - dependencies: array[string] (other skills or tools)
  - model: string (e.g., "inherit", "claude-sonnet-4-5")
```

**Validation Checks:**

1. **YAML Syntax**: Parse frontmatter, ensure valid YAML
2. **Required Fields**: All required fields present
3. **Field Types**: Correct types for all fields
4. **Token Budget**: Warn if > 5000, error if > 20000
5. **Name Match**: Frontmatter name matches skill-name argument
6. **Section Completeness**: All required sections present

**If validation passes:**

1. Determine output path:

   ```python
   output_paths = {
       "skill": ".claude/skills/{skill_name}/SKILL.md",
       "agent": ".claude/agents/amplihack/specialized/{skill_name}.md",
       "command": ".claude/commands/amplihack/{skill_name}.md",
       "scenario": ".claude/scenarios/{skill_name}/README.md"
   }
   output_path = output_paths[skill_type]
   ```

2. Create directories if needed (skill and scenario types create directories)

3. Write skill file using Write tool

4. Confirm creation with absolute path

**If validation fails:**

- Display specific errors
- Request builder to revise
- Re-run validation

### Step 8: Completion Report

After successful creation, provide a comprehensive report:

```markdown
## Skill Created Successfully!

**Skill Name**: {skill_name}
**Skill Type**: {skill_type}
**Location**: {absolute_path}

### Usage

For {skill_type} skills:

{usage_instructions_based_on_type}

### Next Steps

1. Review the generated skill file
2. Test the skill with a sample invocation
3. Iterate if needed using `/amplihack:skill-builder` again
4. {type_specific_next_steps}

### Skill Details

- **Token Budget**: {token_budget}
- **Maturity**: {maturity}
- **Complexity**: {complexity}
- **Version**: {version}

### Philosophy Compliance

{reviewer_compliance_summary}

---

**Reference Documentation:**

- Claude Code Skills: https://code.claude.com/docs/en/skills
- Agent SDK: https://docs.claude.com/en/docs/agent-sdk/skills
- Skill Builder: https://github.com/metaskills/skill-builder
```

## SKILL TEMPLATE

Use this template as the foundation for all generated skills:

```markdown
---
name: { skill-name }
description: { clear-description }
version: 1.0.0
tags: [{ relevant-tags }]
token_budget: { recommended-budget }
maturity: experimental
---

# {Skill Title}

## Purpose

{1-2 sentence purpose statement}

This skill provides {core-capability} for {target-use-case}.

## Input Validation

@~/.amplihack/.claude/context/AGENT_INPUT_VALIDATION.md

## Core Responsibilities

1. **{Responsibility 1}**: {Brief description}
2. **{Responsibility 2}**: {Brief description}
3. **{Responsibility 3}**: {Brief description}

## Usage

### Basic Usage

\`\`\`bash
{usage-command-or-invocation}
\`\`\`

### Arguments

- `{arg1}`: {description} (required/optional)
- `{arg2}`: {description} (required/optional)

### Options

- `{option1}`: {description} (default: {value})
- `{option2}`: {description} (default: {value})

## Instructions

### When to Use This Skill

Use this skill when:

- {Use case 1}
- {Use case 2}
- {Use case 3}

### Execution Steps

When this skill is invoked:

1. **{Step 1}**: {Description}
   - {Sub-step or detail}
   - {Sub-step or detail}

2. **{Step 2}**: {Description}
   - {Sub-step or detail}
   - {Sub-step or detail}

3. **{Step 3}**: {Description}
   - {Sub-step or detail}
   - {Sub-step or detail}

### Input Specifications

**Required Inputs:**

- `{input1}`: {type} - {description}
- `{input2}`: {type} - {description}

**Optional Inputs:**

- `{input3}`: {type} - {description} (default: {value})

### Output Specifications

**Returns:**

- `{output1}`: {type} - {description}
- `{output2}`: {type} - {description}

**Side Effects:**

- {Side effect 1 if any}
- {Side effect 2 if any}

## Examples

### Example 1: {Basic Use Case}

\`\`\`bash
{command-example-1}
\`\`\`

**Expected Output:**
\`\`\`
{output-example-1}
\`\`\`

### Example 2: {Advanced Use Case}

\`\`\`bash
{command-example-2}
\`\`\`

**Expected Output:**
\`\`\`
{output-example-2}
\`\`\`

### Example 3: {Edge Case or Complex Scenario}

\`\`\`bash
{command-example-3}
\`\`\`

**Expected Output:**
\`\`\`
{output-example-3}
\`\`\`

## Integration Points

This skill integrates with:

- **{System/Tool 1}**: {How it integrates}
- **{System/Tool 2}**: {How it integrates}
- **{System/Tool 3}**: {How it integrates}

## Error Handling

Common errors and solutions:

**Error**: {Error message or condition}
**Cause**: {What causes this error}
**Solution**: {How to resolve it}

**Error**: {Error message or condition}
**Cause**: {What causes this error}
**Solution**: {How to resolve it}

## Validation Rules

This skill validates:

1. {Validation rule 1}
2. {Validation rule 2}
3. {Validation rule 3}

## Philosophy Compliance

This skill follows Amplihack principles:

- **Ruthless Simplicity**: {How this skill stays simple}
- **Zero-BS**: {How this skill avoids placeholders and stubs}
- **Self-Contained**: {How this skill is complete and self-sufficient}
- **Regeneratable**: {How this skill can be rebuilt from spec}

## References

- **Official Documentation**: https://code.claude.com/docs/en/skills
- **Agent SDK Skills**: https://docs.claude.com/en/docs/agent-sdk/skills
- **Related Skills**: {List related skills in the framework}
- **Source Inspiration**: {If based on external reference}

## Maintenance

**Version History:**

- v1.0.0 (Initial): {Brief description of initial implementation}

**Future Enhancements:**

- {Potential future improvement 1}
- {Potential future improvement 2}

**Known Limitations:**

- {Limitation 1}
- {Limitation 2}
```

## Type-Specific Guidance

### For Claude Code Skills (`skill`)

**Location**: `.claude/skills/{skill-name}/SKILL.md`

**Purpose**: Auto-discoverable skills that Claude loads based on description matching

**Additional Considerations:**

- Skills auto-activate when description matches user intent
- Description MUST include trigger keywords users would say
- **TARGET: Keep SKILL.md at 1,000-2,000 tokens** (not 5,000!)
- **MANDATORY**: Use progressive disclosure with supporting files (reference.md, examples.md, patterns.md)
- **MANDATORY**: Include navigation guide when using supporting documents (see template below)
- Can include scripts/ directory for executable code
- Skills are token-efficient (load only when needed)

**Progressive Disclosure Philosophy:**

- SKILL.md = Quick start and core workflows only
- Supporting files = Deep dives, API details, advanced patterns
- Split based on CONTENT (beginner vs expert), not just token count
- Reference example: agent-sdk skill (514-line SKILL.md with comprehensive supporting docs)

**YAML Frontmatter Requirements:**

```yaml
---
name: skill-name
description: Keyword-rich description for auto-discovery (optimized for trigger words)
version: 1.0.0
token_budget: 2000 # Target for SKILL.md only (1,000-2,000 recommended)
source_urls: # MANDATORY if skill is based on external documentation
  - https://docs.example.com/main-source
  - https://github.com/org/repo/reference
---
```

**Description Best Practices:**

- Include action verbs: "analyze", "generate", "transform", "validate"
- Mention file types: ".xlsx", ".pdf", "JSON", "YAML"
- Add domain keywords: "financial", "testing", "documentation"
- Specify use cases: "Use when analyzing test coverage", "Use for data transformation"
- Length: 50-200 characters (not too short, not too long)

**Source URLs:**

- MUST include if skill is based on external documentation (official docs, GitHub repos, blog posts)
- Provides drift detection capability and attribution
- Helps users find authoritative sources for deeper information
- Good example: agent-sdk skill includes 4 official Anthropic documentation URLs
- Bad example: Omitting source URLs for skills derived from external knowledge bases

**Directory Structure:**

```
.claude/skills/{skill-name}/
├── SKILL.md           # Required: Main skill with YAML frontmatter (1,000-2,000 tokens)
├── reference.md       # Recommended: Complete API reference, detailed specs
├── examples.md        # Recommended: Working code examples, patterns
├── patterns.md        # Optional: Best practices, anti-patterns, production tips
└── scripts/           # Optional: Executable utilities
```

**Navigation Guide Template (MANDATORY for multi-file skills):**

When your skill includes supporting documents (reference.md, examples.md, patterns.md), you MUST include a navigation guide section in SKILL.md. This tells Claude when to read each file:

```markdown
## Navigation Guide

### When to Read Supporting Files

**reference.md** - Read when you need:

- Complete API reference with all methods and parameters
- Detailed configuration options and environment setup
- Comprehensive tool schema specifications
- In-depth architecture and internals documentation

**examples.md** - Read when you need:

- Working code examples for specific patterns
- Step-by-step implementation guides
- Advanced use case demonstrations
- Integration examples with existing systems

**patterns.md** - Read when you need:

- Production-ready architectural patterns
- Performance optimization techniques
- Security best practices and anti-patterns
- Common pitfalls and how to avoid them
```

**Reference Example:** See `.claude/skills/agent-sdk/SKILL.md` lines 376-408 for an excellent navigation guide implementation.

### For Agent Skills (`agent`)

**Location**: `.claude/agents/amplihack/specialized/{skill-name}.md`

**Additional Considerations:**

- Agents are invoked by other agents or commands
- Should have clear entry points and exit conditions
- Must define what they analyze, what they output
- Include decision-making criteria
- Specify when to delegate to other agents

**YAML Additions:**

```yaml
model: inherit # or specific model like "claude-sonnet-4-5"
```

### For Command Skills (`command`)

**Location**: `.claude/commands/amplihack/{skill-name}.md`

**Additional Considerations:**

- Commands are user-facing slash commands
- Should provide immediate value
- Must have clear usage examples
- Include argument validation
- Specify command syntax in frontmatter

**YAML Additions:**

```yaml
argument-hint: <required-arg> [optional-arg]
```

### For Scenario Skills (`scenario`)

**Location**: `.claude/scenarios/{skill-name}/SKILL.md`

**Additional Considerations:**

- Scenarios are production-ready tools
- Should have comprehensive documentation
- Must include test coverage plan
- Create directory structure: `{skill-name}/`
- Consider graduation from experimental

**YAML Additions:**

```yaml
maturity: experimental # or beta, stable
dependencies: [list-of-dependencies]
```

**Directory Structure:**

```
.claude/scenarios/{skill-name}/
├── SKILL.md          # Main skill definition
├── README.md         # User-facing documentation
├── tool.py           # Implementation (if applicable)
├── tests/            # Test suite
└── examples/         # Usage examples
```

---

**Implementation Status**: Phase 1 Complete
**Maturity**: Experimental
**Version**: 1.0.0
**Last Updated**: 2025-11-15
