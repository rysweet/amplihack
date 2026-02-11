# Design Decision: LSP Integration Strategy

**Date**: 2026-02-11
**Status**: Decided
**Decision**: Deliver LSP capabilities through language-specific dev-tools bundles, not as separate LSP suite

---

## Context

The amplihack ecosystem expansion needed to add multi-language LSP support (Python, TypeScript, JavaScript, Rust) for semantic code intelligence. Two approaches were considered:

1. **Separate LSP Suite**: Include standalone LSP bundles (`lsp-python`, `lsp-typescript`, `lsp-rust`) alongside dev-tools
2. **Integrated via Dev-Tools**: Rely on dev-tools bundles which already include LSP capabilities

## Investigation (Phase 1)

### Key Findings

**Python Development Bundle** (`microsoft/amplifier-bundle-python-dev`):

- Repository description: "Includes lsp-python for code intelligence"
- Already bundles LSP capabilities within the dev-tools package
- Provides: ruff (linting/formatting), pyright (type checking), AND pylsp (LSP intelligence)

**TypeScript Development Bundle** (`microsoft/amplifier-bundle-ts-dev`):

- Documentation states: "The bundle includes the core lsp bundle, which provides the tool-lsp module"
- Already bundles typescript-language-server
- Provides: eslint (linting), prettier (formatting), tsserver (type checking), AND LSP intelligence

**Rust**: No `rust-dev` bundle exists yet, but `lsp-rust` standalone bundle is available

### Architectural Analysis

Microsoft's design philosophy is **language-specific integration**, not separation of concerns:

```
✅ MICROSOFT'S APPROACH:
python-dev = linting + formatting + type checking + LSP intelligence (all Python tooling together)
ts-dev = linting + formatting + type checking + LSP intelligence (all TypeScript tooling together)

❌ NOT MICROSOFT'S APPROACH:
lsp-suite = all LSP servers (language-agnostic abstraction)
dev-tools = only quality checks (separated from intelligence)
```

## Decision

**Use Microsoft's integrated approach**: Include dev-tools bundles which bring LSP capabilities with them.

### Implementation

amplihack will include:

1. `python-dev` → provides Python quality tools + LSP intelligence
2. `ts-dev` → provides TypeScript/JavaScript quality tools + LSP intelligence
3. `lsp-rust` → provides Rust LSP intelligence (standalone, pending rust-dev bundle)

### Rationale

**Pros**:

- ✅ Follows Microsoft's established bundle architecture
- ✅ Simpler mental model: "Install python-dev for all Python needs"
- ✅ Avoids redundancy: No need to include both `python-dev` AND `lsp-python`
- ✅ Fewer dependency edges: 2-3 bundles instead of 6-7
- ✅ Easier maintenance: Updates to dev-tools automatically include LSP updates

**Cons**:

- ⚠️ Users wanting "only LSP without quality tools" must include full dev-tools bundle
- ⚠️ Less granular control over which capabilities to enable
- ⚠️ Rust is inconsistent (standalone LSP until rust-dev exists)

### Trade-off Analysis

We prioritize **simplicity and alignment with upstream architecture** over granular control. Users who need fine-grained control can fork and customize their own bundle includes.

## Documentation Impact

### What Changes

1. **SECURITY.md**: Merge "LSP Suite" and "Dev Tools" into single "Dev Tools with Integrated LSP" section
2. **PRIVACY.md**: Clarify that LSP data flows are part of dev-tools, not separate
3. **PREREQUISITES.md**: Update LSP setup to reference dev-tools installation
4. **docs/index.md**: Update Language Support Matrix to show "Delivered via dev-tools"
5. **Implementation**: Create `dev-tools.yaml` behavior (python-dev + ts-dev + lsp-rust), NOT `lsp-suite.yaml`

### What Stays the Same

- Language support matrix: Still Python, TypeScript, JavaScript, Rust
- LSP features: Still full semantic intelligence (go-to-def, hover, refs, autocomplete)
- Security posture: Still "local-only, no data transmission"

## Future Considerations

If Microsoft releases:

- `rust-dev` → Replace standalone `lsp-rust` with integrated `rust-dev`
- `go-dev`, `java-dev`, etc. → Follow same pattern (include dev bundle, not separate LSP)

## References

- [microsoft/amplifier-bundle-python-dev](https://github.com/microsoft/amplifier-bundle-python-dev) - "Includes lsp-python for code intelligence"
- [microsoft/amplifier-bundle-lsp-typescript](https://github.com/microsoft/amplifier-bundle-lsp-typescript) - "The bundle includes the core lsp bundle"
- Original design spec: `design-multi-language-lsp-integration.md`

## Approval

**Architect Review**: Approved (Phase 1 investigation requirement satisfied)
**Implementation**: Ready to proceed to Phase 2 (behavior YAML creation)
