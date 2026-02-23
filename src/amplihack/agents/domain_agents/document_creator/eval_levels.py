"""Evaluation levels for the Document Creator agent."""

from __future__ import annotations

from amplihack.agents.domain_agents.base import EvalLevel, EvalScenario

_SIMPLE_CONTENT = (
    "# Introduction\n"
    "This report covers the Q1 results for our engineering team.\n\n"
    "# Results\n"
    "We shipped 15 features and fixed 42 bugs. Deployment frequency "
    "increased by 30%. Customer satisfaction improved to 4.2/5.\n\n"
    "# Conclusion\n"
    "Q1 was a strong quarter. We recommend continuing the current approach.\n"
)

_UNSTRUCTURED_CONTENT = (
    "The project started in January. We had three developers and one designer. "
    "The main challenge was integrating with the legacy API. Bob handled the "
    "database migration while Alice worked on the frontend. The deployment was "
    "delayed by two weeks due to infrastructure issues. Eventually we launched "
    "on March 15th. Customer feedback has been positive so far. Revenue increased "
    "by 12% in the first month. We plan to add mobile support in Q2."
)

_TECHNICAL_CONTENT = (
    "# API Migration Guide\n\n"
    "## Overview\n"
    "This guide covers migrating from REST API v2 to v3.\n\n"
    "## Breaking Changes\n"
    "The authentication endpoint moved from /auth to /oauth2/token. "
    "All responses now use camelCase instead of snake_case. "
    "Rate limiting headers changed from X-RateLimit to RateLimit.\n\n"
    "## Migration Steps\n"
    "1. Update SDK to version 3.0\n"
    "2. Replace authentication calls\n"
    "3. Update response parsers\n"
    "4. Test all API endpoints\n\n"
    "## Conclusion\n"
    "Follow these steps to migrate. Contact devops@company.com for help.\n"
)

_EXECUTIVE_CONTENT = (
    "The Q1 revenue target was $2.5M. We achieved $2.8M, a 12% overperformance. "
    "Customer acquisition cost decreased by 8%. The main risk is competitor "
    "product launching in Q2. Our strategy is to accelerate feature development "
    "and expand into the SMB market. Budget allocation: 60% engineering, "
    "25% marketing, 15% operations. ROI on the marketing campaign was 340%. "
    "We recommend increasing the marketing budget by 20% for Q2."
)


def get_eval_levels() -> list[EvalLevel]:
    return [_l1(), _l2(), _l3(), _l4()]


def _l1() -> EvalLevel:
    return EvalLevel(
        level_id="L1",
        name="Structure Analysis",
        description="Identifies document structure elements",
        passing_threshold=0.6,
        scenarios=[
            EvalScenario(
                scenario_id="L1-001",
                name="Structured document analysis",
                input_data={"content": _SIMPLE_CONTENT, "task_type": "analyze"},
                expected_output={
                    "min_heading_count": 2,
                    "must_mention": ["introduction", "conclusion"],
                },
                grading_rubric="Must identify headings and key sections.",
            ),
            EvalScenario(
                scenario_id="L1-002",
                name="Unstructured content handling",
                input_data={"content": _UNSTRUCTURED_CONTENT, "task_type": "analyze"},
                expected_output={
                    "min_word_count": 1,
                },
                grading_rubric="Must handle content without explicit structure.",
            ),
            EvalScenario(
                scenario_id="L1-003",
                name="Empty content handling",
                input_data={"content": "", "task_type": "analyze"},
                expected_output={},
                grading_rubric="Must handle empty content gracefully.",
            ),
        ],
    )


def _l2() -> EvalLevel:
    return EvalLevel(
        level_id="L2",
        name="Content Quality",
        description="Evaluates content quality and completeness",
        passing_threshold=0.6,
        scenarios=[
            EvalScenario(
                scenario_id="L2-001",
                name="Quality evaluation of structured doc",
                input_data={"content": _SIMPLE_CONTENT, "task_type": "evaluate"},
                expected_output={
                    "must_mention": ["readability", "completeness"],
                },
                grading_rubric="Must assess readability and completeness.",
            ),
            EvalScenario(
                scenario_id="L2-002",
                name="Unstructured doc quality",
                input_data={"content": _UNSTRUCTURED_CONTENT, "task_type": "evaluate"},
                expected_output={
                    "must_mention": ["completeness"],
                },
                grading_rubric="Must identify missing structure elements.",
            ),
        ],
    )


def _l3() -> EvalLevel:
    return EvalLevel(
        level_id="L3",
        name="Formatting",
        description="Applies and validates document formatting",
        passing_threshold=0.6,
        scenarios=[
            EvalScenario(
                scenario_id="L3-001",
                name="Markdown formatting",
                input_data={"content": _TECHNICAL_CONTENT, "task_type": "format", "format_type": "markdown"},
                expected_output={
                    "must_mention": ["formatted"],
                },
                grading_rubric="Must produce formatted output.",
            ),
            EvalScenario(
                scenario_id="L3-002",
                name="Format issue detection",
                input_data={"content": "# \n# Second heading\nSome content", "task_type": "format"},
                expected_output={
                    "must_mention": ["issue"],
                },
                grading_rubric="Must detect formatting issues.",
            ),
        ],
    )


def _l4() -> EvalLevel:
    return EvalLevel(
        level_id="L4",
        name="Audience Adaptation",
        description="Tailors content for specific audiences",
        passing_threshold=0.5,
        scenarios=[
            EvalScenario(
                scenario_id="L4-001",
                name="Technical audience assessment",
                input_data={
                    "content": _TECHNICAL_CONTENT,
                    "task_type": "audience",
                    "target_audience": "technical",
                },
                expected_output={
                    "must_mention": ["technical", "audience"],
                },
                grading_rubric="Must assess technical audience fit.",
            ),
            EvalScenario(
                scenario_id="L4-002",
                name="Executive audience assessment",
                input_data={
                    "content": _EXECUTIVE_CONTENT,
                    "task_type": "audience",
                    "target_audience": "executive",
                },
                expected_output={
                    "must_mention": ["executive", "audience"],
                },
                grading_rubric="Must assess executive audience fit.",
            ),
        ],
    )
