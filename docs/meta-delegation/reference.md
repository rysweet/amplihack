# Meta-Delegation API Reference

**Complete technical reference for the meta-delegation system.**

---

## Module: `amplihack.meta_delegation`

Primary module for meta-agentic task delegation functionality.

### Functions

#### `run_meta_delegation()`

Execute a task in an isolated subprocess environment with automatic validation.

**Signature:**

```python
def run_meta_delegation(
    goal: str,
    success_criteria: str,
    persona_type: str = "guide",
    platform: str = "claude-code",
    context: Optional[str] = None,
    timeout_minutes: int = 30,
    enable_scenarios: bool = False,
    working_directory: Optional[str] = None,
    environment: Optional[Dict[str, str]] = None
) -> MetaDelegationResult:
    """
    Run meta-delegation task in isolated subprocess.

    Args:
        goal: Primary objective for the agent to accomplish
        success_criteria: Measurable criteria to evaluate success
        persona_type: Agent behavior persona (guide, qa_engineer, architect, junior_dev)
        platform: Platform CLI to use (claude-code, copilot, amplifier)
        context: Optional context information to provide to the agent
        timeout_minutes: Maximum execution time before timeout (default: 30)
        enable_scenarios: Whether to generate test scenarios using Gadugi (default: False)
        working_directory: Custom working directory for subprocess (default: temp dir)
        environment: Additional environment variables for subprocess (default: None)

    Returns:
        MetaDelegationResult object containing status, evidence, and metadata

    Raises:
        DelegationTimeout: If execution exceeds timeout_minutes
        DelegationError: If subprocess fails to start or execute
        ValueError: If invalid persona_type or platform specified

    Example:
        >>> result = run_meta_delegation(
        ...     goal="Create a calculator module",
        ...     success_criteria="Module has add/subtract/multiply/divide functions, tests pass",
        ...     persona_type="junior_dev"
        ... )
        >>> print(result.status)
        'SUCCESS'
        >>> print(result.success_score)
        92
    """
```

**Parameters:**

| Parameter          | Type                  | Default        | Description                                            |
| ------------------ | --------------------- | -------------- | ------------------------------------------------------ |
| `goal`             | `str`                 | (required)     | Task objective for the agent                           |
| `success_criteria` | `str`                 | (required)     | Measurable success indicators                          |
| `persona_type`     | `str`                 | `"guide"`      | Agent persona (see [Personas](#personas))              |
| `platform`         | `str`                 | `"claude-code"`| Platform CLI (see [Platforms](#platforms))             |
| `context`          | `Optional[str]`       | `None`         | Additional context for agent                           |
| `timeout_minutes`  | `int`                 | `30`           | Maximum execution time                                 |
| `enable_scenarios` | `bool`                | `False`        | Enable Gadugi scenario generation                      |
| `working_directory`| `Optional[str]`       | `None`         | Custom working directory (default: temp)               |
| `environment`      | `Optional[Dict[str, str]]` | `None`    | Environment variables for subprocess                   |

**Returns:**

`MetaDelegationResult` object (see [MetaDelegationResult](#metadelegationresult))

**Raises:**

- `DelegationTimeout`: Execution time exceeded `timeout_minutes`
- `DelegationError`: Subprocess failed to start or crashed
- `ValueError`: Invalid `persona_type` or `platform`

---

## Data Classes

### `MetaDelegationResult`

Result object returned by `run_meta_delegation()`.

**Attributes:**

```python
@dataclass
class MetaDelegationResult:
    status: str                          # "SUCCESS", "PARTIAL", or "FAILURE"
    success_score: int                   # Score from 0-100
    evidence: List[EvidenceItem]         # Collected artifacts
    execution_log: str                   # Full subprocess output
    duration_seconds: float              # Total execution time
    persona_used: str                    # Persona that executed the task
    platform_used: str                   # Platform that executed the task
    failure_reason: Optional[str]        # Reason if status is FAILURE
    partial_completion_notes: Optional[str]  # Notes if status is PARTIAL
    subprocess_pid: Optional[int]        # Process ID of subprocess
    test_scenarios: Optional[List[TestScenario]]  # Generated scenarios if enabled
```

**Methods:**

```python
def get_evidence_by_type(self, evidence_type: str) -> List[EvidenceItem]:
    """
    Filter evidence by type.

    Args:
        evidence_type: Type to filter by (e.g., "code_file", "test_file")

    Returns:
        List of EvidenceItem objects matching the type

    Example:
        >>> result = run_meta_delegation(...)
        >>> code_files = result.get_evidence_by_type("code_file")
        >>> for code in code_files:
        ...     print(code.path)
        calculator.py
        utils.py
    """

def get_evidence_by_path_pattern(self, pattern: str) -> List[EvidenceItem]:
    """
    Filter evidence using glob pattern.

    Args:
        pattern: Glob pattern (e.g., "*.py", "test_*.py")

    Returns:
        List of EvidenceItem objects matching the pattern

    Example:
        >>> test_files = result.get_evidence_by_path_pattern("test_*.py")
    """

def export_evidence(self, output_dir: str) -> None:
    """
    Export all evidence to directory.

    Args:
        output_dir: Directory path to export evidence

    Creates directory structure organized by evidence type.

    Example:
        >>> result.export_evidence("./evidence_archive")
    """

def to_json(self) -> str:
    """
    Serialize result to JSON string.

    Returns:
        JSON string representation of result

    Example:
        >>> json_data = result.to_json()
        >>> with open("result.json", "w") as f:
        ...     f.write(json_data)
    """

@classmethod
def from_json(cls, json_str: str) -> 'MetaDelegationResult':
    """
    Deserialize result from JSON string.

    Args:
        json_str: JSON string representation

    Returns:
        MetaDelegationResult object

    Example:
        >>> with open("result.json") as f:
        ...     json_data = f.read()
        >>> result = MetaDelegationResult.from_json(json_data)
    """
```

**Status Values:**

| Status    | Success Score | Meaning                                     |
| --------- | ------------- | ------------------------------------------- |
| `SUCCESS` | 80-100        | Task completed, success criteria met        |
| `PARTIAL` | 50-79         | Task completed with issues or gaps          |
| `FAILURE` | 0-49          | Task failed or success criteria not met     |

---

### `EvidenceItem`

Individual piece of evidence collected during execution.

```python
@dataclass
class EvidenceItem:
    type: str                # Evidence type (see Evidence Types below)
    path: str                # File path or identifier
    content: str             # Full content of the artifact
    excerpt: Optional[str]   # Brief excerpt (first 200 chars)
    size_bytes: int          # Size of content in bytes
    timestamp: datetime      # When evidence was collected
    metadata: Dict[str, Any] # Additional metadata

    def save_to_file(self, output_path: str) -> None:
        """
        Save evidence content to file.

        Args:
            output_path: Path to save file

        Example:
            >>> evidence = result.evidence[0]
            >>> evidence.save_to_file("./output/code.py")
        """

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get metadata value.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default

        Example:
            >>> language = evidence.get_metadata("language", "python")
        """
```

**Evidence Types:**

| Type                 | Description                            | Typical Files           |
| -------------------- | -------------------------------------- | ----------------------- |
| `code_file`          | Source code files                      | `*.py`, `*.js`, etc.    |
| `test_file`          | Test files                             | `test_*.py`, `*.test.js`|
| `documentation`      | Documentation files                    | `README.md`, `*.md`     |
| `architecture_doc`   | Architecture/design documents          | `architecture.md`       |
| `api_spec`           | API specifications                     | `openapi.yaml`, etc.    |
| `test_results`       | Test execution results                 | `test_output.txt`       |
| `execution_log`      | Subprocess output logs                 | `subprocess.log`        |
| `validation_report`  | Success criteria evaluation report     | `validation_report.md`  |
| `diagram`            | Visual diagrams                        | `*.mmd`, `*.svg`        |
| `configuration`      | Configuration files                    | `*.yaml`, `*.json`      |

---

### `TestScenario`

Generated test scenario from Gadugi (when `enable_scenarios=True`).

```python
@dataclass
class TestScenario:
    name: str                   # Scenario name
    category: str               # Category (happy_path, error_handling, etc.)
    description: str            # Detailed description
    preconditions: List[str]    # Setup requirements
    steps: List[str]            # Test steps
    expected_outcome: str       # Expected result
    priority: str               # "high", "medium", "low"
    tags: List[str]             # Searchable tags
```

**Scenario Categories:**

| Category               | Description                                    |
| ---------------------- | ---------------------------------------------- |
| `happy_path`           | Normal successful operations                   |
| `error_handling`       | Invalid inputs and error conditions            |
| `boundary_conditions`  | Edge cases and limits                          |
| `security`             | Security vulnerabilities and exploits          |
| `performance`          | Load, stress, and performance scenarios        |
| `integration`          | Cross-system and integration scenarios         |

---

## Exceptions

### `DelegationTimeout`

Raised when execution exceeds the specified timeout.

```python
class DelegationTimeout(Exception):
    """
    Delegation execution exceeded timeout.

    Attributes:
        elapsed_minutes: Actual execution time in minutes
        timeout_minutes: Configured timeout limit
        partial_result: Partial MetaDelegationResult if available
    """
    def __init__(
        self,
        elapsed_minutes: float,
        timeout_minutes: int,
        partial_result: Optional[MetaDelegationResult] = None
    ):
        self.elapsed_minutes = elapsed_minutes
        self.timeout_minutes = timeout_minutes
        self.partial_result = partial_result
```

**Example:**

```python
from amplihack.meta_delegation import run_meta_delegation, DelegationTimeout

try:
    result = run_meta_delegation(
        goal="Complex task",
        success_criteria="...",
        timeout_minutes=10
    )
except DelegationTimeout as e:
    print(f"Timed out after {e.elapsed_minutes:.1f} minutes")
    if e.partial_result:
        print(f"Partial evidence: {len(e.partial_result.evidence)} items")
```

---

### `DelegationError`

Raised when subprocess fails to start or crashes.

```python
class DelegationError(Exception):
    """
    Delegation subprocess failed.

    Attributes:
        reason: Error description
        subprocess_output: Output from failed subprocess (if available)
        exit_code: Process exit code (if available)
    """
    def __init__(
        self,
        reason: str,
        subprocess_output: Optional[str] = None,
        exit_code: Optional[int] = None
    ):
        self.reason = reason
        self.subprocess_output = subprocess_output
        self.exit_code = exit_code
```

**Example:**

```python
from amplihack.meta_delegation import run_meta_delegation, DelegationError

try:
    result = run_meta_delegation(
        goal="Task requiring missing dependencies",
        success_criteria="..."
    )
except DelegationError as e:
    print(f"Delegation failed: {e.reason}")
    if e.subprocess_output:
        print(f"Last output:\n{e.subprocess_output[-500:]}")  # Last 500 chars
```

---

## Enumerations

### Personas

Valid values for `persona_type` parameter:

```python
class Persona(Enum):
    GUIDE = "guide"
    QA_ENGINEER = "qa_engineer"
    ARCHITECT = "architect"
    JUNIOR_DEV = "junior_dev"
```

**Persona Characteristics:**

| Persona      | Communication Style | Thoroughness | Speed   | Evidence Volume |
| ------------ | ------------------- | ------------ | ------- | --------------- |
| `guide`      | Explanatory         | Balanced     | Moderate| Medium          |
| `qa_engineer`| Precise             | Exhaustive   | Slower  | High            |
| `architect`  | Strategic           | Holistic     | Moderate| Medium          |
| `junior_dev` | Task-focused        | Adequate     | Faster  | Low             |

See [Concepts: Personas](./concepts.md#personas) for detailed behavior.

---

### Platforms

Valid values for `platform` parameter:

```python
class Platform(Enum):
    CLAUDE_CODE = "claude-code"
    COPILOT = "copilot"
    AMPLIFIER = "amplifier"
```

**Platform Capabilities:**

| Platform       | Subprocess Isolation | Evidence Collection | Scenario Generation | Notes              |
| -------------- | -------------------- | ------------------- | ------------------- | ------------------ |
| `claude-code`  | ✅ Full              | ✅ Full             | ✅ Full             | Default, recommended |
| `copilot`      | ✅ Full              | ✅ Full             | ✅ Full             | Requires Copilot CLI |
| `amplifier`    | ✅ Full              | ✅ Full             | ✅ Full             | Requires Amplifier   |

---

## Configuration

### Environment Variables

Meta-delegation respects the following environment variables:

| Variable                        | Default       | Description                           |
| ------------------------------- | ------------- | ------------------------------------- |
| `META_DELEGATION_TIMEOUT`       | `1800`        | Default timeout in seconds            |
| `META_DELEGATION_WORK_DIR`      | `~/.amplihack/meta_delegation` | Working directory |
| `META_DELEGATION_LOG_LEVEL`     | `INFO`        | Logging level                         |
| `META_DELEGATION_KEEP_ARTIFACTS`| `false`       | Keep subprocess artifacts after completion |

**Example:**

```bash
export META_DELEGATION_TIMEOUT=3600  # 1 hour
export META_DELEGATION_KEEP_ARTIFACTS=true
python my_delegation.py
```

---

## Advanced Usage

### Custom Evidence Collectors

Register custom evidence collectors for specialized artifacts:

```python
from amplihack.meta_delegation import register_evidence_collector

def collect_performance_metrics(working_dir: str) -> List[EvidenceItem]:
    """Custom collector for performance metrics."""
    metrics_file = os.path.join(working_dir, "performance.json")
    if os.path.exists(metrics_file):
        with open(metrics_file) as f:
            content = f.read()
        return [EvidenceItem(
            type="performance_metrics",
            path="performance.json",
            content=content,
            excerpt=content[:200],
            size_bytes=len(content),
            timestamp=datetime.now(),
            metadata={"collector": "custom_performance"}
        )]
    return []

# Register collector
register_evidence_collector("performance_metrics", collect_performance_metrics)

# Now performance metrics will be automatically collected
result = run_meta_delegation(...)
perf_metrics = result.get_evidence_by_type("performance_metrics")
```

---

### Custom Success Evaluators

Implement custom success evaluation logic:

```python
from amplihack.meta_delegation import register_success_evaluator

def custom_evaluator(
    goal: str,
    success_criteria: str,
    evidence: List[EvidenceItem],
    execution_log: str
) -> Tuple[int, str]:
    """
    Custom success evaluation logic.

    Args:
        goal: Original goal
        success_criteria: Original success criteria
        evidence: Collected evidence
        execution_log: Subprocess output

    Returns:
        Tuple of (score: int, notes: str)
    """
    score = 50  # Base score

    # Check for required evidence types
    if any(e.type == "code_file" for e in evidence):
        score += 10

    if any(e.type == "test_file" for e in evidence):
        score += 15

    # Check test results in log
    if "All tests passed" in execution_log:
        score += 25

    notes = f"Evaluated {len(evidence)} evidence items"
    return (score, notes)

# Register evaluator
register_success_evaluator("custom", custom_evaluator)

# Use custom evaluator
result = run_meta_delegation(
    goal="...",
    success_criteria="...",
    evaluator="custom"
)
```

---

## Subprocess Interaction

### Monitoring Subprocess State

Monitor subprocess execution in real-time:

```python
from amplihack.meta_delegation import run_meta_delegation_async
import asyncio

async def run_with_monitoring():
    """Run delegation with progress monitoring."""
    async for event in run_meta_delegation_async(
        goal="Long-running task",
        success_criteria="...",
        persona_type="architect"
    ):
        if event.type == "progress":
            print(f"Progress: {event.data['percentage']}%")
        elif event.type == "log":
            print(f"Log: {event.data['message']}")
        elif event.type == "evidence_collected":
            print(f"Evidence: {event.data['item'].path}")
        elif event.type == "completed":
            result = event.data['result']
            print(f"Completed: {result.status}")
            return result

result = asyncio.run(run_with_monitoring())
```

**Event Types:**

| Event Type           | Description                    | Data Fields                        |
| -------------------- | ------------------------------ | ---------------------------------- |
| `started`            | Subprocess started             | `pid`, `timestamp`                 |
| `progress`           | Progress update                | `percentage`, `message`            |
| `log`                | Log message from subprocess    | `message`, `level`, `timestamp`    |
| `evidence_collected` | New evidence collected         | `item` (EvidenceItem)              |
| `evaluation_start`   | Success evaluation starting    | `criteria`                         |
| `evaluation_complete`| Success evaluation done        | `score`, `notes`                   |
| `completed`          | Delegation completed           | `result` (MetaDelegationResult)    |
| `error`              | Error occurred                 | `error`, `traceback`               |

---

## Type Hints

Complete type definitions for type checking:

```python
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# Import all public types
from amplihack.meta_delegation import (
    MetaDelegationResult,
    EvidenceItem,
    TestScenario,
    DelegationTimeout,
    DelegationError,
    Persona,
    Platform
)
```

---

## Performance Considerations

### Timeouts

- Default timeout: 30 minutes
- Minimum recommended: 5 minutes
- Maximum supported: 4 hours

**Guideline:**

- Simple tasks (< 100 LOC): 10-15 minutes
- Medium tasks (100-500 LOC): 30-45 minutes
- Complex tasks (> 500 LOC): 60+ minutes

### Evidence Collection Overhead

Evidence collection adds minimal overhead:

- File scanning: ~1-2 seconds per 100 files
- Content extraction: ~0.1 seconds per MB
- Typical overhead: < 5% of total execution time

### Memory Usage

- Base overhead: ~50 MB
- Per evidence item: ~5 KB + content size
- Subprocess isolation: ~100 MB

**Large Codebases:**

For projects > 1000 files, consider:

```python
result = run_meta_delegation(
    goal="...",
    success_criteria="...",
    working_directory="/tmp/isolated",  # Use dedicated directory
    environment={"PYTHONPATH": ""}      # Clean environment
)
```

---

## Version Compatibility

**Minimum Versions:**

- Python: 3.8+
- amplihack: 0.9.0+
- Claude Code: Any
- GitHub Copilot CLI: 1.0.0+
- Microsoft Amplifier: 1.0.0+

**Python Version Matrix:**

| Python | Status       | Notes                |
| ------ | ------------ | -------------------- |
| 3.8    | ✅ Supported | Minimum version      |
| 3.9    | ✅ Supported | Recommended          |
| 3.10   | ✅ Supported | Recommended          |
| 3.11   | ✅ Supported | Best performance     |
| 3.12   | ✅ Supported | Latest features      |

---

## Related Documentation

- [Tutorial](./tutorial.md) - Learn by doing
- [How-To Guide](./howto.md) - Common tasks
- [Concepts](./concepts.md) - Architecture and design
- [Troubleshooting](./troubleshooting.md) - Fix problems

---

**Status**: [PLANNED - Implementation Pending]

This reference describes the intended API of the meta-delegation system once implemented.
