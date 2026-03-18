// atlas-relationships.cypher — Relationships between atlas nodes

// --- Service CALLS Service ---
MATCH (a:Service {name: 'amplihack-cli'}), (b:Service {name: 'claude-launcher'})
CREATE (a)-[:CALLS {protocol: 'function-call'}]->(b);

MATCH (a:Service {name: 'amplihack-cli'}), (b:Service {name: 'copilot-launcher'})
CREATE (a)-[:CALLS {protocol: 'function-call'}]->(b);

MATCH (a:Service {name: 'amplihack-cli'}), (b:Service {name: 'codex-launcher'})
CREATE (a)-[:CALLS {protocol: 'function-call'}]->(b);

MATCH (a:Service {name: 'amplihack-cli'}), (b:Service {name: 'amplifier-launcher'})
CREATE (a)-[:CALLS {protocol: 'function-call'}]->(b);

MATCH (a:Service {name: 'amplihack-cli'}), (b:Service {name: 'recipe-runner'})
CREATE (a)-[:CALLS {protocol: 'function-call'}]->(b);

MATCH (a:Service {name: 'amplihack-cli'}), (b:Service {name: 'fleet-cli'})
CREATE (a)-[:CALLS {protocol: 'function-call'}]->(b);

MATCH (a:Service {name: 'claude-launcher'}), (b:Service {name: 'proxy-server'})
CREATE (a)-[:CALLS {protocol: 'subprocess'}]->(b);

MATCH (a:Service {name: 'claude-launcher'}), (b:Service {name: 'auto-mode'})
CREATE (a)-[:CALLS {protocol: 'function-call'}]->(b);

MATCH (a:Service {name: 'claude-launcher'}), (b:Service {name: 'memory-system'})
CREATE (a)-[:CALLS {protocol: 'function-call'}]->(b);

MATCH (a:Service {name: 'claude-launcher'}), (b:Service {name: 'blarify'})
CREATE (a)-[:CALLS {protocol: 'function-call'}]->(b);

MATCH (a:Service {name: 'claude-launcher'}), (b:Service {name: 'docker-manager'})
CREATE (a)-[:CALLS {protocol: 'function-call'}]->(b);

MATCH (a:Service {name: 'proxy-server'}), (b:Service {name: 'trace-logger'})
CREATE (a)-[:CALLS {protocol: 'function-call'}]->(b);

// --- Service EXPOSES Route ---
MATCH (s:Service {name: 'amplihack-cli'}), (r:Route {path: 'amplihack launch'})
CREATE (s)-[:EXPOSES]->(r);

MATCH (s:Service {name: 'amplihack-cli'}), (r:Route {path: 'amplihack install'})
CREATE (s)-[:EXPOSES]->(r);

MATCH (s:Service {name: 'amplihack-cli'}), (r:Route {path: 'amplihack uninstall'})
CREATE (s)-[:EXPOSES]->(r);

MATCH (s:Service {name: 'amplihack-cli'}), (r:Route {path: 'amplihack update'})
CREATE (s)-[:EXPOSES]->(r);

MATCH (s:Service {name: 'amplihack-cli'}), (r:Route {path: 'amplihack claude'})
CREATE (s)-[:EXPOSES]->(r);

MATCH (s:Service {name: 'amplihack-cli'}), (r:Route {path: 'amplihack copilot'})
CREATE (s)-[:EXPOSES]->(r);

MATCH (s:Service {name: 'amplihack-cli'}), (r:Route {path: 'amplihack codex'})
CREATE (s)-[:EXPOSES]->(r);

MATCH (s:Service {name: 'amplihack-cli'}), (r:Route {path: 'amplihack amplifier'})
CREATE (s)-[:EXPOSES]->(r);

MATCH (s:Service {name: 'amplihack-cli'}), (r:Route {path: 'amplihack recipe run'})
CREATE (s)-[:EXPOSES]->(r);

MATCH (s:Service {name: 'amplihack-cli'}), (r:Route {path: 'amplihack fleet'})
CREATE (s)-[:EXPOSES]->(r);

MATCH (s:Service {name: 'amplihack-cli'}), (r:Route {path: 'amplihack memory tree'})
CREATE (s)-[:EXPOSES]->(r);

MATCH (s:Service {name: 'amplihack-cli'}), (r:Route {path: 'amplihack plugin install'})
CREATE (s)-[:EXPOSES]->(r);

MATCH (s:Service {name: 'amplihack-cli'}), (r:Route {path: 'amplihack new'})
CREATE (s)-[:EXPOSES]->(r);

MATCH (s:Service {name: 'proxy-server'}), (r:Route {path: '/v1/messages'})
CREATE (s)-[:EXPOSES]->(r);

MATCH (s:Service {name: 'responses-api-proxy'}), (r:Route {path: '/v1/responses'})
CREATE (s)-[:EXPOSES]->(r);

// --- Service READS_FROM / WRITES_TO DataStore ---
MATCH (s:Service {name: 'memory-system'}), (d:DataStore {name: 'kuzu-memory-db'})
CREATE (s)-[:READS_FROM]->(d);

MATCH (s:Service {name: 'memory-system'}), (d:DataStore {name: 'kuzu-memory-db'})
CREATE (s)-[:WRITES_TO]->(d);

MATCH (s:Service {name: 'blarify'}), (d:DataStore {name: 'neo4j-blarify'})
CREATE (s)-[:READS_FROM]->(d);

MATCH (s:Service {name: 'blarify'}), (d:DataStore {name: 'neo4j-blarify'})
CREATE (s)-[:WRITES_TO]->(d);

MATCH (s:Service {name: 'trace-logger'}), (d:DataStore {name: 'trace-log'})
CREATE (s)-[:WRITES_TO]->(d);

MATCH (s:Service {name: 'amplihack-cli'}), (d:DataStore {name: 'runtime-context-fs'})
CREATE (s)-[:WRITES_TO]->(d);

MATCH (s:Service {name: 'claude-launcher'}), (d:DataStore {name: 'session-logs'})
CREATE (s)-[:WRITES_TO]->(d);

MATCH (s:Service {name: 'amplihack-cli'}), (d:DataStore {name: 'discoveries-md'})
CREATE (s)-[:READS_FROM]->(d);

// --- Service USES_ENV EnvVar ---
MATCH (s:Service {name: 'amplihack-cli'}), (e:EnvVar {name: 'AMPLIHACK_HOME'})
CREATE (s)-[:USES_ENV]->(e);

MATCH (s:Service {name: 'amplihack-cli'}), (e:EnvVar {name: 'AMPLIHACK_DEBUG'})
CREATE (s)-[:USES_ENV]->(e);

MATCH (s:Service {name: 'amplihack-cli'}), (e:EnvVar {name: 'AMPLIHACK_NONINTERACTIVE'})
CREATE (s)-[:USES_ENV]->(e);

MATCH (s:Service {name: 'amplihack-cli'}), (e:EnvVar {name: 'AMPLIHACK_AGENT_BINARY'})
CREATE (s)-[:USES_ENV]->(e);

MATCH (s:Service {name: 'amplihack-cli'}), (e:EnvVar {name: 'AMPLIHACK_USE_DOCKER'})
CREATE (s)-[:USES_ENV]->(e);

MATCH (s:Service {name: 'claude-launcher'}), (e:EnvVar {name: 'AMPLIHACK_HOME'})
CREATE (s)-[:USES_ENV]->(e);

MATCH (s:Service {name: 'claude-launcher'}), (e:EnvVar {name: 'AMPLIHACK_DEBUG'})
CREATE (s)-[:USES_ENV]->(e);

MATCH (s:Service {name: 'claude-launcher'}), (e:EnvVar {name: 'AMPLIHACK_DEFAULT_MODEL'})
CREATE (s)-[:USES_ENV]->(e);

MATCH (s:Service {name: 'claude-launcher'}), (e:EnvVar {name: 'AMPLIHACK_ENABLE_BLARIFY'})
CREATE (s)-[:USES_ENV]->(e);

MATCH (s:Service {name: 'proxy-server'}), (e:EnvVar {name: 'ANTHROPIC_API_KEY'})
CREATE (s)-[:USES_ENV]->(e);

MATCH (s:Service {name: 'proxy-server'}), (e:EnvVar {name: 'AZURE_OPENAI_API_KEY'})
CREATE (s)-[:USES_ENV]->(e);

MATCH (s:Service {name: 'proxy-server'}), (e:EnvVar {name: 'AZURE_OPENAI_ENDPOINT'})
CREATE (s)-[:USES_ENV]->(e);

MATCH (s:Service {name: 'proxy-server'}), (e:EnvVar {name: 'PREFERRED_PROVIDER'})
CREATE (s)-[:USES_ENV]->(e);

MATCH (s:Service {name: 'proxy-server'}), (e:EnvVar {name: 'AMPLIHACK_TRACE_LOGGING'})
CREATE (s)-[:USES_ENV]->(e);

MATCH (s:Service {name: 'memory-system'}), (e:EnvVar {name: 'AMPLIHACK_MEMORY_ENABLED'})
CREATE (s)-[:USES_ENV]->(e);

MATCH (s:Service {name: 'recipe-runner'}), (e:EnvVar {name: 'AMPLIHACK_USE_RECIPES'})
CREATE (s)-[:USES_ENV]->(e);

MATCH (s:Service {name: 'auto-mode'}), (e:EnvVar {name: 'AMPLIHACK_AUTO_MODE'})
CREATE (s)-[:USES_ENV]->(e);

MATCH (s:Service {name: 'copilot-launcher'}), (e:EnvVar {name: 'AMPLIHACK_HOOK_ENGINE'})
CREATE (s)-[:USES_ENV]->(e);

// --- Package DEPENDS_ON Package ---
MATCH (a:Package {name: 'amplihack.proxy'}), (b:Package {name: 'flask'})
CREATE (a)-[:DEPENDS_ON]->(b);

MATCH (a:Package {name: 'amplihack.proxy'}), (b:Package {name: 'fastapi'})
CREATE (a)-[:DEPENDS_ON]->(b);

MATCH (a:Package {name: 'amplihack.proxy'}), (b:Package {name: 'litellm'})
CREATE (a)-[:DEPENDS_ON]->(b);

MATCH (a:Package {name: 'amplihack.memory'}), (b:Package {name: 'kuzu'})
CREATE (a)-[:DEPENDS_ON]->(b);

MATCH (a:Package {name: 'amplihack.docker'}), (b:Package {name: 'docker'})
CREATE (a)-[:DEPENDS_ON]->(b);

MATCH (a:Package {name: 'amplihack'}), (b:Package {name: 'rich'})
CREATE (a)-[:DEPENDS_ON]->(b);

MATCH (a:Package {name: 'amplihack'}), (b:Package {name: 'aiohttp'})
CREATE (a)-[:DEPENDS_ON]->(b);

MATCH (a:Package {name: 'amplihack.launcher'}), (b:Package {name: 'amplihack.proxy'})
CREATE (a)-[:DEPENDS_ON]->(b);

MATCH (a:Package {name: 'amplihack.launcher'}), (b:Package {name: 'amplihack.memory'})
CREATE (a)-[:DEPENDS_ON]->(b);

MATCH (a:Package {name: 'amplihack'}), (b:Package {name: 'amplihack.launcher'})
CREATE (a)-[:DEPENDS_ON]->(b);

MATCH (a:Package {name: 'amplihack'}), (b:Package {name: 'amplihack.fleet'})
CREATE (a)-[:DEPENDS_ON]->(b);

MATCH (a:Package {name: 'amplihack'}), (b:Package {name: 'amplihack.recipe_cli'})
CREATE (a)-[:DEPENDS_ON]->(b);

// --- Journey TRAVERSES Route ---
MATCH (j:Journey {name: 'install-amplihack'}), (r:Route {path: 'amplihack install'})
CREATE (j)-[:TRAVERSES {step_order: 1}]->(r);

MATCH (j:Journey {name: 'launch-claude-session'}), (r:Route {path: 'amplihack launch'})
CREATE (j)-[:TRAVERSES {step_order: 1}]->(r);

MATCH (j:Journey {name: 'launch-claude-session'}), (r:Route {path: '/v1/messages'})
CREATE (j)-[:TRAVERSES {step_order: 2}]->(r);

MATCH (j:Journey {name: 'run-recipe'}), (r:Route {path: 'amplihack recipe run'})
CREATE (j)-[:TRAVERSES {step_order: 1}]->(r);

MATCH (j:Journey {name: 'auto-mode-execution'}), (r:Route {path: 'amplihack launch'})
CREATE (j)-[:TRAVERSES {step_order: 1}]->(r);

MATCH (j:Journey {name: 'auto-mode-execution'}), (r:Route {path: '/v1/messages'})
CREATE (j)-[:TRAVERSES {step_order: 2}]->(r);

MATCH (j:Journey {name: 'store-memory'}), (r:Route {path: 'amplihack memory tree'})
CREATE (j)-[:TRAVERSES {step_order: 1}]->(r);
