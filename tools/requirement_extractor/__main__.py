"""
Command-line interface for requirements extraction tool
"""
import argparse
import sys
from pathlib import Path
from .models import ExtractionConfig, OutputFormat
from .orchestrator import run_extraction


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Extract functional requirements from codebases using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m tools.requirement_extractor /path/to/project --output requirements.md
  python -m tools.requirement_extractor . --format json --output reqs.json
  python -m tools.requirement_extractor ~/myproject --compare existing_reqs.md
  python -m tools.requirement_extractor . --resume  # Resume previous extraction
        """
    )

    parser.add_argument(
        'project_path',
        help='Path to the project directory to analyze'
    )

    parser.add_argument(
        '--output', '-o',
        default='requirements.md',
        help='Output file path (default: requirements.md)'
    )

    parser.add_argument(
        '--format', '-f',
        choices=['markdown', 'json', 'yaml'],
        default='markdown',
        help='Output format (default: markdown)'
    )

    parser.add_argument(
        '--compare', '-c',
        help='Path to existing requirements document for gap analysis'
    )

    parser.add_argument(
        '--no-evidence',
        action='store_true',
        help='Exclude code evidence from output'
    )

    parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.5,
        help='Minimum confidence threshold for requirements (0.0-1.0, default: 0.5)'
    )

    parser.add_argument(
        '--max-files',
        type=int,
        default=50,
        help='Maximum files per module (default: 50)'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=120,
        help='Timeout in seconds for AI extraction (default: 120)'
    )

    parser.add_argument(
        '--no-retry',
        action='store_true',
        help='Do not retry failed modules'
    )

    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from previous extraction if available'
    )

    parser.add_argument(
        '--clear-state',
        action='store_true',
        help='Clear any existing extraction state and start fresh'
    )

    args = parser.parse_args()

    # Validate project path
    project_path = Path(args.project_path).resolve()
    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}", file=sys.stderr)
        return 1

    if not project_path.is_dir():
        print(f"Error: Project path is not a directory: {project_path}", file=sys.stderr)
        return 1

    # Parse output format
    format_map = {
        'markdown': OutputFormat.MARKDOWN,
        'json': OutputFormat.JSON,
        'yaml': OutputFormat.YAML
    }
    output_format = format_map[args.format]

    # Create configuration
    config = ExtractionConfig(
        project_path=str(project_path),
        output_path=args.output,
        output_format=output_format,
        include_evidence=not args.no_evidence,
        min_confidence=args.min_confidence,
        max_files_per_module=args.max_files,
        timeout_seconds=args.timeout,
        retry_failed=not args.no_retry,
        existing_requirements_path=args.compare
    )

    # Handle state management
    if args.clear_state:
        from .state_manager import StateManager
        state_manager = StateManager(config.state_file)
        state_manager.clear_state()
        print("Cleared existing extraction state")
        if not args.resume:  # If only clearing state, exit
            return 0

    print("=" * 60)
    print("Requirements Extraction Tool")
    print("=" * 60)
    print(f"Project: {project_path}")
    print(f"Output: {args.output} ({args.format})")
    if args.compare:
        print(f"Comparing with: {args.compare}")
    print(f"Settings:")
    print(f"  - Min confidence: {args.min_confidence}")
    print(f"  - Max files/module: {args.max_files}")
    print(f"  - Timeout: {args.timeout}s")
    print(f"  - Include evidence: {not args.no_evidence}")
    print("=" * 60)
    print()

    # Run extraction
    try:
        success = run_extraction(config)
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\nExtraction interrupted by user")
        print("Run with --resume flag to continue from where you left off")
        return 130
    except Exception as e:
        print(f"Error during extraction: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())