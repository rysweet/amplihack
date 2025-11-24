#!/usr/bin/env python3
"""Generate DAP configuration for detected language.

Reads template from configs/{debugger}.json and substitutes variables.

Public API:
    generate_config(language, project_dir, **kwargs) -> dict
    validate_config(config) -> bool
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

# Public API
__all__ = ["generate_config", "validate_config"]


def generate_config(language: str, project_dir: str, **kwargs) -> Dict[str, Any]:
    """Generate DAP config for language.

    Args:
        language: Detected language (python, javascript, etc.)
        project_dir: Project root directory
        **kwargs: Additional template variables (port, entry_point, etc.)

    Returns:
        Complete DAP configuration dict
    """
    # Get configs directory relative to this script
    script_dir = Path(__file__).parent
    skill_dir = script_dir.parent
    configs_dir = skill_dir / "configs"

    # Map language to debugger config file (dap-mcp supported only)
    debugger_map = {
        "python": "debugpy.json",
        "c": "lldb.json",
        "cpp": "lldb.json",
        "rust": "lldb.json",
    }

    config_file = configs_dir / debugger_map.get(language, "lldb.json")

    if not config_file.exists():
        raise FileNotFoundError(f"No config template for {language}: {config_file}")

    # Load template
    with open(config_file) as f:
        template_data = json.load(f)

    # Prepare substitutions
    project_path = Path(project_dir).resolve()
    substitutions = {
        "project_dir": str(project_path),
        "port": str(kwargs.get("port", template_data.get("default_port", 5678))),
        "entry_point": kwargs.get("entry_point", "main"),
        **kwargs,
    }

    # Flat template substitution (simpler than recursion)
    # Serialize config to JSON string, replace variables, parse back
    config_str = json.dumps(template_data.get("config", {}))

    # Replace all template variables in format ${variable_name}
    for key, value in substitutions.items():
        config_str = config_str.replace(f"${{{key}}}", str(value))

    config = json.loads(config_str)

    return config


def validate_config(config: Dict[str, Any]) -> bool:
    """Validate generated configuration matches dap-mcp schema.

    Required fields for dap-mcp:
    - type: debugger type (debugpy, lldb)
    - debuggerPath: path to debugger executable
    - sourceDirs: list of source directories
    """
    required_fields = ["type", "debuggerPath", "sourceDirs"]

    for field in required_fields:
        if field not in config:
            return False

    # Validate type is supported
    if config["type"] not in ["debugpy", "lldb"]:
        return False

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate DAP configuration")
    parser.add_argument("language", help="Programming language")
    parser.add_argument("--project-dir", default=".", help="Project root directory")
    parser.add_argument("--port", type=int, help="Debug adapter protocol port")
    parser.add_argument("--entry-point", help="Main program entry point")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    parser.add_argument("--validate", action="store_true", help="Validate generated config")
    args = parser.parse_args()

    try:
        # Prepare kwargs
        kwargs = {}
        if args.port:
            kwargs["port"] = args.port
        if args.entry_point:
            kwargs["entry_point"] = args.entry_point

        # Generate config
        config = generate_config(args.language, args.project_dir, **kwargs)

        # Validate if requested
        if args.validate:
            if not validate_config(config):
                print("ERROR: Invalid configuration generated", file=sys.stderr)
                sys.exit(1)

        # Output config
        config_json = json.dumps(config, indent=2)

        if args.output:
            output_path = Path(args.output)
            output_path.write_text(config_json)
            print(f"Configuration written to: {args.output}", file=sys.stderr)
        else:
            print(config_json)

    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to generate config: {e}", file=sys.stderr)
        sys.exit(1)
