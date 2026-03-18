"""Layer 5: API Contracts -- CLI commands, HTTP routes, hooks, recipes, skills, agents.

Parses argparse calls for CLI subcommands, HTTP route decorators, hook files,
recipe YAMLs, and skill/agent markdown frontmatter to produce a complete
contract map of all user-facing interfaces.
"""

import argparse
import ast
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
from scripts.atlas.common import (
    load_manifest,
    parse_file_safe,
    write_layer_json,
)


def _resolve_call_name(node: ast.expr) -> str | None:
    """Resolve a call's func node to a dotted string."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        value = _resolve_call_name(node.value)
        if value:
            return f"{value}.{node.attr}"
        return node.attr
    return None


def _get_string_arg(node: ast.Call, pos: int = 0, kw: str | None = None) -> str | None:
    """Extract a string argument from a call by position or keyword."""
    if kw:
        for keyword in node.keywords:
            if keyword.arg == kw and isinstance(keyword.value, ast.Constant):
                return str(keyword.value.value)
    if pos < len(node.args) and isinstance(node.args[pos], ast.Constant):
        return str(node.args[pos].value)
    return None


def _extract_cli_commands(tree: ast.Module, filepath: str) -> tuple[list[dict], list[dict]]:
    """Extract argparse add_parser and add_argument calls.

    Returns:
        Tuple of (parsers, arguments) where each is a list of dicts.
    """
    parsers = []
    arguments = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        call_name = _resolve_call_name(node.func)
        if not call_name:
            continue

        if call_name.endswith("add_parser"):
            name = _get_string_arg(node, 0)
            help_text = _get_string_arg(node, kw="help")
            if name:
                parsers.append({
                    "parser_name": name,
                    "help": help_text,
                    "file": filepath,
                    "lineno": node.lineno,
                })

        elif call_name.endswith("add_argument"):
            # Get argument name(s)
            arg_names = []
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    arg_names.append(arg.value)

            if not arg_names:
                continue

            arg_name = arg_names[-1]  # Use longest form (--foo over -f)
            help_text = _get_string_arg(node, kw="help")
            arg_type = _get_string_arg(node, kw="type")
            default = _get_string_arg(node, kw="default")

            # Check required
            required = False
            for kw_node in node.keywords:
                if kw_node.arg == "required" and isinstance(kw_node.value, ast.Constant):
                    required = bool(kw_node.value.value)

            # Check action
            action = _get_string_arg(node, kw="action")

            arguments.append({
                "name": arg_name,
                "all_names": arg_names,
                "type": arg_type,
                "required": required,
                "default": default,
                "help": help_text,
                "action": action,
                "file": filepath,
                "lineno": node.lineno,
            })

    return parsers, arguments


def _extract_http_routes(tree: ast.Module, filepath: str) -> list[dict]:
    """Extract HTTP route decorators (@app.route, @app.get, @router.post, etc.)."""
    routes = []
    http_methods = {"get", "post", "put", "delete", "patch", "options", "head"}

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for dec in node.decorator_list:
            call_name = None
            dec_call = None

            if isinstance(dec, ast.Call):
                call_name = _resolve_call_name(dec.func)
                dec_call = dec
            elif isinstance(dec, ast.Attribute):
                call_name = _resolve_call_name(dec)

            if not call_name:
                continue

            method = None
            path = None

            # @app.route("/path", methods=["GET"])
            if call_name.endswith(".route") and dec_call:
                path = _get_string_arg(dec_call, 0)
                # Extract methods kwarg
                for kw_node in dec_call.keywords:
                    if kw_node.arg == "methods" and isinstance(kw_node.value, ast.List):
                        methods = []
                        for elt in kw_node.value.elts:
                            if isinstance(elt, ast.Constant):
                                methods.append(str(elt.value).upper())
                        method = ",".join(methods) if methods else "GET"
                if not method:
                    method = "GET"

            # @app.get("/path"), @router.post("/path")
            elif any(call_name.endswith(f".{m}") for m in http_methods):
                for m in http_methods:
                    if call_name.endswith(f".{m}"):
                        method = m.upper()
                        break
                if dec_call:
                    path = _get_string_arg(dec_call, 0)

            if method and path:
                routes.append({
                    "method": method,
                    "path": path,
                    "function": node.name,
                    "file": filepath,
                    "lineno": node.lineno,
                })

    return routes


def _extract_hooks(repo_root: Path) -> list[dict]:
    """Scan hook directories for hook definitions."""
    hooks = []
    hook_dirs = [
        repo_root / ".claude" / "tools",
        repo_root / "hooks",
    ]

    # Also search within src for hooks directories
    for hdir in hook_dirs:
        if not hdir.exists():
            continue
        for f in sorted(hdir.rglob("*.py")):
            hook_name = f.stem
            # Classify by name
            if "pre" in hook_name and "commit" in hook_name:
                event_type = "pre-commit"
            elif "post" in hook_name and "commit" in hook_name:
                event_type = "post-commit"
            elif "pre" in hook_name and "push" in hook_name:
                event_type = "pre-push"
            elif hook_name == "stop":
                event_type = "lifecycle"
            else:
                event_type = "custom"

            hooks.append({
                "name": hook_name,
                "type": event_type,
                "handler": hook_name,
                "file": str(f),
            })

    return hooks


def _extract_recipes(repo_root: Path) -> list[dict]:
    """Parse recipe YAML files."""
    recipes = []
    recipe_dirs = [
        repo_root / "recipes",
        repo_root / "amplifier-bundle" / "recipes",
        repo_root / ".claude" / "recipes",
    ]

    # Also check inside src tree
    for rdir in [repo_root / "src"]:
        if rdir.exists():
            for subdir in rdir.rglob("recipes"):
                if subdir.is_dir():
                    recipe_dirs.append(subdir)

    try:
        import yaml
    except ImportError:
        print("WARNING: PyYAML not available, skipping recipe parsing", file=sys.stderr)
        return recipes

    seen_files: set[str] = set()
    for rdir in recipe_dirs:
        if not rdir.exists():
            continue
        for pattern in ["*.yaml", "*.yml"]:
            for f in sorted(rdir.glob(pattern)):
                fstr = str(f.resolve())
                if fstr in seen_files:
                    continue
                seen_files.add(fstr)

                try:
                    data = yaml.safe_load(f.read_text())
                except Exception:
                    continue

                if not isinstance(data, dict):
                    continue

                name = data.get("name", f.stem)
                description = data.get("description", "")
                steps = data.get("steps", [])
                agents_used = set()
                if isinstance(steps, list):
                    for step in steps:
                        if isinstance(step, dict):
                            agent = step.get("agent")
                            if agent:
                                agents_used.add(str(agent))

                recipes.append({
                    "file": str(f),
                    "name": name,
                    "description": str(description)[:200] if description else "",
                    "step_count": len(steps) if isinstance(steps, list) else 0,
                    "agents_used": sorted(agents_used),
                })

    return recipes


def _parse_frontmatter(filepath: Path) -> dict:
    """Extract YAML frontmatter from a markdown file."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}

    if not content.startswith("---"):
        return {}

    end = content.find("---", 3)
    if end == -1:
        return {}

    frontmatter_str = content[3:end].strip()
    try:
        import yaml
        data = yaml.safe_load(frontmatter_str)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _extract_skills(repo_root: Path) -> list[dict]:
    """Extract skill definitions from markdown files."""
    skills = []
    skill_dirs = [
        repo_root / ".claude" / "skills",
    ]

    seen: set[str] = set()
    for sdir in skill_dirs:
        if not sdir.exists():
            continue
        for f in sorted(sdir.rglob("*.md")):
            fstr = str(f.resolve())
            if fstr in seen:
                continue
            seen.add(fstr)

            fm = _parse_frontmatter(f)
            name = fm.get("name", f.stem)
            description = fm.get("description", "")
            triggers = fm.get("triggers", [])
            if isinstance(triggers, str):
                triggers = [triggers]

            skills.append({
                "file": str(f),
                "name": name,
                "description": str(description)[:200] if description else "",
                "triggers": triggers if isinstance(triggers, list) else [],
            })

    return skills


def _extract_agents(repo_root: Path) -> list[dict]:
    """Extract agent definitions from markdown files."""
    agents = []
    agent_dirs = [
        repo_root / ".claude" / "agents",
        repo_root / "agents",
    ]

    seen: set[str] = set()
    for adir in agent_dirs:
        if not adir.exists():
            continue
        for f in sorted(adir.rglob("*.md")):
            fstr = str(f.resolve())
            if fstr in seen:
                continue
            seen.add(fstr)

            fm = _parse_frontmatter(f)
            name = fm.get("name", f.stem)
            role = fm.get("role", "")
            capabilities = fm.get("capabilities", [])

            agents.append({
                "file": str(f),
                "name": name,
                "role": str(role)[:200] if role else "",
                "capabilities": capabilities if isinstance(capabilities, list) else [],
            })

    return agents


def extract(manifest: dict, repo_root: Path) -> dict:
    """Extract layer 5 API contracts data.

    Args:
        manifest: Loaded manifest.json.
        repo_root: Repository root directory.

    Returns:
        Layer 5 data dict.
    """
    py_files = [f for f in manifest["files"] if f["extension"] == ".py"]

    all_parsers: list[dict] = []
    all_arguments: list[dict] = []
    all_routes: list[dict] = []

    for finfo in py_files:
        filepath = finfo["path"]
        tree = parse_file_safe(Path(filepath))
        if tree is None:
            continue

        parsers, arguments = _extract_cli_commands(tree, filepath)
        all_parsers.extend(parsers)
        all_arguments.extend(arguments)

        routes = _extract_http_routes(tree, filepath)
        all_routes.extend(routes)

    # Build CLI command entries with their arguments
    # Group arguments by file proximity to parsers
    cli_commands = []
    for p in all_parsers:
        # Find arguments defined in the same file near this parser
        file_args = [
            a for a in all_arguments
            if a["file"] == p["file"]
        ]
        cli_commands.append({
            "command": p["parser_name"],
            "parser_name": p["parser_name"],
            "help": p["help"],
            "file": p["file"],
            "lineno": p["lineno"],
            "argument_count": len(file_args),
        })

    # Non-Python contracts
    hooks = _extract_hooks(repo_root)
    recipes = _extract_recipes(repo_root)
    skills = _extract_skills(repo_root)
    agents = _extract_agents(repo_root)

    return {
        "layer": "api-contracts",
        "cli_commands": cli_commands,
        "cli_arguments": all_arguments,
        "http_routes": all_routes,
        "hook_events": hooks,
        "recipes": recipes,
        "skills": skills,
        "agents": agents,
        "summary": {
            "cli_command_count": len(cli_commands),
            "cli_argument_count": len(all_arguments),
            "http_route_count": len(all_routes),
            "hook_event_count": len(hooks),
            "recipe_count": len(recipes),
            "skill_count": len(skills),
            "agent_count": len(agents),
        },
    }


def self_check(data: dict, manifest: dict) -> list[str]:
    """Completeness self-check for layer 5."""
    issues = []

    # Verify CLI commands have names
    for cmd in data.get("cli_commands", []):
        if not cmd.get("parser_name"):
            issues.append(f"CLI command without name at {cmd['file']}:{cmd['lineno']}")

    # Verify HTTP routes have paths
    for route in data.get("http_routes", []):
        if not route.get("path"):
            issues.append(f"HTTP route without path at {route['file']}:{route['lineno']}")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Layer 5: API Contracts")
    parser.add_argument("--root", required=True, help="Project source root")
    parser.add_argument("--output", required=True, help="Output directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output = Path(args.output).resolve()

    # Repo root is parent of src/amplihack
    repo_root = root
    while repo_root.name != "amplihack" or not (repo_root / "pyproject.toml").exists():
        if repo_root.parent == repo_root:
            repo_root = root.parent.parent
            break
        repo_root = repo_root.parent

    manifest = load_manifest(output)
    data = extract(manifest, repo_root)
    issues = self_check(data, manifest)

    out_path = write_layer_json("layer5_api_contracts", data, output)

    s = data["summary"]
    print(f"Layer 5: api-contracts")
    print(f"  CLI commands:     {s['cli_command_count']}")
    print(f"  CLI arguments:    {s['cli_argument_count']}")
    print(f"  HTTP routes:      {s['http_route_count']}")
    print(f"  Hook events:      {s['hook_event_count']}")
    print(f"  Recipes:          {s['recipe_count']}")
    print(f"  Skills:           {s['skill_count']}")
    print(f"  Agents:           {s['agent_count']}")
    if issues:
        print(f"  ISSUES: {len(issues)}")
        for issue in issues:
            print(f"    - {issue}")
    print(f"  Output: {out_path} ({out_path.stat().st_size:,} bytes)")

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
