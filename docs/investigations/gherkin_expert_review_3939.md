# Issue #3939 Review: Gherkin Expert Skill/Agent Deliverables

## Summary

Review pass for the 5 deliverables added in commit `d144c779a` on branch
`feat/issue-3939-gherkin-expert-skill-agent`.

## Deliverables Reviewed

| #   | File                                                     | Status | Notes                                                                       |
| --- | -------------------------------------------------------- | ------ | --------------------------------------------------------------------------- |
| 1   | `.claude/skills/gherkin-expert/SKILL.md`                 | Pass   | Clean frontmatter, activation keywords, judgment-based guidance             |
| 2   | `.claude/agents/amplihack/specialized/gherkin-expert.md` | Pass   | Comprehensive agent: syntax, design principles, anti-patterns, evidence     |
| 3   | `.claude/agents/amplihack/specialized/prompt-writer.md`  | Pass   | Tri-path update (English/Gherkin/TLA+), consistent "judgment call" framing  |
| 4   | `.claude/context/PATTERNS.md`                            | Pass   | Expanded "Formal Specification as Prompt" pattern with both evidence tables |
| 5   | `amplifier-bundle/recipes/default-workflow.yaml`         | Pass   | Light-touch additions in design and testing steps                           |

## Test Results

48/48 deliverable validation tests pass (`test_gherkin_expert_deliverables.py`).

## Issues Found and Resolved

- **Experiment artifacts staged in repo root**: 3 Python files (`recipe_step_executor.py`,
  `test_gherkin_expert_deliverables.py`, `test_recipe_step_executor.py`) from the Gherkin v2
  experiment (#3969/#3975) were staged but not part of #3939's deliverables. Unstaged them.

## Key Design Decisions

- "Judgment call, not a rule" framing is consistent across all 5 files
- English-only remains the explicit default; formal specs must earn their place
- Gherkin and TLA+ are presented as complementary tools for different domains
- Workflow additions are non-intrusive (2 small paragraphs added)

## Evidence Referenced

- Gherkin: AVG=0.898 vs English 0.713 (+26%), N=3 agent consensus
- TLA+: 0.86 vs English 0.57 (+51%), #3497 experiment
