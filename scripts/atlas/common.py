"""Common utilities for code atlas extraction.

Shared foundation for all atlas layers: file discovery via git, AST helpers,
JSON I/O, and import classification.

Public API:
    build_manifest: Build canonical file manifest using git ls-files
    load_manifest: Load manifest.json from output directory
    parse_file_safe: Parse Python file safely (None on SyntaxError)
    walk_definitions: Extract top-level and class-level definitions
    walk_imports: Extract and classify all import statements
    walk_calls: Extract all function/method calls from AST
    resolve_internal_import: Resolve module path to file path
    write_layer_json: Write layer JSON with metadata
    load_layer_json: Load a previously generated layer JSON
    get_stdlib_modules: Return set of stdlib module names
"""

import ast
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

__all__ = [
    "build_manifest",
    "load_manifest",
    "parse_file_safe",
    "walk_definitions",
    "walk_imports",
    "walk_calls",
    "resolve_internal_import",
    "write_layer_json",
    "load_layer_json",
    "get_stdlib_modules",
    "_resolve_call_name",
    "_find_enclosing_function",
]


def get_stdlib_modules() -> set[str]:
    """Return set of stdlib module names for import classification.

    Uses sys.stdlib_module_names (Python 3.10+).
    """
    return set(sys.stdlib_module_names)


def build_manifest(root: Path) -> dict:
    """Build canonical file manifest using git ls-files.

    Uses ``git ls-files --cached --others --exclude-standard`` for correctness.
    Classifies each file by extension, counts lines, identifies packages.

    Args:
        root: Root directory to scan (e.g. src/amplihack).

    Returns:
        Manifest dict matching the schema in SPEC.md.
    """
    root = root.resolve()

    # Get git commit hash
    git_commit = _git_commit(root)

    # Get authoritative file list from git
    raw_paths = _git_ls_files(root)

    files = []
    by_extension: dict[str, int] = {}
    by_classification: dict[str, int] = {}
    packages: set[str] = set()

    for rel in sorted(raw_paths):
        filepath = root / rel
        if not filepath.is_file():
            continue

        ext = filepath.suffix
        size_bytes = filepath.stat().st_size
        line_count = _count_lines(filepath)

        is_test = _is_test_file(rel)
        is_init = filepath.name == "__init__.py"

        # Determine package from parent dir relative to root
        parent_rel = str(Path(rel).parent)
        package = parent_rel.replace("/", ".") if parent_rel != "." else root.name

        classification = _classify_py_file(rel, ext, is_test, is_init)

        # Track packages (dirs with __init__.py)
        if is_init:
            pkg_path = str(Path(rel).parent)
            if pkg_path == ".":
                packages.add(root.name)
            else:
                packages.add(pkg_path.replace("/", "."))

        entry = {
            "path": str(root / rel),
            "rel_path": rel,
            "extension": ext,
            "size_bytes": size_bytes,
            "line_count": line_count,
            "is_test": is_test,
            "is_init": is_init,
            "package": package,
            "classification": classification,
        }
        files.append(entry)

        by_extension[ext] = by_extension.get(ext, 0) + 1
        by_classification[classification] = by_classification.get(classification, 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "git_commit": git_commit,
        "total_files": len(files),
        "files": files,
        "summary": {
            "by_extension": dict(sorted(by_extension.items())),
            "by_classification": dict(sorted(by_classification.items())),
            "packages": sorted(packages),
        },
    }


def load_manifest(output_dir: Path) -> dict:
    """Load manifest.json from output directory.

    Raises:
        FileNotFoundError: If manifest.json does not exist.
        json.JSONDecodeError: If manifest.json is invalid JSON.
    """
    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found in {output_dir}")
    return json.loads(manifest_path.read_text())


def parse_file_safe(path: Path) -> ast.Module | None:
    """Parse Python file, return None on SyntaxError (log to stderr).

    Args:
        path: Absolute path to .py file.

    Returns:
        Parsed AST module, or None if parsing fails.
    """
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        return ast.parse(source, filename=str(path))
    except SyntaxError as e:
        print(f"SyntaxError parsing {path}: {e}", file=sys.stderr)
        return None


def walk_definitions(tree: ast.Module, filepath: str) -> list[dict]:
    """Extract all top-level and class-level definitions.

    Extracts FunctionDef, AsyncFunctionDef, ClassDef, and module-level Assign
    nodes with simple name targets.

    Args:
        tree: Parsed AST module.
        filepath: File path for context in output records.

    Returns:
        List of definition dicts with name, type, lineno, is_private, decorators,
        and additional fields for classes (methods, bases) and functions (args,
        return_annotation).
    """
    defs = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.append(_extract_function_def(node, filepath))
        elif isinstance(node, ast.ClassDef):
            defs.append(_extract_class_def(node, filepath))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defs.append({
                        "file": filepath,
                        "name": target.id,
                        "type": "constant",
                        "lineno": node.lineno,
                        "is_private": target.id.startswith("_"),
                        "decorators": [],
                    })

    return defs


def walk_imports(tree: ast.Module, filepath: str) -> list[dict]:
    """Extract all import statements and classify them.

    Classification:
        - stdlib: module is in sys.stdlib_module_names
        - internal: starts with '.' (relative) or 'amplihack'
        - third_party: everything else

    Args:
        tree: Parsed AST module.
        filepath: File path for context.

    Returns:
        List of import dicts with module, names, category, lineno, is_conditional.
    """
    stdlib = get_stdlib_modules()
    imports = []
    try_cache: dict[int, set[int]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_module = alias.name.split(".")[0]
                category = _classify_import(alias.name, top_module, stdlib)
                is_conditional = _is_inside_try(tree, node, _cache=try_cache)
                imports.append({
                    "file": filepath,
                    "module": alias.name,
                    "names": [alias.asname or alias.name.split(".")[-1]],
                    "alias": alias.asname,
                    "category": category,
                    "lineno": node.lineno,
                    "is_conditional": is_conditional,
                })

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            level = node.level or 0

            if level > 0:
                category = "internal"
            else:
                top_module = module.split(".")[0] if module else ""
                category = _classify_import(module, top_module, stdlib)

            names = [alias.name for alias in node.names] if node.names else []
            is_conditional = _is_inside_try(tree, node, _cache=try_cache)

            imports.append({
                "file": filepath,
                "module": ("." * level + module) if level > 0 else module,
                "names": names,
                "alias": None,
                "category": category,
                "lineno": node.lineno,
                "is_conditional": is_conditional,
                "level": level,
            })

    return imports


def walk_calls(tree: ast.Module, filepath: str) -> list[dict]:
    """Extract all function/method calls from AST.

    Args:
        tree: Parsed AST module.
        filepath: File path for context.

    Returns:
        List of call dicts with name, lineno, and context.
    """
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = _resolve_call_name(node.func)
            if call_name:
                calls.append({
                    "file": filepath,
                    "name": call_name,
                    "lineno": node.lineno,
                })
    return calls


def resolve_internal_import(module: str, names: list[str], root: Path) -> str | None:
    """Resolve 'amplihack.foo.bar' to relative file path.

    Handles both module imports (amplihack.foo -> amplihack/foo.py or
    amplihack/foo/__init__.py) and relative imports.

    Args:
        module: Module string (e.g. 'amplihack.foo.bar').
        names: Imported names (unused for path resolution but kept for API).
        root: Project root directory.

    Returns:
        Resolved file path relative to root, or None if not resolvable.
    """
    if not module:
        return None

    # Strip leading dots for relative imports
    clean = module.lstrip(".")
    if not clean:
        return None

    # Convert dotted module to path
    parts = clean.split(".")

    # Try as direct .py file
    candidate = root / Path(*parts).with_suffix(".py")
    if candidate.exists():
        return str(candidate)

    # Try as package __init__.py
    candidate = root / Path(*parts) / "__init__.py"
    if candidate.exists():
        return str(candidate)

    return None


def write_layer_json(layer_name: str, data: dict, output_dir: Path) -> Path:
    """Write layer JSON with timestamp and meta.

    Args:
        layer_name: Layer identifier (e.g. 'layer1_repo_surface').
        data: Layer data dict.
        output_dir: Output directory.

    Returns:
        Path to written file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{layer_name}.json"

    envelope = {
        "meta": {
            "layer": layer_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        **data,
    }

    output_path.write_text(json.dumps(envelope, indent=2, default=str))
    return output_path


def load_layer_json(layer_name: str, output_dir: Path) -> dict:
    """Load a previously generated layer JSON.

    Args:
        layer_name: Layer identifier.
        output_dir: Output directory.

    Returns:
        Parsed JSON dict.

    Raises:
        FileNotFoundError: If layer file does not exist.
    """
    path = output_dir / f"{layer_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"{layer_name}.json not found in {output_dir}")
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _git_commit(root: Path) -> str:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        print(
            f"WARNING: git rev-parse HEAD failed (exit {result.returncode}), "
            f"using 'unknown': {result.stderr.strip()}",
            file=sys.stderr,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(
            f"WARNING: git rev-parse HEAD failed ({e}), using 'unknown'",
            file=sys.stderr,
        )
    return "unknown"


def _git_ls_files(root: Path) -> list[str]:
    """Get file list from git ls-files."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        cwd=root,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git ls-files failed (exit {result.returncode}): {result.stderr}"
        )
    return [line for line in result.stdout.splitlines() if line.strip()]


def _count_lines(filepath: Path) -> int:
    """Count lines in a file."""
    try:
        return len(filepath.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError as e:
        print(f"WARNING: could not read {filepath} for line count: {e}", file=sys.stderr)
        return 0


def _is_test_file(rel_path: str) -> bool:
    """Check if a file is a test file."""
    parts = Path(rel_path).parts
    name = Path(rel_path).name
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or "tests" in parts
        or "test" in parts
    )


def _classify_py_file(rel_path: str, ext: str, is_test: bool, is_init: bool) -> str:
    """Classify a file by its role."""
    if ext != ".py":
        return "non_python"
    if is_test:
        return "test"
    if is_init:
        return "init"
    if "vendor" in Path(rel_path).parts:
        return "vendor"
    return "source"


def _classify_import(module: str, top_module: str, stdlib: set[str]) -> str:
    """Classify an import as stdlib, internal, or third_party."""
    if not module:
        return "third_party"
    if top_module == "amplihack":
        return "internal"
    if top_module in stdlib:
        return "stdlib"
    return "third_party"


def _build_try_node_ids(tree: ast.Module) -> set[int]:
    """Pre-compute the set of node ids that are inside Try blocks."""
    inside_try: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for child in ast.walk(node):
                inside_try.add(id(child))
    return inside_try


def _is_inside_try(tree: ast.Module, target_node: ast.AST, _cache: dict[int, set[int]] | None = None) -> bool:
    """Check if a node is inside a Try block (conditional import).

    Uses pre-computed set when available via _cache, keyed by id(tree).
    """
    if _cache is not None:
        tree_id = id(tree)
        if tree_id not in _cache:
            _cache[tree_id] = _build_try_node_ids(tree)
        return id(target_node) in _cache[tree_id]
    # Fallback: single-pass build (still O(n) per call but avoids repeated walks)
    return id(target_node) in _build_try_node_ids(tree)


def _resolve_call_name(func_node: ast.expr) -> str | None:
    """Resolve call target to a string name.

    Handles Name, Attribute chains, and Subscript (e.g. os.environ["X"]).
    """
    if isinstance(func_node, ast.Name):
        return func_node.id
    elif isinstance(func_node, ast.Attribute):
        value_name = _resolve_call_name(func_node.value)
        if value_name:
            return f"{value_name}.{func_node.attr}"
        return func_node.attr
    elif isinstance(func_node, ast.Subscript):
        return _resolve_call_name(func_node.value)
    return None


def _find_enclosing_function(tree: ast.Module, target_lineno: int) -> str | None:
    """Find the function name enclosing a given line number."""
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_lineno = getattr(node, "end_lineno", None)
            if end_lineno and node.lineno <= target_lineno <= end_lineno:
                if best is None or node.lineno > best[1]:
                    best = (node.name, node.lineno)
    return best[0] if best else None


def _extract_function_def(node: ast.FunctionDef | ast.AsyncFunctionDef, filepath: str) -> dict:
    """Extract function definition metadata."""
    decorators = []
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            decorators.append(dec.id)
        elif isinstance(dec, ast.Attribute):
            name = _resolve_call_name(dec)
            if name:
                decorators.append(name)
        elif isinstance(dec, ast.Call):
            name = _resolve_call_name(dec.func)
            if name:
                decorators.append(name)

    args = [arg.arg for arg in node.args.args]

    return_annotation = None
    if node.returns:
        try:
            return_annotation = ast.unparse(node.returns)
        except Exception as e:
            print(f"WARNING: ast.unparse failed in {filepath}: {e}", file=sys.stderr)

    return {
        "file": filepath,
        "name": node.name,
        "type": "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
        "lineno": node.lineno,
        "is_private": node.name.startswith("_"),
        "decorators": decorators,
        "args": args,
        "return_annotation": return_annotation,
    }


def _extract_class_def(node: ast.ClassDef, filepath: str) -> dict:
    """Extract class definition metadata."""
    decorators = []
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            decorators.append(dec.id)
        elif isinstance(dec, ast.Attribute):
            name = _resolve_call_name(dec)
            if name:
                decorators.append(name)
        elif isinstance(dec, ast.Call):
            name = _resolve_call_name(dec.func)
            if name:
                decorators.append(name)

    methods = []
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(child.name)

    bases = []
    for base in node.bases:
        try:
            bases.append(ast.unparse(base))
        except Exception as e:
            print(f"WARNING: ast.unparse failed in {filepath}: {e}", file=sys.stderr)

    return {
        "file": filepath,
        "name": node.name,
        "type": "class",
        "lineno": node.lineno,
        "is_private": node.name.startswith("_"),
        "decorators": decorators,
        "methods": methods,
        "bases": bases,
    }
