"""
Auto-Mode Integration Demo

Demonstrates the complete Claude Agent SDK integration for auto-mode,
showing how all components work together to provide persistent analysis
and autonomous progression through complex objectives.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.sdk import (
    AutoModeOrchestrator,
    AutoModeConfig,
    AutoModeState,
    AnalysisType,
    SessionConfig,
    PromptType,
    ErrorSeverity
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoModeDemo:
    """Demonstration of auto-mode integration capabilities"""

    def __init__(self):
        self.orchestrator = None

    async def run_complete_demo(self):
        """Run complete auto-mode demonstration"""
        logger.info("=== Auto-Mode Integration Demo ===")

        try:
            # 1. Initialize and configure auto-mode
            await self._demo_initialization()

            # 2. Start session with complex objective
            await self._demo_session_creation()

            # 3. Simulate development workflow
            await self._demo_development_workflow()

            # 4. Demonstrate error handling
            await self._demo_error_handling()

            # 5. Show progress monitoring
            await self._demo_progress_monitoring()

            # 6. Demonstrate session recovery
            await self._demo_session_recovery()

        except Exception as e:
            logger.error(f"Demo failed: {e}", exc_info=True)
        finally:
            await self._cleanup()

    async def _demo_initialization(self):
        """Demonstrate initialization of auto-mode components"""
        logger.info("--- Initializing Auto-Mode Components ---")

        # Configure auto-mode with custom settings
        config = AutoModeConfig(
            max_iterations=20,
            iteration_timeout_seconds=60,
            min_confidence_threshold=0.6,
            auto_progression_enabled=True,
            persistence_enabled=True
        )

        # Create orchestrator
        self.orchestrator = AutoModeOrchestrator(config)

        # Set up callbacks for monitoring
        self.orchestrator.add_state_change_callback(self._on_state_change)
        self.orchestrator.add_milestone_callback(self._on_milestone)

        logger.info("✓ Auto-mode orchestrator initialized")
        logger.info(f"✓ Configuration: {config.max_iterations} max iterations, persistence enabled")

    async def _demo_session_creation(self):
        """Demonstrate creating an auto-mode session"""
        logger.info("--- Creating Auto-Mode Session ---")

        objective = """
        Build a comprehensive e-commerce REST API with the following features:
        1. User authentication and authorization (JWT-based)
        2. Product catalog management (CRUD operations)
        3. Shopping cart functionality
        4. Order processing and payment integration
        5. Admin dashboard for inventory management
        6. Comprehensive testing and documentation
        """

        working_directory = "/tmp/ecommerce_api_project"

        # Start session
        session_id = await self.orchestrator.start_auto_mode_session(
            objective.strip(),
            working_directory
        )

        logger.info(f"✓ Session created: {session_id}")
        logger.info(f"✓ Objective: {objective.strip()[:100]}...")
        logger.info(f"✓ Working directory: {working_directory}")

    async def _demo_development_workflow(self):
        """Demonstrate processing Claude Code output through auto-mode"""
        logger.info("--- Simulating Development Workflow ---")

        # Simulate a series of Claude Code outputs representing development progress
        development_outputs = [
            {
                "output": "I'll start by setting up the project structure and implementing user authentication.",
                "iteration": 1
            },
            {
                "output": """
                I've created the basic project structure with the following components:
                - FastAPI application setup
                - User model with SQLAlchemy
                - JWT authentication middleware
                - Basic user registration and login endpoints
                - Password hashing with bcrypt
                """,
                "iteration": 2
            },
            {
                "output": """
                Added comprehensive user authentication:
                - JWT token generation and validation
                - Role-based access control (admin, customer)
                - Password reset functionality
                - Email verification system
                - Rate limiting on auth endpoints
                - Security headers and CORS configuration
                """,
                "iteration": 3
            },
            {
                "output": """
                Implemented product catalog management:
                - Product model with categories, pricing, inventory
                - CRUD operations for products (admin only)
                - Product search and filtering
                - Image upload and management
                - Inventory tracking
                - Product reviews and ratings system
                """,
                "iteration": 4
            },
            {
                "output": """
                Built shopping cart functionality:
                - Cart model linked to users
                - Add/remove items from cart
                - Quantity management
                - Cart persistence across sessions
                - Price calculations including tax
                - Cart abandonment handling
                """,
                "iteration": 5
            }
        ]

        for dev_output in development_outputs:
            logger.info(f"Processing iteration {dev_output['iteration']}...")

            # Process through auto-mode
            result = await self.orchestrator.process_claude_output(
                dev_output["output"],
                {"iteration": dev_output['iteration'], "timestamp": datetime.now().isoformat()}
            )

            # Log analysis results
            analysis = result["analysis"]
            logger.info(f"  Confidence: {analysis['confidence']:.2f}")
            logger.info(f"  Quality Score: {analysis['quality_score']:.2f}")
            logger.info(f"  Findings: {len(analysis['findings'])} identified")

            if result.get("next_action"):
                logger.info(f"  Next Action Generated: {result['next_action'][:100]}...")

            # Small delay to simulate real development
            await asyncio.sleep(0.5)

    async def _demo_error_handling(self):
        """Demonstrate error handling and recovery"""
        logger.info("--- Demonstrating Error Handling ---")

        try:
            # Simulate problematic output that might cause issues
            problematic_outputs = [
                "I encountered an error: Connection timeout when accessing the database.",
                "The authentication system is failing with 500 errors on login attempts.",
                "Tests are failing due to import errors and missing dependencies."
            ]

            for i, output in enumerate(problematic_outputs):
                logger.info(f"Processing error scenario {i + 1}...")

                try:
                    result = await self.orchestrator.process_claude_output(output)

                    # Check if error was handled gracefully
                    if result["analysis"]["confidence"] < 0.5:
                        logger.info("  ✓ Low confidence detected - error handling activated")

                    if "error" in result["analysis"]["ai_reasoning"].lower():
                        logger.info("  ✓ Error diagnosis mode activated")

                except Exception as e:
                    logger.info(f"  ✓ Error handled gracefully: {type(e).__name__}")

        except Exception as e:
            logger.error(f"Error handling demo failed: {e}")

    async def _demo_progress_monitoring(self):
        """Demonstrate progress monitoring and milestone tracking"""
        logger.info("--- Progress Monitoring and Milestones ---")

        # Get current progress
        current_state = self.orchestrator.get_current_state()
        progress_summary = self.orchestrator.get_progress_summary()

        logger.info(f"Current State: {current_state['state']}")
        logger.info(f"Iteration: {current_state['iteration']}")
        logger.info(f"Milestones Achieved: {progress_summary['milestones']}")
        logger.info(f"Progress: {progress_summary['progress_percentage']:.1f}%")

        if progress_summary.get('average_confidence'):
            logger.info(f"Average Confidence: {progress_summary['average_confidence']:.2f}")

        # Show analysis engine statistics
        analysis_stats = self.orchestrator.analysis_engine.get_analysis_stats()
        logger.info(f"Total Analyses: {analysis_stats['total_analyses']}")
        logger.info(f"Cache Hit Rate: {analysis_stats.get('cache_hit_rate', 0):.2f}")

        # Show session statistics
        session_stats = self.orchestrator.session_manager.get_session_stats()
        logger.info(f"Active Sessions: {session_stats['active_sessions']}")
        logger.info(f"Total Conversations: {session_stats['total_conversations']}")

    async def _demo_session_recovery(self):
        """Demonstrate session persistence and recovery"""
        logger.info("--- Session Persistence and Recovery ---")

        if not self.orchestrator.active_session_id:
            logger.warning("No active session to demonstrate recovery")
            return

        session_id = self.orchestrator.active_session_id
        logger.info(f"Current session: {session_id}")

        # Simulate saving session state
        await self.orchestrator._take_state_snapshot("Demo checkpoint")
        logger.info("✓ Session state saved")

        # Show that conversation history is preserved
        conversation_history = await self.orchestrator.session_manager.get_conversation_history(
            session_id, limit=3
        )
        logger.info(f"✓ Conversation history: {len(conversation_history)} messages preserved")

        # Demonstrate session recovery (would work across restarts)
        try:
            recovered_session = await self.orchestrator.session_manager.recover_session(session_id)
            logger.info(f"✓ Session recovery successful: {recovered_session.status}")
        except Exception as e:
            logger.info(f"Recovery test: {e}")

    def _on_state_change(self, new_state: AutoModeState, snapshot):
        """Callback for state changes"""
        logger.info(f"🔄 State Change: {new_state.value}")

    def _on_milestone(self, milestone):
        """Callback for milestones"""
        logger.info(f"🎯 Milestone Achieved: {milestone.description} (confidence: {milestone.confidence:.2f})")

    async def _cleanup(self):
        """Clean up demo resources"""
        logger.info("--- Cleanup ---")
        if self.orchestrator:
            await self.orchestrator.stop_auto_mode()
            logger.info("✓ Auto-mode session stopped")


async def run_integration_test():
    """Run basic integration test"""
    logger.info("=== Running Integration Test ===")

    try:
        # Quick integration test
        config = AutoModeConfig(max_iterations=5, persistence_enabled=False)
        orchestrator = AutoModeOrchestrator(config)

        # Start session
        session_id = await orchestrator.start_auto_mode_session(
            "Create a simple Python calculator with basic operations",
            "/tmp/calculator_test"
        )

        # Process a few outputs
        test_outputs = [
            "I'll create a Calculator class with basic arithmetic operations.",
            "Implemented Calculator class with add, subtract, multiply, and divide methods.",
            "Added error handling for division by zero and input validation."
        ]

        for output in test_outputs:
            result = await orchestrator.process_claude_output(output)
            assert result["iteration"] > 0
            assert "analysis" in result
            logger.info(f"✓ Processed output, confidence: {result['analysis']['confidence']:.2f}")

        # Check final state
        final_state = orchestrator.get_current_state()
        assert final_state["state"] == "active"
        logger.info(f"✓ Final state: {final_state['iteration']} iterations completed")

        # Cleanup
        await orchestrator.stop_auto_mode()
        logger.info("✓ Integration test passed")

    except Exception as e:
        logger.error(f"Integration test failed: {e}", exc_info=True)
        raise


async def main():
    """Main demo entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        await run_integration_test()
    else:
        demo = AutoModeDemo()
        await demo.run_complete_demo()


if __name__ == "__main__":
    asyncio.run(main())