# Plan Retrieval Prompt

Given this question, what specific information do I need to find in a knowledge base?

Question: {question}
Question type: {intent_type}
{extra_instruction}

Generate 2-5 SHORT, TARGETED search queries (keywords/phrases) that would find the needed facts.
Each query should target ONE specific piece of information.

Return ONLY a JSON object:
{{"search_queries": ["query1", "query2", ...], "reasoning": "brief explanation of search strategy"}}

---

# Intent-Specific Plan Instructions

## Multi-Source Synthesis

Strategy:

1. First, identify the DISTINCT topics/sources this question touches (e.g., current standings, historical records, athlete profiles)
2. Generate at least ONE search query for EACH distinct topic
3. Include one BROAD query using the main subject of the question
4. Include one query specifically targeting COMPARISONS or RELATIONSHIPS between topics

You MUST generate at least 3 queries covering different aspects of the question.

## Temporal Comparison

Strategy:

1. Extract EVERY time period mentioned in the question (e.g., 'Day 7', 'Day 10', 'February 13')
2. Generate a SEPARATE search query for EACH time period found
3. Each query MUST include the exact time marker as a keyword (e.g., 'Day 7 medals', 'Day 10 gold')
4. Also include a query for the specific metric being compared

CRITICAL: If the question mentions 'Day 7 to Day 10', you need queries for Day 7, Day 9, AND Day 10.
Do NOT skip any time period - missing data makes computation impossible.
