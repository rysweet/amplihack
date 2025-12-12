# Future Language Support

These debugger configurations are prepared for future implementation but **not currently supported** by dap-mcp.

## Unsupported Languages (Pending dap-mcp Extension)

The following languages require extending dap-mcp to add new debugger type classes:

- **node.json** - JavaScript/TypeScript (Node debugger)
- **gdb.json** - C/C++ alternative (GDB)
- **delve.json** - Go (Delve debugger)
- **rust-gdb.json** - Rust (rust-gdb wrapper)
- **java.json** - Java (JDWP)
- **dotnet.json** - .NET (vsdbg)

## Current dap-mcp Support

**Supported NOW:**

- ✅ debugpy (Python) - `../debugpy.json`
- ✅ lldb (C/C++/Rust) - `../lldb.json`

## How to Add Support

To add these languages, contribute to dap-mcp project:

1. Create new config class in `dap_mcp/config.py`:

   ```python
   class NodeDebugger(DAPConfig):
       type: Literal["node"]
       # Add node-specific fields
   ```

2. Update union type to include new class

3. Implement DAP protocol handler if needed

## Tracking Issue

See issue #1554 for tracking additional language support implementation.

## Alternative Approaches

- **Direct DAP**: Bypass MCP, use DAP protocol directly (more complex)
- **Multiple MCP Servers**: Use different MCP servers for different languages
- **Wait for Community**: dap-mcp may add support over time

---

**Note:** These configs use simplified format (5-6 fields). When implementing,
ensure they match actual dap-mcp schema requirements (see `../debugpy.json` and
`../lldb.json` for correct format).
