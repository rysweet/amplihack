# Synthesis Level Instructions

## L1 - Direct Recall

Provide a direct, factual answer based on the facts. State the answer clearly and concisely. Do NOT add arithmetic verification or computation - just report the facts as stored.

## L2 - Inference

Connect multiple facts to infer an answer. Explain your reasoning.

## L3 - Synthesis

Synthesize information from the facts to create a comprehensive answer.

## L4 - Procedural Application

Apply the knowledge to answer the question. For PROCEDURAL questions (describing workflows, steps, commands), reconstruct the exact ordered sequence of steps from the facts. Number each step. Include specific commands or actions at each step. Do not skip steps or add prerequisites that aren't in the facts.

---

# Intent-Specific Instructions

## Mathematical Computation (complex intents only)

- Extract the raw numbers from the facts FIRST
- Show all arithmetic step by step
- Write out each calculation explicitly (e.g., 26 - 18 = 8)
- When computing differences for multiple entities, do ALL of them
- Double-check every subtraction and addition
- Verify your final numerical answer by re-doing the computation

## Temporal Reasoning (complex intents only)

You MUST follow this exact process:

STEP A: Build a data table
Create a table with rows = entities (countries/people) and columns = time periods.
Fill in the EXACT numbers from the facts for each cell.
Example:
| Country | Day 7 Golds | Day 9 Golds | Day 10 Golds |
| Norway | 8 | 12 | 13 |

STEP B: Compute differences
For EACH entity, calculate: later_value - earlier_value = difference
Write out the arithmetic explicitly: '13 - 8 = 5'
Do this for EVERY entity, not just the one you think is the answer.

STEP C: Compare and conclude
List all computed differences side by side.
Only THEN identify which is largest/smallest/etc.

STEP D: Verify
Re-check your arithmetic. Recompute at least one difference to confirm.

CRITICAL RULES:

- NEVER skip the data table step
- NEVER guess differences - always compute them from the raw numbers
- Pay attention to WHICH metric is asked about (gold vs total vs other)
- When describing trends, state the EXACT change in each sub-period (e.g., '+4 golds Day 7→9, then +1 gold Day 9→10, total +5')

## Multi-Source Synthesis

- The answer requires combining information from MULTIPLE different sources/articles
- First, identify which facts come from which source (look at [Source: ...] labels)
- If the question asks about a SPECIFIC source/article (e.g., 'mentioned in the athlete article'):
  - Filter facts to ONLY those from that specific source
  - COUNT the relevant items from that source precisely
  - Do NOT use data from other sources for this part
- When finding connections ACROSS sources, cite the specific numbers from each
- When counting entities (athletes, events, etc.), list them explicitly

## Contradiction Resolution

- Present both viewpoints with their sources if available
- Explain why they might differ (different time periods, different measurements, etc.)
- Let the questioner decide which to trust
- If one source seems more reliable or recent, note that

## Counterfactual / Hypothetical Reasoning

This question asks you to imagine an alternative scenario. You MUST:

1. Start from the ACTUAL facts as your baseline
2. Apply the hypothetical change (remove X, change timing, etc.)
3. Reason through the CONSEQUENCES of that change step by step
4. Compare the hypothetical outcome to ALL other entities (not just the one asked about)
5. Draw a clear conclusion about how things would be different

Do NOT refuse to answer by saying the hypothetical isn't in the facts.
The whole point is to REASON about what WOULD happen based on what you DO know.
