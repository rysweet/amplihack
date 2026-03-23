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

| Check                     | Status                                         | Details                                                                       |
| ------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------------- |
| FILE_COVERAGE             | :material-check-circle:{ .atlas-health--pass } | 2304 .py files covered across layers 1, 2, 7                                  |
| CLI_COMMAND_COVERAGE      | :material-check-circle:{ .atlas-health--pass } | 84 CLI commands all have journeys                                             |
| EXPORT_CONSISTENCY        | :material-alert-circle:{ .atlas-health--warn } | 16 exported names missing definitions                                         |
| DEPENDENCY_CONSISTENCY    | :material-alert-circle:{ .atlas-health--warn } | 18 declared deps appear unused                                                |
| IO_TRACEABILITY           | :material-alert-circle:{ .atlas-health--warn } | 533/916 I/O files in unreachable packages                                     |
| SUBPROCESS_TRACEABILITY   | :material-alert-circle:{ .atlas-health--warn } | 190/335 subprocess files in unreachable packages                              |
| PACKAGE_CONSISTENCY       | :material-alert-circle:{ .atlas-health--warn } | layer1 vs manifest: 65 differences; layer3 vs manifest: 0 missing, 2083 extra |
| ROUTE_COVERAGE            | :material-check-circle:{ .atlas-health--pass } | 21 HTTP routes all have journeys                                              |
| IMPORT_RESOLUTION         | :material-alert-circle:{ .atlas-health--warn } | 84/2938 imports unresolved                                                    |
| CLI_HANDLER_REACHABILITY  | :material-check-circle:{ .atlas-health--pass } | 172 CLI commands have reachable handlers                                      |
| DEAD_DEP_CROSS_VALIDATION | :material-alert-circle:{ .atlas-health--warn } | 1 deps marked unused in layer3 but found in layer2                            |
| CIRCULAR_IMPORT_SEVERITY  | :material-alert-circle:{ .atlas-health--warn } | 12 circular dependency cycles found (10 internal, 2 vendor)                   |
| ENV_VAR_COMPLETENESS      | :material-alert-circle:{ .atlas-health--warn } | 253 env vars found but no .env.example file                                   |
| ROUTE_TEST_COVERAGE       | :material-alert-circle:{ .atlas-health--warn } | 15/33 routes without test references                                          |
| REEXPORT_CHAIN_VALIDATION | :material-alert-circle:{ .atlas-health--warn } | 14 broken re-export chains                                                    |

## Warnings

### EXPORT_CONSISTENCY

16 exported names missing definitions

Missing items:

- `.claude/scenarios/az-devops-tools/__init__.py::auth_check`
- `.claude/scenarios/az-devops-tools/__init__.py::format_html`
- `.claude/scenarios/az-devops-tools/__init__.py::create_work_item`
- `.claude/scenarios/az-devops-tools/__init__.py::link_parent`
- `.claude/scenarios/az-devops-tools/__init__.py::query_wiql`
- `.claude/scenarios/az-devops-tools/__init__.py::list_types`
- `.claude/tools/amplihack/hooks/claude_power_steering.py::CLAUDE_SDK_AVAILABLE`
- `.claude/tools/amplihack/profile_management/__init__.py::cli_main`
- `amplifier-bundle/tools/amplihack/profile_management/__init__.py::cli_main`
- `docs/claude/tools/amplihack/profile_management/__init__.py::cli_main`
- `src/amplihack/cli/hive_haymaker.py::hive_group`
- `src/amplihack/eval/__init__.py::LongHorizonRunnerResult`
- `src/amplihack/eval/__init__.py::CapabilityEvalTypeResult`
- `src/amplihack/eval/__init__.py::CapabilityScenarioResult`
- `src/amplihack/eval/__init__.py::CapabilityToolCall`
- `src/amplihack/vendor/blarify/vendor/multilspy/__init__.py::Types`

### DEPENDENCY_CONSISTENCY

18 declared deps appear unused

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
- `pytest-cov`
- `pytest-cov`
- `black`
- `ruff`
- `build`
- `pre-commit`
- `beautifulsoup4`
- `lxml`
- `pyyaml`

### IO_TRACEABILITY

533/916 I/O files in unreachable packages

Missing items:

- `amplifier-bundle/skills/pptx/scripts/rearrange.py`
- `.claude/skills/dynamic-debugger/tests/test_mcp_integration.py`
- `.claude/scenarios/az-devops-tools/format_html.py`
- `.claude/tools/amplihack/remote/test_components.py`
- `.github/scripts/link_fixer.py`
- `tests/eval/test_long_horizon_memory.py`
- `.claude/tools/amplihack/remote/test_with_existing_vm.py`
- `.claude/tools/test_ci_status.py`
- `tests/test_settings_migration.py`
- `.claude/tools/amplihack/remote/tests/test_session.py`

### SUBPROCESS_TRACEABILITY

190/335 subprocess files in unreachable packages

Missing items:

- `.claude/skills/dynamic-debugger/tests/test_mcp_integration.py`
- `.claude/tools/amplihack/remote/test_components.py`
- `.github/scripts/link_fixer.py`
- `.claude/tools/amplihack/remote/test_with_existing_vm.py`
- `.claude/tools/platform_bridge/detector.py`
- `.claude/skills/common/verification/verify_skill.py`
- `.claude/tools/amplihack/hooks/test_integration.py`
- `.claude/tools/ci_workflow.py`
- `.claude/tools/amplihack/remote/tests/test_context_packager.py`
- `.claude/tools/amplihack/hooks/session_end.py`

### PACKAGE_CONSISTENCY

layer1 vs manifest: 65 differences; layer3 vs manifest: 0 missing, 2083 extra

Missing items:

- `layer1 vs manifest: 65 differences`
- `layer3 vs manifest: 0 missing, 2083 extra`

### IMPORT_RESOLUTION

84/2938 imports unresolved

Missing items:

- `.claude/tools/amplihack/builders/claude_transcript_builder.py imports amplihack from amplihack/__init__.py`
- `.claude/tools/amplihack/builders/codex_transcripts_builder.py imports amplihack from amplihack/__init__.py`
- `.claude/tools/amplihack/hooks/power_steering_checker/__init__.py imports get_shared_runtime_dir from .claude/tools/amplihack/hooks/power_steering_checker/main_checker.py`
- `.claude/tools/amplihack/hooks/power_steering_checker/__init__.py imports analyze_consideration from .claude/tools/amplihack/hooks/power_steering_checker/sdk_calls.py`
- `.claude/tools/amplihack/memory/context_preservation.py imports amplihack from amplihack/__init__.py`
- `.claude/tools/amplihack/memory/examples.py imports amplihack from amplihack/__init__.py`
- `.claude/tools/amplihack/paths.py imports amplihack from amplihack/__init__.py`
- `.claude/tools/amplihack/remote/tests/test_cli.py imports cli from .claude/tools/amplihack/remote/__init__.py`
- `.github/scripts/pr_triage/validator.py imports github_client from .github/scripts/pr_triage/__init__.py`
- `.github/scripts/pr_triage/validator.py imports security from .github/scripts/pr_triage/__init__.py`
- `.github/scripts/pr_triage/validator.py imports analyzers from .github/scripts/pr_triage/__init__.py`
- `.github/scripts/pr_triage/validator.py imports analyzers_mvp from .github/scripts/pr_triage/__init__.py`
- `amplifier-bundle/tools/amplihack/builders/claude_transcript_builder.py imports amplihack from amplihack/__init__.py`
- `amplifier-bundle/tools/amplihack/builders/codex_transcripts_builder.py imports amplihack from amplihack/__init__.py`
- `amplifier-bundle/tools/amplihack/memory/context_preservation.py imports amplihack from amplihack/__init__.py`
- `amplifier-bundle/tools/amplihack/memory/examples.py imports amplihack from amplihack/__init__.py`
- `amplifier-bundle/tools/amplihack/paths.py imports amplihack from amplihack/__init__.py`
- `amplifier-bundle/tools/amplihack/remote/tests/test_cli.py imports cli from amplifier-bundle/tools/amplihack/remote/__init__.py`
- `docs/claude/tools/amplihack/builders/claude_transcript_builder.py imports amplihack from amplihack/__init__.py`
- `docs/claude/tools/amplihack/builders/codex_transcripts_builder.py imports amplihack from amplihack/__init__.py`

### DEAD_DEP_CROSS_VALIDATION

1 deps marked unused in layer3 but found in layer2

Missing items:

- `rich`

### CIRCULAR_IMPORT_SEVERITY

12 circular dependency cycles found (10 internal, 2 vendor)

Missing items:

- `['.claude.skills.documentation-writing.github_pages.generator', '.claude.skills.documentation-writing.github_pages.validator', '.claude.skills.documentation-writing.github_pages.deployer', '.claude.skills.documentation-writing.github_pages', '.claude.skills.documentation-writing.github_pages.generator']`
- `['.github.scripts.pr_triage.validator', '.github.scripts.pr_triage', '.github.scripts.pr_triage.validator']`
- `['amplifier-bundle.skills.documentation-writing.github_pages.deployer', 'amplifier-bundle.skills.documentation-writing.github_pages.generator', 'amplifier-bundle.skills.documentation-writing.github_pages.validator', 'amplifier-bundle.skills.documentation-writing.github_pages', 'amplifier-bundle.skills.documentation-writing.github_pages.deployer']`
- `['docs.claude.skills.documentation-writing.github_pages.generator', 'docs.claude.skills.documentation-writing.github_pages.deployer', 'docs.claude.skills.documentation-writing.github_pages.validator', 'docs.claude.skills.documentation-writing.github_pages', 'docs.claude.skills.documentation-writing.github_pages.generator']`
- `['src.amplihack.utils.claude_cli', 'src.amplihack.utils.prerequisites', 'src.amplihack.utils.claude_cli']`
- `['src.amplihack.memory.kuzu.indexing.background_indexer', 'src.amplihack.memory.kuzu.indexing.orchestrator', 'src.amplihack.memory.kuzu.indexing.background_indexer']`
- `['src.amplihack.uninstall', 'src.amplihack.install', 'src.amplihack.launcher.copilot', 'src.amplihack.launcher.core', 'src.amplihack.launcher', 'src.amplihack.cli', 'src.amplihack.hook_verification', 'src.amplihack.settings', 'src.amplihack', 'src.amplihack.uninstall']`
- `['src.amplihack.agents.goal_seeking.hive_mind.gossip', 'src.amplihack.agents.goal_seeking.hive_mind.hive_graph', 'src.amplihack.agents.goal_seeking.hive_mind.gossip']`
- `['src.amplihack.proxy.monitoring', 'src.amplihack.proxy.azure_errors', 'src.amplihack.proxy.monitoring']`
- `['src.amplihack.proxy.streaming', 'src.amplihack.proxy.integrated_proxy', 'src.amplihack.proxy.streaming']`

### ENV_VAR_COMPLETENESS

253 env vars found but no .env.example file

Missing items:

- `AGENT_DOMAIN`
- `AGENT_ID`
- `AMPLIHACK_AGENTS_PER_APP`
- `AMPLIHACK_AGENT_BINARY`
- `AMPLIHACK_AGENT_COUNT`
- `AMPLIHACK_AGENT_NAME`
- `AMPLIHACK_AGENT_PROMPT`
- `AMPLIHACK_AGENT_READY_REPUBLISH_COOLDOWN_SECONDS`
- `AMPLIHACK_AGENT_TOPOLOGY`
- `AMPLIHACK_APP_COUNT`
- `AMPLIHACK_APP_INDEX`
- `AMPLIHACK_AUTO_DEV`
- `AMPLIHACK_AUTO_INSTALL`
- `AMPLIHACK_AUTO_MODE`
- `AMPLIHACK_AUTO_PRECOMMIT`
- `AMPLIHACK_BASE_DIR`
- `AMPLIHACK_BLARIFY_MODE`
- `AMPLIHACK_DEBUG`
- `AMPLIHACK_DEFAULT_MODEL`
- `AMPLIHACK_DELEGATE`

### ROUTE_TEST_COVERAGE

15/33 routes without test references

Missing items:

- `POST /learn_fact (learn_fact)`
- `POST /learn_batch (learn_batch)`
- `POST /set_group (set_group)`
- `POST /reset (reset_agent)`
- `POST /v1/messages (create_message)`
- `POST /v1/messages (create_message)`
- `GET /performance/cache/status (cache_status)`
- `GET /performance/cache/clear (clear_caches)`
- `GET /azure/test-error-handling (test_azure_error_handling)`
- `GET /azure/status (azure_status)`
- `POST /v1/messages (create_message)`
- `GET /stream/logs (stream_logs)`
- `POST /v1/chat/completions (chat_completions)`
- `POST /v1/messages (create_message)`
- `POST /openai/responses (openai_responses)`

### REEXPORT_CHAIN_VALIDATION

14 broken re-export chains

Missing items:

- `.claude/scenarios/az-devops-tools/__init__.py::auth_check`
- `.claude/scenarios/az-devops-tools/__init__.py::format_html`
- `.claude/scenarios/az-devops-tools/__init__.py::create_work_item`
- `.claude/scenarios/az-devops-tools/__init__.py::link_parent`
- `.claude/scenarios/az-devops-tools/__init__.py::query_wiql`
- `.claude/scenarios/az-devops-tools/__init__.py::list_types`
- `.claude/tools/amplihack/profile_management/__init__.py::cli_main`
- `amplifier-bundle/tools/amplihack/profile_management/__init__.py::cli_main`
- `docs/claude/tools/amplihack/profile_management/__init__.py::cli_main`
- `src/amplihack/eval/__init__.py::LongHorizonRunnerResult`
- `src/amplihack/eval/__init__.py::CapabilityEvalTypeResult`
- `src/amplihack/eval/__init__.py::CapabilityScenarioResult`
- `src/amplihack/eval/__init__.py::CapabilityToolCall`
- `src/amplihack/vendor/blarify/vendor/multilspy/__init__.py::Types`
