# Amplihack Skills Catalog

Skills provide automatic invocation of amplihack's capabilities based on context. Unlike slash commands that require explicit user invocation, Skills activate automatically when patterns are detected.

## Philosophy

**Skills are thin coordination layers** that:
- Detect when specialized capabilities are needed
- Invoke appropriate agents/workflows automatically
- Reduce cognitive load on users
- Make expertise accessible without memorization

**Skills complement (not replace) slash commands**:
- Skills = Auto-detection layer
- Agents = Core expertise
- Slash Commands = Explicit control

## Skill Categories

### Development Workflow

Skills that enhance the development process:

- **[Architecting Solutions](development/architecting-solutions/SKILL.md)**
  - Auto-triggers: Design questions, "how should I", architecture discussions
  - Purpose: Ensures design-before-code philosophy
  - Invokes: Architect agent

- **[Setting Up Projects](development/setting-up-projects/SKILL.md)**
  - Auto-triggers: New projects, missing configs, pre-commit setup
  - Purpose: Instant best practices and boilerplate
  - Invokes: Builder agent + templates

- **[Debugging Issues](development/debugging-issues/SKILL.md)**
  - Auto-triggers: Errors, "why doesn't", troubleshooting
  - Purpose: Systematic problem-solving
  - Invokes: Debugging workflow

### Code Quality

Skills that maintain and improve code quality:

- **[Reviewing Code](quality/reviewing-code/SKILL.md)**
  - Auto-triggers: "review this", before PR, quality checks
  - Purpose: Consistent quality gates
  - Invokes: Reviewer agent

- **[Testing Code](quality/testing-code/SKILL.md)**
  - Auto-triggers: New features, "add tests", test gaps
  - Purpose: Test-driven development
  - Invokes: Tester agent

- **[Securing Code](quality/securing-code/SKILL.md)**
  - Auto-triggers: Auth/secrets/validation code
  - Purpose: Proactive security
  - Invokes: Security agent

### Research & Learning

Skills that accelerate learning and research:

- **[Researching Topics](research/researching-topics/SKILL.md)**
  - Auto-triggers: "how does X work", unfamiliar terms
  - Purpose: Quick research and synthesis
  - Invokes: Web search + synthesis
  - Escalates: /knowledge-builder for deep research

- **[Explaining Concepts](research/explaining-concepts/SKILL.md)**
  - Auto-triggers: "explain", "what is", learning requests
  - Purpose: Progressive explanation system
  - Invokes: Teaching methodology

- **[Building Knowledge](research/building-knowledge/SKILL.md)**
  - Auto-triggers: Documentation tasks, knowledge gaps
  - Purpose: Quick documentation (light version)
  - Escalates: /knowledge-builder for comprehensive research

### Meta-Cognitive

Skills that enhance thinking and decision-making:

- **[Analyzing Problems Deeply](meta-cognitive/analyzing-deeply/SKILL.md)**
  - Auto-triggers: Complex problems, "I'm not sure", ambiguity
  - Purpose: Structured deep thinking
  - Invokes: Ultrathink workflow

- **[Evaluating Tradeoffs](meta-cognitive/evaluating-tradeoffs/SKILL.md)**
  - Auto-triggers: "should I use X or Y", decision points
  - Purpose: Multi-perspective analysis
  - Invokes: Consensus/debate workflow

### Collaboration

Skills that improve team workflow:

- **[Creating Pull Requests](collaboration/creating-pull-requests/SKILL.md)**
  - Auto-triggers: "create PR", ready to merge
  - Purpose: High-quality PR descriptions
  - Invokes: Smart PR generation

- **[Writing RFCs](collaboration/writing-rfcs/SKILL.md)**
  - Auto-triggers: "design doc", major changes
  - Purpose: Structured design communication
  - Invokes: RFC template + architect

## Implementation Status

### Phase 1: Foundation (Implemented)
Core workflow Skills that trigger most frequently:

- ✅ Architecting Solutions
- ✅ Reviewing Code
- ✅ Researching Topics
- ✅ Analyzing Problems Deeply

### Phase 2: Quality & Depth (In Progress)
Expand quality assurance and deep analysis:

- ✅ Testing Code
- ✅ Setting Up Projects
- ⏳ Securing Code
- ⏳ Debugging Issues

### Phase 3: Collaboration (Planned)
Team workflow automation:

- ✅ Creating Pull Requests
- ⏳ Explaining Concepts
- ⏳ Evaluating Tradeoffs
- ⏳ Writing RFCs
- ⏳ Building Knowledge

## How Skills Work

### Auto-Activation

Skills activate based on their `description` field in YAML frontmatter:

```yaml
---
name: "Skill Name"
description: "Describes what the skill does and WHEN it should activate. Should include clear trigger signals."
---
```

The Claude Code model reads descriptions and automatically invokes Skills when context matches.

### Trigger Signals

Good descriptions include specific phrases that signal activation:

- "Activates when user asks..."
- "Triggers on questions like..."
- "When encountering..."
- "Before creating..."

Example:
```yaml
description: "Performs code review. Activates when user requests review, before creating PRs, or when code changes are ready."
```

### Tool Restrictions

Skills can restrict which tools they access using `allowed-tools`:

```yaml
---
name: "Read-Only Analysis"
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---
```

Useful for:
- Security (read-only skills can't modify code)
- Focus (limit to relevant tools)
- Performance (fewer tool options)

### Progressive Disclosure

Keep SKILL.md files under 500 lines by referencing external docs:

```markdown
For detailed methodology, see: Specs/Architecture.md
For examples, see: Examples/ArchitectureReviews.md
For templates, see: Templates/ModuleSpec.md
```

## Skills vs Slash Commands

### Use Skills When:
- Pattern is recognizable from context
- Frequently needed capability
- Auto-activation reduces friction
- User doesn't need to know command exists

### Use Slash Commands When:
- Requires explicit user setup
- Complex multi-step workflow
- User wants full control
- Configuration/preferences needed
- Ambiguous without user input

### Both (Skill + Command Pairs)

Some capabilities benefit from dual access:

| Auto (Skill) | Explicit (Command) | When |
|--------------|-------------------|------|
| Researching Topics | /knowledge-builder | Quick vs deep research |
| Reviewing Code | /review --deep | Standard vs custom review |
| Analyzing Deeply | /ultrathink | Auto vs forced deep analysis |

## Integration with Agents

Skills are **thin wrappers** that invoke existing agents:

```
User Request
    ↓
Skill (Auto-Detection)
    ↓
Agent (Core Logic)
    ↓
Tools (Execution)
```

Example:
- **Skill**: "Architecting Solutions" detects design questions
- **Agent**: Architect agent performs actual analysis
- **Tools**: Read, Grep, etc. for implementation

**Benefits**:
- Skills add auto-detection without duplicating logic
- Agents remain single source of truth
- Easy to maintain (logic in one place)
- Skills can be added/removed without affecting agents

## Creating New Skills

### 1. Identify Need

Ask:
- Is this capability frequently needed?
- Can context signal when it's needed?
- Would auto-activation add value?
- Is there an existing agent to invoke?

### 2. Choose Category

- `development/` - Development workflow
- `quality/` - Code quality and review
- `research/` - Research and learning
- `meta-cognitive/` - Thinking and decisions
- `collaboration/` - Team workflow

### 3. Create Structure

```bash
mkdir -p .claude/skills/[category]/[skill-name]
touch .claude/skills/[category]/[skill-name]/SKILL.md
```

### 4. Write SKILL.md

Use this template:

```markdown
---
name: "Skill Name (Gerund Form)"
description: "What it does and when it activates. Include trigger signals."
allowed-tools: ["Tool1", "Tool2"]  # Optional
---

# Skill Name

Brief introduction.

## When to Activate
- Trigger signal 1
- Trigger signal 2

## Process
1. Step 1
2. Step 2

## Integration Points
- Invokes: [Agent/Command]
- Escalates To: [Deeper capability]
- References: [Documentation]

## Examples
[2-3 clear examples]

## Related
- Slash command: /command
- Documentation: Specs/Guide.md
```

### 5. Test Activation

Verify:
- Activates on intended patterns
- No false positives
- Works with existing agents
- Provides value over manual invocation

## Best Practices

### Naming
- Use gerund form: "Processing", "Analyzing", "Building"
- Be specific: "Reviewing Code" not "Code Stuff"
- Match user mental models

### Descriptions
- Third person: "Performs X when Y"
- Include clear trigger signals
- Mention what it invokes/escalates to
- Keep under 3 sentences

### Content
- Keep under 500 lines
- Reference external docs for details
- Include 2-3 examples
- Show integration points

### Tool Restrictions
- Use `allowed-tools` for focused Skills
- Read-only Skills: `["Read", "Grep", "Glob", "Bash"]`
- Write Skills: Add `["Write", "Edit"]`
- Full access: Omit field

## Monitoring and Iteration

### Track Metrics
- Activation frequency
- False positive rate
- User satisfaction
- Time saved

### Iterate Based On
- Actual usage patterns
- User feedback
- False activation cases
- Missing trigger signals

### Refine Over Time
- Update descriptions for better matching
- Add examples based on real usage
- Adjust tool restrictions
- Split/merge Skills as needed

## Examples from Real Usage

### Example 1: Architecture Discussion

```
User: "I'm building a real-time chat app. Should I use WebSockets or polling?"

→ "Architecting Solutions" skill activates
→ Invokes Architect agent
→ Provides design analysis with tradeoffs
→ Recommends WebSockets with fallback
→ Creates module specifications
```

**Value**: User didn't need to know `/architect` command exists

### Example 2: Code Review Request

```
User: "Can you review this authentication code before I commit?"

→ "Reviewing Code" skill activates
→ Invokes Reviewer agent + Security agent
→ Performs multi-level review
→ Finds timing attack vulnerability
→ Suggests fixes with examples
```

**Value**: Automatic security analysis included

### Example 3: Research Need

```
User: "What's the difference between JWT and session tokens?"

→ "Researching Topics" skill activates
→ Performs web search
→ Synthesizes key differences
→ Provides security implications
→ Offers to escalate to /knowledge-builder
```

**Value**: Quick answer with option for deep-dive

### Example 4: Ambiguous Problem

```
User: "Our API is slow but I'm not sure why."

→ "Analyzing Problems Deeply" skill activates
→ Asks clarifying questions
→ Performs systematic analysis
→ Identifies likely causes
→ Suggests diagnostic steps
```

**Value**: Structured approach to unclear problem

## Troubleshooting

### Skill Not Activating

**Possible Causes**:
- Description doesn't match user's language
- Trigger signals too specific
- Other skill matched first

**Solutions**:
- Broaden description
- Add more trigger phrases
- Test with various phrasings

### False Positives

**Possible Causes**:
- Description too broad
- Overlaps with other Skills
- Matches unintended patterns

**Solutions**:
- Narrow description
- Add exclusion criteria
- Differentiate from similar Skills

### Performance Issues

**Possible Causes**:
- Skill too complex
- Too many tool invocations
- Heavy external calls

**Solutions**:
- Simplify skill logic
- Move heavy work to agents
- Add caching where appropriate

## Documentation

- **Architecture**: See [Specs/SkillsIntegration.md](../../Specs/SkillsIntegration.md)
- **Agent System**: See [.claude/agents/](..agents/)
- **Slash Commands**: See [.claude/commands/](../commands/)
- **Claude Code Docs**: https://docs.claude.com/claude-code

## Contributing

To add a new Skill:

1. Discuss need and design
2. Create skill directory
3. Write SKILL.md following template
4. Test activation patterns
5. Document in this README
6. Update implementation status

## Questions?

- Review existing Skills for examples
- Check [Specs/SkillsIntegration.md](../../Specs/SkillsIntegration.md) for architecture
- Reference Claude Code Skills documentation

---

**Remember**: Skills make amplihack's power invisible and automatic. The best Skills are the ones users don't know they're using.
