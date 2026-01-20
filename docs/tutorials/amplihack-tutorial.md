# Amplihack Interactive Tutorial

Learn amplihack from basics to advanced topics in 60-90 minutes with the interactive guide agent.

## What You'll Learn

This comprehensive tutorial covers:

1. **Welcome & Setup** (5 min) - Core concepts and environment setup
2. **First Workflow** (10 min) - Execute your first successful workflow
3. **Workflows Deep Dive** (15 min) - All 8 workflows and when to use them
4. **Prompting Techniques** (15 min) - Write effective prompts for AI agents
5. **Continuous Work** (15 min) - Auto mode and lock mode for autonomous execution
6. **Goal Agents** (15 min) - Create custom goal-seeking agents
7. **Advanced Topics** (15 min) - Skills, hooks, memory, and power features

## Who This Tutorial Is For

- **Complete Beginners**: Never used AI coding assistants
- **Basic Users**: Used GitHub Copilot or similar tools
- **Intermediate**: Used Claude Code or Cursor regularly
- **Advanced**: Built custom agents or workflows

The tutorial adapts to your skill level with progressive disclosure.

## How to Start the Tutorial

### Option 1: Using the Guide Agent

**In Claude Code or Amplifier**:

```bash
# Invoke the guide agent directly
amplihack:guide
```

The agent will greet you and start the tutorial with a skill assessment.

### Option 2: Via Amplifier Recipe

```bash
# Use the guide recipe
amplifier --recipe guide
```

### Option 3: Manual Invocation

If you're using a different platform (Copilot, Codex, RustyClawd):

```bash
# Ask your AI assistant to load the guide agent
"Load the amplihack guide agent from .claude/agents/amplihack/core/guide.md"
```

## Tutorial Features

### Progressive Disclosure

The tutorial adjusts complexity based on your experience:

- **[BEGINNER]** tags provide extra context and explanations
- **[ADVANCED]** tags offer deep technical details
- **Platform Notes** give platform-specific instructions
- **Try It Now** exercises provide hands-on practice

### Stateless Design

No session memory required - you can:

- Pause and resume anytime
- Jump to any section directly
- Repeat sections as needed
- Skip sections you already know

### Platform Support

Works with all major AI coding platforms:

- Claude Code
- Amplifier
- GitHub Copilot CLI
- OpenAI Codex
- RustyClawd

## Navigation

### Jump to Specific Sections

During the tutorial, you can navigate freely:

```
"Section 1" - Welcome & Setup
"Section 2" - First Workflow
"Section 3" - Workflows Deep Dive
"Section 4" - Prompting Techniques
"Section 5" - Continuous Work
"Section 6" - Goal Agents
"Section 7" - Advanced Topics
"Menu" - Show all sections
"Continue" - Go to next section
```

### Skill-Specific Learning Paths

Based on your experience level:

**Beginners**: Start with Sections 1 → 2 → 3
- Learn core concepts
- Execute your first workflow
- Understand workflow types

**Intermediate**: Focus on Sections 2 → 3 → 5
- Master workflow execution
- Learn all workflow types
- Use autonomous work modes

**Advanced**: Jump to Sections 3 → 6 → 7
- Advanced workflows and fault tolerance
- Create custom goal-seeking agents
- Customize with skills, hooks, and memory

## Expected Outcomes

After completing this tutorial, you will be able to:

✅ Execute the default 22-step workflow for features and bugs
✅ Choose the right workflow for any task (Q&A, default, investigation, auto, etc.)
✅ Write effective prompts that get quality results
✅ Use auto mode for autonomous multi-turn execution
✅ Create and run custom goal-seeking agents
✅ Leverage skills, hooks, and memory systems
✅ Customize amplihack for your specific needs
✅ Integrate amplihack into your daily development workflow

## Prerequisites

Before starting the tutorial, ensure you have:

- **amplihack installed**: `pip install amplihack`
- **Platform CLI available**: `claude`, `gh copilot`, `amplifier`, etc.
- **API key configured**: `ANTHROPIC_API_KEY` or equivalent

See [Prerequisites Guide](../PREREQUISITES.md) for detailed setup instructions.

## Tutorial Structure

### Section 1: Welcome & Setup (5 minutes)

**Topics**:
- What amplihack is and why it exists
- Core philosophy: ruthless simplicity, modular design, zero-BS
- Environment verification
- Tutorial navigation

**Hands-On**: Quick environment check

### Section 2: First Workflow (10 minutes)

**Topics**:
- The default 22-step workflow
- Workflow phases: Requirements → Design → Implementation → Testing → PR → Merge
- Agent orchestration in action

**Hands-On**: Execute a simple "Hello World" workflow from start to finish

### Section 3: Workflows Deep Dive (15 minutes)

**Topics**:
- All 8 workflows: Q&A, Default, Investigation, Auto, Consensus, Debate, N-Version, Cascade
- Workflow selection framework
- Document-Driven Development (DDD)
- Fault-tolerant workflows for critical code

**Hands-On**: Understand when to use each workflow type

### Section 4: Prompting Techniques (15 minutes)

**Topics**:
- Anatomy of a great prompt: Objective, Context, Constraints, Success Criteria
- Bad vs good prompt examples
- Platform-specific prompting patterns
- Common mistakes and how to avoid them

**Hands-On**: Practice writing effective prompts

### Section 5: Continuous Work (15 minutes)

**Topics**:
- Auto mode for multi-turn autonomous execution
- Lock mode for manual control
- Injecting instructions mid-session with `--append`
- Monitoring and controlling autonomous agents

**Hands-On**: Run an auto mode session, monitor logs, inject requirements

### Section 6: Goal Agents (15 minutes)

**Topics**:
- What goal-seeking agents are
- Creating agents from prompts with `amplihack new`
- Running and monitoring goal agents
- Goal agents vs workflows

**Hands-On**: Create and run a custom goal agent

### Section 7: Advanced Topics (15 minutes)

**Topics**:
- Skills system (74 capabilities)
- Hooks for customization
- Memory systems (5-type and Neo4j)
- Power features (DDD, fault-tolerant workflows)
- Customization and extension

**Hands-On**: Explore skills, customize user preferences

## Troubleshooting

### "Cannot find guide agent"

**Solution**: Ensure amplihack is installed correctly:

```bash
pip install amplihack --upgrade
```

The guide agent is located at `.claude/agents/amplihack/core/guide.md`.

### "Agent doesn't respond"

**Solution**: Check that your AI platform is running:

```bash
# For Claude Code
claude --version

# For Amplifier
amplifier --version

# For GitHub Copilot
gh copilot --version
```

### "Tutorial sections don't load"

**Solution**: The guide agent should be stateless. Try restarting:

```bash
# Re-invoke the guide agent
amplihack:guide

# Or explicitly request a section
"Go to Section 2 of the amplihack tutorial"
```

### Platform-specific issues

**Claude Code**: Ensure Claude Code is up to date
**Amplifier**: Check that the amplifier bundle is installed
**Copilot**: Verify `gh` CLI is authenticated
**Codex/RustyClawd**: Ensure API keys are configured

## After the Tutorial

### Next Steps

1. **Practice**: Try the default workflow on a real task from your backlog
2. **Explore**: Browse `.claude/agents/` and `.claude/skills/` directories
3. **Customize**: Set user preferences with `/amplihack:customize`
4. **Integrate**: Add amplihack to your daily workflow
5. **Share**: Create goal agents for common team tasks

### Additional Resources

- [Documentation Index](../index.md) - Complete amplihack documentation
- [Command Selection Guide](../commands/COMMAND_SELECTION_GUIDE.md) - Choose the right command
- [Auto Mode Guide](../AUTO_MODE.md) - Deep dive into autonomous execution
- [DDD Guide](../document_driven_development/README.md) - Document-driven development
- [Goal Agent Guide](../GOAL_AGENT_GENERATOR_GUIDE.md) - Create custom agents

### Community

- [GitHub Repository](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding)
- [Issue Tracker](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues)
- [Documentation Site](https://rysweet.github.io/amplihack/)

## Feedback

Help improve this tutorial:

- Report issues or suggestions on [GitHub Issues](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues)
- Tag with `documentation` and `tutorial`
- Include your skill level and platform

---

**Ready to start learning?** Invoke the guide agent and begin your amplihack journey!

```bash
amplihack:guide
```
