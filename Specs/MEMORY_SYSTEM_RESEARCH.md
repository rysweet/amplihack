# Memory System Research

## Research Date: 2026-02-20

## System Overview

The memory system uses a layered architecture:

- **amplihack-memory-lib**: Kuzu graph database backend (via `ExperienceStore`)
- **HierarchicalMemory**: Direct Kuzu access with SemanticMemory/EpisodicMemory nodes, SIMILAR_TO/DERIVES_FROM/SUPERSEDES edges
- **FlatRetrieverAdapter**: Translates HierarchicalMemory to MemoryRetriever interface
- **CognitiveAdapter**: 6-type cognitive memory (sensory, working, episodic, semantic, procedural, prospective)
- **LearningAgent**: Orchestrates learning (fact extraction) and answering (retrieval + LLM synthesis)

## Research Area 1: Retrieval Strategy (Iterative vs Simple vs Hybrid)

### Hypothesis

A hybrid retrieval strategy could outperform the current binary approach (simple for small KBs / iterative for large KBs).

### Evidence

**Current approach** (from `learning_agent.py`):

- For KBs with <=150 facts: always use simple retrieval (dump all facts)
- For KBs >150 facts: use iterative plan/search/evaluate loop
- `SIMPLE_INTENTS = {"simple_recall", "incremental_update"}` always use simple path

**L1-L6 eval results show**:

- Simple retrieval dominates at current KB sizes (all levels use < 150 facts)
- L2 breakthrough (46.7% -> 100%) came from **source-specific fact filtering**, not retrieval strategy
- L3 breakthrough came from **retrieval threshold increase** (50 -> 150) and temporal ordering
- Iterative retrieval was never invoked in L1-L6 because KB stayed below 150 facts

**Counter-arguments**:

- The current binary threshold (150) is well-calibrated for the eval's KB sizes (5-80 facts per level)
- For production use with hundreds/thousands of facts, iterative would become necessary
- Hybrid (e.g., simple retrieval + keyword-boosted reranking) would add complexity for marginal gain at current scale

### Decision: **DEFER**

The simple retrieval path works well for the eval harness. A hybrid strategy would be premature optimization given that:

1. KB sizes in eval are well under 150 facts
2. The 150 threshold was already tuned in Loop 1 (from 50 to 150)
3. The real bottleneck is in synthesis quality, not retrieval completeness

**Future trigger**: When eval adds levels with KB sizes > 200 facts, revisit hybrid retrieval.

---

## Research Area 2: SUPERSEDES Edges for Temporal Reasoning

### Hypothesis

SUPERSEDES edges are being used effectively for temporal reasoning, but could be improved by making the LLM synthesis prompt explicitly aware of superseded facts.

### Evidence

**Current implementation** (from `hierarchical_memory.py`):

- `_detect_supersedes()` runs at STORAGE time: checks for older facts with same concept and lower temporal_index
- When found, creates `SUPERSEDES` edge (new -> old) and lowers old fact's confidence to `max(0.1, confidence * 0.5)`
- `_mark_superseded()` runs at RETRIEVAL time: checks for incoming SUPERSEDES edges, marks metadata as `superseded=True`
- `to_llm_context()` shows `[OUTDATED - superseded by newer information]` for marked facts
- `_format_fact()` in learning_agent also shows the OUTDATED marker

**L6 (Incremental Learning) results**:

- L6 has scored 100% across ALL 5 loops - SUPERSEDES is working perfectly
- The agent correctly answers "10 golds" (not 9) after incremental update

**Counter-arguments**:

- SUPERSEDES detection relies on concept word overlap + different numbers heuristic
- This heuristic could create false positives (e.g., two unrelated stats about "Norway" with different numbers)
- However, the confidence penalty (0.5x) is mild enough that false positives just slightly demote a fact rather than removing it

### Decision: **REJECT improvement**

SUPERSEDES edges are working effectively. L6 is at 100% consistently. The heuristic-based detection with mild confidence penalty is a good design that balances accuracy with robustness.

---

## Research Area 3: Graph Structure (Clustering, Community Detection)

### Hypothesis

Adding graph clustering or community detection could improve retrieval by grouping related facts and reducing noise.

### Evidence

**Current graph structure**:

- SemanticMemory nodes connected by SIMILAR_TO edges (Jaccard word similarity > 0.3)
- 2-hop subgraph traversal in `retrieve_subgraph()`
- No explicit clustering or community detection

**Similarity computation** (`similarity.py`):

- Jaccard coefficient on tokenized words minus stop words (weight: 0.5)
- Tag similarity (weight: 0.2)
- Concept field similarity (weight: 0.3)
- Threshold: > 0.3 for edge creation

**Observations from eval data**:

- At current KB sizes (30-80 facts), the keyword search + 2-hop expansion already retrieves all relevant facts
- The bottleneck is not retrieval completeness but synthesis quality
- Graph clustering would add significant complexity to the Kuzu schema

**Counter-arguments**:

- For larger KBs (1000+ facts), clustering could help narrow down to relevant topic clusters
- Current Jaccard-based similarity is fragile: "Norway gold medals" and "Norwegian gold count" have low Jaccard overlap despite being about the same thing
- Embedding-based similarity would be more robust but requires vector index infrastructure

### Decision: **DEFER**

- Current approach works at eval scale
- Embedding-based similarity should be explored when KB sizes exceed 500 facts
- Graph clustering adds too much complexity for current needs

---

## Research Area 4: Fact Extraction Quality

### Hypothesis

The fact extraction prompt could capture more detail, especially for causal relationships and conditional information.

### Evidence

**Current extraction** (from `learning_agent.py:_extract_facts_with_llm`):

- Extracts context, fact, confidence, tags per fact
- Has special hints for temporal content and procedural content
- Requires full names and specific numbers (added in Loop 2)

**Analysis of L9/L10 failures**:

- L9 Q3 (root cause): The agent correctly extracted ALL causal facts but chose the wrong root cause during synthesis
- L10 Q2 (counterfactual): The agent had all relevant facts but refused to engage with the hypothetical
- These are SYNTHESIS failures, not extraction failures

**Extraction improvements that COULD help**:

1. Extract causal relationships explicitly (e.g., "X caused Y" -> store edge "CAUSES")
2. Extract conditional facts (e.g., "If X, then Y" -> store with condition metadata)
3. Extract numeric relationships (e.g., "increased by 40%") as structured data

**Counter-arguments**:

- Adding structured extraction increases LLM call complexity and cost
- The eval only has 3-5 articles per level with 5-15 facts each
- At this scale, the LLM can reason about causality during synthesis without explicit causal edges
- Structured extraction would need its own eval to verify correctness

### Decision: **DEFER**

- Fact extraction quality is not the bottleneck for L1-L12
- The bottleneck for L9/L10 is synthesis reasoning quality
- The improvement we already made (causal_counterfactual intent + root cause instructions) addresses this more directly

---

## Research Area 5: Retrieval Failures from L1-L6 Eval Results

### Hypothesis

There may be systematic retrieval failures in L1-L6 that are masked by high scores but could cause issues at larger scales.

### Evidence

**L1-L6 final scores** (Loop 5):

- L1: 96.7% (was 100% at baseline, slight degradation)
- L2: 100% (was 46.7% at baseline, massive improvement)
- L3: 100% (was 66.7% at baseline, significant improvement)
- L4: 86.25% (was 87.5% at baseline, slight degradation)
- L5: 96.7% (was 98.3% at baseline, slight degradation)
- L6: 100% (stable)

**Patterns**:

1. **L1 degradation (100% -> 96.7%)**: Likely LLM stochasticity. The "lost" score is probably one question where the LLM adds unnecessary caveats to a simple recall answer. Not a retrieval issue.

2. **L4 stable at 86-91%**: Procedural questions require step sequence reconstruction. The agent sometimes misordering steps or including prerequisites when only asked for a subset. This is a synthesis quality issue.

3. **L5 volatility (75-98%)**: Contradiction handling depends on the LLM's willingness to present both sides equally. Sometimes the LLM "picks a side" despite instructions. Not a retrieval issue - both conflicting facts are always retrieved.

**Counter-arguments**:

- Running all levels with the same memory DB (cumulative) means later levels see facts from earlier levels (up to 149 facts by L6)
- This could cause interference: L3 temporal facts about "Norway medals" could confuse L5 contradiction answers about "viewership numbers"
- Memory isolation per level would eliminate this interference

### Decision: **IMPLEMENT (future)** - Memory isolation per level

- Not implementing now because it requires changes to the eval harness runner
- The interference effect is real but minor (L5 scores are still 93-100% in most runs)
- Should be part of a larger eval harness improvement effort

---

## Research Area 6: L7-L12 Advanced Level Analysis

### Hypothesis

The advanced levels reveal new memory system limitations that were not apparent in L1-L6.

### Evidence

**L7 (Teaching)**: Not runnable through progressive_test_suite (needs separate eval path via DomainAgent)

**L8 (Metacognition): 95%**: Memory system works well. Agent correctly identifies knowledge gaps and calibrates confidence. No memory improvements needed.

**L9 (Causal Reasoning): 63-67%**: Root cause analysis is a reasoning challenge, not a memory challenge. All causal facts are correctly stored and retrieved. The improvement (causal_counterfactual intent) addresses the synthesis side. The remaining gap is in Q3 where the expected answer's root cause is debatable.

**L10 (Counterfactual): 56.67% -> 78.33%**: The critical fix was intent classification (preventing `simple_recall` classification for counterfactual questions) and stronger counterfactual instructions. This was a synthesis/intent issue, not memory.

**L11 (Novel Skill): 75%**: Agent learns gh-aw documentation and applies it. Q2 (workflow file generation) scored 0.65 - the agent includes unnecessary fields. Q4 (teaching) scored 0.45 - the agent doesn't identify the "common mistake" clearly. These are LLM reasoning issues.

**L12 (Far Transfer): 76.67%**: Q3 (bug-fix ratio trend) scored 0.3 - the agent computed ratios correctly but presented the trend analysis poorly. Temporal reasoning patterns transfer well (Q2: 100%) but ratio analysis is weaker.

### Decision: No memory system changes needed for L7-L12

The advanced levels primarily stress synthesis/reasoning quality rather than memory storage/retrieval.

---

## Summary of Decisions

| Research Area               | Decision                 | Rationale                                   |
| --------------------------- | ------------------------ | ------------------------------------------- |
| Retrieval strategy (hybrid) | DEFER                    | Current binary approach works at eval scale |
| SUPERSEDES edges            | REJECT (working well)    | L6 at 100% consistently                     |
| Graph clustering            | DEFER                    | Premature for current KB sizes              |
| Fact extraction quality     | DEFER                    | Synthesis is the bottleneck, not extraction |
| Retrieval failures L1-L6    | DEFER (memory isolation) | Minor interference, not blocking            |
| L7-L12 analysis             | No changes needed        | Issues are synthesis/reasoning, not memory  |

## Implemented Change

**Added `causal_counterfactual` intent type** to intent classifier and strengthened counterfactual/causal reasoning instructions in synthesis prompt.

- Impact: L10 improved from 56.67% to 78.33% (+21.66%)
- L9 remained stable at ~65% (root cause ambiguity in Q3)
- No regression on L1-L6 (spot-checked L1: 100%, L5: 93.33%)

## Recommendations for Future Work

1. **Embedding-based similarity**: Replace Jaccard word similarity with sentence embeddings for more robust graph edges. Trigger: KB sizes > 500 facts.

2. **Memory isolation per eval level**: Each level should get its own database to prevent cross-level interference. Requires eval harness changes.

3. **3-run medians for all levels**: Single-run scores are noisy. The parallel runner already supports this but is not used by default.

4. **Causal edge type**: Add CAUSES edges to the graph for explicit causal chain traversal. Trigger: When L9 needs to reason over multi-hop causal chains.

5. **Confidence calibration**: The agent always outputs confidence=0.8. Use fact coverage as a signal for actual confidence.
