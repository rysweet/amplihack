#!/bin/bash
# Comprehensive testing suite for blarify Kuzu integration
# Tests multiple scenarios to build confidence

set -e

echo "=============================================="
echo "COMPREHENSIVE BLARIFY KUZU INTEGRATION TESTS"
echo "=============================================="

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Helper function
run_test() {
    local test_name="$1"
    local test_func="$2"

    echo ""
    echo "=========================================="
    echo "TEST $((TOTAL_TESTS + 1)): $test_name"
    echo "=========================================="

    if $test_func; then
        echo "✅ PASSED: $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo "❌ FAILED: $test_name"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
}

# Test 1: Small codebase (already tested)
test_small_codebase() {
    python3 << 'EOF'
import sys, warnings, tempfile, shutil
from pathlib import Path
warnings.filterwarnings('ignore')

from src.amplihack.memory.kuzu.connector import KuzuConnector
from src.amplihack.memory.kuzu.code_graph import KuzuCodeGraph

test_dir = Path(tempfile.mkdtemp())
(test_dir / 'small.py').write_text('def test(): pass\nclass Test: pass')

kuzu_path = Path(tempfile.gettempdir()) / "test_small"
connector = KuzuConnector(str(kuzu_path))
connector.connect()
code_graph = KuzuCodeGraph(connector)

counts = code_graph.run_blarify(str(test_dir))

success = counts['files'] >= 1 and counts['functions'] >= 1
shutil.rmtree(test_dir, ignore_errors=True)
shutil.rmtree(kuzu_path, ignore_errors=True)

sys.exit(0 if success else 1)
EOF
}

# Test 2: Larger real codebase
test_large_codebase() {
    python3 << 'EOF'
import sys, warnings, tempfile, shutil, time
from pathlib import Path
warnings.filterwarnings('ignore')

from src.amplihack.memory.kuzu.connector import KuzuConnector
from src.amplihack.memory.kuzu.code_graph import KuzuCodeGraph

# Test on full amplihack src directory
test_dir = Path("src/amplihack")

kuzu_path = Path(tempfile.gettempdir()) / "test_large"
connector = KuzuConnector(str(kuzu_path))
connector.connect()
code_graph = KuzuCodeGraph(connector)

print(f"Testing on large codebase: {test_dir}")
start = time.time()
counts = code_graph.run_blarify(str(test_dir))
elapsed = time.time() - start

print(f"  Files: {counts['files']}")
print(f"  Classes: {counts['classes']}")
print(f"  Functions: {counts['functions']}")
print(f"  Time: {elapsed:.1f}s")

# Should index significant amount of code
success = counts['files'] >= 50 and counts['functions'] >= 200
shutil.rmtree(kuzu_path, ignore_errors=True)

sys.exit(0 if success else 1)
EOF
}

# Test 3: Empty directory
test_empty_directory() {
    python3 << 'EOF'
import sys, warnings, tempfile, shutil
from pathlib import Path
warnings.filterwarnings('ignore')

from src.amplihack.memory.kuzu.connector import KuzuConnector
from src.amplihack.memory.kuzu.code_graph import KuzuCodeGraph

test_dir = Path(tempfile.mkdtemp())
# Empty directory - no Python files

kuzu_path = Path(tempfile.gettempdir()) / "test_empty"
connector = KuzuConnector(str(kuzu_path))
connector.connect()
code_graph = KuzuCodeGraph(connector)

counts = code_graph.run_blarify(str(test_dir))

# Should handle empty gracefully
success = counts['files'] == 0 and counts['classes'] == 0
shutil.rmtree(test_dir, ignore_errors=True)
shutil.rmtree(kuzu_path, ignore_errors=True)

sys.exit(0 if success else 1)
EOF
}

# Test 4: Invalid Python syntax
test_invalid_syntax() {
    python3 << 'EOF'
import sys, warnings, tempfile, shutil
from pathlib import Path
warnings.filterwarnings('ignore')

from src.amplihack.memory.kuzu.connector import KuzuConnector
from src.amplihack.memory.kuzu.code_graph import KuzuCodeGraph

test_dir = Path(tempfile.mkdtemp())
(test_dir / 'broken.py').write_text('def broken(\n  # Missing closing paren')

kuzu_path = Path(tempfile.gettempdir()) / "test_invalid"
connector = KuzuConnector(str(kuzu_path))
connector.connect()
code_graph = KuzuCodeGraph(connector)

# Should not crash on syntax errors
try:
    counts = code_graph.run_blarify(str(test_dir))
    success = True  # Completed without crashing
except:
    success = False

shutil.rmtree(test_dir, ignore_errors=True)
shutil.rmtree(kuzu_path, ignore_errors=True)

sys.exit(0 if success else 1)
EOF
}

# Test 5: Temp file cleanup
test_temp_cleanup() {
    python3 << 'EOF'
import sys, warnings, tempfile, shutil, glob
from pathlib import Path
warnings.filterwarnings('ignore')

from src.amplihack.memory.kuzu.code_graph import run_blarify

test_dir = Path(tempfile.mkdtemp())
(test_dir / 'test.py').write_text('def foo(): pass')

output_file = test_dir / 'output.json'

# Count temp dirs before
before = len(glob.glob('/tmp/blarify_kuzu_*'))

# Run blarify
run_blarify(test_dir, output_file)

# Count temp dirs after
after = len(glob.glob('/tmp/blarify_kuzu_*'))

# Should clean up temp directories
success = (after <= before)  # No new temp dirs left behind

print(f"  Temp dirs before: {before}")
print(f"  Temp dirs after: {after}")
print(f"  Cleanup: {'✅ OK' if success else '❌ LEAKED'}")

shutil.rmtree(test_dir, ignore_errors=True)

sys.exit(0 if success else 1)
EOF
}

# Test 6: Multiple runs (stability)
test_multiple_runs() {
    python3 << 'EOF'
import sys, warnings, tempfile, shutil
from pathlib import Path
warnings.filterwarnings('ignore')

from src.amplihack.memory.kuzu.connector import KuzuConnector
from src.amplihack.memory.kuzu.code_graph import KuzuCodeGraph

test_dir = Path(tempfile.mkdtemp())
(test_dir / 'code.py').write_text('def test(): pass\nclass TestClass: pass')

kuzu_path = Path(tempfile.gettempdir()) / "test_multi"
connector = KuzuConnector(str(kuzu_path))
connector.connect()
code_graph = KuzuCodeGraph(connector)

# Run twice - should be idempotent
counts1 = code_graph.run_blarify(str(test_dir))
counts2 = code_graph.run_blarify(str(test_dir))

# Counts should be stable
success = (counts1 == counts2)

print(f"  Run 1: {counts1}")
print(f"  Run 2: {counts2}")

shutil.rmtree(test_dir, ignore_errors=True)
shutil.rmtree(kuzu_path, ignore_errors=True)

sys.exit(0 if success else 1)
EOF
}

# Run all tests
run_test "Small Codebase (Smoke Test)" test_small_codebase
run_test "Large Codebase (Full amplihack)" test_large_codebase
run_test "Empty Directory (Edge Case)" test_empty_directory
run_test "Invalid Python Syntax (Error Handling)" test_invalid_syntax
run_test "Temp File Cleanup (Resource Management)" test_temp_cleanup
run_test "Multiple Runs (Idempotence)" test_multiple_runs

# Summary
echo ""
echo "=============================================="
echo "TEST SUMMARY"
echo "=============================================="
echo "Total:  $TOTAL_TESTS"
echo "Passed: $PASSED_TESTS ✅"
echo "Failed: $FAILED_TESTS ❌"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED!"
    exit 0
else
    echo "⚠️ SOME TESTS FAILED"
    exit 1
fi
