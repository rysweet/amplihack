"""Layer 1: Repository Surface -- exhaustive directory tree.

Enumerates ALL directories and files from the manifest, classifies directory
roles, and finds entry points from pyproject.toml.
"""

import argparse
import json
import sys
from pathlib import Path

# Allow running as script from repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
from scripts.atlas.common import build_manifest, load_manifest, write_layer_json


def extract(manifest: dict, root: Path) -> dict:
    """Extract layer 1 data from manifest.

    Groups files by directory, classifies directory roles, finds entry points,
    and performs a completeness self-check.

    Args:
        manifest: Loaded manifest dict.
        root: Project root directory.

    Returns:
        Layer 1 data dict matching the spec schema.
    """
    root = root.resolve()
    files = manifest["files"]

    # Group files by directory
    dir_files: dict[str, list[dict]] = {}
    for f in files:
        parent = str(Path(f["rel_path"]).parent)
        if parent == ".":
            parent = "."
        dir_files.setdefault(parent, []).append(f)

    # Build directory entries
    directories = []
    for dir_path, dir_file_list in sorted(dir_files.items()):
        abs_dir = str(root / dir_path) if dir_path != "." else str(root)
        depth = 0 if dir_path == "." else dir_path.count("/") + 1
        parent_dir = str(Path(dir_path).parent) if dir_path != "." else None
        if parent_dir == ".":
            parent_dir = str(root)
        elif parent_dir is not None:
            parent_dir = str(root / parent_dir)

        py_count = sum(1 for f in dir_file_list if f["extension"] == ".py")
        test_count = sum(1 for f in dir_file_list if f.get("is_test", False))
        init_count = sum(1 for f in dir_file_list if f.get("is_init", False))

        role = _classify_dir_role(dir_path, dir_file_list)

        directories.append({
            "path": abs_dir,
            "rel_path": dir_path,
            "depth": depth,
            "role": role,
            "parent": parent_dir,
            "file_counts": {
                "total": len(dir_file_list),
                "python": py_count,
                "test": test_count,
                "init": init_count,
            },
        })

    # Find entry points from pyproject.toml
    entry_points = _find_entry_points(root)

    # Find __main__.py files
    for f in files:
        if Path(f["rel_path"]).name == "__main__.py":
            entry_points.append({
                "type": "__main__",
                "path": f["path"],
            })

    # Non-python assets
    non_python = []
    for f in files:
        if f["extension"] != ".py":
            asset_type = f["extension"].lstrip(".")
            if not asset_type:
                asset_type = "unknown"
            non_python.append({
                "path": f["path"],
                "type": asset_type,
            })

    # Completeness self-check
    file_count_sum = sum(d["file_counts"]["total"] for d in directories)
    completeness_ok = file_count_sum == manifest["total_files"]

    return {
        "layer": "repo-surface",
        "directories": directories,
        "entry_points": entry_points,
        "non_python_assets": non_python,
        "completeness": {
            "directory_file_sum": file_count_sum,
            "manifest_total": manifest["total_files"],
            "ok": completeness_ok,
        },
    }


def _classify_dir_role(dir_path: str, dir_files: list[dict]) -> str:
    """Classify a directory's role based on name and contents."""
    parts = Path(dir_path).parts if dir_path != "." else ()
    name = parts[-1] if parts else ""

    if name in ("tests", "test"):
        return "tests"
    if name == "vendor" or "vendor" in parts:
        return "vendor"

    extensions = {f["extension"] for f in dir_files}
    has_init = any(f.get("is_init", False) for f in dir_files)

    config_exts = {".toml", ".cfg", ".ini", ".yaml", ".yml"}
    doc_exts = {".md", ".rst", ".txt"}

    if has_init:
        return "package"

    if extensions & config_exts and not (extensions & {".py"}):
        return "config"
    if extensions & doc_exts and not (extensions & {".py"}):
        return "docs"

    return "other"


def _find_entry_points(root: Path) -> list[dict]:
    """Find entry points from pyproject.toml [project.scripts]."""
    entry_points = []

    # Check pyproject.toml - could be in root or parent dirs
    for candidate in [root / "pyproject.toml", root.parent / "pyproject.toml",
                      root.parent.parent / "pyproject.toml"]:
        if candidate.exists():
            try:
                # Use tomllib (3.11+) or tomli
                try:
                    import tomllib
                except ImportError:
                    import tomli as tomllib

                with open(candidate, "rb") as f:
                    data = tomllib.load(f)

                scripts = data.get("project", {}).get("scripts", {})
                for name, target in scripts.items():
                    entry_points.append({
                        "type": "console_script",
                        "name": name,
                        "target": target,
                        "source": str(candidate),
                    })

                if scripts:
                    break  # Found scripts, stop searching
            except Exception as e:
                print(f"Warning: failed to parse {candidate}: {e}", file=sys.stderr)

    return entry_points


def main():
    """CLI entry point for layer 1 extraction."""
    parser = argparse.ArgumentParser(description="Layer 1: Repository Surface")
    parser.add_argument("--root", required=True, help="Project root directory")
    parser.add_argument("--output", required=True, help="Output directory for JSON files")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build or load manifest
    manifest_path = output_dir / "manifest.json"
    if manifest_path.exists():
        manifest = load_manifest(output_dir)
    else:
        print("Building manifest...")
        manifest = build_manifest(root)
        manifest_path.write_text(json.dumps(manifest, indent=2))
        print(f"Manifest: {manifest['total_files']} files")

    # Extract layer 1
    layer_data = extract(manifest, root)

    # Write output
    out_path = write_layer_json("layer1_repo_surface", layer_data, output_dir)

    # Print summary
    dirs = layer_data["directories"]
    print(f"Layer 1: {len(dirs)} directories, "
          f"{len(layer_data['entry_points'])} entry points, "
          f"{len(layer_data['non_python_assets'])} non-python assets")

    roles = {}
    for d in dirs:
        roles[d["role"]] = roles.get(d["role"], 0) + 1
    print(f"  Roles: {json.dumps(roles)}")

    completeness = layer_data["completeness"]
    if completeness["ok"]:
        print(f"  Completeness: PASS ({completeness['directory_file_sum']}/{completeness['manifest_total']})")
    else:
        print(f"  Completeness: FAIL ({completeness['directory_file_sum']}/{completeness['manifest_total']})")
        sys.exit(1)

    print(f"  Output: {out_path} ({out_path.stat().st_size} bytes)")
    sys.exit(0)


if __name__ == "__main__":
    main()
