// schema.cypher — Kuzu node and relationship table definitions
// Based on code-atlas/reference.md schema

CREATE NODE TABLE Service(name STRING, language STRING, port INT64, path STRING, PRIMARY KEY(name));
CREATE NODE TABLE Package(name STRING, version STRING, service STRING, PRIMARY KEY(name));
CREATE NODE TABLE Route(method STRING, path STRING, handler STRING, auth STRING, PRIMARY KEY(path));
CREATE NODE TABLE DTO(name STRING, file STRING, line INT64, PRIMARY KEY(name));
CREATE NODE TABLE Symbol(name STRING, file STRING, line INT64, exported BOOLEAN, PRIMARY KEY(name));
CREATE NODE TABLE EnvVar(name STRING, required BOOLEAN, default_value STRING, PRIMARY KEY(name));
CREATE NODE TABLE DataStore(name STRING, type STRING, version STRING, PRIMARY KEY(name));
CREATE NODE TABLE Journey(name STRING, verdict STRING, PRIMARY KEY(name));

CREATE REL TABLE DEPENDS_ON(FROM Package TO Package);
CREATE REL TABLE CALLS(FROM Service TO Service, protocol STRING);
CREATE REL TABLE EXPOSES(FROM Service TO Route);
CREATE REL TABLE USES_DTO(FROM Route TO DTO, direction STRING);
CREATE REL TABLE REFERENCES_SYM(FROM Symbol TO Symbol);
CREATE REL TABLE READS_FROM(FROM Service TO DataStore);
CREATE REL TABLE WRITES_TO(FROM Service TO DataStore);
CREATE REL TABLE USES_ENV(FROM Service TO EnvVar);
CREATE REL TABLE TRAVERSES(FROM Journey TO Route, step_order INT64);
