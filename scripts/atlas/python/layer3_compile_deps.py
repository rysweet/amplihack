"""Layer 3: Compile Dependencies -- external deps, internal import graph, cycles.

Parses pyproject.toml for declared dependencies, builds the internal import graph
from layer2 data, detects circular dependencies via iterative Tarjan's SCC, and
cross-checks declared vs actually-imported packages.
"""

import argparse
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
from scripts.atlas.common import (
    find_repo_root,
    get_stdlib_modules,
    load_layer_json,
    load_manifest,
    write_layer_json,
)


def _normalize_package_name(name: str) -> str:
    """Normalize per PEP 503: lowercase, replace [-_.] with hyphens."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _parse_dep_spec(spec: str) -> tuple[str, str]:
    """Parse 'flask>=2.0.0' into (name, version_constraint)."""
    match = re.match(r"^([A-Za-z0-9][-A-Za-z0-9_.]*)", spec)
    if not match:
        return spec, ""
    name = match.group(1)
    constraint = spec[len(name):].strip()
    return name, constraint


def _parse_pyproject(repo_root: Path) -> list[dict]:
    """Parse pyproject.toml and extract all dependency declarations."""
    toml_path = repo_root / "pyproject.toml"
    if not toml_path.exists():
        print(f"WARNING: {toml_path} not found", file=sys.stderr)
        return []

    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    deps: list[dict] = []
    project = data.get("project", {})

    # Core dependencies
    for spec in project.get("dependencies", []):
        name, constraint = _parse_dep_spec(spec)
        deps.append({
            "name": name,
            "normalized_name": _normalize_package_name(name),
            "version_constraint": constraint,
            "group": "core",
            "imported_by": [],
            "import_count": 0,
        })

    # Optional dependencies
    for group, group_deps in project.get("optional-dependencies", {}).items():
        for spec in group_deps:
            name, constraint = _parse_dep_spec(spec)
            deps.append({
                "name": name,
                "normalized_name": _normalize_package_name(name),
                "version_constraint": constraint,
                "group": group,
                "imported_by": [],
                "import_count": 0,
            })

    return deps


def _import_module_to_package_name(module: str) -> str:
    """Extract the top-level package name from an import module string."""
    clean = module.lstrip(".")
    return clean.split(".")[0] if clean else ""


def _file_to_package(filepath: str, root: str) -> str:
    """Convert absolute filepath to package name relative to root."""
    try:
        rel = Path(filepath).relative_to(root)
    except ValueError:
        return filepath
    parts = list(rel.parts)
    # Remove filename, build dotted package
    if parts and parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
        if parts[-1] == "__init__":
            parts = parts[:-1]
    return ".".join(parts) if parts else Path(root).name


def _tarjan_scc(graph: dict[str, set[str]]) -> list[list[str]]:
    """Iterative Tarjan's SCC algorithm.

    Args:
        graph: Adjacency dict mapping node -> set of successors.

    Returns:
        List of SCCs (each a list of nodes). Only SCCs with size > 1
        represent circular dependencies.
    """
    index_counter = [0]
    stack: list[str] = []
    on_stack: set[str] = set()
    index: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    sccs: list[list[str]] = []

    all_nodes = set(graph.keys())
    for targets in graph.values():
        all_nodes.update(targets)

    def strongconnect(v: str) -> None:
        # Use explicit work stack to avoid recursion limit
        work: list[tuple[str, list[str], int]] = []
        work.append((v, list(graph.get(v, set())), 0))
        index[v] = lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack.add(v)

        while work:
            node, successors, pos = work[-1]

            if pos < len(successors):
                work[-1] = (node, successors, pos + 1)
                w = successors[pos]
                if w not in index:
                    index[w] = lowlink[w] = index_counter[0]
                    index_counter[0] += 1
                    stack.append(w)
                    on_stack.add(w)
                    work.append((w, list(graph.get(w, set())), 0))
                elif w in on_stack:
                    lowlink[node] = min(lowlink[node], index[w])
            else:
                # All successors processed
                if lowlink[node] == index[node]:
                    scc = []
                    while True:
                        w = stack.pop()
                        on_stack.discard(w)
                        scc.append(w)
                        if w == node:
                            break
                    sccs.append(scc)

                work.pop()
                if work:
                    parent = work[-1][0]
                    lowlink[parent] = min(lowlink[parent], lowlink[node])

    for node in sorted(all_nodes):
        if node not in index:
            strongconnect(node)

    return sccs


def extract(manifest: dict, layer2: dict, repo_root: Path) -> dict:
    """Extract layer 3 compile dependency data.

    Args:
        manifest: Loaded manifest.json.
        layer2: Loaded layer2_ast_bindings.json.
        repo_root: Repository root directory (parent of src/amplihack).

    Returns:
        Layer 3 data dict.
    """
    root_str = manifest["root"]
    stdlib = get_stdlib_modules()

    # 1. Parse external dependencies from pyproject.toml
    ext_deps = _parse_pyproject(repo_root)

    # Build lookup: normalized name -> dep entry
    dep_lookup: dict[str, dict] = {}
    for dep in ext_deps:
        dep_lookup[dep["normalized_name"]] = dep

    # Also map common import-name -> normalized-name discrepancies
    # (e.g., python-dotenv imports as dotenv, PyYAML imports as yaml)
    import_name_aliases: dict[str, str] = {}
    for dep in ext_deps:
        norm = dep["normalized_name"]
        raw = dep["name"].lower()
        # Common transforms
        if raw.startswith("python-"):
            alias = raw[7:]
            import_name_aliases[alias] = norm
        if "-" in raw:
            import_name_aliases[raw.replace("-", "_")] = norm
        if "_" in raw:
            import_name_aliases[raw.replace("_", "-")] = norm

    # 2. Cross-check external deps vs actual imports
    third_party_imports = [
        imp for imp in layer2.get("imports", [])
        if imp.get("category") == "third_party"
    ]

    # Track which declared deps are actually imported
    for imp in third_party_imports:
        top_pkg = _import_module_to_package_name(imp["module"])
        if not top_pkg:
            continue
        norm = _normalize_package_name(top_pkg)

        matched_dep = dep_lookup.get(norm)
        if not matched_dep and norm in import_name_aliases:
            matched_dep = dep_lookup.get(import_name_aliases[norm])
        if not matched_dep:
            # Try alias lookup for the raw name too
            for alias, dep_norm in import_name_aliases.items():
                if top_pkg.lower() == alias:
                    matched_dep = dep_lookup.get(dep_norm)
                    break

        if matched_dep:
            if imp["file"] not in matched_dep["imported_by"]:
                matched_dep["imported_by"].append(imp["file"])
            matched_dep["import_count"] += 1

    # Find unused (declared but never imported)
    unused_deps = [
        dep["name"] for dep in ext_deps
        if dep["import_count"] == 0 and dep["group"] == "core"
    ]

    # Find undeclared (imported but not declared, excluding stdlib)
    declared_normalized = set(dep_lookup.keys())
    declared_aliases = set(import_name_aliases.keys())
    undeclared_deps: list[str] = []
    seen_undeclared: set[str] = set()

    for imp in third_party_imports:
        top_pkg = _import_module_to_package_name(imp["module"])
        if not top_pkg:
            continue
        norm = _normalize_package_name(top_pkg)
        if norm in declared_normalized:
            continue
        if norm in declared_aliases:
            continue
        if top_pkg.lower() in declared_aliases:
            continue
        if norm not in seen_undeclared:
            seen_undeclared.add(norm)
            undeclared_deps.append(top_pkg)

    # 3. Build internal import graph
    internal_imports = [
        imp for imp in layer2.get("imports", [])
        if imp.get("category") == "internal"
    ]

    # File-level edges
    file_edges: dict[str, set[str]] = {}
    for imp in internal_imports:
        src_file = imp["file"]
        target = imp.get("resolved_target")
        if target:
            file_edges.setdefault(src_file, set()).add(target)

    # Aggregate to package level
    pkg_edges: dict[str, dict[str, int]] = {}
    all_packages: set[str] = set()

    # Get all .py files and their packages
    py_files = [f for f in manifest["files"] if f["extension"] == ".py"]
    for f in py_files:
        pkg = _file_to_package(f["path"], root_str)
        all_packages.add(pkg)

    for src_file, targets in file_edges.items():
        src_pkg = _file_to_package(src_file, root_str)
        for tgt_file in targets:
            tgt_pkg = _file_to_package(tgt_file, root_str)
            if src_pkg != tgt_pkg:
                pkg_edges.setdefault(src_pkg, {})
                pkg_edges[src_pkg][tgt_pkg] = pkg_edges[src_pkg].get(tgt_pkg, 0) + 1

    # Build graph for Tarjan
    pkg_graph: dict[str, set[str]] = {}
    for src, targets in pkg_edges.items():
        pkg_graph.setdefault(src, set()).update(targets.keys())

    # 4. Detect circular dependencies via Tarjan's SCC
    sccs = _tarjan_scc(pkg_graph)
    cycles = [scc for scc in sccs if len(scc) > 1]

    circular_deps = []
    for cycle_pkgs in cycles:
        cycle_set = set(cycle_pkgs)
        files_involved = []
        for imp in internal_imports:
            src_pkg = _file_to_package(imp["file"], root_str)
            tgt = imp.get("resolved_target")
            if tgt:
                tgt_pkg = _file_to_package(tgt, root_str)
                if src_pkg in cycle_set and tgt_pkg in cycle_set and src_pkg != tgt_pkg:
                    files_involved.append({
                        "file": imp["file"],
                        "imports": imp["module"],
                        "lineno": imp["lineno"],
                    })
        # Build cycle path
        cycle_path = list(cycle_pkgs) + [cycle_pkgs[0]]
        circular_deps.append({
            "cycle": cycle_path,
            "files_involved": files_involved,
        })

    # Build edges list for output
    edge_list = []
    for src, targets in sorted(pkg_edges.items()):
        for tgt, count in sorted(targets.items()):
            edge_list.append({
                "from": src,
                "to": tgt,
                "import_count": count,
            })

    nodes = sorted(all_packages)

    return {
        "layer": "compile-deps",
        "external_dependencies": ext_deps,
        "internal_import_graph": {
            "nodes": nodes,
            "edges": edge_list,
        },
        "circular_dependencies": circular_deps,
        "unused_dependencies": unused_deps,
        "undeclared_dependencies": undeclared_deps,
        "summary": {
            "external_dep_count": len(ext_deps),
            "internal_packages": len(nodes),
            "internal_edges": len(edge_list),
            "circular_dependency_count": len(circular_deps),
            "unused_dep_count": len(unused_deps),
            "undeclared_dep_count": len(undeclared_deps),
        },
    }


def self_check(data: dict, manifest: dict, layer2: dict) -> list[str]:
    """Completeness self-check for layer 3.

    Returns list of issues (empty = pass).
    """
    issues = []

    # Every internal import from layer2 should be in the graph
    internal_imports = [
        imp for imp in layer2.get("imports", [])
        if imp.get("category") == "internal" and imp.get("resolved_target")
    ]
    graph_edges = data.get("internal_import_graph", {}).get("edges", [])
    if not graph_edges and internal_imports:
        issues.append(
            f"No graph edges but {len(internal_imports)} internal imports exist"
        )

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Layer 3: Compile Dependencies")
    parser.add_argument("--root", required=True, help="Project source root")
    parser.add_argument("--output", required=True, help="Output directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output = Path(args.output).resolve()

    repo_root = find_repo_root(root)

    manifest = load_manifest(output)
    layer2 = load_layer_json("layer2_ast_bindings", output)

    data = extract(manifest, layer2, repo_root)

    issues = self_check(data, manifest, layer2)

    out_path = write_layer_json("layer3_compile_deps", data, output)

    # Summary
    s = data["summary"]
    print(f"Layer 3: compile-deps")
    print(f"  External dependencies: {s['external_dep_count']}")
    print(f"  Internal packages:     {s['internal_packages']}")
    print(f"  Internal edges:        {s['internal_edges']}")
    print(f"  Circular dependencies: {s['circular_dependency_count']}")
    print(f"  Unused deps:           {s['unused_dep_count']}")
    print(f"  Undeclared deps:       {s['undeclared_dep_count']}")
    if data["unused_dependencies"]:
        print(f"  Unused: {', '.join(data['unused_dependencies'])}")
    if data["undeclared_dependencies"]:
        print(f"  Undeclared: {', '.join(data['undeclared_dependencies'][:20])}")
    if issues:
        print(f"  ISSUES: {len(issues)}")
        for issue in issues:
            print(f"    - {issue}")
    print(f"  Output: {out_path} ({out_path.stat().st_size:,} bytes)")

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
