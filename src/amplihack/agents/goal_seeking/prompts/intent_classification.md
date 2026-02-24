# Intent Classification Prompt

Classify this question. Does it require:
(a) simple recall - direct fact lookup
(b) mathematical computation - arithmetic, counting, differences
(c) temporal comparison/ordering - comparing values across time periods, tracking changes, describing trends
(d) multi-source synthesis - combining information from different sources
(e) contradiction resolution - handling conflicting information
(f) incremental update - finding the MOST RECENT or UPDATED information. Use this when the question asks about a SINGLE entity's current state or history (keywords: "how many now", "current", "latest", "updated", "changed", "how did X change", "trajectory", "complete history", "describe X's achievement/record/progress")

Question: {question}

Return ONLY a JSON object:
{{"intent": "one of: simple_recall, mathematical_computation, temporal_comparison, multi_source_synthesis, contradiction_resolution, incremental_update", "needs_math": true/false, "needs_temporal": true/false, "reasoning": "brief explanation"}}
