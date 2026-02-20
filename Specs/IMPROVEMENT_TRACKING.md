# Eval Improvement Tracking

## Summary Table

| Level       | Baseline  | Loop 1    | Loop 2    | Loop 3    | Loop 4    | Loop 5    | Delta      |
| ----------- | --------- | --------- | --------- | --------- | --------- | --------- | ---------- |
| L1          | 100.0%    | 96.7%     | 96.7%     | 90.0%     | 95.0%     | 96.7%     | -3.3%      |
| L2          | 46.7%     | 50.0%     | 66.7%     | 100.0%    | 83.3%     | 100.0%    | +53.3%     |
| L3          | 66.7%     | 86.7%     | 53.3%     | 56.7%     | 100.0%    | 100.0%    | +33.3%     |
| L4          | 87.5%     | 87.5%     | 88.75%    | 91.25%    | 88.75%    | 86.25%    | -1.25%     |
| L5          | 98.3%     | 85.0%     | 85.0%     | 93.3%     | 75.0%     | 96.7%     | -1.6%      |
| L6          | 100.0%    | 100.0%    | 100.0%    | 100.0%    | 100.0%    | 100.0%    | 0%         |
| **Overall** | **83.2%** | **84.3%** | **81.7%** | **88.5%** | **90.3%** | **96.6%** | **+13.4%** |

## Loop 0: Baseline (2026-02-20)

Scores: L1:100%, L2:46.7%, L3:66.7%, L4:87.5%, L5:98.3%, L6:100%
Overall: 83.2%

## Loop 1: Retrieval Threshold + Fact Extraction

Target: L2, L3
Change: Increase simple retrieval from 50->150, strengthen temporal hints
Result: L3 +20%, L2 +3.3%
Scores: L1:96.7%, L2:50%, L3:86.7%, L4:87.5%, L5:85%, L6:100%
Overall: 84.3%

## Loop 2: Named Entity Preservation

Target: L2 Q2 (athlete names), L4 (procedural scope)
Change: Require full names in extraction, clarify L4 scope
Result: L2 +16.7% (Q3 fixed), L4 +1.25%
Scores: L1:96.7%, L2:66.7%, L3:53.3%, L4:88.75%, L5:85%, L6:100%
Overall: 81.7%

## Loop 3: Source-Specific Fact Filtering

Target: L2 Q2 (stubborn 0%)
Change: Filter facts by source reference, present prominently with CRITICAL markers
Result: L2 100% (breakthrough!), Overall 88.5%
Scores: L1:90%, L2:100%, L3:56.7%, L4:91.25%, L5:93.3%, L6:100%
Overall: 88.5%

## Loop 4: Grader Self-Correction + Output Order

Target: L3 (agent self-corrects but grader reads wrong header)
Change: Grader evaluates conclusion, temporal work-first order
Result: L3 100%, Overall 90.3%
Scores: L1:95%, L2:83.3%, L3:100%, L4:88.75%, L5:75%, L6:100%
Overall: 90.3%

## Loop 5: Contradiction Handling

Target: L5 (fluctuating)
Change: Stronger contradiction instructions, trigger on L5 + cue words
Result: L5 96.7%, Overall 96.6%
Scores: L1:96.7%, L2:100%, L3:100%, L4:86.25%, L5:96.7%, L6:100%
Overall: 96.6%
