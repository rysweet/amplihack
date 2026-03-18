// queries.cypher — Example queries for atlas traversal

// 1. Which services does the CLI call?
MATCH (cli:Service {name: 'amplihack-cli'})-[c:CALLS]->(target:Service)
RETURN target.name, c.protocol;

// 2. What environment variables does each service use?
MATCH (s:Service)-[:USES_ENV]->(e:EnvVar)
RETURN s.name, e.name, e.default_value
ORDER BY s.name, e.name;

// 3. What data stores does each service read from or write to?
MATCH (s:Service)-[r:READS_FROM|WRITES_TO]->(d:DataStore)
RETURN s.name, type(r) AS relationship, d.name, d.type;

// 4. Show all CLI commands exposed by the main service
MATCH (s:Service {name: 'amplihack-cli'})-[:EXPOSES]->(r:Route)
WHERE r.method = 'CLI'
RETURN r.path, r.handler
ORDER BY r.path;

// 5. Trace a user journey through all routes
MATCH (j:Journey {name: 'launch-claude-session'})-[t:TRAVERSES]->(r:Route)
RETURN r.method, r.path, r.handler, t.step_order
ORDER BY t.step_order;

// 6. What packages does the proxy depend on?
MATCH (p:Package {name: 'amplihack.proxy'})-[:DEPENDS_ON]->(dep:Package)
RETURN dep.name, dep.version;

// 7. Full dependency chain from CLI to external packages (2-hop)
MATCH (root:Package {name: 'amplihack'})-[:DEPENDS_ON]->(mid:Package)-[:DEPENDS_ON]->(leaf:Package)
RETURN root.name, mid.name, leaf.name, leaf.version;

// 8. Services that use Azure-related environment variables
MATCH (s:Service)-[:USES_ENV]->(e:EnvVar)
WHERE e.name STARTS WITH 'AZURE'
RETURN s.name, e.name;

// 9. HTTP routes exposed by the system
MATCH (s:Service)-[:EXPOSES]->(r:Route)
WHERE r.method = 'HTTP'
RETURN s.name, r.method, r.path, r.auth;

// 10. Which services write to which data stores?
MATCH (s:Service)-[:WRITES_TO]->(d:DataStore)
RETURN s.name AS service, d.name AS store, d.type AS store_type
ORDER BY s.name;
