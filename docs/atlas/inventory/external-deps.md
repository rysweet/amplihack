# External Dependencies Inventory

Source: `pyproject.toml` — amplihack v0.6.81

## Core Dependencies

| Package              | Version Constraint | Purpose                                                     |
| -------------------- | ------------------ | ----------------------------------------------------------- |
| flask                | >=2.0.0            | Web framework (proxy server routes)                         |
| requests             | >=2.32.4           | HTTP client (CVE-2024-47081 fix)                            |
| fastapi              | >=0.68.0           | Async web framework (Responses API proxy)                   |
| uvicorn              | >=0.15.0           | ASGI server for FastAPI                                     |
| aiohttp              | >=3.8.0            | Async HTTP client                                           |
| python-dotenv        | >=0.19.0           | .env file loading                                           |
| claude-agent-sdk     | >=0.1.0            | Claude Python Agent SDK for auto mode streaming             |
| github-copilot-sdk   | >=0.1.0            | GitHub Copilot SDK for embedding Copilot                    |
| rich                 | >=13.0.0           | Interactive TUI mode rendering                              |
| azure-identity       | >=1.12.0           | Azure Service Principal authentication                      |
| kuzu                 | >=0.11.0           | Embedded graph database for memory system                   |
| amplihack-memory-lib | git@v0.2.0         | Standalone memory system with CognitiveMemory 6-type system |
| amplihack-agent-eval | git@main           | Agent evaluation and benchmarking framework                 |

## Blarify Vendored Dependencies

| Package                | Version Constraint          | Purpose                                                     |
| ---------------------- | --------------------------- | ----------------------------------------------------------- |
| json-repair            | >=0.47.7                    | JSON repair for Blarify LLM provider                        |
| langchain              | >=1.2.3                     | LangChain core for Blarify agents                           |
| langchain-openai       | >=1.1.7                     | LangChain OpenAI integration                                |
| langchain-anthropic    | >=1.3.1                     | LangChain Anthropic integration                             |
| langchain-google-genai | >=4.1.3                     | LangChain Google integration                                |
| tree-sitter            | >=0.23.2                    | Code parsing engine                                         |
| tree-sitter-python     | >=0.23.2                    | Python grammar for tree-sitter                              |
| tree-sitter-javascript | >=0.23.0                    | JavaScript grammar                                          |
| tree-sitter-typescript | >=0.23.2                    | TypeScript grammar                                          |
| tree-sitter-c-sharp    | >=0.23.1                    | C# grammar                                                  |
| tree-sitter-go         | >=0.23.1                    | Go grammar                                                  |
| tree-sitter-java       | >=0.23.2                    | Java grammar                                                |
| tree-sitter-php        | >=0.23.4                    | PHP grammar                                                 |
| tree-sitter-ruby       | >=0.23.0                    | Ruby grammar                                                |
| psutil                 | >=7.0.0                     | Process utilities for Blarify                               |
| protobuf               | >=5.29.0                    | SCIP index format (relaxed for agent-framework-core compat) |
| typing-extensions      | >=4.12.2                    | Backport for Python 3.10 (NotRequired, etc.)                |
| falkordb               | >=1.0.10                    | FalkorDB graph database client                              |
| neo4j                  | >=5.25.0                    | Neo4j graph database client                                 |
| jedi-language-server   | >=0.43.1                    | Jedi LSP for Python code intelligence                       |
| docker                 | >=7.1.0                     | Docker client for Blarify containers                        |
| packaging              | >=21.0                      | Semantic version comparison for auto-update                 |
| tomli                  | >=2.0.0 (Python <3.11 only) | TOML parser backport                                        |

## Optional Dependency Groups

### microsoft-sdk

| Package                               | Version         | Purpose                   |
| ------------------------------------- | --------------- | ------------------------- |
| agent-framework-core                  | >=1.0.0rc1      | Microsoft Agent Framework |
| opentelemetry-semantic-conventions-ai | >=0.4.1,<0.4.14 | AI telemetry conventions  |

### amplifier

| Package        | Version  | Purpose                       |
| -------------- | -------- | ----------------------------- |
| amplifier-core | git@main | Amplifier bundle runtime core |

### test

| Package        | Version  | Purpose            |
| -------------- | -------- | ------------------ |
| pytest         | >=7.0.0  | Test framework     |
| pytest-cov     | >=4.0.0  | Coverage reporting |
| pytest-asyncio | >=0.21.0 | Async test support |

### dev

| Package        | Version  | Purpose                             |
| -------------- | -------- | ----------------------------------- |
| black          | >=22.0.0 | Code formatter                      |
| ruff           | >=0.1.0  | Linter                              |
| build          | >=1.0.0  | Package builder                     |
| pre-commit     | latest   | Pre-commit hooks                    |
| beautifulsoup4 | >=4.9.0  | Documentation validation            |
| lxml           | >=4.6.0  | XML/HTML parsing for doc validation |
| pyyaml         | >=6.0.0  | YAML parsing for mkdocs validation  |
