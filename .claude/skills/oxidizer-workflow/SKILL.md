---
name: oxidizer-workflow
description: |
  Automated Python-to-Rust migration via iterative convergence loops.
  Treats the Python codebase as the living specification and produces a
  fully-tested Rust equivalent with zero-tolerance parity validation.
  Use when migrating Python modules, libraries, or CLIs to Rust.
  Activates for: migration, oxidize, python to rust, port to rust, rewrite in rust.
---

# Oxidizer Workflow Skill

## Purpose

Orchestrates the `oxidizer-workflow` recipe to migrate Python codebases to Rust.
The workflow is recursive and goal-seeking — it loops until 100% feature parity
is achieved, with quality audit and silent degradation checks on every iteration.

## When to Use

- Migrating a Python module, package, or CLI to Rust
- Porting a Python library to a standalone Rust crate
- Creating a Rust binary that replaces a Python tool

## Core Principles

1. **Tests first** — Python test coverage must be complete before any porting begins
2. **Zero tolerance** — 100% parity required; partial results are not accepted
3. **Quality gates** — Every iteration runs clippy, fmt, and a full test suite
4. **No silent degradation** — Every feature, edge case, and error path must be preserved
5. **Iterative convergence** — Module-by-module, loop until converged

## Required Inputs

| Input                 | Example                   | Description                           |
| --------------------- | ------------------------- | ------------------------------------- |
| `python_package_path` | `src/amplihack/recipes`   | Path to the Python package to migrate |
| `rust_target_path`    | `rust/recipe-runner`      | Where to create the Rust project      |
| `rust_repo_name`      | `amplihack-recipe-runner` | GitHub repo name for the Rust project |
| `rust_repo_org`       | `rysweet`                 | GitHub org or user for the repo       |

## Execution

### Via Recipe Runner

```bash
recipe-runner-rs amplifier-bundle/recipes/oxidizer-workflow.yaml \
  --set python_package_path=src/mypackage \
  --set rust_target_path=rust/mypackage \
  --set rust_repo_name=my-rust-package \
  --set rust_repo_org=myorg
```

### Via Python API

```python
from amplihack.recipes import run_recipe_by_name
from amplihack.recipes.adapters.cli_subprocess import CLISubprocessAdapter

result = run_recipe_by_name(
    "oxidizer-workflow",
    adapter=CLISubprocessAdapter(),
    user_context={
        "python_package_path": "src/mypackage",
        "rust_target_path": "rust/mypackage",
        "rust_repo_name": "my-rust-package",
        "rust_repo_org": "myorg",
    },
)
```

## Workflow Phases

```
Phase 1: Analysis
  └─ AST analysis, dependency mapping, type inference, public API extraction

Phase 1B: Test Completeness Gate
  └─ Measure coverage → write missing tests → re-verify → BLOCK if < 100%

Phase 2: Scaffolding
  └─ cargo init, add dependencies, create module structure

Phase 3: Test Extraction
  └─ Port Python tests to Rust test modules → quality audit tests

Phase 4-6: Iterative Convergence Loop (× N until 100% parity)
  ├─ Select next module (priority order from Phase 1)
  ├─ Implement module in Rust
  ├─ Compare: feature matrix diff against Python
  ├─ Quality gate: cargo clippy + fmt + test
  ├─ Silent degradation audit: check for lossy conversions
  ├─ Fix any degradation found
  └─ Convergence check: if < 100% parity → loop again

Final: Summary report with parity matrix
```

## Convergence Rules

- Each iteration processes one module at a time (core-out strategy)
- Up to 5 unrolled loops in the recipe, plus `max_depth: 8` for sub-recipes
- The recipe terminates when `convergence_status == "CONVERGED"` or
  `iteration_number > max_iterations` (default 30)
- If max iterations reached without convergence, the final summary reports
  which modules are still incomplete

## What Success Looks Like

- Rust project builds cleanly (`cargo build`)
- All tests pass (`cargo test`)
- Zero clippy warnings (`cargo clippy -- -D warnings`)
- Formatted (`cargo fmt --check`)
- Feature parity matrix shows 100% coverage
- No silent degradation detected
