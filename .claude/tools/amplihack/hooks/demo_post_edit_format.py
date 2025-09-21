#!/usr/bin/env python3
"""
Demo script for post_edit_format.py hook.
Shows how the hook automatically formats files after Edit tool usage.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run_hook(tool_use_data: dict) -> dict:
    """Simulate running the hook with given tool use data"""
    hook_path = Path(__file__).parent / "post_edit_format.py"

    # Prepare input
    input_data = {"toolUse": tool_use_data}
    input_json = json.dumps(input_data)

    # Run hook
    result = subprocess.run(
        [sys.executable, str(hook_path)],
        input=input_json,
        capture_output=True,
        text=True,
    )

    # Parse output
    if result.returncode == 0 and result.stdout:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {}
    return {}


def create_sample_files(temp_dir: Path) -> dict:
    """Create sample files with formatting issues"""
    files = {}

    # Unformatted Python file
    py_file = temp_dir / "example.py"
    py_file.write_text("""def  hello( name ):
    print(  "Hello, " + name  )
    return   True


class  MyClass:
    def __init__(  self, value  ):
        self.value=value
    def get_value(self):
        return  self.value
""")
    files["python"] = py_file

    # Unformatted JSON file
    json_file = temp_dir / "config.json"
    json_file.write_text(
        '{"name":"test","version":"1.0","dependencies":{"lib1":"1.2.3","lib2":"4.5.6"},"scripts":{"test":"pytest","lint":"ruff"}}'
    )
    files["json"] = json_file

    # Unformatted JavaScript file
    js_file = temp_dir / "script.js"
    js_file.write_text("""function  calculate( x,y ){
    const result=x+y;
    console.log(  'Result: '+result );
    return   result;
}

const  data={name:'test',value:42,items:[1,2,3,4,5]};
""")
    files["javascript"] = js_file

    # Unformatted Markdown file
    md_file = temp_dir / "README.md"
    md_file.write_text("""# My Project

This is  a test  project.

## Features
- Feature  1
-  Feature 2
-   Feature 3

### Code Example
```python
def hello():
    print("Hello")
```

## Installation
Run  `npm install`  to  install.
""")
    files["markdown"] = md_file

    return files


def demo_edit_tool():
    """Demonstrate Edit tool formatting"""
    print("=" * 60)
    print("DEMO: Post-Edit Auto-Formatting Hook")
    print("=" * 60)
    print()

    # Create temp directory with sample files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        files = create_sample_files(temp_path)

        # Test each file type
        for file_type, file_path in files.items():
            print(f"\n--- Testing {file_type.upper()} file ---")
            print(f"File: {file_path.name}")

            # Show original content (first few lines)
            original_content = file_path.read_text()
            print("\nOriginal content (first 200 chars):")
            print(
                original_content[:200] + "..." if len(original_content) > 200 else original_content
            )

            # Simulate Edit tool usage
            tool_use = {
                "name": "Edit",
                "parameters": {
                    "file_path": str(file_path),
                    "old_string": "dummy",  # Not used by hook
                    "new_string": "dummy",  # Not used by hook
                },
            }

            # Run the hook
            print("\nRunning formatting hook...")
            output = run_hook(tool_use)

            if output.get("message"):
                print(output["message"])
            else:
                print("No formatting performed (formatter may not be available)")

            # Show formatted content (if changed)
            new_content = file_path.read_text()
            if new_content != original_content:
                print("\nFormatted content (first 200 chars):")
                print(new_content[:200] + "..." if len(new_content) > 200 else new_content)
            else:
                print("\nContent unchanged")

            print("-" * 40)


def demo_multi_edit():
    """Demonstrate MultiEdit tool formatting"""
    print("\n" + "=" * 60)
    print("DEMO: MultiEdit Tool Formatting")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a Python file
        py_file = Path(temp_dir) / "multi_edit.py"
        py_file.write_text("""def func1():pass
def func2():pass
def func3():pass""")

        print(f"\nFile: {py_file.name}")
        print("Original content:")
        print(py_file.read_text())

        # Simulate MultiEdit tool usage
        tool_use = {
            "name": "MultiEdit",
            "parameters": {
                "file_path": str(py_file),
                "edits": [
                    {"old_string": "pass", "new_string": "return None"},
                ],
            },
        }

        print("\nRunning formatting hook after MultiEdit...")
        output = run_hook(tool_use)

        if output.get("message"):
            print(output["message"])

        print("\nFormatted content:")
        print(py_file.read_text())


def demo_environment_config():
    """Demonstrate environment-based configuration"""
    print("\n" + "=" * 60)
    print("DEMO: Environment Configuration")
    print("=" * 60)

    print("\n1. Testing with formatting DISABLED:")
    os.environ["CLAUDE_AUTO_FORMAT"] = "false"

    with tempfile.TemporaryDirectory() as temp_dir:
        py_file = Path(temp_dir) / "test.py"
        py_file.write_text("def  hello( ): pass")

        tool_use = {"name": "Edit", "parameters": {"file_path": str(py_file)}}
        output = run_hook(tool_use)

        print(f"   Result: {output or 'No formatting (disabled)'}")

    print("\n2. Testing with formatting ENABLED:")
    os.environ["CLAUDE_AUTO_FORMAT"] = "true"

    with tempfile.TemporaryDirectory() as temp_dir:
        py_file = Path(temp_dir) / "test.py"
        py_file.write_text("def  hello( ): pass")

        tool_use = {"name": "Edit", "parameters": {"file_path": str(py_file)}}
        output = run_hook(tool_use)

        if output.get("message"):
            print(f"   Result: {output['message']}")
        else:
            print("   Result: Formatting attempted (formatter may not be available)")

    # Clean up environment
    os.environ.pop("CLAUDE_AUTO_FORMAT", None)


def check_available_formatters():
    """Check which formatters are available on the system"""
    print("\n" + "=" * 60)
    print("Available Formatters on This System")
    print("=" * 60)

    formatters = [
        ("Python", ["black", "ruff", "autopep8"]),
        ("JavaScript/TypeScript", ["prettier", "eslint"]),
        ("JSON", ["prettier", "jq"]),
        ("Markdown", ["prettier", "mdformat"]),
    ]

    for lang, tools in formatters:
        print(f"\n{lang}:")
        for tool in tools:
            try:
                result = subprocess.run(
                    ["which", tool], capture_output=True, text=True, check=False
                )
                if result.returncode == 0:
                    print(f"  ✓ {tool} - Available at {result.stdout.strip()}")
                else:
                    print(f"  ✗ {tool} - Not found")
            except Exception:
                print(f"  ✗ {tool} - Error checking")


def main():
    """Run all demos"""
    print("\n" + "=" * 60)
    print(" POST-EDIT FORMATTING HOOK DEMO")
    print("=" * 60)
    print("""
This demo shows how the post_edit_format.py hook automatically
formats files after they are edited using Claude Code's Edit tools.

The hook:
- Detects when Edit, MultiEdit, Write, or NotebookEdit tools are used
- Identifies the file type from the extension
- Runs appropriate formatters if available
- Reports formatting changes to the user
    """)

    # Check available formatters first
    check_available_formatters()

    print("\n" + "=" * 60)
    print("Press Enter to continue with demos...")
    input()

    # Run demos
    demo_edit_tool()
    demo_multi_edit()
    demo_environment_config()

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print("""
To use this hook in your Claude Code sessions:

1. Ensure the hook is installed in the hooks directory
2. Set environment variables to configure:
   - CLAUDE_AUTO_FORMAT=true/false (global toggle)
   - CLAUDE_FORMAT_PYTHON=true/false (Python formatting)
   - CLAUDE_FORMAT_JS=true/false (JavaScript formatting)
   - etc.

3. Install formatters you want to use:
   - pip install black ruff autopep8
   - npm install -g prettier eslint
   - brew install jq (on macOS)

The hook will automatically format files after edits!
    """)


if __name__ == "__main__":
    main()
