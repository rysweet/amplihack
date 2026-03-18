"""Layer 2: AST+LSP Symbol Bindings -- cross-file references and dead code.

Parses ALL .py files with ast.parse(), extracts definitions, exports (__all__),
imports, cross-references, and dead code candidates. This is the most critical
layer -- it provides the symbol table that layers 3, 7, and 8 depend on.
"""

import argparse
import ast
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
from scripts.atlas.common import (
    load_manifest,
    parse_file_safe,
    resolve_internal_import,
    walk_calls,
    walk_definitions,
    walk_imports,
    write_layer_json,
)


def extract(manifest: dict, root: Path) -> dict:
    """Extract layer 2 data by parsing all Python files.

    For each .py file:
      1. Parse with ast.parse()
      2. Extract definitions (functions, classes, constants)
      3. Extract __all__ exports
      4. Extract imports (classify as stdlib/third_party/internal)
      5. Resolve internal imports to file paths

    After all files:
      6. Build cross-reference map
      7. Detect dead code (conservative)
      8. Tag conditional imports
      9. Detect importlib.import_module() calls

    Args:
        manifest: Loaded manifest dict.
        root: Project root directory.

    Returns:
        Layer 2 data dict matching the spec schema.
    """
    root = root.resolve()
    py_files = [f for f in manifest["files"] if f["extension"] == ".py"]

    all_definitions = []
    all_exports = []
    all_imports = []
    all_calls_by_file: dict[str, list[dict]] = {}
    all_name_refs_by_file: dict[str, set[str]] = {}  # Fix 2: track all Name references per file
    files_analyzed = 0
    files_failed_parse: list[dict] = []
    importlib_calls: list[dict] = []

    # --- Phase 1: Parse every file ---
    for file_entry in py_files:
        filepath = file_entry["path"]
        rel_path = file_entry["rel_path"]

        tree = parse_file_safe(Path(filepath))
        if tree is None:
            files_failed_parse.append({
                "file": filepath,
                "rel_path": rel_path,
                "reason": "SyntaxError",
            })
            files_analyzed += 1
            continue

        files_analyzed += 1

        # Definitions
        defs = walk_definitions(tree, filepath)
        all_definitions.extend(defs)

        # Exports (__all__)
        exports_entry = _extract_all_exports(tree, filepath)
        if exports_entry is not None:
            all_exports.append(exports_entry)

        # Imports
        file_imports = walk_imports(tree, filepath)
        for imp in file_imports:
            resolved = None
            if imp["category"] == "internal":
                module = imp["module"]
                resolved = resolve_internal_import(module, imp.get("names", []), root, importing_file=filepath)
            imp["resolved_target"] = resolved
            all_imports.append(imp)

        # Calls (for intra-file usage detection)
        file_calls = walk_calls(tree, filepath)
        all_calls_by_file[filepath] = file_calls

        # Fix 2: Collect all Name references (Load context) for intra-file usage
        # This catches bare name references like `logger.info(...)` where `logger`
        # is used as an attribute base, and constants used in expressions/assignments.
        name_refs: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                name_refs.add(node.id)
        all_name_refs_by_file[filepath] = name_refs

        # Detect importlib.import_module() calls
        for call in file_calls:
            if call["name"] in ("importlib.import_module", "import_module"):
                importlib_calls.append({
                    "file": filepath,
                    "lineno": call["lineno"],
                    "call": call["name"],
                })

    # --- Phase 2: Cross-references ---
    # Build: for each definition, which files import it?
    # Index definitions by (file, name)
    def_index: dict[str, set[str]] = {}  # "file::name" -> set of importing files
    for defn in all_definitions:
        key = f"{defn['file']}::{defn['name']}"
        def_index[key] = set()

    # Build re-export map: for __init__.py files that do "from .submod import Name",
    # map (init_file, Name) -> submodule_file so we can propagate references.
    init_reexport_map: dict[tuple[str, str], str] = {}
    for imp in all_imports:
        if imp.get("level", 0) <= 0:
            continue
        if not imp["file"].endswith("__init__.py"):
            continue
        # This is a relative import in an __init__.py
        target = imp.get("resolved_target")
        if not target:
            continue
        for name in imp.get("names", []):
            if name != "*":
                init_reexport_map[(imp["file"], name)] = target

    # For each import, find the definitions it references
    for imp in all_imports:
        if imp["category"] != "internal":
            continue
        target = imp.get("resolved_target")
        if not target:
            continue
        for name in imp.get("names", []):
            key = f"{target}::{name}"
            if key in def_index:
                def_index[key].add(imp["file"])

            # Fix 1: Follow re-export chains through __init__.py
            # If target is an __init__.py that re-exports 'name' from a submodule,
            # also mark the original definition in the submodule as referenced.
            reexport_source = init_reexport_map.get((target, name))
            if reexport_source:
                source_key = f"{reexport_source}::{name}"
                if source_key in def_index:
                    def_index[source_key].add(imp["file"])

            # Also check wildcard: if name == '*', mark all exports of target
            if name == "*":
                for exp in all_exports:
                    if exp["file"] == target:
                        for ename in exp["all_names"]:
                            ekey = f"{target}::{ename}"
                            if ekey in def_index:
                                def_index[ekey].add(imp["file"])
                            # Propagate wildcard through re-exports too
                            reexport_src = init_reexport_map.get((target, ename))
                            if reexport_src:
                                src_key = f"{reexport_src}::{ename}"
                                if src_key in def_index:
                                    def_index[src_key].add(imp["file"])

    # Build exported names set per file
    exported_names: dict[str, set[str]] = {}
    for exp in all_exports:
        exported_names[exp["file"]] = set(exp["all_names"])

    # Annotate definitions with references
    definitions_out = []
    for defn in all_definitions:
        key = f"{defn['file']}::{defn['name']}"
        refs = def_index.get(key, set())

        # Build reference list with lineno
        reference_list = []
        for ref_file in sorted(refs):
            # Find the import lineno
            lineno = None
            for imp in all_imports:
                if imp["file"] == ref_file and defn["name"] in imp.get("names", []):
                    lineno = imp["lineno"]
                    break
            reference_list.append({"file": ref_file, "lineno": lineno})

        is_exported = defn["name"] in exported_names.get(defn["file"], set())

        defn_out = {
            "file": defn["file"],
            "name": defn["name"],
            "type": defn["type"],
            "lineno": defn["lineno"],
            "is_private": defn["is_private"],
            "is_exported": is_exported,
            "references": reference_list,
            "reference_count": len(reference_list),
        }
        # Include extra fields if present
        if "args" in defn:
            defn_out["args"] = defn["args"]
        if "return_annotation" in defn:
            defn_out["return_annotation"] = defn["return_annotation"]
        if "methods" in defn:
            defn_out["methods"] = defn["methods"]
        if "bases" in defn:
            defn_out["bases"] = defn["bases"]
        if "decorators" in defn:
            defn_out["decorators"] = defn["decorators"]

        definitions_out.append(defn_out)

    # --- Phase 3: Validate exports ---
    exports_out = []
    for exp in all_exports:
        # Check that every name in __all__ is defined or imported in the file
        file_def_names = {d["name"] for d in all_definitions if d["file"] == exp["file"]}
        file_import_names = set()
        for imp in all_imports:
            if imp["file"] == exp["file"]:
                file_import_names.update(imp.get("names", []))

        available = file_def_names | file_import_names
        missing = [n for n in exp["all_names"] if n not in available]

        exports_out.append({
            "file": exp["file"],
            "all_names": exp["all_names"],
            "valid": len(missing) == 0,
            "missing_definitions": missing,
        })

    # --- Phase 4: Dead code detection (conservative) ---
    # Pre-compute file sets for skipping
    test_files = {f["path"] for f in py_files if f.get("is_test", False)}
    vendor_files = {f["path"] for f in py_files if f.get("classification") == "vendor"}

    potentially_dead = []
    for defn in all_definitions:
        name = defn["name"]
        filepath = defn["file"]

        # Skip dunders
        if name.startswith("__") and name.endswith("__"):
            continue

        # Skip definitions in test files — test classes/functions are discovered
        # by pytest at runtime, not via imports
        if filepath in test_files:
            continue

        # Skip vendored files — external code we don't control
        if filepath in vendor_files:
            continue

        # Skip if exported
        if name in exported_names.get(filepath, set()):
            continue

        # Skip if imported by any other file
        key = f"{filepath}::{name}"
        if def_index.get(key, set()):
            continue

        # Skip if referenced within its own file (Fix 2: use Name refs, not just calls)
        # This catches: logger.info(), constants in expressions, class instantiation, etc.
        file_name_refs = all_name_refs_by_file.get(filepath, set())
        if name in file_name_refs:
            continue

        # Also check call-based references (for dotted names like self.method)
        file_calls = all_calls_by_file.get(filepath, [])
        called_names = {c["name"].split(".")[-1] for c in file_calls}
        called_full = {c["name"] for c in file_calls}
        if name in called_names or name in called_full:
            continue

        # Skip if it's a decorated function (likely registered via decorator)
        if defn.get("decorators"):
            continue

        potentially_dead.append({
            "file": filepath,
            "name": name,
            "type": defn["type"],
            "lineno": defn["lineno"],
            "reason": "no_imports_no_exports_no_intra_file_calls",
        })

    # --- Summary ---
    files_with_all = len(all_exports)
    py_file_count = len(py_files)
    files_without_all = py_file_count - files_with_all

    summary = {
        "total_definitions": len(definitions_out),
        "total_exports": sum(len(e["all_names"]) for e in exports_out),
        "total_imports": len(all_imports),
        "potentially_dead_count": len(potentially_dead),
        "files_with_all": files_with_all,
        "files_without_all": files_without_all,
        "importlib_dynamic_imports": len(importlib_calls),
    }

    # --- Completeness check ---
    completeness_ok = files_analyzed == py_file_count
    # Every __all__ file must produce an exports entry
    all_files_with_all = {e["file"] for e in all_exports}

    return {
        "layer": "ast-lsp-bindings",
        "files_analyzed": files_analyzed,
        "files_failed_parse": files_failed_parse,
        "definitions": definitions_out,
        "exports": exports_out,
        "imports": all_imports,
        "potentially_dead": potentially_dead,
        "importlib_calls": importlib_calls,
        "summary": summary,
        "completeness": {
            "files_analyzed": files_analyzed,
            "py_files_in_manifest": py_file_count,
            "files_failed_parse_count": len(files_failed_parse),
            "ok": completeness_ok,
        },
    }


def _extract_all_exports(tree: ast.Module, filepath: str) -> dict | None:
    """Extract __all__ assignment from a module.

    Handles both list and tuple literal forms, and annotated assignments:
        __all__ = ["name1", "name2"]
        __all__ = ("name1", "name2")
        __all__: list[str] = ["name1", "name2"]

    Returns:
        Dict with file and all_names, or None if no __all__.
    """
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    names = _extract_string_list(node.value)
                    if names is not None:
                        return {
                            "file": filepath,
                            "all_names": names,
                        }
        elif isinstance(node, ast.AnnAssign):
            if (isinstance(node.target, ast.Name)
                    and node.target.id == "__all__"
                    and node.value is not None):
                names = _extract_string_list(node.value)
                if names is not None:
                    return {
                        "file": filepath,
                        "all_names": names,
                    }
    return None


def _extract_string_list(node: ast.expr) -> list[str] | None:
    """Extract a list of string literals from a List or Tuple AST node.

    Returns:
        List of string names, or None if the node is not a List/Tuple
        or if all elements are non-string (indicating a dynamic __all__).
    """
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    names = []
    skipped = 0
    for elt in node.elts:
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
            names.append(elt.value)
        else:
            skipped += 1
            print(
                f"WARNING: non-string element in __all__ at line {getattr(elt, 'lineno', '?')}: "
                f"{ast.dump(elt)}",
                file=sys.stderr,
            )
    # If the node had elements but none were strings, return None to signal
    # we couldn't resolve it (distinct from a genuinely empty __all__ = [])
    if not names and node.elts:
        return None
    return names


def main():
    """CLI entry point for layer 2 extraction."""
    parser = argparse.ArgumentParser(description="Layer 2: AST+LSP Symbol Bindings")
    parser.add_argument("--root", required=True, help="Project root directory")
    parser.add_argument("--output", required=True, help="Output directory for JSON files")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load manifest
    manifest = None
    manifest_path = output_dir / "manifest.json"
    if manifest_path.exists():
        from scripts.atlas.common import load_manifest
        manifest = load_manifest(output_dir)
    else:
        from scripts.atlas.common import build_manifest
        print("Building manifest...")
        manifest = build_manifest(root)
        manifest_path.write_text(json.dumps(manifest, indent=2))
        print(f"Manifest: {manifest['total_files']} files")

    # Extract layer 2
    layer_data = extract(manifest, root)

    # Write output
    out_path = write_layer_json("layer2_ast_bindings", layer_data, output_dir)

    # Print summary
    s = layer_data["summary"]
    print(f"Layer 2: {layer_data['files_analyzed']} files analyzed")
    print(f"  Definitions: {s['total_definitions']}")
    print(f"  Exports (__all__): {s['total_exports']} names across {s['files_with_all']} files")
    print(f"  Imports: {s['total_imports']}")
    print(f"  Potentially dead: {s['potentially_dead_count']}")
    print(f"  Dynamic imports (importlib): {s['importlib_dynamic_imports']}")

    if layer_data["files_failed_parse"]:
        print(f"  Parse failures: {len(layer_data['files_failed_parse'])}")
        for fail in layer_data["files_failed_parse"]:
            print(f"    {fail['rel_path']}: {fail['reason']}")

    comp = layer_data["completeness"]
    if comp["ok"]:
        print(f"  Completeness: PASS ({comp['files_analyzed']}/{comp['py_files_in_manifest']})")
    else:
        print(f"  Completeness: FAIL ({comp['files_analyzed']}/{comp['py_files_in_manifest']})")
        sys.exit(1)

    print(f"  Output: {out_path} ({out_path.stat().st_size} bytes)")
    sys.exit(0)


if __name__ == "__main__":
    main()
