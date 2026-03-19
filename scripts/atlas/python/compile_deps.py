"""Layer 3: Compile Dependencies -- external deps, internal import graph, cycles.

Parses dependency manifests for all detected languages (pyproject.toml,
Cargo.toml, package.json, go.mod, *.csproj), builds the internal import graph
from layer2 data, detects circular dependencies via iterative Tarjan's SCC, and
cross-checks declared vs actually-imported packages.
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
from scripts.atlas.common import (
    detect_languages,
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
    constraint = spec[len(name) :].strip()
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
        deps.append(
            {
                "name": name,
                "normalized_name": _normalize_package_name(name),
                "version_constraint": constraint,
                "group": "core",
                "imported_by": [],
                "import_count": 0,
            }
        )

    # Optional dependencies
    for group, group_deps in project.get("optional-dependencies", {}).items():
        for spec in group_deps:
            name, constraint = _parse_dep_spec(spec)
            deps.append(
                {
                    "name": name,
                    "normalized_name": _normalize_package_name(name),
                    "version_constraint": constraint,
                    "group": group,
                    "imported_by": [],
                    "import_count": 0,
                }
            )

    return deps


def _parse_cargo_toml(repo_root: Path, manifest_paths: list[str] | None = None) -> list[dict]:
    """Parse Cargo.toml and extract Rust crate dependencies.

    Handles both inline version strings (``serde = "1.0"``) and table entries
    (``clap = { version = "4.5", features = ["derive"] }``).

    Parses [dependencies], [dev-dependencies], and [build-dependencies].

    Args:
        repo_root: Repository root directory.
        manifest_paths: Relative paths to Cargo.toml files (from detect_languages).
            Falls back to repo_root/Cargo.toml if not provided.
    """
    if manifest_paths:
        toml_paths = [repo_root / p for p in manifest_paths if p.endswith("Cargo.toml")]
    else:
        toml_paths = [repo_root / "Cargo.toml"]
    toml_paths = [p for p in toml_paths if p.exists()]
    if not toml_paths:
        return []

    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            print(
                "WARNING: tomllib/tomli not available, skipping Cargo.toml",
                file=sys.stderr,
            )
            return []

    deps: list[dict] = []
    seen: set[str] = set()
    # Top-level and workspace-level dependency sections
    cargo_sections = [
        (["dependencies"], "dependencies"),
        (["dev-dependencies"], "dev-dependencies"),
        (["build-dependencies"], "build-dependencies"),
        (["workspace", "dependencies"], "dependencies"),
    ]

    for toml_path in toml_paths:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)

        source = str(toml_path.relative_to(repo_root))
        for key_path, group in cargo_sections:
            section = data
            for key in key_path:
                section = section.get(key, {})
            if not isinstance(section, dict):
                continue
            for name, value in section.items():
                norm = name.lower().replace("_", "-")
                if norm in seen:
                    continue
                seen.add(norm)
                if isinstance(value, str):
                    version = value
                elif isinstance(value, dict):
                    version = value.get("version", "")
                else:
                    version = ""
                deps.append(
                    {
                        "name": name,
                        "normalized_name": norm,
                        "version_constraint": version,
                        "group": group,
                        "language": "rust",
                        "source": source,
                        "imported_by": [],
                        "import_count": 0,
                    }
                )

    return deps


def _parse_package_json(repo_root: Path, manifest_paths: list[str] | None = None) -> list[dict]:
    """Parse package.json and extract JavaScript/TypeScript dependencies.

    Parses dependencies, devDependencies, peerDependencies, and
    optionalDependencies.
    """
    if manifest_paths:
        pkg_paths = [repo_root / p for p in manifest_paths if p.endswith("package.json")]
    else:
        pkg_paths = [repo_root / "package.json"]
    pkg_paths = [p for p in pkg_paths if p.exists()]
    if not pkg_paths:
        return []

    deps: list[dict] = []
    seen: set[str] = set()
    npm_sections = [
        ("dependencies", "dependencies"),
        ("devDependencies", "dev-dependencies"),
        ("peerDependencies", "peer-dependencies"),
        ("optionalDependencies", "optional-dependencies"),
    ]

    for pkg_path in pkg_paths:
        try:
            data = json.loads(pkg_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARNING: failed to parse {pkg_path}: {e}", file=sys.stderr)
            continue

        source = str(pkg_path.relative_to(repo_root))
        for section_key, group in npm_sections:
            section = data.get(section_key, {})
            for name, version in section.items():
                norm = name.lower()
                if norm in seen:
                    continue
                seen.add(norm)
                deps.append(
                    {
                        "name": name,
                        "normalized_name": norm,
                        "version_constraint": version,
                        "group": group,
                        "language": "javascript",
                        "source": source,
                        "imported_by": [],
                        "import_count": 0,
                    }
                )

    return deps


def _parse_go_mod(repo_root: Path, manifest_paths: list[str] | None = None) -> list[dict]:
    """Parse go.mod and extract Go module dependencies.

    Handles both single-line ``require`` and block ``require ( ... )``.
    """
    if manifest_paths:
        mod_paths = [repo_root / p for p in manifest_paths if p.endswith("go.mod")]
    else:
        mod_paths = [repo_root / "go.mod"]
    mod_paths = [p for p in mod_paths if p.exists()]
    if not mod_paths:
        return []

    deps: list[dict] = []
    seen: set[str] = set()

    # Match require blocks: require ( ... )
    block_pattern = re.compile(r"require\s*\((.*?)\)", re.DOTALL)
    # Match single require lines: require github.com/foo v1.2.3
    single_pattern = re.compile(r"^require\s+(\S+)\s+(\S+)", re.MULTILINE)
    # Match lines inside a require block: module version
    line_pattern = re.compile(r"^\s+(\S+)\s+(\S+)", re.MULTILINE)

    for mod_path in mod_paths:
        try:
            content = mod_path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"WARNING: failed to read {mod_path}: {e}", file=sys.stderr)
            continue

        source = str(mod_path.relative_to(repo_root))

        # Parse blocks
        for block_match in block_pattern.finditer(content):
            block = block_match.group(1)
            for line_match in line_pattern.finditer(block):
                module_path_str = line_match.group(1)
                version = line_match.group(2)
                if module_path_str.startswith("//"):
                    continue
                norm = module_path_str.lower()
                if norm in seen:
                    continue
                seen.add(norm)
                deps.append(
                    {
                        "name": module_path_str,
                        "normalized_name": norm,
                        "version_constraint": version,
                        "group": "dependencies",
                        "language": "go",
                        "source": source,
                        "imported_by": [],
                        "import_count": 0,
                    }
                )

        # Parse single-line requires
        for match in single_pattern.finditer(content):
            module_path_str = match.group(1)
            version = match.group(2)
            norm = module_path_str.lower()
            if norm in seen:
                continue
            seen.add(norm)
            deps.append(
                {
                    "name": module_path_str,
                    "normalized_name": norm,
                    "version_constraint": version,
                    "group": "dependencies",
                    "language": "go",
                    "source": source,
                    "imported_by": [],
                    "import_count": 0,
                }
            )

    return deps


def _parse_csproj(repo_root: Path) -> list[dict]:
    """Parse *.csproj files and extract .NET/C# NuGet package references.

    Looks for ``<PackageReference Include="..." Version="..." />`` elements.
    """
    csproj_files = list(repo_root.glob("**/*.csproj"))
    if not csproj_files:
        return []

    deps: list[dict] = []
    seen: set[str] = set()

    for csproj_path in csproj_files:
        try:
            tree = ET.parse(csproj_path)
        except ET.ParseError as e:
            print(
                f"WARNING: failed to parse {csproj_path}: {e}",
                file=sys.stderr,
            )
            continue

        for pkg_ref in tree.iter("PackageReference"):
            name = pkg_ref.get("Include", "")
            version = pkg_ref.get("Version", "")
            if not name:
                continue
            norm = name.lower()
            if norm in seen:
                continue
            seen.add(norm)
            deps.append(
                {
                    "name": name,
                    "normalized_name": norm,
                    "version_constraint": version,
                    "group": "dependencies",
                    "language": "csharp",
                    "source": csproj_path.name,
                    "imported_by": [],
                    "import_count": 0,
                }
            )

    return deps


def _parse_pom_xml(repo_root: Path, manifest_paths: list[str] | None = None) -> list[dict]:
    """Parse pom.xml files and extract Java Maven dependencies.

    Looks for ``<dependency>`` elements with ``<groupId>``, ``<artifactId>``,
    and optionally ``<version>``.

    Args:
        repo_root: Repository root directory.
        manifest_paths: Relative paths to pom.xml files (from detect_languages).
    """
    if manifest_paths:
        pom_paths = [repo_root / p for p in manifest_paths if p.endswith("pom.xml")]
    else:
        pom_paths = [repo_root / "pom.xml"]
    pom_paths = [p for p in pom_paths if p.exists()]
    if not pom_paths:
        return []

    deps: list[dict] = []
    seen: set[str] = set()

    for pom_path in pom_paths:
        try:
            tree = ET.parse(pom_path)
        except ET.ParseError as e:
            print(f"WARNING: failed to parse {pom_path}: {e}", file=sys.stderr)
            continue

        root = tree.getroot()
        # Handle Maven namespace
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        source = str(pom_path.relative_to(repo_root))

        for dep in root.iter(f"{ns}dependency"):
            group_id_el = dep.find(f"{ns}groupId")
            artifact_id_el = dep.find(f"{ns}artifactId")
            version_el = dep.find(f"{ns}version")
            scope_el = dep.find(f"{ns}scope")

            if group_id_el is None or artifact_id_el is None:
                continue

            group_id = group_id_el.text or ""
            artifact_id = artifact_id_el.text or ""
            version = version_el.text if version_el is not None else ""
            scope = scope_el.text if scope_el is not None else "compile"

            name = f"{group_id}:{artifact_id}"
            norm = name.lower()
            if norm in seen:
                continue
            seen.add(norm)

            group = "dev-dependencies" if scope == "test" else "dependencies"
            deps.append(
                {
                    "name": name,
                    "normalized_name": norm,
                    "version_constraint": version,
                    "group": group,
                    "language": "java",
                    "source": source,
                    "imported_by": [],
                    "import_count": 0,
                }
            )

    return deps


def _parse_build_gradle(repo_root: Path, manifest_paths: list[str] | None = None) -> list[dict]:
    """Parse build.gradle / build.gradle.kts and extract Gradle dependencies.

    Extracts dependency declarations matching patterns like:
        implementation 'group:artifact:version'
        testImplementation "group:artifact:version"
        api("group:artifact:version")

    Args:
        repo_root: Repository root directory.
        manifest_paths: Relative paths to build.gradle files (from detect_languages).
    """
    gradle_names = {"build.gradle", "build.gradle.kts"}
    if manifest_paths:
        gradle_paths = [repo_root / p for p in manifest_paths if Path(p).name in gradle_names]
    else:
        gradle_paths = [repo_root / n for n in gradle_names]
    gradle_paths = [p for p in gradle_paths if p.exists()]
    if not gradle_paths:
        return []

    # Match: configuration 'group:artifact:version' or configuration("group:artifact:version")
    dep_pattern = re.compile(
        r"""(?:implementation|api|compileOnly|runtimeOnly|testImplementation|"""
        r"""testCompileOnly|testRuntimeOnly|classpath|annotationProcessor)"""
        r"""\s*[\(]?\s*['"]([^'"]+)['"]""",
        re.MULTILINE,
    )

    # Map Gradle configurations to our group names
    test_configs = {"testImplementation", "testCompileOnly", "testRuntimeOnly"}

    deps: list[dict] = []
    seen: set[str] = set()

    for gradle_path in gradle_paths:
        try:
            content = gradle_path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"WARNING: failed to read {gradle_path}: {e}", file=sys.stderr)
            continue

        source = str(gradle_path.relative_to(repo_root))

        for match in dep_pattern.finditer(content):
            dep_str = match.group(1)
            parts = dep_str.split(":")

            if len(parts) < 2:
                continue

            group_id = parts[0]
            artifact_id = parts[1]
            version = parts[2] if len(parts) > 2 else ""

            name = f"{group_id}:{artifact_id}"
            norm = name.lower()
            if norm in seen:
                continue
            seen.add(norm)

            # Determine group from configuration keyword
            line = content[: match.start()].rsplit("\n", 1)[-1] if match.start() > 0 else ""
            group = "dev-dependencies" if any(tc in line for tc in test_configs) else "dependencies"

            deps.append(
                {
                    "name": name,
                    "normalized_name": norm,
                    "version_constraint": version,
                    "group": group,
                    "language": "java",
                    "source": source,
                    "imported_by": [],
                    "import_count": 0,
                }
            )

    return deps


def _parse_all_dependencies(manifest: dict, repo_root: Path) -> list[dict]:
    """Parse dependency manifests for all detected languages.

    Calls detect_languages() to find which languages are present, then invokes
    the appropriate parsers. All results share a uniform schema with a
    ``language`` field to distinguish origin.

    Args:
        manifest: Loaded manifest dict.
        repo_root: Repository root directory.

    Returns:
        Combined list of external dependency dicts.
    """
    languages = detect_languages(manifest, repo_root)
    all_deps: list[dict] = []

    def _manifests_for(lang: str) -> list[str]:
        return languages.get(lang, {}).get("manifests", [])

    # Always try Python (existing behavior)
    if "python" in languages or (repo_root / "pyproject.toml").exists():
        py_deps = _parse_pyproject(repo_root)
        for dep in py_deps:
            dep.setdefault("language", "python")
            dep.setdefault("source", "pyproject.toml")
        all_deps.extend(py_deps)

    if "rust" in languages:
        all_deps.extend(_parse_cargo_toml(repo_root, _manifests_for("rust")))

    if "javascript" in languages or "typescript" in languages:
        js_manifests = _manifests_for("javascript") + _manifests_for("typescript")
        all_deps.extend(_parse_package_json(repo_root, js_manifests))

    if "go" in languages:
        all_deps.extend(_parse_go_mod(repo_root, _manifests_for("go")))

    if "csharp" in languages:
        all_deps.extend(_parse_csproj(repo_root))

    if "java" in languages:
        java_manifests = _manifests_for("java")
        all_deps.extend(_parse_pom_xml(repo_root, java_manifests))
        all_deps.extend(_parse_build_gradle(repo_root, java_manifests))

    return all_deps


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

    # 1. Parse external dependencies from ALL detected language manifests
    ext_deps = _parse_all_dependencies(manifest, repo_root)

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
        imp for imp in layer2.get("imports", []) if imp.get("category") == "third_party"
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
        dep["name"] for dep in ext_deps if dep["import_count"] == 0 and dep["group"] == "core"
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
        imp for imp in layer2.get("imports", []) if imp.get("category") == "internal"
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
                    files_involved.append(
                        {
                            "file": imp["file"],
                            "imports": imp["module"],
                            "lineno": imp["lineno"],
                        }
                    )
        # Build cycle path
        cycle_path = list(cycle_pkgs) + [cycle_pkgs[0]]
        circular_deps.append(
            {
                "cycle": cycle_path,
                "files_involved": files_involved,
            }
        )

    # Build edges list for output
    edge_list = []
    for src, targets in sorted(pkg_edges.items()):
        for tgt, count in sorted(targets.items()):
            edge_list.append(
                {
                    "from": src,
                    "to": tgt,
                    "import_count": count,
                }
            )

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
        imp
        for imp in layer2.get("imports", [])
        if imp.get("category") == "internal" and imp.get("resolved_target")
    ]
    graph_edges = data.get("internal_import_graph", {}).get("edges", [])
    if not graph_edges and internal_imports:
        issues.append(f"No graph edges but {len(internal_imports)} internal imports exist")

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
    print("Layer 3: compile-deps")
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
