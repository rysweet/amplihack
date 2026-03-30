"""Transform atlas extraction JSON into structured input for LLM bug hunt.

Collects cross-layer warnings, journey traces with outcome classifications,
I/O operations grouped by error-handling presence, and subprocess calls with
security context into a single structured JSON for LLM analysis.

Public API:
    prepare_bug_hunt: Build bug hunt input from atlas data
    main: CLI entry point
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

__all__ = ["prepare_bug_hunt", "main"]


def prepare_bug_hunt(data_dir: Path) -> dict:
    """Build structured bug hunt input from atlas extraction JSON.

    Args:
        data_dir: Directory containing atlas layer JSON files.

    Returns:
        Dict with sections: warnings, journey_traces, io_operations,
        subprocess_calls, summary.

    Raises:
        FileNotFoundError: If data_dir does not exist.
    """
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    layers = _load_layers(data_dir)

    result = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_dir": str(data_dir),
        "sections": {
            "cross_layer_warnings": _extract_warnings(layers),
            "journey_traces": _extract_journey_traces(layers),
            "io_operations": _extract_io_operations(layers),
            "subprocess_calls": _extract_subprocess_calls(layers),
        },
        "summary": {},
    }

    # Compute summary
    sections = result["sections"]
    result["summary"] = {
        "total_warnings": len(sections["cross_layer_warnings"]),
        "total_journey_traces": len(sections["journey_traces"]),
        "total_io_operations": len(sections["io_operations"]),
        "total_subprocess_calls": len(sections["subprocess_calls"]),
        "io_without_error_handling": sum(
            1 for op in sections["io_operations"] if not op.get("has_error_handling")
        ),
        "dynamic_subprocess_calls": sum(
            1 for call in sections["subprocess_calls"] if call.get("command_is_dynamic")
        ),
    }

    return result


def _load_layers(data_dir: Path) -> dict[str, dict]:
    """Load all available layer JSONs."""
    layers = {}
    for json_file in data_dir.glob("*.json"):
        layers[json_file.stem] = json.loads(json_file.read_text())
    return layers


def _extract_warnings(layers: dict[str, dict]) -> list[dict]:
    """Extract all cross-layer warnings and failures."""
    warnings = []

    # From cross-layer report
    report = layers.get("cross_layer_report", {})
    for check in report.get("checks", []):
        status = check.get("status", "")
        if status in ("WARN", "FAIL"):
            warnings.append(
                {
                    "source": "cross_layer_report",
                    "check_name": check.get("name", "unknown"),
                    "severity": "error" if status == "FAIL" else "warning",
                    "details": check.get("details", ""),
                    "missing_items": check.get("missing", []),
                }
            )

    # Dead code from layer 2
    layer2 = layers.get("layer2_ast_bindings", {})
    dead_code = layer2.get("potentially_dead", [])
    if dead_code:
        warnings.append(
            {
                "source": "layer2_ast_bindings",
                "check_name": "dead_code",
                "severity": "info",
                "details": f"{len(dead_code)} potentially dead definitions",
                "items": dead_code[:50],  # Cap for LLM context
            }
        )

    # Unused dependencies from layer 3
    layer3 = layers.get("layer3_compile_deps", {})
    unused = layer3.get("unused_dependencies", [])
    if unused:
        warnings.append(
            {
                "source": "layer3_compile_deps",
                "check_name": "unused_dependencies",
                "severity": "warning",
                "details": f"{len(unused)} declared but unused dependencies",
                "items": unused,
            }
        )

    # Circular dependencies from layer 3
    cycles = layer3.get("circular_dependencies", [])
    if cycles:
        warnings.append(
            {
                "source": "layer3_compile_deps",
                "check_name": "circular_dependencies",
                "severity": "warning",
                "details": f"{len(cycles)} circular dependency chains",
                "items": cycles,
            }
        )

    # Export consistency from layer 2
    exports = layer2.get("exports", [])
    invalid_exports = [e for e in exports if not e.get("valid", True)]
    if invalid_exports:
        warnings.append(
            {
                "source": "layer2_ast_bindings",
                "check_name": "invalid_exports",
                "severity": "error",
                "details": f"{len(invalid_exports)} files with invalid __all__ exports",
                "items": invalid_exports[:20],
            }
        )

    return warnings


def _extract_journey_traces(layers: dict[str, dict]) -> list[dict]:
    """Extract journey traces with outcome classifications."""
    layer8 = layers.get("layer8_user_journeys", {})
    journeys = layer8.get("journeys", [])

    traces = []
    for journey in journeys:
        outcomes = journey.get("outcomes", [])
        outcome_types: dict[str, int] = {}
        for outcome in outcomes:
            otype = outcome.get("type", "unknown")
            outcome_types[otype] = outcome_types.get(otype, 0) + 1

        traces.append(
            {
                "entry_type": journey.get("entry_type", ""),
                "command": journey.get("command", ""),
                "handler_file": journey.get("handler", {}).get("file", ""),
                "handler_function": journey.get("handler", {}).get("function", ""),
                "trace_depth": journey.get("trace_depth", 0),
                "functions_reached": journey.get("functions_reached", 0),
                "packages_touched": journey.get("packages_touched", []),
                "outcome_summary": outcome_types,
                "outcomes": outcomes,
            }
        )

    return traces


def _extract_io_operations(layers: dict[str, dict]) -> list[dict]:
    """Extract I/O operations grouped by error-handling presence.

    Checks whether each I/O operation's enclosing function context appears
    in files that have try/except handling (based on layer 2 conditional
    import data as a proxy for error handling patterns).
    """
    layer6 = layers.get("layer6_data_flow", {})
    layer2 = layers.get("layer2_ast_bindings", {})

    # Build set of files known to have try/except patterns (from conditional imports)
    files_with_try: set[str] = set()
    for imp in layer2.get("imports", []):
        if imp.get("is_conditional"):
            files_with_try.add(imp.get("file", ""))

    operations = []

    for io_op in layer6.get("file_io", []):
        op_file = io_op.get("file", "")
        operations.append(
            {
                "type": "file_io",
                "file": op_file,
                "lineno": io_op.get("lineno", 0),
                "operation": io_op.get("operation", ""),
                "format": io_op.get("format", ""),
                "function_context": io_op.get("function_context", ""),
                "has_error_handling": op_file in files_with_try,
            }
        )

    for db_op in layer6.get("database_ops", []):
        op_file = db_op.get("file", "")
        operations.append(
            {
                "type": "database",
                "file": op_file,
                "lineno": db_op.get("lineno", 0),
                "operation": db_op.get("operation", ""),
                "db_type": db_op.get("db_type", ""),
                "function_context": db_op.get("function_context", ""),
                "has_error_handling": op_file in files_with_try,
            }
        )

    for net_op in layer6.get("network_io", []):
        op_file = net_op.get("file", "")
        operations.append(
            {
                "type": "network",
                "file": op_file,
                "lineno": net_op.get("lineno", 0),
                "method": net_op.get("method", ""),
                "function_context": net_op.get("function_context", ""),
                "has_error_handling": op_file in files_with_try,
            }
        )

    return operations


def _extract_subprocess_calls(layers: dict[str, dict]) -> list[dict]:
    """Extract subprocess calls with security context."""
    layer4 = layers.get("layer4_runtime_topology", {})
    calls = layer4.get("subprocess_calls", [])

    enriched = []
    for call in calls:
        command = call.get("command_literal")
        is_dynamic = call.get("command_is_dynamic", False)

        # Security flags
        security_flags = []
        if is_dynamic:
            security_flags.append("dynamic_command")

        call_type = call.get("call_type", "")
        if call_type in ("os.system", "os.popen"):
            security_flags.append("shell_injection_risk")

        if isinstance(command, str) and any(
            c in command for c in ["|", ";", "&&", "||", "`", "$("]
        ):
            security_flags.append("shell_metacharacters")

        enriched.append(
            {
                "file": call.get("file", ""),
                "lineno": call.get("lineno", 0),
                "function_context": call.get("function_context", ""),
                "call_type": call_type,
                "command": command,
                "command_is_dynamic": is_dynamic,
                "security_flags": security_flags,
            }
        )

    return enriched


def main():
    """CLI entry point for bug hunt preparation."""
    parser = argparse.ArgumentParser(
        description="Prepare structured bug hunt input from atlas data"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("atlas_output"),
        help="Directory containing layer JSON files (default: atlas_output/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("atlas_output/bug_hunt_input.json"),
        help="Output file path (default: atlas_output/bug_hunt_input.json)",
    )
    args = parser.parse_args()

    if not args.data_dir.exists():
        print(f"Error: data directory {args.data_dir} does not exist.")
        print("Run the extraction pipeline first: python -m scripts.atlas.run_all")
        raise SystemExit(1)

    print(f"Loading atlas data from {args.data_dir}...")
    result = prepare_bug_hunt(args.data_dir)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, default=str))

    summary = result["summary"]
    print(f"Bug hunt input written to {args.output}")
    print(f"  Warnings: {summary['total_warnings']}")
    print(f"  Journey traces: {summary['total_journey_traces']}")
    print(f"  I/O operations: {summary['total_io_operations']}")
    print(f"    (without error handling: {summary['io_without_error_handling']})")
    print(f"  Subprocess calls: {summary['total_subprocess_calls']}")
    print(f"    (dynamic commands: {summary['dynamic_subprocess_calls']})")


if __name__ == "__main__":
    main()
