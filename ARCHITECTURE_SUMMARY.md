# Architecture Summary: Issue #2353 Session Start Workflow

## System Overview

The session start workflow system is a **4-module brick architecture** that
classifies user requests and routes them to appropriate workflow handlers.

```
SessionStartClassifierSkill (Orchestrator)
    ├── SessionStartDetector (Trigger Detector)
    ├── WorkflowClassifier (4-Way Router)
    └── ExecutionTierCascade (Fallback Executor)
```

---

## Module Architecture

### 1. SessionStartDetector (72 lines)

**Responsibility**: Determine when workflow classification should trigger

**Public Contract**:

```python
is_session_start(context: Dict[str, Any]) -> bool
should_bypass_classification(context: Dict[str, Any]) -> bool
```

**Logic**:

```
Bypass if:
  - is_explicit_command = True
  - user_request starts with "/"

Classify if:
  - is_first_message = True
  - AND not bypassed

Otherwise:
  - Do not classify (follow-up message)
```

**Input Keys**:

- `is_first_message` (bool): Whether this is the session's first message
- `is_explicit_command` (bool): Whether user used explicit command like
  `/ultrathink`
- `user_request` or `prompt` (str): The user's request text
- `message_count` (int, optional): Total message count

**Output**: Boolean indicating if classification should trigger

**Design Notes**:

- Zero dependencies on other modules
- No state (stateless)
- Clear early-return pattern
- No hypothesis checking (just reads what's provided)

---

### 2. WorkflowClassifier (205 lines)

**Responsibility**: Route user requests to one of 4 workflows

**Public Contract**:

```python
classify(request: str, context: Optional[Dict] = None) -> Dict[str, Any]
format_announcement(result: Dict[str, Any]) -> str
```

**4-Way Classification**:

```
Q&A_WORKFLOW (Question & Answer)
├─ "what is"
├─ "explain briefly"
├─ "quick question"
├─ "how do i run"
├─ "what does"
└─ "can you explain"

OPS_WORKFLOW (Operations)
├─ "run command"
├─ "disk cleanup"
├─ "repo management"
├─ "git operations"
├─ "delete files"
├─ "cleanup" / "clean up"
└─ "organize" / "manage"

INVESTIGATION_WORKFLOW (Research)
├─ "investigate"
├─ "understand"
├─ "analyze"
├─ "research"
├─ "explore"
├─ "how does"
└─ "how it works"

DEFAULT_WORKFLOW (Development)
├─ "implement"
├─ "add"
├─ "fix"
├─ "create"
├─ "refactor"
├─ "update"
├─ "build"
├─ "develop"
├─ "remove"
├─ "delete"
└─ "modify"
```

**Priority Order**:

```
1. DEFAULT_WORKFLOW (highest priority - development tasks)
2. INVESTIGATION_WORKFLOW (research/analysis)
3. OPS_WORKFLOW (operations/admin)
4. Q&A_WORKFLOW (lowest priority - simple questions)

This ensures "implement analyze" → DEFAULT (not INVESTIGATION)
```

**Classification Algorithm**:

1. Extract keywords from request (case-insensitive substring match)
2. Check priority order
3. Return first workflow with matching keywords
4. If no matches: DEFAULT_WORKFLOW with confidence 0.5

**Return Format**:

```python
{
    "workflow": "DEFAULT_WORKFLOW",
    "reason": "keyword 'implement'",
    "confidence": 0.9,
    "keywords": ["implement", "create"],
    "context": {...}  # If provided
}
```

**Features**:

- Customizable keywords (can extend on init)
- Confidence scores (0.9 for clear match, 0.5 for ambiguous)
- Keyword extraction (returns matched keywords)
- User-friendly announcement formatting

**Design Notes**:

- No machine learning (intentional simplicity)
- No fuzzy matching (substring is enough)
- Transparent keyword lists
- Configurable via constructor

---

### 3. ExecutionTierCascade (307 lines)

**Responsibility**: Execute workflow via highest available tier with fallback

**Tier Architecture**:

```
Tier 1: Recipe Runner (Fastest)
├─ Use if: Available and AMPLIHACK_USE_RECIPES != "0"
├─ Method: run_recipe_by_name(recipe_name, context)
└─ Recipes: default-workflow, investigation-workflow

Tier 2: Workflow Skills (LLM-Driven)
├─ Use if: Tier 1 fails and skills available
├─ Method: skill.execute(workflow, context)
└─ Status: Not yet implemented (raises ImportError)

Tier 3: Markdown (Always Works)
├─ Use if: Tier 1 and 2 fail (fallback)
├─ Method: Return success, Claude reads markdown
└─ Note: This always works - guaranteed fallback
```

**Public Contract**:

```python
execute(workflow: str, context: Optional[Dict] = None) -> Dict[str, Any]
detect_available_tier(self) -> int
is_recipe_runner_available(self) -> bool
is_workflow_skills_available(self) -> bool
is_markdown_available(self) -> bool
workflow_to_recipe_name(workflow: str) -> Optional[str]
```

**Execution Result**:

```python
{
    "tier": 1,                           # Which tier succeeded
    "method": "recipe_runner",           # Method name
    "status": "success",                 # Execution status
    "workflow": "DEFAULT_WORKFLOW",      # Original workflow
    "recipe": "default-workflow",        # Recipe name (if tier 1)
    "execution_time": 1.234,            # Seconds
    "fallback_count": 0,                # How many fallbacks attempted
    "fallback_reason": "Tier 1 failed: ..."  # Why fallback occurred
}
```

**Workflow to Recipe Mapping**:

```python
{
    "DEFAULT_WORKFLOW": "default-workflow",
    "INVESTIGATION_WORKFLOW": "investigation-workflow",
    "Q&A_WORKFLOW": None,      # No recipe - direct answer
    "OPS_WORKFLOW": None,      # No recipe - direct execution
}
```

**Features**:

- Automatic tier detection based on availability
- Graceful fallback on failure
- Execution timing and metrics
- Fallback reason tracking
- Customizable tier priority order
- Environment variable control (AMPLIHACK_USE_RECIPES)

**Design Notes**:

- Tier 3 always succeeds (markdown is guaranteed available)
- Each tier is independent (failure doesn't cascade internally)
- Dependency injection for recipe_runner and workflow_skill
- Lazy import pattern defers errors to when tier is actually used

---

### 4. SessionStartClassifierSkill (147 lines)

**Responsibility**: Orchestrate all three components in correct sequence

**Public Contract**:

```python
process(context: Dict[str, Any]) -> Dict[str, Any]
```

**Processing Pipeline**:

```
1. Check: Should bypass classification?
   ├─ If yes: Return {bypassed: True, reason: "explicit_command" or "follow_up_message"}
   └─ If no: Continue to step 2

2. Check: Is this a session start?
   ├─ If no: Return {activated: False}
   └─ If yes: Continue to step 3

3. Classify the request
   ├─ Extract user_request from context
   ├─ Call WorkflowClassifier.classify()
   ├─ Set activated=True, should_classify=True
   └─ Continue to step 4

4. Format announcement
   ├─ Determine if Recipe Runner available
   ├─ Call WorkflowClassifier.format_announcement()
   └─ Continue to step 5

5. Execute workflow (if applicable)
   ├─ If DEFAULT or INVESTIGATION: Call ExecutionTierCascade.execute()
   ├─ If Q&A or OPS: Skip execution (direct handling)
   └─ Capture execution result

6. Return comprehensive result
   └─ {activated, classification, workflow, reason, announcement, tier, method, status, ...}
```

**Result Structure**:

```python
{
    # Activation status
    "activated": True,              # Did classification trigger?
    "should_classify": True,        # Synonym for activated
    "bypassed": False,              # Was classification bypassed?

    # Classification results
    "classification": {...},        # Full classification result
    "workflow": "DEFAULT_WORKFLOW", # Classified workflow
    "reason": "keyword 'implement'",# Why this workflow

    # Execution results (if applicable)
    "tier": 1,                      # Execution tier used
    "method": "recipe_runner",      # Execution method
    "status": "success",            # Execution status
    "execution": {...},             # Full execution result

    # User-facing output
    "announcement": "WORKFLOW: DEFAULT\n...",  # Announcement to display

    # Augmented context
    "context": {...},               # Context with classification added
}
```

**Features**:

- Bypass detection (explicit commands, slash commands, follow-ups)
- Graceful degradation (continues even if classification fails)
- Result completeness (tier, method, status always present)
- Context augmentation (adds classification to context for downstream)
- Flexible response (different fields for different scenarios)

**Design Notes**:

- Orchestrator pattern: Calls three modules in sequence
- No business logic of its own (just coordination)
- Supports both 'prompt' and 'user_request' context keys
- Always returns result dict (never raises on invalid input)

---

## Data Flow Diagram

```
User Request
    ↓
SessionStartClassifierSkill.process(context)
    ↓
    ├→ SessionStartDetector.should_bypass_classification()
    │   ├─ Check is_explicit_command
    │   ├─ Check "/" prefix
    │   └─ Check is_first_message
    │
    ├→ SessionStartDetector.is_session_start()
    │   └─ Return if classification should trigger
    │
    ├→ WorkflowClassifier.classify(request)
    │   ├─ Extract keywords
    │   ├─ Check priority order
    │   └─ Return {workflow, reason, confidence, keywords}
    │
    ├→ WorkflowClassifier.format_announcement()
    │   ├─ Check Recipe Runner availability
    │   └─ Format user message
    │
    ├→ ExecutionTierCascade.execute(workflow, context)
    │   ├─ Tier 1: Try Recipe Runner
    │   ├─ Tier 2: Try Workflow Skills
    │   ├─ Tier 3: Return Markdown (always succeeds)
    │   └─ Return {tier, method, status, ...}
    │
    └→ Return comprehensive result
        {activated, workflow, announcement, tier, method, status, ...}
```

---

## Module Dependencies

**Dependency Graph**:

```
SessionStartClassifierSkill
├─ depends on: SessionStartDetector
├─ depends on: WorkflowClassifier
└─ depends on: ExecutionTierCascade

ExecutionTierCascade
├─ depends on: (optional) recipe_runner (injected)
├─ depends on: (optional) workflow_skill (injected)
└─ depends on: logging

WorkflowClassifier
├─ depends on: typing
└─ depends on: logging

SessionStartDetector
└─ depends on: typing
```

**Coupling Analysis**:

- All dependencies are explicit (no global imports)
- All external dependencies are injected
- No circular dependencies
- No implicit dependencies on singletons

---

## Configuration Points

**1. Custom Keywords**:

```python
classifier = WorkflowClassifier(custom_keywords={
    "Q&A_WORKFLOW": ["tell me about"],
    "DEFAULT_WORKFLOW": ["build", "construct"],
})
```

**2. Custom Tier Priority**:

```python
cascade = ExecutionTierCascade(tier_priority=[3, 1, 2])  # Markdown first
```

**3. Pre-configured Instances**:

```python
skill = SessionStartClassifierSkill(
    classifier=my_classifier,
    cascade=my_cascade,
    detector=my_detector,
)
```

**4. Environment Variable**:

```bash
export AMPLIHACK_USE_RECIPES=0  # Disable Recipe Runner
# System will fall back to Workflow Skills or Markdown
```

---

## Testing Strategy

**Test Distribution** (Proportional):

- 60% Unit Tests: Classification logic, detection, cascade logic
- 20% Integration Tests: Component interaction, tier detection
- 20% Acceptance Tests: End-to-end workflow behavior

**Test Organization**:

```
tests/workflows/
├─ test_classifier.py (classification logic)
├─ test_session_start.py (detection logic)
├─ test_execution_tier_cascade.py (tier execution)
├─ test_session_start_integration.py (components together)
├─ test_e2e_acceptance_criteria.py (full workflows)
├─ test_performance.py (speed metrics)
└─ test_regression.py (historical bugs)
```

---

## Key Design Decisions

| Decision                                 | Rationale                          | Alternative Considered            |
| ---------------------------------------- | ---------------------------------- | --------------------------------- |
| Keyword matching (substring)             | Simple, transparent, sufficient    | Fuzzy matching (overly complex)   |
| Priority order (DEFAULT > INVESTIGATION) | Development is primary use case    | Other priorities (wrong priority) |
| Tier cascade with markdown fallback      | Always works, graceful degradation | Single method (fails hard)        |
| No ML classification                     | Ruthless simplicity, maintainable  | Neural networks (overkill)        |
| Dependency injection                     | Testable, decoupled                | Singletons (hard to test)         |
| Lazy imports                             | Works without recipe runner        | Eager imports (breaks early)      |

---

## Error Handling Strategy

**1. Classification Errors**:

- Invalid request type → raises TypeError with clear message
- Empty request → raises ValueError
- Other errors → logged, returns activated=False

**2. Execution Errors**:

- Tier 1 fails → falls back to Tier 2
- Tier 2 fails → falls back to Tier 3
- Tier 3 never fails (guaranteed markdown)

**3. Configuration Errors**:

- Unknown workflow → raises ValueError in execute()
- Invalid context → gracefully continues with partial data

**4. Graceful Degradation**:

```
Recipe Runner unavailable → Workflow Skills
Workflow Skills unavailable → Markdown (always works)
```

---

## Extensibility

**Adding New Workflows**:

1. Add keywords to `WorkflowClassifier.DEFAULT_KEYWORD_MAP`
2. Adjust priority if needed
3. No other changes required

**Adding New Tiers**:

1. Implement tier check method
2. Add to tier priority list
3. Implement `_execute_tierN` method
4. Update `detect_available_tier()` logic

**Customizing Classification**:

```python
classifier = WorkflowClassifier(custom_keywords={
    "CUSTOM_WORKFLOW": ["my", "keywords"]
})
```

---

## Summary

The system achieves **simplicity through clear separation of concerns**:

1. **SessionStartDetector**: Knows when to classify (not what)
2. **WorkflowClassifier**: Knows which workflow (not how to execute)
3. **ExecutionTierCascade**: Knows how to execute (not which workflow)
4. **SessionStartClassifierSkill**: Orchestrates all three

Each brick is independently testable, replaceable, and understandable. The
architecture scales horizontally (more keywords, more tiers, more workflows)
without increasing complexity.
