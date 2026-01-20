# Investigation Documentation Templates

This directory contains standardized templates for capturing investigation findings in persistent documentation.

## Purpose

After completing investigations (code analysis, architecture reviews, system explorations), the knowledge-archaeologist agent can generate documentation using these templates to preserve findings for future sessions.

## Template Types

### 1. investigation-doc-template.md

**Use for:**

- General code investigations
- Bug analysis and root cause investigations
- Performance investigations
- Feature explorations
- System behavior analysis

**Sections:**

- Findings Summary
- Architecture Diagrams (optional)
- Key Files
- System Integration
- Verification Steps
- Examples
- Knowledge Gaps
- Related Documentation

### 2. architecture-doc-template.md

**Use for:**

- System architecture analysis
- Component relationship mapping
- Integration flow investigations
- Design pattern documentation
- Architectural decision records

**Sections:**

- Findings Summary
- Architecture Diagrams (overview, relationships, data flow)
- Key Files
- System Integration (with dependencies and patterns)
- Verification Steps
- Examples
- Design Decisions
- Future Considerations
- Related Documentation

## Usage

### Automatic Generation (via knowledge-archaeologist agent)

When completing an investigation, the knowledge-archaeologist agent will:

1. Prompt: "Shall I create a permanent record of this investigation in the ship's logs (documentation)?"
2. If accepted, select appropriate template based on investigation type
3. Populate template with investigation findings
4. Save to `.claude/docs/[TYPE]_[TOPIC].md`

### Manual Generation

You can manually create documentation using these templates:

1. Copy the appropriate template
2. Replace all `[PLACEHOLDER]` sections with actual content
3. Save to `.claude/docs/` with naming convention:
   - `ARCHITECTURE_[TOPIC].md` for architecture investigations
   - `INVESTIGATION_[TOPIC].md` for general investigations
4. Use UPPER_SNAKE_CASE for TOPIC (e.g., `USER_PREFERENCES_HOOKS`)

## Template Variables

Common placeholders in templates:

- `[TOPIC]`: Investigation focus (e.g., "USER_PREFERENCES_HOOKS", "MEMORY_SYSTEM")
- `[FINDINGS]`: Executive summary of discoveries
- `[DIAGRAMS]`: Mermaid diagrams (system structure, data flow, relationships)
- `[FILE_PATH]`: Absolute path to key file
- `[DESCRIPTION]`: Purpose or role explanation
- `[TIMESTAMP]`: Generation date and time

## Examples

See `.claude/docs/` directory for examples of generated documentation.

## File Naming Convention

**Format**: `[TYPE]_[TOPIC].md`

**Examples:**

- `ARCHITECTURE_NEO4J_MEMORY_SYSTEM.md`
- `INVESTIGATION_HOOK_EXECUTION_ORDER.md`
- `ARCHITECTURE_USER_PREFERENCES_INTEGRATION.md`

**Rules:**

- Use UPPER_SNAKE_CASE for visibility and consistency
- Be specific but concise in TOPIC naming
- TYPE is either `ARCHITECTURE` or `INVESTIGATION`

## Benefits

- **Knowledge Preservation**: Investigations aren't lost in chat history
- **Faster Onboarding**: New contributors can read past investigations
- **No Repeated Work**: Don't re-investigate the same systems
- **Documentation Growth**: System documentation grows organically from investigations
- **Searchability**: Easy to find and reference past investigations

## Integration

These templates integrate with:

- **INVESTIGATION_WORKFLOW.md**: Investigation workflow includes documentation step
- **knowledge-archaeologist agent**: Primary agent for doc generation
- **analyzer agent**: Source of investigation findings

## Customization

To customize templates:

1. Edit the template file directly
2. Add or remove sections as needed
3. Modify placeholder text for clarity
4. Keep the basic structure intact for consistency

Templates should remain simple markdown with clear section headers and minimal formatting complexity.
