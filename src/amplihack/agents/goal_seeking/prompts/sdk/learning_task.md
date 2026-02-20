## Learning Task Instructions

When given content to learn from:

1. **Extract key facts** - Identify the most important claims and data points
2. **Categorize** - Group facts by topic/domain
3. **Store with context** - Use `store_fact` with descriptive context and appropriate confidence:
   - 0.9-1.0: Verified facts from authoritative sources
   - 0.7-0.8: Well-supported claims
   - 0.5-0.6: Plausible but unverified claims
   - 0.3-0.4: Uncertain or contradicted information
4. **Cross-reference** - Use `verify_fact` to check against existing knowledge
5. **Identify gaps** - Use `find_knowledge_gaps` to note what else should be learned
6. **Summarize** - Report what was learned and what remains unknown

## Content Types

Handle different content types appropriately:

- **Factual text**: Extract discrete facts with high confidence
- **Opinion pieces**: Lower confidence, note source perspective
- **Technical docs**: Extract procedures and specifications precisely
- **Historical content**: Include temporal context in fact storage
- **Scientific papers**: Note methodology alongside findings
