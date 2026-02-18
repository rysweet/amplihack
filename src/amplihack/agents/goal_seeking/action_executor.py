from __future__ import annotations

"""Action executor with tool registry for goal-seeking agents.

Philosophy:
- Single responsibility: Execute actions/tools
- Registry pattern for extensibility
- Clear error handling
- Synchronous execution (simpler than async)
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class ActionResult:
    """Result of an action execution.

    Attributes:
        success: Whether action succeeded
        output: Output data from the action
        error: Error message if failed
        action_name: Name of the action executed
    """

    success: bool
    output: Any
    error: str | None = None
    action_name: str = ""


class ActionExecutor:
    """Tool registry and executor for goal-seeking agents.

    Provides a registry of available actions (tools) that agents can invoke.
    Each action is a callable that takes parameters and returns a result.

    Philosophy:
    - Simple function-based actions (no complex classes)
    - Clear success/failure reporting
    - Extensible via register_action()

    Example:
        >>> executor = ActionExecutor()
        >>> executor.register_action("greet", lambda name: f"Hello {name}!")
        >>> result = executor.execute("greet", name="Alice")
        >>> print(result.output)  # "Hello Alice!"
    """

    def __init__(self):
        """Initialize action executor with empty registry."""
        self._actions: dict[str, Callable] = {}

    def register_action(self, name: str, func: Callable) -> None:
        """Register an action (tool) with the executor.

        Args:
            name: Action name (must be unique)
            func: Callable that implements the action

        Raises:
            ValueError: If name is empty or already registered

        Example:
            >>> executor = ActionExecutor()
            >>> def add(a: int, b: int) -> int:
            ...     return a + b
            >>> executor.register_action("add", add)
        """
        if not name or not name.strip():
            raise ValueError("Action name cannot be empty")
        if name in self._actions:
            raise ValueError(f"Action '{name}' is already registered")
        if not callable(func):
            raise ValueError(f"Action '{name}' must be callable")

        self._actions[name] = func

    def execute(self, action_name: str, **kwargs) -> ActionResult:
        """Execute a registered action with given parameters.

        Args:
            action_name: Name of action to execute
            **kwargs: Parameters to pass to the action

        Returns:
            ActionResult with success status and output

        Example:
            >>> executor = ActionExecutor()
            >>> executor.register_action("add", lambda a, b: a + b)
            >>> result = executor.execute("add", a=5, b=3)
            >>> print(result.output)  # 8
            >>> print(result.success)  # True
        """
        if action_name not in self._actions:
            return ActionResult(
                success=False,
                output=None,
                error=f"Action '{action_name}' not found. Available: {list(self._actions.keys())}",
                action_name=action_name,
            )

        try:
            action = self._actions[action_name]
            output = action(**kwargs)
            return ActionResult(success=True, output=output, action_name=action_name)
        except Exception as e:
            return ActionResult(
                success=False,
                output=None,
                error=f"Action '{action_name}' failed: {e!s}",
                action_name=action_name,
            )

    def get_available_actions(self) -> list[str]:
        """Get list of registered action names.

        Returns:
            List of available action names
        """
        return list(self._actions.keys())

    def has_action(self, action_name: str) -> bool:
        """Check if action is registered.

        Args:
            action_name: Name of action to check

        Returns:
            True if action exists, False otherwise
        """
        return action_name in self._actions


# Standard actions for goal-seeking agents


def read_content(content: str) -> dict[str, Any]:
    """Read and parse content for learning.

    Args:
        content: Text content to read

    Returns:
        Dictionary with parsed content metadata
    """
    if not content or not content.strip():
        return {"word_count": 0, "char_count": 0, "content": ""}

    content = content.strip()
    words = content.split()

    return {
        "word_count": len(words),
        "char_count": len(content),
        "content": content,
        "preview": content[:200] if len(content) > 200 else content,
    }


def search_memory(memory_retriever, query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search memory for relevant experiences.

    Args:
        memory_retriever: MemoryRetriever instance
        query: Search query
        limit: Maximum results

    Returns:
        List of matching experiences
    """
    if not query or not query.strip():
        return []

    return memory_retriever.search(query.strip(), limit=limit)


def calculate(expression: str) -> dict[str, Any]:
    """Evaluate a simple arithmetic expression safely.

    Supports +, -, *, /, parentheses, and integer/float operands.
    No variable names or function calls allowed.

    Args:
        expression: Arithmetic expression string (e.g., "26 - 18")

    Returns:
        Dictionary with result or error:
            - expression: The input expression
            - result: The numeric result (if successful)
            - error: Error message (if failed)

    Example:
        >>> calculate("26 - 18")
        {'expression': '26 - 18', 'result': 8.0, 'error': None}
    """
    if not expression or not expression.strip():
        return {"expression": expression, "result": None, "error": "Empty expression"}

    expr = expression.strip()

    # Allow only digits, operators, parentheses, whitespace, and decimal points
    import re

    if not re.match(r"^[\d\s\+\-\*/\(\)\.]+$", expr):
        return {
            "expression": expr,
            "result": None,
            "error": f"Invalid characters in expression: {expr}",
        }

    try:
        # Use compile + eval with empty globals for safety
        code = compile(expr, "<calc>", "eval")
        # Verify no names are used (only constants and operators)
        if code.co_names:
            return {
                "expression": expr,
                "result": None,
                "error": "No variables or functions allowed",
            }
        result = eval(code, {"__builtins__": {}}, {})
        return {"expression": expr, "result": float(result), "error": None}
    except Exception as e:
        return {"expression": expr, "result": None, "error": str(e)}


def synthesize_answer(
    llm_synthesizer, question: str, context: list[dict[str, Any]], question_level: str = "L1"
) -> str:
    """Synthesize answer using LLM from retrieved context.

    Args:
        llm_synthesizer: LLM synthesizer function (uses litellm)
        question: Question to answer
        context: Retrieved context from memory
        question_level: Question complexity (L1-L4)

    Returns:
        Synthesized answer string
    """
    if not question or not question.strip():
        return "Error: Question is empty"

    if not context:
        return "No relevant information found in memory."

    return llm_synthesizer(question=question, context=context, question_level=question_level)
