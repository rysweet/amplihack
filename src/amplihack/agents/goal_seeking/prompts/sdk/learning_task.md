## Learning Task Instructions

When processing content to learn from:

### Content Types
- **Factual text**: Extract discrete facts, dates, names, relationships
- **Procedural text**: Extract step-by-step processes and their prerequisites
- **Analytical text**: Extract claims, evidence, and conclusions separately
- **Comparative text**: Extract entities being compared and their attributes

### Extraction Guidelines
1. Break content into atomic facts (one claim per fact)
2. Assign confidence based on source reliability
3. Tag facts with relevant categories
4. Link related facts to existing knowledge
5. Note any contradictions with stored knowledge

### Storage Format
For each extracted fact, store with:
- **context**: The topic or domain this fact belongs to
- **fact**: The actual knowledge claim (keep under 200 words)
- **confidence**: Your confidence in this fact (0.0 to 1.0)

### Quality Checks
- Reject vague or unsupported claims (confidence < 0.3)
- Flag contradictions for human review
- Prefer primary sources over secondary
- Note temporal context (when was this true?)
