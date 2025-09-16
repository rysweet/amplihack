"""
Orchestrator module that coordinates the entire requirements extraction pipeline
"""
import asyncio
import time
from pathlib import Path
from typing import List, Optional
from .models import (
    ExtractionConfig, CodeModule, ModuleRequirements,
    OutputFormat, GapAnalysis
)
from .discovery import CodeDiscovery
from .extractor import RequirementsExtractor
from .state_manager import StateManager
from .gap_analyzer import GapAnalyzer
from .formatter import RequirementsFormatter


class RequirementsOrchestrator:
    """Orchestrates the entire requirements extraction process"""

    def __init__(self, config: ExtractionConfig):
        self.config = config
        self.discovery = CodeDiscovery(
            config.project_path,
            config.max_files_per_module
        )
        self.extractor = RequirementsExtractor(config.timeout_seconds)
        self.state_manager = StateManager(config.state_file)
        self.gap_analyzer = GapAnalyzer()
        self.formatter = RequirementsFormatter(
            config.include_evidence,
            config.min_confidence
        )
        self.module_requirements: List[ModuleRequirements] = []

    async def extract_requirements(self) -> bool:
        """Main entry point for requirements extraction"""
        print(f"Starting requirements extraction for: {self.config.project_path}")

        # Step 1: Discover and group files
        print("Discovering code files...")
        files = self.discovery.discover_files()
        if not files:
            print("No code files found!")
            return False

        modules = self.discovery.group_into_modules(files)
        print(f"Found {len(files)} files grouped into {len(modules)} modules")

        # Step 2: Check for existing state (resume capability)
        state = self.state_manager.load_state(self.config.project_path)
        if state:
            print(f"Resuming from previous extraction ({state.progress_percentage:.1f}% complete)")
            remaining_modules = self.state_manager.get_remaining_modules(
                [m.name for m in modules]
            )
            # Filter modules to only process remaining ones
            modules = [m for m in modules if m.name in remaining_modules]
        else:
            # Create new state
            state = self.state_manager.create_state(
                self.config.project_path,
                len(modules)
            )
            state.requirements_file = self.config.output_path

        # Step 3: Extract requirements from each module
        for i, module in enumerate(modules):
            print(f"Processing module {i+1}/{len(modules)}: {module.name}")
            self.state_manager.set_current_module(module.name)

            try:
                # Extract requirements
                module_reqs = await self.extractor.extract_requirements(module)
                self.module_requirements.append(module_reqs)

                # Update state
                success = module_reqs.extraction_status == "completed"
                self.state_manager.update_progress(module.name, success)

                if success:
                    print(f"  ✓ Extracted {len(module_reqs.requirements)} requirements")
                else:
                    print(f"  ✗ Failed: {module_reqs.error_message}")

                # Save intermediate results
                if (i + 1) % 5 == 0:  # Save every 5 modules
                    self._save_intermediate_results()

            except Exception as e:
                print(f"  ✗ Unexpected error: {e}")
                self.state_manager.update_progress(module.name, False)

        # Step 4: Perform gap analysis if requested
        gap_analysis = None
        if self.config.existing_requirements_path:
            print("Performing gap analysis...")
            if self.gap_analyzer.load_existing_requirements(self.config.existing_requirements_path):
                all_requirements = []
                for module_reqs in self.module_requirements:
                    all_requirements.extend(module_reqs.requirements)
                gap_analysis = self.gap_analyzer.analyze_gaps(all_requirements)
                print(f"  Found {len(gap_analysis.missing_in_docs)} new requirements")

        # Step 5: Generate final output
        print("Generating output...")
        output = self.formatter.format_requirements(
            self.module_requirements,
            self.config.output_format,
            gap_analysis
        )

        # Save output with retry logic
        self._save_output(output)

        # Clear state on successful completion
        if state.is_complete:
            self.state_manager.clear_state()
            print("Extraction complete!")
        else:
            print(f"Extraction partially complete ({state.progress_percentage:.1f}%)")
            print(f"Run again to continue from where it left off")

        return True

    def _save_intermediate_results(self):
        """Save intermediate results during processing"""
        try:
            output = self.formatter.format_requirements(
                self.module_requirements,
                self.config.output_format
            )
            temp_path = f"{self.config.output_path}.tmp"
            self._save_output(output, temp_path)
        except Exception as e:
            print(f"Failed to save intermediate results: {e}")

    def _save_output(self, content: str, path: Optional[str] = None):
        """Save output with retry logic for cloud-synced files"""
        output_path = Path(path or self.config.output_path)
        retry_count = 3
        retry_delay = 0.5

        for attempt in range(retry_count):
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    f.flush()
                print(f"Requirements saved to: {output_path}")
                return

            except (OSError, IOError) as e:
                if attempt < retry_count - 1:
                    if attempt == 0:
                        print(f"File I/O error saving output - retrying...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"Failed to save output after {retry_count} attempts: {e}")
                    raise


def run_extraction(config: ExtractionConfig) -> bool:
    """Run the extraction process"""
    orchestrator = RequirementsOrchestrator(config)
    return asyncio.run(orchestrator.extract_requirements())