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

Backward compatibility:
    LearningAgent is NOT removed; existing callers continue to work unchanged.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Minimal sentinel so orient/decide/act can be called without prior observe()
_NO_INPUT = object()


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
        model: LLM model string (litellm format).  Defaults to ``EVAL_MODEL``
            env var or ``claude-opus-4-6``.
        storage_path: Override storage directory for memory.
        use_hierarchical: Pass through to LearningAgent backend selection.
        hive_store: Shared hive graph store for distributed memory.
        prompt_variant: Variant number (1-5) for A/B prompt testing.
    """

    def __init__(
        self,
        agent_name: str = "goal_seeking_agent",
        model: str | None = None,
        storage_path: Path | None = None,
        use_hierarchical: bool = False,
        hive_store: object | None = None,
        prompt_variant: int | None = None,
    ) -> None:
        # Import here to avoid circular imports and keep module-level import clean
        from .learning_agent import LearningAgent

        self._agent_name = agent_name
        self._learning_agent = LearningAgent(
            agent_name=agent_name,
            model=model,
            storage_path=storage_path,
            use_hierarchical=use_hierarchical,
            hive_store=hive_store,
            prompt_variant=prompt_variant,
        )

        # OODA state — reset per process() call
        self._current_input: str = ""
        self._oriented_facts: dict[str, Any] = {}
        self._decision: str = ""  # "store" | "answer"

        # Optional callback fired after act() produces an answer.
        # Set via DI by the entrypoint for distributed eval answer collection.
        # Signature: on_answer(agent_name: str, answer: str) -> None
        self.on_answer: Any | None = None

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
        logger.debug("Agent %s observed input (%d chars)", self._agent_name, len(self._current_input))

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

        # Use LearningAgent's internal memory to recall relevant context
        facts: list[str] = []
        try:
            memory = self._learning_agent.memory
            if hasattr(memory, "search"):
                raw = memory.search(self._current_input[:200], limit=5)
                facts = [r.get("fact", str(r)) if isinstance(r, dict) else str(r) for r in (raw or [])]
            elif hasattr(memory, "search_facts"):
                raw = memory.search_facts(self._current_input[:200], limit=5)
                facts = [r.get("fact", str(r)) if isinstance(r, dict) else str(r) for r in (raw or [])]
        except Exception:
            logger.debug("orient() memory recall failed", exc_info=True)

        self._oriented_facts = {"input": self._current_input, "facts": facts}
        logger.debug(
            "Agent %s oriented: %d recalled facts", self._agent_name, len(facts)
        )
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
        lower = text.lower()
        _QUESTION_PREFIXES = (
            "what ", "who ", "when ", "where ", "why ", "how ", "which ",
            "is ", "are ", "was ", "were ", "do ", "does ", "did ", "can ",
            "could ", "should ", "would ", "will ", "has ", "have ", "had ",
        )
        is_question = (
            text.endswith("?")
            or any(lower.startswith(p) for p in _QUESTION_PREFIXES)
        )

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
        """
        text = self._current_input
        output = ""

        if self._decision == "answer":
            try:
                result = self._learning_agent.answer_question(text)
                output = result[0] if isinstance(result, tuple) else str(result)
            except Exception:
                logger.exception("Agent %s act() answer_question failed", self._agent_name)
                output = "Error: could not synthesize answer."
            # Write answer to stdout — Container Apps streams this to Log Analytics
            print(f"[{self._agent_name}] ANSWER: {output}", flush=True)
            logger.info("Agent %s ANSWER: %s", self._agent_name, output)
            # Fire callback for distributed eval answer collection
            if self.on_answer:
                try:
                    self.on_answer(self._agent_name, output)
                except Exception:
                    pass  # Never let callback errors break the OODA loop

        else:  # "store" (or empty / unknown)
            try:
                result_dict = self._learning_agent.learn_from_content(text)
                stored = result_dict.get("facts_stored", 0)
                output = f"Stored {stored} facts from input."
            except Exception:
                logger.exception("Agent %s act() learn_from_content failed", self._agent_name)
                output = "Error: could not store input."
            logger.debug("Agent %s STORED: %s", self._agent_name, output)

        return output

    # ------------------------------------------------------------------
    # Convenience pipeline
    # ------------------------------------------------------------------

    def process(self, input_data: str) -> str:
        """Run the full OODA pipeline for a single input.

        Equivalent to::

            agent.observe(input_data)
            agent.orient()
            agent.decide()
            return agent.act()

        Args:
            input_data: Raw input string.

        Returns:
            Output produced by ``act()``.
        """
        self.observe(input_data)
        self.orient()
        self.decide()
        return self.act()

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
            logger.debug(
                "Agent %s OODA turn %d (len=%d)", self._agent_name, turn, len(text)
            )
            try:
                self.process(text)
            except Exception:
                logger.exception(
                    "Agent %s: process() failed on turn %d", self._agent_name, turn
                )

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

    def close(self) -> None:
        """Delegate close to LearningAgent."""
        if hasattr(self._learning_agent, "close"):
            self._learning_agent.close()
