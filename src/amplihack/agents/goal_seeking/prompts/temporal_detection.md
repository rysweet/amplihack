# Temporal Metadata Detection Prompt

Analyze this content for temporal markers (dates, day numbers, time references).
Extract any date or time ordering information.

Content (first 500 chars):
{content}

Return ONLY a JSON object:
{{"source_date": "YYYY-MM-DD or empty string", "temporal_order": "brief label like Day 7 or February 13 or empty string", "temporal_index": 0}}

Rules:

- source_date: The primary date mentioned (ISO format YYYY-MM-DD), or "" if none
- temporal_order: A brief label for ordering (e.g., "Day 7", "After Day 9"), or "" if none
- temporal_index: A numeric value for chronological sorting (e.g., day number 7, 9, 10), or 0 if none
