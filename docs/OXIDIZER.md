# Oxidizer Workflow

The Oxidizer workflow automates Python-to-Rust migration through iterative
convergence loops. It treats the Python codebase as the living specification
and produces a fully-tested Rust equivalent with zero-tolerance parity
validation.

## Overview

Oxidizer is a recipe-driven workflow that:

- Analyzes the Python codebase (AST, dependencies, types, public API)
- Ensures complete test coverage before any porting begins
- Scaffolds a Rust project with the correct structure
- Ports tests first, then implementation module-by-module
- Runs quality and degradation audits on every iteration
- Loops until 100% feature parity is achieved

## Quick Start

```bash
recipe-runner-rs amplifier-bundle/recipes/oxidizer-workflow.yaml \
  --set python_package_path=src/mypackage \
  --set rust_target_path=rust/mypackage \
  --set rust_repo_name=my-rust-crate \
  --set rust_repo_org=myorg
```

## Required Context Variables

| Variable              | Description                           | Example                   |
| --------------------- | ------------------------------------- | ------------------------- |
| `python_package_path` | Path to the Python package to migrate | `src/amplihack/recipes`   |
| `rust_target_path`    | Where to create the Rust project      | `rust/recipe-runner`      |
| `rust_repo_name`      | GitHub repository name for the output | `amplihack-recipe-runner` |
| `rust_repo_org`       | GitHub org or user                    | `rysweet`                 |

## Workflow Phases

### Phase 1: Analysis

Performs comprehensive analysis of the Python codebase:

- AST analysis of every module
- Dependency graph mapping
- Type inference for function signatures
- Public API surface extraction
- Migration priority ordering (leaf modules first)

### Phase 1B: Test Completeness Gate

**This gate blocks all further progress until test coverage is sufficient.**

1. Measures current Python test coverage
2. Identifies untested code paths
3. Writes missing tests
4. Re-verifies coverage
5. If coverage is still insufficient → **workflow stops**

### Phase 2: Scaffolding

Creates the Rust project structure:

- `cargo init` with appropriate dependencies
- Module structure mirroring the Python package
- CI configuration (clippy, fmt, test)
- README and documentation scaffolding

### Phase 3: Test Extraction

Ports Python tests to Rust before any implementation:

- Converts pytest fixtures to Rust test helpers
- Maps Python assertions to Rust equivalents
- Runs a quality audit on extracted tests
- Tests are expected to fail at this point (no implementation yet)

### Phase 4–6: Iterative Convergence

Each iteration processes one module:

```
┌─────────────────────────────────────────────┐
│  Select next module (priority order)         │
│  ↓                                           │
│  Implement module in Rust                    │
│  ↓                                           │
│  Compare: feature matrix diff vs Python      │
│  ↓                                           │
│  Quality gate: clippy + fmt + test           │
│  ↓                                           │
│  Silent degradation audit                    │
│  ↓                                           │
│  Fix any degradation found                   │
│  ↓                                           │
│  Convergence check                           │
│  ↓                                           │
│  < 100% parity? → loop again                 │
│  = 100% parity? → done                       │
└─────────────────────────────────────────────┘
```

The recipe unrolls 5 explicit loop iterations. The `max_depth: 8` recursion
setting allows sub-recipes to recurse further if needed. The `max_iterations`
context variable (default: 30) provides an upper bound.

## Zero-Tolerance Policy

The oxidizer enforces strict standards:

- **No partial convergence** — `allow_partial_convergence` is `false`
- **Parity target is 100%** — anything less loops again
- **Silent degradation audit** — catches lossy type conversions, missing error
  variants, dropped edge cases, and behavioral differences
- **Unsafe code audit** — flags every `unsafe` block as a critical finding;
  requires elimination or justification with safety comments and Miri testing
- **Quality gate** — `cargo clippy -- -D warnings`, `cargo fmt --check`, full
  test suite must pass

## Effective Rust Compliance

All generated Rust code follows the [Effective Rust](https://effective-rust.com/)
guide. Key rules enforced on every iteration:

### Types (Items 1–6)

- Use `enum` with data fields — make invalid states unrepresentable
- `Option<T>` for optional values, never sentinel values
- `Result<T, E>` for fallible ops, never panic on expected errors
- Newtype pattern for domain semantics (`struct Miles(f64)`)
- `From`/`Into` conversions over `as` casts
- `thiserror` for library errors, `anyhow` for applications

### Unsafe (Item 16)

- `#![deny(unsafe_code)]` in lib.rs by default
- If FFI requires `unsafe`: isolate in wrapper, add safety comments, run Miri
- See <https://effective-rust.com/unsafe.html>

### Parallelism (Item 17)

- Prefer channels over shared state
- `Arc<Mutex<T>>` with small lock scopes, single-lock grouping
- Never invoke closures or return `MutexGuard` with locks held
- See <https://effective-rust.com/deadlock.html>

### Tooling (Items 29, 31, 32)

- `cargo clippy -- -D warnings`, `cargo fmt`, `cargo doc`
- `rust-toolchain.toml` for reproducible CI builds
- `cargo-deny` for license/advisory checks, `cargo-udeps` for unused deps
- See <https://effective-rust.com/use-tools.html>

## Using via Python API

```python
from amplihack.recipes import run_recipe_by_name

result = run_recipe_by_name(
    "oxidizer-workflow",
    user_context={
        "python_package_path": "src/mypackage",
        "rust_target_path": "rust/mypackage",
        "rust_repo_name": "my-rust-crate",
        "rust_repo_org": "myorg",
    },
)

if result.success:
    print("Migration complete — 100% parity achieved")
else:
    for sr in result.step_results:
        if sr.error:
            print(f"  {sr.step_id}: {sr.error}")
```

## Recipe Location

The oxidizer recipe lives at:

```
amplifier-bundle/recipes/oxidizer-workflow.yaml
```

## Customization

Override any context variable with `--set`:

```bash
recipe-runner-rs amplifier-bundle/recipes/oxidizer-workflow.yaml \
  --set max_iterations=50 \
  --set parity_target=100
```

The recipe is designed to be used as-is for most migrations. For specialized
needs, copy the recipe and modify the agent prompts in each phase.
