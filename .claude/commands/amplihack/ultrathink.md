# Ultra-Think Command

## Input Validation

@.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/ultrathink <TASK_DESCRIPTION>`

## Purpose

Deep analysis mode for complex tasks. Orchestrates multiple agents to break down, analyze, and solve challenging problems by following the default workflow.

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

1. **[NEW] Assess investigation complexity** if task is an investigation (Step 0 below)
2. **Read the workflow file** using FrameworkPathResolver.resolve_workflow_file() to get the correct path, then use the Read tool
3. **Create a comprehensive todo list** using TodoWrite that includes all workflow steps (adjusted based on complexity routing)
4. **Execute each step systematically**, marking todos as in_progress and completed
5. **Use the specified agents** for each step (marked with "**Use**" or "**Always use**")
6. **Track decisions** by creating `.claude/runtime/logs/<session_timestamp>/DECISIONS.md`
7. **End with cleanup agent** to ensure code quality

## STEP 0: INVESTIGATION COMPLEXITY ASSESSMENT (NEW)

**When to Apply**: This step applies ONLY to investigation tasks. Skip for implementation, bug fixes, or other non-investigation work.

**Investigation Detection Keywords**:

- "how does", "how do", "explain", "what is", "what are", "describe"
- "tell me about", "walk me through", "understand", "learn about"
- "overview of", "details on", "clarify"

**If NOT an investigation task** (contains "add", "implement", "fix", "create", "build", "refactor"), **skip to Step 1 of the workflow**.

### Complexity Assessment Algorithm

For investigation tasks, analyze the request using three dimensions:

#### 1. Scope Analysis (Systems/Components Involved)

**Count unique systems, modules, or concepts mentioned:**

- Look for: file/module names, technical terms, "integrate", "between", "connection"
- Keywords indicating multiple systems: "and", "with", "integration", "interaction"
- Keywords indicating breadth: "entire", "all", "whole system", "orchestration"

**Scope Scoring:**

- **1 point (Simple)**: Single system or concept (e.g., "lock system", "pre-commit hooks")
- **2 points (Medium)**: 2-3 systems (e.g., "preferences and hooks integration")
- **3 points (Complex)**: 4+ systems OR keywords like "entire", "all aspects", "orchestration"

#### 2. Depth Analysis (Level of Detail Required)

**Identify depth keywords:**

- **Overview level**: "what is", "overview", "summarize", "briefly explain", "describe"
- **Detailed level**: "how does X work", "implement", "integrate", "connection", "mechanism"
- **Comprehensive level**: "comprehensive", "deep dive", "all aspects", "thoroughly", "in-depth"

**Depth Scoring:**

- **1 point (Simple)**: Overview/explanation only
- **2 points (Medium)**: Detailed analysis of mechanisms
- **3 points (Complex)**: Comprehensive deep-dive required

#### 3. Breadth Analysis (Coverage Area)

**Identify breadth keywords:**

- **Narrow**: "specific", "just", "only", single focused question
- **Moderate**: Multiple related topics, 2-3 areas, "and" connectors
- **Broad**: "all", "entire", "every", "cross-cutting", many topics

**Breadth Scoring:**

- **1 point (Simple)**: Single focused topic
- **2 points (Medium)**: 2-3 related areas
- **3 points (Complex)**: Broad coverage, many interconnected areas

#### 4. Final Classification

**Calculate average score**: (Scope + Depth + Breadth) / 3

**Classification Rules:**

- **Complex**: Average >= 2.5 OR any dimension = 3
- **Medium**: Average >= 1.5 AND average < 2.5
- **Simple**: Average < 1.5

**Special Cases:**

- If Depth = 1 (overview) AND Scope = 1 → Simple (Quick Mode)
- If Depth >= 2 AND Scope = 1 → Simple (Thorough Mode)
- Mixed investigation + implementation → Complex (requires full workflow)

### Routing Decision Matrix

Based on classification, route to appropriate execution path:

#### Route A: Simple Investigation (Quick Mode)

**Triggers**: Scope=1, Depth=1, Breadth=1 (e.g., "What are pre-commit hooks?")

**Execution:**

```
1. Announce: "I've assessed this as a Simple investigation (overview level) focusing on [TOPIC]. I'll use a focused Explore approach for quick results!"
2. Deploy single Explore agent with narrow scope
3. Focus: Documentation and high-level explanation only
4. Expected messages: 15-25
5. Skip todo list creation and workflow steps
6. Return results directly to user
```

#### Route B: Simple Investigation (Thorough Mode)

**Triggers**: Scope=1, Depth=2, Breadth=1 (e.g., "How does the lock system work?")

**Execution:**

```
1. Announce: "I've assessed this as a Simple investigation (detailed analysis) focusing on [TOPIC]. I'll use a thorough Explore approach for comprehensive understanding!"
2. Deploy single Explore agent with deeper analysis
3. Include: Code review + documentation + usage examples
4. Expected messages: 25-40
5. Create minimal 3-step todo list (analyze, document, report)
6. Skip full workflow orchestration
```

#### Route C: Medium Investigation

**Triggers**: Average score 1.5-2.5 (e.g., "How do preferences and hooks integrate?")

**Execution:**

```
1. Announce: "I've assessed this as a Medium complexity investigation involving [KEY SYSTEMS]. I'll use targeted Ultra-Think with 2-3 agents for optimal coverage!"
2. Read workflow file but execute with limited agent deployment
3. Create workflow todo list
4. Deploy 2-3 specific agents (typically: analyzer + patterns OR analyzer + architect)
5. Follow workflow steps but limit orchestration scope
6. Expected messages: 70-120
7. Focus on key integration points and connections
```

#### Route D: Complex Investigation

**Triggers**: Average score >= 2.5 OR any dimension = 3 (e.g., "How does the entire agent orchestration system work?")

**Execution:**

```
1. Announce: "I've assessed this as a Complex investigation covering [MULTIPLE SYSTEMS]. I'll use full Ultra-Think orchestration for comprehensive analysis!"
2. Proceed with standard Ultra-Think execution (Steps 1-15 below)
3. Deploy all relevant agents at each workflow step
4. Create comprehensive todo list
5. Expected messages: 120-250
6. Full multi-agent coordination and deep analysis
```

### Assessment Examples

**Example 1: Simple (Quick)**

```
Input: "What are pre-commit hooks?"
Scope: 1 (single concept)
Depth: 1 (overview - "what are")
Breadth: 1 (single topic)
Average: 1.0
→ Route A: Simple (Quick Mode) - Explore agent, 15-25 messages
```

**Example 2: Simple (Thorough)**

```
Input: "How does the lock system work?"
Scope: 1 (single system)
Depth: 2 (detailed - "how does work")
Breadth: 1 (focused)
Average: 1.33
→ Route B: Simple (Thorough Mode) - Explore agent, 25-40 messages
```

**Example 3: Medium**

```
Input: "How do preferences and hooks integrate?"
Scope: 2 (two systems: preferences, hooks)
Depth: 2 (detailed - integration mechanism)
Breadth: 2 (moderate - two areas)
Average: 2.0
→ Route C: Medium - Ultra-Think with 2 agents, 70-120 messages
```

**Example 4: Complex**

```
Input: "How does the entire agent orchestration system work?"
Scope: 3 (entire system = multiple components)
Depth: 3 (comprehensive - "entire" keyword)
Breadth: 3 (broad - "entire system")
Average: 3.0
→ Route D: Complex - Full Ultra-Think, 120-250 messages
```

**Example 5: Non-Investigation**

```
Input: "Add authentication to the API"
Detection: "Add" = imperative verb, implementation task
→ Skip Step 0, proceed directly to Step 1 of workflow
```

## PROMPT-BASED WORKFLOW EXECUTION

Execute this exact sequence for the task: `{TASK_DESCRIPTION}`

### Step-by-Step Execution:

1. **Initialize**:
   - Read workflow file using FrameworkPathResolver to get the current 13-step process
   - Create TodoWrite list with all workflow steps
   - Create session directory for decision logging

2. **For Each Workflow Step**:
   - Mark step as in_progress in TodoWrite
   - Read the step requirements from workflow
   - Invoke specified agents via Task tool
   - Log decisions made
   - Mark step as completed

3. **Agent Invocation Pattern**:

   ```
   For step requiring "**Use** architect agent":
   → Invoke Task(subagent_type="architect", prompt="[step requirements + task context]")

   For step requiring multiple agents:
   → Invoke multiple Task calls in parallel
   ```

4. **Decision Logging**:
   After each major decision, append to DECISIONS.md:
   - What was decided
   - Why this approach
   - Alternatives considered

5. **Mandatory Cleanup**:
   Always end with Task(subagent_type="cleanup")

## ACTUAL IMPLEMENTATION PROMPT

When `/ultrathink` is called, execute this:

## Agent Orchestration

### When to Use Sequential

- Architecture → Implementation → Review
- Each step depends on previous
- Building progressive context

### When to Use Parallel

- Multiple independent analyses
- Different perspectives needed
- Gathering diverse solutions

## When to Use UltraThink

### Use UltraThink When:

- Task complexity requires deep multi-agent analysis
- Architecture decisions need careful decomposition
- Requirements are vague and need exploration
- Multiple solution paths need evaluation
- Cross-cutting concerns need coordination

### Follow Workflow Directly When:

- Requirements are clear and straightforward
- Solution approach is well-defined
- Standard implementation patterns apply
- Single agent can handle the task

## Task Management

Always use TodoWrite to:

- Break down complex tasks
- Track progress
- Coordinate agents
- Document decisions
- Track workflow checklist completion

## Example Flow

```
1. Read workflow using FrameworkPathResolver.resolve_workflow_file()
2. Begin executing workflow steps with deep analysis
3. Orchestrate multiple agents where complexity requires
4. Follow all workflow steps as defined
5. Adapt to any user customizations automatically
6. MANDATORY: Invoke cleanup agent at task completion
```

## Mandatory Cleanup Phase

**CRITICAL**: Every ultrathink task MUST end with cleanup agent invocation.

The cleanup agent:

- Reviews git status and file changes
- Removes temporary artifacts and planning documents
- Ensures philosophy compliance (ruthless simplicity)
- Provides final report on codebase state
- Guards against technical debt accumulation

**Cleanup Trigger**: Automatically invoke cleanup agent when:

- All todo items are completed
- Main task objectives are achieved
- Before reporting task completion to user

UltraThink enhances the workflow with deep multi-agent analysis while respecting user customizations.

Remember: Ultra-thinking means thorough analysis before action, followed by ruthless cleanup.
