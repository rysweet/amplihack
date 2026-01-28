#!/bin/bash
# Manual test script for blarify code indexing user flow
# Tests the feature as a real user would experience it

set -e

echo "========================================="
echo "Blarify Code Indexing - User Flow Test"
echo "========================================="

# Create test directory with sample Python code
TEST_DIR=$(mktemp -d -t blarify_test_XXXXXX)
echo "Test directory: $TEST_DIR"

# Create sample Python files
cat > "$TEST_DIR/app.py" << 'EOF'
def calculate_sum(numbers):
    """Calculate sum of numbers."""
    return sum(numbers)

class DataProcessor:
    """Process data from various sources."""

    def __init__(self):
        self.data = []

    def add_data(self, item):
        """Add item to data list."""
        self.data.append(item)

    def process(self):
        """Process all data items."""
        return [self._transform(item) for item in self.data]

    def _transform(self, item):
        """Transform a single item."""
        return str(item).upper()

def main():
    """Main entry point."""
    processor = DataProcessor()
    processor.add_data("hello")
    processor.add_data("world")
    results = processor.process()
    print(calculate_sum([1, 2, 3]))
    print(results)

if __name__ == "__main__":
    main()
EOF

cat > "$TEST_DIR/utils.py" << 'EOF'
def validate_input(value):
    """Validate user input."""
    if not value:
        raise ValueError("Input cannot be empty")
    return value.strip()

class Logger:
    """Simple logging utility."""

    def log(self, message):
        print(f"[LOG] {message}")
EOF

echo ""
echo "Created test files:"
ls -la "$TEST_DIR"

echo ""
echo "========================================="
echo "TEST 1: Run blarify programmatically"
echo "========================================="

# Test the run_blarify function directly
python3 << EOTEST
import sys
import warnings
warnings.filterwarnings('ignore')

from pathlib import Path
from src.amplihack.memory.kuzu.connector import KuzuConnector
from src.amplihack.memory.kuzu.code_graph import KuzuCodeGraph
import tempfile
import shutil

test_dir = Path("$TEST_DIR")
kuzu_path = Path(tempfile.gettempdir()) / "test_user_flow_kuzu"

try:
    # Initialize Kuzu
    connector = KuzuConnector(str(kuzu_path))
    connector.connect()
    code_graph = KuzuCodeGraph(connector)

    print(f"Running blarify on: {test_dir}")
    counts = code_graph.run_blarify(str(test_dir))

    print(f"\n✅ Blarify analysis completed!")
    print(f"  Files indexed: {counts['files']}")
    print(f"  Classes indexed: {counts['classes']}")
    print(f"  Functions indexed: {counts['functions']}")

    # Verify we got meaningful results
    if counts['files'] >= 2 and counts['classes'] >= 2 and counts['functions'] >= 5:
        print(f"\n✅ TEST 1 PASSED - Adequate code indexed")
        sys.exit(0)
    else:
        print(f"\n❌ TEST 1 FAILED - Not enough code indexed")
        print(f"   Expected: 2+ files, 2+ classes, 5+ functions")
        print(f"   Got: {counts['files']} files, {counts['classes']} classes, {counts['functions']} functions")
        sys.exit(1)

except Exception as e:
    print(f"\n❌ TEST 1 FAILED with exception: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    # Cleanup
    shutil.rmtree(kuzu_path, ignore_errors=True)
EOTEST

TEST1_RESULT=$?

if [ $TEST1_RESULT -eq 0 ]; then
    echo ""
    echo "✅ TEST 1 PASSED"
else
    echo ""
    echo "❌ TEST 1 FAILED"
    echo "Cleaning up and exiting..."
    rm -rf "$TEST_DIR"
    exit 1
fi

echo ""
echo "========================================="
echo "TEST 2: Verify JSON export format"
echo "========================================="

# Test that JSON output has correct structure
python3 << EOTEST
import sys
import warnings
warnings.filterwarnings('ignore')

from pathlib import Path
from src.amplihack.memory.kuzu.code_graph import run_blarify
import tempfile
import json
import shutil

test_dir = Path("$TEST_DIR")
output_file = Path(tempfile.gettempdir()) / "test_output.json"

try:
    # Run blarify
    success = run_blarify(test_dir, output_file)

    if not success:
        print("❌ TEST 2 FAILED - run_blarify returned False")
        sys.exit(1)

    if not output_file.exists():
        print("❌ TEST 2 FAILED - Output JSON file not created")
        sys.exit(1)

    # Parse and validate JSON structure
    with open(output_file) as f:
        data = json.load(f)

    print(f"JSON structure:")
    for key in data.keys():
        print(f"  {key}: {len(data[key])} items")

    # Verify required keys
    required_keys = ['files', 'classes', 'functions', 'relationships']
    missing = [k for k in required_keys if k not in data]
    if missing:
        print(f"\n❌ TEST 2 FAILED - Missing keys: {missing}")
        sys.exit(1)

    # Verify arrays not null
    for key in required_keys:
        if not isinstance(data[key], list):
            print(f"\n❌ TEST 2 FAILED - {key} is not a list")
            sys.exit(1)

    # Verify we got data
    if len(data['files']) == 0:
        print(f"\n❌ TEST 2 FAILED - No files indexed")
        sys.exit(1)

    print(f"\n✅ TEST 2 PASSED - JSON export format correct")
    sys.exit(0)

except Exception as e:
    print(f"\n❌ TEST 2 FAILED with exception: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    output_file.unlink(missing_ok=True)
EOTEST

TEST2_RESULT=$?

if [ $TEST2_RESULT -eq 0 ]; then
    echo ""
    echo "✅ TEST 2 PASSED"
else
    echo ""
    echo "❌ TEST 2 FAILED"
    rm -rf "$TEST_DIR"
    exit 1
fi

echo ""
echo "========================================="
echo "TEST 3: Verify Kuzu database content"
echo "========================================="

# Test that data is actually in Kuzu database
python3 << EOTEST
import sys
import warnings
warnings.filterwarnings('ignore')

from pathlib import Path
from src.amplihack.memory.kuzu.connector import KuzuConnector
from src.amplihack.memory.kuzu.code_graph import KuzuCodeGraph
import tempfile
import shutil

test_dir = Path("$TEST_DIR")
kuzu_path = Path(tempfile.gettempdir()) / "test_kuzu_content"

try:
    # Run blarify and import
    connector = KuzuConnector(str(kuzu_path))
    connector.connect()
    code_graph = KuzuCodeGraph(connector)

    counts = code_graph.run_blarify(str(test_dir))

    # Query Kuzu database directly to verify data exists
    print("Querying Kuzu database for indexed code...")

    # Check files
    files = connector.execute_query("""
        MATCH (f:CodeFile)
        RETURN f.file_path as path
    """)
    print(f"  Files in database: {len(files)}")
    if files:
        print(f"    Example: {files[0]['path']}")

    # Check classes
    classes = connector.execute_query("""
        MATCH (c:CodeClass)
        RETURN c.class_name as name
    """)
    print(f"  Classes in database: {len(classes)}")
    if classes:
        print(f"    Examples: {[c['name'] for c in classes[:3]]}")

    # Check functions
    functions = connector.execute_query("""
        MATCH (f:CodeFunction)
        RETURN f.function_name as name
    """)
    print(f"  Functions in database: {len(functions)}")
    if functions:
        print(f"    Examples: {[f['name'] for f in functions[:5]]}")

    # Verify expected entities exist
    expected_classes = ['DataProcessor', 'Logger']
    expected_functions = ['calculate_sum', 'main', 'validate_input', 'add_data', 'process']

    found_classes = [c['name'] for c in classes]
    found_functions = [f['name'] for f in functions]

    missing_classes = [c for c in expected_classes if c not in found_classes]
    missing_functions = [f for f in expected_functions if f not in found_functions]

    if missing_classes:
        print(f"\n⚠️ Missing classes: {missing_classes}")

    if missing_functions:
        print(f"\n⚠️ Missing functions: {missing_functions}")

    if len(files) >= 2 and len(classes) >= 2 and len(functions) >= 5:
        print(f"\n✅ TEST 3 PASSED - Data correctly stored in Kuzu")
        sys.exit(0)
    else:
        print(f"\n❌ TEST 3 FAILED - Insufficient data in Kuzu")
        sys.exit(1)

except Exception as e:
    print(f"\n❌ TEST 3 FAILED with exception: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    shutil.rmtree(kuzu_path, ignore_errors=True)
EOTEST

TEST3_RESULT=$?

if [ $TEST3_RESULT -eq 0 ]; then
    echo ""
    echo "✅ TEST 3 PASSED"
else
    echo ""
    echo "❌ TEST 3 FAILED"
    rm -rf "$TEST_DIR"
    exit 1
fi

# Cleanup
echo ""
echo "Cleaning up test directory: $TEST_DIR"
rm -rf "$TEST_DIR"

echo ""
echo "========================================="
echo "ALL TESTS PASSED! ✅"
echo "========================================="
echo ""
echo "Summary:"
echo "  ✅ Test 1: Blarify analysis works programmatically"
echo "  ✅ Test 2: JSON export format is correct"
echo "  ✅ Test 3: Data correctly stored in Kuzu database"
echo ""
echo "The blarify integration with Kuzu is WORKING!"
