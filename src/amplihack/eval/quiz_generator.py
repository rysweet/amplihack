"""Quiz question generator for L1-L4 cognitive levels.

Generates questions at four cognitive levels from news articles:
- L1 (Recall): Direct facts from single source
- L2 (Inference): Reasoning from facts
- L3 (Synthesis): Combining multiple sources
- L4 (Application): Applying to new scenarios

Philosophy: Rule-based generation, deterministic output.
"""

import re
from dataclasses import dataclass

from .multi_source_collector import NewsArticle


@dataclass
class QuizQuestion:
    """Quiz question at a specific cognitive level."""

    question: str
    expected_answer: str
    level: str  # L1, L2, L3, or L4
    source_urls: list[str]


def generate_quiz(
    articles: list[NewsArticle], levels: list[str] | None = None
) -> list[QuizQuestion]:
    """Generate quiz questions from news articles.

    Args:
        articles: List of NewsArticle objects
        levels: Cognitive levels to generate (default: all)

    Returns:
        List of QuizQuestion objects
    """
    if levels is None:
        levels = ["L1", "L2", "L3", "L4"]

    questions = []

    if "L1" in levels:
        questions.extend(_generate_l1_recall(articles))

    if "L2" in levels:
        questions.extend(_generate_l2_inference(articles))

    if "L3" in levels and len(articles) >= 2:
        questions.extend(_generate_l3_synthesis(articles))

    if "L4" in levels:
        questions.extend(_generate_l4_application(articles))

    return questions


def _generate_l1_recall(articles: list[NewsArticle]) -> list[QuizQuestion]:
    """Generate L1 (recall) questions - direct facts."""
    questions = []

    for article in articles[:3]:  # Limit to first 3
        # Extract key entities (simplified - look for capitalized words)
        entities = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", article.content)
        if not entities:
            continue

        # Extract dates
        dates = re.findall(
            r"\b\d{4}-\d{2}-\d{2}\b|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
            article.content,
        )

        # Create recall question about entity
        if entities:
            entity = entities[0]
            question = QuizQuestion(
                question=f"According to the article '{article.title}', what is mentioned about {entity}?",
                expected_answer=_extract_sentence_with_entity(article.content, entity),
                level="L1",
                source_urls=[article.url],
            )
            questions.append(question)

        # Create recall question about date if present
        if dates:
            date = dates[0]
            question = QuizQuestion(
                question=f"What date is mentioned in the article '{article.title}'?",
                expected_answer=date,
                level="L1",
                source_urls=[article.url],
            )
            questions.append(question)

    return questions


def _generate_l2_inference(articles: list[NewsArticle]) -> list[QuizQuestion]:
    """Generate L2 (inference) questions - reasoning from facts."""
    questions = []

    for article in articles[:2]:  # Limit to first 2
        # Look for cause-effect patterns
        content_lower = article.content.lower()

        if any(
            word in content_lower
            for word in ["because", "due to", "resulted in", "led to", "after", "following"]
        ):
            question = QuizQuestion(
                question=f"Based on the article '{article.title}', why did the described events occur or what was the impact?",
                expected_answer=_extract_reasoning_context(article.content),
                level="L2",
                source_urls=[article.url],
            )
            questions.append(question)

        elif any(
            word in content_lower for word in ["will", "expect", "predict", "forecast", "expected"]
        ):
            question = QuizQuestion(
                question=f"What does the article '{article.title}' suggest about future developments?",
                expected_answer=_extract_forward_looking_statement(article.content),
                level="L2",
                source_urls=[article.url],
            )
            questions.append(question)
        else:
            # Fallback: Always generate at least one L2 question
            question = QuizQuestion(
                question=f"Based on the article '{article.title}', what conclusion can you draw from the information presented?",
                expected_answer=article.content[:150],
                level="L2",
                source_urls=[article.url],
            )
            questions.append(question)

    return questions


def _generate_l3_synthesis(articles: list[NewsArticle]) -> list[QuizQuestion]:
    """Generate L3 (synthesis) questions - combining multiple sources."""
    questions = []

    if len(articles) < 2:
        return questions

    # Compare first two articles
    article1 = articles[0]
    article2 = articles[1]

    question = QuizQuestion(
        question=f"How do the events described in '{article1.title}' and '{article2.title}' relate to each other?",
        expected_answer=f"Both articles discuss related developments: {article1.content[:100]}... and {article2.content[:100]}...",
        level="L3",
        source_urls=[article1.url, article2.url],
    )
    questions.append(question)

    # Find common themes
    question = QuizQuestion(
        question=f"What common theme or trend can you identify from these articles: '{article1.title}' and '{article2.title}'?",
        expected_answer=_identify_common_theme(article1, article2),
        level="L3",
        source_urls=[article1.url, article2.url],
    )
    questions.append(question)

    return questions


def _generate_l4_application(articles: list[NewsArticle]) -> list[QuizQuestion]:
    """Generate L4 (application) questions - applying to new scenarios."""
    questions = []

    for article in articles[:2]:  # Limit to first 2
        question = QuizQuestion(
            question=f"If the trends described in '{article.title}' continue, what implications might this have for similar situations in the future?",
            expected_answer=f"Based on {article.content[:100]}..., this could lead to similar developments in related areas.",
            level="L4",
            source_urls=[article.url],
        )
        questions.append(question)

    return questions


def _extract_sentence_with_entity(content: str, entity: str) -> str:
    """Extract sentence containing the entity."""
    sentences = content.split(". ")
    for sentence in sentences:
        if entity in sentence:
            return sentence.strip()
    return content[:100]


def _extract_reasoning_context(content: str) -> str:
    """Extract reasoning/causal context from content."""
    sentences = content.split(". ")
    for sentence in sentences:
        if any(
            word in sentence.lower()
            for word in ["because", "due to", "resulted", "led to", "after", "following"]
        ):
            return sentence.strip()
    return content[:150]


def _extract_forward_looking_statement(content: str) -> str:
    """Extract forward-looking statements."""
    sentences = content.split(". ")
    for sentence in sentences:
        if any(
            word in sentence.lower()
            for word in ["will", "expect", "predict", "forecast", "expected"]
        ):
            return sentence.strip()
    return content[:150]


def _identify_common_theme(article1: NewsArticle, article2: NewsArticle) -> str:
    """Identify common theme between articles."""
    # Simplified - just note both articles exist
    return f"Both articles discuss developments in their respective domains: {article1.title} and {article2.title}."


__all__ = ["generate_quiz", "QuizQuestion"]
