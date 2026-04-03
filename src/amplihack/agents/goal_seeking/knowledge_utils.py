from __future__ import annotations

"""Arithmetic validation, entity helpers, fact extraction utilities."""

import json
import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from .action_executor import calculate
from .prompt_utils import _get_llm_completion, _load_prompt
from .prompts import load_prompt

logger = logging.getLogger(__name__)


class KnowledgeUtilsMixin:
    """Mixin providing knowledge utilities for LearningAgent."""

    # Person and project detection constants
    _PERSON_DETAIL_CUES = (
        "allerg",
        "birthday",
        "degree",
        "favorite food",
        "hobby",
        "hometown",
        "personal information",
        "pet",
        "team",
    )
    _NON_PERSON_NAME_TOKENS = frozenset(
        {
            "affected",
            "allergies",
            "allergy",
            "award",
            "birthday",
            "center",
            "city",
            "climate",
            "competitor",
            "computer",
            "customer",
            "daily",
            "data",
            "database",
            "development",
            "difference",
            "discrepancy",
            "educational",
            "engineering",
            "estimate",
            "experience",
            "facilities",
            "favorite",
            "food",
            "framework",
            "gartner",
            "hiring",
            "hobby",
            "hometown",
            "incident",
            "indicators",
            "information",
            "innovation",
            "internal",
            "island",
            "market",
            "marketing",
            "migration",
            "nationality",
            "newsletter",
            "personnel",
            "personal",
            "pet",
            "pets",
            "preference",
            "product",
            "professional",
            "production",
            "project",
            "report",
            "rhode",
            "school",
            "security",
            "segment",
            "senior",
            "size",
            "sprint",
            "success",
            "satisfaction",
            "team",
            "threat",
            "user",
            "vulnerability",
        }
    )
    _NON_PROJECT_NAMES = frozenset(
        {
            "assignment",
            "framework",
            "identity",
            "lead",
            "leadership",
            "management",
            "new",
            "overview",
            "status",
            "type",
        }
    )

    _PERSON_NAME_PART_PATTERN = re.compile(r"^[A-Z][a-z]*(?:['\u2019\-][A-Z]?[a-z]+)?$")
    _PERSON_NAME_FRAGMENT = (
        r"[A-Z][a-z]*(?:['\u2019\-][A-Z]?[a-z]+)?"
        r"\s+[A-Z][a-z]*(?:['\u2019\-][A-Z]?[a-z]+)?"
    )
    _PERSON_NAME_PATTERN = re.compile(rf"\b({_PERSON_NAME_FRAGMENT})\b")
    _PERSON_ATTRIBUTE_PATTERNS = (
        re.compile(
            rf"\b({_PERSON_NAME_FRAGMENT})(?:'s|\u2019s)\s+"
            r"(?:birthday|favorite food|degree|hobby|hometown|pet|team|allerg(?:y|ies)|nationality)\b"
        ),
        re.compile(rf"\b({_PERSON_NAME_FRAGMENT})\s+(?:has|holds|is)\b"),
    )
    _PROJECT_NAME_PATTERNS = (re.compile(r"\bProject\s+([A-Z][A-Za-z0-9_-]+)\b"),)

    # APT attribution constants
    _APT_ATTRIBUTION_SEARCH_TERMS = ("threat attribution", "matched APT", "TTPs matched")
    _APT_ATTRIBUTION_HINT_TERMS = (
        "development infrastructure",
        "event-stream",
        "supply chain",
        "dns tunneling",
        "xz-utils",
    )
    _APT_ATTRIBUTION_FACT_CUES = (
        "apt",
        "attribution",
        "development infrastructure",
        "threat actor",
        "ttp",
    )
    _APT_ATTRIBUTION_FACT_SCAN_LIMIT = 50
    _APT_ATTRIBUTION_MAX_ENTITY_IDS = 3
    _APT_ATTRIBUTION_MAX_SEARCH_TERMS = 6
    _APT_ATTRIBUTION_SEARCH_LIMIT = 50

    @staticmethod
    def _format_distinct_item_list(items: list[str]) -> str:
        if not items:
            return ""
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return f"{items[0]} and {items[1]}"
        return f"{', '.join(items[:-1])}, and {items[-1]}"

    @staticmethod
    def _normalize_person_name(candidate: str) -> str:
        candidate = " ".join(candidate.split()).strip()
        return re.sub(r"(?:'s|\u2019s)\b", "", candidate).strip()

    def _looks_like_person_name(self, candidate: str) -> bool:
        candidate = self._normalize_person_name(candidate)
        if not candidate or any(ch.isdigit() for ch in candidate):
            return False
        parts = candidate.split()
        if len(parts) != 2:
            return False
        return all(
            self._PERSON_NAME_PART_PATTERN.match(part)
            and part.casefold() not in self._NON_PERSON_NAME_TOKENS
            for part in parts
        )

    def _looks_like_project_name(self, candidate: str) -> bool:
        candidate = candidate.strip(".,;:!?()[]{}\"'")
        if not candidate or any(ch.isspace() for ch in candidate):
            return False
        return candidate.casefold() not in self._NON_PROJECT_NAMES

    def _extract_personal_detail_people(self, facts: list[dict[str, Any]]) -> list[str]:
        people: dict[str, str] = {}
        personal_texts: list[str] = []

        for fact in facts:
            text = f"{fact.get('context', '')} {fact.get('outcome', fact.get('fact', ''))}"
            if not any(cue in text.lower() for cue in self._PERSON_DETAIL_CUES):
                continue
            personal_texts.append(text)
            for pattern in self._PERSON_ATTRIBUTE_PATTERNS:
                for match in pattern.findall(text):
                    cleaned = self._normalize_person_name(match)
                    if self._looks_like_person_name(cleaned):
                        people.setdefault(cleaned.casefold(), cleaned)

        if people:
            return [people[key] for key in sorted(people)]

        for text in personal_texts:
            for match in self._PERSON_NAME_PATTERN.findall(text):
                cleaned = self._normalize_person_name(match)
                if self._looks_like_person_name(cleaned):
                    people.setdefault(cleaned.casefold(), cleaned)

        return [people[key] for key in sorted(people)]

    def _extract_project_names(self, facts: list[dict[str, Any]]) -> list[str]:
        context_projects: dict[str, str] = {}
        outcome_projects: dict[str, str] = {}
        outcome_counts: dict[str, int] = {}
        for fact in facts:
            context_text = fact.get("context", "")
            outcome_text = fact.get("outcome", fact.get("fact", ""))
            for pattern in self._PROJECT_NAME_PATTERNS:
                for match in pattern.findall(context_text):
                    cleaned = match.strip(".,;:!?()[]{}\"'")
                    if not self._looks_like_project_name(cleaned):
                        continue
                    context_projects.setdefault(cleaned.casefold(), cleaned)

                for match in pattern.findall(outcome_text):
                    cleaned = match.strip(".,;:!?()[]{}\"'")
                    if not self._looks_like_project_name(cleaned):
                        continue
                    key = cleaned.casefold()
                    outcome_projects.setdefault(key, cleaned)
                    outcome_counts[key] = outcome_counts.get(key, 0) + 1

        projects = dict(context_projects)
        for key, value in outcome_projects.items():
            if key in projects or outcome_counts.get(key, 0) >= 2:
                projects.setdefault(key, value)

        return [projects[key] for key in sorted(projects)]

    @classmethod
    def _facts_contain_specific_apt(cls, facts: list[dict[str, Any]]) -> bool:
        return any(
            re.search(
                r"\bapt(?:-| )?\d+\b",
                f"{fact.get('context', '')} {fact.get('outcome', fact.get('fact', ''))}",
                re.IGNORECASE,
            )
            for fact in facts
        )

    @staticmethod
    def _is_apt_attribution_question(question: str) -> bool:
        question_lower = question.lower()
        return "apt" in question_lower and any(
            cue in question_lower for cue in ("attributed", "group", "threat actor")
        )

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

    async def _compute_math_result(
        self, question: str, facts: list[dict[str, Any]], intent: dict[str, Any]
    ) -> str | None:
        """Pre-compute a math result from facts using LLM extraction + safe eval.

        Uses the LLM to extract relevant numbers from facts and build an
        arithmetic expression, then evaluates it with the AST-based calculator.
        This avoids relying on the LLM to do arithmetic correctly during synthesis.

        Args:
            question: The user's question
            facts: Retrieved fact dicts
            intent: Intent classification dict (must have needs_math=True)

        Returns:
            A string like "COMPUTED: (2.3 - 2.0) / 2.0 * 100 = 15.0 (percentage)"
            or None if extraction/computation fails.
        """
        math_type = intent.get("math_type", "none")
        facts_text = "\n".join(f"- {f.get('outcome', f.get('fact', ''))}" for f in facts[:120])

        prompt = _load_prompt(
            "number_extraction_user",
            question=question,
            math_type=math_type,
            facts_text=facts_text,
        )

        try:
            response_text = (
                await _get_llm_completion()(
                    [
                        {
                            "role": "system",
                            "content": load_prompt("number_extraction_system"),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    model=self.model,
                    temperature=0.0,
                )
            ).strip()

            # Parse JSON response
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    result = json.loads(response_text[json_start:json_end].strip())
                else:
                    return None

            expression = result.get("expression", "").strip()
            description = result.get("description", "")

            if not expression:
                return None

            calc = calculate(expression)
            if calc.get("error") or calc.get("result") is None:
                logger.debug("Math computation failed: %s", calc.get("error"))
                return None

            value = calc["result"]
            # Format nicely: use int when result is whole number
            formatted = str(int(value)) if value == int(value) else f"{value:.4g}"

            return f"COMPUTED: {expression} = {formatted} ({description})"

        except Exception as e:
            logger.debug("_compute_math_result failed: %s", e)
            return None

    async def _extract_facts_with_llm(
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
                "\n\nCRITICAL: This content contains step-by-step procedures.\n"
                "You MUST:\n"
                "1. Extract EACH step as a separate fact with its EXACT step number.\n"
                "   Format: 'Step N: [exact action]' (e.g., 'Step 3: flutter create my_app')\n"
                "2. Extract ONE summary fact listing ALL steps in numbered order.\n"
                "   Format: 'Complete workflow: 1) X, 2) Y, 3) Z, 4) W, ...'\n"
                "3. Extract EACH troubleshooting tip as a separate fact.\n"
                "   Format: 'Troubleshooting: If [problem], then [solution]'\n"
                "4. Preserve the EXACT commands mentioned (e.g., 'flutter pub get', not just 'install deps')\n"
            )

        prompt = _load_prompt(
            "fact_extraction_user",
            temporal_hint=temporal_hint,
            procedural_hint=procedural_hint,
            content=content[:2000],
        )

        try:
            response_text = await self._llm_completion_with_retry(
                messages=[
                    {"role": "system", "content": load_prompt("fact_extraction_system")},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )

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

        except Exception as e:
            logger.warning("Fact extraction LLM call failed: %s", e)
            # Fallback: create simple fact from content
            return [
                {
                    "context": "General",
                    "fact": content[:500],
                    "confidence": 0.5,
                    "tags": ["auto_extracted"],
                }
            ]

    def get_memory_stats(self) -> dict[str, Any]:
        """Get statistics about stored knowledge.

        Returns:
            Dictionary with memory statistics
        """
        return self.memory.get_statistics()

    async def _explain_knowledge(self, topic: str, depth: str = "overview") -> str:
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

        prompt = _load_prompt(
            "explanation_user",
            topic=topic,
            depth_instruction=depth_instructions.get(depth, depth_instructions["overview"]),
            facts_text=facts_text,
        )

        try:
            return (
                await _get_llm_completion()(
                    [
                        {"role": "system", "content": load_prompt("explanation_system")},
                        {"role": "user", "content": prompt},
                    ],
                    model=self.model,
                    temperature=0.3,
                )
            ).strip()
        except Exception as e:
            logger.error("Explanation generation failed: %s", e)
            return f"Unable to generate explanation for '{topic}'."

    async def _find_knowledge_gaps(self, topic: str) -> dict[str, Any]:
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

        prompt = _load_prompt("knowledge_gaps_user", topic=topic, facts_text=facts_text)

        gaps = ["Unable to analyze gaps"]
        coverage = "unknown"
        try:
            response_text = await _get_llm_completion()(
                [
                    {"role": "system", "content": load_prompt("knowledge_gaps_system")},
                    {"role": "user", "content": prompt},
                ],
                model=self.model,
                temperature=0.2,
            )
            from .json_utils import parse_llm_json

            result = parse_llm_json(response_text)
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

    async def _verify_fact(self, fact: str) -> dict[str, Any]:
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

        prompt = _load_prompt("verify_fact_user", fact=fact, facts_text=facts_text)

        try:
            response_text = await _get_llm_completion()(
                [
                    {"role": "system", "content": load_prompt("verify_fact_system")},
                    {"role": "user", "content": prompt},
                ],
                model=self.model,
                temperature=0.1,
            )
            from .json_utils import parse_llm_json

            result = parse_llm_json(response_text)
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
