# Meta-Delegation Concepts

**Understanding the architecture and design of meta-agentic task delegation.**

---

## Overview

Meta-delegation is a system for running AI agents in isolated subprocess environments to accomplish complex tasks autonomously. This document explains the architecture, design decisions, and underlying concepts.

---

## Core Concepts

### What is Meta-Delegation?

**Meta-delegation** means delegating task execution to an AI agent that runs in a separate process, while the parent process monitors execution, collects evidence, and validates results.

```
┌────────────────────────────────────────────────┐
│           Parent Process (Meta-Layer)          │
│                                                │
│  • Defines goal and success criteria           │
│  • Spawns subprocess with selected persona     │
│  • Monitors execution state                    │
│  • Collects evidence artifacts                 │
│  • Evaluates success                           │
│  • Returns structured results                  │
└────────────────────────────────────────────────┘
                        │
                        │ spawns
                        ↓
┌────────────────────────────────────────────────┐
│         Subprocess (Execution Layer)           │
│                                                │
│  • Runs AI agent with persona behavior         │
│  • Executes on chosen platform (Claude/etc)    │
│  • Generates code, tests, documentation        │
│  • Isolated environment (no parent access)     │
└────────────────────────────────────────────────┘
```

**Why Isolation?**

1. **Safety**: Subprocess can't affect parent environment
2. **Reproducibility**: Clean environment each time
3. **Monitoring**: Track execution state externally
4. **Evidence**: Capture all outputs systematically
5. **Validation**: Evaluate results objectively

---

## Architecture

The meta-delegation system consists of 7 modules that work together:

### 1. Platform CLI Abstraction

Provides a unified interface to different AI platform CLIs.

**Purpose**: Hide platform-specific differences behind a common API.

```python
class PlatformCLI(Protocol):
    """Abstract interface for platform CLIs."""

    def spawn_subprocess(
        self,
        goal: str,
        persona: str,
        working_dir: str,
        environment: Dict[str, str]
    ) -> subprocess.Popen:
        """Spawn subprocess with platform-specific command."""
        ...

    def format_prompt(self, goal: str, persona: str, context: str) -> str:
        """Format prompt for platform's expected input format."""
        ...

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse platform-specific output format."""
        ...
```

**Implementations:**

- **ClaudeCodeCLI**: Uses `claude` command
- **CopilotCLI**: Uses GitHub Copilot CLI
- **AmplifierCLI**: Uses Microsoft Amplifier

**Design Decision**: Protocol-based abstraction allows adding new platforms without changing core logic.

---

### 2. Subprocess State Machine

Manages subprocess lifecycle and state transitions.

**States:**

```
CREATED → STARTING → RUNNING → COMPLETING → COMPLETED
                        ↓
                    FAILED
```

**State Definitions:**

| State        | Description                               | Next States                |
| ------------ | ----------------------------------------- | -------------------------- |
| `CREATED`    | Subprocess object created, not started    | `STARTING`                 |
| `STARTING`   | Process launching, waiting for ready      | `RUNNING`, `FAILED`        |
| `RUNNING`    | Agent actively working on task            | `COMPLETING`, `FAILED`     |
| `COMPLETING` | Task done, collecting evidence            | `COMPLETED`, `FAILED`      |
| `COMPLETED`  | Evidence collected, ready for evaluation  | (terminal)                 |
| `FAILED`     | Error occurred, process terminated        | (terminal)                 |

**Example State Flow:**

```
Time  | State       | Event
------|-------------|----------------------------------------
0.0s  | CREATED     | Subprocess object instantiated
0.1s  | STARTING    | Process.spawn() called
0.5s  | RUNNING     | Agent confirms ready, begins task
45.2s | COMPLETING  | Agent signals task complete
46.0s | COMPLETED   | Evidence collection finished
```

**Design Decision**: State machine provides clear lifecycle hooks for monitoring and intervention.

---

### 3. Persona Strategy Module

Defines agent behavior patterns based on persona type.

**Persona Characteristics:**

```python
@dataclass
class PersonaStrategy:
    """Defines persona-specific behavior."""
    name: str
    communication_style: str
    thoroughness_level: str
    evidence_collection_priority: List[str]
    prompt_template: str
```

**Persona Definitions:**

#### Guide Persona

```python
GUIDE = PersonaStrategy(
    name="guide",
    communication_style="socratic",
    thoroughness_level="balanced",
    evidence_collection_priority=[
        "documentation",
        "code_file",
        "test_file"
    ],
    prompt_template="""
    You are a teaching guide. Your goal is to help the user learn by:
    1. Breaking down complex concepts
    2. Providing clear explanations
    3. Including educational examples
    4. Encouraging understanding

    Task: {goal}
    Success Criteria: {success_criteria}

    Focus on creating materials that teach, not just deliver.
    """
)
```

**Behavior:**
- Emphasizes explanations and rationale
- Creates tutorial-style documentation
- Includes learning exercises
- Moderate code output, high documentation

#### QA Engineer Persona

```python
QA_ENGINEER = PersonaStrategy(
    name="qa_engineer",
    communication_style="precise",
    thoroughness_level="exhaustive",
    evidence_collection_priority=[
        "test_file",
        "test_results",
        "validation_report",
        "code_file"
    ],
    prompt_template="""
    You are a QA engineer. Your goal is to ensure quality by:
    1. Identifying edge cases and error conditions
    2. Writing comprehensive test suites
    3. Validating against all success criteria
    4. Documenting findings thoroughly

    Task: {goal}
    Success Criteria: {success_criteria}

    Test everything rigorously and document all findings.
    """
)
```

**Behavior:**
- Tests every scenario exhaustively
- Generates extensive test coverage
- Produces detailed validation reports
- Highest evidence volume

#### Architect Persona

```python
ARCHITECT = PersonaStrategy(
    name="architect",
    communication_style="strategic",
    thoroughness_level="holistic",
    evidence_collection_priority=[
        "architecture_doc",
        "api_spec",
        "diagram",
        "code_file"
    ],
    prompt_template="""
    You are a system architect. Your goal is to design systems by:
    1. Understanding requirements and constraints
    2. Creating high-level architecture
    3. Defining clear interfaces and contracts
    4. Considering scalability and maintainability

    Task: {goal}
    Success Criteria: {success_criteria}

    Focus on design decisions, structure, and system boundaries.
    """
)
```

**Behavior:**
- Emphasizes system design
- Creates architecture diagrams
- Defines clear interfaces
- Strategic documentation

#### Junior Developer Persona

```python
JUNIOR_DEV = PersonaStrategy(
    name="junior_dev",
    communication_style="task_focused",
    thoroughness_level="adequate",
    evidence_collection_priority=[
        "code_file",
        "test_file",
        "documentation"
    ],
    prompt_template="""
    You are a junior developer. Your goal is to implement tasks by:
    1. Following specifications closely
    2. Writing clean, working code
    3. Including basic tests
    4. Documenting what you built

    Task: {goal}
    Success Criteria: {success_criteria}

    Focus on getting it working correctly and cleanly.
    """
)
```

**Behavior:**
- Implementation-focused
- Follows specs closely
- Clean, working code
- Minimal but adequate documentation

**Design Decision**: Persona strategies allow tailoring agent behavior to task requirements without changing core delegation logic.

---

### 4. Gadugi Scenario Generator

Generates comprehensive test scenarios for QA validation.

**Name Origin**: "Gadugi" is a Cherokee concept meaning "working together" — scenarios work together to ensure comprehensive coverage.

**Scenario Categories:**

```python
class ScenarioCategory(Enum):
    HAPPY_PATH = "happy_path"
    ERROR_HANDLING = "error_handling"
    BOUNDARY_CONDITIONS = "boundary_conditions"
    SECURITY = "security"
    PERFORMANCE = "performance"
    INTEGRATION = "integration"
```

**Generation Process:**

1. **Analyze Goal**: Extract entities, operations, constraints
2. **Identify Paths**: Enumerate happy paths and error conditions
3. **Generate Variants**: Create boundary and edge case scenarios
4. **Add Security**: Consider security vulnerabilities
5. **Include Performance**: Add load/stress scenarios

**Example Scenario Generation:**

```python
Goal: "Create a user registration API"

Generated Scenarios:
1. Happy Path: Valid user registration with all required fields
   → Expects: 201 Created, user ID returned

2. Error Handling: Registration with duplicate email
   → Expects: 409 Conflict, clear error message

3. Boundary: Username at maximum length (255 chars)
   → Expects: 201 Created or 400 with validation message

4. Security: SQL injection attempt in email field
   → Expects: Input sanitized, 400 Bad Request

5. Performance: 1000 concurrent registrations
   → Expects: All succeed, response time < 2s per request
```

**Design Decision**: Automated scenario generation ensures comprehensive test coverage without manual enumeration.

---

### 5. Success Criteria Evaluator

Evaluates task completion against success criteria using evidence-based scoring.

**Evaluation Algorithm:**

```python
def evaluate_success(
    success_criteria: str,
    evidence: List[EvidenceItem],
    execution_log: str
) -> Tuple[int, str]:
    """
    Evaluate success using multi-factor analysis.

    Returns: (score: 0-100, notes: str)
    """
    score = 0
    notes = []

    # 1. Parse success criteria into requirements
    requirements = parse_criteria(success_criteria)

    # 2. Check evidence for each requirement
    for req in requirements:
        req_score = evaluate_requirement(req, evidence)
        score += req_score
        if req_score < req.weight:
            notes.append(f"Incomplete: {req.description}")

    # 3. Bonus for quality indicators
    if has_tests_passing(evidence, execution_log):
        score += 10
        notes.append("Bonus: All tests passing")

    if has_documentation(evidence):
        score += 5
        notes.append("Bonus: Documentation included")

    # 4. Normalize to 0-100
    final_score = min(100, score)

    return (final_score, "\n".join(notes))
```

**Evaluation Factors:**

| Factor                    | Weight | Description                           |
| ------------------------- | ------ | ------------------------------------- |
| Required artifacts exist  | 30%    | Code, tests, docs present             |
| Success criteria met      | 40%    | Explicit criteria satisfied           |
| Quality indicators        | 20%    | Tests pass, no errors, clean code     |
| Completeness              | 10%    | No partial implementations            |

**Score Ranges:**

- **90-100**: Exceptional — exceeds criteria with quality
- **80-89**: Success — meets all criteria
- **70-79**: Adequate — meets most criteria, minor gaps
- **60-69**: Partial — significant work done, key gaps
- **50-59**: Incomplete — some progress, major gaps
- **0-49**: Failure — criteria not met

**Design Decision**: Multi-factor evaluation provides nuanced assessment beyond binary pass/fail.

---

### 6. Evidence Collector

Systematically collects artifacts produced during execution.

**Collection Strategy:**

```
1. Monitor working directory for new files
2. Track process output streams (stdout, stderr)
3. Capture file modifications and creations
4. Extract metadata (timestamps, sizes, types)
5. Organize by evidence type
6. Generate excerpts for quick scanning
```

**Evidence Types and Patterns:**

```python
EVIDENCE_PATTERNS = {
    "code_file": ["*.py", "*.js", "*.ts", "*.go", "*.rs", "*.java"],
    "test_file": ["test_*.py", "*_test.py", "*.test.js", "test/*.py"],
    "documentation": ["README.md", "*.md", "docs/*.md"],
    "architecture_doc": ["architecture.md", "design.md", "ARCHITECTURE.md"],
    "api_spec": ["*.yaml", "*.json", "openapi.yaml", "swagger.yaml"],
    "test_results": ["test_output.txt", "pytest.log", "test_results.xml"],
    "execution_log": ["subprocess.log", "execution.log"],
    "validation_report": ["validation_report.md", "success_report.md"],
    "diagram": ["*.mmd", "*.svg", "*.png"],
    "configuration": ["*.yaml", "*.json", "*.toml", "*.ini"]
}
```

**Collection Timing:**

- **Real-time**: Execution logs as they're produced
- **Periodic**: File system scans every 5 seconds
- **Final**: Complete scan after subprocess completes

**Design Decision**: Comprehensive collection ensures all work products are captured without requiring agent cooperation.

---

### 7. Meta-Delegator Orchestrator

Coordinates all modules and manages the complete delegation lifecycle.

**Orchestration Flow:**

```
1. Initialization
   ├─ Validate parameters
   ├─ Select persona strategy
   ├─ Choose platform CLI
   └─ Setup working directory

2. Subprocess Spawn
   ├─ Format prompt with persona strategy
   ├─ Setup environment variables
   ├─ Spawn subprocess via platform CLI
   └─ Initialize state machine

3. Monitoring Loop
   ├─ Poll subprocess state
   ├─ Collect evidence periodically
   ├─ Check for timeout
   ├─ Log progress events
   └─ Wait for completion

4. Evidence Collection
   ├─ Final file system scan
   ├─ Capture complete execution log
   ├─ Organize evidence by type
   └─ Generate excerpts

5. Success Evaluation
   ├─ Parse success criteria
   ├─ Run evaluator on evidence
   ├─ Calculate success score
   └─ Generate evaluation notes

6. Result Construction
   ├─ Build MetaDelegationResult
   ├─ Attach all evidence
   ├─ Include metadata
   └─ Return to caller
```

**Error Handling:**

```python
try:
    # Run delegation
    result = orchestrate_delegation(...)
except DelegationTimeout:
    # Timeout exceeded
    # Return partial results if available
except DelegationError:
    # Subprocess crashed
    # Collect diagnostic information
except Exception:
    # Unexpected error
    # Cleanup and re-raise
finally:
    # Always cleanup subprocess
    cleanup_subprocess()
```

**Design Decision**: Centralized orchestration ensures consistent behavior across all delegation paths.

---

## Design Decisions

### Why Subprocess Isolation?

**Alternative Considered**: In-process execution with namespace isolation.

**Decision**: Use subprocess isolation.

**Rationale:**
1. **True Isolation**: Subprocess can't access parent memory
2. **Platform CLI Support**: Platforms expect separate process invocations
3. **Resource Limits**: Can enforce CPU/memory limits via OS
4. **Fault Tolerance**: Subprocess crash doesn't affect parent
5. **Monitoring**: Process state visible via OS tools

**Trade-offs:**
- ✓ Strong isolation guarantees
- ✓ Platform compatibility
- ✗ Higher resource overhead (~100 MB per subprocess)
- ✗ Inter-process communication complexity

---

### Why Evidence-Based Validation?

**Alternative Considered**: Trust agent's self-reported success.

**Decision**: Collect and validate evidence independently.

**Rationale:**
1. **Objectivity**: Evidence is factual, not subjective
2. **Verification**: Can verify claims with artifacts
3. **Debugging**: Evidence helps diagnose failures
4. **Reproducibility**: Evidence can be re-evaluated
5. **Accountability**: Permanent record of what was produced

**Trade-offs:**
- ✓ Objective validation
- ✓ Comprehensive audit trail
- ✗ Storage overhead (evidence size)
- ✗ Collection complexity

---

### Why Persona Strategies?

**Alternative Considered**: Single general-purpose agent.

**Decision**: Multiple specialized personas.

**Rationale:**
1. **Task Alignment**: Match agent behavior to task needs
2. **Predictability**: Known behavior patterns
3. **Optimization**: Tuned for specific objectives
4. **User Control**: Explicit choice of approach
5. **Evidence Quality**: Better artifacts from specialized agents

**Trade-offs:**
- ✓ Better task alignment
- ✓ Predictable behavior
- ✗ User must choose persona
- ✗ More complex implementation

---

## Performance Characteristics

### Time Complexity

| Operation              | Complexity | Notes                        |
| ---------------------- | ---------- | ---------------------------- |
| Subprocess spawn       | O(1)       | Constant overhead            |
| Evidence collection    | O(n)       | n = number of files          |
| Success evaluation     | O(m)       | m = criteria complexity      |
| Overall delegation     | O(t)       | t = task completion time     |

### Space Complexity

| Component              | Size       | Notes                        |
| ---------------------- | ---------- | ---------------------------- |
| Subprocess overhead    | ~100 MB    | Platform CLI + runtime       |
| Evidence storage       | ~file size | Proportional to artifacts    |
| Result object          | ~10 KB     | Metadata + references        |
| Total per delegation   | ~100 MB    | Plus evidence size           |

### Concurrency

Meta-delegation supports concurrent delegations:

```python
import asyncio
from amplihack.meta_delegation import run_meta_delegation

async def run_concurrent_delegations():
    """Run multiple delegations in parallel."""
    tasks = [
        run_meta_delegation(goal="Task 1", success_criteria="..."),
        run_meta_delegation(goal="Task 2", success_criteria="..."),
        run_meta_delegation(goal="Task 3", success_criteria="...")
    ]

    results = await asyncio.gather(*tasks)
    return results
```

**Concurrency Limits:**

- **Recommended**: 3-5 concurrent delegations
- **Maximum**: Limited by system resources (RAM, CPU)
- **Consideration**: Each subprocess uses ~100 MB

---

## Security Considerations

### Subprocess Isolation

**Threat**: Subprocess could access parent environment or file system.

**Mitigation:**
- Run subprocess in restricted directory
- Don't pass sensitive environment variables
- Use minimal file system permissions
- Monitor subprocess for unauthorized access

### Evidence Validation

**Threat**: Evidence could be manipulated or forged.

**Mitigation:**
- Collect evidence from file system directly (not from agent output)
- Timestamp all evidence collection
- Hash evidence files for integrity
- Store evidence immutably

### Resource Limits

**Threat**: Subprocess could exhaust system resources.

**Mitigation:**
- Enforce timeout limits
- Monitor CPU and memory usage
- Kill runaway processes
- Clean up resources after completion

---

## Extending Meta-Delegation

### Adding New Platforms

Implement the `PlatformCLI` protocol:

```python
from amplihack.meta_delegation import PlatformCLI, register_platform

class MyPlatformCLI(PlatformCLI):
    """Custom platform implementation."""

    def spawn_subprocess(self, goal, persona, working_dir, environment):
        # Launch your platform's CLI
        return subprocess.Popen([
            "my-platform-cli",
            "--goal", goal,
            "--persona", persona
        ], cwd=working_dir, env=environment)

    def format_prompt(self, goal, persona, context):
        # Format for your platform's input
        return f"[{persona}] {goal}\n\nContext:\n{context}"

    def parse_output(self, output):
        # Parse your platform's output format
        return {"stdout": output}

# Register platform
register_platform("my-platform", MyPlatformCLI())

# Use it
result = run_meta_delegation(
    goal="...",
    success_criteria="...",
    platform="my-platform"
)
```

### Adding New Personas

Define a new persona strategy:

```python
from amplihack.meta_delegation import PersonaStrategy, register_persona

RESEARCHER = PersonaStrategy(
    name="researcher",
    communication_style="analytical",
    thoroughness_level="deep",
    evidence_collection_priority=[
        "documentation",
        "analysis_report",
        "data_file"
    ],
    prompt_template="""
    You are a researcher. Your goal is to investigate by:
    1. Gathering information systematically
    2. Analyzing data thoroughly
    3. Documenting findings clearly
    4. Drawing evidence-based conclusions

    Task: {goal}
    Success Criteria: {success_criteria}

    Research deeply and document your methodology.
    """
)

# Register persona
register_persona("researcher", RESEARCHER)

# Use it
result = run_meta_delegation(
    goal="...",
    success_criteria="...",
    persona_type="researcher"
)
```

---

## Related Documentation

- [Tutorial](./tutorial.md) - Learn by doing
- [How-To Guide](./howto.md) - Task recipes
- [Reference](./reference.md) - Complete API
- [Troubleshooting](./troubleshooting.md) - Fix issues

---

**Status**: [PLANNED - Implementation Pending]

This document describes the intended architecture of the meta-delegation system once implemented.
