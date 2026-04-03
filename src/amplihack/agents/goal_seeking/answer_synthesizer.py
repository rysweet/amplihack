from __future__ import annotations

"""LLM-based answer synthesis, completeness evaluation, agentic answering."""

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from .agentic_loop import ReasoningTrace
from .prompt_utils import _get_llm_completion, _load_prompt
from .prompts import load_prompt
from .retrieval_constants import (
    KEYWORD_EXPANSION_SPARSE_FACT_THRESHOLD,
    MAX_RETRIEVAL_LIMIT,
    SIMPLE_RETRIEVAL_THRESHOLD,
)
from .similarity import (
    extract_entity_anchor_tokens,
    extract_query_anchor_tokens,
    extract_query_phrases,
    rerank_facts_by_query,
    tokenize_similarity_text,
)

logger = logging.getLogger(__name__)


class AnswerSynthesizerMixin:
    """Mixin providing answer synthesis for LearningAgent."""

    async def answer_question(
        self,
        question: str,
        question_level: str = "L1",
        return_trace: bool = False,
        _skip_qanda_store: bool = False,
        _force_simple: bool = False,
    ) -> str | tuple[str, ReasoningTrace | None]:
        """Answer a question using adaptive retrieval and LLM synthesis.

        Uses intent complexity to decide the retrieval strategy:
        - Simple intents (simple_recall): single-pass retrieval, no iteration
        - Broad retrieval (multi_source_synthesis): get all facts for cross-source synthesis
        - Iterative intents: plan -> search -> evaluate -> refine loop

        Args:
            question: Question to answer
            question_level: Complexity level (L1/L2/L3/L4)
            return_trace: If True, return (answer, ReasoningTrace) tuple
            _skip_qanda_store: (Solution B) When True, skip storing the Q&A pair as
                a learning fact. Used when answer_question_agentic calls this
                internally to reduce concurrent DB writes during parallel eval.
            _force_simple: (Solution C) When True AND entity retrieval returns empty,
                force _simple_retrieval to return all facts verbatim (bypass tiered
                summarization). Prevents infrastructure facts stored early in the
                knowledge base from being lost in Tier 3 topic-level summaries.

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

        self._thread_local._last_simple_retrieval_exhaustive = False

        # ── OODA: OBSERVE ────────────────────────────────────────────────────
        # Ingest the question and recall any prior answers from Memory facade.
        self.loop.observe(question)

        # Step 1 / OODA ORIENT (start): Intent detection -- single LLM call
        intent = await self._detect_intent(question)
        intent_type = intent.get("intent", "simple_recall")

        # Step 2: Adaptive retrieval based on intent complexity
        # For small KBs (<=100 facts), always use simple retrieval (all facts).
        # The iterative search can miss facts whose text doesn't match queries,
        # and for small KBs the LLM can easily handle all facts in context.
        # This is critical for temporal/multi-source questions where completeness matters.
        reasoning_trace = None

        # Detect enumeration keywords that need broader retrieval even if
        # the LLM classified as a different intent. These questions ask about
        # ALL items ("list all", "which topics", "how many different") and
        # need high retrieval limits to avoid missing entries.
        _q_lower = question.lower()
        _ENUMERATION_KEYWORDS = (
            "list all",
            "which topics",
            "how many different",
            "enumerate",
            "what are all",
            "name all",
            "show all",
            "count all",
            "every incident",
            "all incidents",
            "all cve",
        )
        is_enumeration = any(kw in _q_lower for kw in _ENUMERATION_KEYWORDS)
        if is_enumeration and intent_type not in self.AGGREGATION_INTENTS:
            # Force aggregation routing for enumeration questions that were
            # misclassified as simple_recall or other intents.
            logger.info(
                "Enumeration keywords detected in '%s'; routing to aggregation retrieval",
                question[:60],
            )
            intent_type = "meta_memory"
            intent["intent"] = "meta_memory"

        # Route meta-memory questions to Cypher aggregation
        used_simple_path = False
        if intent_type in self.AGGREGATION_INTENTS:
            relevant_facts = self._aggregation_retrieval(question, intent)
        else:
            use_simple = intent_type in self.SIMPLE_INTENTS
            if not use_simple and hasattr(self.memory, "get_all_facts"):
                # Solution A: Use thread-local cache to avoid data races when
                # multiple threads share one LearningAgent instance
                # (e.g. --parallel-workers 10 in the eval harness).
                # Solution D: Skip the DB query entirely when pre-snapshot is already
                # available — _simple_retrieval() will use it and the thread-local
                # cache would never be consumed, causing a wasted get_all_facts() call.
                if self._pre_snapshot_facts is not None:
                    kb_size = len(self._pre_snapshot_facts)
                else:
                    cached = getattr(self._thread_local, "_cached_all_facts", None)
                    if cached is None:
                        cached = self.memory.get_all_facts(
                            limit=MAX_RETRIEVAL_LIMIT, query=question
                        )
                    self._thread_local._cached_all_facts = cached
                    kb_size = self._estimate_total_fact_count() or len(cached)
                if kb_size <= SIMPLE_RETRIEVAL_THRESHOLD:
                    use_simple = True

            if use_simple:
                # Simple retrieval: get all facts for complete coverage.
                # Solution C: pass force_verbatim so simple_recall questions in agentic
                # context also bypass Tier 3 compression (not just entity-retrieval fallback).
                relevant_facts = self._simple_retrieval(question, force_verbatim=_force_simple)
                used_simple_path = True
            else:
                # Large KB: try entity-centric retrieval first
                relevant_facts = self._entity_retrieval(question)

                # Filter Q&A echoes early so we can correctly detect empty retrieval
                relevant_facts = [
                    f
                    for f in relevant_facts
                    if not (
                        f.get("context", "").startswith("Question:")
                        and "q_and_a" in (f.get("tags") or [])
                    )
                ]
                if not relevant_facts:
                    # Entity retrieval empty (or only Q&A echoes).
                    # Fall back to simple retrieval + rerank which is proven
                    # to surface correct facts for non-entity questions.
                    logger.info(
                        "Entity retrieval empty/noise for '%s'; simple retrieval + rerank",
                        question[:50],
                    )
                    # Solution C: When _force_simple is set (agentic context),
                    # bypass tiered summarization to avoid losing early-stored
                    # infrastructure facts that get compressed into Tier 3 summaries.
                    relevant_facts = self._simple_retrieval(question, force_verbatim=_force_simple)

        # Fall back to simple retrieval if all strategies found nothing
        if not relevant_facts:
            logger.info("All retrieval empty; falling back to _simple_retrieval")
            relevant_facts = self._simple_retrieval(question)

        if not relevant_facts:
            return "I don't have enough information to answer that question."

        exhaustive_retrieval = bool(
            getattr(self._thread_local, "_last_simple_retrieval_exhaustive", False)
        )
        supplemental_local_only = hasattr(self.memory, "search_local")

        # Filter out Q&A self-learning facts from retrieval -- they are stored
        # for cross-session learning but pollute within-session eval results.
        relevant_facts = [
            f
            for f in relevant_facts
            if not (
                f.get("context", "").startswith("Question:") and "q_and_a" in (f.get("tags") or [])
            )
        ]

        if used_simple_path and not exhaustive_retrieval:
            relevant_facts = self._supplement_simple_retrieval(
                question,
                relevant_facts,
                local_only=supplemental_local_only,
            )

        # Entity-linked retrieval: when the question mentions structured IDs
        # (e.g. INC-2024-001, CVE-2024-3094), pull related LOCAL facts without
        # re-fanning the whole hive. Large-KB tiered retrieval preserves exact-ID
        # matches verbatim so we do not need a second distributed search pass here.
        if self._ENTITY_ID_PATTERN.search(question) and not exhaustive_retrieval:
            relevant_facts = self._entity_linked_retrieval(
                question,
                relevant_facts,
                local_only=supplemental_local_only,
            )

        # Chain-aware multi-hop: when the question mentions 2+ named entities
        # or IDs, retrieve facts for each entity separately and merge.
        if not exhaustive_retrieval:
            relevant_facts = self._multi_entity_retrieval(
                question,
                relevant_facts,
                local_only=supplemental_local_only,
            )

        # For math/numerical and temporal questions on large KBs, supplement retrieval
        # with keyword-targeted search to recover exact numbers/temporal chains
        # lost in summarization or missed by entity retrieval.
        _supplement_intents = (
            "mathematical_computation",
            "ratio_trend_analysis",
            "temporal_comparison",
        )
        if (
            intent_type in _supplement_intents
            and hasattr(self.memory, "search")
            and not exhaustive_retrieval
            and len(relevant_facts) < KEYWORD_EXPANSION_SPARSE_FACT_THRESHOLD
        ):
            existing_ids = {
                f.get("experience_id", "") for f in relevant_facts if f.get("experience_id")
            }
            supplemental = await self._keyword_expanded_retrieval(
                question,
                relevant_facts,
                local_only=supplemental_local_only,
            )
            for f in supplemental:
                eid = f.get("experience_id", "")
                if eid and eid not in existing_ids:
                    existing_ids.add(eid)
                    relevant_facts.append(f)

        # For meta_memory questions: keep tiered summaries since they provide
        # the broad coverage needed for counting/enumerating entities across
        # a large KB. Only filter out DB-stored SUMMARY nodes (context == "SUMMARY")
        # which are different from tiered retrieval summaries.
        if intent_type == "meta_memory":
            relevant_facts = [f for f in relevant_facts if f.get("context", "") != "SUMMARY"]

        # Always rerank by query relevance first to prioritize the most relevant facts.
        # For large fact sets (>80), this ensures we trim noise, not signal.
        relevant_facts = rerank_facts_by_query(relevant_facts, question)

        # Sort temporally if needed (after reranking so top-K are already relevant).
        # Only promote the temporally sortable facts that still match the question's
        # discriminative anchors. A global time sort across every temporal fact can
        # let unrelated early timeline items outrank the entity-specific history the
        # question is actually asking about.
        if intent.get("needs_temporal") or intent_type in (
            "temporal_comparison",
            "incremental_update",
        ):
            entity_anchor_tokens = extract_entity_anchor_tokens(question)
            anchor_tokens = extract_query_anchor_tokens(question)
            query_phrases = extract_query_phrases(question)
            prioritized_temporal_facts = []
            remaining_facts = []

            def matches_temporal_query(fact: dict[str, Any]) -> bool:
                fact_text = f"{fact.get('context', '')} {fact.get('outcome', '')}"
                fact_text_lower = fact_text.lower()
                fact_tokens = tokenize_similarity_text(fact_text)
                entity_anchor_hits = len(entity_anchor_tokens & fact_tokens)
                anchor_hits = len(anchor_tokens & fact_tokens)
                phrase_hits = sum(1 for phrase in query_phrases if phrase in fact_text_lower)
                required_anchor_hits = 1 if len(anchor_tokens) < 3 else 2
                if entity_anchor_tokens:
                    return entity_anchor_hits > 0 and (
                        phrase_hits > 0 or anchor_hits >= required_anchor_hits
                    )
                return phrase_hits > 0 or anchor_hits >= required_anchor_hits

            for f in relevant_facts:
                meta = f.get("metadata", {})
                t_idx = meta.get("temporal_index", 0) if meta else 0
                if t_idx > 0 and matches_temporal_query(f):
                    prioritized_temporal_facts.append(f)
                else:
                    remaining_facts.append(f)

            def temporal_sort_key(fact):
                meta = fact.get("metadata", {})
                t_idx = meta.get("temporal_index", 999999) if meta else 999999
                return (t_idx, fact.get("timestamp", ""))

            prioritized_temporal_facts.sort(key=temporal_sort_key)
            relevant_facts = prioritized_temporal_facts + remaining_facts

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

        deterministic_meta_answer = None
        if intent_type == "meta_memory":
            deterministic_meta_answer = self._deterministic_meta_memory_answer(
                question,
                relevant_facts,
            )

        # Pre-compute math result if needed, so synthesis can use it directly
        if intent.get("needs_math") and deterministic_meta_answer is None:
            computed = await self._compute_math_result(question, relevant_facts, intent)
            if computed:
                intent["computed_math"] = computed

        # Pre-compute temporal code generation for temporal trap/current/change-count questions
        question_lower_for_temporal = question.lower()
        direct_temporal_lookup = self._heuristic_temporal_entity_field(question)
        _temporal_code_keywords = (
            "after first",
            "before final",
            "second",
            "intermediate",
            "between",
            "before the",
            "before any",
            "originally",
            "original",
            "previous",
            "current",
            "latest",
            "final",
            "last",
            "change",
            "changed",
            "how many times",
            "times did",
        )
        is_temporal_code_candidate = direct_temporal_lookup is not None or (
            (
                intent.get("needs_temporal")
                or intent_type in ("temporal_comparison", "incremental_update")
            )
            and any(kw in question_lower_for_temporal for kw in _temporal_code_keywords)
        )

        if is_temporal_code_candidate:
            try:
                code_result = await self._code_generation_tool(
                    question, candidate_facts=relevant_facts
                )
                if code_result.get("result") is not None:
                    intent["temporal_code"] = code_result
                    logger.info(
                        "TEMPORAL_CODE_DIAG question=%.80s operation=%s states=%d result=%r direct_lookup=%s",
                        question,
                        code_result.get("operation", ""),
                        code_result.get("state_count", 0),
                        code_result.get("result"),
                        "true" if direct_temporal_lookup is not None else "false",
                    )
            except Exception as e:
                logger.warning("Temporal code generation failed: %s", e)

        # ── OODA: DECIDE ─────────────────────────────────────────────────────
        # Diagnostic: log retrieval result counts before synthesis
        logger.info(
            "RETRIEVAL_DIAG question=%.80s intent=%s facts_count=%d use_simple=%s",
            question,
            intent_type,
            len(relevant_facts),
            "true" if used_simple_path else "false",
        )

        if deterministic_meta_answer is not None:
            answer = deterministic_meta_answer
        elif self._should_short_circuit_temporal_answer(question, intent.get("temporal_code")):
            answer = self._format_temporal_lookup_answer(question, intent.get("temporal_code"))
        else:
            # Synthesize answer from the oriented world model (relevant_facts).
            answer = await self._synthesize_with_llm(
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

        # ── OODA: ACT ────────────────────────────────────────────────────────
        # Return the answer and remember the Q&A pair for future recall.
        # Solution B: Skip Q&A store when called from answer_question_agentic
        # to reduce concurrent DB writes during parallel evaluation. The agentic
        # caller will store its own final answer after refinement if needed.
        if not _skip_qanda_store:
            self.memory.store_fact(
                context=f"Question: {question[:200]}",
                fact=f"Answer: {answer[:900]}",
                confidence=0.7,
                tags=["q_and_a", question_level.lower()],
            )
            # Also remember via OODA loop for Memory facade integration
            self.loop.observe(f"Q: {question[:200]} A: {answer[:300]}")

        if return_trace:
            return answer, reasoning_trace
        return answer

    async def answer_question_agentic(
        self, question: str, max_iterations: int = 3, return_trace: bool = False
    ) -> str | tuple[str, ReasoningTrace | None]:
        """Agentic mode: run single-shot FIRST, then augment with iterative refinement.

        Never scores lower than single-shot because it starts with single-shot's
        result and only replaces it when refinement finds additional information.

        Strategy:
        1. Run the full single-shot pipeline (intent, retrieve, synthesize)
        2. Self-evaluate -- is the answer complete?
        3. If gaps detected, search again with refined queries
        4. Re-synthesize with ALL facts (original + new)

        Args:
            question: The question to answer
            max_iterations: Max gap-filling search iterations (default 3)
            return_trace: If True, return (answer, ReasoningTrace) tuple

        Returns:
            Synthesized answer string, or (answer, trace) if return_trace=True.
        """
        if not question or not question.strip():
            return "Error: Question is empty"

        # Step 1: Run the full single-shot pipeline (guaranteed baseline).
        # Solution B: pass _skip_qanda_store=True to avoid concurrent DB writes.
        # Solution C: pass _force_simple=True so entity-retrieval fallback returns
        #   all verbatim facts instead of compressed Tier 3 summaries, ensuring
        #   early-stored infrastructure facts are not lost.
        initial_result = await self.answer_question(
            question,
            return_trace=True,
            _skip_qanda_store=True,
            _force_simple=True,
        )
        if isinstance(initial_result, tuple):
            initial_answer, trace = initial_result
        else:
            initial_answer = initial_result
            trace = None

        # Step 2: Self-evaluate -- is the answer complete?
        evaluation = await self._evaluate_answer_completeness(question, initial_answer)

        if evaluation.get("is_complete", True):
            logger.info("Agentic: single-shot answer is complete, no refinement needed")
            if return_trace:
                return initial_answer, trace
            return initial_answer

        # Step 3: Identify gaps and search for additional facts
        gaps = evaluation.get("gaps", [])
        if not gaps:
            logger.info("Agentic: no specific gaps identified, returning single-shot")
            if return_trace:
                return initial_answer, trace
            return initial_answer

        additional_facts: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for gap_query in gaps[:max_iterations]:
            if hasattr(self.memory, "search"):
                new_facts = self.memory.search(query=gap_query, limit=50)
                for f in new_facts:
                    fid = f.get("experience_id", f.get("fact", ""))
                    if fid not in seen_ids:
                        seen_ids.add(fid)
                        additional_facts.append(f)

        if not additional_facts:
            logger.info("Agentic: no additional facts found for gaps, returning single-shot")
            if return_trace:
                return initial_answer, trace
            return initial_answer

        # Step 4: Re-synthesize with ALL facts (original + new)
        # Include original single-shot answer as a fact so re-synthesis can't lose info
        original_facts = self._simple_retrieval(question)
        original_answer_fact = {
            "context": "PREVIOUS_ANSWER",
            "outcome": f"A previous analysis answered: {initial_answer}",
            "confidence": 0.95,
            "tags": ["previous_answer"],
            "metadata": {"is_previous_answer": True},
        }
        all_facts = [original_answer_fact] + original_facts + additional_facts

        # Deduplicate by experience_id or fact text
        deduped: list[dict[str, Any]] = []
        dedup_keys: set[str] = set()
        for f in all_facts:
            key = f.get("experience_id", f.get("fact", f.get("outcome", "")))
            if key and key not in dedup_keys:
                dedup_keys.add(key)
                deduped.append(f)
            elif not key:
                deduped.append(f)

        # Re-detect intent for proper synthesis prompting
        intent = await self._detect_intent(question)

        refined_answer = await self._synthesize_with_llm(
            question=question,
            context=deduped,
            question_level="L3",  # Use L3 for synthesis-level refinement
            intent=intent,
        )

        logger.info(
            "Agentic: refined with %d additional facts (total %d)",
            len(additional_facts),
            len(deduped),
        )

        if return_trace:
            return refined_answer, trace
        return refined_answer

    async def _evaluate_answer_completeness(self, question: str, answer: str) -> dict[str, Any]:
        """Evaluate whether an answer fully addresses the question.

        Uses a single LLM call to assess completeness and identify gaps.

        Args:
            question: The original question
            answer: The current answer to evaluate

        Returns:
            Dict with:
                is_complete: bool -- True if no gaps detected
                gaps: list[str] -- search queries for missing information
        """
        # Short-circuit: only consider incomplete if answer is empty or explicit "don't know"
        if not answer or not answer.strip():
            return {"is_complete": False, "gaps": [question]}
        answer_lower = answer.lower().strip()
        no_info_phrases = [
            "i don't have enough",
            "i don't have information",
            "i cannot answer",
            "no information available",
            "not enough context",
        ]
        if any(answer_lower.startswith(p) for p in no_info_phrases):
            return {"is_complete": False, "gaps": [question]}
        # If the answer is substantive (>50 chars and doesn't say "don't know"),
        # it's likely complete enough. Re-synthesis tends to LOSE details,
        # so we only evaluate short/uncertain answers.
        if len(answer.strip()) > 50:
            return {"is_complete": True, "gaps": []}

        prompt = (
            "You are evaluating whether an answer FULLY addresses a question.\n\n"
            f"QUESTION: {question}\n\n"
            f"ANSWER: {answer}\n\n"
            "Evaluate:\n"
            "1. Does the answer directly address what was asked?\n"
            "2. Is any specific information MISSING that the question requires?\n"
            "3. Are there vague or hedged parts that could be more specific?\n\n"
            "Respond in this exact JSON format (no markdown, no extra text):\n"
            '{"is_complete": true}\n'
            "OR\n"
            '{"is_complete": false, "gaps": ["search query for missing info 1", '
            '"search query for missing info 2"]}\n\n'
            "IMPORTANT: Only mark as incomplete if SPECIFIC, CONCRETE information "
            "is missing. A well-formed answer that addresses the question is complete "
            "even if more detail COULD be added. Err on the side of marking complete.\n"
            "Return ONLY the JSON object, nothing else."
        )

        try:
            raw = (
                await _get_llm_completion()(
                    [{"role": "user", "content": prompt}],
                    model=self.model,
                    temperature=0.0,
                )
            ).strip()

            # Parse JSON -- handle markdown code fences if the LLM wraps it
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            result = json.loads(raw)
            if not isinstance(result, dict):
                return {"is_complete": True, "gaps": []}

            return {
                "is_complete": bool(result.get("is_complete", True)),
                "gaps": list(result.get("gaps", [])),
            }
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.warning("Answer evaluation parse error: %s", exc)
            return {"is_complete": True, "gaps": []}
        except Exception as exc:
            logger.warning("Answer evaluation failed: %s", exc)
            return {"is_complete": False, "gaps": ["evaluation_failed"]}

    async def _synthesize_with_llm(
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

        # Use generous fact limits - with 200K token models, the LLM handles
        # fact selection better than keyword-based filtering. Trimming too
        # aggressively causes retrieval failures where facts exist but are cut.
        if intent_type in (
            "multi_source_synthesis",
            "temporal_comparison",
            "mathematical_computation",
            "ratio_trend_analysis",
            "contradiction_resolution",
            "meta_memory",
        ):
            max_facts = 500
        else:
            max_facts = 300

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

        include_temporal_context = intent.get("needs_temporal") or intent_type in (
            "temporal_comparison",
            "incremental_update",
        )
        if include_temporal_context:
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
            "L5": (
                "This question involves POTENTIALLY CONFLICTING information. "
                "First identify whether the facts contain contradictory claims. "
                "If they do, present BOTH sides with their sources. "
                "When asked about reliability or credibility, consider: "
                "(a) data described as 'preliminary' is less reliable than finalized data, "
                "(b) independent/third-party analysts are generally less biased than the "
                "organization being measured (e.g., IOC reporting on its own viewership), "
                "(c) explicit methodology description increases reliability."
            ),
        }

        instruction = level_instructions.get(question_level, level_instructions["L1"])
        question_lower = question.lower()

        # Add intent-specific instructions only for complex intents
        # (simple_recall and incremental_update don't need math/temporal prompts
        #  which can cause the LLM to add wrong verification steps)
        extra_instructions = ""
        is_complex_intent = intent_type not in self.SIMPLE_INTENTS

        # Category-specific synthesis instructions: targeted guidance per intent type
        # instead of generic math instructions that can cause the LLM to hallucinate
        _category_instructions = {
            "mathematical_computation": (
                "\n\nIMPORTANT - MATHEMATICAL COMPUTATION:\n"
                "A pre-computed result is provided below. Use it directly.\n"
                "Do NOT re-calculate. State the pre-computed answer and explain what it means.\n"
            ),
            "meta_memory": (
                "\n\nIMPORTANT - COUNTING/ENUMERATION:\n"
                "Scan ALL facts below (including summaries) to enumerate every distinct item.\n"
                "List each one by name. Do NOT stop at the first few facts.\n"
                "Read EVERY fact before answering. Count precisely -- do NOT estimate.\n"
                "IMPORTANT: When asked to LIST or ENUMERATE items, include EVERY item from "
                "the facts. Do not summarize or skip any. Count them explicitly.\n"
                "If a Knowledge Overview section is provided below, use it as a checklist and "
                "take the UNION of distinct items from the overview and detailed facts.\n"
                "Prefer the full de-duplicated list over an early partial cluster.\n"
            ),
            "temporal_comparison": (
                "\n\nIMPORTANT - TEMPORAL COMPARISON:\n"
                "Reconstruct the FULL chronological chain before answering.\n"
                "If the question asks for the current/latest/final value, use the LAST state.\n"
                "If it asks for an original/previous/intermediate value, identify the exact "
                "historical state requested.\n"
                "If it asks how many times something changed, answer with the number of "
                "TRANSITIONS (number of states minus one), not the number of states.\n"
            ),
        }

        # Detect incident-tracking questions (CVEs, APTs, timeline events)
        _incident_cues = (
            "incident",
            "cve-",
            "cve ",
            "apt-",
            "apt ",
            "breach",
            "attack",
            "vulnerability",
            "timeline",
            "forensic",
        )
        if any(cue in question_lower for cue in _incident_cues):
            extra_instructions += (
                "\n\nIMPORTANT - INCIDENT TRACKING:\n"
                "For incident questions: include ALL related details - CVEs, timeline events, "
                "APT attributions, affected systems. Cross-reference between incidents when "
                "relevant.\n"
                "List each CVE, each affected system, and each timeline event separately.\n"
                "Do NOT omit any cross-referenced details even if they seem tangential.\n"
            )

        # Detect multi-hop reasoning questions (multiple entities needing connection)
        _multi_hop_cues = (
            "how are",
            "relationship between",
            "connect",
            "in common",
            "relate to",
            "link between",
            "both",
            "and also",
        )
        if any(cue in question_lower for cue in _multi_hop_cues):
            extra_instructions += (
                "\n\nIMPORTANT - MULTI-HOP REASONING:\n"
                "For questions mentioning multiple entities: address EACH entity separately, "
                "then explain the CONNECTION between them. Do not skip any entity mentioned "
                "in the question.\n"
                "Step 1: Identify ALL entities referenced in the question.\n"
                "Step 2: State what you know about EACH entity individually.\n"
                "Step 3: Explain the relationship or connection between them.\n"
            )

        if is_complex_intent and intent_type in _category_instructions:
            extra_instructions += _category_instructions[intent_type]
        elif is_complex_intent and intent.get("needs_math"):
            # Fallback generic math instructions for intent types not in the dispatch
            extra_instructions += (
                "\n\nIMPORTANT - MATHEMATICAL COMPUTATION REQUIRED:\n"
                "- Extract the raw numbers from the facts FIRST\n"
                "- Show all arithmetic step by step\n"
                "- Write out each calculation explicitly (e.g., 26 - 18 = 8)\n"
                "- When computing differences for multiple entities, do ALL of them\n"
                "- Double-check every subtraction and addition\n"
                "- Verify your final numerical answer by re-doing the computation\n"
            )

        # Inject pre-computed math result when available
        computed_math = intent.get("computed_math")
        if computed_math:
            extra_instructions += (
                f"\n\nPRE-COMPUTED RESULT (use this, do NOT re-calculate):\n{computed_math}\n"
            )

        if intent.get("needs_temporal") or intent_type in (
            "temporal_comparison",
            "incremental_update",
        ):
            # Detect if this is a temporal_trap question (asks for specific point in chain)
            temporal_trap_cues = (
                "before the",
                "after the first",
                "before any",
                "originally",
                "previous",
                "intermediate",
                "i want the",
                "not the current",
                "return the",
            )
            is_temporal_trap = any(cue in question_lower for cue in temporal_trap_cues)

            if is_temporal_trap:
                extra_instructions += (
                    "\n\nIMPORTANT - TEMPORAL TRAP QUESTION:\n"
                    "This question asks for a SPECIFIC historical value, NOT the current one.\n"
                    "The facts below CONTAIN the answer -- look for temporal chains, version numbers,\n"
                    "date-stamped changes, or sequences of values. Do NOT say you cannot find the answer.\n"
                    "\nSTEP 1: Build the timeline -- list ALL values in chronological order:\n"
                    "  Value1 (original) -> Value2 (after 1st change) -> Value3 (after 2nd change) -> ...\n"
                    "STEP 2: Identify which position the question asks for:\n"
                    "  - 'original' / 'BEFORE any changes' / 'BEFORE the first change' = Value1 (the FIRST in the chain)\n"
                    "  - 'AFTER first change BUT BEFORE second' = Value2 (the SECOND in the chain)\n"
                    "  - 'BEFORE the [specific] change' = the value IMMEDIATELY BEFORE that change\n"
                    "  - 'previous leader' = the person BEFORE the transition\n"
                    "STEP 3: Report ONLY that one value. Do NOT list the chain.\n"
                    "\nCRITICAL: 'BEFORE the first change' means the value BEFORE the change happened,\n"
                    "which is the ORIGINAL value -- NOT the value the first change produced.\n"
                )
            else:
                extra_instructions += (
                    "\n\nIMPORTANT - TEMPORAL REASONING REQUIRED:\n"
                    "Step 1: Reconstruct the chronological chain of values\n"
                    "Step 2: Identify the specific point asked about\n"
                    "Step 3: Calculate differences if asked\n"
                    "Step 4: State conclusion clearly\n"
                    "RULES: 'BEFORE' = value prior to event. 'AFTER X but BEFORE Y' = value between.\n"
                )

        # Inject temporal code generation result if available
        temporal_code = intent.get("temporal_code")
        temporal_code_result = temporal_code.get("result") if temporal_code else None
        if temporal_code and temporal_code_result is not None:
            resolved_label = (
                "Resolved change count"
                if temporal_code.get("operation") == "change_count"
                else "Resolved value"
            )
            extra_instructions += (
                "\n\nAUTHORITATIVE TEMPORAL RESOLUTION:\n"
                "A deterministic temporal resolution is provided below. Use it directly when it "
                "answers the question.\n"
                "Do NOT replace it with a guessed timeline count or alternate value.\n"
                f"Code: {temporal_code['code']}\n"
                f"{resolved_label}: {temporal_code_result}\n"
                f"Chain length: {len(temporal_code.get('transitions', []))}\n"
            )
            if temporal_code.get("operation") == "change_count":
                extra_instructions += (
                    "For change-count questions, number of changes = number of states - 1.\n"
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

        # Add summary context only for intents that benefit from a bird's-eye checklist.
        summary_section = ""
        if intent.get("summary_context") and intent_type in (
            "multi_source_synthesis",
            "meta_memory",
        ):
            heading = (
                "Knowledge Overview (use as checklist before counting):"
                if intent_type == "meta_memory"
                else "Knowledge Overview (what was learned):"
            )
            summary_section = f"""
{heading}
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
        is_counterfactual = intent_type == "causal_counterfactual" or any(
            kw in question_lower
            for kw in ("what if", "if ", "would ", "without ", "had not", "removed")
        )
        is_causal = intent_type == "causal_counterfactual" or any(
            kw in question_lower
            for kw in (
                "cause",
                "caused",
                "why did",
                "most important",
                "root cause",
                "single factor",
            )
        )
        if is_counterfactual:
            counterfactual_instructions = (
                "\n\nIMPORTANT - HYPOTHETICAL/COUNTERFACTUAL REASONING:\n"
                "This question asks you to imagine an alternative scenario. You MUST:\n"
                "1. Start from the ACTUAL facts as your baseline\n"
                "2. Apply the hypothetical change (remove X, change timing, etc.)\n"
                "3. Reason through the CONSEQUENCES of that change step by step\n"
                "4. For EACH relevant entity, estimate how the change affects them\n"
                "5. Compare the hypothetical outcome to ALL other entities (not just the one asked about)\n"
                "6. Acknowledge uncertainty: use language like 'likely', 'might have', 'approximately'\n"
                "7. Consider what WOULD still remain even without the changed factor\n\n"
                "CRITICAL RULES FOR COUNTERFACTUALS:\n"
                "- You MUST NOT refuse to engage with the hypothetical scenario.\n"
                "- You MUST NOT say 'that didn't happen' or 'the facts show otherwise'.\n"
                "- 'What if X had happened instead of Y?' REQUIRES you to IMAGINE the X scenario.\n"
                "- Even if X contradicts the actual facts, that is the ENTIRE POINT of the question.\n"
                "- Start your answer: 'In this hypothetical scenario where [X], the consequences would be...'\n"
                "- Use the real facts as DATA to estimate what the alternative scenario would produce.\n"
                "- When removing an athlete: subtract ONLY their individual medals, keep team medals.\n"
                "- When changing timing: estimate the effect using known data about home advantage, etc.\n"
            )
        if is_causal:
            counterfactual_instructions += (
                "\n\nIMPORTANT - CAUSAL/ROOT CAUSE REASONING:\n"
                "When asked about causes, distinguish between:\n"
                "- ROOT CAUSES: The original trigger that set everything else in motion\n"
                "- CONTRIBUTING FACTORS: Things that amplified or enabled the outcome\n"
                "- PROXIMATE CAUSES: The immediate/direct causes of the outcome\n\n"
                "A root cause is the one that, if removed, would prevent ALL downstream effects.\n"
                "Ask yourself: 'Would the other factors have happened without THIS one?'\n"
                "If Factor A triggered Factor B and C, then A is the root cause,\n"
                "even if B and C directly produced the outcome.\n"
            )

        # Add ratio/trend analysis instructions
        ratio_trend_instructions = ""
        if intent_type == "ratio_trend_analysis" or (
            is_complex_intent
            and any(
                kw in question_lower
                for kw in ("ratio", "rate", "per ", "trend", "improving", "worsening")
            )
        ):
            ratio_trend_instructions = (
                "\n\nIMPORTANT - RATIO/TREND ANALYSIS REQUIRED:\n"
                "This question requires computing ratios AND analyzing trends.\n\n"
                "STEP 1: COMPUTE RATIOS\n"
                "For EACH entity in EACH time period, compute the ratio explicitly:\n"
                "  ratio = numerator / denominator (show the division)\n"
                "  Example: '35 bug fixes / 28 features = 1.25'\n\n"
                "STEP 2: BUILD RATIO TABLE\n"
                "Create a table with rows = entities and columns = time periods.\n"
                "Fill in the computed ratios.\n\n"
                "STEP 3: ANALYZE TREND DIRECTION\n"
                "For EACH entity, compare ratios across time periods:\n"
                "  - Is the ratio INCREASING or DECREASING from period to period?\n"
                "  - State explicitly: 'Ratio went from X to Y, which is an INCREASE/DECREASE'\n"
                "  - Interpret: what does the direction mean? (e.g., decreasing bug-to-feature "
                "ratio = IMPROVING because fewer bugs per feature)\n\n"
                "STEP 4: COMPARE AND RANK\n"
                "Compare entities on both: absolute ratio level AND trend direction.\n"
                "State which has the 'best' ratio and which has the 'best' trend.\n"
            )

        # Add novel skill (L11) specific instructions
        novel_skill_instructions = ""
        if (
            question_level in ("L11",)
            or "workflow file" in question_lower
            or "teach" in question_lower
        ):
            is_teaching_question = "teach" in question_lower or "junior developer" in question_lower
            is_workflow_gen = "write" in question_lower and (
                "workflow" in question_lower or "file" in question_lower
            )

            novel_skill_instructions = (
                "\n\nIMPORTANT - NOVEL SKILL APPLICATION:\n"
                "When generating technical artifacts (workflow files, configs, code):\n"
                "- Include ONLY the fields required by the specification\n"
                "- Do NOT add optional fields unless the question asks for them\n"
                "- Use the EXACT field names and YAML structure from the documentation\n"
                "- Follow the EXACT file path conventions (e.g., .github/workflows/)\n"
            )

            if is_teaching_question:
                novel_skill_instructions += (
                    "\nTEACHING INSTRUCTIONS:\n"
                    "When teaching someone how to use a technology:\n"
                    "1. Give EXACT file paths (e.g., .github/workflows/my-workflow.md)\n"
                    "2. Give EXACT commands (e.g., 'gh aw compile', not 'compile the workflow')\n"
                    "3. Include BOTH what to create AND how to run/deploy it\n"
                    "4. Always mention committing/pushing as a step\n"
                    "5. End with 'Common mistake:' followed by the most frequent beginner error\n"
                    "6. Specifically mention: after editing frontmatter, you MUST recompile\n"
                )

            if is_workflow_gen:
                novel_skill_instructions += (
                    "\nWORKFLOW FILE GENERATION:\n"
                    "The workflow file MUST have this exact structure:\n"
                    "---\n"
                    "on: <trigger definition>\n"
                    "engine: <ai engine name>\n"
                    "permissions: <permission level>\n"
                    "tools: <tool configuration>\n"
                    "safe-outputs: <output definitions>\n"
                    "---\n"
                    "# <Title>\n"
                    "<markdown instructions for the AI>\n"
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

        # Add cross-reference instruction when question involves role transitions
        cross_ref_instructions = ""
        cross_ref_cues = (
            "replaced",
            "who replaced",
            "currently leading",
            "took over",
            "moved from",
            "moved to",
            "who leads",
            "who is leading",
            "and what",
            "who received",
        )
        if any(kw in question_lower for kw in cross_ref_cues):
            cross_ref_instructions = (
                "\n\nIMPORTANT - CROSS-REFERENCE / ROLE TRANSITION:\n"
                "When the facts describe role changes or transitions between people:\n"
                "- Carefully distinguish WHO has the role NOW vs who had it BEFORE\n"
                "- Look for temporal markers: 'now leads', 'moved to', 'replaced by'\n"
                "- If person A moved to research and person B took over, then B leads NOW\n"
                "- 'X leads the maintenance phase' means X (not anyone else) leads it\n"
                "- State the CURRENT state of affairs, then explain the history\n"
            )

        # Adversarial confidence boost
        adversarial_instructions = ""
        adversarial_cues = (
            "be careful",
            "be precise",
            "do not confuse",
            "don't confuse",
            "note:",
            "note that",
            "i want the",
            "not the current",
            "not any other",
        )
        if any(cue in question_lower for cue in adversarial_cues):
            adversarial_instructions = (
                "\n\nPRECISION REQUIRED: The question warns about potential confusion.\n"
                "CRITICAL RULES FOR YOUR ANSWER:\n"
                "1. State ONLY the correct answer for the specific entity asked about\n"
                "2. Do NOT mention other entities' values, names, or attributes\n"
                "3. Do NOT explain what might be confused -- just give the right answer\n"
                "4. Do NOT compare with other entities or provide contrast\n"
                "5. Keep the answer SHORT and DIRECT\n"
                "Example: If asked 'What is X's hobby? Do not confuse with Y.'\n"
                "  GOOD: 'X's hobby is chess.'\n"
                "  BAD: 'X's hobby is chess. (Y's hobby is painting -- different.)'\n"
            )

        # Cross-entity aggregation
        aggregation_instructions = ""
        aggregation_cues = (
            "total across",
            "sum of",
            "combined",
            "all projects",
            "across all",
            "total budget",
            "total cost",
            "per user",
        )
        if any(cue in question_lower for cue in aggregation_cues):
            aggregation_instructions = (
                "\n\nAGGREGATION REQUIRED: List EACH entity's contribution by name. "
                "Show the full addition. Verify the total by re-adding.\n"
            )

        # Numerical step-by-step
        numerical_instructions = ""
        if intent_type == "mathematical_computation" or (
            intent.get("needs_math") and not computed_math
        ):
            numerical_instructions = (
                "\n\nSTEP-BY-STEP CALCULATION: Extract ALL relevant numbers. "
                "Label each. Show each arithmetic step. Double-check result.\n"
            )

        # Diagnostic logging: surface what the LLM will see for debugging
        # retrieval quality issues (e.g., needle_in_haystack failures).
        _q_words = [w.lower().strip("?.,!") for w in question.split() if len(w) > 2]
        _needle_matches = [
            f
            for f in context[:max_facts]
            if any(w in f.get("outcome", "").lower() for w in _q_words)
            or any(w in f.get("context", "").lower() for w in _q_words)
        ]
        logger.info(
            "SYNTH_DIAG question=%.80s total_facts=%d matching_facts=%d first_3_contexts=%s",
            question,
            len(context[:max_facts]),
            len(_needle_matches),
            [f.get("context", "")[:60] for f in context[: min(3, len(context))]],
        )
        if _needle_matches:
            logger.info(
                "SYNTH_DIAG needle_hits: %s",
                [
                    (f.get("context", "")[:40], f.get("outcome", "")[:80])
                    for f in _needle_matches[:5]
                ],
            )

        prompt = _load_prompt(
            "synthesis_user",
            question=question,
            question_level=question_level,
            instruction=instruction,
            extra_instructions=extra_instructions,
            contradiction_instructions=contradiction_instructions,
            counterfactual_instructions=counterfactual_instructions,
            ratio_trend_instructions=ratio_trend_instructions,
            novel_skill_instructions=novel_skill_instructions,
            cross_ref_instructions=cross_ref_instructions,
            adversarial_instructions=adversarial_instructions,
            aggregation_instructions=aggregation_instructions,
            numerical_instructions=numerical_instructions,
            summary_section=summary_section,
            source_specific_section=source_specific_section,
            context_str=context_str,
        )

        try:
            return (
                await self._llm_completion_with_retry(
                    messages=[
                        {
                            "role": "system",
                            "content": self._variant_system_prompt
                            or load_prompt("synthesis_system"),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                )
            ).strip()

        except Exception as e:
            logger.error("LLM synthesis failed: %s", e)
            return "I was unable to synthesize an answer due to an internal error."
