# Layer 7: Service Component Architecture

Internal packages/modules within the amplihack monolith, with a focused refresh for the Copilot parity control-plane slice.

## Scope

This refresh focuses on the modules changed by PR #3500:

- `src/amplihack/__init__.py` as the root entrypoint and Rust-first command gate
- `src/amplihack/recipes/*` as the recipe-runner control plane
- `src/amplihack/launcher/copilot.py` as the staged Copilot launcher surface

## Recent Impact Notes

- `amplihack.__init__.py` now treats `install`, `mode`, `recipe`, and `update` as Rust-first commands when an installed Rust CLI is available, then falls back to the Python CLI for everything else.
- The recipe runner is no longer a single monolith. `rust_runner.py` now delegates subprocess execution and progress-file writes to `rust_runner_execution.py`, keeps version checks in `rust_runner_binary.py`, and preserves nested Copilot compatibility in `rust_runner_copilot.py`.
- The Copilot launcher remains the staging surface for `.github/hooks/*`, but the nested recipe path now depends on the smaller recipe-runner support modules instead of duplicating execution logic.

## Package Summary

| Package                                    | Public / Control-Plane Surface                                          | Current Role                                                                                                      |
| ------------------------------------------ | ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `amplihack/__init__.py`                    | `main()`, `RUST_FIRST_COMMANDS`, `_delegate_to_rust_cli_if_supported()` | Root entrypoint that routes selected commands to the installed Rust CLI before falling back to Python CLI parsing |
| `launcher/copilot.py`                      | `stage_hooks()` and generated `.github/hooks/pre-tool-use` wrapper      | Stages the Copilot-native control plane and aggregates amplihack + XPIA permission decisions                      |
| `recipes/rust_runner.py`                   | `run_recipe_via_rust()`                                                 | Builds the Rust-runner invocation and parses structured JSON results                                              |
| `recipes/rust_runner_binary.py`            | `find_rust_binary()`, `raise_for_runner_version()`                      | Rust runner discovery and strict version gating                                                                   |
| `recipes/rust_runner_execution.py`         | `_run_rust_process()`, progress file helpers                            | Owns subprocess execution, stderr progress streaming, and deterministic progress-file writes                      |
| `recipes/rust_runner_copilot.py`           | nested Copilot wrapper generation                                       | Normalizes nested Copilot prompt and permission flags without widening explicit permissions                       |
| `recipes/rust_runner_recipe_resolution.py` | recipe lookup helpers                                                   | Resolves bundled vs repo-local recipes without overloading `rust_runner.py`                                       |

## Diagrams

### Mermaid Diagram

![Service Components (Mermaid)](service-components-mermaid.svg)

### DOT Diagram

![Service Components (DOT)](service-components-dot.svg)

**Source files:** [service-components.mmd](service-components.mmd) | [service-components.dot](service-components.dot)
