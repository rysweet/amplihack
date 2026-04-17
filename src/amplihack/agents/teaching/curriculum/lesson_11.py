"""Lesson 11 content builder."""

from __future__ import annotations

import textwrap

from amplihack.agents.teaching.models import Exercise, Lesson, QuizQuestion


def _build_lesson_11() -> Lesson:
    """Lesson 11: Retrieval Architecture."""
    return Lesson(
        id="L11",
        title="Retrieval Architecture",
        description="Understand the four retrieval strategies and when each is used.",
        content=textwrap.dedent("""\
            # Lesson 11: Retrieval Architecture

            ## The Retrieval Problem

            A goal-seeking agent stores facts in memory. When answering a question,
            it must decide *which* facts to retrieve. Different questions require
            different retrieval strategies.

            ## Four Retrieval Strategies

            ### 1. Simple Retrieval

            ```python
            def _simple_retrieval(self, question: str) -> list[dict]:
            ```

            - **How it works**: Returns all facts from memory (up to 15,000).
            - **Used when**: KB has <= 500 facts, or intent is in `SIMPLE_INTENTS`
              (simple_recall, incremental_update, contradiction_resolution,
              multi_source_synthesis).
            - **Why**: For small KBs, the LLM can handle all facts in context.
              Keyword-based filtering can miss facts whose text does not match
              the query. Simple retrieval guarantees completeness.

            ### 2. Entity Retrieval

            ```python
            def _entity_retrieval(self, question: str) -> list[dict]:
            ```

            - **How it works**: Extracts proper nouns from the question using regex,
              then calls `memory.retrieve_by_entity(name)` for each entity.
            - **Used when**: Question contains proper nouns (capitalized names) and
              KB has > 500 facts.
            - **Why**: Large KBs cannot fit in context. Entity retrieval targets
              the specific person/project the question is about.
            - **Fallback**: If entity retrieval returns nothing, falls back to
              simple retrieval + reranking.

            ### 3. Concept Retrieval

            ```python
            def _concept_retrieval(self, question: str) -> list[dict]:
            ```

            - **How it works**: Extracts key noun phrases (not proper nouns) by
              filtering stop-words, then searches memory with bigrams and unigrams.
            - **Used when**: Question has no proper nouns but has domain concepts.
            - **Why**: Handles questions like "What is the temperature threshold?"
              where there are no named entities but specific domain terms.

            ### 4. Tiered Retrieval (Progressive Summarization)

            ```python
            def _tiered_retrieval(self, question: str, all_facts: list) -> list:
            ```

            - **How it works**: Splits facts into three tiers by recency:
              - Tier 1 (most recent 200): returned verbatim
              - Tier 2 (facts 201-1000): entity-level summaries
              - Tier 3 (facts 1000+): topic-level summaries
            - **Used when**: KB has > 1000 facts and simple retrieval is triggered.
            - **Why**: Keeps recent facts detailed while compressing old facts.
              Summaries preserve numbers, names, dates, and status values.

            ## Retrieval Selection Flow

            ```
            answer_question()
                |
                +-- _detect_intent() -> intent_type
                |
                +-- if intent_type in AGGREGATION_INTENTS:
                |       -> _aggregation_retrieval() (Cypher graph queries)
                |
                +-- elif intent_type in SIMPLE_INTENTS or KB <= 500:
                |       -> _simple_retrieval()
                |           |
                |           +-- if KB > 1000: _tiered_retrieval()
                |
                +-- else (large KB, complex intent):
                        -> _entity_retrieval()
                        |
                        +-- if empty: _simple_retrieval() + rerank
            ```

            ## Reranking

            After retrieval, `rerank_facts_by_query()` sorts facts by relevance
            to the question using token overlap scoring. This ensures the most
            relevant facts appear first in the LLM context.

            ## Source-Specific Filtering

            If the question references a specific article (e.g., "mentioned in the
            athlete achievements article"), `_filter_facts_by_source_reference()`
            extracts the source name and filters facts whose metadata has a matching
            `source_label`. This filtered subset is passed to the LLM as extra context.
        """),
        prerequisites=["L07"],
        exercises=[
            Exercise(
                id="E11-01",
                instruction=(
                    "List the four retrieval strategies (simple, entity, concept, tiered) "
                    "and write one sentence for each explaining when it is used."
                ),
                expected_output=(
                    "Simple: Used for small KBs (<=500 facts) or simple intents; returns all facts. "
                    "Entity: Used when question has proper nouns and KB > 500; targets named entities. "
                    "Concept: Used when no proper nouns but domain terms exist; searches bigrams. "
                    "Tiered: Used when KB > 1000 facts; progressive summarization by recency."
                ),
                hint="Each strategy targets a different KB size and question type.",
                validation_fn="validate_retrieval_strategy",
            ),
            Exercise(
                id="E11-02",
                instruction=(
                    "An agent with 2000 facts receives the question 'What is Sarah Chen's role?'. "
                    "Trace the retrieval path: which strategy is tried first, and what happens "
                    "if it returns no results?"
                ),
                expected_output=(
                    "1. Intent detection classifies as simple_recall. "
                    "2. But KB has 2000 facts (> 500), so entity retrieval is tried first. "
                    "3. 'Sarah Chen' is extracted as a proper noun. "
                    "4. memory.retrieve_by_entity('Sarah Chen') is called. "
                    "5. If entity retrieval returns nothing, fallback to simple retrieval + rerank."
                ),
                hint="Check the retrieval selection flow diagram in the lesson.",
            ),
        ],
        quiz=[
            QuizQuestion(
                question="What is the KB size threshold where simple retrieval always applies?",
                correct_answer="500 facts or fewer -- all facts are returned verbatim",
                wrong_answers=[
                    "100 facts or fewer",
                    "1000 facts or fewer",
                    "There is no threshold -- intent determines it",
                ],
                explanation="For KBs <= 500 facts, simple retrieval is always used regardless of intent.",
            ),
            QuizQuestion(
                question="What does tiered retrieval do with facts older than the most recent 200?",
                correct_answer="Summarizes them: entity-level summaries for 201-1000, topic-level for 1000+",
                wrong_answers=[
                    "Discards them entirely",
                    "Returns them verbatim but at the end",
                    "Compresses them with gzip",
                ],
                explanation="Tiered retrieval uses progressive summarization preserving key details.",
            ),
            QuizQuestion(
                question="Why does entity retrieval fall back to simple retrieval when it finds nothing?",
                correct_answer=(
                    "The question may not have proper nouns in the memory's entity index, "
                    "so simple retrieval with reranking surfaces the correct facts"
                ),
                wrong_answers=[
                    "Entity retrieval always finds something",
                    "It falls back to concept retrieval first",
                    "Empty results mean the agent has no relevant knowledge",
                ],
                explanation="Entity extraction is regex-based and can miss names not in the index.",
            ),
        ],
    )
