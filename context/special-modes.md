# Special Operating Modes

This bundle supports several special operating modes that modify behavior.

## Lock Mode

**Activation**: "lock mode", "lock", "stay focused"

Lock mode restricts the agent to only the current task, preventing scope creep.

### Behavior
- Only processes requests related to the locked task
- Politely declines unrelated requests
- Maintains tight focus until unlocked
- Tracks task completion criteria

### Usage
```
User: lock mode - implement the caching layer
Agent: [Locked to: implement caching layer]
       I'll focus exclusively on implementing the caching layer.
       Any unrelated requests will be deferred until this is complete.
```

### Exit
- "unlock" - releases lock
- Task completion - automatic unlock
- User override - "unlock and [new task]"

---

## Auto Mode

**Activation**: "auto mode", "autonomous", "keep going"

Auto mode enables continuous operation with periodic check-ins.

### Behavior
- Continues working without waiting for confirmation
- Checks in every 5 operations (configurable)
- Provides progress summaries at milestones
- Pauses only for errors or decisions

### Safety Constraints
- Still requires approval for irreversible actions
- Respects tool safety blocks
- Limited to current task scope

### Usage
```
User: auto mode - run all tests and fix any failures
Agent: [Auto Mode Enabled]
       I'll continuously work on running tests and fixing failures.
       I'll check in periodically with progress updates.
       
       [Progress: 3/10 test files processed, 2 failures fixed]
       [Progress: 7/10 test files processed, 5 failures fixed]
       [Complete: All tests passing]
```

### Exit
- Task completion
- Error requiring human judgment
- "stop", "pause", "hold"

---

## Ultrathink Mode

**Activation**: "ultrathink", "think deeply", "analyze thoroughly"

Ultrathink mode enables deep, multi-perspective analysis.

### Task Detection
The mode automatically detects task type:

| Type | Indicators | Workflow |
|------|------------|----------|
| Q&A | "what", "how", "why", "explain" | Research → Synthesize → Answer |
| Investigation | "find", "analyze", "debug" | Scope → Gather → Hypothesis → Test → Conclude |
| Development | "implement", "create", "build" | Understand → Design → Build → Test → Document |

### Mandatory Steps
1. **Understand**: Clarify requirements, identify ambiguities
2. **Research**: Gather relevant context and precedents
3. **Analyze**: Multi-perspective evaluation
4. **Synthesize**: Integrate findings
5. **Validate**: Verify conclusions

### Multi-Perspective Analysis
Engages multiple analytical lenses:
- Technical feasibility
- Security implications
- Performance impact
- Maintainability
- Philosophy alignment

### Usage
```
User: ultrathink - should we use microservices for this project?
Agent: [Ultrathink Mode - Investigation]
       
       ## Understanding
       Key question: Microservices vs monolith for [project]
       Context needed: Team size, deployment requirements, domain complexity
       
       ## Multi-Perspective Analysis
       
       ### Technical Perspective
       [Analysis of technical trade-offs]
       
       ### Operational Perspective
       [Analysis of deployment/monitoring complexity]
       
       ### Team Perspective
       [Analysis of team capabilities and coordination costs]
       
       ## Synthesis
       [Integrated recommendation with confidence level]
```

---

## Mode Combinations

Modes can be combined:

| Combination | Behavior |
|-------------|----------|
| lock + auto | Focused autonomous work on single task |
| lock + ultrathink | Deep focused analysis of single topic |
| auto + ultrathink | Continuous deep analysis (rare) |

## Mode Persistence

- **Session scope**: Modes persist for current session only
- **No permanent change**: Modes don't modify preferences
- **Explicit exit**: Modes require explicit deactivation or task completion
