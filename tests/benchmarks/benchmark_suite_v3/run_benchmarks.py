#!/usr/bin/env python3
"""
Benchmark Suite v3 Runner

Runs all 4 benchmark tasks against specified models and collects comprehensive results.

Features:
- Automated worktree creation for isolated execution
- claude-trace integration for detailed API logging
- Result collection with metrics (duration, turns, cost, tool calls)
- Support for multiple models and selective task execution
- Quality assessment via reviewer agents (optional)

Usage:
    python run_benchmarks.py --all                    # Run all benchmarks
    python run_benchmarks.py --model opus             # Run Opus only
    python run_benchmarks.py --tasks 1,2,3,4         # Run specific tasks
    python run_benchmarks.py --quality-assessment    # Include code quality scoring
"""

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class BenchmarkTask:
    """A benchmark task definition."""

    id: str
    name: str
    complexity: str
    prompt: str
    expected_files: int


@dataclass
class BenchmarkResult:
    """Results from running a benchmark."""

    task_id: str
    model: str
    duration_ms: int = 0
    num_turns: int = 0
    cost_usd: float = 0.0
    success: bool = False
    session_id: str = ""
    trace_log: str = ""
    model_usage: dict = field(default_factory=dict)
    error: str = ""
    quality_score: float = 0.0  # 0-5 scale from reviewer agent
    tool_calls: int = 0
    subagent_calls: int = 0
    skills_used: list = field(default_factory=list)


# Task definitions
TASKS = [
    BenchmarkTask(
        id="task1_greeting",
        name="Simple - Greeting Utility",
        complexity="Low",
        prompt="""Create a simple greeting utility:
1) Create src/amplihack/utils/greeting.py with greet(name) function that returns 'Hello, {name}!'
2) Create tests/unit/test_greeting.py with one test
3) Run the test
Use TDD approach. Complete all steps without asking questions.""",
        expected_files=2,
    ),
    BenchmarkTask(
        id="task2_config",
        name="Medium - Configuration Manager",
        complexity="Medium",
        prompt="""Create a configuration manager module:
1) Create src/amplihack/config/manager.py with a ConfigManager class that:
   - Loads config from YAML files
   - Supports environment variable overrides (AMPLIHACK_* prefix)
   - Has get(key, default=None) and set(key, value) methods
   - Validates required keys on initialization
2) Create tests/unit/test_config_manager.py with tests for:
   - Loading from YAML
   - Environment variable override
   - Default values
   - Validation errors
3) Create a sample config file at config/default.yaml
4) Run all tests
Use TDD approach. Handle edge cases. Complete all steps without asking questions.""",
        expected_files=3,
    ),
    BenchmarkTask(
        id="task3_plugins",
        name="Complex - CLI Plugin System",
        complexity="High",
        prompt="""Implement a plugin system for CLI commands:
1) Create src/amplihack/plugins/base.py with:
   - Abstract PluginBase class with execute(args) method
   - PluginRegistry singleton for registering/discovering plugins
   - @register_plugin decorator
2) Create src/amplihack/plugins/loader.py with:
   - Function to discover plugins from a directory
   - Function to load plugin by name
   - Validation that plugins implement PluginBase
3) Create src/amplihack/plugins/builtin/hello.py as example plugin
4) Create tests/unit/test_plugin_system.py with tests for:
   - Plugin registration
   - Plugin discovery
   - Plugin loading
   - Invalid plugin handling
5) Create tests/integration/test_plugin_integration.py testing end-to-end flow
6) Update src/amplihack/plugins/__init__.py with public API
7) Run all tests
Use TDD approach. Follow SOLID principles. Complete all steps without asking questions.""",
        expected_files=6,
    ),
    BenchmarkTask(
        id="task4_api_client",
        name="Advanced - REST API Client",
        complexity="Very High",
        prompt="""Create a robust REST API client library:
1) Create src/amplihack/api/client.py with APIClient class:
   - Configurable base_url, timeout, headers
   - Methods: get, post, put, delete
   - Automatic retry with exponential backoff (max 3 retries)
   - Rate limiting support (respect 429 responses)
   - Request/response logging
2) Create src/amplihack/api/exceptions.py with custom exceptions:
   - APIError (base)
   - RateLimitError
   - TimeoutError
   - AuthenticationError
3) Create src/amplihack/api/models.py with:
   - Request/Response dataclasses
   - Serialization helpers
4) Create tests/unit/test_api_client.py testing:
   - Successful requests
   - Retry behavior
   - Rate limit handling
   - Timeout handling
   - Error responses
5) Create tests/unit/test_api_exceptions.py
6) Create tests/integration/test_api_integration.py with mock server
7) Update src/amplihack/api/__init__.py with public API
8) Run all tests
Use TDD approach. Handle all edge cases. Follow best practices for HTTP clients. Complete all steps without asking questions.""",
        expected_files=7,
    ),
]


def create_worktree(base_dir: Path, name: str) -> Path:
    """Create a fresh git worktree for benchmarking."""
    worktree_path = base_dir / "worktrees" / name

    # Remove if exists
    if worktree_path.exists():
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree_path)],
            cwd=base_dir,
            capture_output=True,
        )

    # Create new worktree from main
    subprocess.run(
        ["git", "worktree", "add", str(worktree_path), "main"],
        cwd=base_dir,
        check=True,
        capture_output=True,
    )

    # Set up venv
    subprocess.run(
        ["python3", "-m", "venv", ".venv"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Install dependencies
    subprocess.run(
        [str(worktree_path / ".venv" / "bin" / "pip"), "install", "-e", ".[dev]"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    return worktree_path


def run_benchmark(
    worktree: Path,
    task: BenchmarkTask,
    model: str,
    output_dir: Path,
) -> BenchmarkResult:
    """Run a single benchmark task."""
    result = BenchmarkResult(task_id=task.id, model=model)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trace_log = output_dir / f"{task.id}_{model}_{timestamp}.jsonl"

    # Find claude executable - check env var first, then PATH
    claude_path = os.environ.get("CLAUDE_PATH", shutil.which("claude"))
    if not claude_path:
        raise RuntimeError(
            "claude command not found. Please ensure it's in your PATH or set CLAUDE_PATH environment variable."
        )

    # Build command
    cmd = [
        "claude-trace",
        "--claude-path",
        claude_path,
        "--run-with",
        "--dangerously-skip-permissions",
        "--model",
        model,
        "--output-format",
        "json",
        "-p",
        f"/amplihack:ultrathink {task.prompt}",
    ]

    try:
        start_time = time.time()
        proc = subprocess.run(
            cmd,
            cwd=worktree,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour max
            env={
                **os.environ,
                "PATH": f"{worktree / '.venv' / 'bin'}:{os.environ['PATH']}",
            },
        )
        duration = (time.time() - start_time) * 1000

        # Parse JSON output
        for line in proc.stdout.split("\n"):
            if line.startswith('{"type":"result"'):
                data = json.loads(line)
                result.duration_ms = data.get("duration_ms", int(duration))
                result.num_turns = data.get("num_turns", 0)
                result.cost_usd = data.get("total_cost_usd", 0.0)
                result.success = data.get("subtype") == "success"
                result.session_id = data.get("session_id", "")
                result.model_usage = data.get("modelUsage", {})
                break

        result.trace_log = str(trace_log)

    except subprocess.TimeoutExpired:
        result.error = "Timeout after 1 hour"
    except Exception as e:
        result.error = str(e)

    return result


def main():
    """Run all benchmarks."""
    # Use environment variable or current working directory
    base_dir = Path(os.environ.get("AMPLIHACK_BASE_DIR", Path.cwd()))
    output_dir = base_dir / ".claude" / "runtime" / "benchmarks" / "suite_v3"
    output_dir.mkdir(parents=True, exist_ok=True)

    models = ["claude-opus-4-5-20251101", "claude-sonnet-4-5-20250929"]

    results: list[BenchmarkResult] = []

    for model in models:
        model_short = "opus" if "opus" in model else "sonnet"

        for task in TASKS:
            print(f"\n{'=' * 60}")
            print(f"Running: {task.name}")
            print(f"Model: {model_short}")
            print(f"{'=' * 60}")

            # Create fresh worktree
            worktree_name = f"bench-{model_short}-{task.id}"
            worktree = create_worktree(base_dir, worktree_name)

            # Run benchmark
            result = run_benchmark(worktree, task, model, output_dir)
            results.append(result)

            # Print progress
            status = "SUCCESS" if result.success else "FAILED"
            print(f"  Status: {status}")
            print(f"  Duration: {result.duration_ms / 1000:.1f}s")
            print(f"  Turns: {result.num_turns}")
            print(f"  Cost: ${result.cost_usd:.2f}")

    # Save all results
    results_file = output_dir / "all_results.json"
    with open(results_file, "w") as f:
        json.dump(
            [
                {
                    "task_id": r.task_id,
                    "model": r.model,
                    "duration_ms": r.duration_ms,
                    "num_turns": r.num_turns,
                    "cost_usd": r.cost_usd,
                    "success": r.success,
                    "session_id": r.session_id,
                    "trace_log": r.trace_log,
                    "model_usage": r.model_usage,
                    "error": r.error,
                }
                for r in results
            ],
            f,
            indent=2,
        )

    print(f"\n\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()
