# Storytelling Synthesizer - Quick Reference

## One-Minute Overview

Transform any technical work (PRs, commits, features) into narratives for:

- Demo scripts (5-10 minutes)
- Blog posts (1,500+ words)
- Presentations (20-45 minutes)
- Marketing copy (varied)

**The formula**: Problem → Solution → Impact → Hook

## Quick Start Commands

### Transform PR to Demo

```
Claude: Convert this PR into a 7-minute demo script:
[Paste PR description]

Result: Ready-to-deliver demo with timing, hooks, talking points
```

### PR to Blog Post

```
Claude: Write a technical blog post outline from this PR:
[Paste PR and details]

Result: 1,500-word outline with sections, code examples, metrics
```

### Feature to Marketing

```
Claude: Create marketing copy for this feature:
[Paste feature specs and benefits]

Result: Value prop, before/after, customer scenarios, CTA
```

### Commits to Presentation

```
Claude: Design a 30-minute presentation outline:
[Describe technical topic]

Result: 15-slide outline with speaker notes and timing
```

## Four Core Narrative Templates

### 1. Demo Script (5-10 minutes)

```
[Hook - 30 sec] "Imagine if..."
[Problem - 1-2 min] "Here's what's broken..."
[Solution - 2-3 min] [Live demo]
[Metrics - 1 min] "Here's the impact..."
[Close - 30 sec] "This changes everything"
```

### 2. Blog Post (1,500-3,000 words)

```
[Problem] What's broken and why it matters
[Context] Why existing solutions fail
[Solution] How we fixed it (with code)
[Results] Metrics and validation
[Future] What this enables
```

### 3. Presentation (20-45 minutes)

```
[Problem] What's broken (3 min)
[Architecture] How we fixed it (5 min)
[Demo] It in action (8 min)
[Results] Impact and metrics (3 min)
[Roadmap] What's next (3 min)
[Close] Key takeaway (1 min)
```

### 4. Marketing Copy

```
[Headline] Outcome-focused promise
[Problem] What customer struggles with
[Before] Typical bad experience
[After] Amazing new experience
[Proof] Metrics and testimonials
[CTA] What to do next
```

## Key Principles

| Principle          | Example                                         |
| ------------------ | ----------------------------------------------- |
| Start with problem | 40% of time on why it matters                   |
| Be specific        | "95% faster" not "much faster"                  |
| Show, don't tell   | Demo, metrics, examples > words                 |
| Audience matters   | Engineers care about code, execs care about ROI |
| Medium matters     | 7-minute demo ≠ 30-minute talk                  |
| Use hooks          | Open with something surprising or provocative   |
| Vary pacing        | Mix explanation with excitement                 |
| End strong         | Close with implication, not just summary        |

## Hooks That Work

| Hook Type       | Example                                       |
| --------------- | --------------------------------------------- |
| Surprising stat | "95% of developers waste 10 hours/week on X"  |
| Question        | "What if you could cut time by 80%?"          |
| Problem         | "We've all experienced the frustration of..." |
| Bold claim      | "This changes how we think about..."          |
| Contradiction   | "The simplest solution was also the fastest"  |

## Audience Adaptations

### For Engineers

Focus: Technical novelty, elegant solutions, architecture
Include: Code samples, algorithm details, tradeoffs
Tone: Precise, technical, honest

### For Product Managers

Focus: User impact, business metrics, adoption
Include: Before/after, customer quotes, timelines
Tone: Outcome-focused, data-driven

### For Executives

Focus: Business value, ROI, strategic fit
Include: Revenue impact, cost savings, risk reduction
Tone: High-level, strategic, quantified

### For Users/Customers

Focus: Simplicity, benefits, how-to
Include: Specific examples, relatable scenarios
Tone: Non-technical, benefit-focused, friendly

### For Marketing

Focus: Differentiation, emotional resonance
Include: Customer stories, competitive advantage
Tone: Engaging, compelling, memorable

## Transformation Examples

### Example 1: PR → Demo (Quick)

**INPUT**:

```
PR: "Caching layer improves auth latency by 80%"
Before: 200ms per check
After: 40ms per check
```

**OUTPUT**:

```
Hook: "Imagine every user interaction was 5x faster."
Problem: "Our auth became a bottleneck at scale."
Demo: [Show old vs new latency comparison]
Metric: "200ms down to 40ms—5x improvement"
Close: "This fundamentally changes what we can build."
```

### Example 2: Commits → Blog (Section Headings)

```
Title: "Zero-Overhead Authentication: 80% Latency Reduction"

1. The Problem (400w) - Why auth latency matters at scale
2. The Insight (300w) - What we realized about token validity
3. The Implementation (600w) - How we built it (code samples)
4. The Results (400w) - Metrics and production performance
5. Lessons Learned (300w) - What we'd do differently
6. What's Next (300w) - Future optimization opportunities
```

### Example 3: Feature → Marketing (Value Prop)

```
HEADLINE: "Integrate in Hours, Not Days"
PROBLEM: "Powerful APIs shouldn't be complicated"
BEFORE: "200 parameters, 3-day integration, support tickets"
AFTER: "10 parameters, 6-hour integration, it just works"
PROOF: "75% faster, 60% fewer support tickets"
CTA: "Try free for 30 days, no credit card"
```

## Quality Checklist

- [ ] Hook captures attention in 30 seconds
- [ ] Problem is clearly articulated
- [ ] Solution is appropriate technical depth
- [ ] Metrics are concrete (numbers, not vague)
- [ ] "Why this matters to me" is clear
- [ ] Specific examples make it tangible
- [ ] Pacing varies (not monotonous)
- [ ] Smooth transitions between sections
- [ ] Strong close (implication, not summary)
- [ ] Appropriate for medium (5-min demo, not 20-min)
- [ ] Right for audience (engineers ≠ marketers)
- [ ] Timing is realistic

## 5-Second Tips

1. **Start strong** - Hook in first 30 seconds
2. **Problem first** - Spend time on "why"
3. **Specific metrics** - "47% faster" not "much faster"
4. **Show examples** - Demos, screenshots, code
5. **Vary pace** - Mix slow explanation with fast excitement
6. **Match audience** - Engineers want code, execs want ROI
7. **Pick medium** - 7-min demo ≠ 30-min talk
8. **Audience matters** - Same work, different stories
9. **Practice timing** - Narratives need polish
10. **Close strong** - End with implication

## Common Mistakes (Avoid These)

| Mistake        | Problem                        | Solution                                       |
| -------------- | ------------------------------ | ---------------------------------------------- |
| Too technical  | Audience loses interest        | Lead with impact, dive deep only if needed     |
| No problem     | Why should anyone care?        | Spend 40% on problem statement                 |
| Vague metrics  | Sounds impressive but unproven | Always quantify: "5x faster" not "much faster" |
| Wrong audience | Bores the people listening     | Analyze audience first, adapt accordingly      |
| Weak closing   | Fizzles out                    | Close with implication, not summary            |
| Bad pacing     | Drags or rushes                | Plan timing, vary speed                        |

## Output Templates

### Demo Script Format

```markdown
# [Feature Name] Demo Script (7 minutes)

**HOOK (0:00-0:30)**
[Opening line that captures attention]

**PROBLEM (0:30-2:00)**
[What's broken and why it matters]

**DEMO (2:00-5:30)**
[Live walkthrough with commentary]

**METRICS (5:30-6:30)**

- Metric 1: [specific number]
- Metric 2: [specific number]

**CLOSING (6:30-7:00)**
[Memorable final thought]

---

**Timing**: [Actual duration]
**Equipment**: [What you need]
**Talking Points**: [Key things to emphasize]
```

### Blog Outline Format

```markdown
# [Article Title]

## Introduction

[Hook + problem statement]

## The Problem

[Detailed explanation - 400-500 words]

## The Solution

[High-level overview before diving in - 300-400 words]

## Technical Deep Dive

[Implementation details with code - 600-800 words]

## Results & Validation

[Metrics and proof - 300-400 words]

## Implications

[What this enables - 200-300 words]

## Code Example

[Complete, runnable example]

## Conclusion

[Takeaway and next steps]
```

### Presentation Outline Format

```markdown
# [Presentation Title] - [Duration]

## Slide 1-2: Problem (3 min)

- Slide 1: Problem statement
- Slide 2: Why it matters

## Slide 3-5: Solution (5 min)

- Slide 3: Architecture overview
- Slide 4: Key innovation
- Slide 5: How it works

## Slide 6-8: Demo (8 min)

- Live demonstration
- Before/after comparison

## Slide 9-10: Impact (3 min)

- Metrics and results
- Customer impact

## Slide 11: Roadmap (2 min)

- What's next

## Slide 12: Closing (1 min)

- Key takeaway
```

## When to Use Each Format

| Goal           | Medium        | Time         | Audience     |
| -------------- | ------------- | ------------ | ------------ |
| Quick demo     | Demo script   | 5-10 min     | Everyone     |
| Deep learning  | Blog post     | 1,500+ words | Technical    |
| Get buy-in     | Presentation  | 20-45 min    | Stakeholders |
| Drive adoption | Marketing     | Varied       | Prospects    |
| Share wins     | Release notes | Varied       | Users        |

## Real-World Example: Full Cycle

**Technical Achievement**:

- Built distributed caching layer
- 200ms → 40ms latency (5x improvement)
- Handles 100k concurrent users

**Demo (7 min)**:
"Imagine if every interaction was 5x faster. Here's our new caching architecture handling 100k users with sub-50ms latency."

**Blog Post**:
Deep dive: Why we needed this, how we built it, what we learned, what's next (2,000 words)

**Presentation (30 min)**:
Architecture, live demo, results, roadmap for engineering team buy-in

**Marketing Copy**:
"Enterprise-grade performance at consumer-friendly simplicity"

**Release Notes**:
"User-facing: Platform now 5x faster. Technical: Distributed cache, event-driven invalidation, production-ready."

---

**Start here**: What technical work do you want to tell a story about?
