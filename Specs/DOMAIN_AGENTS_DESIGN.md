# Domain-Specific Goal-Seeking Agents Design

## Overview

Five domain-specific goal-seeking agents for office work domains, each with
evaluation harnesses and a teaching layer that measures knowledge transfer.

All agents extend the existing `AgenticLoop` + `ActionExecutor` + `MemoryRetriever`
pattern from `src/amplihack/agents/goal_seeking/`.

## Architecture

```
src/amplihack/agents/domain_agents/
    base.py                    # DomainAgent ABC
    skill_injector.py          # Skill injection registry
    __init__.py

    code_review/
        agent.py               # CodeReviewAgent
        tools.py               # Code review tool functions
        prompts/system.txt
        eval_levels.py         # L1-L4 eval scenarios

    meeting_synthesizer/
        agent.py               # MeetingSynthesizerAgent
        tools.py               # Meeting processing tools
        prompts/system.txt
        eval_levels.py         # L1-L4 eval scenarios

    document_creator/          # Designed, not fully built
    data_analysis/             # Designed, not fully built
    project_planning/          # Designed, not fully built

src/amplihack/eval/
    domain_eval_harness.py     # Generic eval harness for domain agents
    teaching_eval.py           # Teaching quality grading

tests/agents/domain_agents/
    test_base.py
    test_code_review_agent.py
    test_meeting_synthesizer_agent.py
    test_domain_eval_harness.py
    test_teaching_eval.py
    test_skill_injector.py
```

## The 5 Domain Agents

### 1. Code Review Agent (FULLY BUILT)

- Injected Skills: code-smell-detector, pr-review-assistant, socratic-review
- Eval: L1 Basic Detection, L2 Style/Quality, L3 Security, L4 Architecture

### 2. Meeting Synthesizer Agent (FULLY BUILT)

- Injected Skills: meeting-synthesizer, email-drafter, backlog-curator
- Eval: L1 Extraction, L2 Attribution, L3 Synthesis, L4 Actionability

### 3. Document Creator Agent (DESIGNED)

- Injected Skills: docx, pdf, pptx, documentation-writing
- Eval: L1 Structure, L2 Content, L3 Formatting, L4 Audience

### 4. Data Analysis Agent (DESIGNED)

- Injected Skills: xlsx, mermaid-diagram-generator, storytelling-synthesizer
- Eval: L1 Basic Stats, L2 Trend Detection, L3 Insight Quality, L4 Storytelling

### 5. Project Planning Agent (DESIGNED)

- Injected Skills: pm-architect, roadmap-strategist, work-delegator, workstream-coordinator
- Eval: L1 Decomposition, L2 Dependencies, L3 Risk Assessment, L4 Plan Quality

## Teaching Layer

Teaching eval runs as a second layer on domain eval:

1. Domain agent passes L1-L4 eval (proves competence)
2. Teaching session evaluates knowledge transfer ability
3. Combined score = 0.6 _ domain_score + 0.4 _ teaching_score

Teaching dimensions: Clarity (25%), Completeness (25%), Student Performance (30%), Adaptivity (20%)

## Skill Injection

Skills are injected at agent creation via SkillInjector registry:

```python
injector = SkillInjector()
injector.register("code_review", "code-smell-detector", detect_smells_fn)
agent = CodeReviewAgent(skill_injector=injector)
```
