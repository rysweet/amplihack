# Continuous Improvement Loop: Goal-Seeking Agent Learning & Teaching

## Date: 2026-02-19

## Branch: feat/issue-2394-eval-harness-3scenario

---

## Vision

Build a **recursive self-improving loop** where each iteration:

1. Measures current capability (eval)
2. Identifies the weakest dimension
3. Researches relevant learning theory
4. Implements targeted improvements
5. Validates improvement via eval
6. Logs methods, insights, and next steps
7. Increases complexity for the next iteration

## Architecture: The Improvement Loop

```
┌─────────────────────────────────────────────────────┐
│                  ORCHESTRATOR (this session)          │
│                                                       │
│  For each iteration:                                  │
│    1. Run eval → identify weakest level               │
│    2. Research theory → design improvement             │
│    3. Implement fix → test locally                     │
│    4. Full eval → validate improvement                 │
│    5. Log results → plan next iteration               │
│                                                       │
│  Parallel execution:                                  │
│    - Multiple eval runs (parallel_suite)              │
│    - Research agents (theory, pedagogy, examples)     │
│    - Implementation agents per task                   │
│    - Remote sessions for long-running experiments     │
└─────────────────────────────────────────────────────┘
```

## Iteration Plan

### Phase 1: Foundation (Steps 1-2) ✅ COMPLETE

- Fix L2 multi-source synthesis: 60% → 93%
- Fix L3 temporal reasoning: 53% → 95%
- Method: Prompt engineering (plan quality, temporal extraction)
- Key insight: Facts must preserve temporal context during extraction

### Phase 2: Metacognition (Step 3) 🔄 IN PROGRESS

**Goal**: Add ReasoningTrace to measure HOW the agent thinks, not just WHAT it answers.

**Research foundation**:

- Flavell (1979): Metacognition = thinking about thinking
- Schraw & Dennison (1994): Metacognitive awareness inventory
- Efklides (2008): Metacognitive feelings and judgments
- Applied to AI: Agent should know when it knows enough, when it's uncertain

**Metrics to implement**:
| Metric | Source | Measurement |
|---|---|---|
| Effort Calibration | Bloom's taxonomy / cognitive load theory | Steps taken vs complexity |
| Sufficiency Judgment | JOL (Judgments of Learning) research | Correct sufficient/insufficient decisions |
| Search Quality | Information foraging theory | Retrieved-to-used ratio |
| Self-Correction | Error monitoring research | Arithmetic validations, query refinements |

**Implementation**:

- Add `ReasoningTrace` dataclass to `agentic_loop.py`
- `reason_iteratively` populates trace at each step
- Grader evaluates trace alongside answer
- New eval dimension reported per level

### Phase 3: CognitiveMemory Integration (Step 4)

**Goal**: Replace HierarchicalMemory with 6-type CognitiveMemory from amplihack-memory-lib.

**Expected improvements**:

- Working memory: Better task state tracking during iterative reasoning
- Sensory memory: Raw input buffering with TTL
- Procedural memory: Step sequences for L4 (Flutter tutorial)
- Prospective memory: Future intentions for teaching scenario

**Risk**: Regression on L1-L6 scores during migration. Mitigation: parallel eval before/after.

### Phase 4: Teacher-Student (Step 5)

**Goal**: Two-agent knowledge transfer scenario.

**Research foundation**:

- Vygotsky's Zone of Proximal Development (1978)
- Feynman Technique: Teaching reveals understanding gaps
- Bloom's 2-Sigma Problem: 1-on-1 tutoring >> classroom
- Chi et al. (2001): Self-explanation effect
- Palinscar & Brown (1984): Reciprocal teaching

**Teaching strategies to implement**:

1. **Scaffolding**: Teacher provides support, gradually removes it
2. **Socratic questioning**: Teacher asks probing questions
3. **Elaborative interrogation**: Student explains "why" not just "what"
4. **Interleaving**: Mix topics for deeper encoding
5. **Testing effect**: Student retrieves from memory (not re-reads)

**Eval dimensions**:

- Knowledge transfer rate: student_facts / teacher_facts
- Teaching quality: student_score / teacher_score
- Efficiency: turns needed for student competency
- Adaptation: Did teacher adjust to student confusion?

### Phase 5: Advanced Reasoning (Step 6)

**Goal**: L8 metacognition, L9 causal, L10 counterfactual scenarios.

**Research foundation**:

- Kahneman (2011): System 1 vs System 2 thinking
- Pearl (2009): Causal reasoning ladder (seeing, doing, imagining)
- Byrne (2005): Counterfactual thinking
- Gopnik et al. (2004): Theory theory of child development

**L8 (Metacognition)**: Agent evaluates its own reasoning trace

- "How confident should you be in this answer?"
- "What additional information would change your answer?"
- Uses ReasoningTrace from Phase 2

**L9 (Causal)**: "Why did Norway improve fastest?"

- Requires chain of events reasoning
- Agent must identify causal mechanisms, not just correlations

**L10 (Counterfactual)**: "What if Klaebo hadn't competed?"

- Requires hypothetical inference
- Agent must reason about absence of events

## Evaluation Strategy

### Multi-Run Statistical Validation

Every improvement gets validated with 3-run parallel eval:

```bash
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite --parallel 3 --output-dir /tmp/eval_phase_N
```

### Score Dashboard

| Level | Baseline | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Target |
| ----- | -------- | ------- | ------- | ------- | ------- | ------ |
| L1    | 100%     | 100%    | -       | -       | -       | ≥100%  |
| L2    | 60%      | 93%     | -       | -       | -       | ≥85%   |
| L3    | 53%      | 95%     | -       | -       | -       | ≥70%   |
| L4    | 81%      | -       | -       | -       | -       | ≥80%   |
| L5    | 100%     | -       | -       | -       | -       | ≥90%   |
| L6    | 98%      | -       | -       | -       | -       | ≥95%   |
| L7    | N/A      | N/A     | N/A     | N/A     | TBD     | ≥60%   |
| L8    | N/A      | N/A     | TBD     | -       | -       | ≥50%   |
| L9    | N/A      | N/A     | N/A     | -       | TBD     | ≥50%   |
| L10   | N/A      | N/A     | N/A     | -       | TBD     | ≥40%   |

### Regression Prevention

- Before each commit, full L1-L6 eval
- Any level dropping >5% below previous score triggers investigation
- 3-run median used to account for LLM stochasticity

## Parallel Execution Plan

### Concurrent Workstreams

1. **Main session (this)**: Orchestration, implementation, commits
2. **Eval sessions**: Continuous parallel eval runs during development
3. **Research agents**: Theory research for upcoming phases
4. **Remote sessions**: Long-running experiments (teacher-student training)

### Resource Management

- Max 4 concurrent eval processes (API rate limit)
- Remote sessions for experiments > 30 min
- All results logged to `/tmp/eval_*` with timestamps

## Learning Theory Research Agenda

### For Phase 2 (Metacognition)

- [ ] Metacognitive monitoring accuracy in LLMs
- [ ] Calibration of confidence in AI systems
- [ ] Dunning-Kruger effect in language models

### For Phase 4 (Teaching)

- [ ] Effective tutoring strategies (Chi 2009)
- [ ] Scaffolding in intelligent tutoring systems
- [ ] Conversational agents for education (review)
- [ ] Zone of Proximal Development operationalization

### For Phase 5 (Causal/Counterfactual)

- [ ] Pearl's causal hierarchy and LLMs
- [ ] Counterfactual reasoning in children vs AI
- [ ] Causal discovery from observational data

## Method Logging

### Entry Format

```
[DATE] [PHASE] [ACTION]
Method: What was tried
Result: What happened (scores, observations)
Insight: What was learned
Next: What this suggests for next iteration
```

### Log Location

- Session notes: /tmp/SESSION_SUMMARY_2026-02-19.md (updated)
- Eval results: /tmp/eval\_\*/ (per-run)
- Code changes: git commits on feat/issue-2394-eval-harness-3scenario
- Theory notes: Specs/LEARNING_THEORY_NOTES.md (to be created)
