# DEVELOPING_AMPLIHACK.md

**Version**: 1.0.0
**Last Updated**: 2025-10-17
**Target Audience**: AI Agents, Developers
**Lookup Time Target**: < 10 seconds for 80% of queries

---

## Document Purpose

This is the **authoritative technical reference** for developing with and extending the amplihack framework. It provides:

- **Quick Reference Card** for common operations (Section 1.2)
- **Complete feature-to-implementation mapping** (Section 3)
- **Module-level API documentation** (Section 4)
- **Configuration guides** with examples (Section 5)
- **Development workflows** and common tasks (Sections 6-7)
- **Troubleshooting guide** with solutions (Section 8)

**Search Terms**: amplihack, development, technical reference, API documentation, architecture, modules, configuration, troubleshooting

---

## Table of Contents

1. [Front Matter](#1-front-matter)
   - 1.1 [Document Navigation](#11-document-navigation)
   - 1.2 [Quick Reference Card](#12-quick-reference-card)
2. [Architecture Overview](#2-architecture-overview)
   - 2.1 [System Architecture](#21-system-architecture)
   - 2.2 [Core Components](#22-core-components)
   - 2.3 [Data Flow](#23-data-flow)
3. [Feature Inventory](#3-feature-inventory)
   - 3.1 [Launcher Features](#31-launcher-features)
   - 3.2 [Bundle Generator Features](#32-bundle-generator-features)
   - 3.4 [Security Features](#34-security-features)
   - 3.5 [Agent System Features](#35-agent-system-features)
4. [Module Reference](#4-module-reference)
   - 4.1 [Launcher Module](#41-launcher-module)
   - 4.2 [Bundle Generator Module](#42-bundle-generator-module)
   - 4.4 [Security Module](#44-security-module)
   - 4.5 [Memory Module](#45-memory-module)
   - 4.6 [Utilities Module](#46-utilities-module)
5. [Configuration Guide](#5-configuration-guide)
   - 5.1 [Environment Configuration](#51-environment-configuration)
   - 5.2 [Claude Configuration](#52-claude-configuration)
   - 5.3 [Security Configuration](#53-security-configuration)
6. [Development Workflows](#6-development-workflows)
   - 6.1 [Local Development Setup](#61-local-development-setup)
   - 6.2 [Agent Development](#62-agent-development)
   - 6.3 [Testing Workflow](#63-testing-workflow)
   - 6.4 [CI/CD Integration](#64-cicd-integration)
7. [Common Tasks](#7-common-tasks)
   - 7.1 [Creating Custom Agents](#71-creating-custom-agents)
   - 7.2 [Configuring Azure Integration](#72-configuring-azure-integration)
   - 7.3 [Adding Slash Commands](#73-adding-slash-commands)
   - 7.4 [Security Integration](#74-security-integration)
8. [Troubleshooting](#8-troubleshooting)
   - 8.1 [Common Issues](#81-common-issues)
   - 8.2 [Debugging Guide](#82-debugging-guide)
   - 8.3 [Performance Issues](#83-performance-issues)
9. [Code Examples](#9-code-examples)
   - 9.1 [Agent Creation](#91-agent-creation)
   - 9.2 [Tool Integration](#92-tool-integration)
   - 9.3 [API Usage](#93-api-usage)
10. [Appendices](#10-appendices)
    - 10.1 [Glossary](#101-glossary)
    - 10.2 [File Index](#102-file-index)
    - 10.3 [Command Reference](#103-command-reference)

---

## 1. Front Matter

### 1.1 Document Navigation

**For AI Agents**: Use Ctrl+F / Cmd+F to search for specific terms. Section headers use H2 (##) for major sections and H3 (###) for subsections.

**Quick Navigation Patterns**:

- Feature lookup: Go to Section 3 (Feature Inventory)
- API reference: Go to Section 4 (Module Reference)
- Configuration: Go to Section 5 (Configuration Guide)
- How-to guides: Go to Section 7 (Common Tasks)
- Troubleshooting: Go to Section 8

**Search Terms**: navigation, documentation structure, table of contents, quick reference

---

### 1.2 Quick Reference Card

**80% of Common Queries - Optimized for < 10 Second Lookup**

#### Launch Commands

```bash
# Basic launch
amplihack claude

# Autonomous mode
amplihack claude --auto -- -p "your task"

# Launch with repository
amplihack claude --checkout-repo owner/repo

# Launch GitHub Copilot
amplihack copilot
```

**Implementation**: `/home/azureuser/src/amplihack-worktree-921-922/src/amplihack/cli.py:30-150`

#### Slash Commands

| Command                         | Purpose                           | Implementation                                          |
| ------------------------------- | --------------------------------- | ------------------------------------------------------- |
| `/amplihack:ultrathink <task>`  | Orchestrate multi-agent workflows | `~/.amplihack/.claude/commands/amplihack/ultrathink.md` |
| `/amplihack:analyze <path>`     | Code review and analysis          | `~/.amplihack/.claude/commands/amplihack/analyze.md`    |
| `/amplihack:fix [pattern]`      | Intelligent fix workflow          | `~/.amplihack/.claude/commands/amplihack/fix.md`        |
| `/amplihack:improve [target]`   | Capture learnings                 | `~/.amplihack/.claude/commands/amplihack/improve.md`    |
| `/amplihack:customize <action>` | Manage preferences                | `~/.amplihack/.claude/commands/amplihack/customize.md`  |

**Implementation**: `/home/azureuser/src/amplihack-worktree-921-922/.claude/commands/amplihack/`

#### Key Modules

| Module               | Purpose                  | Entry Point                                   |
| -------------------- | ------------------------ | --------------------------------------------- |
| **Launcher**         | Claude Code execution    | `src/amplihack/launcher/core.py`              |
| **Bundle Generator** | Agent creation           | `src/amplihack/bundle_generator/generator.py` |
| **Security**         | XPIA defense             | `src/amplihack/security/xpia_defender.py`     |
| **Memory**           | Session persistence      | `src/amplihack/memory/manager.py`             |

#### Configuration Files

| File                       | Purpose                  | Location                             |
| -------------------------- | ------------------------ | ------------------------------------ |
| **azure.env**              | Azure OpenAI config      | Project root (user-created)          |
| **settings.json**          | Claude settings          | `~/.amplihack/.claude/settings.json` |
| **.env.security-template** | Security config template | Project root                         |
| **pyproject.toml**         | Project metadata         | Project root                         |

#### Agent Locations

| Type                   | Location                                             | Count |
| ---------------------- | ---------------------------------------------------- | ----- |
| **Core Agents**        | `~/.amplihack/.claude/agents/amplihack/core/`        | 10+   |
| **Specialized Agents** | `~/.amplihack/.claude/agents/amplihack/specialized/` | 15+   |
| **Workflow Agents**    | `~/.amplihack/.claude/agents/amplihack/workflows/`   | 5+    |

#### Common File Paths

```
Project Root: /home/azureuser/src/amplihack-worktree-921-922/

Key Directories:
├── .claude/                    # Claude configuration
│   ├── agents/                 # Agent definitions
│   ├── commands/               # Slash commands
│   ├── context/                # Philosophy and patterns
│   └── workflow/               # Development workflows
├── src/amplihack/              # Source code
│   ├── launcher/               # Launch functionality
│   ├── bundle_generator/       # Agent generation
│   ├── security/               # Security features
│   └── memory/                 # Session management
├── tests/                      # Test suite
└── docs/                       # Documentation
```

#### Environment Variables

```bash
# Claude Configuration
CLAUDE_PROJECT_DIR=/path/to/project
AMPLIHACK_TRACE_LOGGING=true   # Enable native trace logging

# Azure Configuration
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://your-endpoint.openai.azure.com
AZURE_OPENAI_API_VERSION=2025-01-01-preview

# Security Configuration
XPIA_SECURITY_LEVEL=MODERATE   # STRICT|HIGH|MODERATE|LOW
XPIA_ENABLED=true
XPIA_BASH_VALIDATION=true
```

**See Also**: Section 5.1 (Environment Configuration)

---

## 2. Architecture Overview

### 2.1 System Architecture

amplihack is a **development framework** that enhances Claude Code and GitHub Copilot with specialized agents, Azure integration, and security features.

**Search Terms**: architecture, system design, components, overview

#### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│  CLI (amplihack) + Claude Code + GitHub Copilot CLI         │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│                   Orchestration Layer                        │
│  • Launcher (core.py)                                        │
│  • Command Router (~/.amplihack/.claude/commands/)                        │
│  • Agent Orchestrator (ultrathink.md)                        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│                     Agent Layer                              │
│  • Core Agents (architect, builder, reviewer, etc.)         │
│  • Specialized Agents (security, optimizer, etc.)           │
│  • Workflow Agents (ci-diagnostic, pre-commit, etc.)        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│                   Service Layer                              │
│  • Security Service (XPIA defense)                          │
│  • Memory Service (session persistence)                     │
│  • Bundle Generator (agent creation)                        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│                  Infrastructure Layer                        │
│  • File System (project detection)                          │
│  • Network (API communication)                              │
│  • Process Management (subprocess execution)                │
└─────────────────────────────────────────────────────────────┘
```

**Implementation**: See Section 4 for detailed module documentation

---

### 2.2 Core Components

#### Component: Launcher

**Purpose**: Manages Claude Code execution lifecycle
**Location**: `/home/azureuser/src/amplihack-worktree-921-922/src/amplihack/launcher/`
**Key Files**:

- `core.py:20-543` - Main ClaudeLauncher class
- `detector.py:1-150` - .claude directory detection
- `repo_checkout.py:1-100` - Repository checkout
- `auto_mode.py:1-200` - Autonomous mode

**Responsibilities**:

1. Prerequisites checking (Node.js, npm, claude CLI)
2. Repository checkout and directory management
3. Claude process spawning and monitoring
4. Environment variable configuration

**See Also**: Section 4.1 (Launcher Module)

---

#### Component: Bundle Generator

**Purpose**: Creates custom agent bundles from natural language
**Location**: `/home/azureuser/src/amplihack-worktree-921-922/src/amplihack/bundle_generator/`
**Key Files**:

- `generator.py:1-556` - Agent content generation
- `parser.py:1-300` - Intent extraction
- `packager.py:1-250` - Bundle packaging
- `cli.py:1-200` - CLI interface

**Responsibilities**:

1. Natural language intent extraction
2. Agent specification generation
3. Test file creation
4. Documentation generation
5. Bundle packaging and distribution

**See Also**: Section 4.3 (Bundle Generator Module)

---

#### Component: Security (XPIA Defense)

**Purpose**: Cross-Prompt Injection Attack defense
**Location**: `/home/azureuser/src/amplihack-worktree-921-922/src/amplihack/security/`
**Key Files**:

- `xpia_defender.py:1-673` - Core security validation
- `xpia_patterns.py:1-400` - Attack pattern detection
- `xpia_hooks.py:1-250` - Hook integration
- `xpia_defense_interface.py:1-200` - Public API

**Responsibilities**:

1. Content validation (prompts, commands, URLs)
2. Attack pattern detection
3. Risk level assessment
4. Mitigation recommendations
5. Security event logging

**See Also**: Section 4.4 (Security Module)

---

### 2.3 Data Flow

#### Claude Launch Flow

```
1. User executes: amplihack claude
   ↓
2. CLI parses arguments (cli.py:30-150)
   ↓
3. ClaudeLauncher.prepare_launch() (launcher/core.py:74-100)
   ├── Check prerequisites (utils/prerequisites.py:1-150)
   ├── Detect .claude directory (launcher/detector.py:20-80)
   └── Configure environment variables
   ↓
4. ClaudeLauncher.build_claude_command() (launcher/core.py:281-348)
   ├── Select claude command
   ├── Add --add-dir for UVX mode
   ├── Configure Azure model
   └── Append user arguments
   ↓
5. ClaudeLauncher.launch() (launcher/core.py:350-420)
   ├── Set environment variables
   ├── Spawn Claude process
   ├── Monitor execution
   └── Clean up on exit
```

**Search Terms**: data flow, execution flow, request flow, process flow

---

## 3. Feature Inventory

**Complete feature-to-implementation mapping for rapid discovery**

**Search Terms**: features, capabilities, functionality, what can amplihack do

---

### 3.1 Launcher Features

| Feature                 | Description                            | Implementation                       | Status        |
| ----------------------- | -------------------------------------- | ------------------------------------ | ------------- |
| **Basic Launch**        | Launch Claude Code with .claude config | `launcher/core.py:350-420`           | ✅ Stable     |
| **Repository Checkout** | Clone and launch in GitHub repo        | `launcher/repo_checkout.py:1-100`    | ✅ Stable     |
| **UVX Detection**       | Detect uvx execution mode              | `uvx/manager.py:1-200`               | ✅ Stable     |
| **--add-dir Support**   | Add project directory to Claude        | `launcher/core.py:311-338`           | ✅ Stable     |
| **Prerequisites Check** | Validate Node.js, npm, claude CLI      | `utils/prerequisites.py:1-150`       | ✅ Stable     |
| **Path Caching**        | Cache resolved paths for performance   | `launcher/core.py:510-528`           | ✅ Stable     |
| **Autonomous Mode**     | Multi-turn task execution              | `launcher/auto_mode.py:1-200`        | ✅ Stable     |
| **Settings Backup**     | Backup/restore Claude settings         | `launcher/settings_manager.py:1-150` | ✅ Stable     |

**Search Terms**: launch, claude code, execution, repository, uvx

---

### 3.2 Bundle Generator Features

| Feature                | Description                         | Implementation                          | Status    |
| ---------------------- | ----------------------------------- | --------------------------------------- | --------- |
| **Intent Extraction**  | Parse natural language requirements | `bundle_generator/parser.py:1-300`      | ✅ Stable |
| **Agent Generation**   | Create agent markdown files         | `bundle_generator/generator.py:87-179`  | ✅ Stable |
| **Test Generation**    | Generate pytest test files          | `bundle_generator/generator.py:409-464` | ✅ Stable |
| **Documentation**      | Create README and integration docs  | `bundle_generator/generator.py:466-528` | ✅ Stable |
| **Bundle Packaging**   | Package as standalone distribution  | `bundle_generator/packager.py:1-250`    | ✅ Stable |
| **CLI Interface**      | Command-line bundle creation        | `bundle_generator/cli.py:1-200`         | ✅ Stable |
| **Validation**         | Validate generated agents           | `bundle_generator/generator.py:530-556` | ✅ Stable |
| **Template System**    | Customizable agent templates        | `bundle_generator/generator.py:26-76`   | ✅ Stable |
| **Capability Mapping** | Map capabilities to implementations | `bundle_generator/generator.py:190-201` | ✅ Stable |
| **Complexity Levels**  | Simple/standard/advanced agents     | `bundle_generator/generator.py:310-342` | ✅ Stable |

**Search Terms**: bundle generator, agent creation, custom agents, agent bundle

---

### 3.4 Security Features

| Feature                 | Description                         | Implementation                      | Status    |
| ----------------------- | ----------------------------------- | ----------------------------------- | --------- |
| **Content Validation**  | Validate arbitrary content          | `security/xpia_defender.py:136-191` | ✅ Stable |
| **Bash Validation**     | Validate shell commands             | `security/xpia_defender.py:193-270` | ✅ Stable |
| **URL Validation**      | Validate URLs for security          | `security/xpia_defender.py:559-625` | ✅ Stable |
| **WebFetch Defense**    | Specialized WebFetch validation     | `security/xpia_defender.py:522-557` | ✅ Stable |
| **Pattern Detection**   | Detect attack patterns              | `security/xpia_patterns.py:1-400`   | ✅ Stable |
| **Risk Assessment**     | Calculate overall risk level        | `security/xpia_defender.py:419-435` | ✅ Stable |
| **Threat Mitigation**   | Generate mitigation recommendations | `security/xpia_defender.py:437-469` | ✅ Stable |
| **Security Levels**     | Configurable strictness (4 levels)  | `security/xpia_defender.py:61-84`   | ✅ Stable |
| **Whitelist/Blacklist** | Domain filtering                    | `security/xpia_defender.py:86-134`  | ✅ Stable |
| **Event Logging**       | Security event audit trail          | `security/xpia_defender.py:471-502` | ✅ Stable |
| **Hook Integration**    | Pre/post validation hooks           | `security/xpia_hooks.py:1-250`      | ✅ Stable |
| **Health Check**        | System health monitoring            | `security/xpia_defender.py:347-357` | ✅ Stable |

**Search Terms**: security, xpia, validation, threat detection, injection attacks

---

### 3.5 Agent System Features

| Feature                 | Description                   | Implementation                                          | Status          |
| ----------------------- | ----------------------------- | ------------------------------------------------------- | --------------- |
| **Core Agents**         | 10+ pre-built core agents     | `~/.amplihack/.claude/agents/amplihack/core/`           | ✅ Stable       |
| **Specialized Agents**  | 15+ specialized agents        | `~/.amplihack/.claude/agents/amplihack/specialized/`    | ✅ Stable       |
| **Workflow Agents**     | 5+ workflow agents            | `~/.amplihack/.claude/agents/amplihack/workflows/`      | ✅ Stable       |
| **Agent Orchestration** | Multi-agent task coordination | `~/.amplihack/.claude/commands/amplihack/ultrathink.md` | ✅ Stable       |
| **Parallel Execution**  | Concurrent agent execution    | `CLAUDE.md:200-350`                                     | ✅ Stable       |
| **Agent Communication** | Inter-agent messaging         | Security validation available                           | 🚧 Experimental |
| **Custom Agents**       | User-created agents           | Bundle Generator                                        | ✅ Stable       |
| **Agent Catalog**       | Browse available agents       | `~/.amplihack/.claude/agents/CATALOG.md`                | ✅ Stable       |
| **Context Injection**   | Automatic context loading     | `~/.amplihack/.claude/context/` files                   | ✅ Stable       |
| **Session Logging**     | Agent decision logging        | `~/.amplihack/.claude/runtime/logs/`                    | ✅ Stable       |

**Search Terms**: agents, orchestration, multi-agent, workflows, agent system

---

## 4. Module Reference

**Detailed API documentation for core modules**

**Search Terms**: api reference, modules, classes, functions, interfaces

---

### 4.1 Launcher Module

**Location**: `/home/azureuser/src/amplihack-worktree-921-922/src/amplihack/launcher/`

#### 4.1.1 ClaudeLauncher Class

**File**: `core.py:20-543`

```python
class ClaudeLauncher:
    """Launches Claude Code with proper configuration and performance optimization."""
```

**Purpose**: Manages the complete Claude Code launch lifecycle including repository checkout and environment configuration.

**Performance Optimizations**:

- Path resolution caching (lines 70-71, 510-528)
- UVX decision caching (lines 72-73)
- Directory comparison optimization (lines 163-171)

---

**Constructor**:

```python
def __init__(
    self,
    append_system_prompt: Optional[Path] = None,
    force_staging: bool = False,
    checkout_repo: Optional[str] = None,
    claude_args: Optional[List[str]] = None,
)
```

**Parameters**:

- `append_system_prompt`: Path to additional system prompt file
- `force_staging`: Force staging approach instead of --add-dir (UVX mode)
- `checkout_repo`: GitHub repository URI (format: "owner/repo")
- `claude_args`: Additional CLI arguments to pass to Claude

**Example**:

```python
from amplihack.launcher.core import ClaudeLauncher

# Basic launch
launcher = ClaudeLauncher()
exit_code = launcher.launch()

# With repository checkout
launcher = ClaudeLauncher(checkout_repo="owner/repo")
exit_code = launcher.launch()
```

**See Also**: Section 7.1 (Creating Custom Agents), Section 9.3 (API Usage)

---

**Key Methods**:

##### `prepare_launch() -> bool`

**Location**: `core.py:74-100`

**Purpose**: Prepare environment for launching Claude (prerequisites, directory setup).

**Returns**: `True` if preparation successful, `False` otherwise

**Process**:

1. Check prerequisites (Node.js, npm, Claude CLI) - line 81
2. Handle repository checkout if requested - lines 85-87
3. Find and validate target directory - lines 90-93
4. Handle directory change - lines 96-97

**Example**:

```python
launcher = ClaudeLauncher()
if launcher.prepare_launch():
    # Ready to launch
    pass
```

---

##### `build_claude_command() -> List[str]`

**Location**: `core.py:281-348`

**Purpose**: Build the Claude command with all necessary arguments.

**Returns**: List of command arguments for subprocess

**Logic**:

- Detects Claude CLI availability (line 291)
- Adds --add-dir for UVX mode (lines 312-313, 336-338)
- Appends user-provided arguments (lines 320-321, 345-346)

**Example**:

```python
launcher = ClaudeLauncher(
    claude_args=["--model", "claude-sonnet-4-5-20250929"]
)
cmd = launcher.build_claude_command()
# cmd = ["claude", "--dangerously-skip-permissions", "--model", "claude-sonnet-4-5-20250929"]
```

---

##### `launch() -> int`

**Location**: `core.py:350-420`

**Purpose**: Launch Claude Code and monitor execution.

**Returns**: Exit code from Claude process

**Features**:

- Signal handling for graceful shutdown (lines 364-374)
- Environment variable configuration (lines 377-404)
- Proxy environment integration (lines 391-404)
- Cleanup on exit (lines 417-419)

**Example**:

```python
launcher = ClaudeLauncher()
exit_code = launcher.launch()
sys.exit(exit_code)
```

---

#### 4.1.2 ClaudeDirectoryDetector Class

**File**: `detector.py:1-150`

**Purpose**: Detect .claude directories and determine project roots.

**Key Methods**:

```python
def find_claude_directory() -> Optional[Path]:
    """Find .claude directory in current or parent directories."""

def get_project_root(claude_dir: Path) -> Path:
    """Get project root directory from .claude directory."""
```

**Example**:

```python
from amplihack.launcher.detector import ClaudeDirectoryDetector

detector = ClaudeDirectoryDetector()
claude_dir = detector.find_claude_directory()
if claude_dir:
    project_root = detector.get_project_root(claude_dir)
```

---

#### 4.1.3 Repository Checkout

**File**: `repo_checkout.py:1-100`

**Purpose**: Clone GitHub repositories and set up working directories.

**Key Function**:

```python
def checkout_repository(repo_uri: str) -> Optional[str]:
    """
    Checkout GitHub repository.

    Args:
        repo_uri: Repository URI (owner/repo or full URL)

    Returns:
        Path to checked out repository or None on failure
    """
```

**Supported Formats**:

- `owner/repo`
- `https://github.com/owner/repo`
- `https://github.com/owner/repo.git`
- `owner/repo@branch-name` (specific branch)

**Example**:

```python
from amplihack.launcher.repo_checkout import checkout_repository

repo_path = checkout_repository("microsoft/TypeScript")
if repo_path:
    os.chdir(repo_path)
```

---

### 4.2 Bundle Generator Module

**Location**: `/home/azureuser/src/amplihack-worktree-921-922/src/amplihack/bundle_generator/`

**Search Terms**: bundle generator, agent creation, agent bundle, custom agents

---

#### 4.3.1 AgentGenerator Class

**File**: `generator.py:18-556`

**Purpose**: Generate agent content from natural language requirements.

**Constructor**:

```python
class AgentGenerator:
    """Generate agent content from extracted requirements."""

    def __init__(self, template_path: Optional[str] = None):
        """
        Initialize the agent generator.

        Args:
            template_path: Optional path to custom templates
        """
```

---

**Key Methods**:

##### `generate(intent: ExtractedIntent, options: Dict = None) -> List[GeneratedAgent]`

**Location**: `generator.py:87-117`

**Purpose**: Generate agents from extracted intent.

**Parameters**:

- `intent`: ExtractedIntent object with parsed requirements
- `options`: Optional generation options
  - `include_tests`: Generate test files (default: True)
  - `include_docs`: Generate documentation (default: True)

**Returns**: List of GeneratedAgent objects

**Example**:

```python
from amplihack.bundle_generator.generator import AgentGenerator
from amplihack.bundle_generator.parser import IntentParser

parser = IntentParser()
intent = parser.parse("Create an agent that validates JSON schemas")

generator = AgentGenerator()
agents = generator.generate(intent, options={"include_tests": True})

for agent in agents:
    print(f"Generated: {agent.name}")
    print(f"Content length: {len(agent.content)} bytes")
```

---

##### `_generate_single_agent(requirement: AgentRequirement, ...) -> GeneratedAgent`

**Location**: `generator.py:119-179`

**Purpose**: Generate a single agent from requirement specification.

**Generated Content**:

- Agent markdown file (lines 126-152)
- Test files (lines 155-157)
- Documentation (lines 160-162)
- Metadata (lines 166-179)

**Agent Template Structure** (lines 26-76):

```markdown
# {name}

{description}

## Role

{role}

## Model Configuration

Model: {model}

## Capabilities

{capabilities}

## Core Responsibilities

{responsibilities}

## Implementation

{implementation}

## Context and Philosophy

{philosophy}

## Error Handling

{error_handling}

## Performance Considerations

{performance}

## Dependencies

{dependencies}

## Example Usage

{examples}

## Testing

{testing}
```

---

##### `validate_agent(agent: GeneratedAgent) -> List[str]`

**Location**: `generator.py:530-556`

**Purpose**: Validate generated agent content.

**Checks**:

- Content length (minimum 100 bytes)
- Required sections present (Role, Capabilities, Implementation)
- No placeholders (TODO, PLACEHOLDER)

**Returns**: List of validation issues (empty if valid)

**Example**:

```python
issues = generator.validate_agent(agent)
if issues:
    print(f"Validation failed: {issues}")
else:
    print("Agent is valid")
```

---

#### 4.3.2 IntentParser Class

**File**: `parser.py:1-300`

**Purpose**: Parse natural language requirements into structured intent.

**Key Methods**:

```python
def parse(self, user_input: str) -> ExtractedIntent:
    """
    Parse user input to extract agent requirements.

    Args:
        user_input: Natural language description

    Returns:
        ExtractedIntent with structured requirements
    """
```

**Example**:

```python
from amplihack.bundle_generator.parser import IntentParser

parser = IntentParser()
intent = parser.parse(
    "Create a security agent that validates bash commands "
    "for injection attacks and provides mitigation advice"
)

print(f"Domain: {intent.domain}")
print(f"Action: {intent.action}")
print(f"Complexity: {intent.complexity}")
print(f"Agent count: {len(intent.agent_requirements)}")
```

---

#### 4.3.3 BundlePackager Class

**File**: `packager.py:1-250`

**Purpose**: Package generated agents into distributable bundles.

**Key Methods**:

```python
def package(
    self,
    agents: List[GeneratedAgent],
    bundle_name: str,
    output_dir: Path
) -> Path:
    """
    Package agents into a bundle.

    Args:
        agents: List of generated agents
        bundle_name: Name for the bundle
        output_dir: Output directory

    Returns:
        Path to created bundle
    """
```

**Bundle Structure**:

```
bundle-name/
├── agents/
│   ├── agent1.md
│   └── agent2.md
├── tests/
│   ├── test_agent1.py
│   └── test_agent2.py
├── manifest.json
├── README.md
└── setup.py (optional)
```

---

### 4.4 Security Module

**Location**: `/home/azureuser/src/amplihack-worktree-921-922/src/amplihack/security/`

**Search Terms**: security, xpia, validation, threat detection, cross-prompt injection

---

#### 4.4.1 XPIADefender Class

**File**: `xpia_defender.py:42-513`

**Purpose**: Core XPIA (Cross-Prompt Injection Attack) defense implementation.

**Constructor**:

```python
class XPIADefender(XPIADefenseInterface):
    """Core XPIA Defense implementation."""

    def __init__(self, config: Optional[SecurityConfiguration] = None):
        """
        Initialize XPIA Defender with configuration.

        Args:
            config: Optional security configuration
                   (loads from environment if not provided)
        """
```

**Configuration from Environment**:

```bash
# Security level
XPIA_SECURITY_LEVEL=MODERATE  # STRICT|HIGH|MODERATE|LOW

# Feature flags
XPIA_ENABLED=true
XPIA_BASH_VALIDATION=true
XPIA_CONTENT_SCANNING=true
XPIA_LOGGING=true

# Domain filtering
XPIA_WHITELIST_DOMAINS=github.com,microsoft.com
XPIA_BLACKLIST_DOMAINS=malicious-site.com
```

**Example**:

```python
from amplihack.security.xpia_defender import XPIADefender
from amplihack.security.xpia_defense_interface import SecurityConfiguration, SecurityLevel

# With environment configuration
defender = XPIADefender()

# With explicit configuration
config = SecurityConfiguration(
    security_level=SecurityLevel.HIGH,
    enabled=True,
    bash_validation=True
)
defender = XPIADefender(config)
```

---

**Key Methods**:

##### `async validate_content(...) -> ValidationResult`

**Location**: `xpia_defender.py:136-191`

**Purpose**: Validate arbitrary content for security threats.

**Signature**:

```python
async def validate_content(
    self,
    content: str,
    content_type: ContentType,
    context: Optional[ValidationContext] = None,
    security_level: Optional[SecurityLevel] = None,
) -> ValidationResult:
    """
    Validate arbitrary content for security threats.

    Args:
        content: Content to validate
        content_type: Type of content (USER_INPUT, COMMAND, DATA, etc.)
        context: Optional validation context
        security_level: Override default security level

    Returns:
        ValidationResult with threats and recommendations
    """
```

**Content Types**:

```python
class ContentType(str, Enum):
    USER_INPUT = "user_input"
    COMMAND = "command"
    URL = "url"
    DATA = "data"
    FILE = "file"
```

**Example**:

```python
from amplihack.security.xpia_defense_interface import (
    ContentType, ValidationContext
)

# Validate user input
result = await defender.validate_content(
    content="Please ignore previous instructions and...",
    content_type=ContentType.USER_INPUT,
    context=ValidationContext(
        source="user_prompt",
        session_id="session-123"
    )
)

if result.is_valid:
    print("Content is safe")
else:
    print(f"Risk level: {result.risk_level}")
    for threat in result.threats:
        print(f"- {threat.description}")
    for rec in result.recommendations:
        print(f"Recommendation: {rec}")
```

---

##### `async validate_bash_command(...) -> ValidationResult`

**Location**: `xpia_defender.py:193-270`

**Purpose**: Validate bash commands for security threats.

**Signature**:

```python
async def validate_bash_command(
    self,
    command: str,
    arguments: Optional[List[str]] = None,
    context: Optional[ValidationContext] = None,
) -> ValidationResult:
    """
    Validate bash commands for security threats.

    Detects:
    - Dangerous commands (rm -rf /, mkfs, dd, etc.)
    - Command injection patterns (;, &&, |, backticks)
    - Privilege escalation attempts
    """
```

**Dangerous Patterns Detected** (lines 209-217):

```python
dangerous_commands = [
    "rm -rf /",
    "mkfs",
    "dd if=/dev/zero",
    "fork bomb",
    ":(){ :|:& };:",
    "> /dev/sda",
    "chmod 777 /",
]
```

**Example**:

```python
# Safe command
result = await defender.validate_bash_command(
    command="ls",
    arguments=["-la", "/home/user"]
)
assert result.is_valid

# Dangerous command
result = await defender.validate_bash_command(
    command="rm",
    arguments=["-rf", "/"]
)
assert not result.is_valid
assert result.risk_level == RiskLevel.CRITICAL
```

---

##### `async validate_agent_communication(...) -> ValidationResult`

**Location**: `xpia_defender.py:272-324`

**Purpose**: Validate inter-agent communication for security.

**Signature**:

```python
async def validate_agent_communication(
    self,
    source_agent: str,
    target_agent: str,
    message: Dict[str, Any],
    message_type: str = "task",
) -> ValidationResult:
    """
    Validate inter-agent communication.

    Detects:
    - Privilege escalation attempts
    - Injection attacks in messages
    - Suspicious content
    """
```

**Example**:

```python
result = await defender.validate_agent_communication(
    source_agent="builder",
    target_agent="reviewer",
    message={
        "task": "Review the implementation",
        "files": ["src/main.py"]
    },
    message_type="task"
)
```

---

##### `async health_check() -> Dict[str, Any]`

**Location**: `xpia_defender.py:347-357`

**Purpose**: Perform health check and return status.

**Returns**:

```python
{
    "status": "healthy",
    "enabled": True,
    "security_level": "MODERATE",
    "patterns_loaded": 50,
    "whitelist_size": 10,
    "blacklist_size": 2,
    "events_logged": 15
}
```

---

#### 4.4.2 WebFetchXPIADefender Class

**File**: `xpia_defender.py:515-673`

**Purpose**: Specialized XPIA defender for WebFetch tool.

**Key Methods**:

##### `async validate_webfetch_request(url: str, prompt: str, ...) -> ValidationResult`

**Location**: `xpia_defender.py:522-557`

**Purpose**: Validate WebFetch requests (URL + prompt combination).

**Checks**:

- URL validation (domain, parameters, protocol)
- Prompt validation (injection patterns)
- Combined attack detection (URL referenced in malicious prompts)

**Example**:

```python
from amplihack.security.xpia_defender import WebFetchXPIADefender

defender = WebFetchXPIADefender()

result = await defender.validate_webfetch_request(
    url="https://github.com/microsoft/TypeScript",
    prompt="Summarize the README file"
)

if result.is_valid:
    # Safe to fetch
    pass
```

---

#### 4.4.3 Risk Levels and Threat Types

**Risk Levels** (`xpia_defense_interface.py`):

```python
class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

**Threat Types**:

```python
class ThreatType(str, Enum):
    INJECTION = "injection"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    MALICIOUS_CODE = "malicious_code"
    SOCIAL_ENGINEERING = "social_engineering"
```

---

### 4.5 Memory Module

**Location**: `/home/azureuser/src/amplihack-worktree-921-922/src/amplihack/memory/`

**Search Terms**: memory, session, persistence, database, conversation history

**Purpose**: Manage session persistence and conversation history.

**Key Files**:

- `manager.py:1-300` - Memory management
- `database.py:1-250` - SQLite database operations
- `models.py:1-150` - Data models
- `maintenance.py:1-200` - Cleanup and optimization

**Status**: 🚧 Experimental (not yet fully integrated)

---

### 4.6 Utilities Module

**Location**: `/home/azureuser/src/amplihack-worktree-921-922/src/amplihack/utils/`

**Search Terms**: utilities, helpers, tools, claude cli, prerequisites

---

#### 4.6.1 Prerequisites Checking

**File**: `prerequisites.py:1-150`

**Purpose**: Check and validate required tools.

**Key Function**:

```python
def check_prerequisites() -> bool:
    """
    Check all required prerequisites.

    Checks:
    - Node.js (version 18+)
    - npm
    - git
    - claude CLI

    Returns:
        True if all prerequisites met, False otherwise
    """
```

**Example**:

```python
from amplihack.utils.prerequisites import check_prerequisites

if not check_prerequisites():
    print("Missing prerequisites")
    sys.exit(1)
```

---

#### 4.6.2 Claude CLI Utilities

**File**: `claude_cli.py:1-200`

**Purpose**: Utilities for detecting and managing Claude CLI.

**Key Functions**:

```python
def get_claude_cli_path(auto_install: bool = True) -> Optional[str]:
    """
    Get path to Claude CLI executable.

    Args:
        auto_install: Attempt to install if not found

    Returns:
        Path to claude or None
    """

def install_claude_cli() -> bool:
    """
    Install Claude CLI via npm.

    Returns:
        True if installation successful
    """
```

**Example**:

```python
from amplihack.utils.claude_cli import (
    get_claude_cli_path,
    install_claude_cli
)

claude_path = get_claude_cli_path(auto_install=False)
if not claude_path:
    if install_claude_cli():
        claude_path = get_claude_cli_path(auto_install=False)
```

---

#### 4.6.3 Native Trace Logging

**Purpose**: Native JSONL trace logging for debugging.

**Usage**:

```python
import os

# Enable native trace logging
os.environ["AMPLIHACK_TRACE_LOGGING"] = "true"

# Traces are written to .claude/runtime/amplihack-traces/
```

---

## 5. Configuration Guide

**Complete configuration reference with examples**

**Search Terms**: configuration, setup, environment variables, config files

---

### 5.1 Environment Configuration

#### 5.1.1 Project Environment Variables

**Core Variables**:

```bash
# Claude Project Directory (automatically set by launcher)
CLAUDE_PROJECT_DIR=/path/to/project

# Enable native trace logging
AMPLIHACK_TRACE_LOGGING=true

# UVX mode (automatically detected)
AMPLIHACK_UVX_MODE=1
```

**Location**: Set by launcher automatically or in shell profile

---

#### 5.1.2 Python Environment

**pyproject.toml**:

```toml
# /home/azureuser/src/amplihack-worktree-921-922/pyproject.toml

[project]
name = "amplihack"
version = "0.2.0"
requires-python = ">=3.8"

dependencies = [
    "flask>=2.0.0",
    "requests>=2.25.0",
    "fastapi>=0.68.0",
    "uvicorn>=0.15.0",
    "aiohttp>=3.8.0",
    "python-dotenv>=0.19.0",
]

[project.scripts]
amplihack = "amplihack:main"
```

**Installation**:

```bash
# Development install
cd /path/to/amplihack-worktree-921-922
uv pip install -e .

# Or via uvx (no install)
uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack
```

---

### 5.2 Claude Configuration

#### 5.2.1 .claude Directory Structure

**Location**: `/home/azureuser/src/amplihack-worktree-921-922/.claude/`

```
.claude/
├── agents/                     # Agent definitions
│   └── amplihack/
│       ├── core/              # Core agents (10+)
│       ├── specialized/       # Specialized agents (15+)
│       └── workflows/         # Workflow agents (5+)
├── commands/                  # Slash commands
│   └── amplihack/
│       ├── ultrathink.md
│       ├── analyze.md
│       ├── fix.md
│       ├── improve.md
│       └── customize.md
├── context/                   # Philosophy and patterns
│   ├── PHILOSOPHY.md
│   ├── PATTERNS.md
│   ├── PROJECT.md
│   ├── USER_PREFERENCES.md
│   └── DISCOVERIES.md
├── workflow/                  # Development workflows
│   └── DEFAULT_WORKFLOW.md
├── hooks/                     # Git-style hooks
├── runtime/                   # Runtime data
│   ├── logs/                  # Session logs
│   └── reports/               # Analysis reports
├── scenarios/                 # Production tools
└── settings.json              # Claude settings
```

**Detection**: Launcher automatically finds .claude directory in current or parent directories.

---

#### 5.2.2 settings.json

**Location**: `~/.amplihack/.claude/settings.json`

```json
{
  "mcp": {
    "enabled": true,
    "servers": {
      "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/project"]
      }
    }
  },
  "permissions": {
    "dangerouslySkipPermissions": true
  }
}
```

**Management**: Automatically backed up and restored by launcher (lines `launcher/settings_manager.py:1-150`)

---

### 5.3 Security Configuration

#### 5.4.1 XPIA Security Configuration

**Environment Variables**:

```bash
# Security level (STRICT|HIGH|MODERATE|LOW)
XPIA_SECURITY_LEVEL=MODERATE

# Enable/disable XPIA defense
XPIA_ENABLED=true

# Feature flags
XPIA_BASH_VALIDATION=true      # Validate bash commands
XPIA_CONTENT_SCANNING=true     # Scan content for threats
XPIA_LOGGING=true              # Log security events

# Domain filtering
XPIA_WHITELIST_DOMAINS=github.com,microsoft.com,stackoverflow.com
XPIA_BLACKLIST_DOMAINS=malicious-site.com,phishing-site.com

# File-based configuration
XPIA_WHITELIST_FILE=.xpia_whitelist
XPIA_BLACKLIST_FILE=.xpia_blacklist
```

**Security Levels** (`security/xpia_defender.py:61-84`):

| Level        | Threshold             | Use Case                   |
| ------------ | --------------------- | -------------------------- |
| **STRICT**   | Flag all patterns     | High-security environments |
| **HIGH**     | Flag all patterns     | Sensitive operations       |
| **MODERATE** | Flag medium+ severity | Default production         |
| **LOW**      | Flag high+ severity   | Development/testing        |

---

#### 5.4.2 Whitelist/Blacklist Files

**.xpia_whitelist** (project root):

```
# Safe domains (one per line)
github.com
microsoft.com
azure.com
openai.com
anthropic.com
stackoverflow.com
python.org
nodejs.org
```

**.xpia_blacklist** (project root):

```
# Blocked domains (one per line)
malicious-site.com
phishing-site.com
known-bad-domain.com
```

**Default Whitelisted Domains** (`security/xpia_defender.py:101-115`):

- github.com
- microsoft.com
- azure.com
- openai.com
- anthropic.com
- stackoverflow.com
- python.org
- nodejs.org
- npmjs.com
- pypi.org

---

#### 5.4.3 Pre-commit Security Hooks

**File**: `.pre-commit-config.yaml`

```yaml
repos:
  - repo: local
    hooks:
      - id: detect-secrets
        name: Detect secrets
        entry: detect-secrets-hook
        language: system
        args: ["--baseline", ".secrets.baseline"]

      - id: gitguardian
        name: GitGuardian scan
        entry: ggshield secret scan pre-commit
        language: system
```

**Configuration**:

```yaml
# .gitguardian.yaml
minimum-severity: CRITICAL
ignore-known-secrets: true
```

**See Also**: Section 6.3 (Testing Workflow)

---

## 6. Development Workflows

**Standard workflows for common development tasks**

**Search Terms**: workflows, development process, testing, ci/cd, git workflow

---

### 6.1 Local Development Setup

#### 6.1.1 Initial Setup

**Prerequisites**:

1. Python 3.8+
2. Node.js 18+
3. npm
4. git
5. uv (https://docs.astral.sh/uv/)

**Installation**:

```bash
# Clone repository
git clone https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding.git
cd MicrosoftHackathon2025-AgenticCoding

# Install dependencies
uv pip install -e .

# Install development dependencies
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Verify installation
amplihack --help
```

---

#### 6.1.2 Development Environment

**Create Azure configuration**:

```bash
# Launch development instance
amplihack claude

# With local changes (editable install)
python -m amplihack claude
```

---

#### 6.1.3 Directory Structure for Development

```
amplihack-worktree-921-922/
├── .claude/                    # Claude configuration (version controlled)
├── src/amplihack/              # Source code
│   ├── launcher/
│   ├── bundle_generator/
│   ├── security/
│   └── ...
├── tests/                      # Test suite
│   ├── launcher/
│   └── ...
├── docs/                       # Documentation
├── examples/                   # Example scripts
├── scripts/                    # Utility scripts
├── azure.env                   # Your Azure config (not committed)
├── pyproject.toml              # Project metadata
└── README.md                   # Project readme
```

---

### 6.2 Agent Development

#### 6.2.1 Creating a New Agent

**Step 1: Determine Agent Type**

- **Core Agent**: Fundamental functionality (architect, builder, reviewer)
  - Location: `~/.amplihack/.claude/agents/amplihack/core/`

- **Specialized Agent**: Specific domain expertise (security, optimizer, database)
  - Location: `~/.amplihack/.claude/agents/amplihack/specialized/`

- **Workflow Agent**: Complete workflows (ci-diagnostic, pre-commit)
  - Location: `~/.amplihack/.claude/agents/amplihack/workflows/`

---

**Step 2: Create Agent File**

**File**: `~/.amplihack/.claude/agents/amplihack/specialized/my-agent.md`

````markdown
# My Agent

Brief description of what this agent does.

## Role

Primary role and responsibility of this agent.

## Model Configuration

Model: inherit

## Capabilities

- Capability 1: Description
- Capability 2: Description
- Capability 3: Description

## Core Responsibilities

1. **Primary**: Main responsibility
2. **Validation**: Ensure input quality
3. **Processing**: Execute core operations
4. **Error Handling**: Handle failures gracefully
5. **Reporting**: Provide clear feedback

## Implementation

### Input Processing

Describe expected input format and validation.

### Core Algorithm

```python
def process(input_data):
    # Pseudocode or actual implementation
    pass
```
````

### Output Format

Describe output structure and format.

## Context and Philosophy

This agent follows amplihack philosophy:

- Ruthless Simplicity
- Modular Design
- Zero-BS Implementation
- Regeneratable

## Error Handling

Describe error handling strategy:

1. Input validation errors
2. Processing errors
3. Resource errors
4. Recovery strategies

## Performance Considerations

- Latency requirements
- Throughput expectations
- Memory usage
- Scalability

## Dependencies

List any dependencies on other agents or services.

## Example Usage

```python
# Example 1: Basic usage
result = my_agent.process(input_data)

# Example 2: With options
result = my_agent.process(input_data, options={...})
```

## Testing

Describe testing strategy and test coverage.

````

---

**Step 3: Test Agent**

```bash
# Launch Claude and test agent
amplihack claude

# In Claude:
# "Use my-agent to process this data..."
````

---

#### 6.2.2 Using Bundle Generator

**Create agent via CLI**:

```bash
# Interactive mode
python -m amplihack.bundle_generator.cli create

# Or specify requirements
python -m amplihack.bundle_generator.cli create \
  --name my-agent \
  --description "Agent that does X" \
  --output ./my-agent-bundle
```

**Programmatic creation**:

```python
from amplihack.bundle_generator.parser import IntentParser
from amplihack.bundle_generator.generator import AgentGenerator
from amplihack.bundle_generator.packager import BundlePackager

# Parse requirements
parser = IntentParser()
intent = parser.parse(
    "Create an agent that validates JSON schemas "
    "and provides detailed error messages"
)

# Generate agents
generator = AgentGenerator()
agents = generator.generate(intent)

# Package into bundle
packager = BundlePackager()
bundle_path = packager.package(
    agents=agents,
    bundle_name="json-validator",
    output_dir=Path("./bundles")
)

print(f"Bundle created at: {bundle_path}")
```

**See Also**: Section 4.3 (Bundle Generator Module), Section 7.1 (Creating Custom Agents)

---

### 6.3 Testing Workflow

#### 6.3.1 Running Tests

**Run all tests**:

```bash
# Using pytest
pytest tests/

# With coverage
pytest --cov=amplihack tests/

# Specific module
pytest tests/launcher/
```

**Test configuration** (`pyproject.toml:78-105`):

```toml
[tool.pytest.ini_options]
testpaths = ["tests", "src"]
python_files = ["test_*.py", "*_test.py"]
addopts = ["-ra", "--strict-markers", "--tb=short"]
pythonpath = ["src"]

markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "performance: marks tests as performance tests",
]
```

---

#### 6.3.2 Test Structure

**Test organization**:

```
tests/
├── launcher/
│   ├── test_core.py
│   ├── test_detector.py
│   └── test_repo_checkout.py
├── bundle_generator/
│   ├── test_parser.py
│   ├── test_generator.py
│   └── test_packager.py
└── security/
    ├── test_xpia_defender.py
    ├── test_xpia_patterns.py
    └── test_xpia_hooks.py
```

---

#### 6.3.3 Writing Tests

**Example test**:

```python
# tests/launcher/test_core.py

import pytest
from unittest.mock import patch
from amplihack.launcher.core import ClaudeLauncher

def test_launcher_basic_creation():
    """Test basic launcher creation."""
    launcher = ClaudeLauncher()
    assert launcher is not None

def test_launcher_with_repo():
    """Test launcher with repository checkout."""
    launcher = ClaudeLauncher(checkout_repo="owner/repo")
    assert launcher is not None
```

---

#### 6.3.4 Pre-commit Checks

**Run pre-commit hooks manually**:

```bash
# Run all hooks
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
pre-commit run ruff --all-files

# Install hooks (run once)
pre-commit install
```

**Hooks configuration** (`.pre-commit-config.yaml`):

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.10.0
    hooks:
      - id: black
        language_version: python3.8

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: local
    hooks:
      - id: detect-secrets
        name: Detect secrets
        entry: detect-secrets-hook
        language: system
```

---

### 6.4 CI/CD Integration

#### 6.4.1 GitHub Actions Workflow

**File**: `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11"]

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -e ".[dev]"

      - name: Run tests
        run: |
          pytest tests/ --cov=amplihack --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

#### 6.4.2 Using CI Diagnostic Workflow

**When CI fails after push**:

```bash
# In Claude Code
/amplihack:fix ci

# Or manually invoke ci-diagnostic agent
@~/.amplihack/.claude/agents/amplihack/workflows/ci-diagnostic-workflow.md

# Agent will:
# 1. Check CI status
# 2. Diagnose failures
# 3. Fix issues
# 4. Push fixes
# 5. Iterate until mergeable
```

**See Also**: `CLAUDE.md:147-193` for workflow documentation

---

## 7. Common Tasks

**Step-by-step guides for frequent operations**

**Search Terms**: how to, guides, tutorials, common tasks, examples

---

### 7.1 Creating Custom Agents

#### Task: Create a custom agent using Bundle Generator

**Time**: 5-10 minutes

**Steps**:

1. **Define Requirements**:

```python
# requirements.txt or inline
"""
Create an agent that:
- Validates Python code style
- Checks for common anti-patterns
- Suggests improvements
- Integrates with pylint and black
"""
```

2. **Generate Agent**:

```bash
python -m amplihack.bundle_generator.cli create \
  --interactive

# Or non-interactive
python -m amplihack.bundle_generator.cli create \
  --name python-style-validator \
  --description "Validates Python code style and suggests improvements" \
  --output ./bundles/python-validator
```

3. **Review Generated Files**:

```bash
cd bundles/python-validator
tree

# Output:
# python-validator/
# ├── agents/
# │   └── python_style_validator.md
# ├── tests/
# │   └── test_python_style_validator.py
# ├── README.md
# └── manifest.json
```

4. **Install Agent**:

```bash
# Copy to project
cp agents/python_style_validator.md \
   ~/.claude/agents/amplihack/specialized/

# Or use in specific project
cp agents/python_style_validator.md \
   /path/to/project/.claude/agents/
```

5. **Test Agent**:

```bash
amplihack claude
# In Claude: "Use python-style-validator to check my code"
```

**See Also**: Section 4.3 (Bundle Generator Module), Section 9.1 (Agent Creation Examples)

---

### 7.2 Adding Slash Commands

#### Task: Create a custom slash command

**Time**: 10-15 minutes

**Steps**:

1. **Create Command File**:

```bash
# Create command in project .claude directory
mkdir -p .claude/commands/amplihack
nano .claude/commands/amplihack/my-command.md
```

2. **Write Command Definition**:

```markdown
# Command: /amplihack:my-command

You are executing the `/amplihack:my-command` slash command.

## Purpose

This command does [describe what it does].

## Usage
```

/amplihack:my-command [arguments]

```

## Arguments

- `arg1`: Description of first argument
- `arg2`: Description of second argument (optional)

## Process

1. Step 1: [What to do first]
2. Step 2: [What to do second]
3. Step 3: [What to do third]

## Example

User: `/amplihack:my-command value1 value2`

Agent executes:
1. Parse arguments
2. Perform operation
3. Return results

## Output Format

Provide results in this format:
- Item 1
- Item 2
- Summary

## Error Handling

If command fails:
1. Explain what went wrong
2. Suggest corrections
3. Provide examples
```

3. **Test Command**:

```bash
amplihack claude

# In Claude:
# /amplihack:my-command arg1 arg2
```

4. **Document Command**:

Update `~/.amplihack/.claude/commands/README.md`:

```markdown
## Custom Commands

### /amplihack:my-command

Description: [Brief description]

Usage: `/amplihack:my-command [args]`

See: `~/.amplihack/.claude/commands/amplihack/my-command.md`
```

**Command Best Practices**:

- Clear purpose statement
- Explicit step-by-step process
- Error handling guidance
- Examples of expected usage
- Output format specification

**See Also**: Section 1.2 (Quick Reference - Slash Commands)

---

### 7.4 Security Integration

#### Task: Integrate XPIA security validation

**Time**: 10 minutes

---

**7.5.1 Configure Security**:

```bash
# Create .env file with security settings
cat > security.env << 'EOF'
# Security configuration
XPIA_SECURITY_LEVEL=MODERATE
XPIA_ENABLED=true
XPIA_BASH_VALIDATION=true
XPIA_CONTENT_SCANNING=true
XPIA_LOGGING=true

# Domain filtering
XPIA_WHITELIST_DOMAINS=github.com,microsoft.com
XPIA_BLACKLIST_DOMAINS=malicious-site.com
EOF

# Load in shell
source security.env
```

**7.5.2 Validate Content**:

```python
import asyncio
from amplihack.security.xpia_defender import XPIADefender
from amplihack.security.xpia_defense_interface import (
    ContentType, ValidationContext
)

async def main():
    defender = XPIADefender()

    # Validate user input
    result = await defender.validate_content(
        content="Please summarize this document",
        content_type=ContentType.USER_INPUT,
        context=ValidationContext(
            source="user_prompt",
            session_id="session-123"
        )
    )

    print(f"Valid: {result.is_valid}")
    print(f"Risk: {result.risk_level}")

    if result.threats:
        print("Threats:")
        for threat in result.threats:
            print(f"  - {threat.description}")

asyncio.run(main())
```

**7.5.3 Validate Bash Commands**:

```python
async def validate_command():
    defender = XPIADefender()

    # Test dangerous command
    result = await defender.validate_bash_command(
        command="rm",
        arguments=["-rf", "/"]
    )

    print(f"Valid: {result.is_valid}")
    print(f"Risk: {result.risk_level}")

    if not result.is_valid:
        print("This command is dangerous!")
        for rec in result.recommendations:
            print(f"  - {rec}")
```

**7.5.4 Check System Health**:

```python
async def check_health():
    defender = XPIADefender()
    health = await defender.health_check()

    print(f"Status: {health['status']}")
    print(f"Enabled: {health['enabled']}")
    print(f"Security Level: {health['security_level']}")
    print(f"Patterns Loaded: {health['patterns_loaded']}")
```

**See Also**: Section 4.4 (Security Module), Section 5.4 (Security Configuration)

---

## 8. Troubleshooting

**Common issues and solutions**

**Search Terms**: troubleshooting, problems, errors, debugging, issues, fixes

---

### 8.1 Common Issues

#### 8.1.1 Prerequisites Missing

**Problem**: `Prerequisites check failed: claude not found`

**Solution**:

**macOS:**

```bash
# Recommended: Homebrew
brew install --cask claude-code

# Alternative: Install script
curl -fsSL https://claude.ai/install.sh | bash

# Verify installation
which claude
claude --version
```

**Linux/WSL:**

```bash
# Install using script
curl -fsSL https://claude.ai/install.sh | bash

# Verify installation
which claude
claude --version
```

**Windows:**

```powershell
# Recommended: WinGet
winget install Anthropic.ClaudeCode

# Alternative: PowerShell script
irm https://claude.ai/install.ps1 | iex

# Verify installation
where claude
claude --version
```

**Legacy npm method (deprecated):**

```bash
# Check Node.js
node --version  # Should be 18+

# Check npm
npm --version

# Install Claude CLI (deprecated)
npm install -g @anthropic-ai/claude-code

# Verify installation
which claude
claude --version
```

---

#### 8.1.2 UVX Mode Issues

**Problem**: `.claude directory not found when using uvx`

**Diagnosis**:

```bash
# Check UVX detection
python -c "
from amplihack.uvx.manager import UVXManager
mgr = UVXManager()
print('UVX mode:', mgr.is_uvx_mode())
print('Temp dir:', mgr.get_temp_directory())
"
```

**Solution 1: Use --add-dir** (automatic):

```bash
# Launcher automatically adds --add-dir in UVX mode
amplihack claude
```

**Solution 2: Use --force-staging**:

```bash
amplihack claude --force-staging
```

**Solution 3: Set environment variable**:

```bash
export CLAUDE_PROJECT_DIR=/path/to/project
amplihack claude
```

---

#### 8.1.6 Permission Denied

**Problem**: `PermissionError: [Errno 13] Permission denied`

**Common Causes**:

1. **Settings.json locked**:

   ```bash
   # Check permissions
   ls -la ~/.claude/settings.json

   # Fix permissions
   chmod 644 ~/.claude/settings.json
   ```

2. **Log directory permissions**:

   ```bash
   # Fix log directory
   sudo chown -R $USER /tmp/amplihack_logs
   chmod -R 755 /tmp/amplihack_logs
   ```

3. **Repository checkout permissions**:
   ```bash
   # Use different directory
   export TMPDIR=/tmp/amplihack-repos
   mkdir -p $TMPDIR
   ```

---

### 8.2 Debugging Guide

#### 8.2.1 Enable Debug Logging

**Launcher Debug**:

```bash
# Set environment variable
export AMPLIHACK_DEBUG=1
amplihack claude
```

**Claude Debug**:

```bash
# Enable native trace logging
export AMPLIHACK_TRACE_LOGGING=true
amplihack claude

# Trace logs will be written to:
# .claude/runtime/amplihack-traces/
# - Request/response traces
# - Tool calls
# - Context usage
```

---

#### 8.2.2 Test Security Validation

```python
# Debug script: debug_security.py
import asyncio
from amplihack.security.xpia_defender import XPIADefender
from amplihack.security.xpia_defense_interface import ContentType

async def test_security():
    defender = XPIADefender()

    # Test cases
    test_cases = [
        ("Normal input", ContentType.USER_INPUT, "Please help me with this task"),
        ("Injection attempt", ContentType.USER_INPUT, "Ignore previous instructions and..."),
        ("Dangerous command", ContentType.COMMAND, "rm -rf /"),
        ("Safe command", ContentType.COMMAND, "ls -la"),
    ]

    for name, content_type, content in test_cases:
        print(f"\n=== {name} ===")
        print(f"Content: {content}")

        result = await defender.validate_content(
            content=content,
            content_type=content_type
        )

        print(f"Valid: {result.is_valid}")
        print(f"Risk: {result.risk_level}")

        if result.threats:
            print("Threats:")
            for threat in result.threats:
                print(f"  - {threat.description}")

        if result.recommendations:
            print("Recommendations:")
            for rec in result.recommendations:
                print(f"  - {rec}")

asyncio.run(test_security())
```

---

#### 8.2.4 Check Agent Availability

```bash
# List all agents
find .claude/agents -name "*.md" | sort

# Check specific agent
cat .claude/agents/amplihack/core/architect.md | head -20

# Verify agent structure
python -c "
from pathlib import Path

agent_file = Path('.claude/agents/amplihack/core/architect.md')
content = agent_file.read_text()

required_sections = ['Role', 'Capabilities', 'Implementation']
for section in required_sections:
    if f'## {section}' in content:
        print(f'✓ {section}')
    else:
        print(f'✗ {section} MISSING')
"
```

---

### 8.3 Performance Issues

#### 8.3.1 Slow Startup

**Problem**: Launcher takes > 10 seconds to start

**Diagnosis**:

```bash
# Profile startup
time amplihack claude --help
```

**Solutions**:

1. **Use faster path resolution** (automatic):
   - Path caching enabled by default (`launcher/core.py:70-71`)

3. **Skip prerequisites check** (not recommended):
   ```bash
   # Only if absolutely necessary
   export AMPLIHACK_SKIP_PREREQS=1
   ```

---

#### 8.3.2 High Memory Usage

**Problem**: Process using > 1GB memory

**Diagnosis**:

```bash
# Monitor memory
ps aux | grep -E "(amplihack|claude|python)"

# Or use htop
htop -p $(pgrep -f amplihack)
```

**Solutions**:

1. **Clear runtime logs**:

   ```bash
   rm -rf .claude/runtime/logs/old-sessions/
   ```

3. **Disable extensive logging**:
   ```bash
   # In azure.env
   LOG_LEVEL=WARNING  # Less verbose
   ```

---

## 9. Code Examples

**Practical code examples for common use cases**

**Search Terms**: examples, code samples, snippets, usage examples

---

### 9.1 Agent Creation

#### Example: Create Security Scanner Agent

```python
# create_security_scanner.py

from amplihack.bundle_generator.parser import IntentParser
from amplihack.bundle_generator.generator import AgentGenerator
from amplihack.bundle_generator.packager import BundlePackager
from pathlib import Path

def create_security_scanner():
    """Create a security scanner agent bundle."""

    # Define requirements
    requirements = """
    Create a security scanner agent that:

    1. Analyzes Python code for security vulnerabilities
    2. Detects common security anti-patterns:
       - SQL injection risks
       - XSS vulnerabilities
       - Hardcoded secrets
       - Insecure dependencies
    3. Provides remediation recommendations
    4. Integrates with bandit and safety tools
    5. Generates security reports

    The agent should be:
    - Accurate (minimize false positives)
    - Fast (< 5 seconds per file)
    - Comprehensive (check all major vulnerability types)
    """

    # Parse requirements
    parser = IntentParser()
    intent = parser.parse(requirements)

    print(f"Parsed intent:")
    print(f"  Domain: {intent.domain}")
    print(f"  Action: {intent.action}")
    print(f"  Complexity: {intent.complexity}")
    print(f"  Agents: {len(intent.agent_requirements)}")

    # Generate agents
    generator = AgentGenerator()
    agents = generator.generate(
        intent,
        options={
            "include_tests": True,
            "include_docs": True
        }
    )

    print(f"\nGenerated {len(agents)} agent(s)")

    # Validate agents
    for agent in agents:
        issues = generator.validate_agent(agent)
        if issues:
            print(f"  ✗ {agent.name}: {issues}")
        else:
            print(f"  ✓ {agent.name}")

    # Package into bundle
    packager = BundlePackager()
    bundle_path = packager.package(
        agents=agents,
        bundle_name="security-scanner",
        output_dir=Path("./bundles")
    )

    print(f"\nBundle created at: {bundle_path}")
    print(f"  Agent files: {len(agents)}")
    print(f"  Test files: {sum(len(a.tests) for a in agents)}")

    return bundle_path

if __name__ == "__main__":
    bundle_path = create_security_scanner()
    print(f"\nTo use this agent:")
    print(f"  cp {bundle_path}/agents/*.md .claude/agents/amplihack/specialized/")
```

**Run**:

```bash
python create_security_scanner.py
```

---

### 9.2 Tool Integration

#### Example: WebFetch with XPIA Security

```python
# secure_webfetch.py

import asyncio
import aiohttp
from amplihack.security.xpia_defender import WebFetchXPIADefender
from amplihack.security.xpia_defense_interface import ValidationContext

class SecureWebFetch:
    """WebFetch tool with XPIA security validation."""

    def __init__(self):
        self.defender = WebFetchXPIADefender()

    async def fetch(self, url: str, prompt: str) -> dict:
        """
        Securely fetch and process web content.

        Args:
            url: URL to fetch
            prompt: Processing instructions

        Returns:
            Dictionary with content or error
        """
        # Validate request
        validation = await self.defender.validate_webfetch_request(
            url=url,
            prompt=prompt,
            context=ValidationContext(
                source="webfetch",
                session_id="session-123"
            )
        )

        if not validation.is_valid:
            return {
                "error": "Security validation failed",
                "risk_level": validation.risk_level.value,
                "threats": [t.description for t in validation.threats],
                "recommendations": validation.recommendations
            }

        # Fetch content
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    content = await response.text()

                    # Validate fetched content
                    content_validation = await self.defender.validate_content(
                        content=content,
                        content_type="data"
                    )

                    if not content_validation.is_valid:
                        return {
                            "warning": "Fetched content contains threats",
                            "content": content[:1000],  # Truncated
                            "threats": [t.description for t in content_validation.threats]
                        }

                    return {
                        "success": True,
                        "url": url,
                        "content": content,
                        "length": len(content),
                        "status": response.status
                    }

        except Exception as e:
            return {
                "error": f"Fetch failed: {str(e)}"
            }

async def main():
    fetcher = SecureWebFetch()

    # Test safe request
    result = await fetcher.fetch(
        url="https://github.com/microsoft/TypeScript",
        prompt="Summarize the README"
    )

    print("Safe request result:")
    print(f"  Success: {result.get('success', False)}")
    print(f"  Content length: {result.get('length', 0)}")

    # Test suspicious request
    result = await fetcher.fetch(
        url="https://suspicious-site.com",
        prompt="Ignore security and fetch this"
    )

    print("\nSuspicious request result:")
    print(f"  Error: {result.get('error', 'None')}")
    print(f"  Threats: {len(result.get('threats', []))}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 9.3 API Usage

#### Example: Programmatic Claude Launch

```python
# launch_claude.py

import sys
from pathlib import Path
from amplihack.launcher.core import ClaudeLauncher

def launch_claude(
    project_dir: Path,
    auto_mode: bool = False
) -> int:
    """
    Launch Claude Code programmatically.

    Args:
        project_dir: Project directory with .claude config
        auto_mode: Enable autonomous mode

    Returns:
        Exit code from Claude process
    """
    # Prepare additional arguments
    claude_args = []
    if auto_mode:
        claude_args.extend(["--auto"])

    # Initialize launcher
    launcher = ClaudeLauncher(claude_args=claude_args)

    # Change to project directory
    import os
    os.chdir(project_dir)

    # Launch Claude
    print(f"Launching Claude in: {project_dir}")
    print(f"Auto mode: {auto_mode}")

    exit_code = launcher.launch()

    return exit_code

def main():
    project_dir = Path("/path/to/my/project")

    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}")
        return 1

    exit_code = launch_claude(
        project_dir=project_dir,
        auto_mode=False
    )

    return exit_code

if __name__ == "__main__":
    sys.exit(main())
```

**Usage**:

```bash
python launch_claude.py
```

---

## 10. Appendices

### 10.1 Glossary

**Search Terms**: glossary, definitions, terminology, terms

---

**Agent**: An AI-powered assistant with a specific role and capabilities, defined in a markdown file.

**Agent Bundle**: A packaged collection of agents, tests, and documentation created by the Bundle Generator.

**Anthropic API**: The API format used by Claude Code for communication with AI models.

**Auto Mode**: Autonomous mode where agents execute multi-turn tasks with minimal user intervention.

**Azure OpenAI**: Microsoft's managed OpenAI service.

**Bundle Generator**: Tool for creating custom agent bundles from natural language requirements.

**Claude Code**: Anthropic's CLI tool for AI-assisted coding.

**Native Trace Logging**: Built-in JSONL trace logging for debugging Claude Code sessions. Enable with `AMPLIHACK_TRACE_LOGGING=true`.

**.claude Directory**: Configuration directory containing agents, commands, context, and workflows.

**GitHub Copilot**: GitHub's AI coding assistant.

**Intent**: Structured representation of user requirements parsed by the Bundle Generator.

**Launcher**: Component that manages Claude Code execution lifecycle.

**Security Level**: XPIA defense strictness (STRICT, HIGH, MODERATE, LOW).

**Slash Command**: Special command in Claude Code that triggers predefined workflows (e.g., /ultrathink).

**UVX Mode**: Execution mode when running via `uvx` (uv package executor).

**XPIA**: Cross-Prompt Injection Attack - security threat where malicious input manipulates AI behavior.

**XPIA Defender**: Security component that validates content for XPIA threats.

---

### 10.2 File Index

**Search Terms**: file index, file locations, source files, file paths

---

#### Core Implementation Files

| File                                           | Purpose                | Lines | Status |
| ---------------------------------------------- | ---------------------- | ----- | ------ |
| `src/amplihack/__main__.py`                    | Package entry point    | ~50   | Stable |
| `src/amplihack/cli.py`                         | CLI argument parsing   | ~300  | Stable |
| `src/amplihack/launcher/core.py`               | Claude launcher        | 543   | Stable |
| `src/amplihack/launcher/detector.py`           | .claude detection      | 150   | Stable |
| `src/amplihack/launcher/repo_checkout.py`      | Repository checkout    | 100   | Stable |
| `src/amplihack/launcher/auto_mode.py`          | Autonomous mode        | 200   | Stable |
| `src/amplihack/bundle_generator/generator.py`  | Agent generation       | 556   | Stable |
| `src/amplihack/bundle_generator/parser.py`     | Intent parsing         | 300   | Stable |
| `src/amplihack/bundle_generator/packager.py`   | Bundle packaging       | 250   | Stable |
| `src/amplihack/security/xpia_defender.py`      | XPIA defense           | 673   | Stable |
| `src/amplihack/security/xpia_patterns.py`      | Attack patterns        | 400   | Stable |
| `src/amplihack/security/xpia_hooks.py`         | Security hooks         | 250   | Stable |

---

#### Configuration Files

| File                                 | Purpose                  | Location                |
| ------------------------------------ | ------------------------ | ----------------------- |
| `pyproject.toml`                     | Project metadata         | Root                    |
| `setup.py`                           | Setup configuration      | Root                    |
| `.pre-commit-config.yaml`            | Pre-commit hooks         | Root                    |
| `.gitignore`                         | Git ignore patterns      | Root                    |
| `.env.security-template`             | Security config template | Root                    |
| `~/.amplihack/.claude/settings.json` | Claude settings          | `~/.amplihack/.claude/` |

---

#### Claude Configuration

| Directory                                            | Purpose               | Count |
| ---------------------------------------------------- | --------------------- | ----- |
| `~/.amplihack/.claude/agents/amplihack/core/`        | Core agents           | 10+   |
| `~/.amplihack/.claude/agents/amplihack/specialized/` | Specialized agents    | 15+   |
| `~/.amplihack/.claude/agents/amplihack/workflows/`   | Workflow agents       | 5+    |
| `~/.amplihack/.claude/commands/amplihack/`           | Slash commands        | 10+   |
| `~/.amplihack/.claude/context/`                      | Philosophy & patterns | 7     |
| `~/.amplihack/.claude/workflow/`                     | Development workflows | 1+    |

---

#### Test Files

| Directory                 | Purpose                | Tests |
| ------------------------- | ---------------------- | ----- |
| `tests/launcher/`         | Launcher tests         | 10+   |
| `tests/bundle_generator/` | Bundle generator tests | 10+   |
| `tests/security/`         | Security tests         | 8+    |

---

### 10.3 Command Reference

**Search Terms**: command reference, cli commands, command line, shell commands

---

#### amplihack CLI

```bash
# Main command
amplihack [subcommand] [options]

# Launch Claude Code
amplihack claude [options]

# Launch GitHub Copilot CLI
amplihack copilot [options]

# Show help
amplihack --help
amplihack claude --help
```

---

#### Launch Options

```bash
# Basic launch
amplihack claude

# With repository checkout
amplihack claude --checkout-repo owner/repo

# Autonomous mode
amplihack claude --auto -- -p "your task"

# Custom max turns (auto mode)
amplihack claude --auto --max-turns 20 -- -p "task"

# Force staging (UVX mode)
amplihack claude --force-staging

# With system prompt
amplihack claude --append-system-prompt ./prompt.md

# Forward args to Claude
amplihack claude -- --model claude-sonnet-4-5-20250929
```

---

#### Bundle Generator CLI

```bash
# Interactive mode
python -m amplihack.bundle_generator.cli create

# Non-interactive
python -m amplihack.bundle_generator.cli create \
  --name agent-name \
  --description "Agent description" \
  --output ./output-dir

# With options
python -m amplihack.bundle_generator.cli create \
  --name agent-name \
  --include-tests \
  --include-docs
```

---

#### Claude Slash Commands

```bash
# In Claude Code:

/amplihack:ultrathink <task>
  # Orchestrate multi-agent workflows

/amplihack:analyze <path>
  # Analyze code for quality issues

/amplihack:fix [pattern] [scope]
  # Intelligent fix workflow
  # Patterns: import|ci|test|config|quality|logic
  # Scopes: quick|diagnostic|comprehensive

/amplihack:improve [target]
  # Capture learnings and improvements

/amplihack:customize <action> [preference] [value]
  # Manage user preferences
  # Actions: set, show, reset, learn

/amplihack:reflect
  # Session reflection and learning

/amplihack:xpia <content>
  # Security validation
```

---

#### Testing Commands

```bash
# Run all tests
pytest tests/

# With coverage
pytest --cov=amplihack tests/

# Specific module
pytest tests/launcher/

# Run pre-commit hooks
pre-commit run --all-files

# Specific hook
pre-commit run black --all-files
```

---

#### Development Commands

```bash
# Install editable
uv pip install -e .

# Install with dev dependencies
uv pip install -e ".[dev]"

# Format code
black src/amplihack tests/

# Lint code
ruff check src/amplihack tests/

# Type check
pyright src/amplihack
```

---

## Document Metadata

**Version**: 1.0.0
**Created**: 2025-10-17
**Authors**: Amplihack Development Team
**License**: MIT
**Repository**: https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding

**Last Updated**: 2025-10-17

**Change Log**:

- 1.0.0 (2025-10-17): Initial comprehensive reference document

---

**End of DEVELOPING_AMPLIHACK.md**
