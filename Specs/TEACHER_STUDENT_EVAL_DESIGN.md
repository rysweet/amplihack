# Teacher-Student Learning Evaluation Design Brief

## For: Next session colleague designing the two-agent eval

## Goal

Design an evaluation harness where **Agent A (Teacher)** learns content with the goal of teaching it, then interacts with **Agent B (Student)** who must demonstrate understanding. We measure how well the Student learned, which reflects how well the Teacher taught.

## Why This Matters

Current eval tests whether an agent can recall facts. But real learning means being able to:
- Explain concepts to someone else (Feynman's "teach to learn")
- Adapt explanations based on the learner's understanding
- Organize knowledge into a teachable structure
- Assess whether the student actually understood

This is a much harder test than recall - it evaluates the agent's ability to **organize and communicate** knowledge, not just store and retrieve it.

## Workflow (Exact Sequence)

```
Step 1: Build prompt for general-purpose learning and teaching agent
  → Write prompt.md describing the agent's goal

Step 2: Generate teacher agent via goal-seeking agent generator
  → amplihack new --file teacher_prompt.md --enable-memory
  → Produces teacher agent with HierarchicalMemory, Graph RAG, intent detection

Step 3: Teacher agent learns content (initial learning)
  → Teacher reads content, stores in its own Kuzu DB
  → Teacher's memory: ~/.amplihack/memory/teacher_{session}/kuzu_db

Step 4: Evaluate teacher's learning
  → Run quiz against teacher to verify it learned the material
  → Must pass L1-L4 thresholds before proceeding to teach

Step 5: Generate student agent via goal-seeking agent generator
  → amplihack new --file student_prompt.md --enable-memory
  → Produces student agent with SEPARATE empty Kuzu DB
  → Student's memory: ~/.amplihack/memory/student_{session}/kuzu_db

Step 6: Teaching session (teacher teaches student)
  → Multi-turn conversation between teacher and student
  → Teacher retrieves from ITS memory, explains to student
  → Student stores what it learns in ITS OWN memory
  → Completely separate memory databases

Step 7: Evaluate student's learning
  → Run same quiz against student
  → Student answers from ITS OWN memory (not teacher's)
  → Compare student scores vs teacher scores (Step 4)
  → Teaching effectiveness = student_score / teacher_score
```

**Critical: Separate memory databases.** Teacher and student each have their own Kuzu DB. The student CANNOT access the teacher's memory. Knowledge transfer happens ONLY through the conversation.

## Key Design Decisions

### 1. Teacher's Learning Goal

The Teacher should NOT just memorize facts. Its learning prompt should be:

> "You are about to learn this content. Your goal is to understand it well enough to teach it to someone who has never seen it. As you learn, think about:
> - What are the key concepts and how do they relate?
> - What order should you teach them in?
> - What examples or analogies would help explain difficult parts?
> - What questions might a student ask?
> - What common misconceptions should you address?"

This changes HOW the agent stores knowledge - it should create:
- Summary/overview nodes (curriculum structure)
- Prerequisite edges (concept A must be understood before B)
- Example nodes (concrete illustrations of abstract concepts)
- Anticipated-question nodes (prospective memory)

### 2. Teaching Interaction Format

Multi-turn conversation, NOT a single dump of information:

```
Turn 1: Teacher introduces the topic with an overview
Turn 2: Student asks a clarifying question
Turn 3: Teacher explains in more detail
Turn 4: Student tries to summarize understanding
Turn 5: Teacher corrects misconceptions
Turn 6: Student asks about implications/applications
Turn 7: Teacher provides deeper analysis
...
Turn N: Teacher assesses if student is ready
```

The Student agent should:
- Start with zero knowledge of the topic
- Ask genuine questions (not scripted)
- Try to build understanding progressively
- Store what it learns in its OWN Kuzu memory
- Be able to say "I don't understand" or "can you explain X differently?"

### 3. Student Assessment

After the teaching session ends, the Student takes a quiz:
- Questions at L1-L4 complexity (same as progressive suite)
- Student answers from its OWN memory (separate Kuzu DB from Teacher)
- Student has NO access to original content or Teacher's memory
- Graded by concept coverage + explanation quality

### 4. Baseline Comparison

To evaluate teaching effectiveness:
1. **Direct baseline**: Run the same content through the existing LearningAgent (learns directly, no teacher). Score on same quiz.
2. **Teacher-Student**: Teacher learns, teaches Student, Student takes quiz.
3. **Effectiveness ratio**: Student score / Direct baseline score

If ratio > 0.8 → Teacher is effective (Student learned 80%+ of what direct learning achieves)
If ratio > 1.0 → Teacher is BETTER than direct learning (teaching deepens understanding)

### 5. Content Selection

Use the same post-training-cutoff content from the progressive test suite:
- Winter Olympics 2026 (rich, interconnected facts)
- Flutter tutorial (procedural knowledge)
- VS2026 update (technical details)

For each content piece:
- Teacher learns it
- Teacher teaches Student over 6-10 turns
- Student takes quiz
- Compare to direct-learning baseline

### 6. Measuring Teaching Quality

Beyond Student quiz scores, also measure:
- **Curriculum structure**: Did Teacher organize content logically? (check for summary/overview nodes in Teacher's memory)
- **Adaptation**: Did Teacher adjust explanations when Student was confused? (analyze conversation for re-explanation patterns)
- **Coverage**: Did Teacher cover all key concepts? (compare Teacher's teaching transcript against content concepts)
- **Depth**: Did Teacher go beyond surface-level facts? (check for relationship explanations, cause-effect reasoning)

## Technical Requirements

### Separate Memory Stores
- Teacher: `~/.amplihack/memory/teacher_{session}/kuzu_db`
- Student: `~/.amplihack/memory/student_{session}/kuzu_db`
- No shared state between them

### Conversation Protocol
```python
class TeachingSession:
    teacher: LearningAgent  # With content in memory
    student: LearningAgent  # Empty memory
    transcript: list[dict]  # {role: "teacher"|"student", content: str}

    def run(self, max_turns: int = 10):
        # Teacher opens with overview
        teacher_msg = self.teacher.teach_opening()
        self.transcript.append({"role": "teacher", "content": teacher_msg})

        for turn in range(max_turns):
            # Student responds (question, summary, or "I understand")
            student_msg = self.student.learn_from_teacher(teacher_msg)
            self.transcript.append({"role": "student", "content": student_msg})

            # Student stores what it learned
            self.student.learn_from_content(student_msg)  # Self-learning from its own understanding

            # Check if student signals understanding
            if self.student.says_ready():
                break

            # Teacher responds to student
            teacher_msg = self.teacher.respond_to_student(student_msg)
            self.transcript.append({"role": "teacher", "content": teacher_msg})
```

### New Agent Methods Needed

For LearningAgent (teacher mode):
- `teach_opening()` → Generate introductory explanation from memory
- `respond_to_student(student_message)` → Adapt explanation based on student's response
- `assess_student_readiness()` → Evaluate if student has grasped key concepts

For LearningAgent (student mode):
- `learn_from_teacher(teacher_message)` → Process teacher's explanation, store in memory, generate follow-up question
- `says_ready()` → True if student feels it understands the material
- Answer questions from its own memory (existing functionality)

### Subprocess Isolation

Same pattern as progressive suite:
1. Teacher learning: subprocess 1 (learns content → Kuzu)
2. Teaching session: subprocess 2 (Teacher + Student interact, each writes to own Kuzu)
3. Student assessment: subprocess 3 (Student only, answers from own Kuzu)

The teaching session subprocess is the new complexity - two agents conversing within one process, each with separate memory stores.

## Success Criteria

### Minimum Viable
- Teacher can explain content coherently
- Student stores what it learns
- Student scores > 50% on quiz (better than random)
- Student score > 60% of direct-learning baseline

### Good
- Multi-turn conversation with genuine Q&A
- Teacher adapts to student questions
- Student scores > 75% on quiz
- Student score > 80% of direct-learning baseline

### Excellent
- Teacher anticipates student confusion
- Student asks insightful follow-up questions
- Student scores > 90% on quiz
- Student score > 100% of direct-learning baseline (teaching improves understanding)

## Implementation Priority

1. **First**: Get basic teacher→student information transfer working (even if clunky)
2. **Second**: Add multi-turn conversation with genuine adaptation
3. **Third**: Measure and optimize teaching effectiveness
4. **Fourth**: Compare against direct-learning baseline

## Dependencies

- LearningAgent with HierarchicalMemory (PR #2395)
- Intent detection and temporal reasoning (already implemented)
- Source provenance in context (being implemented now)
- Progressive test suite for baseline comparison

## Critical Architecture Note: Generator, Not Instance

**We are improving the goal-seeking agent GENERATOR, not a specific agent instance.**

The `amplihack new --file prompt.md --enable-memory` command generates agents. The improvements to learning, memory, intent detection, temporal reasoning, contradiction handling, and teaching ability should all be capabilities that ANY generated agent gets automatically.

This means:
- The `LearningAgent` class is a TEMPLATE that generated agents inherit from
- HierarchicalMemory, Graph RAG, intent detection are INFRASTRUCTURE that all agents use
- The eval harness tests the GENERATOR's output, not a hand-crafted agent
- When we improve the learning loop, ALL future generated agents benefit

For the teacher-student eval:
- The generator should produce agents that can operate in EITHER teacher or student mode
- The mode is determined by the goal prompt, not by different code paths
- A generated agent given the goal "learn X and teach it" should automatically adopt teacher behaviors
- A generated agent given the goal "learn from a teacher" should automatically adopt student behaviors

The goal-seeking agent generator (`src/amplihack/goal_agent_generator/`) uses:
- `PromptAnalyzer` → `ObjectivePlanner` → `AgentAssembler` → `GoalAgentPackager`
- With `--enable-memory`, it adds memory initialization code from templates
- The templates need to include HierarchicalMemory, Graph RAG, intent detection
- The `templates/memory_template.py` needs updating to use the new memory system

## Memory System Implementation Location

**The 6-type cognitive memory system belongs in the separate amplihack-memory-lib repo:**
- Repo: https://github.com/rysweet/amplihack-memory-lib
- Local clone: /home/azureuser/src/amplihack-memory-lib-real/
- The goal-seeking agents in amplihack IMPORT from this library
- Schema changes, new Kuzu tables, consolidation, working memory all go there
- The agent code in amplihack just calls the library's API

**6 Memory Types (all in amplihack-memory-lib):**

| Type | Kuzu Table | Purpose | Teaching Use |
|---|---|---|---|
| Sensory | SensoryMemory | Raw input buffer, timestamps, auto-expires | Track student responses in real-time |
| Working | WorkingMemory | Active task tracking (like TaskList), 20-item capacity | Track teaching session state, which topics covered |
| Episodic | EpisodicMemory + ConsolidatedEpisode | Events with consolidation/summarization | "When did I learn/teach this?" |
| Semantic | SemanticMemory | Facts with confidence, SIMILAR_TO edges | Core knowledge for teaching |
| Procedural | ProceduralMemory | Ordered steps, usage_count strengthens with use | Teaching how-to, tutorials |
| Prospective | ProspectiveMemory | Future intentions, trigger conditions | "Check student understands X before teaching Y" |

**Working memory integrates with all others:**
- Working ← Sensory: new input buffered for attention
- Working → Episodic: completed tasks become episodes
- Working ← Procedural: tracks which step you're on
- Working → Prospective: surfaces triggered reminders

## Questions to Resolve

1. Should Teacher and Student use the same LLM model, or should Student use a weaker model to simulate a less capable learner?
2. How many teaching turns are optimal? Too few = surface coverage. Too many = diminishing returns.
3. Should the Student be allowed to "look things up" (search memory) during the conversation, or only after?
4. How do we prevent the Student from just memorizing the Teacher's exact words vs actually understanding?
5. Should we test with content the Teacher learned imperfectly (to see if teaching reveals gaps)?
