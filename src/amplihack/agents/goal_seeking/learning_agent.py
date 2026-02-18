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
from pathlib import Path
from typing import Any

import litellm

from .action_executor import ActionExecutor, calculate, read_content, search_memory
from .agentic_loop import AgenticLoop
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
        model: str = "gpt-3.5-turbo",
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
        self.model = model
        self.use_hierarchical = use_hierarchical

        # Initialize memory based on mode
        if use_hierarchical:
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

        # Detect temporal metadata from content before extraction
        temporal_meta = self._detect_temporal_metadata(content)

        # In hierarchical mode, store episode first for provenance tracking
        episode_id = ""
        if self.use_hierarchical and hasattr(self.memory, "store_episode"):
            try:
                episode_id = self.memory.store_episode(
                    content=content[:2000],
                    source_label=f"Content: {content[:50]}...",
                )
            except Exception:
                pass

        # Use LLM to extract facts
        facts = self._extract_facts_with_llm(content)

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
                if temporal_meta and self.use_hierarchical:
                    store_kwargs["temporal_metadata"] = temporal_meta

                self.memory.store_fact(**store_kwargs)
                stored_count += 1
            except Exception:
                # Continue storing other facts even if one fails
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

    def answer_question(self, question: str, question_level: str = "L1") -> str:
        """Answer a question using stored knowledge and LLM synthesis.

        Uses intent detection to classify the question before synthesis.
        When use_hierarchical=True, uses retrieve_subgraph for Graph RAG context.
        Otherwise uses smart retrieval: for small knowledge bases (<= 50 facts),
        retrieves ALL facts and lets the LLM decide relevance.

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

        # Step 2: Retrieve relevant facts
        # In hierarchical mode, use Graph RAG subgraph retrieval
        if self.use_hierarchical and hasattr(self.memory, "memory"):
            subgraph = self.memory.memory.retrieve_subgraph(query=question, max_nodes=20)
            if subgraph.nodes:
                # If temporal question, sort chronologically
                if intent.get("needs_temporal"):

                    def temporal_sort_key(node):
                        t_idx = (
                            node.metadata.get("temporal_index", 999999) if node.metadata else 999999
                        )
                        return (t_idx, node.created_at or "")

                    sorted_nodes = sorted(subgraph.nodes, key=temporal_sort_key)
                else:
                    sorted_nodes = subgraph.nodes

                # Convert subgraph nodes to flat format for _synthesize_with_llm
                relevant_facts = [
                    {
                        "context": node.concept,
                        "outcome": node.content,
                        "confidence": node.confidence,
                        "metadata": node.metadata if node.metadata else {},
                    }
                    for node in sorted_nodes
                ]
            else:
                # Fallback to get_all_facts if subgraph empty
                relevant_facts = self.memory.get_all_facts(limit=50)

            # Also retrieve SUMMARY nodes for birds-eye knowledge overview
            summary_nodes = self._get_summary_nodes()
            if summary_nodes:
                intent["summary_context"] = "\n".join(f"- {s['outcome']}" for s in summary_nodes)
        else:
            # Original smart retrieval logic
            stats = self.memory.get_statistics()
            total_experiences = stats.get("total_experiences", 0)

            if total_experiences <= 50:
                relevant_facts = self.memory.get_all_facts(limit=50)
            else:
                relevant_facts = self.memory.search(query=question, limit=10, min_confidence=0.5)
                if len(relevant_facts) < 3:
                    relevant_facts = self.memory.get_all_facts(limit=50)

        if not relevant_facts:
            return "I don't have enough information to answer that question."

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

        # Store the question-answer pair as a learning (truncate to fit)
        self.memory.store_fact(
            context=f"Question: {question[:200]}",
            fact=f"Answer: {answer[:900]}",
            confidence=0.7,
            tags=["q_and_a", question_level.lower()],
        )

        return answer

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

Question: {question}

Return ONLY a JSON object:
{{"intent": "one of: simple_recall, mathematical_computation, temporal_comparison, multi_source_synthesis, contradiction_resolution", "needs_math": true/false, "needs_temporal": true/false, "reasoning": "brief explanation"}}"""

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

    def _extract_facts_with_llm(self, content: str) -> list[dict[str, Any]]:
        """Use LLM to extract structured facts from content.

        Args:
            content: Text content to extract facts from

        Returns:
            List of facts as dictionaries with:
                - context: Topic/context of the fact
                - fact: The actual fact
                - confidence: Confidence score
                - tags: Relevant tags
        """
        prompt = f"""Extract key facts from this content. For each fact, provide:
1. Context (what topic it relates to)
2. The fact itself
3. Confidence (0.0-1.0)
4. Tags (relevant keywords)

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

        # Build context string - include temporal metadata and source labels when available
        if intent.get("needs_temporal"):
            context_str = "Relevant facts (ordered chronologically where possible):\n"
            for i, fact in enumerate(context[:20], 1):
                meta = fact.get("metadata", {})
                time_marker = ""
                source_marker = ""
                if meta.get("source_date"):
                    time_marker = f" [Date: {meta['source_date']}]"
                if meta.get("temporal_order"):
                    time_marker += f" [{meta['temporal_order']}]"
                if meta.get("source_label"):
                    source_marker = f" [Source: {meta['source_label']}]"
                context_str += f"{i}. Context: {fact['context']}{time_marker}{source_marker}\n"
                context_str += f"   Fact: {fact['outcome']}\n\n"
        else:
            context_str = "Relevant facts:\n"
            for i, fact in enumerate(context[:20], 1):
                meta = fact.get("metadata", {})
                source_marker = ""
                if meta.get("source_label"):
                    source_marker = f" [Source: {meta['source_label']}]"
                context_str += f"{i}. Context: {fact['context']}{source_marker}\n"
                context_str += f"   Fact: {fact['outcome']}\n\n"

        # Build prompt based on question level
        level_instructions = {
            "L1": "Provide a direct, factual answer based on the facts.",
            "L2": "Connect multiple facts to infer an answer. Explain your reasoning.",
            "L3": "Synthesize information from the facts to create a comprehensive answer.",
            "L4": "Apply the knowledge to answer the question, showing how the facts relate.",
        }

        instruction = level_instructions.get(question_level, level_instructions["L1"])

        # Add intent-specific instructions
        extra_instructions = ""
        if intent.get("needs_math"):
            extra_instructions += (
                "\n\nIMPORTANT - MATHEMATICAL COMPUTATION REQUIRED:\n"
                "- Show all arithmetic step by step\n"
                "- Write out each calculation explicitly (e.g., 26 - 18 = 8)\n"
                "- Double-check every subtraction and addition\n"
                "- Verify your final numerical answer by re-doing the computation\n"
            )

        if intent.get("needs_temporal"):
            extra_instructions += (
                "\n\nIMPORTANT - TEMPORAL REASONING REQUIRED:\n"
                "- First, organize ALL facts by time period/date before answering\n"
                "- For each entity mentioned, list its values at EACH time point\n"
                "- When comparing changes over time, compute the DIFFERENCE for EACH entity\n"
                "- When describing trends, report the specific changes in each period "
                "(e.g., '+3 in period 1, then +1 in period 2') and the total change\n"
                "- Focus on reporting the FACTUAL changes rather than characterizing trends "
                "with subjective terms. State exactly how many were gained in each sub-period.\n"
                "- If the question asks 'which improved most', compute the difference for "
                "ALL entities and compare them explicitly before concluding\n"
                "- Pay careful attention to what metric is being asked about "
                "(gold medals vs total medals vs other)\n"
            )

        # Add summary context only for multi-source synthesis (not every question)
        summary_section = ""
        intent_type = intent.get("intent", "simple_recall")
        if intent_type == "multi_source_synthesis" and intent.get("summary_context"):
            summary_section = f"""
Knowledge Overview (what was learned):
{intent["summary_context"]}
"""

        # Add contradiction-specific instructions
        contradiction_instructions = ""
        if intent_type == "contradiction_resolution":
            contradiction_instructions = (
                "\n\nIMPORTANT - HANDLING CONFLICTING INFORMATION:\n"
                "- Present both viewpoints with their sources if available\n"
                "- Explain why they might differ (different time periods, different measurements, etc.)\n"
                "- Let the questioner decide which to trust\n"
                "- If one source seems more reliable or recent, note that\n"
            )

        prompt = f"""Answer this question using the provided facts.

Question: {question}
Level: {question_level} - {instruction}
{extra_instructions}{contradiction_instructions}
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
                temperature=0.3,  # Lower temperature for more precise reasoning
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"Error synthesizing answer: {e!s}"

    def get_memory_stats(self) -> dict[str, Any]:
        """Get statistics about stored knowledge.

        Returns:
            Dictionary with memory statistics
        """
        return self.memory.get_statistics()

    def close(self):
        """Close agent and release resources."""
        self.memory.close()
