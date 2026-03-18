---
title: Health Dashboard
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Health Dashboard
</nav>

# Health Dashboard

<div class="atlas-metadata">
Overall: :material-alert-circle:{ .atlas-health--warn } **PASS_WITH_WARNINGS** | Warnings: 11 | Failures: 0
</div>

## Check Results

| Check | Status | Details |
|-------|--------|---------|
| FILE_COVERAGE | :material-check-circle:{ .atlas-health--pass } | 601 .py files covered across layers 1, 2, 7 |
| CLI_COMMAND_COVERAGE | :material-check-circle:{ .atlas-health--pass } | 45 CLI commands all have journeys |
| EXPORT_CONSISTENCY | :material-alert-circle:{ .atlas-health--warn } | 5 exported names missing definitions |
| DEPENDENCY_CONSISTENCY | :material-alert-circle:{ .atlas-health--warn } | 22 declared deps appear unused |
| IO_TRACEABILITY | :material-alert-circle:{ .atlas-health--warn } | 91/178 I/O files in unreachable packages |
| SUBPROCESS_TRACEABILITY | :material-alert-circle:{ .atlas-health--warn } | 55/109 subprocess files in unreachable packages |
| PACKAGE_CONSISTENCY | :material-alert-circle:{ .atlas-health--warn } | layer1 vs manifest: 36 differences; layer3 vs manifest: 0 missing, 524 extra |
| ROUTE_COVERAGE | :material-check-circle:{ .atlas-health--pass } | 14 HTTP routes all have journeys |
| IMPORT_RESOLUTION | :material-alert-circle:{ .atlas-health--warn } | 32/1379 imports unresolved |
| CLI_HANDLER_REACHABILITY | :material-check-circle:{ .atlas-health--pass } | 52 CLI commands have reachable handlers |
| DEAD_DEP_CROSS_VALIDATION | :material-alert-circle:{ .atlas-health--warn } | 1 deps marked unused in layer3 but found in layer2 |
| CIRCULAR_IMPORT_SEVERITY | :material-alert-circle:{ .atlas-health--warn } | 8 circular dependency cycles found (6 internal, 2 vendor) |
| ENV_VAR_COMPLETENESS | :material-alert-circle:{ .atlas-health--warn } | 128 env vars found but no .env.example file |
| ROUTE_TEST_COVERAGE | :material-alert-circle:{ .atlas-health--warn } | 15/22 routes without test references |
| REEXPORT_CHAIN_VALIDATION | :material-alert-circle:{ .atlas-health--warn } | 5 broken re-export chains |

## Warnings

### EXPORT_CONSISTENCY

5 exported names missing definitions

Missing items:

- `/home/azureuser/src/amplihack/src/amplihack/eval/__init__.py::LongHorizonRunnerResult`
- `/home/azureuser/src/amplihack/src/amplihack/eval/__init__.py::CapabilityEvalTypeResult`
- `/home/azureuser/src/amplihack/src/amplihack/eval/__init__.py::CapabilityScenarioResult`
- `/home/azureuser/src/amplihack/src/amplihack/eval/__init__.py::CapabilityToolCall`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/vendor/multilspy/__init__.py::Types`

### DEPENDENCY_CONSISTENCY

22 declared deps appear unused

Missing items:

- `github-copilot-sdk`
- `azure-identity`
- `amplihack-memory-lib`
- `langchain`
- `protobuf`
- `jedi-language-server`
- `amplihack-agent-eval`
- `agent-framework-core`
- `opentelemetry-semantic-conventions-ai`
- `amplifier-core`
- `pytest-asyncio`
- `pytest-cov`
- `pytest-asyncio`
- `pytest-cov`
- `pytest-asyncio`
- `black`
- `ruff`
- `build`
- `pre-commit`
- `beautifulsoup4`
- `lxml`
- `pyyaml`

### IO_TRACEABILITY

91/178 I/O files in unreachable packages

Missing items:

- `/home/azureuser/src/amplihack/src/amplihack/eval/agent_subprocess.py`
- `/home/azureuser/src/amplihack/src/amplihack/fleet/fleet_state.py`
- `/home/azureuser/src/amplihack/src/amplihack/fleet/_cli_scout_advance.py`
- `/home/azureuser/src/amplihack/src/amplihack/tracing/trace_logger.py`
- `/home/azureuser/src/amplihack/src/amplihack/fleet/tests/test_fleet_results.py`
- `/home/azureuser/src/amplihack/src/amplihack/eval/progressive_test_suite.py`
- `/home/azureuser/src/amplihack/src/amplihack/eval/grader.py`
- `/home/azureuser/src/amplihack/src/amplihack/eval/harness_runner.py`
- `/home/azureuser/src/amplihack/src/amplihack/eval/general_capability_eval.py`
- `/home/azureuser/src/amplihack/src/amplihack/settings_generator/generator.py`

### SUBPROCESS_TRACEABILITY

55/109 subprocess files in unreachable packages

Missing items:

- `/home/azureuser/src/amplihack/src/amplihack/fleet/fleet_state.py`
- `/home/azureuser/src/amplihack/src/amplihack/fleet/fleet_health.py`
- `/home/azureuser/src/amplihack/src/amplihack/eval/progressive_test_suite.py`
- `/home/azureuser/src/amplihack/src/amplihack/eval/harness_runner.py`
- `/home/azureuser/src/amplihack/src/amplihack/eval/general_capability_eval.py`
- `/home/azureuser/src/amplihack/src/amplihack/meta_delegation/subprocess_adapter.py`
- `/home/azureuser/src/amplihack/src/amplihack/fleet/_backends.py`
- `/home/azureuser/src/amplihack/src/amplihack/cli.py`
- `/home/azureuser/src/amplihack/src/amplihack/auto_update.py`
- `/home/azureuser/src/amplihack/src/amplihack/fleet/fleet_session_reasoner.py`

### PACKAGE_CONSISTENCY

layer1 vs manifest: 36 differences; layer3 vs manifest: 0 missing, 524 extra

Missing items:

- `layer1 vs manifest: 36 differences`
- `layer3 vs manifest: 0 missing, 524 extra`

### IMPORT_RESOLUTION

32/1379 imports unresolved

Missing items:

- `/home/azureuser/src/amplihack/src/amplihack/cli_extensions.py imports BundleDistributor from /home/azureuser/src/amplihack/src/amplihack/bundle_generator/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/cli_extensions.py imports BundlePackager from /home/azureuser/src/amplihack/src/amplihack/bundle_generator/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/cli_extensions.py imports DistributionMethod from /home/azureuser/src/amplihack/src/amplihack/bundle_generator/models.py`
- `/home/azureuser/src/amplihack/src/amplihack/cli_extensions.py imports PackageFormat from /home/azureuser/src/amplihack/src/amplihack/bundle_generator/models.py`
- `/home/azureuser/src/amplihack/src/amplihack/eval/self_improve/__init__.py imports runner from /home/azureuser/src/amplihack/src/amplihack/eval/self_improve/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/code_hierarchy/languages/language_definitions.py imports RelationshipType from /home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/relationship/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/code_hierarchy/tree_sitter_helper.py imports Reference from /home/azureuser/src/amplihack/src/amplihack/vendor/blarify/code_references/types/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/code_hierarchy/tree_sitter_helper.py imports DefinitionNode from /home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/node/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/code_hierarchy/tree_sitter_helper.py imports FileNode from /home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/node/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/code_hierarchy/tree_sitter_helper.py imports FolderNode from /home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/node/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/code_hierarchy/tree_sitter_helper.py imports Node from /home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/node/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/code_references/lsp_helper.py imports DefinitionNode from /home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/node/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/graph.py imports Relationship from /home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/relationship/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/node/class_node.py imports Reference from /home/azureuser/src/amplihack/src/amplihack/vendor/blarify/code_references/types/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/node/folder_node.py imports Relationship from /home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/relationship/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/node/folder_node.py imports RelationshipCreator from /home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/relationship/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/node/types/definition_node.py imports Reference from /home/azureuser/src/amplihack/src/amplihack/vendor/blarify/code_references/types/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/node/types/definition_node.py imports Relationship from /home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/relationship/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/node/types/definition_node.py imports RelationshipCreator from /home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/relationship/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/node/types/node.py imports NodeLabels from /home/azureuser/src/amplihack/src/amplihack/vendor/blarify/graph/node/__init__.py`

### DEAD_DEP_CROSS_VALIDATION

1 deps marked unused in layer3 but found in layer2

Missing items:

- `rich`

### CIRCULAR_IMPORT_SEVERITY

8 circular dependency cycles found (6 internal, 2 vendor)

Missing items:

- `['utils.prerequisites', 'utils.claude_cli', 'utils.prerequisites']`
- `['memory.kuzu.indexing.background_indexer', 'memory.kuzu.indexing.orchestrator', 'memory.kuzu.indexing.background_indexer']`
- `['launcher.core', 'launcher', 'launcher.copilot', 'cli', 'uninstall', 'settings', 'install', 'hook_verification', 'amplihack', 'launcher.core']`
- `['agents.goal_seeking.hive_mind.gossip', 'agents.goal_seeking.hive_mind.hive_graph', 'agents.goal_seeking.hive_mind.gossip']`
- `['proxy.monitoring', 'proxy.azure_errors', 'proxy.monitoring']`
- `['proxy.streaming', 'proxy.integrated_proxy', 'proxy.streaming']`

### ENV_VAR_COMPLETENESS

128 env vars found but no .env.example file

Missing items:

- `AMPLIHACK_AGENT_BINARY`
- `AMPLIHACK_AUTO_INSTALL`
- `AMPLIHACK_AUTO_MODE`
- `AMPLIHACK_BLARIFY_MODE`
- `AMPLIHACK_DEBUG`
- `AMPLIHACK_DEFAULT_MODEL`
- `AMPLIHACK_ENABLE_BLARIFY`
- `AMPLIHACK_GRAPH_BACKEND`
- `AMPLIHACK_GRAPH_DB_PATH`
- `AMPLIHACK_HOME`
- `AMPLIHACK_HOOK_ENGINE`
- `AMPLIHACK_IN_DOCKER`
- `AMPLIHACK_IS_STAGED`
- `AMPLIHACK_KUZU_DB_PATH`
- `AMPLIHACK_MEMORY_BACKEND`
- `AMPLIHACK_MEMORY_ENABLED`
- `AMPLIHACK_MODE`
- `AMPLIHACK_NONINTERACTIVE`
- `AMPLIHACK_NO_AUTO_INSTALL`
- `AMPLIHACK_ORIGINAL_CWD`

### ROUTE_TEST_COVERAGE

15/22 routes without test references

Missing items:

- `POST /v1/messages (create_message)`
- `POST /v1/messages/count_tokens (count_tokens)`
- `GET /performance/metrics (performance_metrics)`
- `GET /performance/cache/status (cache_status)`
- `GET /performance/cache/clear (clear_caches)`
- `GET /performance/benchmark (performance_benchmark)`
- `GET /azure/test-error-handling (test_azure_error_handling)`
- `GET /azure/status (azure_status)`
- `POST /v1/messages (create_message)`
- `GET /stream/logs (stream_logs)`
- `POST /v1/chat/completions (chat_completions)`
- `POST /v1/messages/count_tokens (count_tokens)`
- `POST /v1/messages (create_message)`
- `POST /v1/messages/count_tokens (count_tokens)`
- `POST /openai/responses (openai_responses)`

### REEXPORT_CHAIN_VALIDATION

5 broken re-export chains

Missing items:

- `/home/azureuser/src/amplihack/src/amplihack/eval/__init__.py::LongHorizonRunnerResult`
- `/home/azureuser/src/amplihack/src/amplihack/eval/__init__.py::CapabilityEvalTypeResult`
- `/home/azureuser/src/amplihack/src/amplihack/eval/__init__.py::CapabilityScenarioResult`
- `/home/azureuser/src/amplihack/src/amplihack/eval/__init__.py::CapabilityToolCall`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/vendor/multilspy/__init__.py::Types`
