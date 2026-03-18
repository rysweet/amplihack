Mode: static-approximation

# Layer 2: AST+LSP Symbol Bindings

**Slug:** `ast-lsp-bindings` | **Display Order:** 2
**Last rebuilt:** 2026-03-18 | **Package version:** 0.6.85

No LSP server was available for this analysis. All symbol bindings were derived via static grep/read of `__all__` exports and `from amplihack.X import Y` statements.

## Public API Boundaries (__all__ exports)

Modules with explicit `__all__` declarations (38 files found):

| Module | Key Exports |
|---|---|
| `amplihack` (root) | `main`, `install`, `uninstall`, `ensure_dirs`, `copytree_manifest` |
| `settings` | `ensure_settings_json`, `update_hook_paths` |
| `launcher` | `ClaudeLauncher`, `ClaudeDirectoryDetector`, `PrerequisiteChecker`, `AutoStager`, `ClaudeBinaryManager` |
| `proxy.token_sanitizer` | `TokenSanitizer`, `sanitize` |
| `security` | `scan`, `SecurityScanner` |
| `safety` | `StagingGuard` |
| `docker` | `DockerDetector`, `DockerManager` |
| `uvx` | `UVXManager` |
| `utils` | `slugify`, `claude_cli`, `prerequisites`, `defensive` |
| `recipes` | `RecipeParser`, `run_recipe_via_rust`, `discover_recipes` |
| `recipes.discovery` | `discover_recipes`, `list_recipes`, `find_recipe`, `RecipeInfo`, `_AMPLIHACK_HOME_BUNDLE_DIR` (module-level, used by `rust_runner`) |
| `recipe_cli` | `create_recipe_subparser`, `handle_recipe_command` |
| `fleet` | `FleetObserver`, `FleetCLI`, `SessionContext` |
| `knowledge_builder` | `KnowledgeBuilder`, `KnowledgeGraph` |
| `bundle_generator` | `BundleBuilder`, `BundlePackager` |
| `workflows` | `WorkflowEngine` |
| `settings_generator` | `SettingsGenerator` |
| `power_steering` | `prompt_re_enable_if_disabled` |
| `lsp_detector` | `LSPDetector` |
| `memory.discoveries` | `store_discovery`, `get_recent_discoveries` |
| `eval` | `teaching_eval`, `grader`, `progressive_test_suite` |
| `hooks.launcher_detector` | `LauncherDetector`, `LauncherInfo` |
| `context.adaptive` | `LauncherDetector`, `HookStrategy`, `ClaudeStrategy`, `CopilotStrategy` |
| `vendor.blarify.prebuilt` | `GraphBuilder` |

## Cross-Package Imports

Key import relationships between top-level subpackages:

| Source | Imports From |
|---|---|
| `cli.py` | `launcher`, `proxy`, `fleet`, `recipes`, `bundle_generator`, `plugin_manager`, `eval`, `settings`, `uvx`, `docker`, `security` |
| `recipe_cli/recipe_command` | `recipes` |
| `launcher/auto_mode` | `launcher` (internal: `completion_signals`, `fork_manager`, `json_logger`, `session_capture`, `work_summary`) |
| `fleet/fleet_copilot` | `fleet` (internal: `_constants`, `_validation`, `_backends`, `_transcript`, `fleet_session_reasoner`, `prompts`) |
| `eval/*` | `agents.domain_agents`, `knowledge_builder` |
| `knowledge_builder/orchestrator` | `knowledge_builder.kb_types`, `knowledge_builder.modules.*` |
| `recipes/rust_runner` | `recipes.discovery` (`_AMPLIHACK_HOME_BUNDLE_DIR`, `_PACKAGE_BUNDLE_DIR`, `_REPO_ROOT_BUNDLE_DIR`), `recipes.models`, stdlib `signal` |
| `recipes/discovery` | stdlib `os` (module-level `os.environ.get` for `AMPLIHACK_HOME`) |
| `vendor/blarify/*` | Self-contained (only intra-vendor imports) |

## Dead Code Candidates

Files that are exported but not imported by any other package module:

| File | Reason |
|---|---|
| `examples/usage_example.py` | Demo file, imports `launcher` and `proxy` but never imported |
| `examples/proxy_context_usage.py` | Demo file, imports `proxy.config` and `proxy.manager` |
| `rust_trial.py` | Experimental, has its own entry point in pyproject.toml |
| `copilot_auto_install.py` | Standalone utility, no cross-package importers found |
| `staging_cleanup.py` | Standalone utility |
| `memory_auto_install.py` | Standalone utility |

## Diagrams

### Mermaid Diagram

> **Note:** SVGs were not regenerated (mmdc/dot not available). Refer to source files for the current truth.

![AST+LSP Symbol Bindings - Mermaid](ast-lsp-bindings-mermaid.svg)

### Graphviz Diagram
![AST+LSP Symbol Bindings - Graphviz](ast-lsp-bindings-dot.svg)

**Source files:** [ast-lsp-bindings.mmd](ast-lsp-bindings.mmd) | [ast-lsp-bindings.dot](ast-lsp-bindings.dot)
