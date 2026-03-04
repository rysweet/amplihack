# Knowledge Gaps User Prompt

Given these facts about '{{topic}}', what important information is MISSING?

Facts:
{{facts_text}}

List 2-4 specific gaps (things we don't know but should).
Return ONLY a JSON object: {"gaps": ["gap1", "gap2"], "overall_coverage": "low/medium/high"}
