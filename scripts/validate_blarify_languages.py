#!/usr/bin/env python3
"""Real multi-language validation for blarify indexing.

Tests blarify indexing on actual real-world repositories across 7+ languages.
This is NOT a stub - it actually downloads repos and runs indexing.
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class LanguageTest:
    """Configuration for testing a language."""

    language: str
    repo_url: str
    branch: str
    expected_min_files: int  # Minimum files to consider success
    expected_min_functions: int  # Minimum functions to consider success
    clone_depth: int = 1
    subdir: str | None = None  # Optional subdirectory to test (for large repos)


@dataclass
class ValidationResult:
    """Result of validating blarify indexing for a language."""

    language: str
    success: bool
    duration_seconds: float
    files_indexed: int
    functions_found: int
    classes_found: int
    errors: list[str]
    index_file_size: int
    clone_successful: bool
    indexing_successful: bool
    symbols_extracted: bool


# Real-world repositories for testing (carefully chosen for manageable size)
REAL_WORLD_REPOS = [
    LanguageTest(
        language="python",
        repo_url="https://github.com/pallets/flask.git",
        branch="main",
        expected_min_files=50,
        expected_min_functions=200,
        clone_depth=1,
        subdir="src/flask",  # Focus on core Flask code
    ),
    LanguageTest(
        language="javascript",
        repo_url="https://github.com/facebook/react.git",
        branch="main",
        expected_min_files=100,
        expected_min_functions=300,
        clone_depth=1,
        subdir="packages/react/src",  # Focus on React core
    ),
    LanguageTest(
        language="typescript",
        repo_url="https://github.com/microsoft/TypeScript.git",
        branch="main",
        expected_min_files=200,
        expected_min_functions=500,
        clone_depth=1,
        subdir="src/compiler",  # Focus on compiler code
    ),
    LanguageTest(
        language="go",
        repo_url="https://github.com/golang/go.git",
        branch="master",
        expected_min_files=100,
        expected_min_functions=300,
        clone_depth=1,
        subdir="src/fmt",  # Focus on fmt package (manageable size)
    ),
    LanguageTest(
        language="rust",
        repo_url="https://github.com/rust-lang/rust.git",
        branch="master",
        expected_min_files=100,
        expected_min_functions=200,
        clone_depth=1,
        subdir="compiler/rustc_ast",  # Focus on AST code
    ),
    LanguageTest(
        language="csharp",
        repo_url="https://github.com/dotnet/runtime.git",
        branch="main",
        expected_min_files=50,
        expected_min_functions=150,
        clone_depth=1,
        subdir="src/libraries/System.Console/src",  # Focus on System.Console
    ),
    LanguageTest(
        language="cpp",
        repo_url="https://github.com/llvm/llvm-project.git",
        branch="main",
        expected_min_files=50,
        expected_min_functions=100,
        clone_depth=1,
        subdir="llvm/include/llvm/ADT",  # Focus on ADT headers
    ),
]


def clone_repository(test: LanguageTest, temp_dir: Path) -> tuple[bool, str, Path]:
    """Clone repository for testing.

    Args:
        test: Language test configuration
        temp_dir: Temporary directory for cloning

    Returns:
        Tuple of (success, error_message, clone_path)
    """
    repo_name = test.repo_url.split("/")[-1].replace(".git", "")
    clone_path = temp_dir / repo_name

    try:
        print(f"  📥 Cloning {test.repo_url} (depth={test.clone_depth})...")
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                str(test.clone_depth),
                "--branch",
                test.branch,
                "--single-branch",
                test.repo_url,
                str(clone_path),
            ],
            check=True,
            capture_output=True,
            timeout=300,  # 5 minute timeout
        )

        # If subdir specified, use that as the target
        if test.subdir:
            target_path = clone_path / test.subdir
            if not target_path.exists():
                return False, f"Subdirectory {test.subdir} not found", clone_path
            # Return absolute path to avoid path resolution issues
            return True, "", target_path.resolve()

        # Return absolute path to avoid path resolution issues
        return True, "", clone_path.resolve()

    except subprocess.TimeoutExpired:
        return False, "Clone timeout (5 minutes)", clone_path
    except subprocess.CalledProcessError as e:
        return False, f"Git clone failed: {e.stderr.decode()}", clone_path
    except Exception as e:
        return False, f"Clone error: {e}", clone_path


def run_blarify_indexing(
    project_path: Path, language: str
) -> tuple[bool, dict[str, Any], list[str]]:
    """Run blarify indexing on project.

    Args:
        project_path: Path to project
        language: Language to index

    Returns:
        Tuple of (success, metrics_dict, errors_list)
    """
    errors = []

    try:
        # Import blarify orchestrator
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from amplihack.memory.kuzu.connector import KuzuConnector
        from amplihack.memory.kuzu.indexing.orchestrator import (
            IndexingConfig,
            Orchestrator,
        )

        # Create temporary database for testing (use absolute path)
        temp_db = (project_path / ".test_index.db").resolve()
        connector = KuzuConnector(str(temp_db))

        # CRITICAL: Connect to database before use
        connector.connect()

        # Run indexing
        print(f"  🔧 Running blarify indexing for {language}...")
        orchestrator = Orchestrator(connector=connector)

        config = IndexingConfig(
            timeout=600,  # 10 minute timeout
            max_retries=2,
        )

        result = orchestrator.run(
            codebase_path=project_path,
            languages=[language],
            background=False,
            config=config,
            dry_run=False,
        )

        # Extract metrics
        metrics = {
            "files_indexed": result.total_files,
            "functions_found": result.total_functions,
            "classes_found": result.total_classes,
            "success": result.success,
            "completed_languages": result.completed_languages,
            "failed_languages": result.failed_languages,
        }

        # Check if index file created
        index_size = 0
        if temp_db.exists():
            index_size = sum(f.stat().st_size for f in temp_db.rglob("*") if f.is_file())

        metrics["index_file_size"] = index_size

        # Collect errors
        if result.errors:
            errors.extend([str(err) for err in result.errors])

        return result.success, metrics, errors

    except ImportError as e:
        errors.append(f"Import error: {e}")
        return False, {}, errors
    except Exception as e:
        errors.append(f"Indexing error: {e}")
        return False, {}, errors


def validate_language(test: LanguageTest, temp_dir: Path) -> ValidationResult:
    """Validate blarify indexing for a specific language.

    Args:
        test: Language test configuration
        temp_dir: Temporary directory for testing

    Returns:
        ValidationResult with all metrics
    """
    start_time = time.time()
    print(f"\n🧪 Testing {test.language}...")

    # Step 1: Clone repository
    clone_success, clone_error, clone_path = clone_repository(test, temp_dir)
    if not clone_success:
        duration = time.time() - start_time
        return ValidationResult(
            language=test.language,
            success=False,
            duration_seconds=duration,
            files_indexed=0,
            functions_found=0,
            classes_found=0,
            errors=[f"Clone failed: {clone_error}"],
            index_file_size=0,
            clone_successful=False,
            indexing_successful=False,
            symbols_extracted=False,
        )

    print(f"  ✅ Clone successful: {clone_path}")

    # Step 2: Run blarify indexing
    indexing_success, metrics, errors = run_blarify_indexing(clone_path, test.language)

    duration = time.time() - start_time

    # Step 3: Validate results
    files_indexed = metrics.get("files_indexed", 0)
    functions_found = metrics.get("functions_found", 0)
    classes_found = metrics.get("classes_found", 0)
    index_size = metrics.get("index_file_size", 0)

    # Check if symbols were actually extracted
    symbols_extracted = (
        functions_found >= test.expected_min_functions and files_indexed >= test.expected_min_files
    )

    # Overall success: clone + indexing + symbols extracted
    overall_success = clone_success and indexing_success and symbols_extracted

    result = ValidationResult(
        language=test.language,
        success=overall_success,
        duration_seconds=duration,
        files_indexed=files_indexed,
        functions_found=functions_found,
        classes_found=classes_found,
        errors=errors,
        index_file_size=index_size,
        clone_successful=clone_success,
        indexing_successful=indexing_success,
        symbols_extracted=symbols_extracted,
    )

    # Print summary
    if overall_success:
        print(f"  ✅ {test.language} validation PASSED")
        print(
            f"     Files: {files_indexed}, Functions: {functions_found}, Classes: {classes_found}"
        )
        print(f"     Duration: {duration:.1f}s, Index size: {index_size / 1024:.1f} KB")
    else:
        print(f"  ❌ {test.language} validation FAILED")
        if errors:
            for error in errors:
                print(f"     Error: {error}")

    return result


def generate_markdown_report(results: list[ValidationResult], output_file: Path) -> None:
    """Generate markdown report from validation results.

    Args:
        results: List of validation results
        output_file: Path to output markdown file
    """
    total = len(results)
    passed = sum(1 for r in results if r.success)
    failed = total - passed

    report = f"""# Blarify Multi-Language Validation Report

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary

- **Total Languages Tested**: {total}
- **Passed**: {passed} ✅
- **Failed**: {failed} ❌
- **Success Rate**: {(passed / total * 100):.1f}%

## Results by Language

| Language   | Status | Files | Functions | Classes | Duration | Index Size | Notes |
|------------|--------|-------|-----------|---------|----------|------------|-------|
"""

    for result in results:
        status = "✅ PASS" if result.success else "❌ FAIL"
        index_kb = result.index_file_size / 1024 if result.index_file_size > 0 else 0

        notes = []
        if not result.clone_successful:
            notes.append("Clone failed")
        if not result.indexing_successful:
            notes.append("Indexing failed")
        if not result.symbols_extracted:
            notes.append("Insufficient symbols")

        notes_str = ", ".join(notes) if notes else "OK"

        report += f"| {result.language:10} | {status:6} | {result.files_indexed:5} | {result.functions_found:9} | {result.classes_found:7} | {result.duration_seconds:6.1f}s | {index_kb:8.1f} KB | {notes_str} |\n"

    report += "\n## Detailed Results\n\n"

    for result in results:
        report += f"### {result.language.upper()}\n\n"
        report += f"- **Status**: {'✅ PASSED' if result.success else '❌ FAILED'}\n"
        report += f"- **Duration**: {result.duration_seconds:.1f} seconds\n"
        report += f"- **Files Indexed**: {result.files_indexed}\n"
        report += f"- **Functions Found**: {result.functions_found}\n"
        report += f"- **Classes Found**: {result.classes_found}\n"
        report += f"- **Index Size**: {result.index_file_size / 1024:.1f} KB\n"

        if result.errors:
            report += "\n**Errors**:\n"
            for error in result.errors:
                report += f"- {error}\n"

        report += "\n"

    output_file.write_text(report)
    print(f"\n📄 Markdown report saved to: {output_file}")


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate blarify indexing across multiple languages"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./blarify_validation_results"),
        help="Output directory for results (default: ./blarify_validation_results)",
    )
    parser.add_argument(
        "--languages",
        type=str,
        default="all",
        help="Comma-separated list of languages to test or 'all' (default: all)",
    )
    parser.add_argument(
        "--keep-repos",
        action="store_true",
        help="Keep cloned repositories after testing (for debugging)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output",
    )

    args = parser.parse_args()

    # Create output directory (use absolute path to avoid path resolution issues)
    args.output_dir = args.output_dir.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Filter languages if specified
    if args.languages == "all":
        tests = REAL_WORLD_REPOS
    else:
        requested = [lang.strip() for lang in args.languages.split(",")]
        tests = [test for test in REAL_WORLD_REPOS if test.language in requested]

    if not tests:
        print(f"❌ No tests found for languages: {args.languages}")
        return 1

    print("🚀 Starting blarify multi-language validation")
    print(f"   Testing {len(tests)} languages: {', '.join(t.language for t in tests)}")

    # Create temp directory for cloning
    temp_dir = args.output_dir / "temp_repos"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Run validation for each language
    results = []
    for test in tests:
        try:
            result = validate_language(test, temp_dir)
            results.append(result)
        except Exception as e:
            print(f"  ❌ Unexpected error testing {test.language}: {e}")
            results.append(
                ValidationResult(
                    language=test.language,
                    success=False,
                    duration_seconds=0,
                    files_indexed=0,
                    functions_found=0,
                    classes_found=0,
                    errors=[f"Unexpected error: {e}"],
                    index_file_size=0,
                    clone_successful=False,
                    indexing_successful=False,
                    symbols_extracted=False,
                )
            )

    # Save results as JSON
    json_file = args.output_dir / "results.json"
    with open(json_file, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    print(f"\n💾 JSON results saved to: {json_file}")

    # Generate markdown report
    markdown_file = args.output_dir / "validation_report.md"
    generate_markdown_report(results, markdown_file)

    # Cleanup temp repos unless --keep-repos
    if not args.keep_repos:
        print("\n🧹 Cleaning up temporary repositories...")
        shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        print(f"\n📁 Keeping repos in: {temp_dir}")

    # Print summary
    passed = sum(1 for r in results if r.success)
    total = len(results)
    print(f"\n{'=' * 60}")
    print(f"VALIDATION COMPLETE: {passed}/{total} languages passed")
    print(f"{'=' * 60}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
