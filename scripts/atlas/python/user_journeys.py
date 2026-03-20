"""Layer 8: User Journeys -- entry points traced through static call graph.

Builds a function-level call graph from layer2 definitions and calls, traces
every entry point through depth-limited traversal, classifies leaf outcomes,
and identifies unreachable functions.

Inputs: layer2_ast_bindings.json (required)
Optional: layer5_api_contracts.json (entry points), layer4, layer6 (outcome classification)
Falls back to extracting entry points directly from codebase if layer5 unavailable.

Limitations (static analysis):
- Dynamic dispatch (getattr, __getattr__) is not traced
- Registry patterns (decorator-based registration) may miss indirect calls
- String-based function references (e.g., importlib.import_module) not followed
- Callbacks passed as arguments are not traced through higher-order functions
"""

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
from scripts.atlas.common import (
    load_layer_json,
    load_manifest,
    parse_file_safe,
    write_layer_json,
)


def extract(manifest: dict, layer2: dict, root: Path,
            layer4: dict | None = None,
            layer5: dict | None = None,
            layer6: dict | None = None) -> dict:
    """Extract layer 8 user journey data.

    Args:
        manifest: Loaded manifest dict.
        layer2: Loaded layer2 ast-bindings dict.
        root: Project root directory.
        layer4: Optional layer4 runtime-topology dict.
        layer5: Optional layer5 api-contracts dict.
        layer6: Optional layer6 data-flow dict.

    Returns:
        Layer 8 data dict.
    """
    root = root.resolve()
    root_str = str(root)

    # --- Step 1: Build call graph ---
    call_graph, all_functions = _build_call_graph(manifest, layer2, root)

    # --- Step 1b: Enrich call graph with blarify CALLS relationships ---
    # When blarify provides CALLS relationships from LSP, add non-Python call
    # edges to the graph. This allows tracing across language boundaries.
    blarify_rels = layer2.get("blarify_relationships", {})
    blarify_edges_added = 0
    if blarify_rels.get("calls", 0) > 0:
        blarify_edges_added = _enrich_call_graph_from_blarify(
            call_graph, all_functions, root
        )

    # --- Step 2: Get entry points ---
    entry_points = _get_entry_points(layer5, root)

    # --- Step 3: Build outcome classifiers from layer4/layer6 ---
    io_functions = _build_io_function_set(layer4, layer6)
    subprocess_functions = _build_subprocess_function_set(layer4)

    # --- Step 4: Trace each entry point ---
    journeys = []
    all_reached: set[str] = set()

    for ep in entry_points:
        handler_key = ep.get("handler_key")
        if not handler_key:
            continue

        # Skip out_of_scope entry points (e.g. hooks pointing to .claude/tools/)
        trace_status = ep.get("trace_status")
        if trace_status == "out_of_scope":
            journeys.append({
                "entry_type": ep["type"],
                "command": ep.get("command", ep.get("path", ep.get("name", "unknown"))),
                "handler": {
                    "file": ep.get("file", ""),
                    "function": ep.get("function", ""),
                    "lineno": ep.get("lineno"),
                },
                "trace_status": "out_of_scope",
                "trace_depth": 0,
                "functions_reached": 0,
                "outcomes": [],
                "packages_touched": [],
            })
            continue

        # If handler_key doesn't exist in call graph, try fuzzy matching:
        # search for functions in the same file whose name contains the parser name
        effective_key = handler_key
        if handler_key not in call_graph and handler_key not in all_functions:
            fuzzy = _fuzzy_resolve_handler(handler_key, all_functions)
            if fuzzy:
                effective_key = fuzzy

        trace = _trace_from(effective_key, call_graph, max_depth=5)
        outcomes = _classify_outcomes(trace["leaves"], all_functions, io_functions, subprocess_functions)
        packages_touched = _packages_from_keys(trace["visited"], root_str)

        all_reached.update(trace["visited"])

        journeys.append({
            "entry_type": ep["type"],
            "command": ep.get("command", ep.get("path", ep.get("name", "unknown"))),
            "handler": {
                "file": ep.get("file", ""),
                "function": ep.get("function", ""),
                "lineno": ep.get("lineno"),
            },
            "trace_depth": trace["max_depth"],
            "functions_reached": len(trace["visited"]),
            "outcomes": outcomes,
            "packages_touched": sorted(packages_touched),
        })

    # --- Step 5: Unreachable functions ---
    unreachable = []
    for func_key, func_info in sorted(all_functions.items()):
        if func_key not in all_reached:
            unreachable.append({
                "file": func_info["file"],
                "function": func_info["name"],
                "lineno": func_info.get("lineno"),
                "reason": "not reachable from any entry point within depth limit",
            })

    # --- Summary ---
    cli_count = sum(1 for j in journeys if j["entry_type"] == "cli")
    http_count = sum(1 for j in journeys if j["entry_type"] == "http")
    hook_count = sum(1 for j in journeys if j["entry_type"] == "hook")
    out_of_scope_count = sum(1 for j in journeys if j.get("trace_status") == "out_of_scope")
    # Exclude out_of_scope journeys from average depth calculation
    in_scope_depths = [j["trace_depth"] for j in journeys
                       if j.get("trace_status") != "out_of_scope"]
    avg_depth = round(sum(in_scope_depths) / len(in_scope_depths), 1) if in_scope_depths else 0.0

    return {
        "layer": "user-journeys",
        "call_graph": {
            "node_count": len(all_functions),
            "edge_count": sum(len(targets) for targets in call_graph.values()),
            "blarify_edges_added": blarify_edges_added,
            "max_depth_reached": 5,
        },
        "journeys": journeys,
        "unreachable_functions": unreachable,
        "limitations": [
            "Dynamic dispatch (getattr, __getattr__) not traced",
            "Registry/decorator-based indirect calls may be missed",
            "String-based imports (importlib.import_module) not followed",
            "Callbacks/higher-order function arguments not traced",
        ],
        "summary": {
            "total_journeys": len(journeys),
            "cli_journeys": cli_count,
            "http_journeys": http_count,
            "hook_journeys": hook_count,
            "out_of_scope_journeys": out_of_scope_count,
            "avg_trace_depth": avg_depth,
            "total_functions_in_graph": len(all_functions),
            "total_functions_reached": len(all_reached),
            "unreachable_function_count": len(unreachable),
        },
    }


def _build_call_graph(
    manifest: dict, layer2: dict, root: Path
) -> tuple[dict[str, set[str]], dict[str, dict]]:
    """Build a function-level call graph from layer2 data and AST re-parsing.

    Returns:
        (call_graph, all_functions) where:
        - call_graph maps "file::func" -> set of "file::func" keys
        - all_functions maps "file::func" -> {file, name, lineno, type}
    """
    root_str = str(root)

    # Index all definitions by file and name
    all_functions: dict[str, dict] = {}
    defs_by_file: dict[str, dict[str, dict]] = defaultdict(dict)
    classes_by_file: dict[str, dict[str, list[str]]] = defaultdict(dict)

    for defn in layer2.get("definitions", []):
        filepath = defn["file"]
        name = defn["name"]
        key = f"{filepath}::{name}"

        if defn["type"] in ("function", "async_function"):
            all_functions[key] = {
                "file": filepath,
                "name": name,
                "lineno": defn.get("lineno"),
                "type": defn["type"],
            }
            defs_by_file[filepath][name] = defn

        elif defn["type"] == "class":
            # Register class methods as functions
            for method in defn.get("methods", []):
                method_key = f"{filepath}::{name}.{method}"
                all_functions[method_key] = {
                    "file": filepath,
                    "name": f"{name}.{method}",
                    "lineno": defn.get("lineno"),
                    "type": "method",
                }
                defs_by_file[filepath][f"{name}.{method}"] = {
                    "file": filepath,
                    "name": f"{name}.{method}",
                    "type": "method",
                }
            classes_by_file[filepath][name] = defn.get("methods", [])

    # Build import resolution: file -> {imported_name: target_file}
    import_targets: dict[str, dict[str, str]] = defaultdict(dict)
    for imp in layer2.get("imports", []):
        if imp["category"] != "internal":
            continue
        target = imp.get("resolved_target")
        if not target:
            continue
        for name in imp.get("names", []):
            import_targets[imp["file"]][name] = target

    # Re-parse files to extract function-level call information
    call_graph: dict[str, set[str]] = defaultdict(set)
    py_files = [f for f in manifest["files"] if f["extension"] == ".py"]

    for file_entry in py_files:
        filepath = file_entry["path"]
        tree = parse_file_safe(Path(filepath))
        if tree is None:
            continue

        _extract_calls_from_ast(
            tree, filepath, defs_by_file, classes_by_file,
            import_targets, all_functions, call_graph
        )

    return dict(call_graph), all_functions


def _enrich_call_graph_from_blarify(
    call_graph: dict[str, set[str]],
    all_functions: dict[str, dict],
    root: Path,
) -> int:
    """Add non-Python CALLS edges from blarify to the call graph.

    Uses the blarify bridge to get CALLS relationships and adds edges
    for non-Python source or target functions. This enables cross-language
    call tracing.

    Returns:
        Number of edges added.
    """
    try:
        from scripts.atlas.blarify_bridge import BlarifyBridge, EXTENSION_TO_LANGUAGE
        import os

        bridge = BlarifyBridge(root)
        bridge.build()
        rels = bridge.get_relationships()
        calls = [r for r in rels if r.get("type") == "CALLS"]

        edges_added = 0
        for call in calls:
            src_file = call.get("source_file", "")
            tgt_file = call.get("target_file", "")
            src_name = call.get("source_name", "")
            tgt_name = call.get("target_name", "")

            if not src_file or not tgt_file or not src_name or not tgt_name:
                continue

            src_ext = os.path.splitext(src_file)[1]
            tgt_ext = os.path.splitext(tgt_file)[1]
            src_lang = EXTENSION_TO_LANGUAGE.get(src_ext, "unknown")
            tgt_lang = EXTENSION_TO_LANGUAGE.get(tgt_ext, "unknown")

            # Only add edges that involve non-Python code (Python edges
            # are already captured by the AST-based call graph)
            if src_lang == "python" and tgt_lang == "python":
                continue

            src_key = f"{src_file}::{src_name}"
            tgt_key = f"{tgt_file}::{tgt_name}"

            # Register functions if not already known
            if src_key not in all_functions:
                all_functions[src_key] = {
                    "file": src_file, "name": src_name,
                    "lineno": call.get("lineno"), "type": "function",
                }
            if tgt_key not in all_functions:
                all_functions[tgt_key] = {
                    "file": tgt_file, "name": tgt_name,
                    "lineno": None, "type": "function",
                }

            if tgt_key not in call_graph.get(src_key, set()):
                if src_key not in call_graph:
                    call_graph[src_key] = set()
                call_graph[src_key].add(tgt_key)
                edges_added += 1

        return edges_added

    except Exception as e:
        print(f"Note: blarify call graph enrichment skipped: {e}", file=sys.stderr)
        return 0


def _extract_calls_from_ast(
    tree: ast.Module,
    filepath: str,
    defs_by_file: dict[str, dict[str, dict]],
    classes_by_file: dict[str, dict[str, list[str]]],
    import_targets: dict[str, dict[str, str]],
    all_functions: dict[str, dict],
    call_graph: dict[str, set[str]],
) -> None:
    """Walk AST and extract function call edges for each function/method body."""

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # Determine the caller key
        caller_key = _get_caller_key(node, filepath, tree)
        if caller_key is None:
            continue

        # Walk the function body for Call nodes
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue

            callee_keys = _resolve_callee(
                child.func, filepath, defs_by_file, classes_by_file,
                import_targets, all_functions, node
            )
            for ck in callee_keys:
                call_graph[caller_key].add(ck)


def _get_caller_key(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    filepath: str,
    tree: ast.Module,
) -> str | None:
    """Determine the call graph key for a function definition node."""
    # Check if this function is a method inside a class
    for top_node in ast.iter_child_nodes(tree):
        if isinstance(top_node, ast.ClassDef):
            for child in top_node.body:
                if child is func_node:
                    return f"{filepath}::{top_node.name}.{func_node.name}"

    # Top-level function
    for top_node in ast.iter_child_nodes(tree):
        if top_node is func_node:
            return f"{filepath}::{func_node.name}"

    # Nested function -- skip for now (not in top-level defs)
    return None


def _resolve_callee(
    func_expr: ast.expr,
    filepath: str,
    defs_by_file: dict[str, dict[str, dict]],
    classes_by_file: dict[str, dict[str, list[str]]],
    import_targets: dict[str, dict[str, str]],
    all_functions: dict[str, dict],
    enclosing_func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[str]:
    """Resolve a Call's func expression to call graph keys.

    Handles:
    - Direct name calls: foo() -> look up in same file or imports
    - self.method() -> look up in enclosing class
    - module.func() -> look up via imports
    """
    results = []

    if isinstance(func_expr, ast.Name):
        name = func_expr.id

        # Check same file
        key = f"{filepath}::{name}"
        if key in all_functions:
            results.append(key)
        elif name in defs_by_file.get(filepath, {}):
            results.append(key)

        # Check imports
        if name in import_targets.get(filepath, {}):
            target_file = import_targets[filepath][name]
            imported_key = f"{target_file}::{name}"
            if imported_key in all_functions:
                results.append(imported_key)

    elif isinstance(func_expr, ast.Attribute):
        attr = func_expr.attr

        if isinstance(func_expr.value, ast.Name):
            obj_name = func_expr.value.id

            # self.method() -> look up in enclosing class
            if obj_name == "self":
                # Find enclosing class name by checking classes_by_file
                for cls_name, methods in classes_by_file.get(filepath, {}).items():
                    if attr in methods:
                        key = f"{filepath}::{cls_name}.{attr}"
                        if key in all_functions:
                            results.append(key)
                            break

            # cls.method() or ClassName.method()
            elif obj_name in {c for c in classes_by_file.get(filepath, {})}:
                key = f"{filepath}::{obj_name}.{attr}"
                if key in all_functions:
                    results.append(key)

            # module.func() via import
            elif obj_name in import_targets.get(filepath, {}):
                target_file = import_targets[filepath][obj_name]
                # The imported name is a module; look for attr in that file
                key = f"{target_file}::{attr}"
                if key in all_functions:
                    results.append(key)

    return results


def _get_entry_points(layer5: dict | None, root: Path) -> list[dict]:
    """Get entry points from layer5 or extract directly from codebase.

    Returns list of dicts with: type, command/path/name, handler_key, file,
    function, lineno, and optionally trace_status.
    """
    entry_points = []
    root_str = str(root)

    # Pre-build set_defaults handler map: file -> {parser_name: handler_func}
    # This resolves the handler_key mismatch where parser_name != actual handler.
    defaults_map = _build_set_defaults_map(root)

    if layer5:
        # CLI commands
        for cmd in layer5.get("cli_commands", []):
            handler_file = cmd.get("file", "")
            parser_name = cmd.get("parser_name", "")
            # Prefer handler_function from layer5, then set_defaults map, then parser_name
            handler_func = cmd.get("handler_function", "")
            if not handler_func and handler_file in defaults_map:
                handler_func = defaults_map[handler_file].get(parser_name, "")
            if not handler_func:
                handler_func = parser_name
            if handler_file and handler_func:
                entry_points.append({
                    "type": "cli",
                    "command": cmd.get("command", ""),
                    "handler_key": f"{handler_file}::{handler_func}",
                    "file": handler_file,
                    "function": handler_func,
                    "lineno": cmd.get("lineno"),
                })

        # HTTP routes
        for route in layer5.get("http_routes", []):
            handler_file = route.get("file", "")
            handler_func = route.get("function", "")
            if handler_file and handler_func:
                entry_points.append({
                    "type": "http",
                    "path": route.get("path", ""),
                    "command": f"{route.get('method', 'GET')} {route.get('path', '')}",
                    "handler_key": f"{handler_file}::{handler_func}",
                    "file": handler_file,
                    "function": handler_func,
                    "lineno": route.get("lineno"),
                })

        # Hooks
        for hook in layer5.get("hook_events", []):
            handler_file = hook.get("file", "")
            handler_func = hook.get("handler", "")
            if handler_file and handler_func:
                # Mark hooks pointing to .claude/tools/ as out_of_scope
                trace_status = None
                if ".claude/tools/" in handler_file:
                    trace_status = "out_of_scope"
                elif not handler_file.startswith(root_str):
                    trace_status = "out_of_scope"

                ep = {
                    "type": "hook",
                    "name": hook.get("name", ""),
                    "command": f"hook:{hook.get('name', '')}",
                    "handler_key": f"{handler_file}::{handler_func}",
                    "file": handler_file,
                    "function": handler_func,
                    "lineno": hook.get("lineno"),
                }
                if trace_status:
                    ep["trace_status"] = trace_status
                entry_points.append(ep)

    # Only fall back to direct codebase scanning when layer5 provided no
    # entry points.  This avoids re-scanning every .py file when layer5
    # already supplied a complete entry-point list.
    if not entry_points:
        direct_eps = _extract_entry_points_from_codebase(root)
        existing_keys = {ep["handler_key"] for ep in entry_points}
        for dep in direct_eps:
            if dep["handler_key"] not in existing_keys:
                entry_points.append(dep)

    return entry_points


def _build_set_defaults_map(root: Path) -> dict[str, dict[str, str]]:
    """Scan codebase for set_defaults(func=X) near add_parser() calls.

    Returns: {filepath: {parser_name: handler_function_name}}
    """
    result: dict[str, dict[str, str]] = {}

    for py_file in root.rglob("*.py"):
        filepath_str = str(py_file)
        if "__pycache__" in filepath_str:
            continue

        tree = parse_file_safe(py_file)
        if tree is None:
            continue

        # Collect add_parser names and set_defaults(func=X) in the same file
        parser_names: list[tuple[str, int]] = []  # (name, lineno)
        defaults_funcs: list[tuple[str, int]] = []  # (func_name, lineno)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue

            if node.func.attr == "add_parser":
                if (node.args
                        and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)):
                    parser_names.append((node.args[0].value, node.lineno))

            elif node.func.attr == "set_defaults":
                for kw in node.keywords:
                    if kw.arg == "func" and isinstance(kw.value, ast.Name):
                        defaults_funcs.append((kw.value.id, node.lineno))

        if not parser_names or not defaults_funcs:
            continue

        # Match each parser to the nearest following set_defaults call
        file_map: dict[str, str] = {}
        for p_name, p_line in parser_names:
            best_func = None
            best_dist = float("inf")
            for d_func, d_line in defaults_funcs:
                dist = d_line - p_line
                if 0 <= dist < best_dist:
                    best_dist = dist
                    best_func = d_func
            if best_func:
                file_map[p_name] = best_func

        if file_map:
            result[filepath_str] = file_map

    return result


def _fuzzy_resolve_handler(
    handler_key: str, all_functions: dict[str, dict]
) -> str | None:
    """Fuzzy-match a handler_key against the call graph when exact match fails.

    For handler_key "file::parser_name", search for functions in the same file
    whose name contains the parser_name (e.g. "generate" -> "generate_command",
    "cmd_generate").
    """
    if "::" not in handler_key:
        return None
    filepath, func_name = handler_key.split("::", 1)
    if not func_name:
        return None

    # Gather all function keys in the same file
    candidates = []
    for key, info in all_functions.items():
        if info["file"] == filepath:
            candidates.append((key, info["name"]))

    # Normalize: replace hyphens with underscores for matching
    name_norm = func_name.lower().replace("-", "_")
    matches = []
    for key, name in candidates:
        cand_norm = name.lower().replace("-", "_")
        if name_norm in cand_norm or cand_norm in name_norm:
            matches.append((key, name))

    if len(matches) == 1:
        return matches[0][0]

    # If multiple matches, prefer the one whose name is closest in length
    if matches:
        matches.sort(key=lambda m: abs(len(m[1]) - len(func_name)))
        return matches[0][0]

    return None


def _extract_entry_points_from_codebase(root: Path) -> list[dict]:
    """Extract entry points directly from the codebase by AST analysis.

    Only scans within root directory. Looks for:
    - main() functions in __main__.py files
    - main() in cli.py / main.py files
    - set_defaults(func=handler) patterns for argparse CLI handlers
    """
    root_str = str(root)
    entry_points = []

    # Only scan within root, skip __pycache__ and test dirs
    for py_file in root.rglob("*.py"):
        filepath_str = str(py_file)
        if "__pycache__" in filepath_str:
            continue

        name = py_file.name

        tree = parse_file_safe(py_file)
        if tree is None:
            continue

        # Collect all top-level function names for handler resolution
        top_level_funcs: set[str] = set()
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                top_level_funcs.add(node.name)

        # __main__.py -> main()
        if name == "__main__.py" and "main" in top_level_funcs:
            entry_points.append({
                "type": "cli",
                "command": f"python -m {_path_to_module(filepath_str, root_str)}",
                "handler_key": f"{filepath_str}::main",
                "file": filepath_str,
                "function": "main",
                "lineno": _find_func_lineno(tree, "main"),
            })

        # cli.py or main.py -> main()
        if name in ("cli.py", "main.py") and "main" in top_level_funcs:
            entry_points.append({
                "type": "cli",
                "command": f"cli:{name}",
                "handler_key": f"{filepath_str}::main",
                "file": filepath_str,
                "function": "main",
                "lineno": _find_func_lineno(tree, "main"),
            })

        # Look for set_defaults(func=X) patterns to find CLI handlers
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "set_defaults":
                continue
            for kw in node.keywords:
                if kw.arg == "func" and isinstance(kw.value, ast.Name):
                    handler_name = kw.value.id
                    # Only add if the handler is a real function defined in this file
                    # or somewhere we can resolve
                    if handler_name in top_level_funcs:
                        entry_points.append({
                            "type": "cli",
                            "command": f"subcommand:{handler_name}",
                            "handler_key": f"{filepath_str}::{handler_name}",
                            "file": filepath_str,
                            "function": handler_name,
                            "lineno": node.lineno,
                        })

    return entry_points


def _find_func_lineno(tree: ast.Module, name: str) -> int | None:
    """Find the line number of a top-level function by name."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node.lineno
    return None


def _path_to_module(filepath: str, root_str: str) -> str:
    """Convert file path to module name."""
    if filepath.startswith(root_str):
        rel = filepath[len(root_str):].lstrip("/")
    else:
        rel = filepath
    return rel.replace("/", ".").removesuffix(".py")


def _trace_from(
    start_key: str,
    call_graph: dict[str, set[str]],
    max_depth: int = 5,
) -> dict:
    """Trace call graph from start_key to max_depth using BFS.

    Returns dict with visited set, leaves set, max_depth reached.
    """
    from collections import deque as _deque

    visited: set[str] = set()
    leaves: set[str] = set()
    max_depth_reached = 0

    # BFS with depth tracking
    queue: _deque[tuple[str, int]] = _deque([(start_key, 0)])
    visited.add(start_key)

    while queue:
        current, depth = queue.popleft()
        max_depth_reached = max(max_depth_reached, depth)

        if depth >= max_depth:
            leaves.add(current)
            continue

        callees = call_graph.get(current, set())
        if not callees:
            leaves.add(current)
            continue

        for callee in callees:
            if callee not in visited:
                visited.add(callee)
                queue.append((callee, depth + 1))

    return {
        "visited": visited,
        "leaves": leaves,
        "max_depth": max_depth_reached,
    }


def _build_io_function_set(layer4: dict | None, layer6: dict | None) -> set[str]:
    """Build set of function keys that perform I/O operations."""
    io_funcs: set[str] = set()

    if layer6:
        for entry in layer6.get("file_io", []):
            ctx = entry.get("function_context", "")
            filepath = entry.get("file", "")
            if ctx and filepath:
                io_funcs.add(f"{filepath}::{ctx}")

        for entry in layer6.get("database_ops", []):
            ctx = entry.get("function_context", "")
            filepath = entry.get("file", "")
            if ctx and filepath:
                io_funcs.add(f"{filepath}::{ctx}")

        for entry in layer6.get("network_io", []):
            ctx = entry.get("function_context", "")
            filepath = entry.get("file", "")
            if ctx and filepath:
                io_funcs.add(f"{filepath}::{ctx}")

    return io_funcs


def _build_subprocess_function_set(layer4: dict | None) -> set[str]:
    """Build set of function keys that call subprocesses."""
    sp_funcs: set[str] = set()

    if layer4:
        for entry in layer4.get("subprocess_calls", []):
            ctx = entry.get("function_context", "")
            filepath = entry.get("file", "")
            if ctx and filepath:
                sp_funcs.add(f"{filepath}::{ctx}")

    return sp_funcs


def _classify_outcomes(
    leaves: set[str],
    all_functions: dict[str, dict],
    io_functions: set[str],
    subprocess_functions: set[str],
) -> list[dict]:
    """Classify leaf nodes in a trace into outcome types."""
    outcomes = []
    seen_types: set[str] = set()

    for leaf_key in sorted(leaves):
        func_info = all_functions.get(leaf_key, {})
        filepath = func_info.get("file", leaf_key.split("::")[0] if "::" in leaf_key else "")
        func_name = func_info.get("name", leaf_key.split("::")[-1] if "::" in leaf_key else leaf_key)

        outcome_type = "return_value"  # default

        # Check against known I/O and subprocess functions
        if leaf_key in subprocess_functions:
            outcome_type = "subprocess"
        elif leaf_key in io_functions:
            outcome_type = "file_io"
        else:
            # Heuristic classification from function name
            name_lower = func_name.lower()
            if any(kw in name_lower for kw in ("write", "save", "dump", "store", "persist")):
                outcome_type = "file_io"
            elif any(kw in name_lower for kw in ("read", "load", "parse_file")):
                outcome_type = "file_io"
            elif any(kw in name_lower for kw in ("exec", "run_command", "subprocess", "popen", "system")):
                outcome_type = "subprocess"
            elif any(kw in name_lower for kw in ("request", "fetch", "post", "get_url", "http", "api_call")):
                outcome_type = "network"
            elif any(kw in name_lower for kw in ("query", "execute_sql", "cursor", "connect_db")):
                outcome_type = "database"
            elif any(kw in name_lower for kw in ("raise", "error", "fail", "abort")):
                outcome_type = "error"

        # Deduplicate by (type, file) pair
        dedup_key = f"{outcome_type}:{filepath}"
        if dedup_key not in seen_types:
            seen_types.add(dedup_key)
            outcomes.append({
                "type": outcome_type,
                "detail": func_name,
                "file": filepath,
            })

    return outcomes


def _packages_from_keys(func_keys: set[str], root_str: str) -> set[str]:
    """Extract package names from function keys."""
    packages = set()
    for key in func_keys:
        if "::" not in key:
            continue
        filepath = key.split("::")[0]
        if filepath.startswith(root_str):
            rel = filepath[len(root_str):].lstrip("/")
        else:
            rel = filepath
        parent = str(Path(rel).parent)
        if parent != ".":
            pkg = parent.replace("/", ".")
            packages.add(pkg)
    return packages


def main():
    """CLI entry point for layer 8 extraction."""
    parser = argparse.ArgumentParser(description="Layer 8: User Journeys")
    parser.add_argument("--root", required=True, help="Project root directory")
    parser.add_argument("--output", required=True, help="Output directory for JSON files")
    parser.add_argument("--max-depth", type=int, default=5, help="Max call graph trace depth")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load required inputs
    manifest = load_manifest(output_dir)
    layer2 = load_layer_json("layer2_ast_bindings", output_dir)

    # Load optional inputs
    layer4 = None
    try:
        layer4 = load_layer_json("layer4_runtime_topology", output_dir)
    except FileNotFoundError:
        print("Note: layer4 not found, subprocess classification will use heuristics",
              file=sys.stderr)

    layer5 = None
    try:
        layer5 = load_layer_json("layer5_api_contracts", output_dir)
    except FileNotFoundError:
        print("Note: layer5 not found, extracting entry points directly from codebase",
              file=sys.stderr)

    layer6 = None
    try:
        layer6 = load_layer_json("layer6_data_flow", output_dir)
    except FileNotFoundError:
        print("Note: layer6 not found, I/O classification will use heuristics",
              file=sys.stderr)

    # Extract
    layer_data = extract(manifest, layer2, root, layer4, layer5, layer6)

    # Write output
    out_path = write_layer_json("layer8_user_journeys", layer_data, output_dir)

    # Print summary
    s = layer_data["summary"]
    cg = layer_data["call_graph"]
    print(f"Layer 8: {s['total_journeys']} journeys traced")
    blarify_extra = f" (+{cg['blarify_edges_added']} blarify)" if cg.get('blarify_edges_added') else ""
    print(f"  Call graph: {cg['node_count']} nodes, {cg['edge_count']} edges{blarify_extra}")
    print(f"  CLI journeys: {s['cli_journeys']}")
    print(f"  HTTP journeys: {s['http_journeys']}")
    print(f"  Hook journeys: {s['hook_journeys']}")
    print(f"  Avg trace depth: {s['avg_trace_depth']}")
    print(f"  Functions reached: {s['total_functions_reached']}/{s['total_functions_in_graph']}")
    print(f"  Unreachable: {s['unreachable_function_count']}")
    print(f"  Output: {out_path} ({out_path.stat().st_size} bytes)")
    sys.exit(0)


if __name__ == "__main__":
    main()
