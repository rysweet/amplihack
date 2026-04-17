"""Lesson 14 content builder."""

from __future__ import annotations

import textwrap

from amplihack.agents.teaching.models import Exercise, Lesson, QuizQuestion


def _build_lesson_14() -> Lesson:
    """Lesson 14: Memory Export, Import, and Cross-Session Persistence."""
    return Lesson(
        id="L14",
        title="Memory Export, Import, and Cross-Session Persistence",
        description="Export agent knowledge as snapshots, import into new agents, and persist across sessions.",
        content=textwrap.dedent("""\
            # Lesson 14: Memory Export, Import, and Cross-Session Persistence

            ## Why Export/Import?

            Agents accumulate knowledge over time. You need to:
            - **Back up** knowledge before risky operations.
            - **Share** knowledge between agents or team members.
            - **Replay** learning to reproduce eval results.
            - **Migrate** from one backend to another.

            ## Memory Architecture

            The agent uses `MemoryRetriever` backed by the Kuzu graph database
            (with SQLite fallback). Each agent has isolated storage:

            ```
            ~/.amplihack/memory/<agent_name>/
            ```

            Storage can be overridden with the `storage_path` parameter:

            ```python
            from amplihack.agents.goal_seeking.memory_retrieval import MemoryRetriever

            retriever = MemoryRetriever(
                agent_name="my-agent",
                storage_path=Path("/tmp/test_memory"),
            )
            ```

            ## ExperienceStore API

            The underlying `ExperienceStore` provides the core storage interface:

            ```python
            from amplihack_memory import ExperienceStore, Experience, ExperienceType

            store = ExperienceStore(agent_name="my-agent")

            # Store a fact
            exp = Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Photosynthesis",
                outcome="Plants convert light energy to chemical energy",
                confidence=0.9,
                tags=["biology"],
            )
            exp_id = store.connector.store_experience(exp)

            # Search
            results = store.search(query="photosynthesis", limit=5)

            # Statistics
            stats = store.get_statistics()
            ```

            ## Export as JSON Snapshot

            To export an agent's knowledge, retrieve all facts and serialize:

            ```python
            retriever = MemoryRetriever("my-agent")
            all_facts = retriever.get_all_facts(limit=50000)

            import json
            with open("knowledge_snapshot.json", "w") as f:
                json.dump(all_facts, f, indent=2)
            ```

            ## Import from Snapshot

            To import into a new agent:

            ```python
            import json

            with open("knowledge_snapshot.json") as f:
                facts = json.load(f)

            new_retriever = MemoryRetriever("new-agent")
            for fact in facts:
                new_retriever.store_fact(
                    context=fact["context"],
                    fact=fact["outcome"],
                    confidence=fact.get("confidence", 0.8),
                    tags=fact.get("tags", []),
                )
            ```

            ## Eval-Specific Memory Isolation

            The progressive test suite creates fresh memory for each eval run by
            using unique agent names with timestamps:

            ```python
            agent_name = f"eval_agent_{int(time.time())}"
            ```

            This prevents cross-contamination between eval runs. Each run starts
            with an empty knowledge base.

            ## Memory Statistics

            ```python
            retriever = MemoryRetriever("my-agent")
            stats = retriever.get_statistics()
            # {
            #     "total_experiences": 142,
            #     "by_type": {"SUCCESS": 130, "FAILURE": 12},
            #     "storage_size_kb": 256
            # }
            ```

            ## Practical: Comparing Agent Knowledge

            After running the self-improvement loop, compare what two agent
            versions know:

            ```python
            v1 = MemoryRetriever("agent-v1")
            v2 = MemoryRetriever("agent-v2")

            v1_facts = v1.get_all_facts()
            v2_facts = v2.get_all_facts()

            print(f"v1: {len(v1_facts)} facts, v2: {len(v2_facts)} facts")
            ```
        """),
        prerequisites=["L06"],
        exercises=[
            Exercise(
                id="E14-01",
                instruction=(
                    "Write Python code to export all facts from an agent called "
                    "'security-scanner' to a JSON file, then import them into a "
                    "new agent called 'security-scanner-v2'."
                ),
                expected_output=(
                    "# Export\n"
                    "retriever = MemoryRetriever('security-scanner')\n"
                    "facts = retriever.get_all_facts(limit=50000)\n"
                    "with open('snapshot.json', 'w') as f:\n"
                    "    json.dump(facts, f)\n\n"
                    "# Import\n"
                    "new_ret = MemoryRetriever('security-scanner-v2')\n"
                    "for fact in facts:\n"
                    "    new_ret.store_fact(context=fact['context'], "
                    "fact=fact['outcome'])"
                ),
                hint="Use get_all_facts() to export and store_fact() to import.",
                validation_fn="validate_memory_export",
            ),
            Exercise(
                id="E14-02",
                instruction=(
                    "Explain why the eval suite uses unique agent names with timestamps "
                    "and what would happen if all eval runs shared the same agent name."
                ),
                expected_output=(
                    "Unique names ensure each eval run starts with an empty knowledge base. "
                    "If eval runs shared the same name, facts from previous runs would "
                    "persist, inflating scores because the agent would 'remember' answers "
                    "from past evaluations instead of learning fresh from the articles."
                ),
                hint="Think about what happens when facts from run N persist into run N+1.",
            ),
        ],
        quiz=[
            QuizQuestion(
                question="Where does MemoryRetriever store data by default?",
                correct_answer="~/.amplihack/memory/<agent_name>/ using the Kuzu graph database",
                wrong_answers=[
                    "In a SQLite file in the current directory",
                    "In memory only -- no persistence",
                    "In a PostgreSQL database",
                ],
                explanation="The default backend is Kuzu with storage under ~/.amplihack/memory/.",
            ),
            QuizQuestion(
                question="What method retrieves all facts without keyword filtering?",
                correct_answer="get_all_facts(limit=N) -- bypasses search and returns all experiences",
                wrong_answers=[
                    "search('*') with a wildcard query",
                    "retrieve_all() method",
                    "dump_memory() method",
                ],
                explanation="get_all_facts() is specifically designed for export and simple retrieval.",
            ),
            QuizQuestion(
                question="Why is memory isolation important during eval?",
                correct_answer=(
                    "Without isolation, facts from previous runs would persist and inflate "
                    "scores because the agent remembers past answers"
                ),
                wrong_answers=[
                    "To save disk space",
                    "Because Kuzu cannot handle concurrent access",
                    "To prevent the agent from learning too many facts",
                ],
                explanation="Cross-contamination makes eval results unreliable.",
            ),
        ],
    )
