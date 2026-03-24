"""Cross-layer completeness validation for code atlas v3.

Runs 15 checks across all layer JSONs to validate consistency.
Each check produces: name, status (PASS/WARN/FAIL), details, missing items.

Structural checks (1-8):
  1. FILE_COVERAGE
  2. CLI_COMMAND_COVERAGE
  3. EXPORT_CONSISTENCY
  4. DEPENDENCY_CONSISTENCY
  5. IO_TRACEABILITY
  6. SUBPROCESS_TRACEABILITY
  7. PACKAGE_CONSISTENCY
  8. ROUTE_COVERAGE

Semantic checks (9-15):
  9. IMPORT_RESOLUTION
  10. CLI_HANDLER_REACHABILITY
  11. DEAD_DEP_CROSS_VALIDATION
  12. CIRCULAR_IMPORT_SEVERITY
  13. ENV_VAR_COMPLETENESS
  14. ROUTE_TEST_COVERAGE
  15. REEXPORT_CHAIN_VALIDATION
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))


def _load_optional(output_dir: Path, name: str) -> dict | None:
    """Load a layer JSON if it exists, return None otherwise."""
    path = output_dir / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def run_checks(output_dir: Path) -> dict:
    """Run all cross-layer checks and return report dict."""
    output_dir = output_dir.resolve()

    # Load all available layers
    manifest = _load_optional(output_dir, "manifest")
    layer1 = _load_optional(output_dir, "layer1_repo_surface")
    layer2 = _load_optional(output_dir, "layer2_ast_bindings")
    layer3 = _load_optional(output_dir, "layer3_compile_deps")
    layer4 = _load_optional(output_dir, "layer4_runtime_topology")
    layer5 = _load_optional(output_dir, "layer5_api_contracts")
    layer6 = _load_optional(output_dir, "layer6_data_flow")
    layer7 = _load_optional(output_dir, "layer7_service_components")
    layer8 = _load_optional(output_dir, "layer8_user_journeys")

    checks = []

    # --- Structural checks (1-8) ---
    checks.append(_check_file_coverage(manifest, layer1, layer2, layer7))
    checks.append(_check_cli_command_coverage(layer5, layer8))
    checks.append(_check_export_consistency(layer2))
    checks.append(_check_dependency_consistency(layer2, layer3))
    checks.append(_check_io_traceability(layer6, layer8))
    checks.append(_check_subprocess_traceability(layer4, layer8))
    checks.append(_check_package_consistency(layer1, layer3, layer7, manifest))
    checks.append(_check_route_coverage(layer5, layer8))

    # --- Semantic checks (9-15) ---
    checks.append(_check_import_resolution(layer2))
    checks.append(_check_cli_handler_reachability(layer5, layer2))
    checks.append(_check_dead_dep_cross_validation(layer2, layer3))
    checks.append(_check_circular_import_severity(layer3))
    checks.append(_check_env_var_completeness(layer4, manifest))
    checks.append(_check_route_test_coverage(layer5, manifest))
    checks.append(_check_reexport_chain_validation(layer2))

    # Overall status
    statuses = [c["status"] for c in checks]
    fail_count = statuses.count("FAIL")
    warn_count = statuses.count("WARN")
    skip_count = statuses.count("SKIP")

    if fail_count > 0:
        overall = "FAIL"
    elif warn_count > 0:
        overall = "PASS_WITH_WARNINGS"
    else:
        overall = "PASS"

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "checks": checks,
        "overall": overall,
        "pass_count": statuses.count("PASS"),
        "warning_count": warn_count,
        "failure_count": fail_count,
        "skip_count": skip_count,
    }


# ---------------------------------------------------------------------------
# Structural checks (1-8)
# ---------------------------------------------------------------------------


def _check_file_coverage(manifest, layer1, layer2, layer7) -> dict:
    """Check 1: Every .py file in manifest appears in layers 1, 2, 7."""
    name = "FILE_COVERAGE"
    if not manifest:
        return _skip(name, "manifest.json not found")

    py_files = {f["rel_path"] for f in manifest["files"] if f["extension"] == ".py"}
    missing_layers = []

    # Layer 1: check directory coverage (files grouped by dir)
    if layer1:
        l1_dirs = {d.get("rel_path", "") for d in layer1.get("directories", [])}
        # All dirs containing py files should exist
        py_dirs = {str(Path(f).parent) for f in py_files}
        missing_l1 = py_dirs - l1_dirs
        if missing_l1:
            missing_layers.append(f"layer1: {len(missing_l1)} dirs missing")
    else:
        missing_layers.append("layer1: not loaded")

    # Layer 2: check files_analyzed count
    if layer2:
        l2_count = layer2.get("files_analyzed", 0)
        expected = len(py_files)
        if l2_count != expected:
            missing_layers.append(f"layer2: analyzed {l2_count}/{expected}")
    else:
        missing_layers.append("layer2: not loaded")

    # Layer 7: check package coverage
    if layer7:
        l7_pkgs = {p["name"] for p in layer7.get("packages", [])}
        manifest_pkgs = set(manifest["summary"]["packages"])
        missing_pkgs = manifest_pkgs - l7_pkgs
        if missing_pkgs:
            missing_layers.append(f"layer7: {len(missing_pkgs)} packages missing")
    else:
        missing_layers.append("layer7: not loaded")

    if not missing_layers:
        return _pass(name, f"{len(py_files)} .py files covered across layers 1, 2, 7")

    all_critical = all("not loaded" not in m for m in missing_layers)
    status = "FAIL" if all_critical else "WARN"
    return _result(name, status, "; ".join(missing_layers), missing_layers)


def _check_cli_command_coverage(layer5, layer8) -> dict:
    """Check 2: Every CLI command in layer5 has a journey in layer8."""
    name = "CLI_COMMAND_COVERAGE"
    if not layer5:
        return _skip(name, "layer5 not found")
    if not layer8:
        return _skip(name, "layer8 not found")

    cli_commands = {c.get("command", "") for c in layer5.get("cli_commands", [])}
    journey_commands = {
        j.get("command", "") for j in layer8.get("journeys", []) if j.get("entry_type") == "cli"
    }

    missing = cli_commands - journey_commands
    if not missing:
        return _pass(name, f"{len(cli_commands)} CLI commands all have journeys")

    if len(missing) < len(cli_commands) * 0.2:
        return _result(
            name,
            "WARN",
            f"{len(cli_commands) - len(missing)}/{len(cli_commands)} covered",
            sorted(missing),
        )
    return _result(
        name,
        "FAIL",
        f"Only {len(cli_commands) - len(missing)}/{len(cli_commands)} covered",
        sorted(missing),
    )


def _check_export_consistency(layer2) -> dict:
    """Check 3: Every __all__ name in layer2 exists in definitions."""
    name = "EXPORT_CONSISTENCY"
    if not layer2:
        return _skip(name, "layer2 not found")

    invalid = []
    for exp in layer2.get("exports", []):
        if not exp.get("valid", True):
            for m in exp.get("missing_definitions", []):
                invalid.append(f"{exp['file']}::{m}")

    if not invalid:
        total = sum(len(e.get("all_names", [])) for e in layer2.get("exports", []))
        return _pass(name, f"{total} exported names all resolve to definitions")

    return _result(
        name, "WARN", f"{len(invalid)} exported names missing definitions", invalid[:20]
    )  # Cap at 20


def _check_dependency_consistency(layer2, layer3) -> dict:
    """Check 4: External deps in layer3 are imported from some file in layer2."""
    name = "DEPENDENCY_CONSISTENCY"
    if not layer2:
        return _skip(name, "layer2 not found")
    if not layer3:
        return _skip(name, "layer3 not found")

    # Get all third-party modules actually imported
    imported_modules = set()
    for imp in layer2.get("imports", []):
        if imp["category"] == "third_party":
            top = imp["module"].split(".")[0]
            imported_modules.add(top.lower().replace("-", "_"))

    # Check declared deps — only Python deps against Python imports.
    # Non-Python deps (Rust, JS, Go, etc.) are validated by their own tooling.
    unused = []
    python_deps = 0
    non_python_deps = 0
    for dep in layer3.get("external_dependencies", []):
        lang = dep.get("language", "python")
        if lang != "python":
            non_python_deps += 1
            continue
        python_deps += 1
        norm = dep.get("normalized_name", dep["name"]).lower().replace("-", "_")
        if dep.get("import_count", 0) == 0 and norm not in imported_modules:
            unused.append(dep["name"])

    if not unused:
        detail = f"All {python_deps} Python dependencies are imported"
        if non_python_deps:
            detail += f" ({non_python_deps} non-Python deps not checked against imports)"
        return _pass(name, detail)

    return _result(name, "WARN", f"{len(unused)} declared deps appear unused", unused)


def _check_io_traceability(layer6, layer8) -> dict:
    """Check 5: Every file_io in layer6 is reachable from some entry point."""
    name = "IO_TRACEABILITY"
    if not layer6:
        return _skip(name, "layer6 not found")
    if not layer8:
        return _skip(name, "layer8 not found")

    # Get all functions reached from journeys
    reached = set()
    for j in layer8.get("journeys", []):
        # We don't have per-function detail in journeys, use packages_touched as proxy
        reached.update(j.get("packages_touched", []))

    # Check if I/O files are in reached packages
    io_files = {e.get("file", "") for e in layer6.get("file_io", [])}
    unreachable = []
    for f in io_files:
        # Extract package
        pkg_parts = Path(f).parts
        # Rough check: is any parent package reached?
        found = False
        for pkg in reached:
            if pkg.replace(".", "/") in f:
                found = True
                break
        if not found:
            unreachable.append(f)

    if not unreachable:
        return _pass(name, f"{len(io_files)} I/O files all in reachable packages")

    return _result(
        name,
        "WARN",
        f"{len(unreachable)}/{len(io_files)} I/O files in unreachable packages",
        unreachable[:10],
    )


def _check_subprocess_traceability(layer4, layer8) -> dict:
    """Check 6: Every subprocess call in layer4 exists in call graph."""
    name = "SUBPROCESS_TRACEABILITY"
    if not layer4:
        return _skip(name, "layer4 not found")
    if not layer8:
        return _skip(name, "layer8 not found")

    sp_files = {e.get("file", "") for e in layer4.get("subprocess_calls", [])}
    reached_pkgs = set()
    for j in layer8.get("journeys", []):
        reached_pkgs.update(j.get("packages_touched", []))

    unreachable = []
    for f in sp_files:
        found = False
        for pkg in reached_pkgs:
            if pkg.replace(".", "/") in f:
                found = True
                break
        if not found:
            unreachable.append(f)

    total = len(sp_files)
    if not unreachable:
        return _pass(name, f"{total} subprocess call files all in reachable packages")

    return _result(
        name,
        "WARN",
        f"{len(unreachable)}/{total} subprocess files in unreachable packages",
        unreachable[:10],
    )


def _check_package_consistency(layer1, layer3, layer7, manifest) -> dict:
    """Check 7: Packages in layer1 == layer3 == layer7."""
    name = "PACKAGE_CONSISTENCY"
    if not manifest:
        return _skip(name, "manifest not found")

    manifest_pkgs = set(manifest["summary"]["packages"])
    issues = []

    if layer1:
        l1_pkgs = {
            d.get("rel_path", "").replace("/", ".")
            for d in layer1.get("directories", [])
            if d.get("role") == "package"
        }
        diff = manifest_pkgs.symmetric_difference(l1_pkgs)
        if diff:
            issues.append(f"layer1 vs manifest: {len(diff)} differences")

    if layer3:
        l3_pkgs = set(layer3.get("internal_import_graph", {}).get("nodes", []))
        if l3_pkgs:
            missing = manifest_pkgs - l3_pkgs
            extra = l3_pkgs - manifest_pkgs
            if missing or extra:
                issues.append(f"layer3 vs manifest: {len(missing)} missing, {len(extra)} extra")

    if layer7:
        l7_pkgs = {p["name"] for p in layer7.get("packages", [])}
        missing = manifest_pkgs - l7_pkgs
        if missing:
            issues.append(f"layer7 vs manifest: {len(missing)} missing packages")

    if not issues:
        return _pass(name, f"{len(manifest_pkgs)} packages consistent across layers")

    return _result(name, "WARN", "; ".join(issues), issues)


def _check_route_coverage(layer5, layer8) -> dict:
    """Check 8: Every HTTP route in layer5 has a journey in layer8."""
    name = "ROUTE_COVERAGE"
    if not layer5:
        return _skip(name, "layer5 not found")
    if not layer8:
        return _skip(name, "layer8 not found")

    routes = {
        f"{r.get('method', 'GET')} {r.get('path', '')}" for r in layer5.get("http_routes", [])
    }
    journey_routes = {
        j.get("command", "") for j in layer8.get("journeys", []) if j.get("entry_type") == "http"
    }

    missing = routes - journey_routes
    if not missing:
        return _pass(name, f"{len(routes)} HTTP routes all have journeys")

    return _result(
        name, "WARN", f"{len(routes) - len(missing)}/{len(routes)} routes covered", sorted(missing)
    )


# ---------------------------------------------------------------------------
# Semantic checks (9-15)
# ---------------------------------------------------------------------------


def _check_import_resolution(layer2) -> dict:
    """Check 9: Every resolved_target in layer2 imports defines the imported name."""
    name = "IMPORT_RESOLUTION"
    if not layer2:
        return _skip(name, "layer2 not found")

    # Build def index: file -> set of defined names
    def_by_file: dict[str, set[str]] = {}
    for defn in layer2.get("definitions", []):
        f = defn["file"]
        if f not in def_by_file:
            def_by_file[f] = set()
        def_by_file[f].add(defn["name"])

    # Also count re-exports from __init__.py
    export_by_file: dict[str, set[str]] = {}
    for exp in layer2.get("exports", []):
        export_by_file[exp["file"]] = set(exp.get("all_names", []))

    unresolved = []
    checked = 0
    for imp in layer2.get("imports", []):
        if imp["category"] != "internal":
            continue
        target = imp.get("resolved_target")
        if not target:
            continue

        target_defs = def_by_file.get(target, set())
        target_exports = export_by_file.get(target, set())
        available = target_defs | target_exports

        for imported_name in imp.get("names", []):
            if imported_name == "*":
                continue
            checked += 1
            if imported_name not in available:
                unresolved.append(f"{imp['file']} imports {imported_name} from {target}")

    if not unresolved:
        return _pass(name, f"{checked} internal import names all resolve")

    return _result(name, "WARN", f"{len(unresolved)}/{checked} imports unresolved", unresolved[:20])


def _check_cli_handler_reachability(layer5, layer2) -> dict:
    """Check 10: Every add_parser has a set_defaults handler that exists."""
    name = "CLI_HANDLER_REACHABILITY"
    if not layer5:
        return _skip(name, "layer5 not found")
    if not layer2:
        return _skip(name, "layer2 not found")

    # Check that handler functions exist in definitions
    def_set = {(d["file"], d["name"]) for d in layer2.get("definitions", [])}

    missing_handlers = []
    for cmd in layer5.get("cli_commands", []):
        handler = cmd.get("handler_function")
        handler_file = cmd.get("file")
        if handler and handler_file:
            if (handler_file, handler) not in def_set:
                missing_handlers.append(f"{cmd.get('command', '')}: {handler}")

    if not missing_handlers:
        total = len(layer5.get("cli_commands", []))
        return _pass(name, f"{total} CLI commands have reachable handlers")

    return _result(
        name, "WARN", f"{len(missing_handlers)} handlers not found in definitions", missing_handlers
    )


def _check_dead_dep_cross_validation(layer2, layer3) -> dict:
    """Check 11: Unused deps in layer3 verified against layer2 imports."""
    name = "DEAD_DEP_CROSS_VALIDATION"
    if not layer3:
        return _skip(name, "layer3 not found")
    if not layer2:
        return _skip(name, "layer2 not found")

    unused_in_l3 = set(layer3.get("unused_dependencies", []))
    if not unused_in_l3:
        return _pass(name, "No unused dependencies declared in layer3")

    # Cross-validate: search layer2 imports for any reference
    imported_modules = set()
    for imp in layer2.get("imports", []):
        if imp["category"] == "third_party":
            imported_modules.add(imp["module"].split(".")[0].lower().replace("-", "_"))

    confirmed_unused = []
    for dep in unused_in_l3:
        norm = dep.lower().replace("-", "_")
        if norm not in imported_modules:
            confirmed_unused.append(dep)

    if len(confirmed_unused) == len(unused_in_l3):
        return _pass(name, f"{len(confirmed_unused)} unused deps confirmed by layer2")

    false_positives = unused_in_l3 - set(confirmed_unused)
    return _result(
        name,
        "WARN",
        f"{len(false_positives)} deps marked unused in layer3 but found in layer2",
        sorted(false_positives),
    )


def _check_circular_import_severity(layer3) -> dict:
    """Check 12: Cycles scored by module-level vs function-level."""
    name = "CIRCULAR_IMPORT_SEVERITY"
    if not layer3:
        return _skip(name, "layer3 not found")

    cycles = layer3.get("circular_dependencies", [])
    if not cycles:
        return _pass(name, "No circular dependencies detected")

    # Separate vendor cycles from internal cycles
    vendor_cycles = []
    internal_cycles = []
    for c in cycles:
        cycle_path = c.get("cycle", [])
        if any("vendor" in node for node in cycle_path):
            vendor_cycles.append(c)
        else:
            internal_cycles.append(c)

    total = len(cycles)
    details = (
        f"{total} circular dependency cycles found "
        f"({len(internal_cycles)} internal, {len(vendor_cycles)} vendor)"
    )

    # Vendor cycles are informational (we don't control vendored code)
    # Internal cycles are warnings (common in Python, usually work at runtime)
    return _result(name, "WARN", details, [str(c.get("cycle", [])) for c in internal_cycles[:10]])


def _check_env_var_completeness(layer4, manifest) -> dict:
    """Check 13: Env vars read in code vs .env.example."""
    name = "ENV_VAR_COMPLETENESS"
    if not layer4:
        return _skip(name, "layer4 not found")

    env_vars = {e.get("variable", "") for e in layer4.get("env_var_reads", []) if e.get("variable")}

    if not env_vars:
        return _pass(name, "No environment variables detected")

    # Resolve .env.example relative to manifest root (repo root), not cwd
    manifest_root = Path(manifest["root"]).parent if manifest else Path(".")
    env_example = manifest_root / ".env.example"
    documented_vars: set[str] = set()
    if env_example.exists():
        for line in env_example.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                documented_vars.add(line.split("=")[0].strip())

    undocumented = env_vars - documented_vars
    if not undocumented:
        return _pass(name, f"{len(env_vars)} env vars all documented in .env.example")

    if not env_example.exists():
        return _result(
            name,
            "WARN",
            f"{len(env_vars)} env vars found but no .env.example file",
            sorted(env_vars)[:20],
        )

    return _result(
        name,
        "WARN",
        f"{len(undocumented)}/{len(env_vars)} env vars not in .env.example",
        sorted(undocumented)[:20],
    )


def _check_route_test_coverage(layer5, manifest) -> dict:
    """Check 14: HTTP routes with at least one test file referencing handler."""
    name = "ROUTE_TEST_COVERAGE"
    if not layer5:
        return _skip(name, "layer5 not found")
    if not manifest:
        return _skip(name, "manifest not found")

    routes = layer5.get("http_routes", [])
    if not routes:
        return _pass(name, "No HTTP routes to check")

    test_files = [f for f in manifest["files"] if f.get("is_test", False)]
    test_contents: dict[str, str] = {}
    for tf in test_files:
        try:
            test_contents[tf["path"]] = Path(tf["path"]).read_text(errors="replace")
        except OSError as e:
            print(f"WARNING: could not read test file {tf['path']}: {e}", file=sys.stderr)

    untested = []
    for route in routes:
        handler = route.get("function", "")
        if not handler:
            continue
        found = False
        for _path, content in test_contents.items():
            if handler in content:
                found = True
                break
        if not found:
            untested.append(f"{route.get('method', '?')} {route.get('path', '?')} ({handler})")

    if not untested:
        return _pass(name, f"{len(routes)} HTTP routes all have test references")

    return _result(
        name, "WARN", f"{len(untested)}/{len(routes)} routes without test references", untested
    )


def _check_reexport_chain_validation(layer2) -> dict:
    """Check 15: __init__.py re-export chains resolve correctly."""
    name = "REEXPORT_CHAIN_VALIDATION"
    if not layer2:
        return _skip(name, "layer2 not found")

    # Find __init__.py exports that import names from submodules
    init_exports = [e for e in layer2.get("exports", []) if e["file"].endswith("__init__.py")]

    if not init_exports:
        return _pass(name, "No __init__.py re-exports to validate")

    broken_chains = []
    for exp in init_exports:
        for missing in exp.get("missing_definitions", []):
            broken_chains.append(f"{exp['file']}::{missing}")

    if not broken_chains:
        total = sum(len(e.get("all_names", [])) for e in init_exports)
        return _pass(name, f"{total} __init__.py re-export names all resolve")

    return _result(
        name, "WARN", f"{len(broken_chains)} broken re-export chains", broken_chains[:20]
    )


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------


def _pass(name: str, details: str) -> dict:
    return {"name": name, "status": "PASS", "details": details, "missing": []}


def _skip(name: str, reason: str) -> dict:
    return {"name": name, "status": "SKIP", "details": reason, "missing": []}


def _result(name: str, status: str, details: str, missing: list) -> dict:
    return {"name": name, "status": status, "details": details, "missing": missing}


def main():
    """CLI entry point for cross-layer checks."""
    parser = argparse.ArgumentParser(description="Cross-layer completeness checks")
    parser.add_argument("--output", required=True, help="Output directory containing layer JSONs")
    args = parser.parse_args()

    output_dir = Path(args.output).resolve()

    report = run_checks(output_dir)

    # Write report
    out_path = output_dir / "cross_layer_report.json"
    out_path.write_text(json.dumps(report, indent=2))

    # Print summary
    print(f"Cross-layer checks: {report['overall']}")
    print(
        f"  PASS: {report['pass_count']}  WARN: {report['warning_count']}  "
        f"FAIL: {report['failure_count']}  SKIP: {report['skip_count']}"
    )
    print()
    for check in report["checks"]:
        status_icon = {"PASS": "+", "WARN": "~", "FAIL": "!", "SKIP": "-"}[check["status"]]
        print(f"  [{status_icon}] {check['name']}: {check['details']}")
        if check["missing"] and check["status"] != "PASS":
            for item in check["missing"][:5]:
                print(f"      - {item}")
            if len(check["missing"]) > 5:
                print(f"      ... and {len(check['missing']) - 5} more")

    print(f"\n  Output: {out_path} ({out_path.stat().st_size} bytes)")

    if report["failure_count"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
