# Investigation Documentation

This directory contains persistent documentation generated from investigation tasks.

## Purpose

After completing code investigations, architecture analysis, or system explorations, the knowledge-archaeologist agent can generate documentation here to preserve findings for future sessions.

## Benefits

- **Knowledge Preservation**: Investigation insights aren't lost in chat history
- **Faster Onboarding**: New team members can read past investigations
- **No Repeated Work**: Avoid re-investigating the same systems
- **Organic Growth**: Documentation grows naturally from actual investigations
- **Searchability**: Easy to find and reference previous work

## File Naming Convention

Documentation files follow this naming pattern:

**Format**: `[TYPE]_[TOPIC].md`

**Types**:

- `ARCHITECTURE_*` - System architecture investigations
- `INVESTIGATION_*` - General investigations

**Examples**:

- `ARCHITECTURE_NEO4J_MEMORY_SYSTEM.md`
- `INVESTIGATION_HOOK_EXECUTION_ORDER.md`
- `ARCHITECTURE_USER_PREFERENCES_INTEGRATION.md`

## How Documentation is Generated

### Automatic Offer (via knowledge-archaeologist agent)

When you complete an investigation using the INVESTIGATION_WORKFLOW.md:

1. Agent completes investigation
2. Agent prompts: "Shall I create a permanent record of this investigation?"
3. You choose Yes or No
4. If Yes: Documentation is generated using standardized templates
5. File saved here with appropriate naming

### Templates Used

Documentation is generated from templates in `.claude/templates/`:

- `investigation-doc-template.md` - General investigations
- `architecture-doc-template.md` - Architecture investigations

See `.claude/templates/README.md` for template details.

## Documentation Structure

All generated documentation includes:

1. **Findings Summary** - Executive summary of discoveries
2. **Architecture Diagrams** - Visual representations (mermaid format)
3. **Key Files** - Table of important files and their roles
4. **System Integration** - How components work together
5. **Verification Steps** - Steps to verify understanding
6. **Examples** - Practical examples demonstrating findings

Architecture documentation also includes:

- **Design Decisions** - Architectural choices and rationale
- **Future Considerations** - Potential improvements

## Examples

This directory contains example documentation files:

- `ARCHITECTURE_EXAMPLE.md` - Example of architecture documentation
- `INVESTIGATION_EXAMPLE.md` - Example of investigation documentation

These examples demonstrate the expected structure and content quality.

## Using Documentation

### Finding Documentation

```bash
# List all architecture documentation
ls .claude/docs/ARCHITECTURE_*.md

# List all investigation documentation
ls .claude/docs/INVESTIGATION_*.md

# Search for specific topic
ls .claude/docs/*TOPIC*.md

# Search content
grep -r "search term" .claude/docs/
```

### Reading Documentation

Simply open the markdown files in your editor or viewer. They contain:

- Clear findings and explanations
- Mermaid diagrams (render with markdown preview)
- File tables with links
- Practical examples
- Verification procedures

### Referencing Documentation

When discussing a system, reference existing documentation:

```markdown
See `.claude/docs/ARCHITECTURE_USER_PREFERENCES_HOOKS.md` for details on how
user preferences integrate with the hooks system.
```

## Best Practices

### When to Generate Documentation

**Always consider** documenting:

- Architecture investigations
- Complex system integrations
- Non-obvious design patterns
- Multi-file investigations
- Significant discoveries

**Optional** for:

- Simple single-file analysis
- Quick bug checks
- Trivial investigations

### Documentation Quality

Good documentation should:

- Have clear, concise findings summary
- Include diagrams when helpful
- List all key files analyzed
- Explain how pieces fit together
- Provide verification steps
- Include working examples

### Keeping Documentation Current

- Update documentation when systems change significantly
- Add references to related documentation
- Note deprecated information
- Archive outdated documentation (move to subdirectory)

## Related Resources

- `.claude/workflow/INVESTIGATION_WORKFLOW.md` - Investigation workflow with documentation step
- `.claude/templates/README.md` - Template usage guide
- `.claude/agents/amplihack/specialized/knowledge-archaeologist.md` - Agent that generates documentation

## Contributing Documentation

You can manually create documentation following the templates:

1. Copy appropriate template from `.claude/templates/`
2. Fill in all sections with investigation findings
3. Save with naming convention: `[TYPE]_[TOPIC].md`
4. Place in this directory

Or use the INVESTIGATION_WORKFLOW.md and let the knowledge-archaeologist agent generate it automatically.

---

**Last Updated**: 2025-11-05
**Documentation Count**: See `ls *.md | wc -l` for current count
