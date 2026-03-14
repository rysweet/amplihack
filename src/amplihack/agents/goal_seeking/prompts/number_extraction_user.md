# Number Extraction User Prompt

Extract the numbers needed to answer this math question.

Question: {{question}}
Math type: {{math_type}}

Facts:
{{facts_text}}

Return ONLY a JSON object:
{
"numbers": {"label1": number1, "label2": number2},
"expression": "arithmetic expression using the numbers (e.g., '(2.3 - 2.0) / 2.0 \* 100')",
"description": "brief description of what the expression computes"
}

Rules:

- Use ONLY numbers that appear explicitly in the facts
- For percentage: (new - old) / old \* 100
- For delta: new - old
- For ratio: numerator / denominator
- For comparison: list the values being compared
- The expression must use ONLY digits, +, -, \*, /, parentheses, and decimal points
- If you cannot find the needed numbers, return {"numbers": {}, "expression": "", "description": "insufficient data"}
