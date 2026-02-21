# Self-Improving Agent Architecture

## Source: Research agent analyzing Reflexion, Self-Refine, LATS, SICA, DSPy

## Core Loop

```
Eval Run → Error Analyzer → Hypothesis Generator → Patch Proposer → Sandbox Validator → Regression Gate → PR
```

## Error Taxonomy (maps eval failures to code components)

| Failure Mode               | Eval Level | Root Component                     |
| -------------------------- | ---------- | ---------------------------------- |
| retrieval_insufficient     | L2, L3     | agentic_loop.\_plan_retrieval()    |
| temporal_ordering_wrong    | L3         | synthesis_instructions.md          |
| intent_misclassification   | L2, L3, L5 | intent_classification.md           |
| fact_extraction_incomplete | L1, L2     | fact_extraction.md                 |
| synthesis_hallucination    | L3, L4     | synthesis.md                       |
| update_not_applied         | L6         | memory supersede logic             |
| contradiction_undetected   | L5         | intent + synthesis prompt          |
| procedural_ordering_lost   | L4         | fact_extraction.md procedural_hint |
| teaching_coverage_gap      | L7         | teaching_response.md               |

## Safety Constraints

- Never modify: grader, test data, safety config, test runner
- Always: git worktree sandbox, 3-run validation, PR (never direct push)
- Max diff: 50 lines per patch
- Regression gate: no level drops >5%, net improvement >=2%

## Key Papers

- Reflexion (Shinn 2023): Verbal reinforcement learning, 91% HumanEval
- Self-Refine (Madaan 2023): Generate→Feedback→Refine loop, +20% avg
- LATS (Zhou 2024): MCTS over action trajectories, 92.7% HumanEval
- SICA (ICLR 2025): Self-improving coding agent editing own codebase
- DSPy MIPROv2: Trace-guided prompt optimization

## Implementation: src/amplihack/eval/self_improve/

- error_analyzer.py: Categorize failures into taxonomy
- hypothesis_generator.py: LLM generates root cause hypotheses
- patch_proposer.py: Generate code/prompt patches
- sandbox_runner.py: Git worktree sandbox execution
- regression_gate.py: Validate before promotion
- improvement_loop.py: Orchestrate full cycle
