"""Advanced usage scenarios for Session Management Toolkit.

Real-world examples that demonstrate complex workflows and patterns.
"""

import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List

from ..claude_session import SessionConfig
from ..session_toolkit import SessionToolkit


class CodeAnalysisWorkflow:
    """Example: Code analysis workflow with session management."""

    def __init__(self, runtime_dir: Path):
        self.toolkit = SessionToolkit(runtime_dir=runtime_dir, auto_save=True, log_level="INFO")

    def analyze_project(self, project_path: str) -> Dict[str, Any]:
        """Analyze a code project with full session tracking."""

        # Custom configuration for analysis tasks
        config = SessionConfig(
            timeout=300.0,  # 5 minutes for complex analysis
            heartbeat_interval=10.0,
            max_retries=3,
        )

        session_id = self.toolkit.create_session(
            "code_analysis",
            config=config,
            metadata={
                "project_path": project_path,
                "analysis_type": "full",
                "timestamp": time.time(),
            },
        )

        results = {}

        with self.toolkit.session(session_id) as session:
            logger = self.toolkit.get_logger("code_analyzer")

            logger.info(f"Starting analysis of project: {project_path}")

            # Phase 1: Discovery
            with logger.operation("discovery"):
                result = session.execute_command("scan_project", path=project_path)
                file_count = result.get("metadata", {}).get("file_count", 0)
                logger.info(f"Discovered {file_count} files")

                # Save checkpoint after discovery
                session.save_checkpoint()

            # Phase 2: Static Analysis
            with logger.operation("static_analysis"):
                # Analyze different file types
                for file_type in ["python", "javascript", "typescript"]:
                    sub_logger = logger.create_child_logger(f"{file_type}_analyzer")

                    with sub_logger.operation(f"{file_type}_analysis"):
                        result = session.execute_command(
                            "analyze_files", file_type=file_type, deep_analysis=True
                        )
                        results[file_type] = result.get("statistics", {})
                        sub_logger.info(f"{file_type} analysis completed")

            # Phase 3: Security Scan
            with logger.operation("security_scan"):
                security_logger = logger.create_child_logger("security")

                result = session.execute_command("security_scan", thorough=True)
                results["security"] = result.get("findings", [])

                if results["security"]:
                    security_logger.warning(f"Found {len(results['security'])} security issues")
                else:
                    security_logger.success("No security issues found")

            # Phase 4: Report Generation
            with logger.operation("report_generation"):
                session.execute_command("generate_report", format="json")
                session.execute_command("generate_report", format="html")

                logger.success("Analysis workflow completed successfully")

        # Export session for later reference
        export_path = self.toolkit.runtime_dir / f"analysis_{session_id}.json"
        self.toolkit.export_session_data(session_id, export_path)

        return {"session_id": session_id, "results": results, "export_path": str(export_path)}


class BatchProcessingManager:
    """Example: Batch processing with session management and error recovery."""

    def __init__(self, runtime_dir: Path):
        self.toolkit = SessionToolkit(runtime_dir=runtime_dir, auto_save=True)

    def process_data_batches(
        self, batch_configs: List[Dict[str, Any]], parallel: bool = False
    ) -> Dict[str, Any]:
        """Process multiple data batches with comprehensive session tracking."""

        session_id = self.toolkit.create_session(
            "batch_processing",
            metadata={
                "batch_count": len(batch_configs),
                "parallel_mode": parallel,
                "start_time": time.time(),
            },
        )

        with self.toolkit.session(session_id) as session:
            logger = self.toolkit.get_logger("batch_processor")

            logger.info(f"Starting batch processing: {len(batch_configs)} batches")

            batch_results = []
            failed_batches = []

            # Initialize processing environment
            with logger.operation("initialization"):
                session.execute_command("setup_batch_environment")
                session.execute_command("validate_configurations")

                # Save checkpoint before processing
                session.save_checkpoint()

            # Process each batch
            for i, batch_config in enumerate(batch_configs):
                batch_logger = logger.create_child_logger(f"batch_{i}")

                try:
                    with batch_logger.operation(f"process_batch_{i}"):
                        batch_logger.info(f"Processing batch {i + 1}/{len(batch_configs)}")

                        # Simulate batch processing
                        result = session.execute_command(
                            "process_batch", batch_id=i, config=batch_config, parallel=parallel
                        )

                        batch_results.append(
                            {
                                "batch_id": i,
                                "status": "success",
                                "result": result,
                                "processing_time": result.get("metadata", {}).get("duration", 0),
                            }
                        )

                        batch_logger.success(f"Batch {i} completed successfully")

                except Exception as e:
                    batch_logger.error(f"Batch {i} failed: {e}")
                    failed_batches.append({"batch_id": i, "error": str(e), "config": batch_config})

                    # For critical failures, restore checkpoint and continue
                    if "critical" in str(e).lower():
                        batch_logger.warning("Critical error - restoring checkpoint")
                        session.restore_checkpoint()

            # Retry failed batches
            if failed_batches:
                logger.warning(f"Retrying {len(failed_batches)} failed batches")

                with logger.operation("retry_failed_batches"):
                    for failed_batch in failed_batches:
                        retry_logger = logger.create_child_logger(
                            f"retry_{failed_batch['batch_id']}"
                        )

                        try:
                            result = session.execute_command(
                                "retry_batch",
                                batch_id=failed_batch["batch_id"],
                                config=failed_batch["config"],
                            )

                            batch_results.append(
                                {
                                    "batch_id": failed_batch["batch_id"],
                                    "status": "retry_success",
                                    "result": result,
                                }
                            )

                            retry_logger.success(
                                f"Retry of batch {failed_batch['batch_id']} succeeded"
                            )

                        except Exception as e:
                            retry_logger.error(f"Retry failed: {e}")

            # Final aggregation
            with logger.operation("aggregation"):
                session.execute_command("aggregate_batch_results")
                logger.success("Batch processing completed")

            # Generate processing summary
            successful_batches = len(
                [r for r in batch_results if r["status"] in ["success", "retry_success"]]
            )
            total_time = time.time() - session.state.start_time

            summary = {
                "total_batches": len(batch_configs),
                "successful_batches": successful_batches,
                "failed_batches": len(batch_configs) - successful_batches,
                "total_processing_time": total_time,
                "session_id": session_id,
            }

            logger.info(f"Processing summary: {summary}")

        return summary


class DebuggingSessionManager:
    """Example: Interactive debugging session with state preservation."""

    def __init__(self, runtime_dir: Path):
        self.toolkit = SessionToolkit(runtime_dir=runtime_dir, auto_save=True)

    @contextmanager
    def debug_session(self, issue_description: str):
        """Create a debugging session with automatic state management."""

        session_id = self.toolkit.create_session(
            "debugging_session", metadata={"issue": issue_description, "debug_start": time.time()}
        )

        with self.toolkit.session(session_id) as session:
            logger = self.toolkit.get_logger("debugger")

            logger.info(f"Starting debug session: {issue_description}")

            # Setup debugging environment
            with logger.operation("debug_setup"):
                session.execute_command("setup_debug_environment")
                session.execute_command("capture_initial_state")

                # Save clean state checkpoint
                session.save_checkpoint()

            try:
                yield DebugContext(session, logger)

            except Exception as e:
                logger.error(f"Debug session encountered error: {e}")
                # Auto-restore to clean state on error
                session.restore_checkpoint()
                raise

            finally:
                with logger.operation("debug_cleanup"):
                    session.execute_command("cleanup_debug_environment")
                    logger.info("Debug session cleanup completed")


class DebugContext:
    """Context object for debugging operations."""

    def __init__(self, session, logger):
        self.session = session
        self.logger = logger
        self.checkpoint_count = 0

    def reproduce_issue(self, steps: List[str]) -> Dict[str, Any]:
        """Reproduce the issue with detailed logging."""
        with self.logger.operation("issue_reproduction"):
            for i, step in enumerate(steps):
                self.logger.info(f"Reproduction step {i + 1}: {step}")
                result = self.session.execute_command("execute_step", step=step)

                if result.get("status") == "error":
                    self.logger.error(f"Issue reproduced at step {i + 1}")
                    return {"reproduced": True, "step": i + 1, "error": result}

            return {"reproduced": False}

    def save_debug_checkpoint(self, name: str) -> None:
        """Save a named checkpoint during debugging."""
        self.session.save_checkpoint()
        self.checkpoint_count += 1
        self.logger.info(f"Debug checkpoint '{name}' saved ({self.checkpoint_count})")

    def test_fix(self, fix_description: str) -> bool:
        """Test a potential fix."""
        with self.logger.operation("test_fix"):
            self.logger.info(f"Testing fix: {fix_description}")

            # Save state before applying fix
            pre_fix_checkpoint = len(self.session._checkpoints)
            self.save_debug_checkpoint(f"pre_fix_{fix_description}")

            try:
                self.session.execute_command("apply_fix", description=fix_description)
                test_result = self.session.execute_command("verify_fix")

                if test_result.get("status") == "success":
                    self.logger.success(f"Fix '{fix_description}' successful")
                    return True
                self.logger.warning(f"Fix '{fix_description}' failed verification")
                # Restore to pre-fix state
                self.session.restore_checkpoint(pre_fix_checkpoint)
                return False

            except Exception as e:
                self.logger.error(f"Fix '{fix_description}' caused error: {e}")
                # Restore to pre-fix state
                self.session.restore_checkpoint(pre_fix_checkpoint)
                return False


class MonitoringSystem:
    """Example: System monitoring with continuous session management."""

    def __init__(self, runtime_dir: Path):
        self.toolkit = SessionToolkit(runtime_dir=runtime_dir, auto_save=True)
        self.monitoring_active = False

    def start_monitoring(self, components: List[str], interval: float = 60.0):
        """Start system monitoring with session persistence."""

        config = SessionConfig(
            timeout=0,  # No timeout for monitoring
            heartbeat_interval=30.0,
            auto_save_interval=interval,
        )

        session_id = self.toolkit.create_session(
            "system_monitoring",
            config=config,
            metadata={
                "components": components,
                "monitoring_interval": interval,
                "start_time": time.time(),
            },
        )

        with self.toolkit.session(session_id) as session:
            logger = self.toolkit.get_logger("monitor")

            logger.info(f"Starting monitoring for: {', '.join(components)}")
            self.monitoring_active = True

            # Initialize monitoring
            with logger.operation("monitoring_setup"):
                session.execute_command("setup_monitoring", components=components)

            # Monitoring loop (simplified for example)
            cycle_count = 0
            while self.monitoring_active and cycle_count < 5:  # Limited for demo
                cycle_count += 1

                with logger.operation(f"monitoring_cycle_{cycle_count}"):
                    for component in components:
                        component_logger = logger.create_child_logger(component)

                        try:
                            result = session.execute_command("check_component", component=component)

                            status = result.get("status", "unknown")
                            if status == "healthy":
                                component_logger.debug(f"{component} is healthy")
                            else:
                                component_logger.warning(f"{component} status: {status}")

                        except Exception as e:
                            component_logger.error(f"{component} check failed: {e}")

                    # Periodic checkpoint
                    if cycle_count % 10 == 0:
                        session.save_checkpoint()

                # Wait for next cycle (shortened for demo)
                time.sleep(min(interval, 1.0))

            logger.info("Monitoring session completed")

    def stop_monitoring(self):
        """Stop monitoring system."""
        self.monitoring_active = False


def run_advanced_examples():
    """Run all advanced examples."""
    print("Session Management Toolkit - Advanced Examples")
    print("=" * 60)

    runtime_dir = Path("./advanced_examples_runtime")

    # Code Analysis Workflow
    print("\n1. Code Analysis Workflow")
    print("-" * 30)
    analyzer = CodeAnalysisWorkflow(runtime_dir)
    analysis_result = analyzer.analyze_project("/example/project")
    print(f"Analysis completed: {analysis_result['session_id']}")

    # Batch Processing
    print("\n2. Batch Processing with Error Recovery")
    print("-" * 40)
    processor = BatchProcessingManager(runtime_dir)
    batch_configs = [
        {"type": "data_import", "source": "database"},
        {"type": "data_transform", "algorithm": "ml_pipeline"},
        {"type": "data_export", "format": "json"},
    ]
    batch_result = processor.process_data_batches(batch_configs)
    print(f"Batch processing: {batch_result}")

    # Debugging Session
    print("\n3. Interactive Debugging Session")
    print("-" * 35)
    debugger = DebuggingSessionManager(runtime_dir)

    with debugger.debug_session("Memory leak in data processor") as debug:
        # Reproduce issue
        reproduction_steps = ["load_large_dataset", "process_data_chunks", "check_memory_usage"]
        reproduction_result = debug.reproduce_issue(reproduction_steps)
        print(f"Issue reproduction: {reproduction_result}")

        # Test potential fixes
        fixes_to_test = [
            "add_garbage_collection",
            "optimize_memory_allocation",
            "implement_streaming_processing",
        ]

        for fix in fixes_to_test:
            success = debug.test_fix(fix)
            print(f"Fix '{fix}': {'SUCCESS' if success else 'FAILED'}")
            if success:
                break

    # Monitoring System
    print("\n4. System Monitoring")
    print("-" * 20)
    monitor = MonitoringSystem(runtime_dir)
    components = ["database", "api_server", "background_workers"]

    print("Starting monitoring (demo version)...")
    monitor.start_monitoring(components, interval=2.0)
    print("Monitoring completed")

    print("\n" + "=" * 60)
    print("Advanced examples completed!")


if __name__ == "__main__":
    run_advanced_examples()
