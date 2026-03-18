"""Layer 6: Data Flow -- file I/O, database ops, network I/O, transformation points.

Walks AST for all data ingress/egress: file reads/writes, database operations,
network calls. Identifies transformation points (functions that both read AND write).
"""

import argparse
import ast
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
from scripts.atlas.common import (
    _find_enclosing_function,
    _resolve_call_name,
    load_manifest,
    parse_file_safe,
    write_layer_json,
)

# File I/O patterns: (call pattern, operation, format)
_FILE_READ_PATTERNS = {
    "open": "read",  # operation depends on mode arg
    "Path.read_text": "read",
    "Path.read_bytes": "read",
    "json.load": "read",
    "json.loads": "read",
    "yaml.safe_load": "read",
    "yaml.load": "read",
    "csv.reader": "read",
    "toml.load": "read",
    "tomllib.load": "read",
    "tomli.load": "read",
}

_FILE_WRITE_PATTERNS = {
    "Path.write_text": "write",
    "Path.write_bytes": "write",
    "json.dump": "write",
    "json.dumps": "write",
    "yaml.dump": "write",
    "yaml.safe_dump": "write",
    "csv.writer": "write",
    "shutil.copy": "write",
    "shutil.copy2": "write",
    "shutil.copytree": "write",
    "shutil.move": "write",
}

# Database patterns
_DB_PATTERNS = {
    # kuzu
    "conn.execute": ("kuzu", None),
    "connection.execute": ("kuzu", None),
    "kuzu.Database": ("kuzu", "schema"),
    "kuzu.Connection": ("kuzu", "schema"),
    # sqlite
    "sqlite3.connect": ("sqlite", "schema"),
    "cursor.execute": ("sqlite", None),
    "conn.execute": ("sqlite", None),
    # neo4j
    "driver.session": ("neo4j", "schema"),
    "session.run": ("neo4j", None),
    "tx.run": ("neo4j", None),
    # falkordb
    "falkordb.FalkorDB": ("falkordb", "schema"),
}

# Network I/O patterns
_NETWORK_PATTERNS = {
    "requests.get": "GET",
    "requests.post": "POST",
    "requests.put": "PUT",
    "requests.delete": "DELETE",
    "requests.patch": "PATCH",
    "requests.head": "HEAD",
    "requests.options": "OPTIONS",
    "aiohttp.ClientSession": "SESSION",
    "urllib.request.urlopen": "GET",
    "httpx.get": "GET",
    "httpx.post": "POST",
    "httpx.AsyncClient": "SESSION",
}


def _get_string_arg(node: ast.Call, pos: int = 0) -> str | None:
    """Extract a string argument from a call by position."""
    if pos < len(node.args) and isinstance(node.args[pos], ast.Constant):
        val = node.args[pos].value
        if isinstance(val, str):
            return val
    return None


def _match_pattern(call_name: str, patterns: dict) -> str | None:
    """Check if call_name matches any pattern. Returns the matched pattern key."""
    # Exact match
    if call_name in patterns:
        return call_name

    # Suffix match (e.g., "self.conn.execute" matches "conn.execute")
    parts = call_name.split(".")
    for n in range(1, len(parts) + 1):
        suffix = ".".join(parts[-n:])
        if suffix in patterns:
            return suffix

    return None


def _infer_format(call_name: str) -> str:
    """Infer the file format from the call name."""
    if "json" in call_name.lower():
        return "json"
    if "yaml" in call_name.lower():
        return "yaml"
    if "csv" in call_name.lower():
        return "csv"
    if "toml" in call_name.lower():
        return "toml"
    if "bytes" in call_name.lower():
        return "binary"
    return "text"


def _determine_open_mode(node: ast.Call) -> str:
    """Determine if an open() call is read or write from mode arg."""
    # Check second positional arg
    if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
        mode = str(node.args[1].value)
        if any(c in mode for c in "wax"):
            return "write"
        return "read"

    # Check 'mode' keyword
    for kw in node.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            mode = str(kw.value.value)
            if any(c in mode for c in "wax"):
                return "write"
            return "read"

    return "read"  # default


def _extract_file_io(tree: ast.Module, filepath: str) -> list[dict]:
    """Extract all file I/O operations from AST."""
    io_ops = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        call_name = _resolve_call_name(node.func)
        if not call_name:
            continue

        # Check read patterns
        matched = _match_pattern(call_name, _FILE_READ_PATTERNS)
        if matched:
            operation = "read"
            if matched == "open" or call_name.endswith(".open") or call_name == "open":
                operation = _determine_open_mode(node)

            target_path = _get_string_arg(node, 0)
            func_ctx = _find_enclosing_function(tree, node.lineno)
            fmt = _infer_format(call_name)
            if matched == "open" and operation == "read":
                fmt = "text"  # generic open

            io_ops.append({
                "file": filepath,
                "lineno": node.lineno,
                "operation": operation,
                "format": fmt,
                "target_path": target_path,
                "function_context": func_ctx,
                "call": call_name,
            })
            continue

        # Check write patterns
        matched = _match_pattern(call_name, _FILE_WRITE_PATTERNS)
        if matched:
            target_path = _get_string_arg(node, 0)
            func_ctx = _find_enclosing_function(tree, node.lineno)
            fmt = _infer_format(call_name)

            io_ops.append({
                "file": filepath,
                "lineno": node.lineno,
                "operation": "write",
                "format": fmt,
                "target_path": target_path,
                "function_context": func_ctx,
                "call": call_name,
            })

    return io_ops


def _extract_database_ops(tree: ast.Module, filepath: str) -> list[dict]:
    """Extract database operations from AST."""
    ops = []
    # Local set for dynamically-discovered DB call names (avoids mutating module-level dict)
    dynamic_db_patterns: dict[str, tuple[str, str | None]] = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        call_name = _resolve_call_name(node.func)
        if not call_name:
            continue

        matched = _match_pattern(call_name, _DB_PATTERNS)
        if not matched:
            matched = _match_pattern(call_name, dynamic_db_patterns)
        if not matched:
            # Check for kuzu/sqlite/neo4j/falkordb in call name directly
            call_lower = call_name.lower()
            if "kuzu" in call_lower:
                matched = call_name
                dynamic_db_patterns[call_name] = ("kuzu", None)
            elif "sqlite" in call_lower:
                matched = call_name
                dynamic_db_patterns[call_name] = ("sqlite", None)
            elif "neo4j" in call_lower:
                matched = call_name
                dynamic_db_patterns[call_name] = ("neo4j", None)
            elif "falkordb" in call_lower:
                matched = call_name
                dynamic_db_patterns[call_name] = ("falkordb", None)

        if not matched:
            continue

        db_type, op_type = _DB_PATTERNS.get(matched, dynamic_db_patterns.get(matched, ("unknown", None)))

        # Try to determine operation from query literal
        query_literal = _get_string_arg(node, 0)
        if op_type is None and query_literal:
            q_upper = query_literal.strip().upper()
            if q_upper.startswith(("SELECT", "MATCH", "RETURN")):
                op_type = "read"
            elif q_upper.startswith(("INSERT", "CREATE", "UPDATE", "DELETE", "DROP", "ALTER", "MERGE")):
                op_type = "write"
            else:
                op_type = "unknown"
        elif op_type is None:
            op_type = "unknown"

        func_ctx = _find_enclosing_function(tree, node.lineno)

        ops.append({
            "file": filepath,
            "lineno": node.lineno,
            "db_type": db_type,
            "operation": op_type,
            "query_literal": query_literal,
            "function_context": func_ctx,
            "call": call_name,
        })

    return ops


def _extract_network_io(tree: ast.Module, filepath: str) -> list[dict]:
    """Extract network I/O calls from AST."""
    ops = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        call_name = _resolve_call_name(node.func)
        if not call_name:
            continue

        matched = _match_pattern(call_name, _NETWORK_PATTERNS)
        if not matched:
            continue

        method = _NETWORK_PATTERNS[matched]
        url_pattern = _get_string_arg(node, 0)
        if not url_pattern:
            url_pattern = "dynamic"
        func_ctx = _find_enclosing_function(tree, node.lineno)

        ops.append({
            "file": filepath,
            "lineno": node.lineno,
            "method": method,
            "url_pattern": url_pattern,
            "function_context": func_ctx,
            "call": call_name,
        })

    return ops


def _find_transformation_points(
    file_io: list[dict],
    database_ops: list[dict],
    network_io: list[dict],
) -> list[dict]:
    """Identify functions that both read AND write data."""
    # Group all operations by (file, function_context)
    func_ops: dict[tuple[str, str], dict[str, list]] = {}

    for op in file_io:
        key = (op["file"], op.get("function_context") or "<module>")
        func_ops.setdefault(key, {"reads": [], "writes": []})
        if op["operation"] == "read":
            func_ops[key]["reads"].append(f"{op['format']} file")
        else:
            func_ops[key]["writes"].append(f"{op['format']} file")

    for op in database_ops:
        key = (op["file"], op.get("function_context") or "<module>")
        func_ops.setdefault(key, {"reads": [], "writes": []})
        if op["operation"] == "read":
            func_ops[key]["reads"].append(f"{op['db_type']} database")
        elif op["operation"] == "write":
            func_ops[key]["writes"].append(f"{op['db_type']} database")

    for op in network_io:
        key = (op["file"], op.get("function_context") or "<module>")
        func_ops.setdefault(key, {"reads": [], "writes": []})
        if op["method"] in ("GET", "HEAD", "OPTIONS", "SESSION"):
            func_ops[key]["reads"].append(f"network {op['method']}")
        else:
            func_ops[key]["writes"].append(f"network {op['method']}")

    # Functions with both reads and writes are transformation points
    transforms = []
    for (filepath, func_name), ops in sorted(func_ops.items()):
        if ops["reads"] and ops["writes"]:
            # Deduplicate
            reads = sorted(set(ops["reads"]))
            writes = sorted(set(ops["writes"]))
            transforms.append({
                "file": filepath,
                "function": func_name,
                "reads": reads,
                "writes": writes,
            })

    return transforms


def extract(manifest: dict) -> dict:
    """Extract layer 6 data flow information.

    Args:
        manifest: Loaded manifest.json.

    Returns:
        Layer 6 data dict.
    """
    py_files = [f for f in manifest["files"] if f["extension"] == ".py"]

    all_file_io: list[dict] = []
    all_database_ops: list[dict] = []
    all_network_io: list[dict] = []
    files_with_io: set[str] = set()

    for finfo in py_files:
        filepath = finfo["path"]
        tree = parse_file_safe(Path(filepath))
        if tree is None:
            continue

        fio = _extract_file_io(tree, filepath)
        if fio:
            all_file_io.extend(fio)
            files_with_io.add(filepath)

        dbo = _extract_database_ops(tree, filepath)
        if dbo:
            all_database_ops.extend(dbo)
            files_with_io.add(filepath)

        nio = _extract_network_io(tree, filepath)
        if nio:
            all_network_io.extend(nio)
            files_with_io.add(filepath)

    transforms = _find_transformation_points(
        all_file_io, all_database_ops, all_network_io
    )

    return {
        "layer": "data-flow",
        "file_io": all_file_io,
        "database_ops": all_database_ops,
        "network_io": all_network_io,
        "transformation_points": transforms,
        "summary": {
            "file_io_count": len(all_file_io),
            "database_op_count": len(all_database_ops),
            "network_io_count": len(all_network_io),
            "transformation_point_count": len(transforms),
            "files_with_io": len(files_with_io),
        },
    }


def self_check(data: dict, manifest: dict) -> list[str]:
    """Completeness self-check for layer 6."""
    issues = []

    # Verify no file_io entries are missing operation
    for op in data.get("file_io", []):
        if not op.get("operation"):
            issues.append(f"file_io without operation at {op['file']}:{op['lineno']}")

    # Verify no database_ops are missing db_type
    for op in data.get("database_ops", []):
        if not op.get("db_type"):
            issues.append(f"database_op without db_type at {op['file']}:{op['lineno']}")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Layer 6: Data Flow")
    parser.add_argument("--root", required=True, help="Project source root")
    parser.add_argument("--output", required=True, help="Output directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output = Path(args.output).resolve()

    manifest = load_manifest(output)
    data = extract(manifest)
    issues = self_check(data, manifest)

    out_path = write_layer_json("layer6_data_flow", data, output)

    s = data["summary"]
    print(f"Layer 6: data-flow")
    print(f"  File I/O ops:          {s['file_io_count']}")
    print(f"  Database ops:          {s['database_op_count']}")
    print(f"  Network I/O ops:       {s['network_io_count']}")
    print(f"  Transformation points: {s['transformation_point_count']}")
    print(f"  Files with I/O:        {s['files_with_io']}")
    if issues:
        print(f"  ISSUES: {len(issues)}")
        for issue in issues:
            print(f"    - {issue}")
    print(f"  Output: {out_path} ({out_path.stat().st_size:,} bytes)")

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
