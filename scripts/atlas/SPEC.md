# Code Atlas: Deterministic Extraction System

## Problem

The current atlas system delegates data extraction to LLM agents, which
cherry-pick examples and produce inconsistent, incomplete results across runs.
An LLM analyzing 601 Python files will summarize a handful and miss the rest.

## Design Principle

**Extraction is deterministic. Presentation is the only LLM role.**

Every layer follows the same contract:

1. A Python script extracts ALL raw data using AST, file system, and regex.
   No heuristics, no sampling, no LLM.
2. Raw data is written to `atlas_output/<layer>.json` with a fixed schema.
3. A completeness check validates exhaustiveness against the file manifest.
4. An optional LLM pass can ONLY do layout/prose for the final markdown --
   it receives the complete JSON and formats it. It never discovers data.

## Architecture

```
scripts/atlas/
    __init__.py
    common.py               # Shared: file discovery, AST helpers, JSON schema
    layer1_repo_surface.py
    layer2_ast_bindings.py
    layer3_compile_deps.py
    layer4_runtime_topology.py
    layer5_api_contracts.py
    layer6_data_flow.py
    layer7_service_components.py
    layer8_user_journeys.py
    cross_layer_checks.py    # Inter-layer completeness validation
    run_all.py               # Orchestrator: run all layers + checks
    render.py                # Optional: JSON -> Markdown (LLM or template)

atlas_output/               # Generated, gitignored
    manifest.json           # Master file list (Layer 0)
    layer1_repo_surface.json
    layer2_ast_bindings.json
    ...
    cross_layer_report.json
```

---

## Layer 0: Manifest (Foundation for All Layers)

Every other layer references this canonical file list. If a file is not in the
manifest, it does not exist for atlas purposes.

### Extraction Script: `common.py::build_manifest()`

```
Input:  root_dir (src/amplihack/)
Method:
  1. os.walk(root_dir), skip __pycache__, .git, node_modules
  2. Respect .gitignore via `git ls-files --cached --others --exclude-standard`
     (this is the ONLY correct way -- os.walk + manual .gitignore parsing
      is fragile and wrong)
  3. Classify each file by extension: .py, .yaml, .yml, .md, .json, .toml, etc.
  4. For .py files, record: path, size_bytes, line_count, is_test (contains
     "test" in path or starts with "test_"), is_init (__init__.py),
     package (parent directory relative to root)

Output: manifest.json
```

### Schema: manifest.json

```json
{
  "generated_at": "ISO8601",
  "root": "src/amplihack",
  "git_commit": "abc123",
  "total_files": 601,
  "files": [
    {
      "path": "src/amplihack/cli.py",
      "rel_path": "cli.py",
      "extension": ".py",
      "size_bytes": 28431,
      "line_count": 892,
      "is_test": false,
      "is_init": false,
      "package": "amplihack",
      "classification": "source"
    }
  ],
  "summary": {
    "by_extension": {".py": 601, ".yaml": 12, ...},
    "by_classification": {"source": 480, "test": 85, "init": 36, ...},
    "packages": ["amplihack", "amplihack.cli", "amplihack.fleet", ...]
  }
}
```

### Completeness Check

- `len(files)` must equal `git ls-files | grep '.py$' | wc -l` for .py files
- Every file reachable from os.walk (minus excluded dirs) appears exactly once

---

## Layer 1: repo-surface

**Purpose**: Exhaustive directory tree with file counts, roles, and structure.

### Extraction: `layer1_repo_surface.py`

```
Input:  manifest.json
Method:
  1. Group files by package (directory)
  2. For each directory, count: total files, .py files, test files, init files
  3. Classify directory role:
     - "package": has __init__.py
     - "tests": name is "tests" or "test"
     - "vendor": under vendor/
     - "config": contains .toml, .cfg, .ini
     - "docs": contains .md, .rst
  4. Compute directory depth, parent relationships
  5. Identify top-level entry points: pyproject.toml [project.scripts],
     __main__.py, cli.py

Output: layer1_repo_surface.json
```

### Schema

```json
{
  "layer": "repo-surface",
  "directories": [
    {
      "path": "src/amplihack/fleet",
      "depth": 2,
      "role": "package",
      "parent": "src/amplihack",
      "file_counts": {
        "total": 42,
        "python": 38,
        "test": 12,
        "init": 1
      }
    }
  ],
  "entry_points": [
    { "type": "console_script", "name": "amplihack", "target": "amplihack.cli:main" },
    { "type": "__main__", "path": "src/amplihack/__main__.py" }
  ],
  "non_python_assets": [
    { "path": "src/amplihack/amplifier-bundle/recipes/foo.yaml", "type": "yaml" }
  ]
}
```

### Completeness Check

- Every directory from manifest appears in `directories`
- Sum of all `file_counts.total` equals `manifest.total_files`
- Every file from manifest is accounted for under its parent directory

### LLM Role

NONE for extraction. LLM may write a 2-paragraph summary describing the
high-level structure for the rendered atlas page.

---

## Layer 2: ast-lsp-bindings

**Purpose**: All symbol definitions, exports, imports, cross-file references,
and dead code detection.

### Extraction: `layer2_ast_bindings.py`

```
Input:  All .py files from manifest
Method:
  For each .py file, parse with ast.parse() and extract:

  1. DEFINITIONS (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
     ast.Assign where target is module-level):
     - name, type (function/class/constant), lineno, is_private (starts with _)
     - For classes: method names, base classes
     - For functions: argument names, return annotation if present

  2. EXPORTS (__all__):
     - Parse __all__ = [...] assignments
     - Record each exported name
     - Cross-check: every name in __all__ must exist as a definition in the
       same file or be imported

  3. IMPORTS (ast.Import, ast.ImportFrom):
     - module, names imported, alias, lineno
     - Classify: stdlib, third_party, internal (starts with . or amplihack)
     - For internal imports, resolve to target file path

  4. CROSS-REFERENCES:
     - For every definition, search all other files' imports for references
     - A definition is "referenced" if any other file imports it (by name or
       via wildcard from a module that exports it)

  5. DEAD CODE DETECTION:
     - A module-level definition that is:
       (a) NOT in __all__ of its module AND
       (b) NOT imported by any other file AND
       (c) NOT a dunder method AND
       (d) NOT called within its own file (intra-file usage)
     - This is CONSERVATIVE -- it may miss dynamic usage (getattr, etc.)
       Mark these as "potentially_dead" not "dead"

Output: layer2_ast_bindings.json
```

### Schema

```json
{
  "layer": "ast-lsp-bindings",
  "files_analyzed": 601,
  "files_failed_parse": [],
  "definitions": [
    {
      "file": "src/amplihack/cli.py",
      "name": "main",
      "type": "function",
      "lineno": 450,
      "is_private": false,
      "is_exported": true,
      "references": [{ "file": "src/amplihack/__main__.py", "lineno": 3 }],
      "reference_count": 1
    }
  ],
  "exports": [
    {
      "file": "src/amplihack/proxy/__init__.py",
      "all_names": ["ProxyConfig", "ProxyManager"],
      "valid": true,
      "missing_definitions": []
    }
  ],
  "imports": [
    {
      "file": "src/amplihack/cli.py",
      "module": "amplihack.proxy",
      "names": ["ProxyConfig", "ProxyManager"],
      "category": "internal",
      "resolved_target": "src/amplihack/proxy/__init__.py",
      "lineno": 23
    }
  ],
  "potentially_dead": [
    {
      "file": "src/amplihack/utils/foo.py",
      "name": "unused_helper",
      "type": "function",
      "lineno": 42,
      "reason": "no_imports_no_exports_no_intra_file_calls"
    }
  ],
  "summary": {
    "total_definitions": 3200,
    "total_exports": 172,
    "total_imports": 4500,
    "potentially_dead_count": 45,
    "files_with_all": 172,
    "files_without_all": 429
  }
}
```

### Completeness Check

- `files_analyzed` == count of .py files in manifest
- `files_failed_parse` must be empty (or explicitly explained -- syntax errors)
- Every `__all__` file from grep (172 known) must appear in `exports`
- Every exported name has a corresponding entry in `definitions`

### LLM Role

NONE for extraction. LLM may annotate the dead code list with likely reasons
(e.g., "used via dynamic dispatch") but the raw list is deterministic.

---

## Layer 3: compile-deps

**Purpose**: External dependencies, internal import graph, circular dependency
detection.

### Extraction: `layer3_compile_deps.py`

```
Input:  pyproject.toml, all .py files from manifest, layer2 imports
Method:

  1. EXTERNAL DEPENDENCIES:
     - Parse pyproject.toml with tomllib (stdlib 3.11+)
     - Extract: [project.dependencies], [project.optional-dependencies.*]
     - For each: package name, version constraint, group (core/optional/dev/test)
     - Normalize names (underscores, hyphens are equivalent per PEP 503)

  2. INTERNAL IMPORT GRAPH:
     - Reuse layer2 imports where category == "internal"
     - Build directed graph: file A -> file B if A imports from B
     - Aggregate to package level: package A -> package B

  3. CIRCULAR DEPENDENCY DETECTION:
     - Run Tarjan's algorithm (or itertools-based SCC detection) on the
       package-level import graph
     - Report all strongly connected components of size > 1
     - For each cycle, list the specific import chain

  4. EXTERNAL DEPENDENCY USAGE:
     - For each external dependency in pyproject.toml, search layer2 imports
       for any file that imports it
     - Flag unused dependencies (declared but never imported)
     - Flag undeclared dependencies (imported but not in pyproject.toml)
       Exclude stdlib modules using sys.stdlib_module_names (3.10+)

Output: layer3_compile_deps.json
```

### Schema

```json
{
  "layer": "compile-deps",
  "external_dependencies": [
    {
      "name": "flask",
      "normalized_name": "flask",
      "version_constraint": ">=2.0.0",
      "group": "core",
      "imported_by": ["src/amplihack/proxy/server.py"],
      "import_count": 3
    }
  ],
  "internal_import_graph": {
    "nodes": ["amplihack.cli", "amplihack.proxy", "amplihack.launcher", ...],
    "edges": [
      {"from": "amplihack.cli", "to": "amplihack.proxy", "import_count": 2}
    ]
  },
  "circular_dependencies": [
    {
      "cycle": ["amplihack.foo", "amplihack.bar", "amplihack.foo"],
      "files_involved": [
        {"file": "src/amplihack/foo.py", "imports": "amplihack.bar", "lineno": 5},
        {"file": "src/amplihack/bar.py", "imports": "amplihack.foo", "lineno": 3}
      ]
    }
  ],
  "unused_dependencies": ["some-unused-package"],
  "undeclared_dependencies": [],
  "summary": {
    "external_dep_count": 52,
    "internal_packages": 35,
    "internal_edges": 280,
    "circular_dependency_count": 2,
    "unused_dep_count": 1
  }
}
```

### Completeness Check

- Every dependency line from pyproject.toml appears in `external_dependencies`
- Every internal import edge from layer2 appears in `internal_import_graph`
- All .py files from manifest are represented as part of some package node

### LLM Role

NONE. LLM may generate a prose summary of dependency health and recommend
removals.

---

## Layer 4: runtime-topology

**Purpose**: All subprocess calls, socket/port bindings, Docker configs, and
external process interactions.

### Extraction: `layer4_runtime_topology.py`

```
Input:  All .py files from manifest, all docker-compose*.yml, all Dockerfile*
Method:

  1. SUBPROCESS CALLS (AST):
     - Walk AST for Call nodes where func resolves to:
       subprocess.run, subprocess.Popen, subprocess.call,
       subprocess.check_output, subprocess.check_call,
       os.system, os.popen, os.exec*
     - Extract: file, lineno, command (if literal string/list), context
       (enclosing function name)

  2. SOCKET/PORT BINDINGS (AST + grep):
     - AST: socket.bind(), socket.connect(), socket.listen()
     - Grep patterns: "port=", "host=", "bind", ":8080" (numeric port literals)
     - uvicorn.run, flask app.run, gunicorn references
     - Extract: file, lineno, port (if determinable), protocol

  3. DOCKER CONFIGS (file parsing):
     - Find all Dockerfile*, docker-compose*.yml, .dockerignore
     - Parse docker-compose YAML: services, ports, volumes, networks, depends_on
     - Parse Dockerfile: FROM, EXPOSE, CMD, ENTRYPOINT

  4. ENVIRONMENT VARIABLE READS (AST):
     - os.environ.get(), os.environ[], os.getenv()
     - Extract: variable name, default value, file, lineno

Output: layer4_runtime_topology.json
```

### Schema

```json
{
  "layer": "runtime-topology",
  "subprocess_calls": [
    {
      "file": "src/amplihack/launcher/core.py",
      "lineno": 142,
      "function_context": "launch_claude",
      "call_type": "subprocess.run",
      "command_literal": ["claude", "--resume"],
      "command_is_dynamic": false
    }
  ],
  "port_bindings": [
    {
      "file": "src/amplihack/proxy/server.py",
      "lineno": 88,
      "port": 8080,
      "protocol": "http",
      "framework": "flask"
    }
  ],
  "docker_configs": [
    {
      "file": "docker-compose.yml",
      "services": [{ "name": "proxy", "image": "...", "ports": ["8080:8080"] }]
    }
  ],
  "env_var_reads": [
    {
      "file": "src/amplihack/cli.py",
      "lineno": 53,
      "variable": "AMPLIHACK_DEBUG",
      "default": "",
      "function_context": "_debug_print"
    }
  ],
  "summary": {
    "subprocess_call_count": 357,
    "unique_subprocess_files": 96,
    "port_binding_count": 5,
    "docker_service_count": 3,
    "env_var_count": 45
  }
}
```

### Completeness Check

- `unique_subprocess_files` count must match grep count (96 files known)
- Every Dockerfile/docker-compose found by glob appears in `docker_configs`
- Every `os.environ`/`os.getenv` call found by AST is captured

### LLM Role

NONE. LLM may produce a network topology diagram description from the data.

---

## Layer 5: api-contracts

**Purpose**: All CLI subcommands, HTTP routes, hook events, recipe definitions.

### Extraction: `layer5_api_contracts.py`

```
Input:  CLI files (cli.py, plugin_cli/, recipe_cli/, fleet/fleet_cli.py),
        proxy files (proxy/), hook files (hooks/),
        recipe YAML files, skill/agent markdown files
Method:

  1. CLI SUBCOMMANDS:
     - Parse cli.py and all files containing add_parser/add_subparsers (5 files)
     - For each add_parser() call, extract:
       command name, help text, parent parser (for nesting)
     - For each add_argument() call on that parser:
       argument name, type, required, default, help
     - Build command tree: amplihack -> {version, install, launch, ...}
       amplihack plugin -> {install, uninstall, link, verify}
       amplihack memory -> {tree, export, import, clean}
       etc.

  2. HTTP ROUTES:
     - Parse proxy/ files for @app.route, @app.get, @router.get, etc.
     - Extract: method, path, function name, file, lineno
     - Parse FastAPI/Flask decorator arguments

  3. HOOK EVENTS:
     - Scan hooks/ directory for all hook definitions
     - Scan .claude/tools/ for hook files (stop.py, etc.)
     - Classify by event type: pre-commit, post-commit, pre-push, stop, etc.
     - Extract: hook name, trigger event, handler function, file

  4. RECIPE DEFINITIONS:
     - Glob for all .yaml/.yml files under recipes/, amplifier-bundle/recipes/
     - Parse each: name, description, steps, agents used, conditions
     - Extract recipe metadata without executing

  5. SKILL DEFINITIONS:
     - Glob for all .md files under known skill directories
     - Extract frontmatter (YAML between ---): name, description, triggers
     - Count: total skills, by category

  6. AGENT DEFINITIONS:
     - Glob for all .md files under agents/amplihack/
     - Extract frontmatter: name, role, capabilities

Output: layer5_api_contracts.json
```

### Schema

```json
{
  "layer": "api-contracts",
  "cli_commands": [
    {
      "command": "amplihack launch",
      "parser_name": "launch",
      "help": "Launch Claude Code with amplihack agents",
      "parent": "amplihack",
      "arguments": [
        {
          "name": "--memory",
          "type": "str",
          "required": false,
          "default": null,
          "help": "Memory backend to use"
        }
      ],
      "file": "src/amplihack/cli.py",
      "lineno": 566
    }
  ],
  "http_routes": [
    {
      "method": "POST",
      "path": "/v1/chat/completions",
      "function": "chat_completions",
      "file": "src/amplihack/proxy/integrated_proxy.py",
      "lineno": 45
    }
  ],
  "hook_events": [
    {
      "name": "stop",
      "type": "lifecycle",
      "handler": "stop",
      "file": ".claude/tools/amplihack/hooks/stop.py"
    }
  ],
  "recipes": [
    {
      "file": "recipes/dev-orchestrator.yaml",
      "name": "dev-orchestrator",
      "description": "...",
      "step_count": 5,
      "agents_used": ["architect", "builder"]
    }
  ],
  "skills": [
    {
      "file": "skills/mermaid-diagram-generator.md",
      "name": "mermaid-diagram-generator",
      "description": "...",
      "triggers": ["diagram", "mermaid"]
    }
  ],
  "agents": [
    {
      "file": "agents/amplihack/core/architect.md",
      "name": "architect",
      "role": "System design"
    }
  ],
  "summary": {
    "cli_command_count": 35,
    "http_route_count": 19,
    "hook_event_count": 7,
    "recipe_count": 25,
    "skill_count": 120,
    "agent_count": 30
  }
}
```

### Completeness Check

- Every `add_parser()` call found by grep (62 occurrences across 5 files)
  produces a `cli_commands` entry
- Every `@app.route`/`@router.*` (19 occurrences across 3 files) produces an
  `http_routes` entry
- Every .yaml file in recipe directories produces a `recipes` entry
- Every .md file in skill/agent directories produces an entry

### LLM Role

NONE for extraction. LLM may write API documentation from the structured data.

---

## Layer 6: data-flow

**Purpose**: All file I/O, database operations, and data transformation paths.

### Extraction: `layer6_data_flow.py`

```
Input:  All .py files from manifest
Method:

  1. FILE I/O OPERATIONS (AST):
     - open() calls: extract mode (r/w/a), file path if literal
     - Path.write_text(), Path.write_bytes(), Path.read_text(), Path.read_bytes()
     - json.dump(), json.dumps(), json.load(), json.loads()
     - yaml.safe_load(), yaml.dump()
     - shutil.copy*, shutil.move
     - csv.reader, csv.writer
     - Extract: file, lineno, operation (read/write), format (json/yaml/text/
       binary), target_path (if determinable), function_context

  2. DATABASE OPERATIONS (AST + grep):
     - Kuzu: conn.execute(), conn.query(), any kuzu.* calls
     - SQLite: sqlite3.connect(), cursor.execute()
     - Neo4j: driver.session(), session.run()
     - FalkorDB: any falkordb.* calls
     - Extract: file, lineno, db_type, operation (read/write/schema),
       query (if literal string), function_context

  3. NETWORK I/O (AST):
     - requests.get/post/put/delete/patch
     - aiohttp.ClientSession
     - urllib calls
     - Extract: file, lineno, method, url (if determinable), function_context

  4. DATA TRANSFORMATION PATHS:
     - For each function that does both read AND write operations,
       record it as a transformation point
     - This is a simplified call-graph trace: function reads X, writes Y

Output: layer6_data_flow.json
```

### Schema

```json
{
  "layer": "data-flow",
  "file_io": [
    {
      "file": "src/amplihack/memory/discoveries.py",
      "lineno": 45,
      "operation": "write",
      "format": "json",
      "target_path": "discoveries.json",
      "function_context": "store_discovery",
      "call": "json.dump"
    }
  ],
  "database_ops": [
    {
      "file": "src/amplihack/memory/kuzu/connector.py",
      "lineno": 88,
      "db_type": "kuzu",
      "operation": "write",
      "query_literal": "CREATE NODE TABLE ...",
      "function_context": "init_schema"
    }
  ],
  "network_io": [
    {
      "file": "src/amplihack/proxy/passthrough.py",
      "lineno": 22,
      "method": "POST",
      "url_pattern": "dynamic",
      "function_context": "forward_request"
    }
  ],
  "transformation_points": [
    {
      "file": "src/amplihack/memory/storage_pipeline.py",
      "function": "process_and_store",
      "reads": ["json file"],
      "writes": ["kuzu database"],
      "lineno": 30
    }
  ],
  "summary": {
    "file_io_count": 850,
    "database_op_count": 120,
    "network_io_count": 45,
    "transformation_point_count": 30,
    "files_with_io": 200
  }
}
```

### Completeness Check

- Every file that grep finds with `open(` / `.write_text` / `json.dump` etc.
  appears in `file_io`
- Every kuzu/sqlite/neo4j file (20 known kuzu files) appears in `database_ops`
- `files_with_io` count matches unique files across all I/O categories

### LLM Role

NONE. LLM may draw data flow diagrams from the structured data.

---

## Layer 7: service-components

**Purpose**: Internal package boundaries, coupling metrics, and architectural
structure.

### Extraction: `layer7_service_components.py`

```
Input:  manifest.json, layer2_ast_bindings.json, layer3_compile_deps.json
Method:

  1. PACKAGE METRICS:
     - For each package (directory with __init__.py):
       file_count, class_count, function_count, line_count
     - Public API size: count of names in __all__ (from layer2)
     - Internal complexity: total definitions minus exports

  2. CROSS-PACKAGE COUPLING:
     - From layer3 internal_import_graph, compute for each package:
       afferent_coupling (Ca): number of packages that import this one
       efferent_coupling (Ce): number of packages this one imports
       instability: Ce / (Ca + Ce)   [0 = stable, 1 = unstable]
     - List all cross-package import edges with counts

  3. PACKAGE COHESION:
     - For each package, count intra-package imports vs inter-package imports
     - High intra / low inter = cohesive (good)
     - Low intra / high inter = scattered (bad)

  4. PACKAGE CLASSIFICATION:
     - core: imported by > 50% of other packages
     - leaf: imports others but not imported (Ce > 0, Ca == 0)
     - utility: small, imported by many, few own imports
     - feature: medium coupling, distinct responsibility

Output: layer7_service_components.json
```

### Schema

```json
{
  "layer": "service-components",
  "packages": [
    {
      "name": "amplihack.fleet",
      "path": "src/amplihack/fleet",
      "file_count": 42,
      "class_count": 15,
      "function_count": 180,
      "line_count": 5200,
      "public_api_size": 25,
      "afferent_coupling": 3,
      "efferent_coupling": 8,
      "instability": 0.73,
      "classification": "feature",
      "imports_from": ["amplihack.utils", "amplihack.memory", ...],
      "imported_by": ["amplihack.cli", "amplihack.launcher", ...]
    }
  ],
  "coupling_matrix": {
    "amplihack.cli": {"amplihack.proxy": 2, "amplihack.launcher": 3, ...}
  },
  "summary": {
    "total_packages": 35,
    "core_packages": 3,
    "leaf_packages": 8,
    "avg_instability": 0.55,
    "most_coupled_pair": ["amplihack.cli", "amplihack.fleet"]
  }
}
```

### Completeness Check

- Every package from manifest `summary.packages` appears in `packages`
- Sum of all `file_count` values equals manifest Python file count
- Every edge in layer3 `internal_import_graph` appears in `coupling_matrix`

### LLM Role

NONE. LLM may write an architecture narrative from the metrics.

---

## Layer 8: user-journeys

**Purpose**: All user-facing entry points traced through the call graph to
outcomes.

### Extraction: `layer8_user_journeys.py`

```
Input:  layer5_api_contracts.json (entry points),
        layer2_ast_bindings.json (imports/definitions),
        all .py files (for intra-file call graph)
Method:

  1. BUILD CALL GRAPH:
     - For each function definition (from layer2), walk its AST body
     - Record all Name and Attribute nodes that resolve to other functions
     - Resolve: if function calls `self.foo()`, look up foo in same class
     - Resolve: if function calls `bar()`, look up bar in imports or same file
     - This produces a directed graph: function -> [called functions]
     - IMPORTANT: This is STATIC analysis only. Dynamic dispatch (getattr,
       **kwargs function calls, registry patterns) will be missed. Document
       this limitation explicitly.

  2. TRACE ENTRY POINTS:
     - For each CLI command (from layer5), find its handler function
     - Walk the call graph from handler to depth N (default 5)
     - Record the path: command -> handler -> called_func -> ... -> leaf
     - Stop at: external library calls, I/O operations (from layer6),
       or depth limit

  3. TRACE HTTP ROUTES:
     - Same as CLI, starting from each route handler

  4. CLASSIFY OUTCOMES:
     - Each leaf in a trace is classified:
       "file_io", "database", "subprocess", "network", "return_value", "error"
     - Use layer4 and layer6 data to classify

  5. JOURNEY ASSEMBLY:
     - Group traces by entry point type (CLI, HTTP, hook)
     - For each entry point: list all reachable outcomes

Output: layer8_user_journeys.json
```

### Schema

```json
{
  "layer": "user-journeys",
  "call_graph": {
    "node_count": 3200,
    "edge_count": 8500,
    "max_depth_reached": 5
  },
  "journeys": [
    {
      "entry_type": "cli",
      "command": "amplihack launch",
      "handler": {
        "file": "src/amplihack/cli.py",
        "function": "main",
        "lineno": 450
      },
      "trace_depth": 5,
      "functions_reached": 45,
      "outcomes": [
        {
          "type": "subprocess",
          "detail": "claude --resume",
          "file": "src/amplihack/launcher/core.py"
        },
        {
          "type": "file_io",
          "detail": "write session log",
          "file": "src/amplihack/launcher/session_tracker.py"
        }
      ],
      "packages_touched": ["amplihack.cli", "amplihack.launcher", "amplihack.utils"]
    }
  ],
  "unreachable_functions": [
    {
      "file": "src/amplihack/utils/foo.py",
      "function": "orphan_func",
      "reason": "not reachable from any entry point within depth limit"
    }
  ],
  "summary": {
    "total_journeys": 55,
    "cli_journeys": 35,
    "http_journeys": 19,
    "hook_journeys": 1,
    "avg_trace_depth": 3.2,
    "total_functions_reached": 2800,
    "unreachable_function_count": 400
  }
}
```

### Completeness Check

- Every CLI command from layer5 has a corresponding journey
- Every HTTP route from layer5 has a corresponding journey
- `total_journeys` >= layer5 `cli_command_count` + `http_route_count`

### LLM Role

NONE for extraction. LLM may write user-facing journey narratives.

---

## Cross-Layer Completeness Checks

### Script: `cross_layer_checks.py`

This is the integrity validator. It runs after all layers and produces a
pass/fail report.

```
Checks:

1. FILE COVERAGE:
   - Every .py file in manifest appears in at least:
     layer1 (repo-surface), layer2 (ast-bindings), layer7 (service-components)
   - Any file missing from ALL three is a BUG in extraction

2. CLI COMMAND COVERAGE:
   - Every CLI command in layer5.cli_commands has a journey in layer8.journeys
   - Missing = incomplete journey tracing

3. EXPORT CONSISTENCY:
   - Every name in layer2.exports exists in layer2.definitions
   - Every exported name is imported by at least one file (or flagged as
     "exported but unreferenced")

4. DEPENDENCY CONSISTENCY:
   - Every external dep in layer3.external_dependencies is also importable
     from some file in layer2.imports (or flagged unused)
   - Every internal import in layer2 has a corresponding edge in
     layer3.internal_import_graph

5. I/O TRACEABILITY:
   - Every file_io entry in layer6 is reachable from some entry point in layer8
     (or flagged as "I/O in unreachable code")

6. SUBPROCESS TRACEABILITY:
   - Every subprocess call in layer4 exists in the call graph of layer8
     (within depth limit) or is flagged

7. PACKAGE CONSISTENCY:
   - Packages in layer1 == packages in layer3 == packages in layer7
   - Any discrepancy is a BUG

8. ROUTE COVERAGE:
   - Every HTTP route in layer5 has a journey in layer8
```

### Output: `cross_layer_report.json`

```json
{
  "generated_at": "ISO8601",
  "checks": [
    {
      "name": "file_coverage",
      "status": "PASS",
      "details": "601/601 .py files appear in layers 1, 2, 7"
    },
    {
      "name": "cli_command_coverage",
      "status": "WARN",
      "details": "33/35 CLI commands have journeys. Missing: _local_install, uvx-help",
      "missing": ["_local_install", "uvx-help"]
    }
  ],
  "overall": "PASS_WITH_WARNINGS",
  "warning_count": 2,
  "failure_count": 0
}
```

---

## Orchestrator: `run_all.py`

```
Usage: python -m scripts.atlas.run_all [--root src/amplihack] [--output atlas_output/]

Execution order (sequential, each depends on previous):

  Phase 1 (independent):
    - manifest (Layer 0)

  Phase 2 (depends on manifest):
    - layer1_repo_surface
    - layer2_ast_bindings    (parallelizable with layer1)
    - layer4_runtime_topology (parallelizable)

  Phase 3 (depends on layer2):
    - layer3_compile_deps
    - layer6_data_flow

  Phase 4 (depends on layers 2, 3):
    - layer7_service_components

  Phase 5 (depends on layers 2, 4, 5, 6):
    - layer5_api_contracts
    - layer8_user_journeys

  Phase 6:
    - cross_layer_checks

Each layer script:
  1. Loads its inputs (manifest + any prior layer JSONs)
  2. Runs extraction
  3. Writes output JSON
  4. Runs its own completeness self-check
  5. Prints summary to stdout
  6. Returns exit code 0 (success) or 1 (completeness failure)

run_all.py aborts on any exit code 1 with a clear error message.
Total runtime target: < 60 seconds for 601 files.
```

---

## Common Module: `common.py`

Shared utilities used by all layers:

```python
# File discovery
def build_manifest(root: Path) -> dict:
    """Build canonical file manifest using git ls-files."""

def load_manifest(output_dir: Path) -> dict:
    """Load manifest.json from output directory."""

# AST helpers
def parse_file_safe(path: Path) -> ast.Module | None:
    """Parse Python file, return None on SyntaxError (log warning)."""

def walk_calls(tree: ast.Module) -> list[dict]:
    """Extract all function/method calls from AST."""

def walk_definitions(tree: ast.Module) -> list[dict]:
    """Extract all top-level and class-level definitions."""

def walk_imports(tree: ast.Module) -> list[dict]:
    """Extract all import statements."""

def resolve_internal_import(module: str, root: Path) -> Path | None:
    """Resolve 'amplihack.foo.bar' to src/amplihack/foo/bar.py."""

# JSON I/O
def write_layer_json(layer_name: str, data: dict, output_dir: Path) -> Path:
    """Write layer JSON with schema validation."""

def load_layer_json(layer_name: str, output_dir: Path) -> dict:
    """Load a previously generated layer JSON."""

# Completeness helpers
def check_file_coverage(manifest: dict, layer_data: dict, key: str) -> list[str]:
    """Return list of manifest files missing from layer_data[key]."""
```

---

## Implementation Priorities

Build in this order for maximum early validation:

1. `common.py` + manifest generation -- foundation everything depends on
2. `layer2_ast_bindings.py` -- most complex, highest value (provides definitions
   and imports for layers 3, 7, 8)
3. `layer1_repo_surface.py` -- simple, provides quick sanity check
4. `layer3_compile_deps.py` -- reuses layer2, adds cycle detection
5. `layer5_api_contracts.py` -- concrete user-facing contracts
6. `layer4_runtime_topology.py` -- straightforward AST grep
7. `layer6_data_flow.py` -- straightforward AST grep
8. `layer7_service_components.py` -- pure computation from layers 2+3
9. `layer8_user_journeys.py` -- most complex, depends on everything
10. `cross_layer_checks.py` -- validation, build last
11. `run_all.py` -- orchestrator shell

---

## Key Design Decisions

**Why AST over regex for Python analysis?**
Regex finds string patterns. AST finds semantic structures. `import foo` as a
string could appear in a comment or docstring. `ast.Import` is unambiguous.
We use regex ONLY for non-Python files (YAML, Markdown, TOML) and as a
secondary validation check ("grep count should match AST count").

**Why static analysis over runtime tracing?**
Runtime tracing requires executing code, which may have side effects, need
credentials, or hang on network calls. Static analysis is safe, fast, and
deterministic. The trade-off is missing dynamic dispatch -- we document this
limitation explicitly rather than pretending it does not exist.

**Why depth-limited call graphs?**
Unbounded call graph traversal on 3200 functions with ~8500 edges will produce
traces thousands of nodes deep through recursive/cyclical paths. Depth 5 captures
the meaningful architectural flow without drowning in implementation details.
Configurable via CLI flag.

**Why separate JSON files per layer?**
Each layer can be regenerated independently. Layers can be diffed across git
commits. Individual layers can be inspected without loading the entire atlas.
The cross-layer check validates consistency.

**Why no LLM in extraction?**
An LLM analyzing 601 files will read a sample and hallucinate the rest. AST
parsing reads ALL 601 files in under 10 seconds. There is no contest.
The LLM adds value ONLY in presentation: writing prose summaries, suggesting
architectural improvements, generating diagram descriptions. It receives
complete, verified JSON and formats it. It never discovers data.
