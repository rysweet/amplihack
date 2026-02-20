"""Evaluation levels for the Project Planning agent."""

from __future__ import annotations

from amplihack.agents.domain_agents.base import EvalLevel, EvalScenario

_SIMPLE_PROJECT = (
    "Build a user authentication system:\n"
    "- Design the database schema for users\n"
    "- Implement login and registration endpoints\n"
    "- Create password hashing and validation\n"
    "- Test authentication flows\n"
    "- Deploy to staging environment\n"
)

_COMPLEX_PROJECT = (
    "Migrate the monolith to microservices:\n"
    "1. Design microservice architecture\n"
    "2. Implement user service\n"
    "3. Implement order service\n"
    "4. Implement payment service (integrate with Stripe)\n"
    "5. Build API gateway\n"
    "6. Create service discovery mechanism\n"
    "7. Implement distributed tracing\n"
    "8. Migrate legacy database\n"
    "9. Test inter-service communication\n"
    "10. Deploy with blue-green deployment strategy\n"
    "The timeline is unclear and some requirements are TBD.\n"
)

_RISKY_PROJECT = (
    "Build a real-time analytics dashboard:\n"
    "- Design the architecture for streaming data\n"
    "- Implement data pipeline with new technology (Apache Flink)\n"
    "- Build complex visualization components\n"
    "- Integrate with legacy data warehouse\n"
    "- Performance test with 10M events/second\n"
    "- Deploy to production\n"
    "All work assigned to Bob. Possibly need ML features too.\n"
)


def get_eval_levels() -> list[EvalLevel]:
    return [_l1(), _l2(), _l3(), _l4()]


def _l1() -> EvalLevel:
    return EvalLevel(
        level_id="L1",
        name="Task Decomposition",
        description="Decomposes projects into actionable tasks",
        passing_threshold=0.6,
        scenarios=[
            EvalScenario(
                scenario_id="L1-001",
                name="Simple project decomposition",
                input_data={"description": _SIMPLE_PROJECT, "task_type": "decompose"},
                expected_output={
                    "min_task_count": 3,
                    "must_mention": ["design", "implement", "test"],
                },
                grading_rubric="Must extract at least 3 tasks with design, impl, and test phases.",
            ),
            EvalScenario(
                scenario_id="L1-002",
                name="Complex project decomposition",
                input_data={"description": _COMPLEX_PROJECT, "task_type": "decompose"},
                expected_output={
                    "min_task_count": 5,
                },
                grading_rubric="Must extract many tasks from complex project.",
            ),
            EvalScenario(
                scenario_id="L1-003",
                name="Empty project handling",
                input_data={"description": "", "task_type": "decompose"},
                expected_output={},
                grading_rubric="Must handle empty project description gracefully.",
            ),
        ],
    )


def _l2() -> EvalLevel:
    return EvalLevel(
        level_id="L2",
        name="Dependency Analysis",
        description="Identifies dependencies between tasks",
        passing_threshold=0.6,
        scenarios=[
            EvalScenario(
                scenario_id="L2-001",
                name="Sequential dependencies",
                input_data={"description": _SIMPLE_PROJECT, "task_type": "dependencies"},
                expected_output={
                    "must_mention": ["dependency", "depend"],
                },
                grading_rubric="Must identify design-before-implementation dependency.",
            ),
            EvalScenario(
                scenario_id="L2-002",
                name="Complex dependencies",
                input_data={"description": _COMPLEX_PROJECT, "task_type": "dependencies"},
                expected_output={
                    "must_mention": ["critical"],
                },
                grading_rubric="Must identify critical path in complex project.",
            ),
        ],
    )


def _l3() -> EvalLevel:
    return EvalLevel(
        level_id="L3",
        name="Risk Assessment",
        description="Identifies and assesses project risks",
        passing_threshold=0.6,
        scenarios=[
            EvalScenario(
                scenario_id="L3-001",
                name="Technical risk detection",
                input_data={"description": _RISKY_PROJECT, "task_type": "risks"},
                expected_output={
                    "must_mention": ["risk", "technical"],
                },
                grading_rubric="Must identify technical risks from new technology and legacy integration.",
            ),
            EvalScenario(
                scenario_id="L3-002",
                name="Resource risk detection",
                input_data={"description": _RISKY_PROJECT, "task_type": "risks"},
                expected_output={
                    "must_mention": ["risk"],
                },
                grading_rubric="Must identify resource/scope risks.",
            ),
        ],
    )


def _l4() -> EvalLevel:
    return EvalLevel(
        level_id="L4",
        name="Plan Quality",
        description="Produces and evaluates complete project plans",
        passing_threshold=0.5,
        scenarios=[
            EvalScenario(
                scenario_id="L4-001",
                name="Complete plan for simple project",
                input_data={"description": _SIMPLE_PROJECT, "task_type": "full_plan"},
                expected_output={
                    "must_mention": ["plan", "task", "risk"],
                },
                grading_rubric="Must produce a complete plan with tasks, deps, and risks.",
            ),
            EvalScenario(
                scenario_id="L4-002",
                name="Plan quality for risky project",
                input_data={"description": _RISKY_PROJECT, "task_type": "full_plan"},
                expected_output={
                    "must_mention": ["risk", "mitigation"],
                },
                grading_rubric="Must include risk assessment and mitigation for risky project.",
            ),
        ],
    )
