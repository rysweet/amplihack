# Memory Systems Diagrams

This file is the presentation-friendly companion to `docs/concepts/memory-enabled-agents-architecture.md`.

## Diagram 1: Two Memory Surfaces

```mermaid
flowchart LR
    CLI[amplihack memory tree / clean] --> RepoMemory[src/amplihack/memory]
    RepoMemory --> Kuzu[(~/.amplihack/memory_kuzu.db)]
    RepoMemory --> SQLite[(optional sqlite backend)]

    Generator[amplihack new --enable-memory] --> Package[generated goal-agent package]
    Package --> MainPy[main.py memory helpers]
    Package --> Config[memory_config.yaml]
    Package --> AgentMemory[(./memory/)]
    MainPy --> ExperienceStore[amplihack_memory ExperienceStore]
    ExperienceStore --> AgentMemory
```

### Speaker Notes

- The repo has one memory story for the top-level CLI and another for generated standalone agents.
- The CLI-facing backend is graph-oriented and Kuzu-first.
- Generated agents package an experience-store scaffold under their own `./memory/` directory.

## Diagram 2: In-Repo Memory Backend

```mermaid
flowchart TD
    Command[amplihack memory tree / clean] --> BackendChoice{backend}
    BackendChoice -->|default| KuzuBackend[Kuzu backend]
    BackendChoice -->|optional| SqliteBackend[SQLite backend]
    KuzuBackend --> Env1[AMPLIHACK_GRAPH_DB_PATH]
    KuzuBackend --> Env2[AMPLIHACK_KUZU_DB_PATH\nDeprecated alias]
    KuzuBackend --> DefaultPath[~/.amplihack/memory_kuzu.db]
    KuzuBackend --> Graph[graph memory + code linking]
```

### Speaker Notes

- `tree` and `clean` are the verified top-level memory commands in this checkout.
- Kuzu is the default backend.
- `AMPLIHACK_GRAPH_DB_PATH` is the preferred environment variable.

## Diagram 3: Memory Type Model

```mermaid
flowchart LR
    Primary[preferred memory types] --> Episodic[episodic]
    Primary --> Semantic[semantic]
    Primary --> Procedural[procedural]
    Primary --> Prospective[prospective]
    Primary --> Working[working]

    Legacy[legacy compatibility types] --> Conversation[conversation]
    Legacy --> Decision[decision]
    Legacy --> Pattern[pattern]
    Legacy --> Context[context]
    Legacy --> Learning[learning]
    Legacy --> Artifact[artifact]
```

### Speaker Notes

- The model layer uses five preferred psychological memory types.
- The CLI still exposes the older compatibility names for `memory tree --type`.
- That mismatch is intentional today and should be explained, not hidden.

## Diagram 4: Generated Agent Memory Scaffold

```mermaid
sequenceDiagram
    participant User
    participant CLI as amplihack new --enable-memory
    participant Packager as goal agent packager
    participant Agent as generated main.py
    participant Store as amplihack_memory store

    User->>CLI: generate package
    CLI->>Packager: assemble bundle
    Packager->>Agent: inject helper functions
    Packager->>Agent: write memory_config.yaml
    Packager->>Agent: create ./memory/
    Agent->>Store: store_success / store_failure / recall_relevant
```

### Speaker Notes

- `--enable-memory` gives the generated package a usable scaffold.
- The important helpers are `store_success`, `store_failure`, `store_pattern`, `store_insight`, and `recall_relevant`.
- The scaffold is explicit: teams still decide where those helpers should be called in their agent flow.

## Diagram 5: Where Confusion Usually Comes From

```mermaid
flowchart TD
    Question["I created a memory-enabled agent. Why doesn't amplihack memory tree show its local store?"] --> Answer[Because the CLI backend and the generated agent store are different surfaces]
    Answer --> RepoBackend[top-level CLI backend]
    Answer --> AgentStore[generated agent ./memory store]
```

### Speaker Notes

- The docs used to blur these together.
- The updated docs separate them on purpose.
- That separation is the fastest way to explain what works, where it lives, and which command owns it.

## Related Material

- `docs/memory/README.md`
- `docs/AGENT_MEMORY_QUICKSTART.md`
- `docs/concepts/memory-enabled-agents-architecture.md`
- `docs/reference/memory-cli-reference.md`
