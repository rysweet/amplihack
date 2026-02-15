---
description: Automates PR categorization, risk assessment, and prioritization for agent-created pull requests in amplihack4
on:
  schedule:
    - cron: "0 */6 * * *" # Every 6 hours
  workflow_dispatch:
permissions:
  contents: read
  pull-requests: read
engine: copilot
tools:
  github:
    lockdown: true
    toolsets: [pull_requests, repos, issues, labels]
  repo-memory:
    branch-name: memory/pr-triage
    file-glob: "**"
    max-file-size: 102400 # 100KB
safe-outputs:
  add-labels:
    max: 100
  add-comment:
    max: 50
  create-issue:
    max: 1
    title-prefix: "[PR Triage Report] "
    expires: 1d
    close-older-issues: true
  messages:
    run-started: "🔍 Starting PR triage analysis... [{workflow_name}]({run_url}) is categorizing and prioritizing agent-created PRs"
    run-success: "✅ PR triage complete! [{workflow_name}]({run_url}) has analyzed and categorized PRs. Check the issue for detailed report."
    run-failure: "❌ PR triage failed! [{workflow_name}]({run_url}) {status}. Some PRs may not be triaged."
timeout-minutes: 30
imports:
  - shared/mood.md
---

# PR Triage Agent

You are an automated PR triage system responsible for categorizing, assessing
risk, prioritizing, and recommending actions for agent-created pull requests in
the amplihack4 repository.

Execute all phases systematically and maintain consistency in scoring and
recommendations across all PRs. This is a condensed workflow adapted from
github/gh-aw with error resilience for amplihack4.
