# Amplihack Tutorial

**Comprehensive guide to mastering amplihack from basics to advanced topics**

---

## Overview

This tutorial provides a complete learning path through amplihack's capabilities, from your first workflow to building custom goal-seeking agents. Designed for 60-90 minutes of hands-on learning with progressive disclosure based on your skill level.

## How to Start the Tutorial

**Claude Code / Amplifier**:
```bash
# Invoke the guide agent
Task(subagent_type="guide", prompt="Start tutorial")
```

**In Natural Conversation**:
```
"I want to learn amplihack - take me through the tutorial"
```

The guide agent will:
1. Assess your skill level
2. Tailor explanations to your experience
3. Provide platform-specific examples
4. Walk you through 7 comprehensive sections

## What You'll Learn

### Section 1: Welcome & Setup (5 min)
- What amplihack is and why it exists
- Core philosophy: ruthless simplicity, modular design, zero-BS
- Quick environment check
- Navigation tips

### Section 2: First Workflow (10 min)
- Execute your first amplihack workflow
- Understand the 22-step default workflow
- Watch agents collaborate
- Verify successful completion

### Section 3: Workflows Deep Dive (15 min)
- All 8 workflows and when to use each
- Workflow selection framework
- Q&A, Default, Investigation, Auto modes
- Fault-tolerant workflows (N-version, Debate, Cascade)
- Document-Driven Development (DDD)

### Section 4: Prompting Techniques (15 min)
- Anatomy of a great prompt
- Structuring complex requests
- Leveraging context and constraints
- Platform-specific prompting patterns
- Common mistakes and how to avoid them

### Section 5: Continuous Work (15 min)
- Auto mode for multi-turn autonomous execution
- Lock mode for keeping agents working
- Injecting instructions mid-session
- Monitoring and controlling autonomous agents

### Section 6: Goal Agents (15 min)
- What goal-seeking agents are
- Creating agents from simple prompts
- Running and monitoring goal agents
- When to use goal agents vs workflows

### Section 7: Advanced Topics (15 min)
- Skills system (74+ capabilities)
- Hooks for customizing behavior
- Memory systems (5-type, Neo4j)
- Power features and customization

## Learning Paths

The tutorial adapts to your experience level:

**Beginner Path** (90 minutes):
```
Section 1 → Section 2 → Section 3 → Section 4
└─ Focus: Understanding basics and running your first workflow
```

**Intermediate Path** (60 minutes):
```
Section 2 → Section 3 → Section 5
└─ Focus: Workflows and autonomous execution
```

**Advanced Path** (60 minutes):
```
Section 3 → Section 6 → Section 7
└─ Focus: Advanced workflows, goal agents, and customization
```

## Features

### Progressive Disclosure

Content tagged by skill level:
- **[BEGINNER]** - Extra explanation for new users
- **[INTERMEDIATE]** - Practical application details
- **[ADVANCED]** - Deep technical details and customization

### Platform Support

Examples for all supported platforms:
- Claude Code
- Amplifier
- GitHub Copilot CLI
- OpenAI Codex
- RustyClawd

### Interactive Navigation

Jump to any section:
```
"Section 3"     - Jump to Workflows Deep Dive
"Continue"      - Go to next section
"Menu"          - Show all sections
"Section 5"     - Jump to Continuous Work
```

### Hands-On Exercises

"Try It Now" sections with real examples:
- Execute your first workflow
- Create a goal-seeking agent
- Use auto mode
- Customize preferences

## Expected Outcomes

After completing this tutorial, you'll be able to:

✅ Execute the default 22-step workflow
✅ Choose the right workflow for any task
✅ Write effective prompts for AI agents
✅ Use auto mode for autonomous multi-turn work
✅ Create custom goal-seeking agents
✅ Customize amplihack for your needs
✅ Understand skills, hooks, and memory systems

## Troubleshooting

### Tutorial Won't Start

**Issue**: Guide agent not responding

**Solution**:
```bash
# Ensure you're in amplihack environment
amplihack --version

# Try explicit agent invocation
Task(subagent_type="guide", prompt="Start tutorial from Section 1")
```

### Navigation Not Working

**Issue**: Jumping to sections doesn't work

**Solution**: Use explicit section names in quotes:
```
"Take me to Section 3: Workflows Deep Dive"
```

### Can't Complete Exercises

**Issue**: Hands-on exercises fail

**Solution**:
- Check [Prerequisites](../PREREQUISITES.md)
- Verify API keys set
- Ensure Git and platform CLIs installed

## Getting Help

**During Tutorial**:
- Type "Help" for assistance
- Ask specific questions at any time
- Request clarification on any topic

**After Tutorial**:
- [Documentation Index](../index.md)
- [Command Selection Guide](../commands/COMMAND_SELECTION_GUIDE.md)
- [GitHub Issues](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues)

## Feedback

Help us improve this tutorial:
1. Report issues or unclear sections
2. Suggest additional topics
3. Share your learning path preferences

**Create an issue**: [Tutorial Feedback](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/new?labels=tutorial-feedback)

---

**Ready to start?** Invoke the guide agent and begin your amplihack journey!

```
"Start the amplihack tutorial"
```

