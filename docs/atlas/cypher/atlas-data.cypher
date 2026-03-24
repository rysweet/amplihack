// atlas-data.cypher — Populate nodes from inventory analysis

// --- Services ---
CREATE (s:Service {name: 'amplihack-cli', language: 'Python', port: 0, path: 'src/amplihack/cli.py'});
CREATE (s:Service {name: 'recipe-runner', language: 'Python', port: 0, path: 'src/amplihack/recipe_cli/recipe_command.py'});
CREATE (s:Service {name: 'fleet-cli', language: 'Python', port: 0, path: 'src/amplihack/fleet/_cli_commands.py'});
CREATE (s:Service {name: 'auto-mode', language: 'Python', port: 0, path: 'src/amplihack/launcher/auto_mode.py'});
CREATE (s:Service {name: 'docker-manager', language: 'Python', port: 0, path: 'src/amplihack/docker/manager.py'});
CREATE (s:Service {name: 'claude-launcher', language: 'Python', port: 0, path: 'src/amplihack/launcher/core.py'});
CREATE (s:Service {name: 'copilot-launcher', language: 'Python', port: 0, path: 'src/amplihack/launcher/copilot.py'});
CREATE (s:Service {name: 'codex-launcher', language: 'Python', port: 0, path: 'src/amplihack/launcher/codex.py'});
CREATE (s:Service {name: 'amplifier-launcher', language: 'Python', port: 0, path: 'src/amplihack/launcher/amplifier.py'});
CREATE (s:Service {name: 'memory-system', language: 'Python', port: 0, path: 'src/amplihack/memory/'});
CREATE (s:Service {name: 'blarify', language: 'Python', port: 0, path: 'src/amplihack/vendor/blarify/'});
CREATE (s:Service {name: 'trace-logger', language: 'Python', port: 0, path: 'src/amplihack/tracing/trace_logger.py'});


// --- Routes (CLI Commands) ---
CREATE (r:Route {method: 'CLI', path: 'amplihack launch', handler: 'cli.launch_command', auth: 'none'});
CREATE (r:Route {method: 'CLI', path: 'amplihack install', handler: 'install.copytree_manifest', auth: 'none'});
CREATE (r:Route {method: 'CLI', path: 'amplihack uninstall', handler: 'uninstall.uninstall', auth: 'none'});
CREATE (r:Route {method: 'CLI', path: 'amplihack update', handler: 'auto_update.update', auth: 'none'});
CREATE (r:Route {method: 'CLI', path: 'amplihack claude', handler: 'cli.launch_command', auth: 'none'});
CREATE (r:Route {method: 'CLI', path: 'amplihack copilot', handler: 'launcher.copilot.launch_copilot', auth: 'none'});
CREATE (r:Route {method: 'CLI', path: 'amplihack codex', handler: 'launcher.codex.launch_codex', auth: 'none'});
CREATE (r:Route {method: 'CLI', path: 'amplihack amplifier', handler: 'launcher.amplifier.launch_amplifier', auth: 'none'});
CREATE (r:Route {method: 'CLI', path: 'amplihack recipe run', handler: 'recipes.rust_runner', auth: 'none'});
CREATE (r:Route {method: 'CLI', path: 'amplihack recipe list', handler: 'recipes.discovery', auth: 'none'});
CREATE (r:Route {method: 'CLI', path: 'amplihack fleet', handler: 'fleet.fleet_cli', auth: 'none'});
CREATE (r:Route {method: 'CLI', path: 'amplihack memory tree', handler: 'memory.cli_visualize', auth: 'none'});
CREATE (r:Route {method: 'CLI', path: 'amplihack plugin install', handler: 'plugin_cli.plugin_install_command', auth: 'none'});
CREATE (r:Route {method: 'CLI', path: 'amplihack new', handler: 'goal_agent_generator.cli', auth: 'none'});
CREATE (r:Route {method: 'HOOK', path: 'hook/session_start', handler: 'hooks.session_start', auth: 'none'});
CREATE (r:Route {method: 'HOOK', path: 'hook/stop', handler: 'hooks.manager.execute_stop_hook', auth: 'none'});
CREATE (r:Route {method: 'HOOK', path: 'hook/pre_tool_use', handler: 'hooks.pre_tool_use', auth: 'none'});
CREATE (r:Route {method: 'HOOK', path: 'hook/post_tool_use', handler: 'hooks.post_tool_use', auth: 'none'});

// --- Environment Variables ---
CREATE (e:EnvVar {name: 'AMPLIHACK_HOME', required: false, default_value: '~/.amplihack'});
CREATE (e:EnvVar {name: 'AMPLIHACK_DEBUG', required: false, default_value: ''});
CREATE (e:EnvVar {name: 'AMPLIHACK_AGENT_BINARY', required: false, default_value: 'claude'});
CREATE (e:EnvVar {name: 'AMPLIHACK_AUTO_MODE', required: false, default_value: ''});
CREATE (e:EnvVar {name: 'AMPLIHACK_USE_DOCKER', required: false, default_value: ''});
CREATE (e:EnvVar {name: 'AMPLIHACK_USE_RECIPES', required: false, default_value: '1'});
CREATE (e:EnvVar {name: 'AMPLIHACK_MEMORY_ENABLED', required: false, default_value: 'true'});
CREATE (e:EnvVar {name: 'AMPLIHACK_ENABLE_BLARIFY', required: false, default_value: ''});
CREATE (e:EnvVar {name: 'AMPLIHACK_TRACE_LOGGING', required: false, default_value: ''});
CREATE (e:EnvVar {name: 'AMPLIHACK_HOOK_ENGINE', required: false, default_value: 'python'});
CREATE (e:EnvVar {name: 'AMPLIHACK_DEFAULT_MODEL', required: false, default_value: 'opus[1m]'});
CREATE (e:EnvVar {name: 'AMPLIHACK_NONINTERACTIVE', required: false, default_value: ''});
CREATE (e:EnvVar {name: 'ANTHROPIC_API_KEY', required: false, default_value: ''});

// --- Data Stores ---
CREATE (d:DataStore {name: 'kuzu-memory-db', type: 'graph-embedded', version: '>=0.11.0'});
CREATE (d:DataStore {name: 'neo4j-blarify', type: 'graph-external', version: '>=5.25.0'});
CREATE (d:DataStore {name: 'falkordb-blarify', type: 'graph-external', version: '>=1.0.10'});
CREATE (d:DataStore {name: 'runtime-context-fs', type: 'filesystem-json', version: ''});
CREATE (d:DataStore {name: 'trace-log', type: 'filesystem-jsonl', version: ''});
CREATE (d:DataStore {name: 'session-logs', type: 'filesystem-mixed', version: ''});
CREATE (d:DataStore {name: 'discoveries-md', type: 'filesystem-markdown', version: ''});

// --- Packages (top-level internal) ---
CREATE (p:Package {name: 'amplihack', version: '0.6.81', service: 'amplihack-cli'});
CREATE (p:Package {name: 'amplihack.launcher', version: '0.6.81', service: 'claude-launcher'});
CREATE (p:Package {name: 'amplihack.fleet', version: '0.6.81', service: 'fleet-cli'});
CREATE (p:Package {name: 'amplihack.recipe_cli', version: '0.6.81', service: 'recipe-runner'});
CREATE (p:Package {name: 'amplihack.memory', version: '0.6.81', service: 'memory-system'});
CREATE (p:Package {name: 'amplihack.docker', version: '0.6.81', service: 'docker-manager'});
CREATE (p:Package {name: 'amplihack.security', version: '0.6.81', service: 'amplihack-cli'});
CREATE (p:Package {name: 'amplihack.tracing', version: '0.6.81', service: 'trace-logger'});
CREATE (p:Package {name: 'amplihack.vendor.blarify', version: '0.6.81', service: 'blarify'});
CREATE (p:Package {name: 'amplihack.context', version: '0.6.81', service: 'amplihack-cli'});
CREATE (p:Package {name: 'amplihack.bundle_generator', version: '0.6.81', service: 'amplihack-cli'});
CREATE (p:Package {name: 'amplihack.uvx', version: '0.6.81', service: 'amplihack-cli'});
CREATE (p:Package {name: 'amplihack.meta_delegation', version: '0.6.81', service: 'amplihack-cli'});

// --- Packages (external) ---
CREATE (p:Package {name: 'kuzu', version: '>=0.11.0', service: 'memory-system'});
CREATE (p:Package {name: 'rich', version: '>=13.0.0', service: 'amplihack-cli'});
CREATE (p:Package {name: 'aiohttp', version: '>=3.8.0', service: 'amplihack-cli'});
CREATE (p:Package {name: 'docker', version: '>=7.1.0', service: 'docker-manager'});

// --- Journeys ---
CREATE (j:Journey {name: 'install-amplihack', verdict: 'pass'});
CREATE (j:Journey {name: 'launch-claude-session', verdict: 'pass'});
CREATE (j:Journey {name: 'run-recipe', verdict: 'pass'});
CREATE (j:Journey {name: 'auto-mode-execution', verdict: 'pass'});
CREATE (j:Journey {name: 'store-memory', verdict: 'pass'});
