# Package Inventory

**Generated:** 2026-03-17

| Package | Version Constraint | Consumers | Direct? | Purpose |
|---------|-------------------|-----------|---------|---------|
| flask | >=2.0.0 | proxy/responses_api_proxy | Yes | OpenAI Responses API proxy |
| requests | >=2.32.4 | multiple | Yes | HTTP client (CVE-2024-47081 fix) |
| fastapi | >=0.68.0 | proxy/integrated_proxy, proxy/log_streaming | Yes | API proxy, SSE streaming |
| uvicorn | >=0.15.0 | proxy/ | Yes | ASGI server for FastAPI |
| aiohttp | >=3.8.0 | proxy/ | Yes | Async HTTP client |
| litellm | >=1.0.0 | proxy/integrated_proxy | Yes | Multi-provider LLM routing |
| python-dotenv | >=0.19.0 | proxy/ | Yes | .env file loading |
| claude-agent-sdk | >=0.1.0 | fleet/, goal_agent_generator/ | Yes | Claude Code SDK for auto mode |
| github-copilot-sdk | >=0.1.0 | launcher/ | Yes | GitHub Copilot SDK integration |
| rich | >=13.0.0 | cli, TUI mode | Yes | Terminal UI rendering |
| azure-identity | >=1.12.0 | proxy/ | Yes | Azure Service Principal auth |
| kuzu | >=0.11.0 | memory/ | Yes | Embedded graph database |
| amplihack-memory-lib | @git v0.2.0 | memory/ | Yes | CognitiveMemory 6-type system |
| json-repair | >=0.47.7 | vendor/blarify | Yes | JSON repair for LLM output |
| langchain | >=1.2.3 | vendor/blarify | Yes | LLM agent framework |
| langchain-openai | >=1.1.7 | vendor/blarify | Yes | OpenAI LangChain integration |
| langchain-anthropic | >=1.3.1 | vendor/blarify | Yes | Anthropic LangChain integration |
| langchain-google-genai | >=4.1.3 | vendor/blarify | Yes | Google LangChain integration |
| tree-sitter | >=0.23.2 | vendor/blarify | Yes | Code parsing (multi-language) |
| tree-sitter-python | >=0.23.2 | vendor/blarify | Yes | Python grammar |
| tree-sitter-javascript | >=0.23.0 | vendor/blarify | Yes | JavaScript grammar |
| tree-sitter-typescript | >=0.23.2 | vendor/blarify | Yes | TypeScript grammar |
| tree-sitter-c-sharp | >=0.23.1 | vendor/blarify | Yes | C# grammar |
| tree-sitter-go | >=0.23.1 | vendor/blarify | Yes | Go grammar |
| tree-sitter-java | >=0.23.2 | vendor/blarify | Yes | Java grammar |
| tree-sitter-php | >=0.23.4 | vendor/blarify | Yes | PHP grammar |
| tree-sitter-ruby | >=0.23.0 | vendor/blarify | Yes | Ruby grammar |
| psutil | >=7.0.0 | vendor/blarify | Yes | Process utilities |
| protobuf | >=5.29.0 | vendor/blarify (SCIP) | Yes | SCIP index format |
| typing-extensions | >=4.12.2 | vendor/blarify | Yes | Python type backports |
| falkordb | >=1.0.10 | vendor/blarify | Yes | FalkorDB graph database |
| neo4j | >=5.25.0 | vendor/blarify | Yes | Neo4j graph database |
| jedi-language-server | >=0.43.1 | lsp_detector/ | Yes | Python LSP |
| docker | >=7.1.0 | docker/ | Yes | Docker API client |
| packaging | >=21.0 | auto_update, uvx | Yes | Version comparison |
| amplihack-agent-eval | @git main | eval/ | Yes | Agent evaluation framework |
