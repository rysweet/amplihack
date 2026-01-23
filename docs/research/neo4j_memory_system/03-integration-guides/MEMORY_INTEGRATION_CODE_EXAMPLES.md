# Memory System Integration: Concrete Code Examples

## Overview

This document provides concrete Python implementation examples for integrating a memory system into Claude Code agents. All examples follow the "minimal integration" principle: maximum value with minimum changes.

---

## Part 1: Core Memory System Components

### 1.1 Memory Store (Simple JSON-Based)

**File**: `~/.amplihack/.claude/memory/system/memory_store.py`

```python
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class MemoryStore:
    """Simple JSON-based memory storage system."""

    def __init__(self, base_path: str = ".claude/runtime/memory"):
        """Initialize memory store with base directory."""
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (self.base_path / "agents").mkdir(exist_ok=True)
        (self.base_path / "workflows").mkdir(exist_ok=True)
        (self.base_path / "errors").mkdir(exist_ok=True)
        (self.base_path / "users").mkdir(exist_ok=True)
        (self.base_path / "domains").mkdir(exist_ok=True)

    def _get_file_path(self, category: str, name: str) -> Path:
        """Get full file path for a memory item."""
        if category not in ["agents", "workflows", "errors", "users", "domains"]:
            raise ValueError(f"Invalid category: {category}")
        return self.base_path / category / f"{name}.json"

    def store(self, category: str, name: str, data: Dict[str, Any]) -> None:
        """Store a memory item."""
        file_path = self._get_file_path(category, name)

        # Load existing data if file exists
        existing_data = []
        if file_path.exists():
            try:
                existing_data = json.loads(file_path.read_text())
                if not isinstance(existing_data, list):
                    existing_data = [existing_data]
            except json.JSONDecodeError:
                existing_data = []

        # Add timestamp if not present
        if "timestamp" not in data:
            data["timestamp"] = datetime.now().isoformat()

        # Append new data (store history)
        existing_data.append(data)

        # Write back
        file_path.write_text(json.dumps(existing_data, indent=2))

    def retrieve(self, category: str, name: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve all memory items for a category/name."""
        file_path = self._get_file_path(category, name)

        if not file_path.exists():
            return None

        try:
            data = json.loads(file_path.read_text())
            return data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            return None

    def update(self, category: str, name: str, data: Dict[str, Any]) -> None:
        """Update/replace all memory items for a category/name."""
        file_path = self._get_file_path(category, name)
        if "timestamp" not in data:
            data["timestamp"] = datetime.now().isoformat()
        file_path.write_text(json.dumps([data], indent=2))

    def get_all(self, category: str) -> Dict[str, Any]:
        """Get all memory items in a category."""
        category_path = self.base_path / category
        if not category_path.exists():
            return {}

        result = {}
        for file_path in category_path.glob("*.json"):
            name = file_path.stem
            try:
                result[name] = json.loads(file_path.read_text())
            except json.JSONDecodeError:
                pass

        return result

    def clear(self, category: str, name: str) -> None:
        """Clear memory items."""
        file_path = self._get_file_path(category, name)
        if file_path.exists():
            file_path.unlink()
```

### 1.2 Memory Retrieval Interface

**File**: `~/.amplihack/.claude/memory/system/memory_retrieval.py`

```python
from typing import Dict, List, Any, Optional
from .memory_store import MemoryStore

class MemoryRetrieval:
    """Query interface for memory system."""

    def __init__(self, store: MemoryStore):
        """Initialize with memory store."""
        self.store = store

    def query_pre_execution(
        self,
        agent_name: str,
        task_category: Optional[str] = None,
        user_domain: Optional[str] = None
    ) -> str:
        """
        Query memory for context to inject before agent execution.

        Returns formatted markdown string for prompt injection.
        """
        context_parts = []

        # 1. Similar past agent decisions
        agent_history = self.store.retrieve("agents", agent_name)
        if agent_history:
            similar_tasks = [
                item for item in agent_history
                if task_category is None or item.get("task_category") == task_category
            ]

            if similar_tasks:
                # Get top 3 most recent successful tasks
                successful = [t for t in similar_tasks if t.get("success", False)]
                top_tasks = sorted(
                    successful,
                    key=lambda x: x.get("timestamp", ""),
                    reverse=True
                )[:3]

                if top_tasks:
                    context_parts.append("## Memory: Similar Past Tasks")
                    context_parts.append(f"Found {len(top_tasks)} successful similar tasks:")
                    for task in top_tasks:
                        context_parts.append(
                            f"- **{task.get('decision', 'Unknown')}**: "
                            f"{task.get('reasoning', '')} "
                            f"(Quality: {task.get('outcome_quality', 0)}/10)"
                        )
                    context_parts.append("")

        # 2. Domain-specific context
        if user_domain:
            domain_context = self.store.retrieve("domains", user_domain)
            if domain_context:
                context_parts.append("## Memory: Domain Context")
                for item in domain_context:
                    if "patterns" in item:
                        context_parts.append("**Recommended Patterns:**")
                        for pattern in item["patterns"]:
                            context_parts.append(f"- {pattern}")
                    if "common_issues" in item:
                        context_parts.append("**Watch Out For:**")
                        for issue in item["common_issues"]:
                            context_parts.append(f"- {issue}")
                context_parts.append("")

        # 3. Common errors for this agent
        error_history = self.store.retrieve("errors", agent_name)
        if error_history and len(error_history) > 3:
            context_parts.append("## Memory: Common Error Patterns")
            errors = sorted(
                error_history,
                key=lambda x: x.get("frequency", 0),
                reverse=True
            )[:3]
            for error in errors:
                context_parts.append(
                    f"- **{error.get('error_type', 'Unknown')}**: "
                    f"{error.get('prevention_tip', '')}"
                )
            context_parts.append("")

        return "\n".join(context_parts) if context_parts else ""

    def get_agent_stats(self, agent_name: str) -> Dict[str, Any]:
        """Get statistics for an agent."""
        history = self.store.retrieve("agents", agent_name)
        if not history:
            return {}

        successful = [h for h in history if h.get("success", False)]
        return {
            "total_executions": len(history),
            "successful": len(successful),
            "success_rate": len(successful) / len(history) if history else 0,
            "avg_execution_time": (
                sum(h.get("execution_time", 0) for h in history) / len(history)
                if history else 0
            ),
            "avg_quality": (
                sum(h.get("outcome_quality", 0) for h in history) / len(history)
                if history else 0
            )
        }

    def get_workflow_stats(self, workflow_name: str, step_number: int) -> Dict[str, Any]:
        """Get statistics for a workflow step."""
        history = self.store.retrieve("workflows", f"{workflow_name}_step_{step_number}")
        if not history:
            return {}

        successful = [h for h in history if h.get("success", False)]
        return {
            "total_executions": len(history),
            "successful": len(successful),
            "success_rate": len(successful) / len(history) if history else 0,
            "avg_duration": (
                sum(h.get("duration", 0) for h in history) / len(history)
                if history else 0
            ),
            "common_blockers": self._extract_blockers(history)
        }

    def query_error_pattern(self, error_type: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Query solutions for an error type."""
        history = self.store.retrieve("errors", error_type)
        if not history:
            return {}

        # Get solutions that worked
        solutions = [
            h for h in history
            if h.get("solution_worked", False)
        ]

        return {
            "previous_occurrences": len(history),
            "solutions_that_worked": len(solutions),
            "success_rate": len(solutions) / len(history) if history else 0,
            "top_solutions": solutions[-3:],  # Most recent successful solutions
            "prevention_tips": list(set(
                h.get("prevention_tip", "")
                for h in history
                if h.get("prevention_tip")
            ))
        }

    @staticmethod
    def _extract_blockers(history: List[Dict[str, Any]]) -> List[str]:
        """Extract common blockers from history."""
        blockers = {}
        for item in history:
            if not item.get("success", False):
                blocker = item.get("blocker", "Unknown")
                blockers[blocker] = blockers.get(blocker, 0) + 1

        # Return top 3 blockers
        return [
            blocker for blocker, count in
            sorted(blockers.items(), key=lambda x: x[1], reverse=True)[:3]
        ]
```

---

## Part 2: Integration Hooks

### 2.1 Pre-Execution Hook (Agent Invocation Enhancement)

**Location**: Agent orchestration layer (where agents are invoked)

```python
from .claude.memory.system.memory_store import MemoryStore
from .claude.memory.system.memory_retrieval import MemoryRetrieval

class AgentOrchestrator:
    """Enhanced orchestrator with memory support."""

    def __init__(self):
        self.memory_store = MemoryStore()
        self.memory_retrieval = MemoryRetrieval(self.memory_store)

    def invoke_agent(
        self,
        agent_name: str,
        task_prompt: str,
        task_category: str = "general",
        user_domain: str = "general"
    ) -> str:
        """
        Invoke agent with memory enhancement.

        MINIMAL CHANGE: Only 3 new lines for memory injection.
        """
        # Load agent definition (existing code)
        agent_def = self.load_agent_definition(agent_name)

        # NEW: Query memory for context (3 lines)
        memory_context = self.memory_retrieval.query_pre_execution(
            agent_name=agent_name,
            task_category=task_category,
            user_domain=user_domain
        )

        # NEW: Augment prompt with memory context
        augmented_prompt = f"""{memory_context}

## Task
{task_prompt}"""

        # Execute agent (existing code)
        response = self.send_to_claude(agent_def, augmented_prompt)

        # NEW: Record decision (existing code path enhanced)
        self.record_decision(agent_name, response, task_category)

        return response

    def record_decision(
        self,
        agent_name: str,
        response: str,
        task_category: str,
        quality_score: float = 0.0,
        execution_time: float = 0.0
    ) -> None:
        """
        Record decision to memory.

        MINIMAL CHANGE: Extract metadata and store.
        """
        # NEW: Extract decision metadata
        decision_data = {
            "agent": agent_name,
            "task_category": task_category,
            "decision": response[:500],  # First 500 chars as summary
            "outcome_quality": quality_score,
            "execution_time": execution_time,
            "success": quality_score > 0.5,  # Simple success metric
        }

        # NEW: Store to memory
        self.memory_store.store("agents", agent_name, decision_data)

    def load_agent_definition(self, agent_name: str) -> str:
        """Existing code - no changes."""
        # Implementation exists
        pass

    def send_to_claude(self, agent_def: str, prompt: str) -> str:
        """Existing code - no changes."""
        # Implementation exists
        pass
```

### 2.2 Post-Execution Hook (Decision Recording)

**Location**: Decision logging (after DECISIONS.md is written)

```python
from pathlib import Path
from .claude.memory.system.memory_store import MemoryStore

class DecisionRecorder:
    """Records decisions to memory after DECISIONS.md creation."""

    def __init__(self):
        self.memory_store = MemoryStore()

    def record_workflow_step(
        self,
        workflow_name: str,
        step_number: int,
        agents_used: List[str],
        success: bool,
        duration: float,
        blockers: Optional[List[str]] = None
    ) -> None:
        """
        Record workflow step execution to memory.

        Called after workflow step completes and DECISIONS.md updated.
        """
        step_key = f"{workflow_name}_step_{step_number}"

        step_data = {
            "workflow": workflow_name,
            "step": step_number,
            "agents": agents_used,
            "success": success,
            "duration": duration,
            "blockers": blockers or []
        }

        self.memory_store.store("workflows", step_key, step_data)

    def record_error_fix(
        self,
        error_type: str,
        error_message: str,
        solution: str,
        solution_worked: bool,
        prevention_tip: str = ""
    ) -> None:
        """
        Record error fix to memory.

        Called when an error is encountered and fixed.
        """
        error_data = {
            "error_type": error_type,
            "error_message": error_message,
            "solution": solution,
            "solution_worked": solution_worked,
            "prevention_tip": prevention_tip
        }

        self.memory_store.store("errors", error_type, error_data)
```

### 2.3 Workflow Orchestration Hook (UltraThink)

**Location**: Workflow execution loop

```python
class UltraThinkOrchestrator:
    """Enhanced UltraThink with memory-aware workflow execution."""

    def __init__(self):
        self.memory_retrieval = MemoryRetrieval(MemoryStore())

    def execute_workflow_step(
        self,
        workflow_name: str,
        step_number: int,
        agents_to_use: List[str]
    ) -> Dict[str, Any]:
        """
        Execute workflow step with memory-enhanced decision making.

        NEW: Query memory to potentially adapt agent usage.
        """
        # NEW: Query workflow history
        step_stats = self.memory_retrieval.get_workflow_stats(
            workflow_name=workflow_name,
            step_number=step_number
        )

        # NEW: Adapt execution based on history
        if step_stats.get("success_rate", 1.0) < 0.7:
            # Low success rate - add extra validation
            print(f"⚠️  Step {step_number} has {step_stats['success_rate']:.0%} success rate")
            print(f"⚠️  Common blockers: {', '.join(step_stats.get('common_blockers', []))}")

            # Optionally add extra agent
            if "security" not in agents_to_use:
                print("ℹ️  Adding security review for extra validation")
                agents_to_use = agents_to_use + ["security"]

        # Execute with agents (existing code)
        results = {}
        for agent in agents_to_use:
            results[agent] = self.execute_agent(agent, step_number)

        return results

    def execute_agent(self, agent_name: str, step_number: int) -> Dict[str, Any]:
        """Existing code - no changes."""
        # Implementation exists
        pass
```

### 2.4 Error Pattern Hook

**Location**: Error handler / fix-agent invocation

```python
class ErrorHandler:
    """Enhanced error handling with memory patterns."""

    def __init__(self):
        self.memory_retrieval = MemoryRetrieval(MemoryStore())
        self.memory_store = MemoryStore()

    def handle_error(self, error: Exception) -> Optional[str]:
        """
        Handle error with memory-enhanced solutions.

        NEW: Query error patterns before invoking fix-agent.
        """
        error_type = type(error).__name__
        error_message = str(error)

        # NEW: Query memory for similar errors
        error_record = self.memory_retrieval.query_error_pattern(
            error_type=error_type,
            context=error_message
        )

        if error_record and error_record.get("success_rate", 0) > 0.7:
            # We've fixed this before - use memory solutions
            print(f"✓ Found {error_record['previous_occurrences']} previous occurrences")
            print(f"✓ Success rate: {error_record['success_rate']:.0%}")

            top_solution = error_record.get("top_solutions", [{}])[0]
            print(f"✓ Recommended solution: {top_solution.get('solution', 'Unknown')}")

            if error_record.get("prevention_tips"):
                print(f"✓ Prevention tips:")
                for tip in error_record["prevention_tips"][:2]:
                    print(f"  - {tip}")

            # Provide memory context to fix-agent
            fix_context = self._format_error_memory(error_record)
            return fix_context

        # No memory - proceed with standard fix
        return None

    def _format_error_memory(self, error_record: Dict[str, Any]) -> str:
        """Format error record for fix-agent prompt injection."""
        lines = [
            "## Error Pattern Memory",
            f"- This error has occurred {error_record['previous_occurrences']} times",
            f"- Success rate: {error_record['success_rate']:.0%}",
            ""
        ]

        solutions = error_record.get("top_solutions", [])
        if solutions:
            lines.append("### Previous Solutions:")
            for i, sol in enumerate(solutions, 1):
                lines.append(f"{i}. {sol.get('solution', '')}")
            lines.append("")

        tips = error_record.get("prevention_tips", [])
        if tips:
            lines.append("### Prevention Tips:")
            for tip in tips:
                lines.append(f"- {tip}")

        return "\n".join(lines)
```

---

## Part 3: Memory System Usage Examples

### 3.1 Example: Architect Agent with Memory

```python
def example_architect_with_memory():
    """Example of architect agent receiving memory context."""

    orchestrator = AgentOrchestrator()

    # Memory system automatically provides context
    architect_response = orchestrator.invoke_agent(
        agent_name="architect",
        task_prompt="Design authentication system for microservices",
        task_category="system_design",
        user_domain="web_services"
    )

    # Memory context is injected before agent sees the prompt:
    # - Similar past auth system designs (3 examples)
    # - Domain-specific patterns for web services
    # - Common authentication errors from past (race conditions, etc.)
    # All of this is added to the prompt automatically

    return architect_response
```

### 3.2 Example: Error Fixing with Memory

```python
def example_error_with_memory():
    """Example of error handling with memory."""

    handler = ErrorHandler()

    try:
        # Some operation that fails
        import_module("non_existent_module")
    except ModuleNotFoundError as e:
        # Query memory for solutions
        fix_context = handler.handle_error(e)

        # Output might be:
        # ✓ Found 7 previous occurrences
        # ✓ Success rate: 100%
        # ✓ Recommended solution: Add to requirements.txt
        # ✓ Prevention tips:
        #   - Always check imports before running
        #   - Run in virtual environment

        if fix_context:
            print(fix_context)
```

### 3.3 Example: Workflow with Memory

```python
def example_workflow_with_memory():
    """Example of workflow execution with memory."""

    orchestrator = UltraThinkOrchestrator()

    # Execute workflow step with memory enhancement
    step_results = orchestrator.execute_workflow_step(
        workflow_name="DEFAULT_WORKFLOW",
        step_number=4,  # Architecture step
        agents_to_use=["architect"]
    )

    # Memory system checks:
    # - Step 4 success rate: 85% (good)
    # - No extra agents needed
    # vs.
    # - Step 4 success rate: 40% (poor)
    # - Common blockers: missing API specs
    # → Automatically add api-designer agent
```

---

## Part 4: Data Structures

### Agent Decision Record

```json
{
  "agent": "architect",
  "task_category": "system_design",
  "decision": "Use token-based authentication with JWT...",
  "reasoning": "Better scalability for distributed systems",
  "outcome_quality": 9.5,
  "execution_time": 180.5,
  "success": true,
  "timestamp": "2025-11-02T10:30:00Z"
}
```

### Workflow Step Record

```json
{
  "workflow": "DEFAULT_WORKFLOW",
  "step": 4,
  "agents": ["architect", "api-designer"],
  "success": true,
  "duration": 520,
  "blockers": [],
  "timestamp": "2025-11-02T10:30:00Z"
}
```

### Error Pattern Record

```json
{
  "error_type": "ModuleNotFoundError",
  "error_message": "No module named 'xyz'",
  "solution": "Add 'xyz' to requirements.txt",
  "solution_worked": true,
  "prevention_tip": "Always verify imports in virtual environment",
  "timestamp": "2025-11-02T10:30:00Z"
}
```

---

## Part 5: Testing the Integration

### Unit Test Example

```python
def test_memory_pre_execution():
    """Test that memory context is injected correctly."""
    retrieval = MemoryRetrieval(MemoryStore())
    store = retrieval.store

    # Store a past decision
    store.store("agents", "architect", {
        "decision": "Use token-based auth",
        "reasoning": "Scalable",
        "outcome_quality": 9.5,
        "task_category": "authentication",
        "success": True
    })

    # Query for context
    context = retrieval.query_pre_execution(
        agent_name="architect",
        task_category="authentication"
    )

    # Verify context is returned
    assert "Similar Past Tasks" in context
    assert "Use token-based auth" in context
    assert "9.5/10" in context

def test_memory_post_execution():
    """Test that decisions are stored correctly."""
    store = MemoryStore()

    # Record a decision
    store.store("agents", "architect", {
        "decision": "Test decision",
        "outcome_quality": 8.0,
        "success": True
    })

    # Retrieve decision
    decisions = store.retrieve("agents", "architect")
    assert decisions is not None
    assert len(decisions) == 1
    assert decisions[0]["decision"] == "Test decision"

def test_error_pattern_query():
    """Test error pattern retrieval."""
    retrieval = MemoryRetrieval(MemoryStore())
    store = retrieval.store

    # Store error records
    store.store("errors", "ModuleNotFoundError", {
        "error_type": "ModuleNotFoundError",
        "solution": "Add to requirements.txt",
        "solution_worked": True
    })

    # Query error pattern
    pattern = retrieval.query_error_pattern("ModuleNotFoundError")

    assert pattern["previous_occurrences"] >= 1
    assert pattern["success_rate"] > 0
```

---

## Summary: What These Examples Show

1. **MemoryStore**: Simple JSON-based persistence
2. **MemoryRetrieval**: Query interface for agents
3. **Integration Hooks**: Where to add 3-5 lines of code
4. **Minimal Changes**: No modifications to agent definitions
5. **Real Usage**: Concrete examples of memory enhancing agents
6. **Data Structures**: What gets stored and how

**Key Insight**: Total implementation is ~500 lines of code (including comments), integrated with only 5-10 line changes in existing code.
