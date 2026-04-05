from __future__ import annotations

"""LLM-driven code generation for temporal queries."""

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from .prompt_utils import _get_llm_completion, _load_prompt
from .prompts import load_prompt

logger = logging.getLogger(__name__)


class CodeSynthesisMixin:
    """Mixin providing code synthesis for LearningAgent."""

    def temporal_code_synthesis(
        self,
        question: str,
        entity: str,
        field: str,
        candidate_facts: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Generate Python code to resolve a temporal question deterministically.

        Produces a code snippet that retrieves the transition chain for
        the entity/field and either indexes into it based on the temporal
        keywords in the question or counts the number of transitions.

        Args:
            question: The temporal question text
            entity: Entity name (e.g., "Atlas project")
            field: Field name (e.g., "deadline")

        Returns:
            Dict with:
                - code: Generated Python code string
                - index_expr: The resolved expression used to answer
                - transitions: The actual transition chain retrieved
                - result: The resolved value (if chain is non-empty)
        """
        question_lower = question.lower()
        change_count_question = (
            "how many times" in question_lower
            or "how many changes" in question_lower
            or "number of changes" in question_lower
        ) and any(
            token in question_lower
            for token in ("change", "changed", "update", "updated", "modification")
        )
        index_expr = (
            "max(0, len(transitions) - 1)"
            if change_count_question
            else self._parse_temporal_index(question)
        )

        # Generate the code snippet
        code_lines = [
            f"transitions = retrieve_transition_chain({entity!r}, {field!r})",
            f"# Temporal index: {index_expr}",
        ]

        # Use safe expression resolution
        if change_count_question:
            code_lines.append(
                f"states = _collapse_change_count_transitions(transitions, {field!r})"
            )
            code_lines.append("# Count transitions after collapsing recap/duplicate states")
            code_lines.append("answer = max(0, len(states) - 1)")
        elif index_expr.startswith("len("):
            code_lines.append("transitions = _collapse_temporal_lookup_transitions(transitions)")
            code_lines.append(f"idx = {index_expr}")
            code_lines.append("answer = transitions[idx].value")
        else:
            code_lines.append("transitions = _collapse_temporal_lookup_transitions(transitions)")
            code_lines.append(f"answer = transitions[{index_expr}].value")

        code = "\n".join(code_lines)

        # Execute the retrieval
        transitions = self.retrieve_transition_chain(entity, field, candidate_facts=candidate_facts)
        effective_transitions = (
            self._collapse_change_count_transitions(transitions, field)
            if change_count_question
            else self._collapse_temporal_lookup_transitions(transitions)
        )
        result = None
        if effective_transitions:
            try:
                # Evaluate the index safely
                if change_count_question:
                    result = max(0, len(effective_transitions) - 1)
                elif index_expr == "-1":
                    latest_state = next(
                        (
                            state
                            for state in reversed(effective_transitions)
                            if not state.get("superseded", False)
                        ),
                        None,
                    )
                    if latest_state is not None:
                        result = latest_state["value"]
                    else:
                        result = effective_transitions[-1]["value"]
                else:
                    if index_expr.startswith("len("):
                        idx = len(effective_transitions) // 2
                    else:
                        idx = int(index_expr)
                    if -len(effective_transitions) <= idx < len(effective_transitions):
                        result = effective_transitions[idx]["value"]
            except (ValueError, IndexError) as e:
                logger.warning("Temporal index resolution failed for %r: %s", index_expr, e)

        return {
            "code": code,
            "index_expr": index_expr,
            "transitions": effective_transitions,
            "result": result,
            "operation": "change_count" if change_count_question else "state_lookup",
            "state_count": len(effective_transitions),
        }

    async def _code_generation_tool(
        self, question: str, candidate_facts: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """Tool interface for temporal code generation.

        Extracts entity and field from the question using LLM, then
        invokes temporal_code_synthesis.

        Args:
            question: The temporal question

        Returns:
            Dict with generated code and result
        """
        heuristic = self._heuristic_temporal_entity_field(question)
        if heuristic is not None:
            entity, field = heuristic
            return self.temporal_code_synthesis(
                question,
                entity,
                field,
                candidate_facts=candidate_facts,
            )

        # Extract entity and field from question using LLM
        prompt = _load_prompt("entity_field_extraction_user", question=question)

        try:
            response_text = (
                await _get_llm_completion()(
                    [
                        {
                            "role": "system",
                            "content": load_prompt("entity_field_extraction_system"),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    model=self.model,
                    temperature=0.0,
                )
            ).strip()
            parsed = json.loads(response_text)
            if isinstance(parsed, dict):
                entity = parsed.get("entity", "").strip()
                field = parsed.get("field", "").strip()
                if not entity or not field:
                    logger.warning("LLM returned empty entity=%r or field=%r", entity, field)
                    return {"code": "", "index_expr": "", "transitions": [], "result": None}
                return self.temporal_code_synthesis(
                    question,
                    entity,
                    field,
                    candidate_facts=candidate_facts,
                )
        except json.JSONDecodeError:
            logger.warning("LLM did not return valid JSON for entity/field extraction")
        except Exception as e:
            logger.warning("Entity/field extraction failed: %s", e)

        return {"code": "", "index_expr": "", "transitions": [], "result": None}
