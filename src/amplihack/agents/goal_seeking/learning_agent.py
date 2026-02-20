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

import json
import logging
import os
from pathlib import Path
from typing import Any

import litellm

from .action_executor import ActionExecutor, calculate, read_content, search_memory
from .agentic_loop import AgenticLoop, ReasoningTrace
from .cognitive_adapter import HAS_COGNITIVE_MEMORY, CognitiveAdapter
from .flat_retriever_adapter import FlatRetrieverAdapter
from .memory_retrieval import MemoryRetriever

logger = logging.getLogger(__name__)


class LearningAgent:
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

    def __init__(
        self,
        agent_name: str = "learning_agent",
        model: str | None = None,
        storage_path: Path | None = None,
        use_hierarchical: bool = False,
    ):
        """Initialize learning agent.

        Args:
            agent_name: Name for the agent
            model: LLM model to use (litellm format)
            storage_path: Custom storage path for memory
            use_hierarchical: If True, use HierarchicalMemory via FlatRetrieverAdapter.
                If False, use original MemoryRetriever (backward compatible).

        Note:
            Requires OPENAI_API_KEY or appropriate provider key to be set.
        """
        self.agent_name = agent_name
        self.model = model or os.environ.get("EVAL_MODEL", "gpt-3.5-turbo")
        self.use_hierarchical = use_hierarchical

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

        # Initialize agentic loop
        self.loop = AgenticLoop(
            agent_name=agent_name,
            action_executor=self.executor,
            memory_retriever=self.memory,
            model=model,
        )

    def learn_from_content(self, content: str) -> dict[str, Any]:
        """Learn from content by extracting and storing facts.

        When use_hierarchical=True, stores the raw content as an episode first,
        then extracts facts with source_id pointing to the episode for provenance.
        Detects temporal markers in content and attaches temporal metadata to facts.

        Args:
            content: Article or content text

        Returns:
            Dictionary with learning results:
                - facts_extracted: Number of facts extracted
                - facts_stored: Number of facts stored
                - content_summary: Summary of content

        Example:
            >>> agent = LearningAgent()
            >>> result = agent.learn_from_content(
            ...     "Photosynthesis converts light into chemical energy."
            ... )
            >>> print(result['facts_extracted'])  # 1
        """
        if not content or not content.strip():
            return {"facts_extracted": 0, "facts_stored": 0, "content_summary": "Empty content"}

        # Input size limit to prevent memory exhaustion (security fix)
        max_content_length = 50_000
        if len(content) > max_content_length:
            logger.warning(
                "Content truncated from %d to %d chars", len(content), max_content_length
            )
            content = content[:max_content_length]

        # Detect temporal metadata from content before extraction
        temporal_meta = self._detect_temporal_metadata(content)

        # Extract source label from content title if present
        source_label = ""
        if content.startswith("Title: "):
            title_end = content.find("\n")
            if title_end > 0:
                source_label = content[7:title_end].strip()
        if not source_label:
            source_label = content[:60].strip()

        # In hierarchical mode, store episode first for provenance tracking
        episode_id = ""
        if self.use_hierarchical and hasattr(self.memory, "store_episode"):
            try:
                episode_id = self.memory.store_episode(
                    content=content[:2000],
                    source_label=source_label,
                )
            except Exception as e:
                logger.warning("Failed to store episode for provenance: %s", e)

        # Use LLM to extract facts (pass temporal metadata for conditional hints)
        facts = self._extract_facts_with_llm(content, temporal_meta)

        # Store each fact
        stored_count = 0
        for fact in facts:
            try:
                tags = fact.get("tags", ["learned"])
                # Add temporal tags if temporal metadata detected
                if temporal_meta.get("source_date"):
                    tags = list(tags) + [f"date:{temporal_meta['source_date']}"]
                if temporal_meta.get("temporal_order"):
                    tags = list(tags) + [f"time:{temporal_meta['temporal_order']}"]

                store_kwargs: dict[str, Any] = {
                    "context": fact["context"],
                    "fact": fact["fact"],
                    "confidence": fact.get("confidence", 0.8),
                    "tags": tags,
                }
                # Pass source_id for provenance when in hierarchical mode
                if self.use_hierarchical and episode_id:
                    store_kwargs["source_id"] = episode_id

                # Attach temporal metadata for chronological sorting
                # and source label for provenance tracking
                if self.use_hierarchical:
                    fact_metadata = {}
                    if temporal_meta:
                        fact_metadata.update(temporal_meta)
                    if source_label:
                        fact_metadata["source_label"] = source_label
                    if fact_metadata:
                        store_kwargs["temporal_metadata"] = fact_metadata

                self.memory.store_fact(**store_kwargs)
                stored_count += 1
            except Exception as e:
                logger.debug("Failed to store fact: %s", e)
                continue

        # Generate and store a summary concept map for knowledge organization
        if facts and stored_count > 0:
            self._store_summary_concept_map(content, facts, episode_id)

        return {
            "facts_extracted": len(facts),
            "facts_stored": stored_count,
            "content_summary": content[:200],
        }

    def _store_summary_concept_map(
        self, content: str, facts: list[dict], episode_id: str = ""
    ) -> None:
        """Generate and store a summary concept map for knowledge organization.

        Uses one LLM call to create a brief organizational overview of what
        was learned from the content. Stored as a SUMMARY node to help the
        agent explain the overall structure of its knowledge.

        Args:
            content: Original content that was learned
            facts: List of extracted fact dicts
            episode_id: Optional source episode ID
        """
        fact_list = "\n".join(
            f"- [{f.get('context', 'General')}] {f.get('fact', '')}" for f in facts[:15]
        )

        prompt = f"""Given these extracted facts, create a brief summary of the topics covered.
List the main themes/categories and how they relate to each other.

Facts:
{fact_list}

Return a concise summary (2-4 sentences) describing what topics this content covers
and how they connect. Format: "This content covers: 1) ..., 2) ..., 3) ..."
"""
        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a knowledge organizer. Create brief, clear summaries.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )

            summary = response.choices[0].message.content.strip()

            # Store as a special SUMMARY node
            store_kwargs: dict[str, Any] = {
                "context": "SUMMARY",
                "fact": summary,
                "confidence": 0.95,
                "tags": ["summary", "concept_map"],
            }
            if self.use_hierarchical and episode_id:
                store_kwargs["source_id"] = episode_id

            self.memory.store_fact(**store_kwargs)
            logger.debug("Stored summary concept map: %s", summary[:100])

        except Exception as e:
            logger.debug("Failed to generate summary concept map: %s", e)

    def _detect_temporal_metadata(self, content: str) -> dict[str, Any]:
        """Detect dates and temporal markers in content using LLM.

        Makes a single LLM call to extract temporal context from content.

        Args:
            content: Text content to analyze

        Returns:
            Dictionary with temporal metadata:
                - source_date: Date string if found (e.g., "2026-02-15")
                - temporal_order: Ordering label (e.g., "Day 7", "February 13")
                - temporal_index: Numeric index for sorting (e.g., 7 for Day 7)
        """
        prompt = f"""Analyze this content for temporal markers (dates, day numbers, time references).
Extract any date or time ordering information.

Content (first 500 chars):
{content[:500]}

Return ONLY a JSON object:
{{"source_date": "YYYY-MM-DD or empty string", "temporal_order": "brief label like Day 7 or February 13 or empty string", "temporal_index": 0}}

Rules:
- source_date: The primary date mentioned (ISO format YYYY-MM-DD), or "" if none
- temporal_order: A brief label for ordering (e.g., "Day 7", "After Day 9"), or "" if none
- temporal_index: A numeric value for chronological sorting (e.g., day number 7, 9, 10), or 0 if none
"""
        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Extract temporal metadata as JSON. Be precise."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )

            response_text = response.choices[0].message.content.strip()

            # Parse JSON response
            try:
                result = json.loads(response_text)
                if isinstance(result, dict):
                    return {
                        "source_date": result.get("source_date", ""),
                        "temporal_order": result.get("temporal_order", ""),
                        "temporal_index": result.get("temporal_index", 0),
                    }
            except json.JSONDecodeError:
                # Try extracting from markdown code block
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_str = response_text[json_start:json_end].strip()
                    result = json.loads(json_str)
                    if isinstance(result, dict):
                        return {
                            "source_date": result.get("source_date", ""),
                            "temporal_order": result.get("temporal_order", ""),
                            "temporal_index": result.get("temporal_index", 0),
                        }
        except Exception as e:
            logger.debug("Temporal metadata detection failed: %s", e)

        return {"source_date": "", "temporal_order": "", "temporal_index": 0}

    # Simple intents: skip iterative loop, use direct retrieval
    # This avoids the plan/search/evaluate overhead for straightforward questions
    # Intents that use simple retrieval (all facts for small KB, keyword search for large)
    # simple_recall: direct fact lookup
    # incremental_update: questions about latest/updated/changed information
    #   (needs ALL facts visible to find the most recent version)
    SIMPLE_INTENTS = {"simple_recall", "incremental_update"}

    # All other intents use iterative reasoning for targeted retrieval
    # The iterative loop filters noise better than dumping all facts

    def answer_question(
        self, question: str, question_level: str = "L1", return_trace: bool = False
    ) -> str | tuple[str, ReasoningTrace | None]:
        """Answer a question using adaptive retrieval and LLM synthesis.

        Uses intent complexity to decide the retrieval strategy:
        - Simple intents (simple_recall): single-pass retrieval, no iteration
        - Broad retrieval (multi_source_synthesis): get all facts for cross-source synthesis
        - Iterative intents: plan -> search -> evaluate -> refine loop

        Args:
            question: Question to answer
            question_level: Complexity level (L1/L2/L3/L4)

        Returns:
            Synthesized answer string

        Question Levels:
        - L1 (Recall): "What is X?"
        - L2 (Inference): "Why does X happen?"
        - L3 (Synthesis): "How are X and Y related?"
        - L4 (Application): "How would you use X to solve Y?"

        Example:
            >>> agent = LearningAgent()
            >>> # First learn some facts
            >>> agent.learn_from_content("Dogs are mammals. Mammals have fur.")
            >>> # Then answer questions
            >>> answer = agent.answer_question("Do dogs have fur?", "L2")
            >>> print(answer)  # LLM infers: "Yes, dogs have fur because..."
        """
        if not question or not question.strip():
            return "Error: Question is empty"

        # Step 1: Intent detection -- single LLM call to classify the question
        intent = self._detect_intent(question)
        intent_type = intent.get("intent", "simple_recall")

        # Step 2: Adaptive retrieval based on intent complexity
        # For small KBs (<=100 facts), always use simple retrieval (all facts).
        # The iterative search can miss facts whose text doesn't match queries,
        # and for small KBs the LLM can easily handle all facts in context.
        # This is critical for temporal/multi-source questions where completeness matters.
        reasoning_trace = None
        use_simple = intent_type in self.SIMPLE_INTENTS
        if not use_simple and hasattr(self.memory, "get_all_facts"):
            kb_size = len(self.memory.get_all_facts(limit=151))
            if kb_size <= 150:
                use_simple = True

        if use_simple:
            # Simple retrieval: get all facts for complete coverage
            relevant_facts = self._simple_retrieval(question)
        else:
            # Large KB: use iterative reasoning with plan/search/evaluate
            relevant_facts, _, reasoning_trace = self.loop.reason_iteratively(
                question=question,
                memory=self.memory,
                intent=intent,
                max_steps=3,
            )

        # Fall back to getting all facts if retrieval found nothing
        if not relevant_facts:
            if hasattr(self.memory, "get_all_facts"):
                relevant_facts = self.memory.get_all_facts(limit=50)

        if not relevant_facts:
            return "I don't have enough information to answer that question."

        # Sort temporally if needed
        if intent.get("needs_temporal"):

            def temporal_sort_key(fact):
                meta = fact.get("metadata", {})
                t_idx = meta.get("temporal_index", 999999) if meta else 999999
                return (t_idx, fact.get("timestamp", ""))

            relevant_facts = sorted(relevant_facts, key=temporal_sort_key)

        # If the question references a specific article/source, provide a filtered
        # subset of facts from JUST that article. This helps the LLM focus on the
        # right source when answering source-specific questions. Runs for any intent
        # type since intent classification may not always detect multi-source needs.
        source_specific_facts = self._filter_facts_by_source_reference(question, relevant_facts)
        if source_specific_facts:
            intent["source_specific_facts"] = source_specific_facts

        # Retrieve SUMMARY nodes for birds-eye knowledge overview
        if self.use_hierarchical:
            summary_nodes = self._get_summary_nodes()
            if summary_nodes:
                intent["summary_context"] = "\n".join(f"- {s['outcome']}" for s in summary_nodes)

        # Step 3: Synthesize answer with intent-aware prompting
        answer = self._synthesize_with_llm(
            question=question,
            context=relevant_facts,
            question_level=question_level,
            intent=intent,
        )

        # Step 4: If math was needed, validate arithmetic in the answer
        if intent.get("needs_math"):
            answer = self._validate_arithmetic(answer)

        # Build trace for simple path
        if reasoning_trace is None:
            from .agentic_loop import ReasoningTrace as _RT

            reasoning_trace = _RT(
                question=question,
                intent=intent,
                used_simple_path=True,
                total_facts_collected=len(relevant_facts),
            )

        # Store the question-answer pair as a learning (truncate to fit)
        self.memory.store_fact(
            context=f"Question: {question[:200]}",
            fact=f"Answer: {answer[:900]}",
            confidence=0.7,
            tags=["q_and_a", question_level.lower()],
        )

        if return_trace:
            return answer, reasoning_trace
        return answer

    def _simple_retrieval(self, question: str) -> list[dict[str, Any]]:
        """Single-pass retrieval for simple recall questions.

        Gets all facts if the knowledge base is small (<=150), otherwise
        uses keyword search. The threshold is set high because:
        - LLMs can easily handle 150 facts in context
        - Keyword search may miss relevant facts (e.g., Day 10 data)
        - Completeness is critical for temporal and multi-source questions

        Args:
            question: The question to retrieve facts for

        Returns:
            List of fact dicts
        """
        if not hasattr(self.memory, "get_all_facts"):
            return []

        # Check knowledge base size -- use generous threshold
        all_facts = self.memory.get_all_facts(limit=151)
        if len(all_facts) <= 150:
            return all_facts

        # Larger knowledge base: use keyword search
        results = self.memory.search(query=question, limit=40)
        return results if results else all_facts[:150]

    def _filter_facts_by_source_reference(
        self, question: str, facts: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Filter facts to those from a specific source referenced in the question.

        When a question mentions a specific article (e.g., "mentioned in the athlete
        achievements article"), extract the source name and filter facts that have
        a matching source_label in their metadata.

        Args:
            question: The question text
            facts: List of all retrieved fact dicts

        Returns:
            Filtered list of facts from the referenced source, or empty list
            if no specific source is referenced in the question.
        """
        q_lower = question.lower()
        # Common patterns: "mentioned in the X article", "from the X article", "in the X"
        source_keywords = []
        for pattern in ("mentioned in the ", "from the ", "in the ", "according to the "):
            idx = q_lower.find(pattern)
            if idx >= 0:
                after = q_lower[idx + len(pattern) :]
                # Extract until "article", "report", "source", or end of phrase
                for end_word in ("article", "report", "source", "piece", "?"):
                    end_idx = after.find(end_word)
                    if end_idx > 0:
                        source_keywords.append(after[:end_idx].strip())
                        break

        if not source_keywords:
            return []

        # Find facts whose source_label matches any keyword
        matched = []
        for fact in facts:
            meta = fact.get("metadata", {})
            source = (meta.get("source_label", "") or "").lower()
            if any(kw in source for kw in source_keywords if kw):
                matched.append(fact)

        logger.debug(
            "Source filter: keywords=%s, matched %d/%d facts",
            source_keywords,
            len(matched),
            len(facts),
        )
        return matched

    def _get_summary_nodes(self) -> list[dict[str, Any]]:
        """Retrieve SUMMARY concept map nodes from memory.

        Returns:
            List of summary fact dicts with context and outcome fields.
        """
        if not (self.use_hierarchical and hasattr(self.memory, "memory")):
            return []

        try:
            result = self.memory.memory.connection.execute(
                """
                MATCH (m:SemanticMemory)
                WHERE m.agent_id = $agent_id AND m.concept = 'SUMMARY'
                RETURN m.memory_id, m.concept, m.content, m.confidence
                ORDER BY m.created_at DESC
                LIMIT 5
                """,
                {"agent_id": self.agent_name},
            )

            summaries = []
            while result.has_next():
                row = result.get_next()
                summaries.append(
                    {
                        "context": row[1],
                        "outcome": row[2],
                        "confidence": row[3],
                    }
                )
            return summaries

        except Exception as e:
            logger.debug("Failed to retrieve summary nodes: %s", e)
            return []

    def _detect_intent(self, question: str) -> dict[str, Any]:
        """Detect question intent using a single LLM call.

        Classifies the question to determine what kind of reasoning is needed,
        allowing the synthesis prompt to be tailored accordingly.

        Args:
            question: The question to classify

        Returns:
            Dictionary with intent classification:
                - intent: str (simple_recall, mathematical_computation,
                  temporal_comparison, multi_source_synthesis, contradiction_resolution)
                - needs_math: bool
                - needs_temporal: bool
                - reasoning: str
        """
        prompt = f"""Classify this question. Does it require:
(a) simple recall - direct fact lookup
(b) mathematical computation - arithmetic, counting, differences
(c) temporal comparison/ordering - comparing values across time periods, tracking changes, describing trends
(d) multi-source synthesis - combining information from different sources
(e) contradiction resolution - handling conflicting information
(f) incremental update - finding the MOST RECENT or UPDATED information. Use this when the question asks about a SINGLE entity's current state or history (keywords: "how many now", "current", "latest", "updated", "changed", "how did X change", "trajectory", "complete history", "describe X's achievement/record/progress")

Question: {question}

Return ONLY a JSON object:
{{"intent": "one of: simple_recall, mathematical_computation, temporal_comparison, multi_source_synthesis, contradiction_resolution, incremental_update", "needs_math": true/false, "needs_temporal": true/false, "reasoning": "brief explanation"}}"""

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a question classifier. Return only JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )

            response_text = response.choices[0].message.content.strip()

            try:
                result = json.loads(response_text)
                if isinstance(result, dict):
                    return {
                        "intent": result.get("intent", "simple_recall"),
                        "needs_math": bool(result.get("needs_math", False)),
                        "needs_temporal": bool(result.get("needs_temporal", False)),
                        "reasoning": result.get("reasoning", ""),
                    }
            except json.JSONDecodeError:
                # Try extracting from markdown code block
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_str = response_text[json_start:json_end].strip()
                    result = json.loads(json_str)
                    if isinstance(result, dict):
                        return {
                            "intent": result.get("intent", "simple_recall"),
                            "needs_math": bool(result.get("needs_math", False)),
                            "needs_temporal": bool(result.get("needs_temporal", False)),
                            "reasoning": result.get("reasoning", ""),
                        }
        except Exception as e:
            logger.debug("Intent detection failed: %s", e)

        # Default: simple recall
        return {
            "intent": "simple_recall",
            "needs_math": False,
            "needs_temporal": False,
            "reasoning": "default",
        }

    def _validate_arithmetic(self, answer: str) -> str:
        """Validate arithmetic expressions found in the answer using the calculator.

        Scans the answer for simple arithmetic expressions (e.g., "26 - 18 = 8")
        and verifies the results using the calculate tool.

        Args:
            answer: The synthesized answer text

        Returns:
            The answer, potentially with corrected arithmetic
        """
        import re

        # Find patterns like "number - number = number" or "number + number = number"
        pattern = r"(\d+(?:\.\d+)?)\s*([+\-*/])\s*(\d+(?:\.\d+)?)\s*=\s*(\d+(?:\.\d+)?)"
        matches = re.finditer(pattern, answer)

        for match in matches:
            a, op, b, claimed_result = (
                match.group(1),
                match.group(2),
                match.group(3),
                match.group(4),
            )
            expr = f"{a} {op} {b}"
            calc_result = calculate(expr)

            if calc_result["result"] is not None:
                actual = calc_result["result"]
                try:
                    claimed = float(claimed_result)
                    if abs(actual - claimed) > 0.01:
                        # Replace wrong result with correct one
                        correct_str = str(int(actual)) if actual == int(actual) else str(actual)
                        old_text = match.group(0)
                        new_text = f"{a} {op} {b} = {correct_str}"
                        answer = answer.replace(old_text, new_text, 1)
                        logger.debug(
                            "Corrected arithmetic: %s -> %s",
                            old_text,
                            new_text,
                        )
                except ValueError:
                    pass

        return answer

    def _extract_facts_with_llm(
        self, content: str, temporal_meta: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Use LLM to extract structured facts from content.

        Args:
            content: Text content to extract facts from
            temporal_meta: Optional temporal metadata detected from content

        Returns:
            List of facts as dictionaries with:
                - context: Topic/context of the fact
                - fact: The actual fact
                - confidence: Confidence score
                - tags: Relevant tags
        """
        temporal_meta = temporal_meta or {}
        # Add temporal instruction only for content with strong temporal markers
        temporal_hint = ""
        if temporal_meta.get("temporal_order") or temporal_meta.get("source_date"):
            time_label = temporal_meta.get("temporal_order") or temporal_meta.get("source_date", "")
            temporal_hint = (
                f"\n\nCRITICAL - TEMPORAL CONTEXT: This content is from {time_label}.\n"
                f"You MUST prefix EVERY fact with '{time_label}' so the time context is preserved.\n"
                f"Example: 'As of {time_label}, Norway has 28 total medals' NOT just "
                "'Norway has 28 total medals'.\n"
                "This is essential for later temporal comparisons across different time periods."
            )

        # Add procedural hint for step-by-step content
        procedural_hint = ""
        content_lower = content.lower()
        if any(
            kw in content_lower
            for kw in ("step 1", "step 2", "steps:", "procedure", "instructions")
        ):
            procedural_hint = (
                "\n\nNote: This content contains step-by-step procedures. "
                "Extract EACH step as a separate fact with its step number preserved. "
                "Also extract ONE summary fact listing ALL steps in order. "
                "Example: 'Complete workflow: Step 1: X, Step 2: Y, Step 3: Z'"
            )

        prompt = f"""Extract key facts from this content. For each fact, provide:
1. Context (what topic it relates to)
2. The fact itself (MUST include specific names, numbers, and entities)
3. Confidence (0.0-1.0)
4. Tags (relevant keywords)

CRITICAL RULES for fact extraction:
- Each NAMED PERSON must appear in at least one fact with their FULL NAME and COUNTRY
- Each SPECIFIC NUMBER must be preserved exactly (medals, dates, records)
- Extract ONE FACT PER PERSON mentioned, even if brief
- Never summarize multiple people as "various athletes" - name them individually
{temporal_hint}{procedural_hint}

Content:
{content[:2000]}

Respond with a JSON list like:
[
  {{
    "context": "Topic name",
    "fact": "The fact itself",
    "confidence": 0.9,
    "tags": ["tag1", "tag2"]
  }}
]
"""

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a fact extraction expert."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )

            response_text = response.choices[0].message.content

            # Parse JSON
            try:
                facts = json.loads(response_text)
                return facts if isinstance(facts, list) else []
            except json.JSONDecodeError:
                # Try to extract from markdown code block
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_str = response_text[json_start:json_end].strip()
                    facts = json.loads(json_str)
                    return facts if isinstance(facts, list) else []
                return []

        except Exception:
            # Fallback: create simple fact from content
            return [
                {
                    "context": "General",
                    "fact": content[:500],
                    "confidence": 0.5,
                    "tags": ["auto_extracted"],
                }
            ]

    def _synthesize_with_llm(
        self,
        question: str,
        context: list[dict[str, Any]],
        question_level: str = "L1",
        intent: dict[str, Any] | None = None,
    ) -> str:
        """Synthesize answer using LLM from retrieved context.

        This is the key method that enables LLM-powered answer synthesis
        rather than just returning retrieved text. Uses intent detection
        results to tailor the synthesis prompt.

        Args:
            question: Question to answer
            context: Retrieved facts from memory
            question_level: Question complexity (L1-L4)
            intent: Optional intent classification from _detect_intent()

        Returns:
            Synthesized answer string
        """
        intent = intent or {}
        intent_type = intent.get("intent", "simple_recall")

        # Use more facts for questions that need complete data coverage
        if intent_type in (
            "multi_source_synthesis",
            "temporal_comparison",
            "mathematical_computation",
        ):
            max_facts = 60
        else:
            max_facts = 30

        # Build context string - include temporal metadata, source labels, and supersede markers
        def _format_fact(i: int, fact: dict, include_temporal: bool) -> str:
            meta = fact.get("metadata", {})
            markers = []
            if include_temporal:
                if meta.get("source_date"):
                    markers.append(f"Date: {meta['source_date']}")
                if meta.get("temporal_order"):
                    markers.append(meta["temporal_order"])
            if meta.get("source_label"):
                markers.append(f"Source: {meta['source_label']}")
            if meta.get("superseded"):
                markers.append("OUTDATED - superseded by newer information")
            marker_str = f" [{', '.join(markers)}]" if markers else ""
            line = f"{i}. Context: {fact['context']}{marker_str}\n"
            line += f"   Fact: {fact['outcome']}\n\n"
            return line

        if intent.get("needs_temporal"):
            context_str = "Relevant facts (ordered chronologically where possible):\n"
            for i, fact in enumerate(context[:max_facts], 1):
                context_str += _format_fact(i, fact, include_temporal=True)
        else:
            context_str = "Relevant facts:\n"
            for i, fact in enumerate(context[:max_facts], 1):
                context_str += _format_fact(i, fact, include_temporal=False)

        # Build prompt based on question level
        level_instructions = {
            "L1": (
                "Provide a direct, factual answer based on the facts. "
                "State the answer clearly and concisely. Do NOT add arithmetic "
                "verification or computation - just report the facts as stored."
            ),
            "L2": "Connect multiple facts to infer an answer. Explain your reasoning.",
            "L3": "Synthesize information from the facts to create a comprehensive answer.",
            "L4": (
                "Apply the knowledge to answer the question. For PROCEDURAL questions "
                "(describing workflows, steps, commands), reconstruct the exact ordered "
                "sequence of steps from the facts. Number each step. Include specific "
                "commands or actions at each step. CRITICAL: Answer ONLY what is asked. "
                "If the question says 'from X to Y', start at step X and end at step Y. "
                "Do NOT include setup/installation prerequisites unless explicitly asked. "
                "For example, 'from creating a project to running tests' means start at "
                "the 'create project' step, not at 'install SDK'."
            ),
        }

        instruction = level_instructions.get(question_level, level_instructions["L1"])

        # Add intent-specific instructions only for complex intents
        # (simple_recall and incremental_update don't need math/temporal prompts
        #  which can cause the LLM to add wrong verification steps)
        extra_instructions = ""
        is_complex_intent = intent_type not in self.SIMPLE_INTENTS
        if is_complex_intent and intent.get("needs_math"):
            extra_instructions += (
                "\n\nIMPORTANT - MATHEMATICAL COMPUTATION REQUIRED:\n"
                "- Extract the raw numbers from the facts FIRST\n"
                "- Show all arithmetic step by step\n"
                "- Write out each calculation explicitly (e.g., 26 - 18 = 8)\n"
                "- When computing differences for multiple entities, do ALL of them\n"
                "- Double-check every subtraction and addition\n"
                "- Verify your final numerical answer by re-doing the computation\n"
            )

        if is_complex_intent and intent.get("needs_temporal"):
            extra_instructions += (
                "\n\nIMPORTANT - TEMPORAL REASONING REQUIRED:\n"
                "You MUST follow this exact process:\n\n"
                "STEP A: Build a data table\n"
                "Create a table with rows = entities (countries/people) and columns = time periods.\n"
                "Fill in the EXACT numbers from the facts for each cell.\n"
                "Example:\n"
                "| Country | Day 7 Golds | Day 9 Golds | Day 10 Golds |\n"
                "| Norway  | 8           | 12          | 13           |\n\n"
                "STEP B: Compute differences\n"
                "For EACH entity, calculate: later_value - earlier_value = difference\n"
                "Write out the arithmetic explicitly: '13 - 8 = 5'\n"
                "Do this for EVERY entity, not just the one you think is the answer.\n\n"
                "STEP C: Compare and conclude\n"
                "List all computed differences side by side.\n"
                "Only THEN identify which is largest/smallest/etc.\n\n"
                "STEP D: Verify\n"
                "Re-check your arithmetic. Recompute at least one difference to confirm.\n\n"
                "CRITICAL RULES:\n"
                "- NEVER skip the data table step\n"
                "- NEVER guess differences - always compute them from the raw numbers\n"
                "- Pay attention to WHICH metric is asked about (gold vs total vs other)\n"
                "- When describing trends, state the EXACT change in each sub-period "
                "(e.g., '+4 golds Day 7→9, then +1 gold Day 9→10, total +5')\n"
                "- Do NOT write your final answer at the top. Show all work FIRST,\n"
                "  then state your conclusion at the END after all calculations.\n"
            )

        # Add multi-source synthesis instructions
        if intent_type == "multi_source_synthesis":
            extra_instructions += (
                "\n\nIMPORTANT - MULTI-SOURCE SYNTHESIS REQUIRED:\n"
                "Before answering, RESTATE the question in your own words to ensure you understand it.\n\n"
                "Rules:\n"
                "- The answer requires combining information from MULTIPLE different sources/articles\n"
                "- First, identify which facts come from which source (look at [Source: ...] labels)\n"
                "- If the question asks about a SPECIFIC source/article (e.g., 'mentioned in the athlete article'):\n"
                "  * Filter facts to ONLY those from that specific source\n"
                "  * COUNT the relevant items from that source precisely\n"
                "  * Do NOT use data from other sources for this part\n"
                "- When finding connections ACROSS sources, cite the specific numbers from each\n"
                "- When counting entities (athletes, events, etc.), list them explicitly by NAME\n"
                "- Read the question carefully:\n"
                "  * 'individual athletes' = count NAMED PEOPLE, not country medal totals\n"
                "  * 'mentioned in article X' = count only items that appear in that article\n"
                "  * 'most medals mentioned' = count how many athletes (medal winners) are named\n"
                "    from each country IN THAT ARTICLE, then compare country counts\n"
            )

        # Add summary context only for multi-source synthesis (not every question)
        summary_section = ""
        if intent_type == "multi_source_synthesis" and intent.get("summary_context"):
            summary_section = f"""
Knowledge Overview (what was learned):
{intent["summary_context"]}
"""

        # Add contradiction-specific instructions
        # Also trigger for questions that hint at conflicting data
        contradiction_instructions = ""
        has_contradiction_cues = any(
            kw in question.lower()
            for kw in ("disagree", "conflicting", "contradiction", "reliable", "trust")
        )
        if intent_type == "contradiction_resolution" or (
            question_level == "L5" or has_contradiction_cues
        ):
            contradiction_instructions = (
                "\n\nIMPORTANT - HANDLING CONFLICTING INFORMATION:\n"
                "Check the facts carefully for CONFLICTING numbers or claims from different sources.\n"
                "If the facts contain DIFFERENT values for the same metric:\n"
                "- You MUST present ALL conflicting values with their sources\n"
                "- Do NOT dismiss any source as an 'outlier' - all sources are equally valid\n"
                "- State clearly: 'According to [Source A], X. According to [Source B], Y.'\n"
                "- Explain possible reasons for the discrepancy\n"
                "- Do NOT pick one value as 'the answer' - the contradiction IS the answer\n"
            )

        # Add counterfactual/hypothetical reasoning instructions
        counterfactual_instructions = ""
        question_lower = question.lower()
        if any(
            kw in question_lower
            for kw in ("what if", "if ", "would ", "without ", "had not", "removed")
        ):
            counterfactual_instructions = (
                "\n\nIMPORTANT - HYPOTHETICAL/COUNTERFACTUAL REASONING:\n"
                "This question asks you to imagine an alternative scenario. You MUST:\n"
                "1. Start from the ACTUAL facts as your baseline\n"
                "2. Apply the hypothetical change (remove X, change timing, etc.)\n"
                "3. Reason through the CONSEQUENCES of that change step by step\n"
                "4. Compare the hypothetical outcome to ALL other entities (not just the one asked about)\n"
                "5. Draw a clear conclusion about how things would be different\n\n"
                "Do NOT refuse to answer by saying the hypothetical isn't in the facts.\n"
                "The whole point is to REASON about what WOULD happen based on what you DO know.\n"
            )

        # Build source-specific section if available
        source_specific_section = ""
        source_specific = intent.get("source_specific_facts", [])
        if source_specific:
            source_label = (
                source_specific[0].get("metadata", {}).get("source_label", "referenced article")
            )
            source_specific_section = (
                f"\n\n*** CRITICAL: FACTS FROM THE REFERENCED ARTICLE '{source_label}' ***\n"
                "READ THESE CAREFULLY - These are the EXACT facts from the specific article "
                "mentioned in the question:\n\n"
            )
            for i, fact in enumerate(source_specific, 1):
                source_specific_section += f"  SOURCE FACT {i}: {fact.get('outcome', '')}\n"
            source_specific_section += (
                "\n*** When the question asks about this specific article, use ONLY "
                "the SOURCE FACTS above. Count the named individuals listed here. ***\n"
            )

        prompt = f"""Answer this question using the provided facts.

Question: {question}
Level: {question_level} - {instruction}
{extra_instructions}{contradiction_instructions}{counterfactual_instructions}
{summary_section}
{source_specific_section}
{context_str}

Provide a clear, well-reasoned answer. If the facts don't fully answer the question, say so.
"""

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a knowledgeable assistant that synthesizes information. "
                        "When doing math, always show your work and verify calculations.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # Lower temperature for more precise reasoning
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error("LLM synthesis failed: %s", e)
            return "I was unable to synthesize an answer due to an internal error."

    def get_memory_stats(self) -> dict[str, Any]:
        """Get statistics about stored knowledge.

        Returns:
            Dictionary with memory statistics
        """
        return self.memory.get_statistics()

    def _explain_knowledge(self, topic: str, depth: str = "overview") -> str:
        """Generate an explanation of a topic from stored knowledge.

        Unlike synthesize_answer (which requires a question), this generates
        topic-driven explanations at varying detail levels.

        Args:
            topic: Topic to explain
            depth: "brief" (1 sentence), "overview" (paragraph), "comprehensive"

        Returns:
            Explanation string
        """
        # Retrieve relevant facts about the topic
        facts = self._simple_retrieval(topic)
        if not facts:
            return f"I don't have knowledge about '{topic}'."

        facts_text = "\n".join(f"- {f.get('outcome', '')[:150]}" for f in facts[:20])

        depth_instructions = {
            "brief": "Provide a 1-2 sentence summary.",
            "overview": "Provide a clear paragraph-length overview.",
            "comprehensive": "Provide a comprehensive explanation covering all key aspects.",
        }

        prompt = f"""Explain the topic '{topic}' using ONLY the facts below.
{depth_instructions.get(depth, depth_instructions["overview"])}

Available facts:
{facts_text}

Be factual and specific. Do not add information beyond what the facts support."""

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a knowledgeable explainer."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Explanation generation failed: %s", e)
            return f"Unable to generate explanation for '{topic}'."

    def _find_knowledge_gaps(self, topic: str) -> dict[str, Any]:
        """Identify what's unknown or uncertain about a topic.

        Analyzes stored facts and identifies missing information,
        low-confidence areas, and potential contradictions.

        Args:
            topic: Topic to analyze

        Returns:
            Dict with gaps, contradictions, and suggestions
        """
        facts = self._simple_retrieval(topic)
        if not facts:
            return {
                "topic": topic,
                "gaps": ["No knowledge stored about this topic"],
                "contradictions": [],
                "low_confidence_facts": [],
                "suggestion": f"Learn about '{topic}' from external content first.",
            }

        # Find low-confidence facts
        low_conf = [f for f in facts if f.get("confidence", 1.0) < 0.6]

        # Find potential contradictions (facts with "superseded" metadata)
        contradictions = [f for f in facts if f.get("metadata", {}).get("superseded")]

        # Use LLM to identify conceptual gaps
        facts_text = "\n".join(
            f"- [{f.get('context', '?')}] {f.get('outcome', '')[:100]} "
            f"(confidence: {f.get('confidence', 0):.1f})"
            for f in facts[:15]
        )

        prompt = f"""Given these facts about '{topic}', what important information is MISSING?

Facts:
{facts_text}

List 2-4 specific gaps (things we don't know but should).
Return ONLY a JSON object: {{"gaps": ["gap1", "gap2"], "overall_coverage": "low/medium/high"}}"""

        gaps = ["Unable to analyze gaps"]
        coverage = "unknown"
        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Identify knowledge gaps. Return JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            from .json_utils import parse_llm_json

            result = parse_llm_json(response.choices[0].message.content)
            if result:
                gaps = result.get("gaps", gaps)
                coverage = result.get("overall_coverage", coverage)
        except Exception as e:
            logger.debug("Gap analysis LLM call failed: %s", e)

        return {
            "topic": topic,
            "total_facts": len(facts),
            "gaps": gaps,
            "contradictions": [f.get("outcome", "")[:100] for f in contradictions],
            "low_confidence_facts": [
                {"fact": f.get("outcome", "")[:100], "confidence": f.get("confidence", 0)}
                for f in low_conf
            ],
            "overall_coverage": coverage,
        }

    def _verify_fact(self, fact: str) -> dict[str, Any]:
        """Verify if a fact is consistent with stored knowledge.

        Checks the fact against all stored facts for consistency,
        identifies supporting evidence and contradictions.

        Args:
            fact: The fact to verify

        Returns:
            Dict with verification results
        """
        # Search for related facts
        related = self._simple_retrieval(fact)
        if not related:
            return {
                "fact": fact,
                "verified": False,
                "confidence": 0.0,
                "supporting_facts": [],
                "contradicting_facts": [],
                "reasoning": "No related knowledge found to verify against.",
            }

        facts_text = "\n".join(f"- {f.get('outcome', '')[:150]}" for f in related[:15])

        prompt = f"""Verify this fact against the stored knowledge:

Fact to verify: {fact}

Stored knowledge:
{facts_text}

Is the fact consistent with stored knowledge? Return ONLY a JSON object:
{{"verified": true/false, "confidence": 0.8, "supporting": ["fact1"], "contradicting": ["fact2"], "reasoning": "explanation"}}"""

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Verify facts against knowledge. Return JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            from .json_utils import parse_llm_json

            result = parse_llm_json(response.choices[0].message.content)
            if result:
                return {
                    "fact": fact,
                    "verified": bool(result.get("verified", False)),
                    "confidence": float(result.get("confidence", 0.5)),
                    "supporting_facts": result.get("supporting", []),
                    "contradicting_facts": result.get("contradicting", []),
                    "reasoning": result.get("reasoning", ""),
                }
        except Exception as e:
            logger.debug("Fact verification LLM call failed: %s", e)

        return {
            "fact": fact,
            "verified": False,
            "confidence": 0.0,
            "supporting_facts": [],
            "contradicting_facts": [],
            "reasoning": "Verification failed due to an internal error.",
        }

    def close(self):
        """Close agent and release resources."""
        self.memory.close()
