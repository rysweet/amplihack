# Tool vs Skill Classification

Guidance for distinguishing between tools (executable operations) and skills (knowledge/capabilities).

---

## Core Distinction

| Aspect | Tool | Skill |
|--------|------|-------|
| **Nature** | Executable action | Knowledge/capability |
| **Invocation** | Called to DO something | Loaded to KNOW something |
| **Output** | Returns result/side effect | Enhances agent behavior |
| **Example** | `read_file`, `bash`, `grep` | `python-async`, `security-patterns` |

---

## Tools

### Definition

A **tool** is an executable capability that performs an action and returns a result.

### Characteristics

- **Has side effects** or **returns data**
- **Called on demand** with specific parameters
- **Produces output** that can be used in next steps
- **Stateless** - each call is independent

### Examples

```yaml
# File operations
read_file:
  input: file_path
  output: file contents
  side_effect: none

write_file:
  input: file_path, content
  output: confirmation
  side_effect: creates/modifies file

# System operations
bash:
  input: command
  output: stdout, stderr, exit code
  side_effect: depends on command

# Search operations
grep:
  input: pattern, path
  output: matching lines
  side_effect: none

# External operations
web_fetch:
  input: url
  output: page content
  side_effect: network request
```

### When to Create a Tool

Create a tool when you need to:
- Execute system commands
- Read/write files
- Make network requests
- Query databases
- Interact with external services
- Perform calculations with external data

---

## Skills

### Definition

A **skill** is a knowledge module that enhances agent capabilities without direct execution.

### Characteristics

- **Provides context** and knowledge
- **Loaded into agent memory** before task
- **Influences behavior** rather than executing actions
- **Persistent** for duration of conversation

### Examples

```yaml
# Knowledge skills
python-async:
  provides: Best practices for async Python
  content: Patterns, pitfalls, examples
  usage: Agent writes better async code

security-patterns:
  provides: Security vulnerability knowledge
  content: OWASP top 10, common vulnerabilities
  usage: Agent identifies security issues

# Domain skills
api-design:
  provides: REST API design principles
  content: Conventions, patterns, anti-patterns
  usage: Agent designs better APIs

# Process skills
code-review:
  provides: Code review methodology
  content: What to look for, how to prioritize
  usage: Agent conducts thorough reviews
```

### When to Create a Skill

Create a skill when you need to:
- Teach agents domain knowledge
- Establish coding conventions
- Define project-specific patterns
- Provide reference information
- Share best practices
- Document decision frameworks

---

## Classification Decision Tree

```
Need to DO something?
├── Yes → TOOL
│   ├── File operation? → read_file, write_file, edit_file
│   ├── System command? → bash
│   ├── Search? → grep, glob
│   ├── Network? → web_fetch, web_search
│   └── Other action? → Create new tool
│
└── No → Need to KNOW something?
    ├── Yes → SKILL
    │   ├── Domain knowledge? → Create knowledge skill
    │   ├── Patterns/practices? → Create pattern skill
    │   ├── Project conventions? → Create context file
    │   └── Process guidance? → Create process skill
    │
    └── No → Probably not needed
```

---

## Hybrid Cases

Some capabilities blur the line. Here's how to handle them:

### Code Analysis

```yaml
# This is a TOOL - it executes analysis
python_check:
  type: tool
  why: Executes ruff, pyright - returns concrete results

# This is a SKILL - it's knowledge about analysis
code-review-checklist:
  type: skill
  why: Teaches agent what to look for, doesn't execute
```

### LSP Operations

```yaml
# These are TOOLS - they execute LSP queries
LSP:goToDefinition:
  type: tool
  why: Executes query, returns location

LSP:findReferences:
  type: tool
  why: Executes query, returns list

# This would be a SKILL
lsp-navigation-patterns:
  type: skill
  why: Teaches when/how to use LSP effectively
```

### Recipes

```yaml
# Recipes are NEITHER tool nor skill
# They are orchestration definitions that USE tools and skills
recipe:
  type: orchestration
  uses_tools: [read_file, bash, grep]
  uses_skills: [python-patterns, security-review]
```

---

## Anti-Patterns

### Don't: Create Tool for Pure Knowledge

```yaml
# WRONG - This should be a skill
name: explain-async
type: tool
action: "Return explanation of async programming"

# RIGHT - Make it a skill
name: async-programming
type: skill
content: |
  # Async Programming Patterns
  ...explanation...
```

### Don't: Create Skill for Actions

```yaml
# WRONG - This should be a tool
name: file-formatter
type: skill
content: "Instructions for formatting files"

# RIGHT - Make it a tool (or use existing)
name: format_code
type: tool
action: Execute formatter on files
```

### Don't: Duplicate Existing Tools

```yaml
# WRONG - bash already does this
name: run-tests
type: tool
action: Execute "pytest"

# RIGHT - Use existing tool with instructions
# In agent context: "Use bash to run: pytest"
```

---

## Quick Reference

| If you need to... | Use |
|-------------------|-----|
| Read a file | Tool: `read_file` |
| Know how to structure code | Skill: coding patterns |
| Execute a command | Tool: `bash` |
| Know when to use which command | Skill: process guidance |
| Search for text | Tool: `grep` |
| Know what patterns to search for | Skill: domain knowledge |
| Make HTTP request | Tool: `web_fetch` |
| Know which APIs to call | Skill: API documentation |
| Check code quality | Tool: `python_check` |
| Know what quality means | Skill: quality standards |

---

## Creating New Capabilities

### Before Creating, Ask:

1. **Does this execute an action?** → Tool
2. **Does this provide knowledge?** → Skill
3. **Does existing tool/skill cover this?** → Don't create
4. **Can bash do this?** → Use bash, maybe with skill for guidance
5. **Is this project-specific?** → Context file, not skill

### Tool Creation Checklist

- [ ] Clear input parameters defined
- [ ] Output format specified
- [ ] Side effects documented
- [ ] Error cases handled
- [ ] Not duplicating existing tool
- [ ] Can't be done with bash + skill

### Skill Creation Checklist

- [ ] Provides genuine knowledge/patterns
- [ ] Not just instructions to call a tool
- [ ] Applicable across multiple tasks
- [ ] Enhances agent reasoning
- [ ] Can't be a simple context file
