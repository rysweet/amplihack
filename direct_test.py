#!/usr/bin/env python3
"""Direct test of the error analysis system."""

import sys
from pathlib import Path

# Add the module path
sys.path.insert(0, str(Path(__file__).parent / ".claude" / "tools" / "amplihack" / "reflection"))

# Initialize analyzer variable
SimpleErrorAnalyzer = None  # type: ignore

# Test direct import
print("Testing direct import...")
try:
    from error_analysis.simple_analyzer import SimpleErrorAnalyzer  # type: ignore

    print("✅ Direct import successful")
except ImportError as e:
    print(f"❌ Direct import failed: {e}")

# Test package import (fallback)
if SimpleErrorAnalyzer is None:
    print("\nTesting package import...")
    try:
        from error_analysis import SimpleErrorAnalyzer  # type: ignore

        print("✅ Package import successful")
    except ImportError as e:
        print(f"❌ Package import failed: {e}")

# Test analysis functionality
print("\nTesting analysis functionality...")
if SimpleErrorAnalyzer is None:
    print("❌ Cannot test analysis - import failed")
else:
    try:
        analyzer = SimpleErrorAnalyzer()  # type: ignore

        test_content = "FileNotFoundError: Could not find the required file config.json"
        results = analyzer.analyze_errors(test_content)

        print(f"Analysis completed: {len(results)} patterns found")
        if results:
            print(f"Top pattern: {results[0].error_type}")
            print(f"Priority: {results[0].priority}")
            print(f"Suggestion: {results[0].suggestion}")

        # Test top suggestion method
        top_suggestion = analyzer.get_top_suggestion(test_content)
        if top_suggestion:
            print(f"Top suggestion type: {top_suggestion['type']}")
            print(f"Top suggestion: {top_suggestion['suggestion']}")

        print("✅ Analysis functionality working")

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback

        traceback.print_exc()

print("\n" + "=" * 50)
print("Testing complete!")
