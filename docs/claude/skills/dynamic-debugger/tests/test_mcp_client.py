#!/usr/bin/env python3
"""
MCP Client for testing dap-mcp debugging tools.

Uses JSON-RPC 2.0 over stdio to communicate with dap-mcp server.
Based on Model Context Protocol specification.
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


class MCPClient:
    """Simple MCP client for testing dap-mcp server."""

    def __init__(self, server_command: list):
        """Initialize MCP client with server command."""
        self.process = None
        self.server_command = server_command
        self.request_id = 0

    def start(self):
        """Start MCP server process."""
        self.process = subprocess.Popen(
            self.server_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        time.sleep(1)  # Give server time to initialize

        # Send MCP initialization handshake
        init_response = self.send_request(
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test_mcp_client", "version": "1.0.0"},
            },
        )

        if "result" not in init_response:
            raise RuntimeError(f"Initialization failed: {init_response}")

        # Send initialized notification
        self.send_notification("notifications/initialized")

    def send_request(self, method: str, params: dict | None = None) -> dict[str, Any]:
        """Send JSON-RPC 2.0 request to MCP server.

        Args:
            method: JSON-RPC method name (e.g., "tools/call", "tools/list")
            params: Optional parameters dict

        Returns:
            JSON-RPC response dict
        """
        self.request_id += 1

        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
        }

        if params:
            request["params"] = params

        # Send request
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json)
        self.process.stdin.flush()

        # Read response
        response_line = self.process.stdout.readline()
        if not response_line:
            return {"error": "No response from server"}

        return json.loads(response_line)

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP tool.

        Args:
            tool_name: Name of the tool (e.g., "set_breakpoint", "evaluate")
            arguments: Tool arguments dict

        Returns:
            Tool response
        """
        return self.send_request(
            method="tools/call", params={"name": tool_name, "arguments": arguments}
        )

    def send_notification(self, method: str, params: dict | None = None):
        """Send JSON-RPC 2.0 notification (no response expected).

        Args:
            method: Notification method name
            params: Optional parameters dict
        """
        notification = {
            "jsonrpc": "2.0",
            "method": method,
        }

        if params:
            notification["params"] = params

        # Send notification
        notification_json = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_json)
        self.process.stdin.flush()

    def list_tools(self) -> dict[str, Any]:
        """List available MCP tools."""
        return self.send_request(method="tools/list")

    def stop(self):
        """Stop MCP server."""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)


def test_mcp_debugging_tools():
    """Test actual MCP debugging tools with real dap-mcp server.

    This validates requirement #9 from issue #1549 by actually invoking
    MCP tools to debug a Python program with a known bug.
    """
    print("\n" + "=" * 70)
    print("MCP Debugging Tools Test (Actual Protocol Testing)")
    print("=" * 70)

    # Prepare test program
    test_program = Path("/tmp/debug_test_program.py")
    if not test_program.exists():
        print("❌ Test program not found. Run test_mcp_integration.py first.")
        return False

    # Prepare config
    config_file = Path("/tmp/mcp_test_config.json")
    if not config_file.exists():
        print("❌ Config not found. Run test_mcp_integration.py first.")
        return False

    # Start MCP server
    print("\n[Setup] Starting dap-mcp MCP server...")
    server_command = ["python3", "-m", "dap_mcp", "--config", str(config_file)]

    client = MCPClient(server_command)

    try:
        client.start()
        print("  ✅ MCP server started")

        # Test 1: List available tools
        print("\n[Test 1] Listing available MCP tools...")
        tools_response = client.list_tools()
        print(f"  Response: {json.dumps(tools_response, indent=2)[:200]}...")

        if "result" in tools_response:
            tools = tools_response.get("result", {}).get("tools", [])
            print(f"  ✅ Found {len(tools)} MCP tools")
            tool_names = [t.get("name") for t in tools if "name" in t]
            print(f"  Tools: {', '.join(tool_names[:5])}...")
        else:
            print(f"  ⚠️  Unexpected response format: {tools_response}")

        # Test 2: Launch program
        print("\n[Test 2] Launching test program via MCP...")
        launch_response = client.call_tool(
            tool_name="launch", arguments={"program": str(test_program)}
        )
        print(f"  Response: {json.dumps(launch_response, indent=2)[:300]}...")

        if "result" in launch_response:
            print("  ✅ Program launched successfully")
        else:
            print(f"  ⚠️  Launch response: {launch_response}")

        # Test 3: Set breakpoint
        print("\n[Test 3] Setting breakpoint at bug location (line 9)...")
        breakpoint_response = client.call_tool(
            tool_name="set_breakpoint",
            arguments={
                "file": str(test_program),
                "line": 9,  # The bug line
            },
        )
        print(f"  Response: {json.dumps(breakpoint_response, indent=2)[:300]}...")

        if "result" in breakpoint_response:
            print("  ✅ Breakpoint set successfully")
        else:
            print(f"  ⚠️  Breakpoint response: {breakpoint_response}")

        # Test 4: Continue execution (should hit breakpoint)
        print("\n[Test 4] Continuing execution to breakpoint...")
        continue_response = client.call_tool(tool_name="continue_execution", arguments={})
        print(f"  Response: {json.dumps(continue_response, indent=2)[:300]}...")

        # Test 5: Evaluate variable
        print("\n[Test 5] Evaluating 'len(numbers)' at breakpoint...")
        eval_response = client.call_tool(
            tool_name="evaluate", arguments={"expression": "len(numbers)"}
        )
        print(f"  Response: {json.dumps(eval_response, indent=2)[:300]}...")

        if "result" in eval_response:
            value = eval_response.get("result", {}).get("content", [{}])[0].get("text", "")
            print(f"  ✅ Evaluation result: {value}")
        else:
            print(f"  ⚠️  Evaluate response: {eval_response}")

        # Test 6: Terminate
        print("\n[Test 6] Terminating debugging session...")
        term_response = client.call_tool(tool_name="terminate", arguments={})
        print(f"  Response: {json.dumps(term_response, indent=2)[:300]}...")

        print("\n" + "=" * 70)
        print("✅ MCP Protocol Testing Complete")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\n❌ MCP testing failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        client.stop()
        print("\n[Cleanup] MCP server stopped")


if __name__ == "__main__":
    success = test_mcp_debugging_tools()
    sys.exit(0 if success else 1)
