#!/usr/bin/env python3
"""
Basic usage examples for the Analyze Codebase tool.

This script demonstrates common usage patterns and expected outputs.
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from ..tool import CodebaseAnalyzer


def example_basic_analysis():
    """Example: Basic directory analysis."""
    print("=" * 60)
    print("EXAMPLE 1: Basic Directory Analysis")
    print("=" * 60)

    # Create analyzer
    analyzer = CodebaseAnalyzer()

    # Analyze current directory (or specify a path)
    target_path = "."  # Change to any directory you want to analyze

    try:
        result = analyzer.analyze(target_path)
        print(result)
    except Exception as e:
        print(f"Error: {e}")


def example_json_output():
    """Example: JSON output for programmatic use."""
    print("=" * 60)
    print("EXAMPLE 2: JSON Output")
    print("=" * 60)

    analyzer = CodebaseAnalyzer()
    target_path = "."

    try:
        result = analyzer.analyze(target_path, {"format": "json"})

        # Pretty print some key information
        print(f"Analysis timestamp: {result['timestamp']}")
        print(f"Execution time: {result['execution_time']:.2f} seconds")
        print(f"Agents run: {result['summary']['agents_run']}")
        print(f"Total findings: {result['summary']['total_findings']}")

        if result["summary"].get("metrics"):
            print("\nKey Metrics:")
            for metric, value in result["summary"]["metrics"].items():
                if isinstance(value, float):
                    print(f"  {metric}: {value:.2f}")
                else:
                    print(f"  {metric}: {value}")

        print("\nTop 3 Recommendations:")
        for i, rec in enumerate(result["recommendations"][:3], 1):
            print(f"  {i}. {rec}")

    except Exception as e:
        print(f"Error: {e}")


def example_custom_configuration():
    """Example: Custom analyzer configuration."""
    print("=" * 60)
    print("EXAMPLE 3: Custom Configuration")
    print("=" * 60)

    # Custom configuration
    custom_config = {
        "max_file_size": 500000,  # 500KB instead of default 1MB
        "skip_patterns": [".git", "__pycache__", "node_modules", ".venv", ".custom"],
        "analysis_depth": "deep",
    }

    analyzer = CodebaseAnalyzer(custom_config)
    target_path = "."

    try:
        result = analyzer.analyze(target_path, {"verbose": True})
        print(result)
        print(f"\nUsed custom config with max file size: {custom_config['max_file_size']} bytes")
    except Exception as e:
        print(f"Error: {e}")


def example_single_file_analysis():
    """Example: Analyzing a single file."""
    print("=" * 60)
    print("EXAMPLE 4: Single File Analysis")
    print("=" * 60)

    analyzer = CodebaseAnalyzer()

    # Create a sample file for analysis
    sample_file = Path("sample_analysis.py")
    sample_content = '''
def calculate_fibonacci(n):
    """Calculate nth Fibonacci number."""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

class DataProcessor:
    def __init__(self):
        self.data = []

    def add_data(self, item):
        # TODO: Add validation
        self.data.append(item)

    def process_all(self):
        return [item * 2 for item in self.data]

# Example usage
if __name__ == "__main__":
    processor = DataProcessor()
    processor.add_data(5)
    result = processor.process_all()
    print(f"Result: {result}")
    '''

    try:
        # Write sample file
        sample_file.write_text(sample_content)

        # Analyze the single file
        result = analyzer.analyze(str(sample_file))
        print(result)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up
        if sample_file.exists():
            sample_file.unlink()


def example_error_handling():
    """Example: Error handling and edge cases."""
    print("=" * 60)
    print("EXAMPLE 5: Error Handling")
    print("=" * 60)

    analyzer = CodebaseAnalyzer()

    # Test various error conditions
    error_cases = [
        "/nonexistent/directory",
        "../../etc/passwd",  # Directory traversal attempt
        "",  # Empty path
    ]

    for case in error_cases:
        print(f"\nTesting: {case}")
        try:
            analyzer.analyze(case)
            print("Unexpected success!")
        except ValueError as e:
            print(f"Caught expected error: {e}")
        except Exception as e:
            print(f"Unexpected error type: {type(e).__name__}: {e}")


def example_output_comparison():
    """Example: Comparing text vs JSON output."""
    print("=" * 60)
    print("EXAMPLE 6: Output Format Comparison")
    print("=" * 60)

    analyzer = CodebaseAnalyzer()
    target_path = "."

    try:
        # Get text output
        print("TEXT OUTPUT:")
        print("-" * 40)
        text_result = analyzer.analyze(target_path, {"format": "text"})
        print(text_result)

        print("\n" + "=" * 40)

        # Get JSON output (just show structure)
        print("JSON OUTPUT STRUCTURE:")
        print("-" * 40)
        json_result = analyzer.analyze(target_path, {"format": "json"})
        print("JSON Keys:", list(json_result.keys()))
        print("Summary Keys:", list(json_result["summary"].keys()))
        print("Number of findings:", len(json_result["findings"]))
        print("Number of recommendations:", len(json_result["recommendations"]))
        print("Number of agent details:", len(json_result["agent_details"]))

    except Exception as e:
        print(f"Error: {e}")


def main():
    """Run all examples."""
    print("🔍 Analyze Codebase Tool - Usage Examples")
    print("=" * 60)
    print()

    examples = [
        example_basic_analysis,
        example_json_output,
        example_custom_configuration,
        example_single_file_analysis,
        example_error_handling,
        example_output_comparison,
    ]

    for i, example_func in enumerate(examples, 1):
        try:
            example_func()
        except Exception as e:
            print(f"Example {i} failed: {e}")

        if i < len(examples):
            print("\n" + "=" * 60)
            print()

    print("\n🎉 Examples completed!")
    print("\nTo run the tool from command line:")
    print("  python tool.py ./path/to/analyze")
    print("  python tool.py ./path/to/analyze --format=json")
    print("  python tool.py ./path/to/analyze --output=analysis.json")


if __name__ == "__main__":
    main()
