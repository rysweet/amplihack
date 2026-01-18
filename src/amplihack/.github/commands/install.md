# GitHub Copilot Command Reference: install

**Source**: `.claude/commands/amplihack/install.md`

---

## Command Metadata

- **name**: amplihack:install
- **version**: 1.0.0
- **description**: Install amplihack framework and tools
- **triggers**: 

---

## Usage with GitHub Copilot CLI

This command is designed for Claude Code but the patterns and approaches
can be referenced when using GitHub Copilot CLI.

**Example**:
```bash
# Reference this command's approach
gh copilot explain .github/commands/install.md

# Use patterns from this command
gh copilot suggest --context .github/commands/install.md "your task"
```

---

## Original Command Documentation


# Install the amplihack tools

Amplihack is a collection of claude code customizations designed to enhance productivity and streamline workflows.

It is located in the current .claude dir of the project.

# if you were called with /amplihack:install

then run the following commands:

```bash
.claude/tools/amplihack/install.sh
```
