"""Orchestrator: run all atlas extraction layers in correct phase order.

Phase 1: manifest (common.build_manifest)
Phase 2: layer1, layer2, layer4 (parallel-safe, but run sequentially for simplicity)
Phase 3: layer3, layer5, layer6 (depend on layer2)
Phase 4: layer7 (depends on 2, 3)
Phase 5: layer8 (depends on 2, 4, 5, 6)
Phase 6: cross_layer_checks

For each script: subprocess.run, check exit code, abort on failure.
Prints timing for each layer and total time.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
from scripts.atlas.common import build_manifest


def run_layer(script_path: str, args: list[str], label: str) -> tuple[bool, float]:
    """Run a layer script and return (success, elapsed_seconds).

    Args:
        script_path: Path to the Python script.
        args: Additional CLI arguments.
        label: Display label for this layer.

    Returns:
        Tuple of (success bool, elapsed seconds).
    """
    start = time.monotonic()
    cmd = [sys.executable, script_path] + args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        print(f"  TIMEOUT {label} after {elapsed:.1f}s")
        return False, elapsed

    elapsed = time.monotonic() - start

    if result.stdout.strip():
        for line in result.stdout.strip().splitlines():
            print(f"  {line}")

    if result.returncode != 0:
        print(f"  FAILED {label} (exit {result.returncode}) in {elapsed:.1f}s")
        if result.stderr.strip():
            for line in result.stderr.strip().splitlines()[:10]:
                print(f"    stderr: {line}")
        return False, elapsed

    print(f"  OK {label} in {elapsed:.1f}s")
    return True, elapsed


def main():
    """Run all atlas layers in order."""
    parser = argparse.ArgumentParser(description="Run all atlas extraction layers")
    parser.add_argument("--root", required=True, help="Project root directory")
    parser.add_argument("--output", required=True, help="Output directory for all JSON files")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    scripts_dir = Path(__file__).resolve().parent
    python_dir = scripts_dir / "python"

    common_args = ["--root", str(root), "--output", str(output_dir)]
    total_start = time.monotonic()
    timings: list[tuple[str, float]] = []

    # --- Phase 1: Manifest ---
    print("Phase 1: Manifest")
    manifest_start = time.monotonic()
    manifest_path = output_dir / "manifest.json"
    manifest = build_manifest(root)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    manifest_elapsed = time.monotonic() - manifest_start
    print(f"  OK manifest ({manifest['total_files']} files) in {manifest_elapsed:.1f}s")
    timings.append(("manifest", manifest_elapsed))

    # --- Phase 2: layer1, layer2, layer4 ---
    print("\nPhase 2: layer1, layer2, layer4")
    phase2_scripts = [
        (str(python_dir / "layer1_repo_surface.py"), "layer1_repo_surface"),
        (str(python_dir / "layer2_ast_bindings.py"), "layer2_ast_bindings"),
    ]
    # layer4 only if script exists
    layer4_script = python_dir / "layer4_runtime_topology.py"
    if layer4_script.exists():
        phase2_scripts.append((str(layer4_script), "layer4_runtime_topology"))

    for script, label in phase2_scripts:
        ok, elapsed = run_layer(script, common_args, label)
        timings.append((label, elapsed))
        if not ok:
            _abort(label, timings, total_start)

    # --- Phase 3: layer3, layer5, layer6 ---
    print("\nPhase 3: layer3, layer5, layer6")
    phase3_scripts = []
    for name in ("layer3_compile_deps", "layer5_api_contracts", "layer6_data_flow"):
        script = python_dir / f"{name}.py"
        if script.exists():
            phase3_scripts.append((str(script), name))
        else:
            print(f"  SKIP {name} (script not found)")

    for script, label in phase3_scripts:
        ok, elapsed = run_layer(script, common_args, label)
        timings.append((label, elapsed))
        if not ok:
            _abort(label, timings, total_start)

    # --- Phase 4: layer7 ---
    print("\nPhase 4: layer7")
    layer7_script = str(python_dir / "layer7_service_components.py")
    ok, elapsed = run_layer(layer7_script, common_args, "layer7_service_components")
    timings.append(("layer7_service_components", elapsed))
    if not ok:
        _abort("layer7_service_components", timings, total_start)

    # --- Phase 5: layer8 ---
    print("\nPhase 5: layer8")
    layer8_script = str(python_dir / "layer8_user_journeys.py")
    ok, elapsed = run_layer(layer8_script, common_args, "layer8_user_journeys")
    timings.append(("layer8_user_journeys", elapsed))
    if not ok:
        _abort("layer8_user_journeys", timings, total_start)

    # --- Phase 6: cross-layer checks ---
    print("\nPhase 6: cross_layer_checks")
    checks_script = str(scripts_dir / "cross_layer_checks.py")
    ok, elapsed = run_layer(checks_script, ["--output", str(output_dir)], "cross_layer_checks")
    timings.append(("cross_layer_checks", elapsed))
    if not ok:
        # Cross-layer check failures are warnings, not fatal
        print("  (cross-layer check failures are non-fatal)")

    # --- Summary ---
    total_elapsed = time.monotonic() - total_start
    print(f"\n{'='*60}")
    print(f"Atlas extraction complete in {total_elapsed:.1f}s")
    print(f"{'='*60}")
    print("\nTiming breakdown:")
    for label, elapsed in timings:
        bar = "#" * int(elapsed * 2)
        print(f"  {label:30s} {elapsed:6.1f}s {bar}")
    print(f"  {'TOTAL':30s} {total_elapsed:6.1f}s")

    # List output files
    print(f"\nOutput files in {output_dir}:")
    for f in sorted(output_dir.glob("*.json")):
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name:40s} {size_kb:7.1f} KB")

    sys.exit(0)


def _abort(failed_label: str, timings: list, total_start: float):
    """Print summary and abort on failure."""
    total_elapsed = time.monotonic() - total_start
    print(f"\nABORTED: {failed_label} failed after {total_elapsed:.1f}s total")
    print("\nCompleted layers:")
    for label, elapsed in timings:
        print(f"  {label:30s} {elapsed:6.1f}s")
    sys.exit(1)


if __name__ == "__main__":
    main()
