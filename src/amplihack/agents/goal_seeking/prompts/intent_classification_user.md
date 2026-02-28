# Intent Classification User Prompt

Classify this question. Does it require:
(a) simple recall - direct fact lookup
(b) mathematical computation - arithmetic, counting, differences
(c) temporal comparison/ordering - comparing values across time periods, tracking changes, describing trends
(d) multi-source synthesis - combining information from different sources
(e) contradiction resolution - handling conflicting information
(f) incremental update - finding the MOST RECENT or UPDATED information. Use this when the question asks about a SINGLE entity's current state or history (keywords: "how many now", "current", "latest", "updated", "changed", "how did X change", "trajectory", "complete history", "describe X's achievement/record/progress")
(g) causal_counterfactual - reasoning about causes, root causes, "why did X happen", OR hypothetical/counterfactual scenarios like "what if X", "if X had not happened", "without X", "would X still", "in a world where". These questions require reasoning from known facts to explore causes or alternate scenarios - they are NOT simple recall even though they may involve hypotheticals not in the data.
(h) ratio_trend_analysis - computing ratios or percentages AND analyzing whether they improve or worsen over time. Use when the question asks about "ratio", "rate", "per", "trend", "improving vs worsening"
(i) meta_memory - questions ABOUT the knowledge itself: "how many projects", "list all people", "count the teams", "what topics do you know about". These ask about the STRUCTURE or QUANTITY of stored knowledge, not about specific facts.

FEW-SHOT EXAMPLES:
Q: "Which country's individual athletes won the most medals mentioned in the athlete achievements article?"
A: {"intent": "multi_source_synthesis", "needs_math": false, "needs_temporal": false, "reasoning": "Asks about individuals from a specific article - needs source-specific synthesis"}

Q: "How many medals did Norway win between Day 7 and Day 9?"
A: {"intent": "temporal_comparison", "needs_math": true, "needs_temporal": true, "reasoning": "Requires comparing numbers across time periods"}

Q: "What caused Italy to improve from 3 golds in 2018 to 8 golds in 2026?"
A: {"intent": "causal_counterfactual", "needs_math": false, "needs_temporal": false, "reasoning": "Asks about causal chain of events"}

Q: "Which framework has the best bug-fix-to-feature ratio trend?"
A: {"intent": "ratio_trend_analysis", "needs_math": true, "needs_temporal": true, "reasoning": "Requires computing ratios and analyzing trend direction"}

Q: "How does Italy's 2026 gold medal performance compare to their previous best?"
A: {"intent": "multi_source_synthesis", "needs_math": false, "needs_temporal": false, "reasoning": "Comparing performance across sources/events, not computing temporal differences"}

Q: "How many projects are being tracked?"
A: {"intent": "meta_memory", "needs_math": false, "needs_temporal": false, "math_type": "none", "reasoning": "Asks about the count of stored entities, not about specific project details"}

Q: "List all team members you know about."
A: {"intent": "meta_memory", "needs_math": false, "needs_temporal": false, "math_type": "none", "reasoning": "Asks for enumeration of stored knowledge, not specific facts"}

Q: "By what percentage did the estimate exceed the actual cost?"
A: {"intent": "mathematical_computation", "needs_math": true, "needs_temporal": false, "math_type": "percentage", "reasoning": "Requires computing a percentage difference between two values"}

Question: {{question}}

Return ONLY a JSON object:
{"intent": "one of: simple_recall, mathematical_computation, temporal_comparison, multi_source_synthesis, contradiction_resolution, incremental_update, causal_counterfactual, ratio_trend_analysis, meta_memory", "needs_math": true/false, "needs_temporal": true/false, "math_type": "none|percentage|delta|ratio|comparison", "reasoning": "brief explanation"}
