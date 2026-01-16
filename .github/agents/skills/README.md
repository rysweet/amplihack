# GitHub Copilot CLI Custom Agents

Custom agents generated from amplihack skills for use with GitHub Copilot CLI.

**Total agents:** 58

## Usage

Invoke agents in Copilot CLI:

```bash
gh copilot agent <agent-name> "<your request>"
```

## Available Agents

### Analyst
*Perspective analysts (anthropologist, economist, etc.)*

- **anthropologist-analyst**: |
- **biologist-analyst**: |
- **chemist-analyst**: |
- **computer-scientist-analyst**: |
- **cybersecurity-analyst**: |
- **economist-analyst**: |
- **engineer-analyst**: |
- **environmentalist-analyst**: |
- **epidemiologist-analyst**: |
- **ethicist-analyst**: |
- **futurist-analyst**: |
- **historian-analyst**: |
- **indigenous-leader-analyst**: |
- **journalist-analyst**: |
- **lawyer-analyst**: |
- **novelist-analyst**: |
- **philosopher-analyst**: |
- **physicist-analyst**: |
- **poet-analyst**: |
- **political-scientist-analyst**: |
- **psychologist-analyst**: |
- **sociologist-analyst**: |
- **urban-planner-analyst**: |

### Code Quality
*Code review and quality assurance*

- **code-smell-detector**: |
- **design-patterns-expert**: |
- **module-spec-generator**: |
- **outside-in-testing**: |
- **pr-review-assistant**: |
- **test-gap-analyzer**: |

### Documentation
*Documentation and visualization*

- **documentation-writing**: Writing clear, discoverable software documentation following the Eight Rules and Diataxis framework. Use when creating README files, API docs, tutorials, how-to guides, or any project documentation. Automatically enforces docs/ location, linking requirements, and runnable examples.
- **mermaid-diagram-generator**: |
- **storytelling-synthesizer**: |

### Domain Specialized
*Specialized domain expertise*

- **pm-architect**: Expert project manager orchestrating backlog-curator, work-delegator, workstream-coordinator, and roadmap-strategist sub-skills. Coordinates complex software projects through delegation and strategic oversight. Activates when managing projects, coordinating work, or tracking overall progress.
- **roadmap-strategist**: Expert strategist managing project roadmaps, goals, milestones, and strategic direction. Tracks goal progress, ensures alignment, and provides strategic recommendations. Activates when planning roadmaps, setting goals, tracking milestones, or discussing strategic direction.

### Integration
*External service integrations (Azure, DevOps)*

- **azure-admin**: Agent for azure-admin
- **azure-devops**: Complete Azure DevOps automation - boards, repos, pipelines, artifacts
- **azure-devops-cli**: Agent for azure-devops-cli

### Management
*Context and resource management*

- **context_management**: |
- **mcp-manager**: Conversational interface for managing MCP (Model Context Protocol) server configurations in Claude Code
- **remote-work**: Execute amplihack work on remote Azure VMs with automatic region and resource selection

### Orchestration
*Meta-orchestration and delegation*

- **goal-seeking-agent-pattern**: |
- **skill-builder**: Creates, refines, and validates Claude Code skills following amplihack philosophy and official best practices. Automatically activates when building, creating, generating, or designing new skills.
- **ultrathink-orchestrator**: Auto-invokes ultrathink workflow for any work request (default orchestrator)
- **work-delegator**: Expert delegation specialist that creates comprehensive context packages for coding agents, analyzes requirements, identifies relevant files, and generates clear instructions. Activates when delegating work, assigning tasks, creating delegation packages, or preparing agent instructions.
- **workstream-coordinator**: Expert workstream coordinator managing multiple concurrent tasks, tracking progress, detecting conflicts and stalls, analyzing dependencies, and ensuring smooth parallel execution. Activates when coordinating workstreams, tracking progress, checking status, or managing concurrent work.

### Productivity
*Productivity and synthesis*

- **backlog-curator**: Expert backlog manager that prioritizes work using multi-criteria scoring, analyzes dependencies, and recommends optimal next tasks. Activates when managing backlogs, prioritizing work, adding items, or analyzing what to work on next.
- **email-drafter**: |
- **knowledge-extractor**: |
- **learning-path-builder**: |
- **meeting-synthesizer**: |

### Workflow
*Multi-step workflow orchestration*

- **cascade-workflow**: Graceful degradation through cascading fallback strategies - ensures system always completes while maintaining acceptable functionality
- **consensus-voting**: Multi-agent consensus voting with domain-weighted expertise for critical decisions requiring structured validation
- **debate-workflow**: Structured multi-perspective debate for important architectural decisions and complex trade-offs
- **default-workflow**: Development workflow for features, bugs, refactoring. Auto-activates for multi-file implementations.
- **investigation-workflow**: |
- **n-version-workflow**: N-version programming for critical implementations - generates N independent solutions and selects the best through comparison
- **philosophy-compliance-workflow**: Philosophy compliance guardian - ensures code aligns with amplihack's ruthless simplicity, brick philosophy, and Zen-like minimalism through systematic review
- **quality-audit-workflow**: Comprehensive codebase quality audit with parallel agent orchestration, GitHub issue creation, automated PR generation per issue, and PM-prioritized recommendations. Use for code review, refactoring audits, technical debt analysis, module quality assessment, or codebase health checks.

## Integration

These agents integrate with:
- GitHub Copilot CLI tool invocation
- amplihack MCP server for enhanced capabilities
- Local file system access
- Terminal command execution

## Generated

Generated from 58 amplihack skills using `amplihack sync-skills`.
