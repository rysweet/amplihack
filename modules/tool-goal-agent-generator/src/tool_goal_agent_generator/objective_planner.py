"""
Objective Planner - Generate execution plans for goals.

Creates structured 3-5 phase plans with dependencies and parallel opportunities.
"""

import uuid

from .models import ExecutionPlan, GoalDefinition, PlanPhase


class ObjectivePlanner:
    """Generate execution plans from goal definitions."""

    # Phase templates for common domains
    DOMAIN_PHASE_TEMPLATES = {
        "data-processing": [
            (
                "Data Collection",
                "Gather required data from sources",
                ["data-ingestion", "validation"],
            ),
            ("Data Transformation", "Transform and clean data", ["parsing", "transformation"]),
            ("Data Analysis", "Analyze processed data", ["analysis", "pattern-detection"]),
            ("Report Generation", "Generate results and reports", ["reporting", "visualization"]),
        ],
        "security-analysis": [
            ("Reconnaissance", "Scan and identify targets", ["scanning", "enumeration"]),
            (
                "Vulnerability Detection",
                "Detect potential vulnerabilities",
                ["vulnerability-scanning", "analysis"],
            ),
            ("Risk Assessment", "Assess and prioritize risks", ["risk-analysis", "scoring"]),
            ("Reporting", "Generate security report", ["reporting", "documentation"]),
        ],
        "automation": [
            ("Setup", "Configure automation environment", ["configuration", "initialization"]),
            ("Workflow Design", "Design automation workflow", ["workflow-design", "orchestration"]),
            ("Execution", "Execute automated tasks", ["task-execution", "monitoring"]),
            ("Validation", "Validate results", ["validation", "quality-check"]),
        ],
        "testing": [
            ("Test Planning", "Plan test strategy", ["test-design", "planning"]),
            ("Test Implementation", "Implement test cases", ["test-coding", "framework-setup"]),
            ("Test Execution", "Run test suite", ["test-execution", "automation"]),
            ("Results Analysis", "Analyze test results", ["analysis", "reporting"]),
        ],
        "deployment": [
            ("Pre-deployment", "Prepare for deployment", ["validation", "backup"]),
            ("Deployment", "Deploy to target environment", ["deployment", "monitoring"]),
            ("Verification", "Verify deployment success", ["verification", "health-check"]),
            ("Post-deployment", "Complete deployment tasks", ["cleanup", "documentation"]),
        ],
        "monitoring": [
            ("Setup Monitors", "Configure monitoring", ["configuration", "instrumentation"]),
            ("Data Collection", "Collect metrics and logs", ["data-collection", "aggregation"]),
            ("Analysis", "Analyze monitoring data", ["analysis", "anomaly-detection"]),
            ("Alerting", "Set up alerts", ["alerting", "notification"]),
        ],
    }

    # Generic phases as fallback
    GENERIC_PHASES = [
        ("Planning", "Plan approach and strategy", ["planning", "analysis"]),
        ("Implementation", "Implement solution", ["coding", "configuration"]),
        ("Testing", "Test implementation", ["testing", "validation"]),
        ("Deployment", "Deploy solution", ["deployment", "verification"]),
    ]

    def generate_plan(self, goal_definition: GoalDefinition) -> ExecutionPlan:
        """
        Generate an execution plan from a goal definition.

        Args:
            goal_definition: Goal to create plan for

        Returns:
            ExecutionPlan with phases and metadata
        """
        # Select phase template based on domain
        phase_templates = self.DOMAIN_PHASE_TEMPLATES.get(
            goal_definition.domain, self.GENERIC_PHASES
        )

        # Create phases
        phases = self._create_phases(phase_templates, goal_definition)

        # Identify parallel opportunities
        parallel_opportunities = self._identify_parallel_opportunities(phases)

        # Calculate required skills
        required_skills = self._calculate_required_skills(phases)

        # Estimate total duration
        total_duration = self._estimate_total_duration(phases, goal_definition.complexity)

        # Identify risk factors
        risk_factors = self._identify_risk_factors(goal_definition)

        return ExecutionPlan(
            goal_id=uuid.uuid4(),
            phases=phases,
            total_estimated_duration=total_duration,
            required_skills=required_skills,
            parallel_opportunities=parallel_opportunities,
            risk_factors=risk_factors,
        )

    def _create_phases(
        self, phase_templates: list[tuple[str, str, list[str]]], goal_definition: GoalDefinition
    ) -> list[PlanPhase]:
        """Create plan phases from templates."""
        phases = []
        dependencies = []

        for i, (name, description, capabilities) in enumerate(phase_templates):
            # Determine if phase is parallel-safe (first phase and last phase usually not)
            parallel_safe = i > 0 and i < len(phase_templates) - 1

            # Estimate duration per phase based on complexity
            duration = self._estimate_phase_duration(goal_definition.complexity)

            # Success indicators based on capabilities
            success_indicators = [
                f"{cap.title()} completed successfully" for cap in capabilities[:2]
            ]

            phase = PlanPhase(
                name=name,
                description=description,
                required_capabilities=capabilities,
                estimated_duration=duration,
                dependencies=dependencies.copy() if i > 0 else [],
                parallel_safe=parallel_safe,
                success_indicators=success_indicators,
            )

            phases.append(phase)
            dependencies = [name]  # Next phase depends on this one

        return phases[:5]  # Limit to 5 phases for MVP

    def _estimate_phase_duration(self, complexity: str) -> str:
        """Estimate duration for a single phase based on complexity."""
        duration_map = {
            "simple": "5 minutes",
            "moderate": "15 minutes",
            "complex": "30 minutes",
        }
        return duration_map.get(complexity, "15 minutes")

    def _estimate_total_duration(self, phases: list[PlanPhase], complexity: str) -> str:
        """Estimate total execution duration."""
        # Simple calculation: sum of phase durations
        duration_values = {
            "5 minutes": 5,
            "15 minutes": 15,
            "30 minutes": 30,
        }

        total_minutes = sum(duration_values.get(phase.estimated_duration, 15) for phase in phases)

        # Add overhead based on complexity
        overhead_map = {
            "simple": 1.1,  # 10% overhead
            "moderate": 1.2,  # 20% overhead
            "complex": 1.3,  # 30% overhead
        }

        total_minutes = int(total_minutes * overhead_map.get(complexity, 1.2))

        # Format duration
        if total_minutes < 60:
            return f"{total_minutes} minutes"
        hours = total_minutes // 60
        minutes = total_minutes % 60
        if minutes > 0:
            return f"{hours} hour{'s' if hours > 1 else ''} {minutes} minutes"
        return f"{hours} hour{'s' if hours > 1 else ''}"

    def _identify_parallel_opportunities(self, phases: list[PlanPhase]) -> list[list[str]]:
        """Identify phases that can execute in parallel."""
        parallel_groups = []
        current_group = []

        for phase in phases:
            if phase.parallel_safe and not phase.dependencies:
                current_group.append(phase.name)
            else:
                if current_group:
                    parallel_groups.append(current_group)
                    current_group = []

        if current_group:
            parallel_groups.append(current_group)

        return parallel_groups

    def _calculate_required_skills(self, phases: list[PlanPhase]) -> list[str]:
        """Calculate unique skills needed across all phases."""
        all_capabilities = []
        for phase in phases:
            all_capabilities.extend(phase.required_capabilities)

        # Convert capabilities to skill names (simplified for MVP)
        skills = set()
        for capability in all_capabilities:
            # Convert "data-ingestion" -> "data-processor", etc.
            if "data" in capability:
                skills.add("data-processor")
            elif "security" in capability or "vulnerability" in capability:
                skills.add("security-analyzer")
            elif "test" in capability:
                skills.add("tester")
            elif "deploy" in capability:
                skills.add("deployer")
            elif "monitor" in capability or "alert" in capability:
                skills.add("monitor")
            elif "report" in capability or "document" in capability:
                skills.add("documenter")
            else:
                skills.add("generic-executor")

        return sorted(list(skills))

    def _identify_risk_factors(self, goal_definition: GoalDefinition) -> list[str]:
        """Identify potential risk factors based on goal."""
        risks = []

        # Complexity-based risks
        if goal_definition.complexity == "complex":
            risks.append("High complexity may require extended execution time")

        # Domain-specific risks
        domain_risks = {
            "security-analysis": "Scan may identify critical vulnerabilities requiring immediate action",
            "deployment": "Deployment errors could affect production systems",
            "data-processing": "Large data volumes may cause performance issues",
            "automation": "Automated changes may have unintended side effects",
        }

        if goal_definition.domain in domain_risks:
            risks.append(domain_risks[goal_definition.domain])

        # Constraint-based risks
        if any("time" in c.lower() for c in goal_definition.constraints):
            risks.append("Time constraints may limit thoroughness")

        if not risks:
            risks.append("Standard execution risks apply")

        return risks
