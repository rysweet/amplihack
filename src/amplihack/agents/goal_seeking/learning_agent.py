from __future__ import annotations

"""Generic learning agent with LLM-powered answer synthesis.

Philosophy:
- Single responsibility: Learn from content sources and answer questions
- Uses agentic loop for structured learning
- LLM synthesizes answers (not just retrieval)
- Handles question complexity levels (L1-L4)
- Supports hierarchical memory with Graph RAG (use_hierarchical=True)
- Not Wikipedia-specific - works with any content sources
- Intent detection classifies questions before synthesis (L3+ improvements)
- Temporal metadata tracked on episodic memories for chronological reasoning
"""

import asyncio
import logging
import os
import threading
from pathlib import Path
from typing import Any

from amplihack.llm import completion as _llm_completion

from .action_executor import ActionExecutor, calculate, read_content, search_memory
from .agentic_loop import AgenticLoop
from .cognitive_adapter import HAS_COGNITIVE_MEMORY, CognitiveAdapter
from .flat_retriever_adapter import FlatRetrieverAdapter
from .memory_retrieval import MemoryRetriever
from .prompts import render_prompt

logger = logging.getLogger(__name__)

# Backward-compatible alias retained because older tests and patch sites
# target amplihack.agents.goal_seeking.learning_agent.completion directly.
_ORIGINAL_LLM_COMPLETION = _llm_completion
completion = _llm_completion


def _get_completion_binding():
    """Return the currently active completion callable.

    Some tests patch ``learning_agent._llm_completion`` while others patch
    ``learning_agent.completion``. Prefer whichever binding diverged from the
    original import so both patch targets continue to work.
    """
    current_primary = _llm_completion
    current_alias = completion
    primary_patched = current_primary is not _ORIGINAL_LLM_COMPLETION
    alias_patched = current_alias is not _ORIGINAL_LLM_COMPLETION

    if alias_patched and not primary_patched:
        return current_alias
    if primary_patched and not alias_patched:
        return current_primary
    if alias_patched:
        return current_alias
    return current_primary


from .answer_synthesizer import AnswerSynthesizerMixin
from .code_synthesis import CodeSynthesisMixin
from .intent_detector import IntentDetectorMixin
from .knowledge_utils import KnowledgeUtilsMixin
from .learning_ingestion import LearningIngestionMixin
from .retrieval_strategies import RetrievalStrategiesMixin
from .temporal_reasoning import TemporalReasoningMixin


def _load_prompt(name: str, **kwargs: str) -> str:
    """Load a prompt template from prompts/{name}.md and substitute placeholders.

    Uses {{variable}} double-brace syntax so that literal JSON braces in
    the prompt templates are preserved.

    Args:
        name: Prompt file name without .md extension
        **kwargs: Values to substitute for {{variable}} placeholders

    Returns:
        Rendered prompt string
    """
    return render_prompt(name, **kwargs)


class LearningAgent(
    IntentDetectorMixin,
    TemporalReasoningMixin,
    CodeSynthesisMixin,
    KnowledgeUtilsMixin,
    RetrievalStrategiesMixin,
    LearningIngestionMixin,
    AnswerSynthesizerMixin,
):
    """Generic agent that learns from content and answers questions.

    Uses the PERCEIVE->REASON->ACT->LEARN loop to:
    1. Read content from various sources
    2. Extract and store facts
    3. Answer questions using LLM synthesis of stored knowledge

    Question Complexity Levels:
    - L1 (Recall): Direct fact retrieval
    - L2 (Inference): Connect multiple facts
    - L3 (Synthesis): Create new understanding
    - L4 (Application): Apply knowledge to new situations

    When use_hierarchical=True, uses HierarchicalMemory with Graph RAG
    for richer knowledge retrieval via similarity edges and subgraph traversal.

    Example:
        >>> agent = LearningAgent("my_agent")
        >>> agent.learn_from_content(
        ...     "Photosynthesis is the process by which plants convert light to energy."
        ... )
        >>> answer = agent.answer_question(
        ...     "What is photosynthesis?",
        ...     question_level="L1"
        ... )
        >>> print(answer)  # LLM-synthesized answer from stored facts
    """

    _TRANSIENT_LLM_ERROR_TYPES = (
        ConnectionError,
        TimeoutError,
        OSError,
    )
    _TRANSIENT_LLM_ERROR_MARKERS = (
        "rate_limit",
        "overloaded",
        "overloaded_error",
        "service unavailable",
        "temporarily unavailable",
        "connection error",
    )

    def __init__(
        self,
        agent_name: str = "learning_agent",
        model: str | None = None,
        storage_path: Path | None = None,
        use_hierarchical: bool = False,
        prompt_variant: int | None = None,
        **kwargs: Any,
    ):
        """Initialize learning agent.

        Args:
            agent_name: Name for the agent
            model: LLM model to use
            storage_path: Custom storage path for memory
            use_hierarchical: If True, use HierarchicalMemory via FlatRetrieverAdapter.
                If False, use original MemoryRetriever (backward compatible).
            prompt_variant: Optional prompt variant number (1-5). When set, loads
                the system prompt from prompts/variants/variant_{N}_{style}.md
                instead of the default synthesis_system.md. Used to test different
                prompting strategies in eval experiments.

        Note:
            The memory backend is topology-unaware.  For distributed operation,
            the caller wraps the memory backend with DistributedCognitiveMemory
            (see agent_entrypoint.py).
        """
        self.agent_name = agent_name
        self.model = model or os.environ.get("EVAL_MODEL", "claude-opus-4-6")
        self.use_hierarchical = use_hierarchical
        self.prompt_variant = prompt_variant
        self._variant_system_prompt: str | None = None
        if prompt_variant is not None:
            self._variant_system_prompt = self._load_variant_prompt(prompt_variant)

        # Initialize memory based on mode
        # Prefer CognitiveMemory (6-type) if available, fall back to HierarchicalMemory
        if use_hierarchical:
            if HAS_COGNITIVE_MEMORY:
                self.memory = CognitiveAdapter(
                    agent_name=agent_name,
                    db_path=storage_path,
                )
            else:
                self.memory = FlatRetrieverAdapter(
                    agent_name=agent_name,
                    db_path=storage_path,
                )
        else:
            self.memory = MemoryRetriever(
                agent_name=agent_name, storage_path=storage_path, backend="kuzu"
            )

        # Initialize action executor
        self.executor = ActionExecutor()

        # Register actions
        self.executor.register_action("read_content", read_content)
        self.executor.register_action(
            "search_memory", lambda query, limit=5: search_memory(self.memory, query, limit)
        )
        self.executor.register_action(
            "synthesize_answer",
            lambda question, context, question_level="L1": self._synthesize_with_llm(
                question, context, question_level
            ),
        )
        self.executor.register_action("calculate", calculate)
        self.executor.register_action(
            "code_generation",
            lambda question: self._code_generation_tool(question),
        )

        # Tier 2+: Learning, memory management, teaching, and application tools
        self.executor.register_action(
            "explain_knowledge",
            lambda topic, depth="overview": self._explain_knowledge(topic, depth),
        )
        self.executor.register_action(
            "find_knowledge_gaps",
            lambda topic: self._find_knowledge_gaps(topic),
        )
        self.executor.register_action(
            "verify_fact",
            lambda fact: self._verify_fact(fact),
        )

        # Initialize agentic loop -- pass self.model (resolved from env/default)
        # not the raw `model` parameter which may be None.
        self.loop = AgenticLoop(
            agent_name=agent_name,
            action_executor=self.executor,
            memory_retriever=self.memory,
            model=self.model,
        )

        # Solution A: Thread-local storage for _cached_all_facts to prevent
        # data races when multiple threads share one LearningAgent instance
        # (e.g. --parallel-workers 10 in the eval harness).
        self._thread_local = threading.local()

        # Solution D: Pre-snapshot holder - set by eval harness before parallel
        # evaluation so all threads use the same consistent fact snapshot.
        self._pre_snapshot_facts: list[dict[str, Any]] | None = None

    async def _llm_completion_with_retry(
        self, messages: list[dict[str, Any]], temperature: float = 0.0, max_retries: int = 5
    ) -> str:
        """Call amplihack.llm.completion with exponential backoff on transient failures.

        Returns the response text content. Raises on non-rate-limit errors.
        """
        last_exception: Exception | None = None
        for _retry_attempt in range(max_retries + 1):  # attempt 0 = first try
            try:
                return await _get_completion_binding()(
                    messages,
                    model=self.model,
                    temperature=temperature,
                )
            except Exception as exc:
                is_transient = self._is_transient_llm_error(exc)
                if not is_transient or _retry_attempt >= max_retries:
                    raise
                delay = 2**_retry_attempt * 2  # 2, 4, 8, 16, 32
                logger.warning(
                    "Transient LLM error (%s), retrying in %ds (attempt %d/%d)",
                    type(exc).__name__,
                    delay,
                    _retry_attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(delay)
                last_exception = exc
        raise last_exception  # type: ignore[misc]

    @classmethod
    def _is_transient_llm_error(cls, exc: Exception) -> bool:
        if isinstance(exc, cls._TRANSIENT_LLM_ERROR_TYPES):
            return True
        error_text = str(exc).lower()
        return any(marker in error_text for marker in cls._TRANSIENT_LLM_ERROR_MARKERS)

    @staticmethod
    def _load_variant_prompt(variant_num: int) -> str:
        """Load a prompt variant from the variants directory.

        Args:
            variant_num: Variant number (1-5)

        Returns:
            The variant system prompt text

        Raises:
            FileNotFoundError: If variant file doesn't exist
        """
        variant_names = {
            1: "variant_1_minimal",
            2: "variant_2_basic",
            3: "variant_3_structured",
            4: "variant_4_detailed",
            5: "variant_5_expert",
        }
        name = variant_names.get(variant_num)
        if name is None:
            raise ValueError(f"Invalid prompt variant: {variant_num}. Must be 1-5.")
        variant_path = Path(__file__).parent / "prompts" / "variants" / f"{name}.md"
        if not variant_path.exists():
            raise FileNotFoundError(f"Prompt variant not found: {variant_path}")
        text = variant_path.read_text()
        # Strip markdown header
        lines = text.split("\n")
        content_lines = []
        past_header = False
        for line in lines:
            if not past_header and line.startswith("#"):
                continue
            if not past_header and line.strip() == "":
                continue
            past_header = True
            content_lines.append(line)
        return "\n".join(content_lines).strip()

    def flush_memory(self) -> None:
        """Flush memory cache without losing data or agent state."""
        if hasattr(self.memory, "flush_memory"):
            self.memory.flush_memory()

    def close(self) -> None:
        """Close agent and release resources."""
        self.memory.close()
