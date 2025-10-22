# Skills Integration Architecture

## Executive Summary

Skills provide an **auto-invocation layer** that makes amplihack's capabilities discoverable and automatic. Rather than replacing slash commands, Skills serve as intelligent triggers that:

1. Detect when specialized capabilities are needed
2. Auto-invoke appropriate agents/workflows
3. Reduce user cognitive load
4. Make expertise accessible without memorization

## Architecture

```
┌─────────────────────────────────────────────────┐
│         User Request / Context                   │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│    Skills Layer (Auto-Detection)                 │
│  - Analyzes context                              │
│  - Matches patterns                              │
│  - Triggers when appropriate                     │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│    Agent System (Existing)                       │
│  - Architect, Builder, Reviewer                  │
│  - Specialized capabilities                      │
│  - Workflow orchestration                        │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│    Slash Commands (Explicit Control)             │
│  - Complex workflows                             │
│  - User-driven processes                         │
│  - Configuration management                      │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│    Core Tools & Infrastructure                   │
└─────────────────────────────────────────────────┘
```

## Design Principles

### 1. Complementary, Not Redundant
- Skills trigger existing agents/commands
- Slash commands remain for explicit control
- No duplication of logic

### 2. Progressive Disclosure
- Start with lightweight assistance
- Escalate to deeper capabilities when needed
- Reference detailed documentation

### 3. Clear Activation Signals
- Description-based matching
- Context pattern detection
- User intent recognition

### 4. Thin Wrapper Pattern
- Skills are coordination layers
- Heavy lifting in agents/commands
- Easy to maintain and update

## Skills vs Slash Commands Decision Matrix

| Use Skill When... | Use Slash Command When... |
|-------------------|---------------------------|
| Pattern is recognizable | Requires explicit setup |
| Frequently needed | Complex multi-step workflow |
| Auto-help reduces friction | User wants full control |
| Context signals intent | Ambiguous without user input |
| Fast pattern matching | Needs configuration/preferences |

## Proposed Skills Catalog

### Category 1: Development Workflow

#### 1.1 Architecting Solutions
- **Auto-triggers**: Design questions, "how should I", architecture discussions
- **Invokes**: Architect agent
- **Value**: Ensures design-before-code philosophy

#### 1.2 Setting Up Projects
- **Auto-triggers**: New project, missing configs, pre-commit gaps
- **Invokes**: Builder agent + templates
- **Value**: Instant best practices

#### 1.3 Debugging Issues
- **Auto-triggers**: Errors, "why doesn't", troubleshooting
- **Invokes**: Systematic debugging workflow
- **Value**: Structured problem-solving

### Category 2: Code Quality

#### 2.1 Reviewing Code
- **Auto-triggers**: "review this", before PR, quality checks
- **Invokes**: Reviewer agent
- **Value**: Consistent quality gates

#### 2.2 Testing Code
- **Auto-triggers**: New features, "add tests", test gaps
- **Invokes**: Tester agent
- **Value**: Test-driven development

#### 2.3 Securing Code
- **Auto-triggers**: Auth/secrets/validation code, security concerns
- **Invokes**: Security agent
- **Value**: Proactive security

### Category 3: Research & Learning

#### 3.1 Researching Topics
- **Auto-triggers**: "how does X work", unfamiliar terms, research needed
- **Invokes**: Web search + synthesis
- **Value**: Instant context building

#### 3.2 Explaining Concepts
- **Auto-triggers**: "explain", "what is", learning requests
- **Invokes**: Progressive explanation system
- **Value**: Accessible learning

#### 3.3 Building Knowledge (Light)
- **Auto-triggers**: Documentation tasks, knowledge gaps
- **Invokes**: Simplified knowledge-builder
- **Value**: Quick documentation

### Category 4: Meta-Cognitive

#### 4.1 Analyzing Problems Deeply
- **Auto-triggers**: Complex problems, ambiguity, "I'm not sure"
- **Invokes**: Ultrathink workflow
- **Value**: Structured deep thinking

#### 4.2 Evaluating Tradeoffs
- **Auto-triggers**: "should I use X or Y", decision points
- **Invokes**: Consensus/debate workflow
- **Value**: Multi-perspective analysis

### Category 5: Collaboration

#### 5.1 Creating Pull Requests
- **Auto-triggers**: "create PR", ready to merge
- **Invokes**: Smart PR generation
- **Value**: High-quality PR descriptions

#### 5.2 Writing RFCs
- **Auto-triggers**: "design doc", major changes
- **Invokes**: RFC template + architect
- **Value**: Structured design communication

## Integration Strategy

### Phase 1: Foundation (Week 1-2)
**Goal**: Core workflow Skills that trigger most frequently

1. **Architecting Solutions** - Most critical, aligns with architect-first philosophy
2. **Reviewing Code** - High-value quality gate
3. **Researching Topics** - Frequent need, clear trigger
4. **Setting Up Projects** - Reduces setup friction

**Success Metrics**:
- Skills auto-trigger appropriately
- No false positives
- Users don't need to know slash commands exist

### Phase 2: Quality & Depth (Week 3-4)
**Goal**: Expand quality assurance and deep analysis

5. **Testing Code** - Complete quality trifecta
6. **Securing Code** - Proactive security
7. **Analyzing Problems Deeply** - Meta-cognitive support
8. **Debugging Issues** - Systematic troubleshooting

**Success Metrics**:
- Quality issues caught automatically
- Deep analysis on complex problems
- Reduced back-and-forth

### Phase 3: Collaboration (Week 5-6)
**Goal**: Team workflow automation

9. **Creating Pull Requests** - Streamline PR process
10. **Explaining Concepts** - Knowledge sharing
11. **Evaluating Tradeoffs** - Decision support
12. **Writing RFCs** - Design documentation

**Success Metrics**:
- PR quality improves
- Faster decision making
- Better documentation

## Knowledge-Builder Strategy

**Analysis**: Current knowledge-builder is powerful but heavy (270 questions, 5 files)

**Recommendation**: Dual approach

### Keep Slash Command
- **/knowledge-builder** remains for deep, comprehensive research
- User-invoked when they want full Socratic method
- Configuration and customization
- Multi-session workflows

### Create Complementary Skill
- **"Researching Topics"** skill for lightweight research
- Auto-triggers on research signals
- Uses web search + synthesis
- Can suggest upgrading to /knowledge-builder for deeper dive

**Example Flow**:
```
User: "How does vector database indexing work?"
  ↓
Skill: Researching Topics (auto-activates)
  ↓
Provides: Overview, key concepts, relevant links
  ↓
Offers: "For comprehensive deep-dive, try /knowledge-builder"
```

## Migration Recommendations

### DO NOT Migrate (Keep as Slash Commands)

1. **/knowledge-builder** - Too complex, needs setup
2. **/customize** - Configuration management
3. Multi-step workflows requiring user input
4. Workflows needing preference/state

**Rationale**: These require explicit user control and configuration

### CREATE NEW (Skills + Existing Integration)

All proposed Skills are **net new coordination layers** that:
- Invoke existing agents internally
- Add auto-detection capability
- Don't duplicate logic
- Remain thin wrappers

**Example**: "Architecting Solutions" skill invokes architect agent, doesn't reimplement it

### KEEP BOTH (Skill + Command Pairs)

Certain capabilities benefit from dual access:

| Skill (Auto) | Command (Explicit) | Use Case |
|--------------|-------------------|----------|
| Researching Topics | /knowledge-builder | Quick vs deep research |
| Reviewing Code | /review --deep | Standard vs custom review |
| Analyzing Deeply | /ultrathink | Auto-detect vs forced deep analysis |

## New Capabilities Enabled by Skills

### 1. Invisible Quality Gates
Skills can auto-check before proceeding:
- Pre-commit setup before first commit
- Architecture review before large changes
- Security scan on auth code
- Test coverage on new features

### 2. Progressive Expertise
Skills can escalate assistance:
```
Level 1: Quick answer
  ↓ (if still unclear)
Level 2: Skill auto-activates, provides structured help
  ↓ (if complex)
Level 3: Suggests slash command for deep-dive
```

### 3. Context-Aware Learning
Skills can teach by doing:
- Explain while implementing
- Show patterns in code reviews
- Reference best practices automatically

### 4. Proactive Assistance
Skills can suggest before asked:
- "This looks like a design discussion, running architect analysis..."
- "No tests detected, triggering test generation..."
- "Security concern detected, running security analysis..."

## Implementation Guidelines

### Skill Structure
```
.claude/skills/[category]/[skill-name]/
└── SKILL.md
```

### SKILL.md Template
```markdown
---
name: "Skill Name (Gerund Form)"
description: "Third-person description with clear activation signals. Describes WHEN to use."
allowed-tools: ["tool1", "tool2"]  # Optional restriction
---

# Core Instructions

[Concise instructions, <500 lines total]

## When to Activate

- Signal 1
- Signal 2
- Signal 3

## Process

1. Step 1
2. Step 2
3. Step 3

## Integration Points

- Invokes: [Agent/Command]
- References: [Documentation]
- Escalates to: [Deeper capability]

## Examples

[2-3 clear examples]

## Related

- Slash command: /command-name
- Documentation: Specs/Guide.md
```

### Tool Restrictions

Consider restricting tools for focused Skills:
```yaml
allowed-tools:
  - Read
  - Grep
  - Bash
  # Intentionally exclude Write/Edit for read-only analysis Skills
```

### Progressive Disclosure

Keep SKILL.md concise by referencing:
```markdown
For detailed methodology, see: Specs/Architecture.md
For examples, see: Examples/ArchitectureReviews.md
For templates, see: Templates/ModuleSpec.md
```

## Quality Assurance

### Testing Skills
1. **Signal Testing**: Verify activation on correct patterns
2. **Boundary Testing**: Ensure no false positives
3. **Integration Testing**: Confirm agent invocation works
4. **Escalation Testing**: Check handoff to slash commands

### Monitoring
- Track skill activation frequency
- Measure user satisfaction
- Monitor false positive rate
- Gather feedback on auto vs manual

### Iteration
- Start conservative (specific triggers)
- Expand based on patterns
- Refine descriptions based on usage
- Add new Skills based on needs

## Success Criteria

### Quantitative
- 50% reduction in need to know slash command names
- 80% of Skills trigger appropriately (no false positives)
- 30% increase in use of advanced capabilities

### Qualitative
- Users say "it just worked"
- Less need to consult documentation
- More focus on problem, less on tools
- Smoother workflow, fewer interruptions

## Risk Mitigation

### Risk: Intrusive Auto-Activation
**Mitigation**:
- Conservative triggers
- Clear activation messages
- User can decline/disable

### Risk: Confusion with Slash Commands
**Mitigation**:
- Clear documentation
- Skills reference related commands
- Complementary, not competing

### Risk: Maintenance Burden
**Mitigation**:
- Thin wrapper pattern
- Logic in agents, not Skills
- Shared documentation

### Risk: Skill Conflicts
**Mitigation**:
- Specific descriptions
- Clear boundaries
- Test interaction patterns

## Future Evolution

### Short-term (3-6 months)
- Personal Skills in `~/.claude/skills/`
- User-specific customization
- Skill composition (Skills calling Skills)

### Medium-term (6-12 months)
- Skill marketplace/library
- Team-shared Skills
- Analytics and optimization

### Long-term (12+ months)
- AI-generated Skills
- Adaptive trigger learning
- Cross-project skill transfer

## Conclusion

Skills transform amplihack from a powerful toolbox requiring knowledge into an intelligent assistant that proactively helps. By combining:

- **Skills** (auto-detection layer)
- **Agents** (specialized expertise)
- **Slash Commands** (explicit control)

We create a system that:
- Reduces cognitive load
- Makes expertise accessible
- Maintains user control
- Scales with complexity

The key is keeping Skills thin, focused, and complementary to existing capabilities.
