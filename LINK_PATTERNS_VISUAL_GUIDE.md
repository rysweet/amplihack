# Link Patterns Visual Guide

Visual reference for understanding and fixing broken documentation links.

---

## Pattern Classification Flowchart

```
                    Broken Link Detected
                            |
                            v
                    What's the Pattern?
                            |
           ┌────────────────┼────────────────┐
           |                |                |
           v                v                v
    Ends with /        Has ../ path    Different file
           |                |                |
           v                v                v
   PATTERN #1         PATTERN #2        PATTERN #3
   Directory Link     Relative Path     Missing File
           |                |                |
           v                v                v
    ┌──────┴──────┐   ┌─────┴─────┐    ┌────┴────┐
    |             |   |           |    |         |
 Has index?   Has README? Same     Cross-  Dead    Moved
    |             |      section? section? Link   File
    v             v      |         |      |        |
Link to      Link to     v         v      v        v
index.md    README.md   Keep    Convert  Remove  Update
                        Fix     to Site  Link    Path
                       Path   Relative
```

---

## Pattern #1: Directory Links

### Problem Visualization

```
┌─────────────────────────────────────────────────────────────┐
│  MARKDOWN FILE: docs/document_driven_development/README.md  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  See [Core Concepts](core_concepts/) for details           │
│                                          ↑                  │
│                        This link is BROKEN                  │
│                                          ↓                  │
│  MkDocs tries to find: core_concepts/index.md              │
│  But only exists:      core_concepts/README.md             │
│                                                             │
│  USER CLICKS → 404 Error!                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Solution Visualization

```
┌─────────────────────────────────────────────────────────────┐
│  FIXED VERSION:                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  See [Core Concepts](core_concepts/README.md) for details  │
│                                             ↑               │
│                       Explicit file reference               │
│                                             ↓               │
│  MkDocs finds: core_concepts/README.md ✓                   │
│  USER CLICKS → Content loads!                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
docs/document_driven_development/
│
├── README.md                    ← Source file with link
│   Content: [Link](core_concepts/)  ❌ Broken
│   Fixed:   [Link](core_concepts/README.md) ✅
│
└── core_concepts/
    ├── README.md                ← Target exists!
    ├── context_poisoning.md
    ├── file_crawling.md
    └── retcon_writing.md
```

---

## Pattern #2: Cross-Boundary Relative Paths

### Problem Visualization

```
┌─────────────────────────────────────────────────────────────┐
│  FILE: docs/agent-bundle-generator-guide.md                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Philosophy](../.claude/context/PHILOSOPHY.md)             │
│                  ↑                                          │
│         Relative path crosses boundaries                    │
│                  ↓                                          │
│                                                             │
│  From:  docs/agent-bundle-generator-guide.md                │
│  Up:    docs/ → (project root)                              │
│  Down:  .claude/context/PHILOSOPHY.md                       │
│                                                             │
│  PROBLEM: MkDocs uses different path resolution!            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Directory Tree Context

```
project-root/
├── docs/                           ← docs/ boundary
│   ├── agent-bundle-generator.md  ← Source file
│   └── [other docs]
│
├── .claude/                        ← .claude/ boundary
│   └── context/
│       └── PHILOSOPHY.md           ← Target file
│
└── mkdocs.yml                      ← Defines nav structure

Link: [Text](../.claude/context/PHILOSOPHY.md)
      ← Crosses from docs/ to .claude/ (crosses boundaries)
```

### Solution Options

```
┌─────────────────────────────────────────────────────────────┐
│  OPTION A: Site-Relative Path                              │
├─────────────────────────────────────────────────────────────┤
│  [Philosophy](/.claude/context/PHILOSOPHY.md)               │
│                ↑                                            │
│       Starts with / = site root                             │
│                                                             │
│  PRO: Works regardless of source location                   │
│  CON: Requires MkDocs to include .claude/ in docs           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  OPTION B: Remove Link, Use Navigation                     │
├─────────────────────────────────────────────────────────────┤
│  See the *Philosophy* section in the navigation.           │
│                                                             │
│  PRO: Always works, relies on stable nav structure          │
│  CON: Less direct than inline link                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  OPTION C: Copy to docs/ (if appropriate)                  │
├─────────────────────────────────────────────────────────────┤
│  [Philosophy](core-concepts/philosophy.md)                  │
│                                                             │
│  PRO: Simple, works perfectly                               │
│  CON: Content duplication (violates DRY)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Pattern #3: Missing Files

### Problem Visualization

```
┌─────────────────────────────────────────────────────────────┐
│  FILE: docs/tutorials/first-docs-site.md                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [API Reference](../reference/github-pages-api.md)          │
│                                    ↑                        │
│                    Link points to non-existent file         │
│                                    ↓                        │
│                                                             │
│  Expected: docs/reference/github-pages-api.md               │
│  Reality:  FILE DOES NOT EXIST!                             │
│                                                             │
│  Possibilities:                                             │
│    - File was removed (deprecated feature)                  │
│    - File was moved (and link not updated)                  │
│    - File is planned but not created yet                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Resolution Decision Tree

```
                Missing File Detected
                        |
                        v
                 Why is it missing?
                        |
        ┌───────────────┼───────────────┐
        |               |               |
        v               v               v
    Removed        Moved/Renamed     Planned
   (deprecated)                      (future)
        |               |               |
        v               v               v
    ┌───┴───┐      ┌────┴────┐     ┌───┴───┐
    |       |      |         |     |       |
Remove  Convert Update    Search Create  Document
Link    to text  path     codebase stub   plan
        note            for file  page
```

---

## Automation Coverage Map

```
┌─────────────────────────────────────────────────────────────┐
│                  AUTOMATION COVERAGE                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Pattern #1: Directory Links                                │
│  ████████████████████████ 100% Automated                    │
│  Tool: fix_common_links.py                                  │
│  Time: < 5 seconds for 16 fixes                             │
│                                                             │
│  Pattern #2: Cross-Boundary Paths                           │
│  ████████░░░░░░░░░░░░░░░░  40% Automated                    │
│  Tool: Manual review with sed patterns                      │
│  Time: 2-3 minutes per link                                 │
│                                                             │
│  Pattern #3: Missing Files                                  │
│  ██░░░░░░░░░░░░░░░░░░░░░░  10% Automated                    │
│  Tool: Detection automated, fix requires human judgment     │
│  Time: 5-15 minutes per file                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│              DOCUMENTATION LINK FIX WORKFLOW                 │
└─────────────────────────────────────────────────────────────┘

    START
      |
      v
[Run Link Checker]
      |
      v
[Review Report] ──→ No Issues? ──→ DONE ✓
      |
      | Issues Found
      v
[Classify Pattern]
      |
      ├──→ Pattern #1? ──→ [Run fix_common_links.py] ──┐
      |                                                  |
      ├──→ Pattern #2? ──→ [Review Each Link] ─────────┤
      |                    [Choose Fix Strategy]        |
      |                                                  |
      └──→ Pattern #3? ──→ [Audit Missing Files] ──────┤
                           [Decide Action per File]     |
                                                        |
                                                        v
                                              [Apply Fixes]
                                                        |
                                                        v
                                              [Verify with mkdocs build]
                                                        |
                                                        v
                                              [Commit Changes]
                                                        |
                                                        v
                                                      DONE ✓
```

---

## Fix Priority Matrix

```
                        High Impact
                            ↑
                            |
        ┌───────────────────┼───────────────────┐
        |                   |                   |
        |   QUICK WINS      |   STRATEGIC       |
        |                   |                   |
        |   Pattern #1      |   Standards       |
        |   16 links        |   Prevention      |
   Low  |   5 seconds       |   CI hooks        |  High
 Effort |                   |                   | Effort
 ←──────┼───────────────────┼───────────────────┼──────→
        |                   |                   |
        |   ONGOING         |   DEEP WORK       |
        |                   |                   |
        |   Pattern #2      |   Pattern #3      |
        |   30 links        |   10-20 files     |
        |   2-3 hours       |   4-5 hours       |
        |                   |                   |
        └───────────────────┼───────────────────┘
                            |
                            ↓
                        Low Impact

LEGEND:
█████ = Do First (Pattern #1)
████░ = Do Second (Pattern #2)
███░░ = Do Third (Pattern #3)
██░░░ = Do Last (Standards & Prevention)
```

---

## Before/After Comparison

### BEFORE (Broken)

```
docs/document_driven_development/README.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Quick Start

1. [Overview](overview.md) - What is DDD
2. [Core Concepts](core_concepts/) ← BROKEN (404)
3. [The Process](phases/) ← BROKEN (404)
4. [Reference](reference/) ← BROKEN (404)

RESULT: 3 broken links, users can't navigate!
```

### AFTER (Fixed)

```
docs/document_driven_development/README.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Quick Start

1. [Overview](overview.md) - What is DDD
2. [Core Concepts](core_concepts/README.md) ← FIXED ✓
3. [The Process](phases/README.md) ← FIXED ✓
4. [Reference](reference/README.md) ← FIXED ✓

RESULT: All links work, smooth navigation!
```

---

## Testing Visualization

```
┌─────────────────────────────────────────────────────────────┐
│                    TESTING PIPELINE                         │
└─────────────────────────────────────────────────────────────┘

  Development          CI/CD              Deployment
      |                 |                     |
      v                 v                     v

  [Edit Docs]      [Push to PR]        [Merge to main]
      |                 |                     |
      v                 v                     v

  [Preview]        [Link Checker]      [Deploy Docs]
  mkdocs serve     link_checker.py     mkdocs gh-deploy
      |                 |                     |
      v                 v                     v

  [Click Links]    [Report Issues]     [Verify Live]
  Manual check     Automated check     Smoke test
      |                 |                     |
      v                 v                     v

  Fix Locally ──→ CI Passes ✓ ──→ Users See Fixes
      ↑                                       |
      |                                       |
      └───────── Feedback Loop ──────────────┘
```

---

## Impact Timeline

```
Time →

0h        1h        2h        4h        1 week    Ongoing
|─────────|─────────|─────────|─────────|─────────|─────→

PHASE 1
├─ Run automation
│  16 links fixed ✓
│
PHASE 2
          ├─ Review cross-boundary
          │  30 links standardized ✓
          │
PHASE 3
                    ├─ Audit missing files
                    │  10-20 decisions made ✓
                    │
PHASE 4
                              ├─ Standards written
                              │  Prevention in place ✓
                              │
ONGOING
                                        └─ Monitor & refine
                                           0 new broken links

Benefits Accumulate →
```

---

## Key Takeaways (Visual)

```
┌─────────────────────────────────────────────────────────────┐
│                  🎯 KEY INSIGHTS                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. AUTOMATION WORKS! ⚡                                     │
│     ████████████████████ 16 fixes in 5 seconds             │
│                                                             │
│  2. PATTERNS MATTER 🎨                                      │
│     3 patterns = 80% of all broken links                    │
│                                                             │
│  3. PREVENTION > CURE 🛡️                                   │
│     CI + Standards = No future breaks                       │
│                                                             │
│  4. PHASED APPROACH 📊                                      │
│     Quick wins → Strategic → Long-tail                      │
│                                                             │
│  5. TOOLS OVER TOIL 🔧                                      │
│     5 seconds (script) vs 30 mins (manual)                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

**Generated**: 2025-12-02
**Purpose**: Visual guide for understanding link fix patterns
**Companion**: PATTERN_ANALYSIS_SUMMARY.md
