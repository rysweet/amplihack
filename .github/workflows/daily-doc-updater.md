---
name: Daily Documentation Updater
description: Automatically reviews and updates documentation to ensure accuracy and completeness
on:
  schedule:
    - cron: "0 6 * * *"
  workflow_dispatch:

permissions:
  contents: read
  issues: read
  pull-requests: read

tracker-id: daily-doc-updater
engine: claude
strict: true

network:
  allowed:
    - defaults
    - github

safe-outputs:
  create-pull-request:
    expires: 1d
    title-prefix: "[docs] "
    labels: [documentation, automation]
    reviewers: []
    draft: false
    auto-merge: false

tools:
  cache-memory: true
  github:
    toolsets: [default]
  edit:
  bash:
    - "find docs -name '*.md'"
    - "git"

timeout-minutes: 45
---

# Daily Documentation Updater

Automatically updates amplihack4 documentation based on merged PRs from the last 24 hours following the Diátaxis framework.
