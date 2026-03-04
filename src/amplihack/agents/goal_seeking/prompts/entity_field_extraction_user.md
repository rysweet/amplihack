# Entity Field Extraction User Prompt

Extract the entity and field from this temporal question.

Question: {{question}}

Return ONLY a JSON object:
{"entity": "the entity name", "field": "the field/attribute being asked about"}

Examples:

- "What WAS the Atlas deadline BEFORE the first change?" -> {"entity": "Atlas", "field": "deadline"}
- "What was the original team size?" -> {"entity": "team", "field": "size"}
- "Who led the project BEFORE the leadership change?" -> {"entity": "project", "field": "leader"}
