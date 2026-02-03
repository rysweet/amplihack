# TDD Implementation Guide

This guide maps each test file to the implementation file that needs to be created to make tests pass.

## Implementation Order (Recommended)

Implement components in this order based on dependencies:

### Phase 1: Models (No External Dependencies)
1. **models/agent_status.py** ← `tests/unit/test_models.py::TestAgentStatus`
2. **models/orchestration.py** ← `tests/unit/test_orchestration_config.py`
3. **models/completion.py** ← `tests/unit/test_models.py::TestOrchestrationReport`

### Phase 2: Core Components (Basic Functionality)
4. **core/issue_parser.py** ← `tests/unit/test_issue_parser.py`
5. **core/status_monitor.py** ← `tests/unit/test_status_monitor.py`

### Phase 3: Deployment Components
6. **core/agent_deployer.py** ← `tests/unit/test_agent_deployer.py`
7. **core/pr_creator.py** ← `tests/unit/test_pr_creator.py`

### Phase 4: Orchestrator (Ties Everything Together)
8. **core/orchestrator.py** ← `tests/integration/test_orchestration_flow.py`, `tests/e2e/test_*.py`

## Test-to-Implementation Mapping

### Unit Tests → Implementation

| Test File | Implementation File | Classes/Functions | Test Count |
|-----------|---------------------|-------------------|------------|
| `test_models.py::TestAgentStatus` | `models/agent_status.py` | `AgentStatus` dataclass | 10 |
| `test_models.py::TestOrchestrationReport` | `models/completion.py` | `OrchestrationReport` dataclass | 8 |
| `test_models.py::TestErrorDetails` | `models/completion.py` | `ErrorDetails` dataclass | 3 |
| `test_orchestration_config.py` | `models/orchestration.py` | `OrchestrationConfig` dataclass | 18 |
| `test_issue_parser.py` | `core/issue_parser.py` | `GitHubIssueParser` class | 15 |
| `test_status_monitor.py` | `core/status_monitor.py` | `StatusMonitor` class | 23 |
| `test_agent_deployer.py` | `core/agent_deployer.py` | `AgentDeployer` class | 22 |
| `test_pr_creator.py` | `core/pr_creator.py` | `PRCreator` class | 17 |

### Integration Tests → Implementation

| Test File | Implementation Files | Purpose | Test Count |
|-----------|---------------------|---------|------------|
| `test_orchestration_flow.py` | All core components | Multi-component flows | 13 |
| `test_github_integration.py` | `issue_parser.py`, `pr_creator.py` | GitHub CLI interactions | 13 |

### E2E Tests → Implementation

| Test File | Implementation Files | Purpose | Test Count |
|-----------|---------------------|---------|------------|
| `test_simple_orchestration.py` | `core/orchestrator.py` + all | Complete workflows | 10 |
| `test_simserv_integration.py` | All components | SimServ validation | 7 |

## Implementation Checklist

For each component, follow this process:

### 1. Read the Tests
```bash
# Read the test file to understand requirements
cat tests/unit/test_issue_parser.py
```

### 2. Create Module Structure
```bash
# Create the implementation file
touch parallel_task_orchestrator/core/issue_parser.py
```

### 3. Run Tests (Watch Them Fail)
```bash
pytest tests/unit/test_issue_parser.py -v
```

### 4. Implement Minimum Code
```python
# Start with class skeleton
class GitHubIssueParser:
    def parse_sub_issues(self, body: str) -> List[int]:
        # Implement to make first test pass
        pass
```

### 5. Run Tests Again (Watch More Pass)
```bash
pytest tests/unit/test_issue_parser.py -v
```

### 6. Iterate Until All Tests Pass
Repeat steps 4-5 until all tests in the file pass.

### 7. Move to Integration Tests
Once unit tests pass, run integration tests:
```bash
pytest tests/integration/ -v
```

### 8. Finally Run E2E Tests
```bash
pytest tests/e2e/ -v
```

## Expected Test Results by Phase

### Phase 1 Complete (Models)
```bash
$ pytest tests/unit/test_models.py tests/unit/test_orchestration_config.py
================================ test session starts =================================
collected 39 items

tests/unit/test_models.py .......................                          [ 59%]
tests/unit/test_orchestration_config.py ..................                 [100%]

================================ 39 passed in 1.23s ==================================
```

### Phase 2 Complete (Core Components)
```bash
$ pytest tests/unit/
================================ test session starts =================================
collected 97 items

tests/unit/test_agent_deployer.py ......................                   [ 23%]
tests/unit/test_issue_parser.py ...............                            [ 38%]
tests/unit/test_models.py .......................                          [ 62%]
tests/unit/test_orchestration_config.py ..................                 [ 81%]
tests/unit/test_pr_creator.py .................                            [ 94%]
tests/unit/test_status_monitor.py .......................                  [100%]

================================ 97 passed in 4.56s ==================================
```

### Phase 3 Complete (Integration)
```bash
$ pytest tests/unit/ tests/integration/
================================ test session starts =================================
collected 118 items

tests/unit/ ........................................................ [ 82%]
tests/integration/test_github_integration.py .............          [ 93%]
tests/integration/test_orchestration_flow.py .............          [100%]

================================ 118 passed in 8.12s =================================
```

### Phase 4 Complete (E2E)
```bash
$ pytest
================================ test session starts =================================
collected 135 items

tests/unit/ ........................................................ [ 72%]
tests/integration/ ..........................                       [ 88%]
tests/e2e/test_simple_orchestration.py ..........                   [ 95%]
tests/e2e/test_simserv_integration.py .......                       [100%]

================================ 135 passed in 15.23s ================================
```

## Key Implementation Requirements

### Required External Dependencies
```python
# Standard library only for models
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
import json

# subprocess for gh CLI and git
import subprocess

# pathlib for file operations
from pathlib import Path
```

### Key Interfaces to Implement

#### 1. GitHubIssueParser
```python
class GitHubIssueParser:
    def parse_sub_issues(self, body: str) -> List[int]: ...
    def fetch_issue_body(self, issue_number: int) -> str: ...
    def validate_format(self, body: str) -> bool: ...
```

#### 2. OrchestrationConfig
```python
@dataclass
class OrchestrationConfig:
    parent_issue: int
    sub_issues: List[int]
    parallel_degree: int = 5
    timeout_minutes: int = 120
    recovery_strategy: str = "continue_on_failure"
```

#### 3. StatusMonitor
```python
class StatusMonitor:
    def poll_all_agents(self) -> List[Dict]: ...
    def filter_by_status(self, statuses: List[Dict], status: str) -> List[Dict]: ...
    def is_timed_out(self, status: Dict) -> bool: ...
    def all_completed(self, statuses: List[Dict]) -> bool: ...
```

#### 4. AgentDeployer
```python
class AgentDeployer:
    def generate_prompt(self, issue_number: int, ...) -> str: ...
    def create_worktree(self, issue_number: int, ...) -> Path: ...
    def deploy_agent(self, issue_number: int, ...) -> Dict: ...
```

#### 5. PRCreator
```python
class PRCreator:
    def generate_title(self, issue_number: int, ...) -> str: ...
    def generate_body(self, issue_number: int, ...) -> str: ...
    def create_pr(self, branch_name: str, ...) -> Dict: ...
```

#### 6. ParallelOrchestrator
```python
class ParallelOrchestrator:
    def orchestrate(self, parent_issue: int, ...) -> Dict: ...
    def monitor_agents(self) -> None: ...
    def create_prs_for_completed(self) -> List[Dict]: ...
```

## Testing Tips

### 1. Run Single Test
```bash
pytest tests/unit/test_issue_parser.py::TestGitHubIssueParser::test_parse_sub_issues_hash_format -v
```

### 2. Run with Print Statements
```bash
pytest tests/unit/test_issue_parser.py -v -s
```

### 3. Stop on First Failure
```bash
pytest tests/unit/ -x
```

### 4. Show Local Variables on Failure
```bash
pytest tests/unit/ -l
```

### 5. Run Only Failed Tests
```bash
pytest --lf
```

## Success Criteria

✅ All 135 tests pass
✅ Tests execute in <20 seconds
✅ No test uses actual GitHub API (all mocked)
✅ SimServ validation tests pass (confidence baseline)
✅ Integration tests verify component contracts
✅ E2E tests demonstrate complete workflows

## Philosophy Reminder

Remember the core principles while implementing:

1. **Ruthless Simplicity**: Start with simplest implementation that makes tests pass
2. **Zero-BS**: No placeholders or stubs in implementation (tests already define behavior)
3. **Modular**: Each component is a self-contained brick with clear interface
4. **TDD**: Let tests guide implementation, don't fight them

The tests tell you exactly what to build. Trust them!
