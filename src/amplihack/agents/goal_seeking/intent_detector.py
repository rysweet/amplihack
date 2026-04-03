from __future__ import annotations

"""Intent detection for classifying questions before synthesis."""

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from .prompt_utils import _get_llm_completion, _load_prompt
from .prompts import load_prompt

logger = logging.getLogger(__name__)


class IntentDetectorMixin:
    """Mixin providing intent detection for LearningAgent."""

    async def _detect_intent(self, question: str) -> dict[str, Any]:
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
        prompt = _load_prompt("intent_classification_user", question=question)

        try:
            response_text = (
                await _get_llm_completion()(
                    [
                        {
                            "role": "system",
                            "content": load_prompt("intent_classification_system"),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    model=self.model,
                    temperature=0.0,
                )
            ).strip()

            try:
                result = json.loads(response_text)
                if isinstance(result, dict):
                    return {
                        "intent": result.get("intent", "simple_recall"),
                        "needs_math": bool(result.get("needs_math", False)),
                        "needs_temporal": bool(result.get("needs_temporal", False)),
                        "math_type": result.get("math_type", "none"),
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
                            "math_type": result.get("math_type", "none"),
                            "reasoning": result.get("reasoning", ""),
                        }
        except Exception as e:
            logger.debug("Intent detection failed: %s", e)

        # Default: simple recall
        return {
            "intent": "simple_recall",
            "needs_math": False,
            "needs_temporal": False,
            "math_type": "none",
            "reasoning": "default",
        }
