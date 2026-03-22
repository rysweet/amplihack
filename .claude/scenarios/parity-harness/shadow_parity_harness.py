#!/usr/bin/env python3
"""Generic shadow-mode parity harness for CLI migration validation.

Runs two CLI implementations side-by-side in isolated sandboxes,
comparing outputs, exit codes, and filesystem side effects.

Usage:
    # Basic: compare two binaries
    python shadow_parity_harness.py \\
        --legacy "python -m myapp.cli" \\
        --candidate "./target/debug/myapp" \\
        --scenario scenarios/smoke.yaml

    # With shadow logging (no failures, just log divergences)
    python shadow_parity_harness.py \\
        --legacy "python -m myapp.cli" \\
        --candidate "./target/debug/myapp" \\
        --scenario scenarios/*.yaml \\
        --shadow-mode \\
        --shadow-log /tmp/divergences.jsonl

    # Built-in quick-check (no scenario file needed)
    python shadow_parity_harness.py \\
        --legacy "python -m myapp.cli" \\
        --candidate "./target/debug/myapp" \\
        --builtin-cases '{"cases":[{"name":"version","argv":["--version"],"compare":["exit_code"]}]}'

Design:
    - Isolated sandboxes: each engine gets its own HOME, TMPDIR, PATH
    - No git collision: GIT_AUTHOR/COMMITTER set to shadow identity
    - No host pollution: all artifacts in /tmp with unique run IDs
    - JSON-semantic comparison: ignores key ordering differences
    - Atomic JSONL divergence log: safe for concurrent append
    - Timeout handling: captures partial output on timeout, doesn't crash

Scenario YAML format:
    See PARITY_SCENARIO_FORMAT.md for the full specification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class HarnessConfig:
    """Configuration for a parity harness run."""
    legacy_command: list[str]
    candidate_command: list[str]
    log_dir: Path = Path("/tmp/parity-shadow")
    keep_sandboxes: bool = False
    shadow_mode: bool = False
    shadow_log: Path | None = None
    run_id: str = field(default_factory=lambda: f"parity-{int(time.time())}")
    default_timeout: int = 30


@dataclass
class EngineResult:
    """Result from running one engine on a test case."""
    stdout: str
    stderr: str
    exit_code: int
    sandbox_root: Path


@dataclass
class CaseResult:
    """Comparison result for a single test case."""
    case_name: str
    category: str
    match: bool
    legacy: EngineResult
    candidate: EngineResult
    divergences: list[dict[str, Any]]
    duration_ms: int
    timestamp: str


# ---------------------------------------------------------------------------
# Sandbox isolation
# ---------------------------------------------------------------------------

def create_sandbox(run_id: str, engine: str, case_name: str) -> Path:
    """Create an isolated sandbox directory."""
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in case_name)[:40]
    sandbox = Path(tempfile.mkdtemp(prefix=f"{run_id}-{engine}-{safe}-"))
    (sandbox / "home").mkdir()
    (sandbox / "tmp").mkdir()
    return sandbox


def build_env(
    sandbox: Path,
    extra_env: dict[str, str] | None = None,
    python_path: str | None = None,
) -> dict[str, str]:
    """Build isolated environment for a sandbox run."""
    env = os.environ.copy()
    home = sandbox / "home"
    env["HOME"] = str(home)
    env["TMPDIR"] = str(sandbox / "tmp")
    env["TMP"] = str(sandbox / "tmp")
    env["TEMP"] = str(sandbox / "tmp")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["GIT_AUTHOR_NAME"] = "parity-shadow"
    env["GIT_AUTHOR_EMAIL"] = "shadow@parity.test"
    env["GIT_COMMITTER_NAME"] = "parity-shadow"
    env["GIT_COMMITTER_EMAIL"] = "shadow@parity.test"
    env["PARITY_SHADOW_RUN"] = "1"
    env["SANDBOX_ROOT"] = str(sandbox)
    if python_path:
        env["PYTHONPATH"] = python_path
    if extra_env:
        for k, v in extra_env.items():
            rendered = v.replace("${SANDBOX_ROOT}", str(sandbox))
            rendered = rendered.replace("${HOME}", str(home))
            rendered = rendered.replace("${PATH}", env.get("PATH", ""))
            env[k] = rendered
    return env


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def run_engine(
    command: list[str],
    argv: list[str],
    sandbox: Path,
    env: dict[str, str],
    cwd: str = ".",
    stdin_data: str = "",
    timeout: int = 30,
) -> EngineResult:
    """Run a single engine (legacy or candidate) in its sandbox."""
    full_cmd = command + argv
    run_cwd = sandbox / cwd
    run_cwd.mkdir(parents=True, exist_ok=True)
    env["SANDBOX_ROOT"] = str(sandbox)

    try:
        result = subprocess.run(
            full_cmd,
            cwd=run_cwd,
            env=env,
            input=stdin_data,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return EngineResult(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
            sandbox_root=sandbox,
        )
    except subprocess.TimeoutExpired as e:
        return EngineResult(
            stdout=e.stdout.decode("utf-8", errors="replace") if e.stdout else "",
            stderr=f"TIMEOUT after {timeout}s",
            exit_code=124,
            sandbox_root=sandbox,
        )
    except Exception as e:
        return EngineResult(
            stdout="",
            stderr=f"ERROR: {e}",
            exit_code=1,
            sandbox_root=sandbox,
        )


def run_setup(script: str | None, sandbox: Path, env: dict[str, str]) -> None:
    """Run setup script in a sandbox."""
    if not script:
        return
    subprocess.run(
        ["bash", "-lc", script],
        cwd=sandbox,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def normalize_text(text: str, sandbox: Path) -> str:
    """Normalize output by replacing sandbox-specific paths."""
    result = text.replace(str(sandbox), "<SANDBOX>")
    result = result.replace(str(sandbox / "home"), "<HOME>")
    return result.strip()


def try_parse_json(text: str) -> Any | None:
    """Try to parse text as JSON."""
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None


def snapshot_path(path: Path) -> dict[str, Any]:
    """Create a comparable snapshot of a file or directory."""
    if not path.exists():
        return {"exists": False}
    if path.is_file():
        data = path.read_bytes()
        text = None
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            pass
        return {
            "exists": True,
            "type": "file",
            "sha256": hashlib.sha256(data).hexdigest(),
            "text": text,
        }
    entries = {}
    for child in sorted(path.rglob("*")):
        if child.is_file():
            rel = child.relative_to(path).as_posix()
            entries[rel] = hashlib.sha256(child.read_bytes()).hexdigest()
    return {"exists": True, "type": "dir", "entries": entries}


def compare_case(
    case: dict[str, Any],
    legacy: EngineResult,
    candidate: EngineResult,
) -> tuple[bool, list[dict[str, Any]]]:
    """Compare legacy and candidate results for a test case."""
    divergences = []
    match = True

    for target in case.get("compare", ["stdout", "stderr", "exit_code"]):
        if target == "exit_code":
            if legacy.exit_code != candidate.exit_code:
                divergences.append({
                    "field": "exit_code",
                    "legacy": legacy.exit_code,
                    "candidate": candidate.exit_code,
                })
                match = False

        elif target == "stdout":
            l_norm = normalize_text(legacy.stdout, legacy.sandbox_root)
            c_norm = normalize_text(candidate.stdout, candidate.sandbox_root)
            # JSON-semantic comparison
            l_json = try_parse_json(l_norm)
            c_json = try_parse_json(c_norm)
            if l_json is not None and c_json is not None:
                if l_json != c_json:
                    divergences.append({
                        "field": "stdout", "mode": "json",
                        "legacy": l_norm[:500], "candidate": c_norm[:500],
                    })
                    match = False
            elif l_norm != c_norm:
                divergences.append({
                    "field": "stdout",
                    "legacy": l_norm[:500], "candidate": c_norm[:500],
                })
                match = False

        elif target == "stderr":
            l_norm = normalize_text(legacy.stderr, legacy.sandbox_root)
            c_norm = normalize_text(candidate.stderr, candidate.sandbox_root)
            if l_norm != c_norm:
                divergences.append({
                    "field": "stderr",
                    "legacy": l_norm[:500], "candidate": c_norm[:500],
                })
                match = False

        elif target.startswith("fs:"):
            rel = target[3:]
            l_snap = snapshot_path(legacy.sandbox_root / rel)
            c_snap = snapshot_path(candidate.sandbox_root / rel)
            if l_snap != c_snap:
                divergences.append({
                    "field": target,
                    "legacy": _truncate(l_snap),
                    "candidate": _truncate(c_snap),
                })
                match = False

        elif target.startswith("jsonfs:"):
            rel = target[7:]
            l_data = _load_json_file(legacy.sandbox_root / rel)
            c_data = _load_json_file(candidate.sandbox_root / rel)
            if l_data != c_data:
                divergences.append({
                    "field": target,
                    "legacy": l_data, "candidate": c_data,
                })
                match = False

    return match, divergences


def _truncate(snap: dict[str, Any]) -> dict[str, Any]:
    result = dict(snap)
    if "text" in result and result["text"] and len(str(result["text"])) > 500:
        result["text"] = str(result["text"])[:500] + "..."
    return result


def _load_json_file(path: Path) -> Any:
    if not path.exists():
        return {"exists": False}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"exists": True, "error": "invalid JSON"}


# ---------------------------------------------------------------------------
# Harness runner
# ---------------------------------------------------------------------------

def run_case(config: HarnessConfig, case: dict[str, Any]) -> CaseResult:
    """Run a single test case through both engines and compare."""
    name = case["name"]
    category = case.get("category", "default")
    start = time.monotonic()

    l_sandbox = create_sandbox(config.run_id, "legacy", name)
    c_sandbox = create_sandbox(config.run_id, "candidate", name)

    try:
        argv = case.get("argv", [])
        stdin_data = case.get("stdin", "")
        timeout = int(case.get("timeout", config.default_timeout))
        extra_env = case.get("env", {})
        cwd = case.get("cwd", ".")
        setup = case.get("setup", "")

        l_env = build_env(l_sandbox, extra_env)
        c_env = build_env(c_sandbox, extra_env)

        if setup:
            run_setup(setup, l_sandbox, l_env)
            run_setup(setup, c_sandbox, c_env)

        legacy = run_engine(
            config.legacy_command, argv, l_sandbox, l_env, cwd, stdin_data, timeout
        )
        candidate = run_engine(
            config.candidate_command, argv, c_sandbox, c_env, cwd, stdin_data, timeout
        )

        match, divergences = compare_case(case, legacy, candidate)
        elapsed = int((time.monotonic() - start) * 1000)

        return CaseResult(
            case_name=name, category=category, match=match,
            legacy=legacy, candidate=candidate,
            divergences=divergences, duration_ms=elapsed,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    finally:
        if not config.keep_sandboxes:
            shutil.rmtree(l_sandbox, ignore_errors=True)
            shutil.rmtree(c_sandbox, ignore_errors=True)


def run_harness(
    config: HarnessConfig,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Run the full harness over all cases."""
    config.log_dir.mkdir(parents=True, exist_ok=True)
    results: list[CaseResult] = []

    for i, case in enumerate(cases, 1):
        name = case["name"]
        print(f"[{i}/{len(cases)}] {name} ... ", end="", flush=True)
        result = run_case(config, case)
        results.append(result)
        status = "MATCH" if result.match else "DIVERGED"
        print(f"{status} ({result.duration_ms}ms)")

        if not result.match and config.shadow_log:
            with open(config.shadow_log, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "run_id": config.run_id,
                    "case": name,
                    "category": result.category,
                    "divergences": result.divergences,
                    "timestamp": result.timestamp,
                }, sort_keys=True) + "\n")

    matched = sum(1 for r in results if r.match)
    total = len(results)
    by_category: dict[str, dict[str, int]] = {}
    for r in results:
        cat = r.category
        if cat not in by_category:
            by_category[cat] = {"matched": 0, "diverged": 0}
        by_category[cat]["matched" if r.match else "diverged"] += 1

    summary = {
        "run_id": config.run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "matched": matched,
        "diverged": total - matched,
        "parity_rate": f"{matched / total * 100:.1f}%" if total else "N/A",
        "by_category": by_category,
        "divergence_details": [
            {"case": r.case_name, "divergences": r.divergences}
            for r in results if not r.match
        ],
    }

    summary_path = config.log_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"PARITY SUMMARY ({config.run_id})")
    print(f"{'='*60}")
    print(f"Total: {total}  Matched: {matched}  Diverged: {total - matched}  Rate: {summary['parity_rate']}")
    for cat, counts in sorted(by_category.items()):
        print(f"  {cat}: {counts['matched']} match, {counts['diverged']} diverged")
    print(f"Summary: {summary_path}")
    if config.shadow_log:
        print(f"Shadow log: {config.shadow_log}")

    return summary


# ---------------------------------------------------------------------------
# Scenario loading
# ---------------------------------------------------------------------------

def load_scenarios(paths: list[Path]) -> list[dict[str, Any]]:
    """Load test cases from one or more YAML scenario files."""
    import yaml  # lazy import — only needed when loading files
    cases = []
    for path in paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "cases" in data:
            for c in data["cases"]:
                c.setdefault("category", path.stem)
            cases.extend(data["cases"])
    return cases


def parse_command(cmd_str: str) -> list[str]:
    """Parse a command string into a list, respecting shell quoting."""
    return shlex.split(cmd_str)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generic shadow-mode parity harness for CLI migration validation"
    )
    parser.add_argument("--legacy", required=True, help="Legacy command (e.g. 'python -m myapp.cli')")
    parser.add_argument("--candidate", required=True, help="Candidate command (e.g. './target/debug/myapp')")
    parser.add_argument("--scenario", nargs="*", type=Path, help="YAML scenario file(s)")
    parser.add_argument("--builtin-cases", help="Inline JSON cases (for quick checks)")
    parser.add_argument("--log-dir", type=Path, default=Path("/tmp/parity-shadow"))
    parser.add_argument("--shadow-mode", action="store_true", help="Log divergences but don't fail")
    parser.add_argument("--shadow-log", type=Path, help="JSONL divergence log path")
    parser.add_argument("--keep-sandboxes", action="store_true")
    parser.add_argument("--timeout", type=int, default=30, help="Default per-case timeout")
    parser.add_argument("--case", action="append", help="Run only named case(s)")
    args = parser.parse_args()

    config = HarnessConfig(
        legacy_command=parse_command(args.legacy),
        candidate_command=parse_command(args.candidate),
        log_dir=args.log_dir,
        keep_sandboxes=args.keep_sandboxes,
        shadow_mode=args.shadow_mode,
        shadow_log=args.shadow_log,
        default_timeout=args.timeout,
    )

    cases: list[dict[str, Any]] = []
    if args.scenario:
        cases.extend(load_scenarios(args.scenario))
    if args.builtin_cases:
        inline = json.loads(args.builtin_cases)
        if isinstance(inline, dict) and "cases" in inline:
            cases.extend(inline["cases"])

    if not cases:
        print("ERROR: No test cases. Provide --scenario or --builtin-cases.", file=sys.stderr)
        return 1

    if args.case:
        requested = set(args.case)
        cases = [c for c in cases if c["name"] in requested]

    summary = run_harness(config, cases)
    if args.shadow_mode:
        return 0
    return 0 if summary["diverged"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
