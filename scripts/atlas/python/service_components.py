"""Layer 7: Service Components -- package metrics, coupling, and classification.

Computes per-package metrics (file_count, class_count, function_count, line_count),
cross-package coupling (afferent/efferent), instability, cohesion, and classification.

Inputs: manifest.json, layer2_ast_bindings.json
Optional: layer3_compile_deps.json (falls back to computing from layer2 imports)
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
from scripts.atlas.common import load_layer_json, load_manifest, write_layer_json


def extract(manifest: dict, layer2: dict, layer3: dict | None, root: Path) -> dict:
    """Extract layer 7 package metrics and coupling data.

    Args:
        manifest: Loaded manifest dict.
        layer2: Loaded layer2 ast-bindings dict.
        layer3: Loaded layer3 compile-deps dict, or None.
        root: Project root directory.

    Returns:
        Layer 7 data dict.
    """
    root = root.resolve()
    root_str = str(root)
    packages_in_manifest = set(manifest["summary"]["packages"])

    # --- Build package-level data from manifest ---
    pkg_files: dict[str, list[dict]] = defaultdict(list)
    for f in manifest["files"]:
        if f["extension"] == ".py":
            pkg_files[f["package"]].append(f)

    # --- Count definitions per package from layer2 ---
    pkg_classes: dict[str, int] = defaultdict(int)
    pkg_functions: dict[str, int] = defaultdict(int)
    pkg_defs: dict[str, list[dict]] = defaultdict(list)

    for defn in layer2.get("definitions", []):
        pkg = _file_to_package(defn["file"], root_str, packages_in_manifest)
        if pkg is None:
            continue
        pkg_defs[pkg].append(defn)
        if defn["type"] == "class":
            pkg_classes[pkg] += 1
        elif defn["type"] in ("function", "async_function"):
            pkg_functions[pkg] += 1

    # --- Public API size from layer2 exports ---
    pkg_public_api: dict[str, int] = defaultdict(int)
    for exp in layer2.get("exports", []):
        pkg = _file_to_package(exp["file"], root_str, packages_in_manifest)
        if pkg is not None:
            pkg_public_api[pkg] += len(exp.get("all_names", []))

    # --- Build import graph from layer2 internal imports ---
    # Edge: source_pkg -> target_pkg with count
    edge_counts: dict[tuple[str, str], int] = defaultdict(int)

    for imp in layer2.get("imports", []):
        if imp["category"] != "internal":
            continue
        target_file = imp.get("resolved_target")
        if not target_file:
            continue

        src_pkg = _file_to_package(imp["file"], root_str, packages_in_manifest)
        tgt_pkg = _file_to_package(target_file, root_str, packages_in_manifest)

        if src_pkg is None or tgt_pkg is None:
            continue
        if src_pkg == tgt_pkg:
            continue  # Intra-package, not cross-package

        edge_counts[(src_pkg, tgt_pkg)] += 1

    # If layer3 is available, use its graph edges too (for completeness)
    if layer3 and "internal_import_graph" in layer3:
        for edge in layer3["internal_import_graph"].get("edges", []):
            src = edge.get("from", "")
            tgt = edge.get("to", "")
            if src and tgt and src != tgt:
                key = (src, tgt)
                if key not in edge_counts:
                    edge_counts[key] = edge.get("import_count", 1)

    # --- Compute coupling metrics ---
    # Ca (afferent): how many OTHER packages import THIS package
    # Ce (efferent): how many OTHER packages THIS package imports
    ca: dict[str, set[str]] = defaultdict(set)
    ce: dict[str, set[str]] = defaultdict(set)

    for (src, tgt), _count in edge_counts.items():
        ce[src].add(tgt)
        ca[tgt].add(src)

    # --- Compute intra-package imports for cohesion ---
    intra_count: dict[str, int] = defaultdict(int)
    inter_count: dict[str, int] = defaultdict(int)

    for imp in layer2.get("imports", []):
        if imp["category"] != "internal":
            continue
        target_file = imp.get("resolved_target")
        if not target_file:
            continue
        src_pkg = _file_to_package(imp["file"], root_str, packages_in_manifest)
        tgt_pkg = _file_to_package(target_file, root_str, packages_in_manifest)
        if src_pkg is None or tgt_pkg is None:
            continue
        if src_pkg == tgt_pkg:
            intra_count[src_pkg] += 1
        else:
            inter_count[src_pkg] += 1

    # --- Build package entries ---
    all_pkgs = sorted(packages_in_manifest)
    total_pkg_count = len(all_pkgs)

    packages = []
    for pkg in all_pkgs:
        files = pkg_files.get(pkg, [])
        file_count = len(files)
        line_count = sum(f.get("line_count", 0) for f in files)
        class_count = pkg_classes.get(pkg, 0)
        function_count = pkg_functions.get(pkg, 0)
        public_api_size = pkg_public_api.get(pkg, 0)

        ca_set = ca.get(pkg, set())
        ce_set = ce.get(pkg, set())
        ca_count = len(ca_set)
        ce_count = len(ce_set)

        if ca_count + ce_count > 0:
            instability = round(ce_count / (ca_count + ce_count), 3)
        else:
            instability = 0.0

        # Cohesion: ratio of intra to total internal imports
        intra = intra_count.get(pkg, 0)
        inter = inter_count.get(pkg, 0)
        total_internal = intra + inter
        cohesion = round(intra / total_internal, 3) if total_internal > 0 else 1.0

        # Classification
        classification = _classify_package(
            ca_count, ce_count, file_count, total_pkg_count, packages_in_manifest
        )

        packages.append(
            {
                "name": pkg,
                "path": _package_to_path(pkg, root_str),
                "file_count": file_count,
                "class_count": class_count,
                "function_count": function_count,
                "line_count": line_count,
                "public_api_size": public_api_size,
                "afferent_coupling": ca_count,
                "efferent_coupling": ce_count,
                "instability": instability,
                "cohesion": cohesion,
                "classification": classification,
                "imports_from": sorted(ce.get(pkg, set())),
                "imported_by": sorted(ca.get(pkg, set())),
            }
        )

    # --- Coupling matrix ---
    coupling_matrix: dict[str, dict[str, int]] = {}
    for (src, tgt), count in sorted(edge_counts.items()):
        if src not in coupling_matrix:
            coupling_matrix[src] = {}
        coupling_matrix[src][tgt] = count

    # --- Find most coupled pair ---
    most_coupled_pair = None
    max_coupling = 0
    for (src, tgt), count in edge_counts.items():
        # Bidirectional total
        reverse = edge_counts.get((tgt, src), 0)
        total = count + reverse
        if total > max_coupling:
            max_coupling = total
            most_coupled_pair = [src, tgt]

    # --- Summary ---
    classifications = defaultdict(int)
    for p in packages:
        classifications[p["classification"]] += 1

    instabilities = [
        p["instability"] for p in packages if p["afferent_coupling"] + p["efferent_coupling"] > 0
    ]
    avg_instability = round(sum(instabilities) / len(instabilities), 3) if instabilities else 0.0

    # --- Completeness check ---
    pkg_names_in_output = {p["name"] for p in packages}
    missing_from_manifest = packages_in_manifest - pkg_names_in_output
    missing_from_output = pkg_names_in_output - packages_in_manifest
    completeness_ok = len(missing_from_manifest) == 0

    return {
        "layer": "service-components",
        "packages": packages,
        "coupling_matrix": coupling_matrix,
        "summary": {
            "total_packages": len(packages),
            "by_classification": dict(classifications),
            "core_packages": classifications.get("core", 0),
            "leaf_packages": classifications.get("leaf", 0),
            "utility_packages": classifications.get("utility", 0),
            "feature_packages": classifications.get("feature", 0),
            "avg_instability": avg_instability,
            "most_coupled_pair": most_coupled_pair,
            "total_cross_package_edges": len(edge_counts),
        },
        "completeness": {
            "packages_in_manifest": len(packages_in_manifest),
            "packages_in_output": len(packages),
            "missing_from_output": sorted(missing_from_manifest),
            "ok": completeness_ok,
        },
    }


def _file_to_package(filepath: str, root_str: str, known_packages: set[str]) -> str | None:
    """Map an absolute file path to its package name.

    Tries to find the longest matching package from the known set.
    """
    # Strip root prefix to get relative path
    if filepath.startswith(root_str):
        rel = filepath[len(root_str) :].lstrip("/")
    else:
        # Try to extract package from path components
        rel = filepath

    # Convert directory path to dotted package name
    parent = str(Path(rel).parent)
    if parent == ".":
        return None

    # Try progressively shorter package paths
    parts = parent.replace("/", ".").split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        if candidate in known_packages:
            return candidate

    # Fallback: use the first component if it exists
    if parts and parts[0] in known_packages:
        return parts[0]

    return None


def _package_to_path(pkg_name: str, root_str: str) -> str:
    """Convert dotted package name to absolute path."""
    rel = pkg_name.replace(".", "/")
    return f"{root_str}/{rel}"


def _classify_package(
    ca: int, ce: int, file_count: int, total_packages: int, all_packages: set[str]
) -> str:
    """Classify a package based on coupling metrics.

    - core: imported by > 50% of other packages
    - leaf: imports others but not imported (Ce > 0, Ca == 0)
    - utility: small (<= 5 files), imported by many (Ca >= 3), few own imports
    - feature: everything else
    """
    other_pkg_count = max(1, total_packages - 1)

    if ca > other_pkg_count * 0.5:
        return "core"

    if ca == 0 and ce > 0:
        return "leaf"

    if file_count <= 5 and ca >= 3 and ce <= 2:
        return "utility"

    return "feature"


def main():
    """CLI entry point for layer 7 extraction."""
    parser = argparse.ArgumentParser(description="Layer 7: Service Components")
    parser.add_argument("--root", required=True, help="Project root directory")
    parser.add_argument("--output", required=True, help="Output directory for JSON files")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load inputs
    manifest = load_manifest(output_dir)
    layer2 = load_layer_json("layer2_ast_bindings", output_dir)

    layer3 = None
    try:
        layer3 = load_layer_json("layer3_compile_deps", output_dir)
    except FileNotFoundError:
        print(
            "Note: layer3_compile_deps.json not found, computing coupling from layer2 only",
            file=sys.stderr,
        )

    # Extract
    layer_data = extract(manifest, layer2, layer3, root)

    # Write output
    out_path = write_layer_json("layer7_service_components", layer_data, output_dir)

    # Print summary
    s = layer_data["summary"]
    print(f"Layer 7: {s['total_packages']} packages")
    print(f"  Classification: {json.dumps(s['by_classification'])}")
    print(f"  Avg instability: {s['avg_instability']}")
    print(f"  Cross-package edges: {s['total_cross_package_edges']}")
    if s["most_coupled_pair"]:
        print(f"  Most coupled pair: {s['most_coupled_pair']}")

    comp = layer_data["completeness"]
    if comp["ok"]:
        print(f"  Completeness: PASS ({comp['packages_in_output']}/{comp['packages_in_manifest']})")
    else:
        print(f"  Completeness: FAIL ({comp['packages_in_output']}/{comp['packages_in_manifest']})")
        print(f"    Missing: {comp['missing_from_output']}")
        sys.exit(1)

    print(f"  Output: {out_path} ({out_path.stat().st_size} bytes)")
    sys.exit(0)


if __name__ == "__main__":
    main()
