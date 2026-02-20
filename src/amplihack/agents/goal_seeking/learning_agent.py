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

from __future__ import annotations

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
        self.agent_name = agent_name
        self.model = model or os.environ.get("EVAL_MODEL", "gpt-3.5-turbo")
        self.use_hierarchical = use_hierarchical

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

        self.executor = ActionExecutor()

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

        self.loop = AgenticLoop(
            agent_name=agent_name,
            action_executor=self.executor,
            memory_retriever=self.memory,
            model=model,
        )

    def learn_from_content(self, content: str) -> dict[str, Any]:
        """Learn from content by extracting and storing facts."""
        if not content or not content.strip():
            return {"facts_extracted": 0, "facts_stored": 0, "content_summary": "Empty content"}

        max_content_length = 50_000
        if len(content) > max_content_length:
            logger.warning(
                "Content truncated from %d to %d chars", len(content), max_content_length
            )
            content = content[:max_content_length]

        temporal_meta = self._detect_temporal_metadata(content)

        source_label = ""
        if content.startswith("Title: "):
            title_end = content.find("\n")
            if title_end > 0:
                source_label = content[7:title_end].strip()
        if not source_label:
            source_label = content[:60].strip()

        episode_id = ""
        if self.use_hierarchical and hasattr(self.memory, "store_episode"):
            try:
                episode_id = self.memory.store_episode(
                    content=content[:2000],
                    source_label=source_label,
                )
            except Exception as e:
                logger.warning("Failed to store episode for provenance: %s", e)

        facts = self._extract_facts_with_llm(content, temporal_meta)

        stored_count = 0
        for fact in facts:
            try:
                tags = fact.get("tags", ["learned"])
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
                if self.use_hierarchical and episode_id:
                    store_kwargs["source_id"] = episode_id

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
        """Generate and store a summary concept map for knowledge organization."""
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
        """Detect dates and temporal markers in content using LLM."""
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

            try:
                result = json.loads(response_text)
                if isinstance(result, dict):
                    return {
                        "source_date": result.get("source_date", ""),
                        "temporal_order": result.get("temporal_order", ""),
                        "temporal_index": result.get("temporal_index", 0),
                    }
            except json.JSONDecodeError:
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

    SIMPLE_INTENTS = {"simple_recall", "incremental_update"}

    def answer_question(
        self, question: str, question_level: str = "L1", return_trace: bool = False
    ) -> str | tuple[str, ReasoningTrace | None]:
        """Answer a question using adaptive retrieval and LLM synthesis."""
        if not question or not question.strip():
            return "Error: Question is empty"

        intent = self._detect_intent(question)
        intent_type = intent.get("intent", "simple_recall")

        reasoning_trace = None
        if intent_type in self.SIMPLE_INTENTS:
            relevant_facts = self._simple_retrieval(question)
        else:
            relevant_facts, _, reasoning_trace = self.loop.reason_iteratively(
                question=question,
                memory=self.memory,
                intent=intent,
                max_steps=3,
            )

        if not relevant_facts:
            if hasattr(self.memory, "get_all_facts"):
                relevant_facts = self.memory.get_all_facts(limit=50)

        if not relevant_facts:
            return "I don't have enough information to answer that question."

        if intent.get("needs_temporal"):

            def temporal_sort_key(fact):
                meta = fact.get("metadata", {})
                t_idx = meta.get("temporal_index", 999999) if meta else 999999
                return (t_idx, fact.get("timestamp", ""))

            relevant_facts = sorted(relevant_facts, key=temporal_sort_key)

        if self.use_hierarchical:
            summary_nodes = self._get_summary_nodes()
            if summary_nodes:
                intent["summary_context"] = "\n".join(f"- {s['outcome']}" for s in summary_nodes)

        answer = self._synthesize_with_llm(
            question=question,
            context=relevant_facts,
            question_level=question_level,
            intent=intent,
        )

        if intent.get("needs_math"):
            answer = self._validate_arithmetic(answer)

        if reasoning_trace is None:
            from .agentic_loop import ReasoningTrace as _RT

            reasoning_trace = _RT(
                question=question,
                intent=intent,
                used_simple_path=True,
                total_facts_collected=len(relevant_facts),
            )

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
        """Single-pass retrieval for simple recall questions."""
        if not hasattr(self.memory, "get_all_facts"):
            return []

        all_facts = self.memory.get_all_facts(limit=51)
        if len(all_facts) <= 50:
            return all_facts

        results = self.memory.search(query=question, limit=20)
        return results if results else all_facts[:50]

    def _get_summary_nodes(self) -> list[dict[str, Any]]:
        """Retrieve SUMMARY concept map nodes from memory."""
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
        """Detect question intent using a single LLM call."""
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

        return {
            "intent": "simple_recall",
            "needs_math": False,
            "needs_temporal": False,
            "reasoning": "default",
        }

    def _validate_arithmetic(self, answer: str) -> str:
        """Validate arithmetic expressions found in the answer using the calculator."""
        import re

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
        """Use LLM to extract structured facts from content."""
        temporal_meta = temporal_meta or {}
        temporal_hint = ""
        if temporal_meta.get("temporal_order") or temporal_meta.get("source_date"):
            temporal_hint = (
                "\n\nNote: This content has a specific time context "
                f"({temporal_meta.get('temporal_order', temporal_meta.get('source_date', ''))}).\n"
                "Include the time period or day number in each fact where relevant. "
                "For example: 'As of Day 10, Norway has 28 total medals' rather than just "
                "'Norway has 28 total medals'."
            )

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
2. The fact itself
3. Confidence (0.0-1.0)
4. Tags (relevant keywords)
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

            try:
                facts = json.loads(response_text)
                return facts if isinstance(facts, list) else []
            except json.JSONDecodeError:
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_str = response_text[json_start:json_end].strip()
                    facts = json.loads(json_str)
                    return facts if isinstance(facts, list) else []
                return []

        except Exception:
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
        """Synthesize answer using LLM from retrieved context."""
        intent = intent or {}
        intent_type = intent.get("intent", "simple_recall")

        max_facts = 40 if intent_type == "multi_source_synthesis" else 20

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
                "commands or actions at each step. Do not skip steps or add prerequisites "
                "that aren't in the facts."
            ),
        }

        instruction = level_instructions.get(question_level, level_instructions["L1"])

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
                "Fill in the EXACT numbers from the facts for each cell.\n\n"
                "STEP B: Compute differences\n"
                "For EACH entity, calculate: later_value - earlier_value = difference\n"
                "Write out the arithmetic explicitly.\n\n"
                "STEP C: Compare and conclude\n"
                "List all computed differences side by side.\n"
                "Only THEN identify which is largest/smallest/etc.\n\n"
                "STEP D: Verify\n"
                "Re-check your arithmetic.\n\n"
                "CRITICAL RULES:\n"
                "- NEVER skip the data table step\n"
                "- NEVER guess differences - always compute them from the raw numbers\n"
                "- Pay attention to WHICH metric is asked about (gold vs total vs other)\n"
            )

        if intent_type == "multi_source_synthesis":
            extra_instructions += (
                "\n\nIMPORTANT - MULTI-SOURCE SYNTHESIS REQUIRED:\n"
                "- The answer requires combining information from MULTIPLE different sources/articles\n"
                "- First, identify which facts come from which source (look at [Source: ...] labels)\n"
                "- When finding connections ACROSS sources, cite the specific numbers from each\n"
                "- When counting entities (athletes, events, etc.), list them explicitly\n"
            )

        summary_section = ""
        if intent_type == "multi_source_synthesis" and intent.get("summary_context"):
            summary_section = f"""
Knowledge Overview (what was learned):
{intent["summary_context"]}
"""

        contradiction_instructions = ""
        if intent_type == "contradiction_resolution":
            contradiction_instructions = (
                "\n\nIMPORTANT - HANDLING CONFLICTING INFORMATION:\n"
                "- Present both viewpoints with their sources if available\n"
                "- Explain why they might differ\n"
                "- Let the questioner decide which to trust\n"
            )

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
                "2. Apply the hypothetical change\n"
                "3. Reason through the CONSEQUENCES step by step\n"
                "4. Compare the hypothetical outcome to ALL other entities\n"
                "5. Draw a clear conclusion\n\n"
                "Do NOT refuse to answer by saying the hypothetical isn't in the facts.\n"
            )

        prompt = f"""Answer this question using the provided facts.

Question: {question}
Level: {question_level} - {instruction}
{extra_instructions}{contradiction_instructions}{counterfactual_instructions}
{summary_section}
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
                temperature=0.3,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error("LLM synthesis failed: %s", e)
            return "I was unable to synthesize an answer due to an internal error."

    def get_memory_stats(self) -> dict[str, Any]:
        """Get statistics about stored knowledge."""
        return self.memory.get_statistics()

    def _explain_knowledge(self, topic: str, depth: str = "overview") -> str:
        """Generate an explanation of a topic from stored knowledge."""
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
        """Identify what's unknown or uncertain about a topic."""
        facts = self._simple_retrieval(topic)
        if not facts:
            return {
                "topic": topic,
                "gaps": ["No knowledge stored about this topic"],
                "contradictions": [],
                "low_confidence_facts": [],
                "suggestion": f"Learn about '{topic}' from external content first.",
            }

        low_conf = [f for f in facts if f.get("confidence", 1.0) < 0.6]
        contradictions = [f for f in facts if f.get("metadata", {}).get("superseded")]

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
        """Verify if a fact is consistent with stored knowledge."""
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
