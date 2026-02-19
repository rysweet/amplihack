# Sufficiency Evaluation Prompt

Can I answer this question with these facts?

Question: {question}
Question type: {intent_type}

Available facts:
{facts_summary}

Evaluate:

1. Do I have ALL the specific data points needed?
2. What is STILL MISSING (if anything)?
3. Confidence I can answer correctly (0.0-1.0)?

Return ONLY a JSON object:
{{"sufficient": true/false, "missing": "what's missing or empty string", "confidence": 0.8, "refined_queries": ["query if more search needed"]}}
