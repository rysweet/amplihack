# Fact Extraction User Prompt

Extract key facts from this content. For each fact, provide:

1. Context (what topic it relates to)
2. The fact itself (MUST include specific names, numbers, and entities)
3. Confidence (0.0-1.0)
4. Tags (relevant keywords)

CRITICAL RULES for fact extraction:

- Each NAMED PERSON must appear in at least one fact with their FULL NAME and COUNTRY
- Each SPECIFIC NUMBER must be preserved exactly (medals, dates, records)
- Extract ONE FACT PER PERSON mentioned, even if brief
- Never summarize multiple people as "various athletes" - name them individually
  {{temporal_hint}}{{procedural_hint}}

Content:
{{content}}

Respond with a JSON list like:
[
{
"context": "Topic name",
"fact": "The fact itself",
"confidence": 0.9,
"tags": ["tag1", "tag2"]
}
]
