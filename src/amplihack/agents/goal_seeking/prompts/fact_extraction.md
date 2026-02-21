# Fact Extraction Prompt

Extract key facts from this content. For each fact, provide:

1. Context (what topic it relates to)
2. The fact itself
3. Confidence (0.0-1.0)
4. Tags (relevant keywords)
   {temporal_hint}{procedural_hint}

Content:
{content}

Respond with a JSON list like:
[
{{
    "context": "Topic name",
    "fact": "The fact itself",
    "confidence": 0.9,
    "tags": ["tag1", "tag2"]
  }}
]
