"""Layer 4: Runtime Topology -- subprocess calls, ports, Docker, env vars.

Walks AST for subprocess/os calls, socket/port bindings, Docker config parsing,
and environment variable reads. Produces a complete runtime interaction map.
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
    find_repo_root,
    load_manifest,
    parse_file_safe,
    write_layer_json,
)

# Subprocess call patterns (attribute chains to match)
_SUBPROCESS_PATTERNS = {
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.check_output",
    "subprocess.check_call",
    "os.system",
    "os.popen",
    "os.execvp",
    "os.execvpe",
    "os.execv",
    "os.execve",
    "os.execlp",
    "os.execlpe",
    "os.execl",
    "os.execle",
}

# Port/server patterns
_SERVER_PATTERNS = {
    "uvicorn.run",
    "app.run",
    "socket.bind",
    "socket.connect",
    "socket.listen",
}

# Env var read patterns
_ENV_PATTERNS = {
    "os.environ.get",
    "os.getenv",
}


def _extract_literal(node: ast.expr) -> str | list | None:
    """Try to extract a literal string or list of strings from an AST node."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.List):
        elements = []
        for elt in node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                elements.append(elt.value)
            else:
                elements.append("<dynamic>")
        return elements
    if isinstance(node, ast.JoinedStr):
        # f-string: try to extract static parts
        parts = []
        for val in node.values:
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                parts.append(val.value)
            else:
                parts.append("{...}")
        return "".join(parts)
    return None


def _extract_subprocess_calls(tree: ast.Module, filepath: str) -> list[dict]:
    """Extract all subprocess/os.system/os.exec* calls."""
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _resolve_call_name(node.func)
        if not call_name:
            continue

        # Check direct match
        matched = None
        for pattern in _SUBPROCESS_PATTERNS:
            if call_name == pattern:
                matched = pattern
                break
            # Match fully-qualified call names like `module.os.system`
            # by verifying the full pattern (e.g. "os.system") appears at the end
            if call_name.endswith("." + pattern):
                matched = pattern
                break

        # Also check for bare function name matches (e.g., after `from subprocess import run`)
        if not matched:
            bare = call_name.split(".")[-1]
            # Only match bare names when the call has no module qualifier
            # (i.e. it was imported directly: `from subprocess import run`)
            # or the qualifier matches the expected module.
            # Skip bare matching for names that collide with stdlib
            # (e.g. `system` can be platform.system, not just os.system).
            if "." not in call_name:
                for pattern in _SUBPROCESS_PATTERNS:
                    if bare == pattern.split(".")[-1] and bare in {
                        "run",
                        "Popen",
                        "call",
                        "check_output",
                        "check_call",
                        "system",
                        "popen",
                    }:
                        matched = pattern
                        break

        if not matched:
            continue

        # Extract command argument
        command_literal = None
        command_is_dynamic = True
        if node.args:
            lit = _extract_literal(node.args[0])
            if lit is not None:
                command_literal = lit
                command_is_dynamic = "<dynamic>" in str(lit) or "{...}" in str(lit)

        func_ctx = _find_enclosing_function(tree, node.lineno)

        calls.append(
            {
                "file": filepath,
                "lineno": node.lineno,
                "function_context": func_ctx,
                "call_type": matched,
                "command_literal": command_literal,
                "command_is_dynamic": command_is_dynamic,
            }
        )

    return calls


def _extract_port_bindings(tree: ast.Module, filepath: str) -> list[dict]:
    """Extract port/server binding calls."""
    bindings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _resolve_call_name(node.func)
        if not call_name:
            continue

        # Check server patterns
        framework = None
        if "uvicorn.run" in call_name or (call_name == "run" and "uvicorn" in filepath):
            framework = "uvicorn"
        elif call_name.endswith("app.run") or call_name == "app.run":
            framework = "flask"
        elif "socket.bind" in call_name or "socket.connect" in call_name:
            framework = "socket"
        else:
            continue

        # Try to extract port
        port = None
        for kw in node.keywords:
            if kw.arg == "port" and isinstance(kw.value, ast.Constant):
                port = kw.value.value

        # Check positional args for socket.bind((host, port))
        if not port and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Tuple) and len(arg.elts) >= 2:
                port_node = arg.elts[1]
                if isinstance(port_node, ast.Constant):
                    port = port_node.value

        func_ctx = _find_enclosing_function(tree, node.lineno)
        bindings.append(
            {
                "file": filepath,
                "lineno": node.lineno,
                "port": port,
                "protocol": "http" if framework in ("flask", "uvicorn") else "tcp",
                "framework": framework,
                "function_context": func_ctx,
            }
        )

    return bindings


def _extract_env_var_reads(tree: ast.Module, filepath: str) -> list[dict]:
    """Extract all os.environ.get/os.environ[]/os.getenv calls."""
    reads = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = _resolve_call_name(node.func)
            if not call_name:
                continue

            var_name = None
            default = None

            if (
                call_name.endswith("os.environ.get")
                or call_name == "os.environ.get"
                or call_name.endswith("environ.get")
                or call_name.endswith("os.getenv")
                or call_name == "os.getenv"
                or call_name == "getenv"
            ):
                if node.args and isinstance(node.args[0], ast.Constant):
                    var_name = str(node.args[0].value)
                if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                    default = str(node.args[1].value)
            else:
                continue

            if var_name:
                func_ctx = _find_enclosing_function(tree, node.lineno)
                reads.append(
                    {
                        "file": filepath,
                        "lineno": node.lineno,
                        "variable": var_name,
                        "default": default,
                        "function_context": func_ctx,
                    }
                )

        elif isinstance(node, ast.Subscript):
            # os.environ["VAR"]
            val_name = _resolve_call_name(node.value) if hasattr(node, "value") else None
            if val_name and ("os.environ" in val_name or val_name == "environ"):
                if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                    func_ctx = _find_enclosing_function(tree, node.lineno)
                    reads.append(
                        {
                            "file": filepath,
                            "lineno": node.lineno,
                            "variable": node.slice.value,
                            "default": None,
                            "function_context": func_ctx,
                        }
                    )

    return reads


def _parse_docker_compose(filepath: Path) -> dict | None:
    """Parse a docker-compose YAML file."""
    try:
        import yaml
    except ImportError:
        print(f"WARNING: PyYAML not available, skipping {filepath}", file=sys.stderr)
        return None

    try:
        content = filepath.read_text()
        data = yaml.safe_load(content)
    except Exception as e:
        print(f"WARNING: Failed to parse {filepath}: {e}", file=sys.stderr)
        return None

    if not isinstance(data, dict):
        return None

    services = []
    for name, svc in (data.get("services") or {}).items():
        if not isinstance(svc, dict):
            continue
        services.append(
            {
                "name": name,
                "image": svc.get("image"),
                "ports": svc.get("ports", []),
                "volumes": svc.get("volumes", []),
                "depends_on": svc.get("depends_on", []),
                "networks": svc.get("networks", []),
            }
        )

    return {
        "file": str(filepath),
        "services": services,
    }


def _parse_dockerfile(filepath: Path) -> dict | None:
    """Parse a Dockerfile for key directives."""
    try:
        lines = filepath.read_text().splitlines()
    except OSError:
        return None

    result = {
        "file": str(filepath),
        "from_images": [],
        "exposed_ports": [],
        "cmd": None,
        "entrypoint": None,
    }

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("FROM "):
            result["from_images"].append(stripped[5:].strip())
        elif stripped.startswith("EXPOSE "):
            for part in stripped[7:].split():
                port_str = part.split("/")[0]
                try:
                    result["exposed_ports"].append(int(port_str))
                except ValueError:
                    result["exposed_ports"].append(port_str)
        elif stripped.startswith("CMD "):
            result["cmd"] = stripped[4:].strip()
        elif stripped.startswith("ENTRYPOINT "):
            result["entrypoint"] = stripped[11:].strip()

    return result


def extract(manifest: dict, repo_root: Path) -> dict:
    """Extract layer 4 runtime topology data.

    Args:
        manifest: Loaded manifest.json.
        repo_root: Repository root directory.

    Returns:
        Layer 4 data dict.
    """
    root_str = manifest["root"]
    root = Path(root_str)

    py_files = [f for f in manifest["files"] if f["extension"] == ".py"]

    subprocess_calls: list[dict] = []
    port_bindings: list[dict] = []
    env_var_reads: list[dict] = []
    files_with_subprocess: set[str] = set()

    for finfo in py_files:
        filepath = finfo["path"]
        tree = parse_file_safe(Path(filepath))
        if tree is None:
            continue

        sc = _extract_subprocess_calls(tree, filepath)
        if sc:
            subprocess_calls.extend(sc)
            files_with_subprocess.add(filepath)

        pb = _extract_port_bindings(tree, filepath)
        port_bindings.extend(pb)

        ev = _extract_env_var_reads(tree, filepath)
        env_var_reads.extend(ev)

    # Docker configs
    docker_configs = []

    # Search for docker-compose files
    for pattern in ["docker-compose*.yml", "docker-compose*.yaml"]:
        for dc in repo_root.glob(pattern):
            parsed = _parse_docker_compose(dc)
            if parsed:
                docker_configs.append(parsed)

    # Search for Dockerfiles
    dockerfiles = []
    for df in repo_root.glob("Dockerfile*"):
        parsed = _parse_dockerfile(df)
        if parsed:
            dockerfiles.append(parsed)

    docker_service_count = sum(len(dc.get("services", [])) for dc in docker_configs)

    return {
        "layer": "runtime-topology",
        "subprocess_calls": subprocess_calls,
        "port_bindings": port_bindings,
        "docker_configs": docker_configs,
        "dockerfiles": dockerfiles,
        "env_var_reads": env_var_reads,
        "summary": {
            "subprocess_call_count": len(subprocess_calls),
            "unique_subprocess_files": len(files_with_subprocess),
            "port_binding_count": len(port_bindings),
            "docker_service_count": docker_service_count,
            "dockerfile_count": len(dockerfiles),
            "env_var_count": len(env_var_reads),
        },
    }


def self_check(data: dict, manifest: dict) -> list[str]:
    """Completeness self-check for layer 4."""
    issues = []

    # Verify all env var reads have a variable name
    for ev in data.get("env_var_reads", []):
        if not ev.get("variable"):
            issues.append(f"env_var_read without variable name at {ev['file']}:{ev['lineno']}")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Layer 4: Runtime Topology")
    parser.add_argument("--root", required=True, help="Project source root")
    parser.add_argument("--output", required=True, help="Output directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output = Path(args.output).resolve()

    repo_root = find_repo_root(root)

    manifest = load_manifest(output)
    data = extract(manifest, repo_root)
    issues = self_check(data, manifest)

    out_path = write_layer_json("layer4_runtime_topology", data, output)

    s = data["summary"]
    print("Layer 4: runtime-topology")
    print(f"  Subprocess calls:      {s['subprocess_call_count']}")
    print(f"  Unique subprocess files: {s['unique_subprocess_files']}")
    print(f"  Port bindings:         {s['port_binding_count']}")
    print(f"  Docker services:       {s['docker_service_count']}")
    print(f"  Dockerfiles:           {s['dockerfile_count']}")
    print(f"  Env var reads:         {s['env_var_count']}")
    if issues:
        print(f"  ISSUES: {len(issues)}")
        for issue in issues:
            print(f"    - {issue}")
    print(f"  Output: {out_path} ({out_path.stat().st_size:,} bytes)")

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
