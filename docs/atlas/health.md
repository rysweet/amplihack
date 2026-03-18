---
title: Health Dashboard
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Health Dashboard
</nav>

# Health Dashboard

<div class="atlas-metadata">
Overall: :material-alert-circle:{ .atlas-health--warn } **PASS_WITH_WARNINGS** | Warnings: 10 | Failures: 0
</div>

## Check Results

| Check | Status | Details |
|-------|--------|---------|
| FILE_COVERAGE | :material-check-circle:{ .atlas-health--pass } | 601 .py files covered across layers 1, 2, 7 |
| CLI_COMMAND_COVERAGE | :material-check-circle:{ .atlas-health--pass } | 45 CLI commands all have journeys |
| EXPORT_CONSISTENCY | :material-alert-circle:{ .atlas-health--warn } | 18 exported names missing definitions |
| DEPENDENCY_CONSISTENCY | :material-alert-circle:{ .atlas-health--warn } | 22 declared deps appear unused |
| IO_TRACEABILITY | :material-alert-circle:{ .atlas-health--warn } | 91/178 I/O files in unreachable packages |
| SUBPROCESS_TRACEABILITY | :material-alert-circle:{ .atlas-health--warn } | 55/109 subprocess files in unreachable packages |
| PACKAGE_CONSISTENCY | :material-alert-circle:{ .atlas-health--warn } | layer1 vs manifest: 36 differences; layer3 vs manifest: 0 missing, 524 extra |
| ROUTE_COVERAGE | :material-check-circle:{ .atlas-health--pass } | 14 HTTP routes all have journeys |
| IMPORT_RESOLUTION | :material-alert-circle:{ .atlas-health--warn } | 54/194 imports unresolved |
| CLI_HANDLER_REACHABILITY | :material-check-circle:{ .atlas-health--pass } | 52 CLI commands have reachable handlers |
| DEAD_DEP_CROSS_VALIDATION | :material-alert-circle:{ .atlas-health--warn } | 1 deps marked unused in layer3 but found in layer2 |
| CIRCULAR_IMPORT_SEVERITY | :material-check-circle:{ .atlas-health--pass } | No circular dependencies detected |
| ENV_VAR_COMPLETENESS | :material-alert-circle:{ .atlas-health--warn } | 126 env vars found but no .env.example file |
| ROUTE_TEST_COVERAGE | :material-alert-circle:{ .atlas-health--warn } | 15/22 routes without test references |
| REEXPORT_CHAIN_VALIDATION | :material-alert-circle:{ .atlas-health--warn } | 6 broken re-export chains |

## Warnings

### EXPORT_CONSISTENCY

18 exported names missing definitions

Missing items:

- `/home/azureuser/src/amplihack/src/amplihack/__init__.py::__version__`
- `/home/azureuser/src/amplihack/src/amplihack/agents/goal_seeking/cognitive_adapter.py::HAS_COGNITIVE_MEMORY`
- `/home/azureuser/src/amplihack/src/amplihack/agents/goal_seeking/hive_mind/embeddings.py::HAS_SENTENCE_TRANSFORMERS`
- `/home/azureuser/src/amplihack/src/amplihack/agents/goal_seeking/hive_mind/query_expansion.py::HAS_ANTHROPIC`
- `/home/azureuser/src/amplihack/src/amplihack/agents/goal_seeking/hive_mind/reranker.py::HAS_CROSS_ENCODER`
- `/home/azureuser/src/amplihack/src/amplihack/dep_check.py::SDK_DEPENDENCIES`
- `/home/azureuser/src/amplihack/src/amplihack/eval/__init__.py::LongHorizonRunnerResult`
- `/home/azureuser/src/amplihack/src/amplihack/eval/__init__.py::CapabilityEvalTypeResult`
- `/home/azureuser/src/amplihack/src/amplihack/eval/__init__.py::CapabilityScenarioResult`
- `/home/azureuser/src/amplihack/src/amplihack/eval/__init__.py::CapabilityToolCall`
- `/home/azureuser/src/amplihack/src/amplihack/eval/matrix_eval.py::AGENT_TYPES`
- `/home/azureuser/src/amplihack/src/amplihack/fleet/_cli_commands.py::COPILOT_LOCK_DIR`
- `/home/azureuser/src/amplihack/src/amplihack/fleet/_cli_commands.py::COPILOT_LOG_DIR`
- `/home/azureuser/src/amplihack/src/amplihack/fleet/_defaults.py::DEFAULT_EXCLUDE_VMS`
- `/home/azureuser/src/amplihack/src/amplihack/fleet/_transcript_report.py::STRATEGY_KEYWORDS`
- `/home/azureuser/src/amplihack/src/amplihack/memory/kuzu/connector.py::KUZU_AVAILABLE`
- `/home/azureuser/src/amplihack/src/amplihack/testing/send_input_allowlist.py::DEFAULT_SAFE_PATTERNS`
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

- `/home/azureuser/src/amplihack/src/amplihack/testing/send_input_allowlist.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/vendor/multilspy/language_servers/jedi_language_server/jedi_server.py`
- `/home/azureuser/src/amplihack/src/amplihack/context/adaptive/detector.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/vendor/multilspy/language_servers/dart_language_server/dart_language_server.py`
- `/home/azureuser/src/amplihack/src/amplihack/fleet/_admiral_types.py`
- `/home/azureuser/src/amplihack/src/amplihack/fleet/fleet_state.py`
- `/home/azureuser/src/amplihack/src/amplihack/fleet/tests/test_fleet_session_reasoner.py`
- `/home/azureuser/src/amplihack/src/amplihack/fleet/tests/test_fleet_reasoners.py`
- `/home/azureuser/src/amplihack/src/amplihack/settings.py`
- `/home/azureuser/src/amplihack/src/amplihack/eval/self_improve/patch_proposer.py`

### SUBPROCESS_TRACEABILITY

55/109 subprocess files in unreachable packages

Missing items:

- `/home/azureuser/src/amplihack/src/amplihack/fleet/fleet_state.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/main.py`
- `/home/azureuser/src/amplihack/src/amplihack/fleet/fleet_adopt.py`
- `/home/azureuser/src/amplihack/src/amplihack/fleet/fleet_setup.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/mcp_server/server.py`
- `/home/azureuser/src/amplihack/src/amplihack/session.py`
- `/home/azureuser/src/amplihack/src/amplihack/eval/progressive_test_suite.py`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/code_references/scip_helper.py`
- `/home/azureuser/src/amplihack/src/amplihack/rust_trial.py`
- `/home/azureuser/src/amplihack/src/amplihack/eval/agent_adapter.py`

### PACKAGE_CONSISTENCY

layer1 vs manifest: 36 differences; layer3 vs manifest: 0 missing, 524 extra

Missing items:

- `layer1 vs manifest: 36 differences`
- `layer3 vs manifest: 0 missing, 524 extra`

### IMPORT_RESOLUTION

54/194 imports unresolved

Missing items:

- `/home/azureuser/src/amplihack/src/amplihack/bundle_generator/__init__.py imports BundleGeneratorError from /home/azureuser/src/amplihack/src/amplihack/exceptions.py`
- `/home/azureuser/src/amplihack/src/amplihack/bundle_generator/__init__.py imports DistributionError from /home/azureuser/src/amplihack/src/amplihack/exceptions.py`
- `/home/azureuser/src/amplihack/src/amplihack/bundle_generator/__init__.py imports GenerationError from /home/azureuser/src/amplihack/src/amplihack/exceptions.py`
- `/home/azureuser/src/amplihack/src/amplihack/bundle_generator/__init__.py imports PackagingError from /home/azureuser/src/amplihack/src/amplihack/exceptions.py`
- `/home/azureuser/src/amplihack/src/amplihack/bundle_generator/__init__.py imports ParsingError from /home/azureuser/src/amplihack/src/amplihack/exceptions.py`
- `/home/azureuser/src/amplihack/src/amplihack/bundle_generator/builder.py imports GenerationError from /home/azureuser/src/amplihack/src/amplihack/exceptions.py`
- `/home/azureuser/src/amplihack/src/amplihack/bundle_generator/cli.py imports BundleGeneratorError from /home/azureuser/src/amplihack/src/amplihack/exceptions.py`
- `/home/azureuser/src/amplihack/src/amplihack/bundle_generator/distributor.py imports DistributionError from /home/azureuser/src/amplihack/src/amplihack/exceptions.py`
- `/home/azureuser/src/amplihack/src/amplihack/bundle_generator/distributor.py imports RateLimitError from /home/azureuser/src/amplihack/src/amplihack/exceptions.py`
- `/home/azureuser/src/amplihack/src/amplihack/bundle_generator/distributor.py imports TimeoutError from /home/azureuser/src/amplihack/src/amplihack/exceptions.py`
- `/home/azureuser/src/amplihack/src/amplihack/bundle_generator/extractor.py imports ExtractionError from /home/azureuser/src/amplihack/src/amplihack/exceptions.py`
- `/home/azureuser/src/amplihack/src/amplihack/bundle_generator/filesystem_packager.py imports PackagingError from /home/azureuser/src/amplihack/src/amplihack/exceptions.py`
- `/home/azureuser/src/amplihack/src/amplihack/bundle_generator/generator.py imports GenerationError from /home/azureuser/src/amplihack/src/amplihack/exceptions.py`
- `/home/azureuser/src/amplihack/src/amplihack/bundle_generator/packager.py imports PackagingError from /home/azureuser/src/amplihack/src/amplihack/exceptions.py`
- `/home/azureuser/src/amplihack/src/amplihack/bundle_generator/parser.py imports ParsingError from /home/azureuser/src/amplihack/src/amplihack/exceptions.py`
- `/home/azureuser/src/amplihack/src/amplihack/bundle_generator/update_manager.py imports BundleGeneratorError from /home/azureuser/src/amplihack/src/amplihack/exceptions.py`
- `/home/azureuser/src/amplihack/src/amplihack/cli_extensions.py imports BundleDistributor from /home/azureuser/src/amplihack/src/amplihack/bundle_generator/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/cli_extensions.py imports BundlePackager from /home/azureuser/src/amplihack/src/amplihack/bundle_generator/__init__.py`
- `/home/azureuser/src/amplihack/src/amplihack/cli_extensions.py imports DistributionMethod from /home/azureuser/src/amplihack/src/amplihack/bundle_generator/models.py`
- `/home/azureuser/src/amplihack/src/amplihack/cli_extensions.py imports PackageFormat from /home/azureuser/src/amplihack/src/amplihack/bundle_generator/models.py`

### DEAD_DEP_CROSS_VALIDATION

1 deps marked unused in layer3 but found in layer2

Missing items:

- `rich`

### ENV_VAR_COMPLETENESS

126 env vars found but no .env.example file

Missing items:

- `AMPLIHACK_AGENT_BINARY`
- `AMPLIHACK_AUTO_INSTALL`
- `AMPLIHACK_AUTO_MODE`
- `AMPLIHACK_BLARIFY_MODE`
- `AMPLIHACK_DEBUG`
- `AMPLIHACK_DEFAULT_MODEL`
- `AMPLIHACK_ENABLE_BLARIFY`
- `AMPLIHACK_GRAPH_BACKEND`
- `AMPLIHACK_HOME`
- `AMPLIHACK_HOOK_ENGINE`
- `AMPLIHACK_IN_DOCKER`
- `AMPLIHACK_IS_STAGED`
- `AMPLIHACK_MEMORY_BACKEND`
- `AMPLIHACK_MEMORY_ENABLED`
- `AMPLIHACK_MODE`
- `AMPLIHACK_NONINTERACTIVE`
- `AMPLIHACK_NO_AUTO_INSTALL`
- `AMPLIHACK_ORIGINAL_CWD`
- `AMPLIHACK_PLUGIN_INSTALLED`
- `AMPLIHACK_PROXY_TIMEOUT`

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

6 broken re-export chains

Missing items:

- `/home/azureuser/src/amplihack/src/amplihack/__init__.py::__version__`
- `/home/azureuser/src/amplihack/src/amplihack/eval/__init__.py::LongHorizonRunnerResult`
- `/home/azureuser/src/amplihack/src/amplihack/eval/__init__.py::CapabilityEvalTypeResult`
- `/home/azureuser/src/amplihack/src/amplihack/eval/__init__.py::CapabilityScenarioResult`
- `/home/azureuser/src/amplihack/src/amplihack/eval/__init__.py::CapabilityToolCall`
- `/home/azureuser/src/amplihack/src/amplihack/vendor/blarify/vendor/multilspy/__init__.py::Types`
