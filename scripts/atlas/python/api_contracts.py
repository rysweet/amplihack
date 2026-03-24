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
    _resolve_call_name,
    find_repo_root,
    load_manifest,
    parse_file_safe,
    write_layer_json,
)


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
                parsers.append(
                    {
                        "parser_name": name,
                        "help": help_text,
                        "file": filepath,
                        "lineno": node.lineno,
                    }
                )

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

            arguments.append(
                {
                    "name": arg_name,
                    "all_names": arg_names,
                    "type": arg_type,
                    "required": required,
                    "default": default,
                    "help": help_text,
                    "action": action,
                    "file": filepath,
                    "lineno": node.lineno,
                }
            )

    return parsers, arguments


def _extract_click_typer_commands(tree: ast.Module, filepath: str) -> list[dict]:
    """Extract Click and Typer CLI command definitions.

    Detects:
    - @click.command(), @click.group()
    - @app.command() where app = click.Group() or typer.Typer()
    - Extracts command name, arguments from function signature, docstring help text.
    """
    commands = []

    # Phase 1: Find module-level objects that are Click groups or Typer apps
    # Case A: app = typer.Typer(), cli = click.Group()
    click_typer_vars: set[str] = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                    call_name = _resolve_call_name(node.value.func)
                    if call_name and call_name in (
                        "click.Group",
                        "click.group",
                        "typer.Typer",
                        "click.MultiCommand",
                        "click.CommandCollection",
                    ):
                        click_typer_vars.add(target.id)

    # Case B: @click.group() decorated functions become group objects
    # e.g. @click.group() def bundle(): ... -> 'bundle' is a Click group
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            dec_name = None
            if isinstance(dec, ast.Call):
                dec_name = _resolve_call_name(dec.func)
            elif isinstance(dec, ast.Attribute):
                dec_name = _resolve_call_name(dec)
            if dec_name and dec_name in ("click.group", "click.Group"):
                click_typer_vars.add(node.name)

    # Phase 2: Find decorated functions
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for dec in node.decorator_list:
            dec_call = None
            call_name = None

            if isinstance(dec, ast.Call):
                call_name = _resolve_call_name(dec.func)
                dec_call = dec
            elif isinstance(dec, ast.Attribute):
                call_name = _resolve_call_name(dec)

            if not call_name:
                continue

            # Check for click.command(), click.group()
            is_click_direct = call_name in ("click.command", "click.group")

            # Check for app.command(), app.group() where app is a known Click/Typer var
            is_app_command = False
            if not is_click_direct and call_name:
                parts = call_name.rsplit(".", 1)
                if len(parts) == 2:
                    obj_name, method = parts
                    if obj_name in click_typer_vars and method in ("command", "group", "callback"):
                        is_app_command = True

            if not is_click_direct and not is_app_command:
                continue

            # Extract command name from decorator arg or fall back to function name
            cmd_name = None
            if dec_call:
                cmd_name = _get_string_arg(dec_call, 0, kw="name")
            if not cmd_name:
                cmd_name = node.name.replace("_", "-")

            # Extract help text from decorator kwarg or docstring
            help_text = None
            if dec_call:
                help_text = _get_string_arg(dec_call, kw="help")
            if not help_text and node.body:
                first = node.body[0]
                if (
                    isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)
                ):
                    help_text = first.value.value.strip().split("\n")[0]

            # Extract arguments from function signature
            func_args = []
            for arg in node.args.args:
                if arg.arg in ("self", "ctx"):
                    continue
                annotation = None
                if arg.annotation:
                    try:
                        annotation = ast.unparse(arg.annotation)
                    except Exception:
                        pass
                func_args.append(
                    {
                        "name": arg.arg,
                        "type": annotation,
                    }
                )

            framework = "click" if is_click_direct or call_name.startswith("click.") else "typer"
            cmd_type = "group" if "group" in (call_name or "") else "command"

            commands.append(
                {
                    "command": cmd_name,
                    "function": node.name,
                    "framework": framework,
                    "type": cmd_type,
                    "help": help_text,
                    "arguments": func_args,
                    "file": filepath,
                    "lineno": node.lineno,
                }
            )

    return commands


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
                routes.append(
                    {
                        "method": method,
                        "path": path,
                        "function": node.name,
                        "file": filepath,
                        "lineno": node.lineno,
                    }
                )

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

            hooks.append(
                {
                    "name": hook_name,
                    "type": event_type,
                    "handler": hook_name,
                    "file": str(f),
                }
            )

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
                except Exception as e:
                    print(f"WARNING: failed to parse recipe {f}: {e}", file=sys.stderr)
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

                recipes.append(
                    {
                        "file": str(f),
                        "name": name,
                        "description": str(description)[:200] if description else "",
                        "step_count": len(steps) if isinstance(steps, list) else 0,
                        "agents_used": sorted(agents_used),
                    }
                )

    return recipes


def _parse_frontmatter(filepath: Path) -> dict:
    """Extract YAML frontmatter from a markdown file."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"WARNING: could not read frontmatter from {filepath}: {e}", file=sys.stderr)
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
    except Exception as e:
        print(f"WARNING: failed to parse YAML frontmatter in {filepath}: {e}", file=sys.stderr)
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

            skills.append(
                {
                    "file": str(f),
                    "name": name,
                    "description": str(description)[:200] if description else "",
                    "triggers": triggers if isinstance(triggers, list) else [],
                }
            )

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

            agents.append(
                {
                    "file": str(f),
                    "name": name,
                    "role": str(role)[:200] if role else "",
                    "capabilities": capabilities if isinstance(capabilities, list) else [],
                }
            )

    return agents


def _extract_rust_clap_commands(root: Path) -> list[dict]:
    """Detect Rust clap CLI commands from source files.

    Scans .rs files for clap derive macros and builder patterns:
    - #[derive(Parser)] or #[derive(Args)] structs
    - #[command(name = "...")] attributes
    - #[subcommand] enum variants
    - clap::Command::new("...") builder calls
    """
    commands: list[dict] = []

    for rs_file in root.rglob("*.rs"):
        filepath_str = str(rs_file)
        if any(skip in filepath_str for skip in ("target/", ".git/", "vendor/")):
            continue

        try:
            content = rs_file.read_text(errors="replace")
        except OSError:
            continue

        lines = content.split("\n")

        # Track derive(Parser) structs and their #[command] attributes
        has_derive_parser = False
        pending_command_name = None

        for lineno_0, line in enumerate(lines):
            lineno = lineno_0 + 1
            stripped = line.strip()

            # Detect #[derive(Parser)] or #[derive(Args)]
            if re.search(r"#\[derive\([^)]*\b(Parser|Args)\b", stripped):
                has_derive_parser = True
                pending_command_name = None
                continue

            # Detect #[command(name = "...")] attribute
            m = re.search(r'#\[command\([^)]*name\s*=\s*"([^"]+)"', stripped)
            if m:
                pending_command_name = m.group(1)
                continue

            # When we hit a struct/enum after derive(Parser), record the command
            if has_derive_parser:
                struct_m = re.match(r"(?:pub\s+)?(?:struct|enum)\s+(\w+)", stripped)
                if struct_m:
                    cmd_name = pending_command_name or struct_m.group(1).lower()
                    commands.append(
                        {
                            "command": cmd_name,
                            "struct": struct_m.group(1),
                            "framework": "clap-derive",
                            "type": "command",
                            "file": filepath_str,
                            "lineno": lineno,
                        }
                    )
                    has_derive_parser = False
                    pending_command_name = None
                    continue

            # Detect #[subcommand] field annotations
            if re.search(r"#\[subcommand\]", stripped):
                # The next field line has the subcommand name
                # e.g. "command: Commands" -- we just record the annotation
                commands.append(
                    {
                        "command": "(subcommand)",
                        "framework": "clap-derive",
                        "type": "subcommand",
                        "file": filepath_str,
                        "lineno": lineno,
                    }
                )
                continue

            # Detect clap::Command::new("...") or Command::new("...")
            for builder_m in re.finditer(r'(?:clap::)?Command::new\(\s*"([^"]+)"', stripped):
                commands.append(
                    {
                        "command": builder_m.group(1),
                        "framework": "clap-builder",
                        "type": "command",
                        "file": filepath_str,
                        "lineno": lineno,
                    }
                )

            # Reset derive tracking on blank lines or non-attribute/non-comment lines
            if (
                has_derive_parser
                and stripped
                and not stripped.startswith("#")
                and not stripped.startswith("//")
            ):
                # If we hit a non-struct definition line, reset
                if (
                    not stripped.startswith("pub")
                    and not stripped.startswith("struct")
                    and not stripped.startswith("enum")
                ):
                    has_derive_parser = False
                    pending_command_name = None

    return commands


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
    all_click_typer: list[dict] = []

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

        click_typer = _extract_click_typer_commands(tree, filepath)
        all_click_typer.extend(click_typer)

    # Build CLI command entries with their arguments
    # Group arguments by file proximity to parsers
    cli_commands = []
    for p in all_parsers:
        # Find arguments defined in the same file near this parser
        file_args = [a for a in all_arguments if a["file"] == p["file"]]
        cli_commands.append(
            {
                "command": p["parser_name"],
                "parser_name": p["parser_name"],
                "help": p["help"],
                "file": p["file"],
                "lineno": p["lineno"],
                "argument_count": len(file_args),
            }
        )

    # Rust CLI commands (clap)
    rust_clap_commands = _extract_rust_clap_commands(repo_root)

    # Non-Python contracts
    hooks = _extract_hooks(repo_root)
    recipes = _extract_recipes(repo_root)
    skills = _extract_skills(repo_root)
    agents = _extract_agents(repo_root)

    return {
        "layer": "api-contracts",
        "cli_commands": cli_commands,
        "cli_arguments": all_arguments,
        "click_typer_commands": all_click_typer,
        "rust_clap_commands": rust_clap_commands,
        "http_routes": all_routes,
        "hook_events": hooks,
        "recipes": recipes,
        "skills": skills,
        "agents": agents,
        "summary": {
            "cli_command_count": len(cli_commands),
            "cli_argument_count": len(all_arguments),
            "click_typer_command_count": len(all_click_typer),
            "rust_clap_command_count": len(rust_clap_commands),
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

    repo_root = find_repo_root(root)

    manifest = load_manifest(output)
    data = extract(manifest, repo_root)
    issues = self_check(data, manifest)

    out_path = write_layer_json("layer5_api_contracts", data, output)

    s = data["summary"]
    print("Layer 5: api-contracts")
    print(f"  CLI commands:     {s['cli_command_count']}")
    print(f"  CLI arguments:    {s['cli_argument_count']}")
    print(f"  Click/Typer:      {s['click_typer_command_count']}")
    print(f"  Rust clap:        {s['rust_clap_command_count']}")
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
