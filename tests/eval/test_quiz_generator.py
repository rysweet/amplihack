"""Tests for quiz question generator."""

from amplihack.eval.multi_source_collector import NewsArticle
from amplihack.eval.quiz_generator import generate_quiz


def test_generate_quiz_creates_l1_recall_questions():
    """Test generation of L1 (recall) questions."""
    articles = [
        NewsArticle(
            url="https://example.com/1",
            title="AI News",
            content="OpenAI released GPT-5 on February 15, 2026.",
            published="2026-02-15T10:00:00Z",
        )
    ]

    quiz = generate_quiz(articles, levels=["L1"])

    assert len(quiz) >= 1
    l1_questions = [q for q in quiz if q.level == "L1"]
    assert len(l1_questions) >= 1
    # Check that question is about the article content
    assert l1_questions[0].question
    assert l1_questions[0].expected_answer
    assert (
        "GPT-5" in l1_questions[0].expected_answer or "February" in l1_questions[0].expected_answer
    )


def test_generate_quiz_creates_l2_inference_questions():
    """Test generation of L2 (inference) questions."""
    articles = [
        NewsArticle(
            url="https://example.com/1",
            title="Market News",
            content="Stock prices fell 10% after earnings report missed expectations.",
            published="2026-02-15T10:00:00Z",
        )
    ]

    quiz = generate_quiz(articles, levels=["L2"])

    assert len(quiz) >= 1
    l2_questions = [q for q in quiz if q.level == "L2"]
    assert len(l2_questions) >= 1
    # L2 should ask about implications/reasons
    assert any(
        word in l2_questions[0].question.lower() for word in ["why", "how", "impact", "result"]
    )


def test_generate_quiz_creates_l3_synthesis_questions():
    """Test generation of L3 (synthesis) questions requiring multiple sources."""
    articles = [
        NewsArticle(
            url="https://example.com/1",
            title="AI Model Release",
            content="Company A released new AI model with 95% accuracy.",
            published="2026-02-15T10:00:00Z",
        ),
        NewsArticle(
            url="https://example.com/2",
            title="Competitor News",
            content="Company B announced similar model with 93% accuracy.",
            published="2026-02-15T11:00:00Z",
        ),
    ]

    quiz = generate_quiz(articles, levels=["L3"])

    assert len(quiz) >= 1
    l3_questions = [q for q in quiz if q.level == "L3"]
    assert len(l3_questions) >= 1
    # L3 should reference multiple sources
    assert (
        "Company A" in l3_questions[0].expected_answer
        or "Company B" in l3_questions[0].expected_answer
    )


def test_generate_quiz_creates_l4_application_questions():
    """Test generation of L4 (application) questions."""
    articles = [
        NewsArticle(
            url="https://example.com/1",
            title="Tech Trend",
            content="AI adoption increased 50% in healthcare sector.",
            published="2026-02-15T10:00:00Z",
        )
    ]

    quiz = generate_quiz(articles, levels=["L4"])

    assert len(quiz) >= 1
    l4_questions = [q for q in quiz if q.level == "L4"]
    assert len(l4_questions) >= 1
    # L4 should ask hypothetical/application
    assert any(
        word in l4_questions[0].question.lower() for word in ["if", "would", "could", "predict"]
    )


def test_generate_quiz_all_levels():
    """Test generating questions at all cognitive levels."""
    articles = [
        NewsArticle(
            url="https://example.com/1",
            title="Tech News",
            content="Major announcement about AI technology.",
            published="2026-02-15T10:00:00Z",
        ),
        NewsArticle(
            url="https://example.com/2",
            title="Industry Update",
            content="Related development in tech sector.",
            published="2026-02-15T11:00:00Z",
        ),
    ]

    quiz = generate_quiz(articles, levels=["L1", "L2", "L3", "L4"])

    assert len(quiz) >= 4
    levels_present = {q.level for q in quiz}
    assert "L1" in levels_present
    assert "L2" in levels_present
    assert "L3" in levels_present
    assert "L4" in levels_present


def test_quiz_question_has_required_fields():
    """Test that quiz questions have all required fields."""
    articles = [
        NewsArticle(
            url="https://example.com/1",
            title="News",
            content="Content here.",
            published="2026-02-15T10:00:00Z",
        )
    ]

    quiz = generate_quiz(articles, levels=["L1"])

    question = quiz[0]
    assert hasattr(question, "question")
    assert hasattr(question, "expected_answer")
    assert hasattr(question, "level")
    assert hasattr(question, "source_urls")
    assert isinstance(question.source_urls, list)
