"""Lesson 9 content builder."""

from __future__ import annotations

import textwrap

from amplihack.agents.teaching.models import Exercise, Lesson, QuizQuestion


def _build_lesson_9() -> Lesson:
    """Lesson 9: Advanced -- Security Domain Agents."""
    return Lesson(
        id="L09",
        title="Advanced: Security Domain Agents",
        description="Generate agents specialized for security analysis with domain-specific eval.",
        content=textwrap.dedent("""\
            # Lesson 9: Security Domain Agents

            ## Domain-Specific Agents

            The agent generator can produce agents specialized for specific domains.
            Security analysis is a common use case that benefits from:
            - Domain-specific knowledge bases.
            - Security-focused eval questions.
            - Threat modeling capabilities.

            ## Creating a Security Agent

            ```markdown
            # Goal: Security Vulnerability Analyzer

            ## Objective
            Analyze codebases for common vulnerabilities (OWASP Top 10,
            CWE-25) and generate remediation recommendations.

            ## Domain
            security-analysis

            ## Constraints
            - Must identify injection, XSS, CSRF, and auth issues
            - Must provide severity ratings (Critical/High/Medium/Low)
            - Must cite CWE numbers for each finding

            ## Success Criteria
            - Identifies SQL injection in test code
            - Provides correct CWE references
            - Generates actionable remediation steps
            ```

            ```bash
            amplihack new --file security_analyzer.md \\
                --sdk claude --multi-agent --enable-memory
            ```

            ## Domain-Specific Eval

            The eval system supports domain-specific test suites:

            ```bash
            python -m amplihack.eval.domain_eval_harness \\
                --domain security \\
                --agent-name security-analyzer \\
                --output-dir security_eval/
            ```

            ## Security Eval Dimensions

            Security agents are evaluated on:
            1. **Vulnerability detection**: Can it find known vulnerabilities?
            2. **Classification accuracy**: Does it assign correct CWE numbers?
            3. **Severity assessment**: Are severity ratings appropriate?
            4. **Remediation quality**: Are fixes actionable and correct?

            ## Multi-Agent Security Setup

            A security-focused multi-agent system might have:
            - **Coordinator**: Dispatches files to sub-agents.
            - **Static analyzer**: Scans code patterns.
            - **Dependency checker**: Reviews package vulnerabilities.
            - **Compliance auditor**: Checks against security standards.
        """),
        prerequisites=["L03", "L04", "L06"],
        exercises=[
            Exercise(
                id="E09-01",
                instruction=(
                    "Write a complete prompt.md for a security agent that focuses on "
                    "API security. Include Goal, Domain, Constraints, and Success Criteria."
                ),
                expected_output=(
                    "# Goal: API Security Analyzer\n\n"
                    "## Domain\nsecurity-analysis\n\n"
                    "## Constraints\n- Focus on auth, rate limiting, input validation\n\n"
                    "## Success Criteria\n- Detects missing authentication on endpoints"
                ),
                hint="Include OWASP-relevant constraints and measurable success criteria.",
                validation_fn="validate_security_prompt",
            ),
            Exercise(
                id="E09-02",
                instruction=(
                    "Write the CLI command to generate a multi-agent security analyzer "
                    "with memory enabled, using the Claude SDK."
                ),
                expected_output=(
                    "amplihack new --file api_security.md "
                    "--sdk claude --multi-agent --enable-memory"
                ),
                hint="Combine --sdk, --multi-agent, and --enable-memory flags.",
                validation_fn="validate_multi_agent_command",
            ),
        ],
        quiz=[
            QuizQuestion(
                question="What four dimensions are security agents evaluated on?",
                correct_answer=(
                    "Vulnerability detection, classification accuracy, "
                    "severity assessment, remediation quality"
                ),
                wrong_answers=[
                    "Speed, accuracy, coverage, cost",
                    "Input, output, throughput, latency",
                    "Detection, prevention, response, recovery",
                ],
                explanation="These match the security eval harness dimensions.",
            ),
            QuizQuestion(
                question="Why use --enable-memory for a security agent?",
                correct_answer=(
                    "To persist vulnerability knowledge across sessions and build "
                    "a cumulative understanding of the codebase's security posture"
                ),
                wrong_answers=[
                    "Memory is always required",
                    "To cache API responses",
                    "To store user credentials securely",
                ],
                explanation="Persistent memory lets the agent build domain knowledge.",
            ),
            QuizQuestion(
                question="Which SDK is best suited for security agents that need file access?",
                correct_answer="claude -- it has read_file, write_file, grep, and bash tools",
                wrong_answers=[
                    "mini -- it is the simplest",
                    "copilot -- it has git integration",
                    "microsoft -- it has enterprise features",
                ],
                explanation="Claude SDK's file tools are essential for code analysis.",
            ),
        ],
    )
