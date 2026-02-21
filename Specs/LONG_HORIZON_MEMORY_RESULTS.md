# Long-Horizon Memory Evaluation Results

## Executive Summary

The long-horizon memory stress test evaluates the goal-seeking agent's ability to
retain, organize, and retrieve information across extended dialogue sequences. The
evaluation uses deterministic, template-generated dialogue content across 8 information
blocks, then tests recall with 7 categories of increasingly difficult questions.

## Quick Variant Results (100 turns, 20 questions)

**Overall Score: 88.00%**

| Category              | Avg Score | Min   | Max   | Questions |
| --------------------- | --------- | ----- | ----- | --------- |
| Temporal Evolution    | 96.0%     | 80.0% | 100%  | 5         |
| Numerical Precision   | 100.0%    | 100%  | 100%  | 4         |
| Distractor Resistance | 92.5%     | 85.0% | 100%  | 2         |
| Cross Reference       | 87.5%     | 75.0% | 100%  | 2         |
| Source Attribution    | 82.5%     | 65.0% | 100%  | 2         |
| Needle in Haystack    | 75.0%     | 0.0%  | 100%  | 4         |
| Meta Memory           | 55.0%     | 55.0% | 55.0% | 1         |

### Memory Statistics

- Semantic nodes stored: 346
- Episodic nodes stored: 100
- Total nodes: 446
- Similarity edges: 3,200
- Derives-from edges: 326
- Facts delivered: 175
- Learning time: 932s (~15.5 min)
- Questioning + grading time: 298s (~5 min)

## Analysis by Category

### Temporal Evolution (96.0%) -- Strongest Category

The agent excels at temporal reasoning, correctly tracking evolving facts across
the conversation:

- **Atlas deadline changes**: Correctly traced June 15 -> August 3 -> September 20
  (score: 1.0)
- **Atlas original deadline**: Correctly identified June 15 (score: 1.0)
- **Deadline change count**: Correctly counted 2 changes (score: 1.0)
- **Echo budget**: Correctly identified $2.2M current budget (score: 1.0)
- **Atlas post-rollout**: 80% score -- mostly correct but missed some details

**Why it works well**: The SUPERSEDES edge mechanism in HierarchicalMemory correctly
marks old facts as superseded by newer facts. The temporal_metadata tracking preserves
chronological ordering, and the retrieve_subgraph method surfaces both current and
historical values with appropriate confidence weighting.

### Numerical Precision (100.0%) -- Perfect

All 4 numerical questions scored 100%:

- Server migration cost: $450K (correct)
- Audit vs vendor difference: $63K (correct math)
- Q2 budget overrun: 15% (correct)
- Customer acquisition cost trend: $127 down from $156 (correct)

**Why it works well**: Numerical values are stored as explicit facts with high
confidence. The keyword-based retrieval finds them reliably because numbers are
distinctive tokens.

### Distractor Resistance (92.5%)

The agent resists noise well, correctly ignoring Block 8 distractors:

- Priya Patel's allergy (none): 85% -- correctly answered but lost some points
  on confidence calibration
- Sprint velocity (47 points): 100% -- precise with contextual detail

### Cross Reference (87.5%)

Cross-referencing facts from different blocks works well but not perfectly:

- Fatima -> Yuki succession on Project Echo: 100%
- Sarah Chen + Atlas + Innovation Award: 75% -- got the project right but
  partially missed the award detail

### Source Attribution (82.5%)

Attributing facts to their sources is the area most needing improvement:

- Q3 revenue from 3 sources: 100% -- perfect source attribution
- Server migration audit vs vendor: 65% -- partially attributed, missed the
  explicit $63K consulting fee connection

### Needle in Haystack (75.0%)

Mixed results for simple fact recall:

- Sarah Chen's birthday: 100%
- James O'Brien's allergy (gluten): 100%
- Yuki Tanaka's degree: 100%
- Fatima Al-Hassan's hobby (calligraphy): **0%** -- fact was not retrievable

**Why the failure**: Fatima's hobby was stored deep in Block 1. With 346 semantic
nodes, the keyword search for "Fatima Al-Hassan hobby" likely failed because:

1. The fact was stored as "calligraphy" under a compound topic
2. The 100-node similarity scan window may not have reached this older node
3. The query keywords ("Fatima", "hobby") may not have matched the stored concept

### Meta Memory (55.0%)

The weakest category -- the agent struggles to reason about its own knowledge:

- "How many projects?" -- Agent answered 2 (correct is 5). The agent cannot
  aggregate across all stored facts to count distinct project entities.

**Why it fails**: Meta-memory questions require scanning ALL stored facts and
performing aggregation (COUNT DISTINCT). The current retrieval pipeline searches
by keyword relevance, not by exhaustive enumeration. Improving this would require
a dedicated "meta-query" strategy that runs a Cypher aggregation query directly.

## Where Retrieval Breaks Down

### Fact Count Threshold

At 346 semantic nodes (from 100 turns, 175 facts delivered):

- The 100-node similarity scan window covers ~29% of total knowledge
- Older facts from Block 1 can fall outside the retrieval window
- The keyword-based seed search mitigates this, but relies on query terms
  matching stored content/concept fields

### Problematic Patterns

1. **Person attributes stored under compound topics**: When the LLM extracts
   facts, it may create context labels like "Personal Information - Hobbies"
   rather than "Fatima Al-Hassan hobbies", making keyword retrieval harder.

2. **Meta-queries**: Any question asking "how many X" requires exhaustive
   scanning, which the current pipeline does not support.

3. **Source attribution partial failures**: When multiple sources report on the
   same topic, the retrieval may only surface some of the source-labeled facts.

## SUPERSEDES at Scale

The SUPERSEDES mechanism works well at this scale (100 turns):

- Atlas deadline: correctly superseded twice (June 15 -> Aug 3 -> Sep 20)
- Atlas security: superseded from "5 vulns" -> "2 remain" -> "all resolved"
- Atlas rollout: superseded through 30% -> 70% -> 100%
- Atlas performance: superseded from 150ms -> 85ms

The temporal_index metadata enables chronological ordering, and the confidence
decay on superseded facts (0.5x multiplier) correctly deprioritizes outdated
information in retrieval results.

## Recommendations

1. **Increase similarity scan window**: The current 100-node window should scale
   with total knowledge size (e.g., min(total_nodes \* 0.3, 500)).

2. **Add meta-query strategy**: For questions containing "how many", "count",
   "list all", route to a Cypher aggregation query instead of keyword search.

3. **Improve fact storage concept labels**: Ensure person+attribute facts always
   include the person's name in the concept field for reliable retrieval.

4. **Source attribution enrichment**: When storing contradictory source reports,
   tag them explicitly with source identity for better attribution retrieval.

## Micro Variant Validation (10 turns, 5 questions)

As a baseline sanity check, the 10-turn variant scored 28% overall, confirming
that questions about data not yet loaded correctly score 0%.

| Category            | Score | Expected                         |
| ------------------- | ----- | -------------------------------- |
| Needle in Haystack  | 100%  | Block 1 data present -- correct  |
| Cross Reference     | 40%   | Partial Block 1 data -- expected |
| Temporal Evolution  | 0%    | No Block 2+ data -- correct      |
| Numerical Precision | 0%    | No Block 5 data -- correct       |
| Source Attribution  | 0%    | No Block 6 data -- correct       |

## Test Suite

43 unit tests covering:

- Dialogue generation (10 tests): turn counts, block coverage, reproducibility
- Ground truth tracking (6 tests): entity tracking, superseded values
- Question generation (7 tests): category distribution, unique IDs, expected answers
- Scoring logic (6 tests): dimension scores, report serialization, JSON extraction
- Eval class (5 tests): generate, run_dialogue, evaluate methods
- Data integrity (7 tests): data structure completeness, counts
