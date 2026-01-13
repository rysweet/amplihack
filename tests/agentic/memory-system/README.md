# Agentic Test Scenarios - 5-Type Memory System

This directory contains end-to-end test scenarios for the 5-type memory system (Issue #1902, PR #1905) using the gadugi-agentic-test framework.

## Test Scenarios

### 01-smoke-test-memory-storage.yaml

**Level**: 1 (Basic)
**Purpose**: Verify basic memory storage works
**Tags**: smoke, memory, critical
**What it tests**:

- Memory system can be imported from installed package
- Basic storage operation works
- Memory ID is returned

### 02-test-all-five-types.yaml

**Level**: 1 (Basic)
**Purpose**: Verify all 5 psychological memory types work
**Tags**: smoke, memory, types
**What it tests**:

- EPISODIC memory storage
- SEMANTIC memory storage
- PROSPECTIVE memory storage
- PROCEDURAL memory storage
- WORKING memory storage

### 03-test-cross-session-recall.yaml

**Level**: 2 (Intermediate)
**Purpose**: Verify memories persist across sessions
**Tags**: integration, memory, cross-session
**What it tests**:

- Memories stored in session 1 can be retrieved in session 2
- Semantic memories are discoverable
- Database persistence works

### 04-test-trivial-filtering.yaml

**Level**: 2 (Intermediate)
**Purpose**: Verify trivial content is filtered automatically
**Tags**: quality, memory, filtering
**What it tests**:

- Simple acknowledgments ("ok", "thanks") are rejected
- Substantive content is stored
- Quality gates work automatically

### 05-test-selective-retrieval.yaml

**Level**: 2 (Intermediate)
**Purpose**: Verify retrieval is selective and respects token budgets
**Tags**: quality, memory, retrieval
**What it tests**:

- Retrieval returns relevant memories (not all stored memories)
- Token budget is enforced (stays under limit)
- Relevance scoring works

## Running the Tests

### All Tests

```bash
gadugi-agentic-test run tests/agentic/memory-system/*.yaml
```

### Specific Test

```bash
gadugi-agentic-test run tests/agentic/memory-system/01-smoke-test-memory-storage.yaml
```

### By Tag

```bash
# Run only smoke tests
gadugi-agentic-test run tests/agentic/memory-system/ --tags smoke

# Run integration tests
gadugi-agentic-test run tests/agentic/memory-system/ --tags integration
```

### In CI/CD

```bash
# Run with verbose output and save evidence
gadugi-agentic-test run tests/agentic/memory-system/ \
  --verbose \
  --evidence-dir ./test-evidence \
  --retry 2
```

## Test Requirements

### Prerequisites

- Python 3.11+
- uv package manager
- gadugi-agentic-test framework: `pip install gadugi-agentic-test`
- Internet access (to install from GitHub)

### Installation

```bash
# Install gadugi-agentic-test
pip install gadugi-agentic-test

# Verify installation
gadugi-agentic-test --version
```

## What These Tests Validate

### User-Facing Behavior ✅

- Memory system works when installed via `uvx --from git...`
- All 5 memory types functional
- Trivial filtering prevents noise
- Selective retrieval respects budgets
- Cross-session persistence works

### Hook Integration ✅

- `.claude` directory packaged in distribution
- Hooks can import MemoryCoordinator
- Hooks use new 5-type system (not old Neo4j system)

### Quality Gates ✅

- Trivial content filtered (multi-agent review fallback working)
- Token budgets enforced
- Duplicate detection working
- Performance within targets

## Test Evidence

After running tests, evidence is collected in `./evidence/` directory:

```
evidence/
  memory-system-smoke-test-20260111-235959/
    ├── scenario.yaml
    ├── execution-log.json
    ├── output-captures/
    │   ├── stdout.txt
    │   └── stderr.txt
    └── report.html
```

## Expected Results

### Success Criteria

All scenarios should **PASS** with the feat/issue-1902-5-type-memory-system branch:

- ✅ Smoke test passes (basic storage works)
- ✅ All 5 types test passes (each type stores successfully)
- ✅ Cross-session test passes (memories recalled from different session)
- ✅ Trivial filtering test passes (low-quality content rejected)
- ✅ Selective retrieval test passes (token budget respected)

### Known Limitations

**Multi-agent review in tests**: The tests use `uvx` which doesn't have Claude Code Task tool available, so:

- Storage uses **fallback heuristic scoring** (not full 3-agent review)
- This is expected and acceptable for testing
- In real Claude Code sessions, full multi-agent review will work

**Output includes**: "Not enough agent reviews, using fallback score" - this is normal for standalone testing

## Troubleshooting

### Tests timeout during install

- Increase timeout in YAML: `timeout: 180s`
- Check internet connection
- Verify GitHub branch exists

### Import errors

- Verify `.claude` directory is packaged: Run scenario 05
- Check Python version (needs 3.11+)
- Try fresh install: `uv cache clear`

### Memory not persisting

- Check database location: `~/.amplihack/memory.db`
- Verify file permissions (should be 600)
- Check session IDs match in test

## Integration with PR #1905

These tests serve as **acceptance criteria** for the 5-type memory system PR:

- All tests must pass before merging
- Tests validate actual user workflows (not just unit tests)
- Evidence collected for PR review
- Demonstrates feature works end-to-end

Run these tests with:

```bash
uvx --from git+https://github.com/rysweet/amplihack@feat/issue-1902-5-type-memory-system gadugi-agentic-test run tests/agentic/memory-system/
```

## Related Documentation

- **Issue #1902**: Requirements and design
- **PR #1905**: Implementation details
- **docs/memory/5-TYPE-MEMORY-GUIDE.md**: User guide
- **docs/memory/5-TYPE-MEMORY-DEVELOPER.md**: Developer reference
