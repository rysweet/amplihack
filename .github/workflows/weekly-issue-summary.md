---
name: Weekly Issue Summary
description: Creates weekly summary of issue activity including trends, charts, and insights every Monday morning
on:
  schedule:
    - cron: "0 14 * * 1" # Weekly on Mondays at 2 PM UTC (9 AM EST / 6 AM PST)
  workflow_dispatch:
permissions:
  issues: read
tracker-id: weekly-issue-summary
engine: copilot
network:
  allowed:
    - defaults
    - python
    - node
sandbox:
  agent: awf # Firewall enabled
tools:
  bash: true
  github:
    toolsets:
      - issues
      - discussions
safe-outputs:
  upload-asset:
  create-discussion:
    title-prefix: "[Weekly Summary] "
    category: "Announcements"
    close-older-discussions: true
timeout-minutes: 20
strict: true
---

# Weekly Issue Summary for amplihack4

## 📊 Trend Charts Requirement

**IMPORTANT**: Generate exactly 2 trend charts that showcase issue activity patterns over time.

### Chart Generation Process

**Phase 1: Data Collection**

Collect data for the past 30 days (or available data) using GitHub API:

1. **Issue Activity Data**:
   - Count of issues opened per day
   - Count of issues closed per day
   - Running count of open issues
   - Issues by label (enhancement, bug, question, documentation, etc.)

2. **Issue Resolution Data**:
   - Average time to close issues (in days)
   - Distribution of issue lifespans
   - Issues by milestone or priority over time

**Phase 2: Data Preparation**

1. Create CSV files in \`/tmp/gh-aw/python/data/\` with the collected data:
   - \`issue_activity.csv\` - Daily opened/closed counts and open count
   - \`issue_resolution.csv\` - Resolution time statistics

2. Each CSV should have a date column and metric columns with appropriate headers

3. Use pandas for data manipulation

**Phase 3: Chart Generation**

Generate exactly **2 high-quality trend charts**:

**Chart 1: Issue Activity Trends**

- Multi-line chart showing opened/closed per week, net change, running total
- X-axis: Week (last 12 weeks)
- Y-axis: Count
- Save as: \`/tmp/gh-aw/python/charts/issue_activity_trends.png\`

**Chart 2: Issue Resolution Time Trends**

- Line chart with 7-day moving averages
- X-axis: Date (last 30 days)
- Y-axis: Days to resolution
- Save as: \`/tmp/gh-aw/python/charts/issue_resolution_trends.png\`

**Chart Quality Requirements**:

- DPI: 300 minimum
- Figure size: 12x7 inches
- Use seaborn styling
- Clear labels and legend

**Phase 4: Upload Charts**

1. Upload both charts using the \`upload asset\` tool
2. Collect the returned URLs for embedding

**Phase 5: Embed Charts in Discussion**

Include charts with analysis in the weekly summary report.

## 📝 Report Formatting Guidelines

**CRITICAL**: Follow these formatting guidelines:

### 1. Header Levels

Use h3 (###) or lower for all headers. The discussion title is h1.

### 2. Progressive Disclosure

Wrap long sections in \`<details>\` tags for readability.

### 3. Report Structure Pattern

1. **Weekly Overview** (always visible)
2. **Key Trends** (always visible)
3. **Summary Statistics** (always visible)
4. **Trend Charts** (always visible)
5. **Detailed Issue Breakdown** (collapsible)
6. **Recommendations** (always visible)

## Weekly Analysis for amplihack4

Analyze all issues in \${{ github.repository }} over the last 7 days.

### Analysis Requirements

Create a comprehensive summary that includes:

1. **Issue Counts & Trends**
2. **Issue Categorization**
3. **Issue Details** (collapsible)
4. **Contributor Activity**
5. **Resolution Metrics**
6. **Sentiment & Themes**
7. **Actionable Recommendations**

### Data Collection

Use bash and GitHub CLI to collect data, then analyze with Python.

### Chart Integration

After generating charts:

1. Upload PNG files
2. Embed in report
3. Provide brief analysis

### Discussion Post

Create GitHub Discussion:

- Title: "[Weekly Summary] Issue Activity for [Date Range]"
- Category: "Announcements"
- Body: Complete formatted report with charts
