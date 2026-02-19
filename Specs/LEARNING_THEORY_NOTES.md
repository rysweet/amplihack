# Learning Theory Implementation Notes

## Date: 2026-02-19

## Source: Research agents analyzing 10 pedagogy theories + 8 child development theories

---

## Top 8 Implementable Strategies (Priority Order)

### 1. Active Retrieval Protocol (Testing Effect + Spaced Repetition)

- **Source**: Roediger & Karpicke 2006, LECTOR 2025
- **Principle**: Retrieval practice >> re-studying. Space at expanding intervals.
- **Implementation**: After teaching, re-test at expanding intervals. Failed = reset interval.
- **Impact**: Single most impactful strategy per cognitive science
- **Status**: Not yet implemented

### 2. Self-Explanation Prompting (Chi 1994 + Elaborative Interrogation)

- **Source**: Chi 1994 (doubled learning gains), Pressley 1987
- **Principle**: "Why does this work?" forces active integration with prior knowledge
- **Implementation**: After each teaching unit, teacher prompts student to explain "why"
- **Impact**: 2x learning gains in original study
- **Status**: Not yet implemented

### 3. Adaptive Scaffolding (Vygotsky ZPD + Bloom's)

- **Source**: Vygotsky 1978, Bloom's taxonomy
- **Principle**: Pitch difficulty just above current level, remove support as competence grows
- **Implementation**: Track per-topic scaffolding_level, promote/demote based on success rate
- **Status**: Not yet implemented

### 4. Role Reversal (Feynman + Reciprocal Teaching)

- **Source**: Feynman technique, Palincsar & Brown 1984
- **Principle**: Student teaches back = reveals understanding gaps
- **Implementation**: Periodically require student to explain concept to teacher
- **Status**: Not yet implemented

### 5. Interleaved Practice (Kornell & Bjork 2008)

- **Source**: Kornell & Bjork 2008
- **Principle**: Mix topics (ABCABC) >> block topics (AABBCC)
- **Implementation**: Round-robin across topics, track discrimination accuracy
- **Status**: Not yet implemented

### 6. Metacognitive Calibration (Dunlosky & Metcalfe 2009, MUSE 2024)

- **Source**: MUSE framework arXiv 2024
- **Principle**: Track confidence-vs-performance, flag overconfidence
- **Implementation**: Already have ReasoningTrace + metacognition_grader.py
- **Status**: PARTIALLY IMPLEMENTED (grader exists, not yet integrated into teaching)

### 7. Concept Graph Assessment (Novak & Canas 2008)

- **Source**: Concept mapping research
- **Principle**: Structured knowledge output reveals understanding quality
- **Implementation**: Student outputs (concept, relationship, concept) triples
- **Status**: Graph structure exists in HierarchicalMemory, not used for assessment

### 8. Progressive Role Transfer (Reciprocal Teaching)

- **Source**: Palincsar & Brown 1984
- **Principle**: Transfer summarize/question/clarify/predict roles to student
- **Implementation**: State machine with 4 ownership flags
- **Status**: Not yet implemented

---

## Key Research Findings (2024-2026)

### LLM-as-Teacher Systems

- TeachLM (2025): Even best LLM tutors achieve only 5-15% student talk time vs 30% for humans
- LECTOR (2025): LLM-enhanced spaced repetition achieves 90.2% retention
- Multi-teacher distillation (WSDM 2025): Student can outperform individual teachers
- Training LLM tutors (arXiv 2025): DPO fine-tuning on dialogue outcomes matches GPT-4o

### Bloom's 2-Sigma Problem

- 1-on-1 tutoring = +2 standard deviations over classroom
- AI tutors showing promise: Kestin 2024 showed 2x learning gains with GPT-4 tutor
- Key gap: AI tutors are too talk-heavy, need more student active processing

### Child Development Patterns for Progressive Learning

- Schema theory: Assimilation (strengthen) vs accommodation (restructure)
- Working memory limits: ~7 items, force chunking and prioritization
- Piaget stages: Gate capabilities behind demonstrated competence
- Novice→Expert: Flat facts → chunked groups → principle-organized hierarchies

---

## Integration with Current System

### Already Implemented

- ReasoningTrace captures plan/search/evaluate steps
- Metacognition grader scores 4 dimensions
- Teaching session with separate memory databases
- Graph-based memory with similarity edges

### Next to Implement (Phase by Phase)

1. **Self-explanation in TeachingSession**: Teacher asks "why" after each concept
2. **Concept graph assessment**: Student produces structured triples, teacher evaluates
3. **Adaptive scaffolding**: Track difficulty level, adjust based on student performance
4. **Spaced repetition**: Re-test previously taught concepts at expanding intervals
5. **Role reversal**: Student teaches back to teacher periodically

### Eval Metrics to Add

- Student talk ratio (% of dialogue from student)
- Bloom's level distribution (% of tasks at each level)
- Calibration accuracy (confidence vs performance)
- Transfer performance (novel problems)
- Knowledge graph density (triples per concept)
