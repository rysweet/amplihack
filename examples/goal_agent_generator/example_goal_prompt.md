# Goal: Automate Code Review Process

Create an autonomous agent that reviews pull requests and provides feedback.

## Objective

Build a system that:

- Analyzes code changes in pull requests
- Detects common issues and anti-patterns
- Generates constructive feedback
- Posts review comments automatically

## Domain

Automation and code quality

## Constraints

- Must complete review within 15 minutes
- Should not modify code directly
- Must respect existing code style
- Cannot access production systems

## Success Criteria

- All pull requests reviewed within SLA
- At least 80% of common issues detected
- Review comments are actionable and helpful
- No false positives on style violations
- Team satisfaction with review quality

## Technical Requirements

- Integrate with GitHub API
- Support multiple programming languages
- Generate reports in markdown format
- Track review metrics over time

## Context

This agent will help reduce code review bottlenecks and improve code quality
by providing fast, consistent, automated feedback on common issues, allowing
human reviewers to focus on architecture and business logic.
