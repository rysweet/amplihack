---
title: "Layer 2: AST + LSP Bindings"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 2: AST + LSP Bindings
</nav>

# Layer 2: AST + LSP Bindings

<div class="atlas-metadata">
Category: <strong>Structural</strong> | Generated: 2026-03-24T05:01:46Z
</div>

## PR #3500 Impact Refresh

This layer was refreshed for the Copilot parity control-plane slice.

- `.claude/tools/xpia/hooks/pre_tool_use.py` now binds directly to `amplihack.security.rust_xpia` as the canonical fail-closed Bash policy entrypoint.
- `pre_tool_use_rust.py` is now only a compatibility shim, reducing drift between the old and canonical entrypoints.
- `rust_runner.py` now binds to `rust_runner_execution._run_rust_process()` for live progress streaming and deterministic progress-file writes.

## Map

### Mermaid

![AST+LSP Symbol Bindings - Mermaid](ast-lsp-bindings-mermaid.svg)

### DOT

![AST+LSP Symbol Bindings - Graphviz](ast-lsp-bindings-dot.svg)

## Cross-References

- [Layer 7: Service Components](../service-components/index.md)
- [Layer 3: Compile-time Dependencies](../compile-deps/index.md)
