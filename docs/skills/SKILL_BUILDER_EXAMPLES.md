# Skill Builder Command - Usage Examples

This document provides practical examples of using the `/amplihack:skill-builder` command.

## Quick Start

```bash
/amplihack:skill-builder <skill-name> <skill-type> <description>
```

**Skill Types**: `skill`, `agent`, `command`, `scenario`

## Example 1: Creating a Claude Code Skill (Auto-Discovery)

Create an auto-discoverable skill that loads when Claude detects relevance:

```bash
/amplihack:skill-builder json-validator skill "Validates JSON data against schemas with detailed error reporting and format checking"
```

**Expected Workflow:**

1. Validates arguments (name, type, description)
2. Creates todo list with 8 steps
3. Invokes prompt-writer to clarify requirements
4. Invokes architect to design skill structure with progressive disclosure
5. Invokes builder to generate SKILL.md with YAML frontmatter
6. Invokes reviewer to validate philosophy compliance
7. Validates YAML frontmatter and token budget
8. Creates directory and file at: `~/.amplihack/.claude/skills/json-validator/SKILL.md`

**Expected Output:**

- Auto-discoverable skill with keyword-rich description
- Progressive disclosure structure (SKILL.md core <5K tokens)
- Optional supporting files (reference.md, examples.md, scripts/)
- Activates automatically when user says "validate JSON" or similar
- Philosophy compliance score >85%

**How It Works After Creation:**

```
User: "Can you validate this JSON for me?"
Claude: *json-validator skill loads automatically*
        "I'll validate that JSON using schema validation..."
```

## Example 2: Creating an Agent Skill

Create a specialized agent for data transformation:

```bash
/amplihack:skill-builder data-transformer agent "Transforms data between JSON, YAML, XML, and CSV formats with schema validation"
```

**Expected Workflow:**

1. Validates arguments (name, type, description)
2. Creates todo list with 8 steps
3. Invokes prompt-writer to clarify requirements
4. Invokes architect to design skill structure
5. Invokes builder to generate skill file
6. Invokes reviewer to validate philosophy compliance
7. Validates YAML frontmatter and structure
8. Creates file at: `~/.amplihack/.claude/agents/amplihack/specialized/data-transformer.md`

**Expected Output:**

- Complete agent skill file with YAML frontmatter
- Clear responsibilities and execution instructions
- 2-3 usage examples
- Validation rules and error handling
- Philosophy compliance notes
- References to documentation

## Example 2: Creating a Command Skill

Create a slash command for dependency analysis:

```bash
/amplihack:skill-builder analyze-dependencies command "Analyzes project dependencies, identifies outdated packages, and generates security report"
```

**Expected Workflow:**

1. Validates arguments
2. Clarifies requirements (what to analyze, report format)
3. Designs command structure (arguments, options, output)
4. Generates command file with proper frontmatter
5. Reviews for philosophy compliance
6. Validates YAML and structure
7. Creates file at: `~/.amplihack/.claude/commands/amplihack/analyze-dependencies.md`

**Key Features:**

- `argument-hint` in YAML frontmatter
- Clear usage instructions with examples
- Argument parsing and validation
- Error handling and user feedback
- Integration with existing tools

## Example 3: Creating a Scenario Skill

Create a production-ready tool for code review:

```bash
/amplihack:skill-builder code-reviewer scenario "Reviews code for quality, security, performance, and best practices with detailed reports"
```

**Expected Workflow:**

1. Validates arguments
2. Clarifies requirements (what to review, criteria)
3. Designs comprehensive scenario structure
4. Generates complete scenario with directory structure
5. Reviews for production readiness
6. Validates all components
7. Creates directory: `~/.amplihack/.claude/scenarios/code-reviewer/`
   - `SKILL.md` - Main skill definition
   - `README.md` - User-facing documentation
   - `tool.py` - Implementation placeholder
   - `tests/` - Test directory structure
   - `examples/` - Usage examples

**Maturity Path:**

- Starts as `experimental`
- Graduates to `beta` after 2-3 successful uses
- Reaches `stable` after 1+ week of stability

## Example 4: Simple Agent (Minimal Complexity)

Create a simple formatter agent:

```bash
/amplihack:skill-builder json-formatter agent "Formats JSON with configurable indentation and sorting"
```

**Complexity Assessment:**

- Scope: Simple (single purpose)
- Implementation: Straightforward
- Token Budget: ~3,000 (recommended for simple skills)

**Generated Structure:**

- Basic YAML frontmatter
- Clear purpose statement
- Simple usage instructions
- 2-3 examples
- Minimal validation rules

## Example 5: Complex Scenario (High Complexity)

Create a comprehensive system analysis tool:

```bash
/amplihack:skill-builder system-analyzer scenario "Analyzes entire codebase for architecture patterns, dependencies, security issues, performance bottlenecks, and generates comprehensive report with recommendations"
```

**Complexity Assessment:**

- Scope: Complex (multi-system analysis)
- Implementation: Advanced (multiple integrations)
- Token Budget: ~8,000 (recommended for complex skills)

**Generated Structure:**

- Comprehensive YAML frontmatter with dependencies
- Detailed purpose and responsibilities
- Multiple usage modes (quick, standard, deep)
- Extensive examples (5-7 scenarios)
- Advanced validation and error handling
- Integration points with multiple systems
- Philosophy compliance checks

## Validation Examples

### Valid Skill Names ✅

- `data-transformer`
- `code-reviewer`
- `api-client`
- `json-formatter`
- `system-analyzer`

### Invalid Skill Names ❌

- `DataTransformer` (camelCase not allowed)
- `data_transformer` (underscores not allowed)
- `data transformer` (spaces not allowed)
- `dt` (too short, min 3 chars)
- `DataTransformerWithVeryLongNameThatExceedsMaxLength` (too long, max 50 chars)

### Valid Skill Types ✅

- `agent`
- `command`
- `scenario`
- `AGENT` (normalized to lowercase)
- `Command` (normalized to lowercase)

### Invalid Skill Types ❌

- `tool` (not a recognized type)
- `utility` (not a recognized type)
- `helper` (not a recognized type)

### Valid Descriptions ✅

- "Transforms data between formats" (clear and concise)
- "Analyzes code for security vulnerabilities and generates report" (specific and detailed)
- "Formats JSON with customizable options" (simple and direct)

### Invalid Descriptions ❌

- "Does stuff" (too vague, length < 10)
- "Transform" (too short, not descriptive)
- "A comprehensive multi-system integrated super-advanced tool that does everything you could possibly imagine with extensive features and capabilities beyond imagination..." (too long, length > 200)

## Testing Your Generated Skills

### For Agent Skills

Test by invoking the agent from another command or agent:

```markdown
**Task for {skill-name}:**

{Provide test input matching the agent's contract}

Expected:

- {Expected output 1}
- {Expected output 2}
```

### For Command Skills

Test by invoking the slash command:

```bash
/{skill-name} {test-arguments}
```

Verify:

- Arguments are parsed correctly
- Validation works as expected
- Output is formatted properly
- Error handling works for invalid inputs

### For Scenario Skills

Test by running through Makefile (once integrated):

```bash
make {skill-name} TARGET={test-target}
```

Verify:

- Tool executes successfully
- Output meets expectations
- Tests pass (if test suite created)
- Documentation is clear and accurate

## Common Issues and Solutions

### Issue: "Invalid skill name"

**Cause**: Name doesn't follow kebab-case convention
**Solution**: Use lowercase letters, numbers, and hyphens only

### Issue: "Missing required field in YAML"

**Cause**: Generated skill missing name, description, or version
**Solution**: Builder agent should always include these; review and regenerate

### Issue: "Token budget too high"

**Cause**: Skill is too complex or has excessive documentation
**Solution**: Simplify scope, break into multiple skills, or optimize documentation

### Issue: "Philosophy compliance failed"

**Cause**: Generated skill contains stubs, TODOs, or placeholders
**Solution**: Reviewer catches these; builder regenerates with complete implementation

### Issue: "File already exists"

**Cause**: Skill with same name already exists
**Solution**: Choose different name or remove existing file first

## Advanced Usage

### Creating Related Skills

Build a family of related skills:

```bash
# 1. Core transformer agent
/amplihack:skill-builder data-transformer agent "Core data transformation engine"

# 2. JSON-specific command
/amplihack:skill-builder json-transform command "Transform JSON files using data-transformer agent"

# 3. Full scenario tool
/amplihack:skill-builder batch-transform scenario "Batch transform multiple files with progress tracking"
```

### Iterating on Skills

If first generation isn't perfect:

```bash
# 1. Review the generated skill
# 2. Identify specific improvements
# 3. Re-run with refined description

/amplihack:skill-builder data-transformer agent "Transforms data between JSON, YAML, XML formats with schema validation, error recovery, and detailed logging"
```

### Integration with Workflow

Use generated skills in your workflow:

```bash
# 1. Create the skill
/amplihack:skill-builder api-client agent "HTTP client with retry logic and error handling"

# 2. Use in /ultrathink workflow
/ultrathink "Implement new API endpoint using api-client agent"

# 3. Agent orchestration will leverage new skill
```

## Best Practices

### Naming Skills

1. Use clear, descriptive names
2. Follow single responsibility principle
3. Keep names under 30 characters when possible
4. Use consistent naming patterns (e.g., `{domain}-{action}`)

### Writing Descriptions

1. Be specific about WHAT the skill does
2. Mention key features or capabilities
3. Keep under 150 characters for clarity
4. Avoid implementation details (HOW)

### Choosing Skill Type

- **Agent**: Internal automation, invoked by other agents
- **Command**: User-facing, slash command interface
- **Scenario**: Production tool, may have UI/CLI

### Token Budget Management

- Simple skills: 2,000-4,000 tokens
- Medium skills: 4,000-6,000 tokens
- Complex skills: 6,000-10,000 tokens
- Avoid exceeding 10,000 unless absolutely necessary

### Philosophy Alignment

- Always prioritize simplicity
- Include working examples, no stubs
- Make skills self-contained
- Ensure regeneratability from spec
- Document integration points clearly

## Success Criteria

A successfully generated skill should:

1. ✅ Pass all validation checks (name, type, YAML, structure)
2. ✅ Achieve >85% philosophy compliance score
3. ✅ Include 2-3 concrete usage examples
4. ✅ Have clear instructions for execution
5. ✅ Be immediately usable without editing
6. ✅ Include proper error handling
7. ✅ Reference relevant documentation
8. ✅ Stay within recommended token budget

## Next Steps After Creation

1. **Review**: Read the generated skill file
2. **Test**: Try using the skill with sample inputs
3. **Iterate**: Refine if needed by regenerating
4. **Integrate**: Use in your workflow or commands
5. **Document**: Add to project documentation
6. **Share**: Contribute to team's skill library

## Getting Help

If you encounter issues:

1. Check this examples file
2. Review the main command documentation
3. Examine similar existing skills
4. Test with simpler examples first
5. Validate arguments before running
6. Check agent logs for detailed errors

## Contributing

To improve the skill builder:

1. Document patterns you discover
2. Share successful skill examples
3. Report issues or edge cases
4. Suggest template improvements
5. Add new validation rules

---

**Last Updated**: 2025-11-15
**Version**: 1.0.0
**Status**: Phase 1 Complete
