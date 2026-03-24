---
title: "Layer 7: Service Components"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 7: Service Components
</nav>

# Layer 7: Service Components

<div class="atlas-metadata">
Category: <strong>Structural</strong> | Generated: 2026-03-24T05:01:46Z
</div>

## PR #3500 Impact Refresh

This layer was refreshed for the Copilot parity control-plane slice.

- `src/amplihack/__init__.py` now gates `install`, `mode`, `recipe`, and `update` through the installed Rust CLI before falling back to Python CLI parsing.
- `recipes/rust_runner.py` now delegates subprocess execution and progress-file writes to `rust_runner_execution.py` instead of carrying a duplicate execution path.
- `launcher/copilot.py` remains the staged `.github/` surface for Copilot, while the nested recipe path relies on the smaller recipe-runner support modules.

## Map

### Mermaid

![Service Components (Mermaid)](service-components-mermaid.svg)

### DOT

![Service Components (DOT)](service-components-dot.svg)

## Cross-References

- [Layer 2: AST + LSP Bindings](../ast-lsp-bindings/index.md)
- [Layer 3: Compile-time Dependencies](../compile-deps/index.md)
