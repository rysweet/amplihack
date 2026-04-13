from __future__ import annotations

"""GoalSeekingAgent — OODA loop interface over the LearningAgent internals.

Philosophy:
- Single agent type with a universal OODA loop (Observe-Orient-Decide-Act).
- Content and questions are both just *input*. The agent classifies and handles
  them internally. The caller never calls learn_from_content() or
  answer_question() directly.
- Output (answers) goes to stdout/log. In distributed mode Container Apps
  streams this to Log Analytics. The eval reads from there — no Service Bus
  round-trip for answers.
- LearningAgent is an implementation detail; GoalSeekingAgent is the public API.

Public API:
    observe(input_data)  → store raw input, start OODA cycle
    orient()             → recall relevant facts from memory → dict
    decide()             → classify as "store" | "answer"
    act()                → execute decision, write output to stdout → str
    process(input_data)  → observe → orient → decide → act pipeline → str
    process_store(input_data) → observe → force-store → act pipeline → str
    learn_from_content(input_data) → benchmark/eval compatibility delegate
    answer_question(question) → benchmark/eval compatibility delegate

Backward compatibility:
    LearningAgent is NOT removed; existing callers continue to work unchanged.
"""

import asyncio
import inspect
import logging
import threading
from pathlib import Path
from typing import Any

from .retrieval_constants import ORIENT_SEARCH_LIMIT

logger = logging.getLogger(__name__)


def _run_awaitable_in_background_thread(awaitable: Any) -> Any:
    """Execute an awaitable to completion on a dedicated event loop thread.

    GoalSeekingAgent exposes a synchronous API, but some backends now return
    coroutines. When callers invoke that sync API from inside an already-running
    event loop, ``asyncio.run()`` is not legal, so we bridge through a short-
    lived thread with its own loop and surface the original result/exception.
    """

    state: dict[str, Any] = {}

    def _runner() -> None:
        try:
            state["result"] = asyncio.run(awaitable)
        except BaseException as exc:  # preserve original failure for the caller
            state["exception"] = exc

    thread = threading.Thread(
        target=_runner,
        name="goal-seeking-awaitable-runner",
        daemon=True,
    )
    thread.start()
    thread.join()

    if "exception" in state:
        raise state["exception"]
    return state.get("result")


def _run_maybe_async(value: Any) -> Any:
    """Run coroutine-like values, otherwise return them unchanged."""
    if inspect.isawaitable(value):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(value)
        return _run_awaitable_in_background_thread(value)
    return value


def _log_background_task_failure(agent_name: str, task: asyncio.Task[Any]) -> None:
    """Log exceptions from fire-and-forget async callbacks."""
    try:
        task.result()
    except Exception:
        logger.exception("Agent %s on_answer callback failed", agent_name)

# Minimal sentinel so orient/decide/act can be called without prior observe()
_NO_INPUT = object()
_QUESTION_PREFIXES = (
    "what ",
    "who ",
    "when ",
    "where ",
    "why ",
    "how ",
    "which ",
    "is ",
    "are ",
    "was ",
    "were ",
    "do ",
    "does ",
    "did ",
    "can ",
    "could ",
    "should ",
    "would ",
    "will ",
    "has ",
    "have ",
    "had ",
)


def _looks_like_question(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    lower = stripped.lower()
    return stripped.endswith("?") or any(lower.startswith(prefix) for prefix in _QUESTION_PREFIXES)


class GoalSeekingAgent:
    """Goal-seeking agent with a pure OODA loop.

    All input — whether content to memorise or a question to answer — is fed
    via ``observe()``.  The agent classifies the input during ``decide()`` and
    produces output (answers written to stdout) during ``act()``.

    Internally this wraps :class:`~amplihack.agents.goal_seeking.LearningAgent`
    so all existing memory / Kuzu / CognitiveAdapter infrastructure is reused
    without modification.

    Args:
        agent_name: Unique identifier for this agent.
        model: LLM model string.  Defaults to ``EVAL_MODEL``
            env var or ``claude-opus-4-6``.
        storage_path: Override storage directory for memory.
        use_hierarchical: Pass through to LearningAgent backend selection.
        prompt_variant: Variant number (1-5) for A/B prompt testing.
    """

    def __init__(
        self,
        agent_name: str = "goal_seeking_agent",
        model: str | None = None,
        storage_path: Path | None = None,
        use_hierarchical: bool = False,
        memory_type: str = "auto",
        prompt_variant: int | None = None,
        **kwargs: Any,
    ) -> None:
        # Import here to avoid circular imports and keep module-level import clean
        from .learning_agent import LearningAgent

        self._agent_name = agent_name
        self._learning_agent = LearningAgent(
            agent_name=agent_name,
            model=model,
            storage_path=storage_path,
            use_hierarchical=use_hierarchical,
            prompt_variant=prompt_variant,
        )
        self._memory_type = memory_type
        self._configure_memory_backend(storage_path)

        # OODA state — reset per process() call
        self._current_input: str = ""
        self._oriented_facts: dict[str, Any] = {}
        self._decision: str = ""  # "store" | "answer"

        # Optional callback fired after act() produces an answer.
        # Set via DI by the entrypoint for distributed eval answer collection.
        # Signature: on_answer(agent_name: str, answer: str) -> None
        self.on_answer: Any | None = None

    def _configure_memory_backend(self, storage_path: Path | None) -> None:
        """Override LearningAgent memory backend when explicitly requested."""
        if self._memory_type == "auto":
            return

        db_path = storage_path

        if self._memory_type == "hierarchical":
            from .flat_retriever_adapter import FlatRetrieverAdapter

            self._close_existing_memory_backend("hierarchical")
            self._learning_agent.memory = FlatRetrieverAdapter(
                agent_name=self._agent_name,
                db_path=db_path,
            )
            self._learning_agent.use_hierarchical = True
            return

        if self._memory_type == "cognitive":
            from .cognitive_adapter import CognitiveAdapter

            self._close_existing_memory_backend("cognitive")
            self._learning_agent.memory = CognitiveAdapter(
                agent_name=self._agent_name,
                db_path=db_path,
            )
            self._learning_agent.use_hierarchical = True

    def _close_existing_memory_backend(self, target_memory_type: str) -> None:
        """Close the current memory backend before swapping implementations."""
        memory = self._learning_agent.memory
        if not hasattr(memory, "close"):
            return

        try:
            memory.close()
        except Exception:
            logger.exception(
                "Agent %s failed to close existing memory backend before switching to %s",
                self._agent_name,
                target_memory_type,
            )
            raise

    def _emit_answer_callback(self, answer: str) -> None:
        """Invoke the optional answer callback without dropping async handlers."""
        if not self.on_answer:
            return

        try:
            callback_result = self.on_answer(self._agent_name, answer)
        except Exception:
            logger.exception("Agent %s on_answer callback failed", self._agent_name)
            return

        if not inspect.isawaitable(callback_result):
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                _run_maybe_async(callback_result)
            except Exception:
                logger.exception("Agent %s async on_answer callback failed", self._agent_name)
            return

        task = loop.create_task(callback_result)
        task.add_done_callback(
            lambda done_task, agent_name=self._agent_name: _log_background_task_failure(
                agent_name,
                done_task,
            )
        )

    # ------------------------------------------------------------------
    # OODA loop — public API
    # ------------------------------------------------------------------

    def observe(self, input_data: str) -> None:
        """Observe raw input from the environment.

        All input types — article text, event payloads, user questions — are
        passed here.  No classification happens yet.

        Args:
            input_data: Raw string input (content, question, or event text).
        """
        self._current_input = input_data or ""
        self._oriented_facts = {}
        self._decision = ""
        logger.debug(
            "Agent %s observed input (%d chars)", self._agent_name, len(self._current_input)
        )

    def orient(self) -> dict[str, Any]:
        """Contextualise the observed input using memory recall.

        Calls Memory.recall / memory search to surface relevant existing
        knowledge.  Returns a dict with ``facts`` (list of recalled fact
        strings) and ``input`` (the raw observed input).

        Returns:
            dict with keys:
                ``input``  — raw observed input string
                ``facts``  — list of recalled fact strings (may be empty)
        """
        if not self._current_input:
            self._oriented_facts = {"input": "", "facts": []}
            return self._oriented_facts

        # Questions will run the full answer_question() retrieval path during ACT.
        # Recalling memory here would duplicate a full distributed search for every
        # question without feeding that context into the actual answer synthesis.
        if _looks_like_question(self._current_input):
            self._oriented_facts = {"input": self._current_input, "facts": []}
            try:
                from amplihack.agents.goal_seeking.hive_mind.tracing import trace_log

                trace_log("orient", "skipping duplicate memory recall for question input")
            except ImportError:
                pass
            return self._oriented_facts

        # Use LearningAgent's internal memory to recall relevant context
        facts: list[str] = []
        try:
            from amplihack.agents.goal_seeking.hive_mind.tracing import trace_log

            trace_log("orient", "searching memory for: %.120s", self._current_input[:200])
        except ImportError:
            pass
        try:
            memory = self._learning_agent.memory
            if hasattr(memory, "search"):
                raw = memory.search(self._current_input[:200], limit=ORIENT_SEARCH_LIMIT)
                facts = [
                    r.get("outcome", r.get("fact", str(r))) if isinstance(r, dict) else str(r)
                    for r in (raw or [])
                ]
            elif hasattr(memory, "search_facts"):
                raw = memory.search_facts(self._current_input[:200], limit=ORIENT_SEARCH_LIMIT)
                facts = [
                    r.get("outcome", r.get("fact", str(r))) if isinstance(r, dict) else str(r)
                    for r in (raw or [])
                ]
        except Exception:
            logger.debug("orient() memory recall failed", exc_info=True)

        self._oriented_facts = {"input": self._current_input, "facts": facts}
        logger.debug("Agent %s oriented: %d recalled facts", self._agent_name, len(facts))
        try:
            from amplihack.agents.goal_seeking.hive_mind.tracing import trace_log

            trace_log("orient", "recalled %d facts", len(facts))
            if facts:
                trace_log("orient", "top fact: %.120s", facts[0])
        except ImportError:
            pass
        return self._oriented_facts

    def decide(self) -> str:
        """Classify the input as ``'store'`` (learn) or ``'answer'`` (respond).

        Uses simple heuristics first (question marks, interrogative words) and
        falls back to the LearningAgent's intent-detection LLM call for
        ambiguous cases.

        Returns:
            ``'answer'`` if the input looks like a question, ``'store'`` otherwise.
        """
        text = self._current_input.strip()
        if not text:
            self._decision = "store"
            return self._decision

        # Fast path: interrogative signals → answer
        is_question = _looks_like_question(text)

        if is_question:
            self._decision = "answer"
        else:
            # Not a question → store. No LLM call needed for classification.
            # The intent detector is designed for questions, not content.
            self._decision = "store"

        logger.debug("Agent %s decided: %s", self._agent_name, self._decision)
        return self._decision

    def act(self) -> str:
        """Execute the decision and produce output.

        * ``'store'`` → calls LearningAgent.learn_from_content() (memory impl detail).
        * ``'answer'`` → calls LearningAgent.answer_question(), writes answer to
          stdout so Container Apps streams it to Log Analytics.

        Returns:
            Output string: answer text for ``'answer'``, summary for ``'store'``.

        Raises:
            Exception: Propagates underlying learning/answer failures after logging
                so direct callers and user-like flows do not mistake them for
                successful outputs.
        """
        text = self._current_input
        output = ""

        if self._decision == "answer":
            try:
                from amplihack.agents.goal_seeking.hive_mind.tracing import trace_log

                trace_log(
                    "act",
                    "ANSWERING with %d context facts: %.120s",
                    len(self._oriented_facts.get("facts", [])),
                    self._current_input[:120],
                )
            except ImportError:
                pass
            try:
                result = self._learning_agent.answer_question(text)
                output = result[0] if isinstance(result, tuple) else str(result)
            except Exception:
                logger.exception("Agent %s act() answer_question failed", self._agent_name)
                raise
            # Write answer to stdout — Container Apps streams this to Log Analytics
            print(f"[{self._agent_name}] ANSWER: {output}", flush=True)
            logger.info("Agent %s ANSWER: %s", self._agent_name, output)
            # Fire callback for distributed eval answer collection
            self._emit_answer_callback(output)

        else:  # "store" (or empty / unknown)
            try:
                result_dict = _run_maybe_async(self._learning_agent.learn_from_content(text))
                stored = result_dict.get("facts_stored", 0)
                output = f"Stored {stored} facts from input."
            except Exception:
                logger.exception("Agent %s act() learn_from_content failed", self._agent_name)
                raise
            logger.debug("Agent %s STORED: %s", self._agent_name, output)

        return output

    # ------------------------------------------------------------------
    # Convenience pipeline
    # ------------------------------------------------------------------

    def process(self, input_data: str) -> str:
        """Run the full OODA pipeline for a single input.

        Order: observe → orient → decide → act.

        The full OODA loop is preserved so that orient() enriches the
        agent's context with memory recall before decide() classifies
        the input.  This is the same loop in both single-agent and
        distributed topologies — the memory backend handles fan-out
        transparently.

        Args:
            input_data: Raw input string.

        Returns:
            Output produced by ``act()``.
        """
        self.observe(input_data)
        self.orient()
        self.decide()
        return self.act()

    def process_store(self, input_data: str) -> str:
        """Store input explicitly without question classification or orient recall.

        This is used when the transport already knows the payload is learning
        content (for example ``LEARN_CONTENT`` events in the Azure hive). That
        avoids misrouting question-shaped content into ``answer_question()`` and
        avoids orient-time distributed recall that ``act()`` does not consume on
        the store path.
        """
        self.observe(input_data)
        self._oriented_facts = {"input": self._current_input, "facts": []}
        self._decision = "store"
        return self.act()

    def learn_from_content(self, input_data: str) -> dict[str, Any]:
        """Compatibility delegate for benchmark/eval surfaces."""
        return _run_maybe_async(self._learning_agent.learn_from_content(input_data))

    def answer_question(self, question: str, answer_mode: str = "single-shot") -> str:
        """Compatibility delegate for benchmark/eval surfaces."""
        if answer_mode == "agentic":
            return self._learning_agent.answer_question_agentic(question)

        result = self._learning_agent.answer_question(question)
        if isinstance(result, tuple):
            return result[0]
        return result

    def prepare_fact_batch(self, input_data: str, include_summary: bool = True) -> dict[str, Any]:
        """Prepare a reusable fact batch from raw content."""
        return _run_maybe_async(
            self._learning_agent.prepare_fact_batch(
                input_data,
                include_summary=include_summary,
            )
        )

    def store_fact_batch(self, batch: dict[str, Any]) -> dict[str, Any]:
        """Store a prepared fact batch without re-running extraction."""
        return self._learning_agent.store_fact_batch(batch, record_learning=False)

    # ------------------------------------------------------------------
    # Event-driven OODA loop
    # ------------------------------------------------------------------

    def run_ooda_loop(self, input_source: object) -> None:
        """Run the OODA loop driven by an InputSource — no polling, no sleeping.

        Calls ``input_source.next()`` in a tight loop.  Each returned string
        is processed via ``self.process()``.  The loop exits when
        ``input_source.next()`` returns ``None`` (end-of-input).

        The special sentinel ``"__FEED_COMPLETE__:<n>"`` emitted by
        :class:`~amplihack.agents.goal_seeking.input_source.ServiceBusInputSource`
        for FEED_COMPLETE events is handled here: the agent logs the event and
        continues running (waiting for eval queries that follow the feed).

        Args:
            input_source: Any object implementing ``InputSource`` (next/close).

        Example::

            from amplihack.agents.goal_seeking.input_source import ListInputSource

            agent = GoalSeekingAgent("eval-agent")
            src = ListInputSource(["Article text…", "What did the article say?"])
            agent.run_ooda_loop(src)
        """
        turn = 0
        logger.info("Agent %s entering event-driven OODA loop", self._agent_name)
        while True:
            try:
                text = input_source.next()
            except Exception:
                logger.warning(
                    "Agent %s: input_source.next() raised, stopping loop",
                    self._agent_name,
                    exc_info=True,
                )
                break

            if text is None:
                logger.info(
                    "Agent %s: input_source exhausted after %d turns",
                    self._agent_name,
                    turn,
                )
                break

            # Handle FEED_COMPLETE sentinel from ServiceBusInputSource
            if isinstance(text, str) and text.startswith("__FEED_COMPLETE__:"):
                total = text.split(":", 1)[1]
                logger.info(
                    "Agent %s received FEED_COMPLETE (total_turns=%s). "
                    "Staying alive for eval queries.",
                    self._agent_name,
                    total,
                )
                continue

            turn += 1
            logger.debug("Agent %s OODA turn %d (len=%d)", self._agent_name, turn, len(text))
            try:
                self.process(text)
            except Exception:
                logger.exception("Agent %s: process() failed on turn %d", self._agent_name, turn)

        logger.info("Agent %s OODA loop finished after %d turns", self._agent_name, turn)

    # ------------------------------------------------------------------
    # Delegation helpers (backward-compat surface for entrypoint)
    # ------------------------------------------------------------------

    @property
    def memory(self) -> Any:
        """Expose underlying memory adapter (read-only, for wiring transports)."""
        return self._learning_agent.memory

    def get_memory_stats(self) -> dict[str, Any]:
        """Delegate to LearningAgent.get_memory_stats() if available."""
        if hasattr(self._learning_agent, "get_memory_stats"):
            return self._learning_agent.get_memory_stats()
        return {}

    def flush_memory(self) -> None:
        """Delegate flush_memory when the underlying learning agent supports it."""
        if hasattr(self._learning_agent, "flush_memory"):
            self._learning_agent.flush_memory()

    def close(self) -> None:
        """Delegate close to LearningAgent."""
        if hasattr(self._learning_agent, "close"):
            self._learning_agent.close()
