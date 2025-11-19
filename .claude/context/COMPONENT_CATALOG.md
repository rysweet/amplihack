# Amplihack Component Catalog

Auto-generated from frontmatter metadata.

**Last Updated**: 2025-11-19 03:43:11

This catalog provides a comprehensive reference to all workflows, commands, skills, and agents in the amplihack framework.

---

## Workflows

**Total**: 9 workflows

### CASCADE_WORKFLOW (v1.0.0)

**Description**: Graceful degradation workflow with 3-level fallback cascade (primary → secondary → tertiary)

**Steps/Phases**: 7

**Phases**: cascade-level-definition, primary-attempt, secondary-fallback, tertiary-guarantee, degradation-reporting, metrics-logging, continuous-optimization

**Location**: `.claude/workflow/CASCADE_WORKFLOW.md`

### CONSENSUS_WORKFLOW (v1.0.0)

**Description**: Enhanced 15-step workflow with multi-agent consensus at critical decision points

**Steps/Phases**: 15

**Phases**: requirements-with-debate, design-with-consensus, n-version-implementation, expert-panel-refactoring, expert-panel-review, final-consensus-validation

**Location**: `.claude/workflow/CONSENSUS_WORKFLOW.md`

### DEBATE_WORKFLOW (v1.0.0)

**Description**: Multi-agent structured debate for complex decisions requiring diverse perspectives

**Steps/Phases**: 8

**Phases**: decision-framing, perspective-initialization, initial-positions, challenge-and-respond, common-ground-synthesis, facilitator-synthesis, decision-documentation, implementation

**Location**: `.claude/workflow/DEBATE_WORKFLOW.md`

### DEFAULT_WORKFLOW (v1.0.0)

**Description**: Standard 15-step workflow for feature development, bug fixes, and refactoring

**Steps/Phases**: 15

**Phases**: requirements-clarification, design, implementation, testing, review, merge

**Location**: `.claude/workflow/DEFAULT_WORKFLOW.md`

### INVESTIGATION_WORKFLOW (v1.0.0)

**Description**: 6-phase workflow for systematic investigation and knowledge excavation

**Steps/Phases**: 6

**Phases**: scope-definition, exploration-strategy, parallel-deep-dives, verification, synthesis, knowledge-capture

**Location**: `.claude/workflow/INVESTIGATION_WORKFLOW.md`

### N_VERSION_WORKFLOW (v1.0.0)

**Description**: N-version programming for critical code - generate multiple independent implementations and select best

**Steps/Phases**: 7

**Phases**: common-context-preparation, n-independent-implementations, collection-and-comparison, review-and-evaluation, selection-or-synthesis, final-implementation, learning-documentation

**Location**: `.claude/workflow/N_VERSION_WORKFLOW.md`

### PHILOSOPHY_COMPLIANCE_WORKFLOW (v1.0.0)

**Description**: 5-phase workflow for validating code against amplihack philosophy principles

**Steps/Phases**: 5

**Phases**: scope-identification, principle-loading, compliance-analysis, violation-remediation, verification

**Location**: `.claude/workflow/PHILOSOPHY_COMPLIANCE_WORKFLOW.md`

### CI_FIX_TEMPLATE (v1.0.0)

**Description**: Template for fixing CI/CD pipeline failures, build issues, and deployment problems

**Steps/Phases**: 3

**Phases**: quick-assessment, solution-application, validation

**Location**: `.claude/workflow/fix/ci-fix-template.md`

### IMPORT_FIX_TEMPLATE (v1.0.0)

**Description**: Template for fixing import errors, circular dependencies, and module resolution issues

**Steps/Phases**: 3

**Phases**: quick-assessment, solution-application, validation

**Location**: `.claude/workflow/fix/import-fix-template.md`

---

## Commands

**Total**: 33 commands

### /amplihack:analyze (v1.0.0)

**Description**: Comprehensive code analysis and philosophy compliance review

**Triggers**: analyze this code, check philosophy compliance, review for simplicity, assess architecture

**Invokes**:

- subagent: `.claude/agents/amplihack/specialized/analyzer.md`
- subagent: `.claude/agents/amplihack/specialized/philosophy-guardian.md`

**Location**: `.claude/commands/amplihack/analyze.md`

### /amplihack:auto (v1.0.0)

**Description**: Autonomous multi-turn agentic loop with clarify-plan-execute-evaluate workflow

**Triggers**: complex multi-step implementation, iterative refinement needed, path not immediately clear, self-correction required

**Invokes**:

- command: `N/A`

**Location**: `.claude/commands/amplihack/auto.md`

### /amplihack:cascade (v1.0.0)

**Description**: Fallback cascade pattern for resilient operations with graceful degradation

**Triggers**: need fallback strategy, external API reliability, graceful degradation needed, multiple viable approaches

**Invokes**:

- workflow: `.claude/workflow/CASCADE_WORKFLOW.md`

**Location**: `.claude/commands/amplihack/cascade.md`

### /amplihack:customize (v1.0.0)

**Description**: Manage user-specific preferences and customizations

**Triggers**: change my preferences, customize workflow, set verbosity to

**Invokes**:

- file: `.claude/context/USER_PREFERENCES.md`

**Location**: `.claude/commands/amplihack/customize.md`

### /amplihack:debate (v1.0.0)

**Description**: Multi-agent debate pattern for complex decisions with structured perspectives

**Triggers**: need multiple perspectives, complex decision needed, debate trade-offs, architectural choice

**Invokes**:

- workflow: `.claude/workflow/DEBATE_WORKFLOW.md`
- command: `N/A`

**Location**: `.claude/commands/amplihack/debate.md`

### /amplihack:default-workflow (v1.0.0)

**Description**: Execute DEFAULT_WORKFLOW directly for development tasks without auto-detection

**Triggers**: run default workflow, execute standard workflow, follow development workflow

**Invokes**:

- workflow: `.claude/workflow/DEFAULT_WORKFLOW.md`

**Location**: `.claude/commands/amplihack/default-workflow.md`

### /amplihack:expert-panel (v1.0.0)

**Description**: Byzantine-robust decision-making through parallel expert reviews and voting

**Triggers**: need multiple expert reviews, code review approval gate, design review board, release decision

**Invokes**:

- subagent: `.claude/agents/amplihack/security.md`
- subagent: `.claude/agents/amplihack/optimizer.md`
- subagent: `.claude/agents/amplihack/specialized/philosophy-guardian.md`

**Location**: `.claude/commands/amplihack/expert-panel.md`

### /amplihack:fix (v1.0.0)

**Description**: Intelligent fix workflow with auto-detection and template-based resolution

**Triggers**: fix this error, CI failing, tests broken, import error, something's broken

**Invokes**:

- subagent: `.claude/agents/amplihack/specialized/fix-agent.md`
- subagent: `.claude/agents/amplihack/specialized/pre-commit-diagnostic.md`
- subagent: `.claude/agents/amplihack/specialized/ci-diagnostic-workflow.md`
- command: `N/A`

**Location**: `.claude/commands/amplihack/fix.md`

### /amplihack:improve (v2.0.0)

**Description**: Self-improvement and learning capture with simplicity validation

**Triggers**: improve the system, enhance agents, update patterns, self-improvement

**Invokes**:

- subagent: `.claude/agents/amplihack/specialized/improvement-workflow.md`
- subagent: `.claude/agents/amplihack/specialized/reviewer.md`
- subagent: `.claude/agents/amplihack/security.md`
- command: `N/A`

**Location**: `.claude/commands/amplihack/improve.md`

### /amplihack:ingest-code (v1.0.0)

**Description**: Ingest codebase into Neo4j graph memory for enhanced understanding

**Triggers**: Ingest codebase into graph, Load code into Neo4j, Index codebase for memory, Build code graph

**Location**: `.claude/commands/amplihack/ingest-code.md`

### /amplihack:install (v1.0.0)

**Description**: Install amplihack tools and customizations

**Triggers**: Install amplihack, Setup amplihack tools, Configure amplihack

**Location**: `.claude/commands/amplihack/install.md`

### /amplihack:investigation-workflow (v1.0.0)

**Description**: Execute INVESTIGATION_WORKFLOW directly for research and understanding tasks without auto-detection

**Triggers**: run investigation workflow, execute investigation, research workflow

**Invokes**:

- workflow: `.claude/workflow/INVESTIGATION_WORKFLOW.md`

**Location**: `.claude/commands/amplihack/investigation-workflow.md`

### /amplihack:knowledge-builder (v1.0.0)

**Description**: Build comprehensive knowledge base using Socratic method and web search

**Triggers**: learn about topic deeply, build knowledge base, research comprehensive understanding, generate question hierarchy

**Invokes**:

- command: `N/A`

**Location**: `.claude/commands/amplihack/knowledge-builder.md`

### /amplihack:lock (v1.0.0)

**Description**: Enable continuous work mode to prevent Claude from stopping

**Triggers**: Enable continuous work mode, Work autonomously, Don't stop until done, Keep working through all tasks

**Location**: `.claude/commands/amplihack/lock.md`

### /amplihack:modular-build (v1.0.0)

**Description**: Build self-contained modules using progressive validation pipeline

**Triggers**: Build a module, Create self-contained component, Generate module from spec, Progressive module build

**Location**: `.claude/commands/amplihack/modular-build.md`

### /amplihack:n-version (v1.0.0)

**Description**: N-version programming for critical implementations with 30-65% error reduction

**Triggers**: critical security code, mission-critical feature, high-stakes implementation, multiple implementation attempts

**Invokes**:

- workflow: `.claude/workflow/N_VERSION_WORKFLOW.md`

**Location**: `.claude/commands/amplihack/n-version.md`

### /amplihack:philosophy-workflow (v1.0.0)

**Description**: Execute PHILOSOPHY_COMPLIANCE_WORKFLOW directly for code validation against amplihack philosophy

**Triggers**: run philosophy workflow, check philosophy compliance, validate philosophy

**Invokes**:

- workflow: `.claude/workflow/PHILOSOPHY_COMPLIANCE_WORKFLOW.md`

**Location**: `.claude/commands/amplihack/philosophy-workflow.md`

### /amplihack:reflect (v1.0.0)

**Description**: AI-powered session analysis for continuous improvement

**Triggers**: Analyze session, Run reflection, Identify improvements, Session retrospective

**Location**: `.claude/commands/amplihack/reflect.md`

### /amplihack:skill-builder (v1.0.0)

**Description**: Build new Claude Code skills with guided workflow and agent orchestration

**Triggers**: create a new skill, build a Claude Code skill, generate skill for

**Invokes**:

- subagent: `.claude/agents/amplihack/specialized/prompt-writer.md`
- subagent: `.claude/agents/amplihack/core/architect.md`

**Location**: `.claude/commands/amplihack/skill-builder.md`

### /amplihack:socratic (v1.0.0)

**Description**: Generate deep Socratic questions using Three-Dimensional Attack pattern

**Triggers**: challenge this claim, ask probing questions, socratic questioning, explore assumptions

**Invokes**:

- command: `N/A`

**Location**: `.claude/commands/amplihack/socratic.md`

### /amplihack:transcripts (v1.0.0)

**Description**: Conversation transcript management for context preservation and restoration

**Triggers**: View conversation history, Restore session context, Search past conversations, Find original request

**Location**: `.claude/commands/amplihack/transcripts.md`

### /amplihack:ultrathink (v1.0.0)

**Description**: Deep analysis mode orchestrating multiple agents for complex tasks

**Triggers**: Complex multi-step task, Need deep analysis, Orchestrate workflow, Break down and solve

**Invokes**:

- workflow: `.claude/workflow/DEFAULT_WORKFLOW.md`
- workflow: `.claude/workflow/INVESTIGATION_WORKFLOW.md`

**Location**: `.claude/commands/amplihack/ultrathink.md`

### /amplihack:uninstall (v1.0.0)

**Description**: Uninstall amplihack tools and customizations

**Triggers**: Uninstall amplihack, Remove amplihack tools, Cleanup amplihack

**Location**: `.claude/commands/amplihack/uninstall.md`

### /amplihack:unlock (v1.0.0)

**Description**: Disable continuous work mode to allow Claude to stop normally

**Triggers**: Disable continuous work mode, Stop working autonomously, Exit lock mode, Allow Claude to stop

**Location**: `.claude/commands/amplihack/unlock.md`

### /amplihack:xpia (v1.0.0)

**Description**: XPIA security system management and health monitoring

**Triggers**: Check XPIA security status, Run XPIA health check, View XPIA logs, Test XPIA defense system

**Location**: `.claude/commands/amplihack/xpia.md`

### /ddd:ddd:0-help (v1.0.0)

**Description**: DDD workflow guide and help

**Triggers**: Need help with DDD, How does document-driven development work, DDD workflow overview

**Invokes**:

- workflow: `.claude/workflow/DDD_WORKFLOW.md`

**Location**: `.claude/commands/ddd/0-help.md`

### /ddd:ddd:1-plan (v1.0.0)

**Description**: DDD Phase 1 - Planning and design

**Triggers**: Start DDD workflow, Plan new feature with DDD, Create DDD plan

**Invokes**:

- workflow: `.claude/workflow/DDD_WORKFLOW.md`

**Location**: `.claude/commands/ddd/1-plan.md`

### /ddd:ddd:2-docs (v1.0.0)

**Description**: DDD Phase 2 - Update all non-code files

**Triggers**: Update DDD documentation, Phase 2 documentation retcon, Apply retcon writing to docs

**Invokes**:

- workflow: `.claude/workflow/DDD_WORKFLOW.md`

**Location**: `.claude/commands/ddd/2-docs.md`

### /ddd:ddd:3-code-plan (v1.0.0)

**Description**: DDD Phase 3 - Plan code implementation

**Triggers**: Plan code implementation for DDD, Create code plan from DDD specs, Phase 3 implementation planning

**Invokes**:

- workflow: `.claude/workflow/DDD_WORKFLOW.md`

**Location**: `.claude/commands/ddd/3-code-plan.md`

### /ddd:ddd:4-code (v1.0.0)

**Description**: DDD Phase 4 - Implement and verify code

**Triggers**: Implement DDD code, Phase 4 code implementation, Test as user in DDD

**Invokes**:

- workflow: `.claude/workflow/DDD_WORKFLOW.md`

**Location**: `.claude/commands/ddd/4-code.md`

### /ddd:ddd:5-finish (v1.0.0)

**Description**: DDD Phase 5 - Cleanup and finalize

**Triggers**: Finish DDD workflow, Phase 5 cleanup and push, Finalize DDD feature

**Invokes**:

- workflow: `.claude/workflow/DDD_WORKFLOW.md`

**Location**: `.claude/commands/ddd/5-finish.md`

### /ddd:ddd:prime (v1.0.0)

**Description**: Load complete DDD context for this session

**Triggers**: Load DDD context, Prime DDD for session, Initialize DDD understanding

**Invokes**:

- workflow: `.claude/workflow/DDD_WORKFLOW.md`

**Location**: `.claude/commands/ddd/prime.md`

### /ddd:ddd:status (v1.0.0)

**Description**: Show current DDD progress and next steps

**Triggers**: Check DDD status, Where am I in DDD workflow, Show DDD progress

**Invokes**:

- workflow: `.claude/workflow/DDD_WORKFLOW.md`

**Location**: `.claude/commands/ddd/status.md`

---

## Skills

**Total**: 46 skills

### claude-agent-sdk (v1.0.0)

**Description**: Comprehensive knowledge of Claude Agent SDK architecture, tools, hooks, skills, and production patterns. Auto-activates for agent building, SDK integration, tool design, and MCP server tasks.

**Activation Keywords**: agent sdk, claude agent, sdk tools, agent hooks, mcp server, subagent, agent loop, agent permissions, agent skill

**Auto-activate**: Yes

**Location**: `.claude/skills/agent-sdk/SKILL.md`

### anthropologist-analyst (v1.0.0)

**Description**: Analyzes events through anthropological lens using cultural analysis, ethnographic methods, kinship and social organization,
symbolic systems, ritual and practice, and comparative ethnology. Provides insights on cultural meanings, social practices,
symbolic structures, cultural change, and cross-cultural patterns.
Use when: Cultural conflicts, identity issues, ritual significance, symbolic meanings, cultural change, cross-cultural comparison.
Evaluates: Cultural systems, symbolic meanings, social practices, kinship structures, cultural adaptation, power-culture nexus.

**Auto-activate**: No

**Location**: `.claude/skills/anthropologist-analyst/SKILL.md`

### biologist-analyst (v1.0.0)

**Description**: Analyzes living systems and biological phenomena through biological lens using evolution, molecular biology,
ecology, and systems biology frameworks.
Provides insights on mechanisms, adaptations, interactions, and life processes.
Use when: Biological systems, health issues, evolutionary questions, ecological problems, biotechnology.
Evaluates: Function, structure, heredity, evolution, interactions, molecular mechanisms.

**Auto-activate**: No

**Location**: `.claude/skills/biologist-analyst/SKILL.md`

### chemist-analyst (v1.0.0)

**Description**: Analyzes events through chemistry lens using molecular structure, reaction mechanisms, thermodynamics,
kinetics, and analytical techniques (spectroscopy, chromatography, mass spectrometry).
Provides insights on chemical processes, material properties, reaction pathways, synthesis, and analytical methods.
Use when: Chemical reactions, material analysis, synthesis planning, process optimization, environmental chemistry.
Evaluates: Molecular structure, reaction mechanisms, yield, selectivity, safety, environmental impact.

**Auto-activate**: No

**Location**: `.claude/skills/chemist-analyst/SKILL.md`

### code-smell-detector (v1.0.0)

**Description**: Identifies anti-patterns specific to amplihack philosophy.
Use when reviewing code for quality issues or refactoring.
Detects: over-abstraction, complex inheritance, large functions (>50 lines), tight coupling, missing **all** exports.
Provides specific fixes and explanations for each smell.

**Auto-activate**: No

**Location**: `.claude/skills/code-smell-detector/SKILL.md`

### Creating Pull Requests (vN/A)

**Description**: Creates high-quality pull requests with comprehensive descriptions, test plans, and context. Activates when user wants to create PR, says 'ready to merge', or has completed feature work. Analyzes commits and changes to generate meaningful PR descriptions.

**Auto-activate**: No

**Location**: `.claude/skills/collaboration/creating-pull-requests/SKILL.md`

### computer-scientist-analyst (v1.0.0)

**Description**: Analyzes events through computer science lens using computational complexity, algorithms, data structures,
systems architecture, information theory, and software engineering principles to evaluate feasibility, scalability, security.
Provides insights on algorithmic efficiency, system design, computational limits, data management, and technical trade-offs.
Use when: Technology evaluation, system architecture, algorithm design, scalability analysis, security assessment.
Evaluates: Computational complexity, algorithmic efficiency, system architecture, scalability, data integrity, security.

**Auto-activate**: No

**Location**: `.claude/skills/computer-scientist-analyst/SKILL.md`

### cybersecurity-analyst (v1.0.0)

**Description**: Analyzes events through cybersecurity lens using threat modeling, attack surface analysis, defense-in-depth,
zero-trust architecture, and risk-based frameworks (CIA triad, STRIDE, MITRE ATT&CK).
Provides insights on vulnerabilities, attack vectors, defense strategies, incident response, and security posture.
Use when: Security incidents, vulnerability assessments, threat analysis, security architecture, compliance.
Evaluates: Confidentiality, integrity, availability, threat actors, attack patterns, controls, residual risk.

**Auto-activate**: No

**Location**: `.claude/skills/cybersecurity-analyst/SKILL.md`

### design-patterns-expert (v1.0.0)

**Description**: Comprehensive knowledge of all 23 Gang of Four design patterns with
progressive disclosure (Quick/Practical/Deep), pattern recognition for
problem-solving, and philosophy-aligned guidance to prevent over-engineering.

**Auto-activate**: No

**Location**: `.claude/skills/design-patterns-expert/SKILL.md`

### Architecting Solutions (vN/A)

**Description**: Analyzes problems and designs system architecture before implementation. Activates when user asks design questions, discusses architecture, or needs to break down complex features. Creates clear specifications following the brick philosophy of simple, modular, regeneratable components.

**Auto-activate**: No

**Location**: `.claude/skills/development/architecting-solutions/SKILL.md`

### Setting Up Projects (vN/A)

**Description**: Automates project setup with best practices including pre-commit hooks, linting, formatting, and boilerplate. Activates when creating new projects, missing configuration files, or setting up development environment. Ensures quality tooling from the start.

**Auto-activate**: No

**Location**: `.claude/skills/development/setting-up-projects/SKILL.md`

### docx (v1.0.0)

**Description**: Create, edit, and analyze Word documents with tracked changes support

**Auto-activate**: No

**Location**: `.claude/skills/docx/SKILL.md`

### economist-analyst (v1.0.0)

**Description**: Analyzes events through economic lens using supply/demand, incentive structures, market dynamics,
and multiple schools of economic thought (Classical, Keynesian, Austrian, Behavioral).
Provides insights on market impacts, resource allocation, policy implications, and distributional effects.
Use when: Economic events, policy changes, market shifts, financial crises, regulatory decisions.
Evaluates: Incentives, efficiency, opportunity costs, market failures, systemic risks.

**Auto-activate**: No

**Location**: `.claude/skills/economist-analyst/SKILL.md`

### engineer-analyst (v1.0.0)

**Description**: Analyzes technical systems and problems through engineering lens using first principles, systems thinking,
design methodologies, and optimization frameworks.
Provides insights on feasibility, performance, reliability, scalability, and trade-offs.
Use when: System design, technical feasibility, optimization, failure analysis, performance issues.
Evaluates: Requirements, constraints, trade-offs, efficiency, robustness, maintainability.

**Auto-activate**: No

**Location**: `.claude/skills/engineer-analyst/SKILL.md`

### environmentalist-analyst (v1.0.0)

**Description**: Analyzes events through environmental lens using ecological principles, systems thinking, sustainability frameworks,
and conservation biology to assess ecosystem health, biodiversity impacts, and long-term environmental sustainability.
Provides insights on climate change, resource management, pollution, habitat conservation, and human-nature relationships.
Use when: Environmental policy, climate decisions, conservation planning, resource extraction, pollution assessment.
Evaluates: Ecosystem health, biodiversity, sustainability, climate impacts, carrying capacity, environmental justice.

**Auto-activate**: No

**Location**: `.claude/skills/environmentalist-analyst/SKILL.md`

### epidemiologist-analyst (v1.0.0)

**Description**: Analyzes disease patterns and health events through epidemiological lens using surveillance systems,
outbreak investigation methods, and disease modeling frameworks.
Provides insights on disease spread, risk factors, prevention strategies, and public health interventions.
Use when: Disease outbreaks, health policy evaluation, risk assessment, intervention planning.
Evaluates: Transmission dynamics, risk factors, causality, population health impact, intervention effectiveness.

**Auto-activate**: No

**Location**: `.claude/skills/epidemiologist-analyst/SKILL.md`

### ethicist-analyst (v1.0.0)

**Description**: Analyzes moral dimensions and value conflicts through ethical frameworks using deontology, consequentialism,
virtue ethics, and applied ethics methodologies.
Provides insights on moral obligations, rights, justice, and ethical decision-making.
Use when: Ethical dilemmas, policy decisions, technology ethics, professional conduct issues.
Evaluates: Moral principles, stakeholder interests, consequences, rights, justice, virtues.

**Auto-activate**: No

**Location**: `.claude/skills/ethicist-analyst/SKILL.md`

### futurist-analyst (v1.0.0)

**Description**: Analyzes events through futures lens using scenario planning, trend analysis, weak signals,
drivers of change, and forecasting methods (exploratory, normative, backcasting).
Provides insights on possible futures, emerging trends, disruptive forces, strategic foresight, and alternative scenarios.
Use when: Strategic planning, emerging trends, technology assessment, long-term planning, uncertainty navigation.
Evaluates: Trends, weak signals, drivers of change, plausible futures, strategic options, uncertainty ranges.

**Auto-activate**: No

**Location**: `.claude/skills/futurist-analyst/SKILL.md`

### Goal-Seeking Agent Pattern (v1.0.0)

**Description**: Guides architects on when and how to use goal-seeking agents as a design pattern.
This skill helps evaluate whether autonomous agents are appropriate for a given
problem, how to structure their objectives, integrate with goal_agent_generator,
and reference real amplihack examples like AKS SRE automation, CI diagnostics,
pre-commit workflows, and fix-agent pattern matching.

**Auto-activate**: No

**Location**: `.claude/skills/goal-seeking-agent-pattern/SKILL.md`

### historian-analyst (v1.0.0)

**Description**: Analyzes events through historical lens using source analysis, comparative history, periodization,
causation, continuity/change, and contextualization frameworks.
Provides insights on historical patterns, precedents, path dependency, and long-term trends.
Use when: Understanding historical context, identifying precedents, analyzing change over time, comparative history.
Evaluates: Causation, continuity, change, context, historical parallels, long-term patterns.

**Auto-activate**: No

**Location**: `.claude/skills/historian-analyst/SKILL.md`

### indigenous-leader-analyst (v1.0.0)

**Description**: Analyzes events through indigenous knowledge systems using relational thinking, seven generations principle,
reciprocity, holistic integration, and traditional ecological knowledge frameworks.
Provides insights on interconnectedness, long-term sustainability, collective wisdom, and decolonial perspectives.
Use when: Environmental decisions, resource stewardship, community governance, decolonization, intergenerational planning.
Evaluates: Relationships, sustainability, collective impact, indigenous rights, traditional knowledge integration.

**Auto-activate**: No

**Location**: `.claude/skills/indigenous-leader-analyst/SKILL.md`

### journalist-analyst (v1.0.0)

**Description**: Analyzes events through journalistic lens using 5 Ws and H, investigative methods, source evaluation,
fact-checking, newsworthiness criteria, and ethical journalism principles.
Provides insights on story angles, information gaps, credibility, public interest, and media framing.
Use when: Breaking news, information verification, source analysis, story development, media criticism.
Evaluates: Factual accuracy, source credibility, completeness, newsworthiness, bias, public interest.

**Auto-activate**: No

**Location**: `.claude/skills/journalist-analyst/SKILL.md`

### knowledge-extractor (v1.0.0)

**Description**: Extracts key learnings from conversations, debugging sessions, and failed attempts.
Use at session end or after solving complex problems to capture insights.
Automatically suggests updates to: DISCOVERIES.md (learnings), PATTERNS.md (reusable solutions), new agent creation (repeated workflows).
Ensures knowledge persists across sessions.

**Auto-activate**: No

**Location**: `.claude/skills/knowledge-extractor/SKILL.md`

### lawyer-analyst (v1.0.0)

**Description**: Analyzes events through legal lens using statutory interpretation, case law analysis, legal reasoning,
constitutional principles, and multiple legal frameworks (common law, civil law, international law).
Provides insights on legal rights, obligations, liabilities, remedies, and compliance requirements.
Use when: Legal disputes, contracts, regulations, compliance, rights analysis, liability assessment.
Evaluates: Legal obligations, rights, liabilities, remedies, precedent, statutory authority, constitutionality.

**Auto-activate**: No

**Location**: `.claude/skills/lawyer-analyst/SKILL.md`

### mermaid-diagram-generator (vN/A)

**Description**: Converts architecture descriptions, module specs, or workflow docs into Mermaid diagrams.
Use when visualizing brick module relationships, workflows (DDD, investigation), or system architecture.
Supports: flowcharts, sequence diagrams, class diagrams, state machines, entity relationship diagrams, and Gantt charts.
Generates valid Mermaid syntax for embedding in markdown docs.

**Auto-activate**: No

**Location**: `.claude/skills/mermaid-diagram-generator.md`

### Analyzing Problems Deeply (vN/A)

**Description**: Performs deep structured analysis on complex or ambiguous problems. Activates when problems are unclear, have multiple perspectives, or require careful thinking before proceeding. Uses ultrathink methodology for systematic exploration of problem space.

**Auto-activate**: No

**Location**: `.claude/skills/meta-cognitive/analyzing-deeply/SKILL.md`

### module-spec-generator (v1.0.0)

**Description**: Generates module specifications following amplihack's brick philosophy template.
Use when creating new modules or documenting existing ones to ensure they follow
the brick & studs pattern. Analyzes code to extract: purpose, public contract,
dependencies, test requirements.

**Auto-activate**: No

**Location**: `.claude/skills/module-spec-generator/SKILL.md`

### novelist-analyst (v1.0.0)

**Description**: Analyzes events through narrative lens using story structure, character arc analysis, dramatic tension,
thematic development, and narrative theory (three-act structure, hero's journey, conflict-resolution).
Provides insights on narrative coherence, character motivations, dramatic stakes, plot development, and thematic resonance.
Use when: Complex human stories, leadership analysis, organizational narratives, crisis narratives, cultural moments.
Evaluates: Character development, narrative arc, dramatic tension, thematic depth, symbolic meaning, narrative coherence.

**Auto-activate**: No

**Location**: `.claude/skills/novelist-analyst/SKILL.md`

### outside-in-testing (v1.0.0)

**Description**: Generates agentic outside-in tests using gadugi-agentic-test framework for CLI, TUI, Web, and Electron apps.
Use when you need behavior-driven tests that verify external interfaces without internal implementation knowledge.
Creates YAML test scenarios that AI agents execute, observe, and validate against expected outcomes.
Supports progressive complexity from simple smoke tests to advanced multi-step workflows.

**Auto-activate**: No

**Location**: `.claude/skills/outside-in-testing/SKILL.md`

### pdf (v1.0.0)

**Description**: Comprehensive PDF manipulation toolkit for extracting text and tables, creating new PDFs, merging/splitting documents, and handling forms. When Claude needs to fill in a PDF form or programmatically process, generate, or analyze PDF documents at scale.

**Auto-activate**: No

**Location**: `.claude/skills/pdf/SKILL.md`

### philosopher-analyst (v1.0.0)

**Description**: Analyzes fundamental questions and concepts through philosophical lens using logic, epistemology,
metaphysics, and critical analysis frameworks.
Provides insights on meaning, truth, knowledge, existence, reasoning, and conceptual clarity.
Use when: Conceptual ambiguity, logical arguments, foundational assumptions, meaning questions.
Evaluates: Validity, soundness, coherence, assumptions, implications, conceptual clarity.

**Auto-activate**: No

**Location**: `.claude/skills/philosopher-analyst/SKILL.md`

### physicist-analyst (v1.0.0)

**Description**: Analyzes events through physics lens using fundamental laws (thermodynamics, conservation, relativity),
quantitative modeling, systems dynamics, and energy principles to understand causation, constraints, and feasibility.
Provides insights on energy systems, physical limits, technological feasibility, and complex systems behavior.
Use when: Energy decisions, technology assessment, systems analysis, physical constraints, feasibility evaluation.
Evaluates: Energy flows, conservation laws, efficiency limits, physical feasibility, scaling behavior, emergent properties.

**Auto-activate**: No

**Location**: `.claude/skills/physicist-analyst/SKILL.md`

### poet-analyst (v1.0.0)

**Description**: Analyzes events through poetic lens using close reading, metaphor analysis, imagery, rhythm,
form analysis, and attention to language's emotional and aesthetic dimensions.
Provides insights on emotional truth, symbolic meaning, human experience, aesthetic impact, and expressive depth.
Use when: Understanding emotional dimensions, symbolic meaning, communication impact, cultural resonance, human experience.
Evaluates: Imagery, metaphor, rhythm, emotional truth, symbolic depth, aesthetic power, resonance, ambiguity.

**Auto-activate**: No

**Location**: `.claude/skills/poet-analyst/SKILL.md`

### political-scientist-analyst (v1.0.0)

**Description**: Analyzes events through political science lens using IR theory (Realism, Liberalism, Constructivism),
comparative politics, institutional analysis, and power dynamics.
Provides insights on governance, security, regime change, international cooperation, and policy outcomes.
Use when: Political events, international crises, elections, regime transitions, policy changes, conflicts.
Evaluates: Power distributions, institutional effects, actor interests, strategic interactions, norms.

**Auto-activate**: No

**Location**: `.claude/skills/political-scientist-analyst/SKILL.md`

### pptx (v1.0.0)

**Description**: Presentation creation, editing, and analysis. When Claude needs to work with presentations (.pptx files) for: (1) Creating new presentations, (2) Modifying or editing content, (3) Working with layouts, (4) Adding comments or speaker notes, or any other presentation tasks

**Auto-activate**: No

**Location**: `.claude/skills/pptx/SKILL.md`

### pr-review-assistant (v1.0.0)

**Description**: Philosophy-aware PR reviews checking alignment with amplihack principles.
Use when reviewing PRs to ensure ruthless simplicity, modular design, and zero-BS implementation.
Suggests simplifications, identifies over-engineering, verifies brick module structure.
Posts detailed, constructive review comments with specific file:line references.

**Auto-activate**: No

**Location**: `.claude/skills/pr-review-assistant/SKILL.md`

### psychologist-analyst (v1.0.0)

**Description**: Analyzes events through psychological lens using cognitive psychology, social psychology, developmental psychology,
clinical psychology, and neuroscience. Provides insights on behavior, cognition, emotion, motivation, group dynamics,
decision-making biases, mental health, and individual differences.
Use when: Behavioral patterns, decision-making, group behavior, mental health, leadership, persuasion, trauma, development.
Evaluates: Cognitive processes, emotional responses, motivations, biases, group dynamics, personality, mental states.

**Auto-activate**: No

**Location**: `.claude/skills/psychologist-analyst/SKILL.md`

### Reviewing Code (vN/A)

**Description**: Performs systematic code review checking for correctness, maintainability, security, and best practices. Activates when user requests review, before creating PRs, or when significant code changes are ready. Ensures quality gates are met before code proceeds to production.

**Auto-activate**: No

**Location**: `.claude/skills/quality/reviewing-code/SKILL.md`

### Testing Code (vN/A)

**Description**: Generates and improves tests following TDD principles. Activates when new features are implemented, test coverage is low, or user requests tests. Ensures comprehensive test coverage with unit, integration, and edge case tests.

**Auto-activate**: No

**Location**: `.claude/skills/quality/testing-code/SKILL.md`

### Researching Topics (vN/A)

**Description**: Performs quick research using web search and synthesis when user asks about unfamiliar topics, new technologies, or needs current information. Activates on questions like 'how does X work', 'what is Y', or when encountering unknown concepts. For deep comprehensive research, suggests knowledge-builder command.

**Auto-activate**: No

**Location**: `.claude/skills/research/researching-topics/SKILL.md`

### skill-builder (v1.0.0)

**Description**: Creates, refines, and validates Claude Code skills following amplihack philosophy and official best practices. Automatically activates when building, creating, generating, or designing new skills.

**Auto-activate**: No

**Location**: `.claude/skills/skill-builder/SKILL.md`

### sociologist-analyst (v1.0.0)

**Description**: Analyzes events through sociological lens using social structures, institutions, stratification, culture,
norms, collective behavior, and multiple theoretical perspectives (functionalist, conflict, symbolic interactionist).
Provides insights on social patterns, group dynamics, inequality, socialization, social change, and collective action.
Use when: Social movements, inequality, cultural trends, group behavior, institutions, identity, social change.
Evaluates: Social structures, power relations, inequality, norms, group dynamics, cultural patterns, social change.

**Auto-activate**: No

**Location**: `.claude/skills/sociologist-analyst/SKILL.md`

### storytelling-synthesizer (v1.0.0)

**Description**: Converts technical work into compelling narratives for demos, blog posts, or presentations.
Use when preparing hackathon demos, writing technical blog posts, or creating marketing content.
Transforms: PR descriptions, commit histories, feature implementations into structured stories.
Formats: demo scripts, blog posts, presentation outlines, marketing copy.

**Auto-activate**: No

**Location**: `.claude/skills/storytelling-synthesizer/SKILL.md`

### test-gap-analyzer (v1.0.0)

**Description**: Analyzes code to identify untested functions, low coverage areas, and missing edge cases.
Use when reviewing test coverage or planning test improvements.
Generates specific test suggestions with example templates following amplihack's testing pyramid (60% unit, 30% integration, 10% E2E).
Can use coverage.py for Python projects.

**Auto-activate**: No

**Location**: `.claude/skills/test-gap-analyzer/SKILL.md`

### urban-planner-analyst (v1.0.0)

**Description**: Analyzes urban development through planning lens using zoning, land use, comprehensive planning,
and transit-oriented development frameworks.
Provides insights on spatial organization, infrastructure, sustainability, and livability.
Use when: Urban development projects, zoning decisions, transportation planning, sustainability initiatives.
Evaluates: Land use patterns, density, accessibility, environmental impact, community needs.

**Auto-activate**: No

**Location**: `.claude/skills/urban-planner-analyst/SKILL.md`

### xlsx (v1.0.0)

**Description**: Comprehensive spreadsheet creation, editing, and analysis with support for formulas, formatting, data analysis, and visualization. When Claude needs to work with spreadsheets (.xlsx, .xlsm, .csv, .tsv, etc) for: (1) Creating new spreadsheets with formulas and formatting, (2) Reading or analyzing data, (3) Modify existing spreadsheets while preserving formulas, (4) Data analysis and visualization in spreadsheets, or (5) Recalculating formulas

**Auto-activate**: No

**Location**: `.claude/skills/xlsx/SKILL.md`

---

## Agents

**Total**: 35 agents

### Core Agents

### api-designer (v1.0.0)

**Description**: API contract specialist. Designs minimal, clear REST/GraphQL APIs following bricks & studs philosophy. Creates OpenAPI specs, versioning strategies, error patterns. Use for API design, review, or refactoring.

**Role**: API contract specialist and interface designer

**Location**: `.claude/agents/amplihack/core/api-designer.md`

### architect (v1.0.0)

**Description**: General architecture and design agent. Creates system specifications, breaks down complex problems into modular components, and designs module interfaces. Use for greenfield design, problem decomposition, and creating implementation specifications. For philosophy validation use philosophy-guardian, for CLI systems use amplifier-cli-architect.

**Role**: System architect and problem decomposition specialist

**Location**: `.claude/agents/amplihack/core/architect.md`

### builder (v1.0.0)

**Description**: Primary implementation agent. Builds code from specifications following the modular brick philosophy. Creates self-contained, regeneratable modules.

**Role**: Primary implementation agent and code builder

**Location**: `.claude/agents/amplihack/core/builder.md`

### optimizer (v1.0.0)

**Description**: Performance optimization specialist. Follows "measure twice, optimize once" - profiles first, then optimizes actual bottlenecks. Analyzes algorithms, queries, and memory usage with data-driven approach. Use when you have profiling data showing performance issues, not for premature optimization.

**Role**: Performance optimization specialist

**Location**: `.claude/agents/amplihack/core/optimizer.md`

### reviewer (v1.0.0)

**Description**: Code review and debugging specialist. Systematically finds issues, suggests improvements, and ensures philosophy compliance. Use for bug hunting and quality assurance.

**Role**: Code review and quality assurance specialist

**Location**: `.claude/agents/amplihack/core/reviewer.md`

### tester (v1.0.0)

**Description**: Test coverage expert. Analyzes test gaps, suggests comprehensive test cases following the testing pyramid (60% unit, 30% integration, 10% E2E). Use when writing features, fixing bugs, or reviewing tests.

**Role**: Test coverage expert and quality specialist

**Location**: `.claude/agents/amplihack/core/tester.md`

### Specialized Agents

### ambiguity (v1.0.0)

**Description**: Requirements clarification specialist. Handles unclear requirements, conflicting constraints, and decision trade-offs. Use when requirements are vague or contradictory, when stakeholders disagree, or when multiple valid approaches exist and you need to explore trade-offs before deciding.

**Role**: Requirements clarification and ambiguity resolution specialist

**Location**: `.claude/agents/amplihack/specialized/ambiguity.md`

### amplifier-cli-architect (v1.0.0)

**Description**: CLI application architect. Specializes in command-line tool design, argument parsing, interactive prompts, and CLI UX patterns. Use when designing CLI tools or refactoring command-line interfaces. For general architecture use architect.

**Role**: CLI application architect and hybrid code/AI systems expert

**Location**: `.claude/agents/amplihack/specialized/amplifier-cli-architect.md`

### analyzer (v1.0.0)

**Description**: Code and system analysis specialist. Automatically selects TRIAGE (rapid scanning), DEEP (thorough investigation), or SYNTHESIS (multi-source integration) based on task. Use for understanding existing code, mapping dependencies, analyzing system behavior, or investigating architectural decisions.

**Role**: Code and system analysis specialist

**Location**: `.claude/agents/amplihack/specialized/analyzer.md`

### azure-kubernetes-expert (v1.0.0)

**Description**: Azure Kubernetes Service (AKS) expert with deep knowledge of production deployments, networking, security, and operations

**Role**: Azure Kubernetes Service (AKS) expert

**Location**: `.claude/agents/amplihack/specialized/azure-kubernetes-expert.md`

### ci-diagnostic-workflow (v1.0.0)

**Description**: CI failure resolution workflow. Monitors CI status after push, diagnoses failures, fixes issues, and iterates until PR is mergeable (never auto-merges). Use when CI checks fail after pushing code.

**Role**: CI failure resolution workflow orchestrator

**Location**: `.claude/agents/amplihack/specialized/ci-diagnostic-workflow.md`

### cleanup (v1.0.0)

**Description**: Post-task cleanup specialist. Reviews git status, removes temporary artifacts, eliminates unnecessary complexity, ensures philosophy compliance. Use proactively after completing tasks or todo lists.

**Role**: Post-task cleanup and codebase hygiene specialist

**Location**: `.claude/agents/amplihack/specialized/cleanup.md`

### database (v1.0.0)

**Description**: Database design and optimization specialist. Use for schema design, query optimization, migrations, and data architecture decisions.

**Role**: Database design and optimization specialist

**Location**: `.claude/agents/amplihack/specialized/database.md`

### fallback-cascade (v1.0.0)

**Description**: Graceful degradation specialist. Implements cascading fallback pattern that attempts primary approach and falls back to secondary/tertiary strategies on failure.

**Role**: Graceful degradation and fallback cascade specialist

**Location**: `.claude/agents/amplihack/specialized/fallback-cascade.md`

### fix-agent (v1.0.0)

**Description**: Error resolution specialist. Rapidly diagnoses and fixes common issues (imports, CI failures, test errors, config problems). Use when you encounter errors and need quick resolution, or when /fix command is invoked.

**Role**: Error resolution and rapid fix specialist

**Location**: `.claude/agents/amplihack/specialized/fix-agent.md`

### integration (v1.0.0)

**Description**: External integration specialist. Designs and implements connections to third-party APIs, services, and external systems. Handles authentication, rate limiting, error handling, and retries. Use when integrating external services, not for internal API design (use api-designer).

**Role**: External integration and third-party API specialist

**Location**: `.claude/agents/amplihack/specialized/integration.md`

### knowledge-archaeologist (v1.0.0)

**Description**: Historical codebase researcher. Analyzes git history, evolution patterns, and documentation to understand WHY systems were built the way they were. Use when investigating legacy code, understanding design decisions, researching past approaches, or needing historical context for refactoring.

**Role**: Historical codebase researcher and knowledge excavation specialist

**Location**: `.claude/agents/amplihack/specialized/knowledge-archaeologist.md`

### memory-manager (v1.0.0)

**Description**: Session state manager. Persists important context, decisions, and findings across conversations to .claude/runtime/logs/. Use when you need to save context for future sessions or retrieve information from past work.

**Role**: Session state manager and context persistence specialist

**Location**: `.claude/agents/amplihack/specialized/memory-manager.md`

### multi-agent-debate (v1.0.0)

**Description**: Structured debate facilitator for fault-tolerant decision-making. Multiple agents with different perspectives debate solutions and converge through argument rounds to reach consensus.

**Role**: Multi-agent debate facilitator and consensus builder

**Location**: `.claude/agents/amplihack/specialized/multi-agent-debate.md`

### n-version-validator (v1.0.0)

**Description**: N-version programming validator. Generates multiple independent implementations and selects the best through comparison and voting for critical tasks.

**Role**: N-version programming validator and fault-tolerance specialist

**Location**: `.claude/agents/amplihack/specialized/n-version-validator.md`

### patterns (v1.0.0)

**Description**: Pattern recognition specialist. Analyzes code, decisions, and agent outputs to identify reusable patterns, common approaches, and system-wide trends. Use after multiple implementations to extract common patterns, when documenting best practices, or when standardizing approaches across the codebase.

**Role**: Pattern recognition and emergence detection specialist

**Location**: `.claude/agents/amplihack/specialized/patterns.md`

### philosophy-guardian (v1.0.0)

**Description**: Philosophy compliance guardian. Ensures code aligns with amplihack's ruthless simplicity, brick philosophy, and Zen-like minimalism. Use for architecture reviews and philosophy validation.

**Role**: Philosophy compliance guardian and minimalism enforcer

**Location**: `.claude/agents/amplihack/specialized/philosophy-guardian.md`

### pre-commit-diagnostic (v1.0.0)

**Description**: Pre-commit failure resolver. Fixes formatting, linting, and type checking issues locally before push. Use when pre-commit hooks fail or code won't commit.

**Role**: Pre-commit failure resolver and local code quality specialist

**Location**: `.claude/agents/amplihack/specialized/pre-commit-diagnostic.md`

### preference-reviewer (v1.0.0)

**Description**: User preference analyzer. Reviews USER_PREFERENCES.md to identify generalizable patterns worth contributing to Claude Code upstream. Use when user preferences might benefit other users, or periodically to assess contribution opportunities.

**Role**: User preference analyzer and contribution opportunity identifier

**Location**: `.claude/agents/amplihack/specialized/preference-reviewer.md`

### prompt-writer (v1.0.0)

**Description**: Requirement clarification and prompt engineering specialist. Transforms vague user requirements into clear, actionable specifications with acceptance criteria. Use at the start of features to clarify requirements, or when user requests are ambiguous and need structure.

**Role**: Requirement clarification and prompt engineering specialist

**Location**: `.claude/agents/amplihack/specialized/prompt-writer.md`

### rust-programming-expert (v1.0.0)

**Description**: Rust programming expert with deep knowledge of memory safety, ownership, and systems programming

**Role**: Rust programming expert and systems programming specialist

**Location**: `.claude/agents/amplihack/specialized/rust-programming-expert.md`

### security (v1.0.0)

**Description**: Security specialist for authentication, authorization, encryption, and vulnerability assessment. Never compromises on security fundamentals.

**Role**: Security specialist and vulnerability assessment expert

**Location**: `.claude/agents/amplihack/specialized/security.md`

### visualization-architect (v1.0.0)

**Description**: Visual communication specialist. Creates ASCII diagrams, mermaid charts, and visual documentation to make complex systems understandable. Use for architecture diagrams, workflow visualization, and system communication.

**Role**: Visual communication specialist and architecture visualization expert

**Location**: `.claude/agents/amplihack/specialized/visualization-architect.md`

### worktree-manager (v1.0.0)

**Description**: Git worktree management specialist. Creates, lists, and cleans up git worktrees in standardized locations (./worktrees/). Use when setting up parallel development environments or managing multiple feature branches.

**Role**: Git worktree management specialist

**Location**: `.claude/agents/amplihack/specialized/worktree-manager.md`

### xpia-defense (v1.0.0)

**Description**: Cross-Prompt Injection Attack defense specialist. Provides transparent AI security protection with sub-100ms processing for prompt injection detection and prevention.

**Role**: AI security specialist and prompt injection defense expert

**Location**: `.claude/agents/amplihack/specialized/xpia-defense.md`

### Workflow Agents

### amplihack-improvement-workflow (v1.0.0)

**Description**: Used ONLY for Improving the amplihack project, not other projects. Enforces progressive validation throughout improvement process. Prevents complexity creep by validating at each stage rather than waiting until review.

**Role**: Amplihack improvement workflow orchestrator with progressive validation

**Location**: `.claude/agents/amplihack/workflows/amplihack-improvement-workflow.md`

### prompt-review-workflow (v1.0.0)

**Description**: Integration pattern between PromptWriter and Architect agents for prompt review and refinement.

**Role**: Prompt review workflow orchestrator

**Location**: `.claude/agents/amplihack/workflows/prompt-review-workflow.md`

### Other Agents

### concept-extractor (v1.0.0)

**Description**: Use this agent when processing articles, papers, or documents to extract knowledge components for synthesis. This agent should be used proactively after reading or importing articles to build a structured knowledge base. It excels at identifying atomic concepts, relationships between ideas, and preserving productive tensions or contradictions in the source material. Examples: <example>Context: The user has just imported or read an article about distributed systems. user: "I've added a new article about CAP theorem to the knowledge base" assistant: "I'll use the concept-extractor agent to extract the key concepts and relationships from this article" <commentary>Since new article content has been added, use the concept-extractor agent to process it and extract structured knowledge components.</commentary></example> <example>Context: The user is building a knowledge synthesis system and needs to process multiple articles. user: "Process these three articles on microservices architecture" assistant: "Let me use the concept-extractor agent to extract and structure the knowledge from these articles" <commentary>Multiple articles need processing for knowledge extraction, perfect use case for the concept-extractor agent.</commentary></example> <example>Context: The user wants to understand contradictions between different sources. user: "These two papers seem to disagree about event sourcing benefits" assistant: "I'll use the concept-extractor agent to extract and preserve the tensions between these viewpoints" <commentary>When dealing with conflicting information that needs to be preserved rather than resolved, the concept-extractor agent is ideal.</commentary></example>

**Role**: Concept extraction and knowledge structuring specialist

**Location**: `.claude/agents/concept-extractor.md`

### insight-synthesizer (v1.0.0)

**Description**: Use this agent when you need to discover revolutionary connections between disparate concepts, find breakthrough insights through collision-zone thinking, identify meta-patterns across domains, or discover simplification cascades that dramatically reduce complexity. Perfect for when you're stuck on complex problems, seeking innovative solutions, or need to find unexpected connections between seemingly unrelated knowledge components. <example>Context: The user wants to find innovative solutions by combining unrelated concepts. user: "I'm trying to optimize our database architecture but feel stuck in conventional approaches" assistant: "Let me use the insight-synthesizer agent to explore revolutionary connections and find breakthrough approaches to your database architecture challenge" <commentary>Since the user is seeking new perspectives on a complex problem, the insight-synthesizer agent will discover unexpected connections and simplification opportunities.</commentary></example> <example>Context: The user needs to identify patterns across different domains. user: "We keep seeing similar failures in our ML models, API design, and user interfaces but can't figure out the connection" assistant: "I'll deploy the insight-synthesizer agent to identify meta-patterns across these different domains and find the underlying principle" <commentary>The user is looking for cross-domain patterns, so use the insight-synthesizer agent to perform pattern-pattern recognition.</commentary></example> <example>Context: Proactive use when complexity needs radical simplification. user: "Our authentication system has grown to 15 different modules and 200+ configuration options" assistant: "This level of complexity suggests we might benefit from a fundamental rethink. Let me use the insight-synthesizer agent to search for simplification cascades" <commentary>Proactively recognizing excessive complexity, use the insight-synthesizer to find revolutionary simplifications.</commentary></example>

**Role**: Revolutionary insight synthesis and breakthrough connection specialist

**Location**: `.claude/agents/insight-synthesizer.md`

### knowledge-archaeologist (v1.0.0)

**Description**: Use this agent when you need to understand how knowledge, concepts, or ideas have evolved over time, trace the lineage of current understanding, identify abandoned but potentially valuable approaches, or recognize when old solutions might solve new problems. This agent excels at temporal analysis of knowledge evolution, paradigm shift documentation, and preserving the 'fossil record' of ideas that may become relevant again. Examples: <example>Context: User wants to understand how a programming paradigm evolved. user: 'How did functional programming concepts evolve from their mathematical origins to modern implementations?' assistant: 'I'll use the knowledge-archaeologist agent to trace the evolution of functional programming concepts through time.' <commentary>The user is asking about the historical evolution of ideas, so the knowledge-archaeologist agent is perfect for excavating the temporal layers of this concept's development.</commentary></example> <example>Context: User is researching why certain architectural patterns fell out of favor. user: 'Why did service-oriented architecture (SOA) decline and what lessons were lost?' assistant: 'Let me invoke the knowledge-archaeologist agent to analyze the decay patterns of SOA and identify valuable concepts that were abandoned.' <commentary>This requires understanding paradigm shifts and preserving potentially valuable 'extinct' ideas, which is the knowledge-archaeologist's specialty.</commentary></example> <example>Context: User notices similarities between old and new approaches. user: 'This new microservices pattern reminds me of something from the 1970s distributed computing era.' assistant: 'I'll use the knowledge-archaeologist agent to trace these lineages and identify if this is a revival or reincarnation of older concepts.' <commentary>Detecting revival patterns and tracing concept genealogies is a core capability of the knowledge-archaeologist agent.</commentary></example>

**Role**: Knowledge evolution and temporal analysis specialist

**Location**: `.claude/agents/knowledge-archaeologist.md`

---

## Summary

- **Workflows**: 9
- **Commands**: 33
- **Skills**: 46
- **Agents**: 35
  - Core: 6
  - Specialized: 24
  - Workflow: 2
  - Other: 3

**Total Components**: 123
