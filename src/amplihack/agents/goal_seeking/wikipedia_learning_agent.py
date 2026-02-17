from __future__ import annotations

"""Wikipedia learning agent with LLM-powered answer synthesis.

Philosophy:
- Single responsibility: Learn from Wikipedia and answer questions
- Uses agentic loop for structured learning
- LLM synthesizes answers (not just retrieval)
- Handles question complexity levels (L1-L4)
- Supports hierarchical memory with Graph RAG (use_hierarchical=True)
"""

from pathlib import Path
from typing import Any

import litellm

from .action_executor import ActionExecutor, read_content, search_memory
from .agentic_loop import AgenticLoop
from .flat_retriever_adapter import FlatRetrieverAdapter
from .memory_retrieval import MemoryRetriever


class WikipediaLearningAgent:
    """Specialized agent that learns from Wikipedia content and answers questions.

    Uses the PERCEIVE->REASON->ACT->LEARN loop to:
    1. Read Wikipedia content
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
        >>> agent = WikipediaLearningAgent("wiki_agent")
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
        agent_name: str = "wikipedia_agent",
        model: str = "gpt-3.5-turbo",
        storage_path: Path | None = None,
        use_hierarchical: bool = False,
    ):
        """Initialize Wikipedia learning agent.

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

        # Initialize agentic loop
        self.loop = AgenticLoop(
            agent_name=agent_name,
            action_executor=self.executor,
            memory_retriever=self.memory,
            model=model,
        )

    def learn_from_content(self, content: str) -> dict[str, Any]:
        """Learn from Wikipedia content by extracting and storing facts.

        When use_hierarchical=True, stores the raw content as an episode first,
        then extracts facts with source_id pointing to the episode for provenance.

        Args:
            content: Wikipedia article text

        Returns:
            Dictionary with learning results:
                - facts_extracted: Number of facts extracted
                - facts_stored: Number of facts stored
                - content_summary: Summary of content

        Example:
            >>> agent = WikipediaLearningAgent()
            >>> result = agent.learn_from_content(
            ...     "Photosynthesis converts light into chemical energy."
            ... )
            >>> print(result['facts_extracted'])  # 1
        """
        if not content or not content.strip():
            return {"facts_extracted": 0, "facts_stored": 0, "content_summary": "Empty content"}

        # In hierarchical mode, store episode first for provenance tracking
        episode_id = ""
        if self.use_hierarchical and hasattr(self.memory, "store_episode"):
            try:
                episode_id = self.memory.store_episode(
                    content=content[:2000],
                    source_label=f"Wikipedia: {content[:50]}...",
                )
            except Exception:
                pass

        # Use LLM to extract facts
        facts = self._extract_facts_with_llm(content)

        # Store each fact
        stored_count = 0
        for fact in facts:
            try:
                store_kwargs: dict[str, Any] = {
                    "context": fact["context"],
                    "fact": fact["fact"],
                    "confidence": fact.get("confidence", 0.8),
                    "tags": fact.get("tags", ["wikipedia"]),
                }
                # Pass source_id for provenance when in hierarchical mode
                if self.use_hierarchical and episode_id:
                    store_kwargs["source_id"] = episode_id

                self.memory.store_fact(**store_kwargs)
                stored_count += 1
            except Exception:
                # Continue storing other facts even if one fails
                continue

        return {
            "facts_extracted": len(facts),
            "facts_stored": stored_count,
            "content_summary": content[:200],
        }

    def answer_question(self, question: str, question_level: str = "L1") -> str:
        """Answer a question using stored knowledge and LLM synthesis.

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
            >>> agent = WikipediaLearningAgent()
            >>> # First learn some facts
            >>> agent.learn_from_content("Dogs are mammals. Mammals have fur.")
            >>> # Then answer questions
            >>> answer = agent.answer_question("Do dogs have fur?", "L2")
            >>> print(answer)  # LLM infers: "Yes, dogs have fur because..."
        """
        if not question or not question.strip():
            return "Error: Question is empty"

        # In hierarchical mode, use Graph RAG subgraph retrieval
        if self.use_hierarchical and hasattr(self.memory, "memory"):
            subgraph = self.memory.memory.retrieve_subgraph(query=question, max_nodes=20)
            if subgraph.nodes:
                # Convert subgraph nodes to flat format for _synthesize_with_llm
                relevant_facts = [
                    {
                        "context": node.concept,
                        "outcome": node.content,
                        "confidence": node.confidence,
                    }
                    for node in subgraph.nodes
                ]
            else:
                # Fallback to get_all_facts if subgraph empty
                relevant_facts = self.memory.get_all_facts(limit=50)
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

        # Use LLM to synthesize answer
        answer = self._synthesize_with_llm(
            question=question, context=relevant_facts, question_level=question_level
        )

        # Store the question-answer pair as a learning (truncate to fit)
        self.memory.store_fact(
            context=f"Question: {question[:200]}",
            fact=f"Answer: {answer[:900]}",
            confidence=0.7,
            tags=["q_and_a", question_level.lower()],
        )

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
            import json

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
        self, question: str, context: list[dict[str, Any]], question_level: str = "L1"
    ) -> str:
        """Synthesize answer using LLM from retrieved context.

        This is the key method that enables LLM-powered answer synthesis
        rather than just returning retrieved text.

        Args:
            question: Question to answer
            context: Retrieved facts from memory
            question_level: Question complexity (L1-L4)

        Returns:
            Synthesized answer string
        """
        # Build context string - include more facts for better coverage
        context_str = "Relevant facts:\n"
        for i, fact in enumerate(context[:20], 1):
            context_str += f"{i}. Context: {fact['context']}\n"
            context_str += f"   Fact: {fact['outcome']}\n\n"

        # Build prompt based on question level
        level_instructions = {
            "L1": "Provide a direct, factual answer based on the facts.",
            "L2": "Connect multiple facts to infer an answer. Explain your reasoning.",
            "L3": "Synthesize information from the facts to create a comprehensive answer.",
            "L4": "Apply the knowledge to answer the question, showing how the facts relate.",
        }

        instruction = level_instructions.get(question_level, level_instructions["L1"])

        prompt = f"""Answer this question using the provided facts.

Question: {question}
Level: {question_level} - {instruction}

{context_str}

Provide a clear, well-reasoned answer. If the facts don't fully answer the question, say so.
"""

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a knowledgeable assistant that synthesizes information.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
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
