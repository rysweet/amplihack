# Amplihack Tutorials

**Learn amplihack through structured, hands-on tutorials**

---

## Available Tutorials

### 🎓 [Amplihack Tutorial](amplihack-tutorial.md)

Comprehensive guide from basics to advanced topics. 60-90 minutes of hands-on learning with progressive disclosure.

**Topics Covered**:
- First workflow execution
- All 8 workflow types
- Prompting techniques
- Autonomous work (auto mode, lock mode)
- Goal-seeking agents
- Advanced features (skills, hooks, memory)

**Start Learning**:
```
"Start the amplihack tutorial"
```

---

## Platform-Specific Quick Starts

### Claude Code / Amplifier

```bash
# Start the tutorial
Task(subagent_type="guide", prompt="Start tutorial")

# Jump to specific section
Task(subagent_type="guide", prompt="Section 3: Workflows")

# Get help
Task(subagent_type="guide", prompt="Help with auto mode")
```

### GitHub Copilot CLI

```bash
# Start the tutorial
gh copilot explain "I want to learn amplihack with the tutorial"

# Get workflow help
gh copilot explain "Explain amplihack workflows"
```

### OpenAI Codex / RustyClawd

```bash
# Start with basics
"Explain amplihack and how to use it"

# Learn specific topics
"How do I use amplihack auto mode?"
```

---

## Tutorial Features

### Progressive Disclosure

Content adapts to your skill level:
- **[BEGINNER]** - Detailed explanations
- **[INTERMEDIATE]** - Practical applications
- **[ADVANCED]** - Deep technical details

### Interactive Navigation

Jump between sections:
- "Section 2" - First Workflow
- "Section 5" - Continuous Work
- "Menu" - Show all sections
- "Continue" - Next section

### Hands-On Exercises

Try real examples:
- Execute workflows
- Create goal agents
- Use auto mode
- Customize settings

### Platform Support

Examples for all platforms:
- Claude Code
- Amplifier
- GitHub Copilot CLI
- OpenAI Codex
- RustyClawd

---

## Learning Paths

### Beginner (90 minutes)

**Goal**: Understand basics and run first workflow

**Path**: Section 1 → 2 → 3 → 4

**Outcome**: Execute default workflow, write good prompts

### Intermediate (60 minutes)

**Goal**: Master workflows and autonomous execution

**Path**: Section 2 → 3 → 5

**Outcome**: Choose right workflows, use auto mode

### Advanced (60 minutes)

**Goal**: Build custom solutions

**Path**: Section 3 → 6 → 7

**Outcome**: Create goal agents, customize amplihack

---

## Additional Resources

### Documentation

- [Command Selection Guide](../commands/COMMAND_SELECTION_GUIDE.md)
- [Auto Mode Guide](../AUTO_MODE.md)
- [DDD Guide](../document_driven_development/README.md)
- [Goal Agent Generator Guide](../GOAL_AGENT_GENERATOR_GUIDE.md)

### Examples

- [Scenario Tools](../../.claude/scenarios/)
- [Agent Library](../../.claude/agents/amplihack/)
- [Skills Library](../../.claude/skills/)

### Community

- [GitHub Repository](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding)
- [Issue Tracker](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues)
- [Discussions](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/discussions)

---

## Troubleshooting

### Tutorial Won't Start

**Solution**: Ensure amplihack installed and environment configured
```bash
amplihack --version
echo $ANTHROPIC_API_KEY
```

### Can't Navigate Sections

**Solution**: Use explicit section names in quotes
```
"Take me to Section 3: Workflows Deep Dive"
```

### Exercises Don't Work

**Solution**: Check prerequisites and platform CLIs
- Git authentication: `gh auth status`
- API keys: Environment variables set
- Platform CLI: `which claude` or `which gh`

---

## Feedback

Help us improve tutorials:

**Report Issues**: [Tutorial Feedback](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/new?labels=tutorial-feedback)

**Suggest Topics**: What would you like to learn?

**Share Experience**: What worked well? What needs improvement?

---

**Ready to learn?** [Start the tutorial](amplihack-tutorial.md) now!

