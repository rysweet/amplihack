# Answer Synthesis Prompt

Answer this question using the provided facts.

Question: {question}
Level: {question_level} - {instruction}
{extra_instructions}{contradiction_instructions}{counterfactual_instructions}
{summary_section}
{context_str}

Provide a clear, well-reasoned answer. If the facts don't fully answer the question, say so.
