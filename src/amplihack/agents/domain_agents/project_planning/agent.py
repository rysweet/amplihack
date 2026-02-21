"""Project Planning domain agent implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from amplihack.agents.domain_agents.base import DomainAgent, EvalLevel, TaskResult, TeachingResult

from . import eval_levels as _eval_levels
from .tools import analyze_dependencies, assess_risks, decompose_project, evaluate_plan

_PROMPTS_DIR = Path(__file__).parent / "prompts"


class ProjectPlanningAgent(DomainAgent):
    """Agent that plans projects: decomposes tasks, identifies dependencies, assesses risks."""

    def __init__(
        self,
        agent_name: str = "project_planning_agent",
        model: str = "gpt-4o-mini",
        skill_injector: Any | None = None,
    ):
        super().__init__(
            agent_name=agent_name,
            domain="project_planning",
            model=model,
            skill_injector=skill_injector,
        )

    def _register_tools(self) -> None:
        self.executor.register_action("decompose_project", decompose_project)
        self.executor.register_action("analyze_dependencies", analyze_dependencies)
        self.executor.register_action("assess_risks", assess_risks)
        self.executor.register_action("evaluate_plan", evaluate_plan)

    def get_system_prompt(self) -> str:
        prompt_file = _PROMPTS_DIR / "system.txt"
        if prompt_file.exists():
            return prompt_file.read_text()
        return "You are an expert project planner."

    def execute_task(self, task: dict[str, Any]) -> TaskResult:
        description = task.get("description", "")
        task_type = task.get("task_type", "full_plan")
        context = task.get("context", "")

        if task_type == "decompose":
            return self._decompose(description)
        if task_type == "dependencies":
            return self._dependencies(description)
        if task_type == "risks":
            return self._risks(description, context)
        if task_type == "full_plan":
            return self._full_plan(description, context)
        return TaskResult(success=False, output=None, error=f"Unknown task_type: {task_type}")

    def _decompose(self, description: str) -> TaskResult:
        if not description or not description.strip():
            return TaskResult(
                success=True,
                output={"tasks": [], "task_count": 0, "estimated_effort": "unknown"},
                metadata={"task_type": "decompose"},
            )
        r = self.executor.execute("decompose_project", description=description)
        if not r.success:
            return TaskResult(success=False, output=None, error=str(r.output))
        return TaskResult(
            success=True,
            output=r.output,
            metadata={"task_type": "decompose"},
        )

    def _dependencies(self, description: str) -> TaskResult:
        # First decompose, then analyze dependencies
        decomp = decompose_project(description)
        tasks = decomp.get("tasks", [])

        r = self.executor.execute("analyze_dependencies", tasks=tasks)
        if not r.success:
            return TaskResult(success=False, output=None, error=str(r.output))

        output = r.output
        output["tasks"] = tasks
        output["task_count"] = len(tasks)
        return TaskResult(
            success=True,
            output=output,
            metadata={"task_type": "dependencies"},
        )

    def _risks(self, description: str, context: str) -> TaskResult:
        decomp = decompose_project(description)
        tasks = decomp.get("tasks", [])

        r = self.executor.execute("assess_risks", tasks=tasks, context=context + " " + description)
        if not r.success:
            return TaskResult(success=False, output=None, error=str(r.output))

        output = r.output
        output["tasks"] = tasks
        output["task_count"] = len(tasks)
        return TaskResult(
            success=True,
            output=output,
            metadata={"task_type": "risks"},
        )

    def _full_plan(self, description: str, context: str) -> TaskResult:
        if not description or not description.strip():
            return TaskResult(
                success=True,
                output={
                    "tasks": [],
                    "task_count": 0,
                    "plan_score": 0.0,
                    "quality_level": "insufficient",
                    "risks": [],
                    "recommendations": ["Provide a project description"],
                },
                metadata={"task_type": "full_plan"},
            )

        # Step 1: Decompose
        decomp = decompose_project(description)
        tasks = decomp.get("tasks", [])

        # Step 2: Dependencies
        r_deps = self.executor.execute("analyze_dependencies", tasks=tasks)
        deps = r_deps.output if r_deps.success else {}

        # Step 3: Risks
        r_risks = self.executor.execute("assess_risks", tasks=tasks, context=context + " " + description)
        risks = r_risks.output if r_risks.success else {}

        # Step 4: Evaluate plan quality
        r_eval = self.executor.execute("evaluate_plan", tasks=tasks, dependencies=deps, risks=risks)
        plan_eval = r_eval.output if r_eval.success else {}

        return TaskResult(
            success=True,
            output={
                "tasks": tasks,
                "task_count": len(tasks),
                "estimated_effort": decomp.get("estimated_effort", "unknown"),
                "dependencies": deps.get("dependencies", []),
                "dependency_count": deps.get("dependency_count", 0),
                "critical_path": deps.get("critical_path", []),
                "parallel_groups": deps.get("parallel_groups", []),
                "risks": risks.get("risks", []),
                "risk_count": risks.get("risk_count", 0),
                "risk_score": risks.get("risk_score", 0),
                "mitigation_strategies": risks.get("mitigation_strategies", []),
                "plan_score": plan_eval.get("plan_score", 0),
                "quality_level": plan_eval.get("quality_level", "unknown"),
                "dimension_scores": plan_eval.get("dimension_scores", {}),
                "recommendations": plan_eval.get("recommendations", []),
                "tool_results": {
                    "decomposition": decomp,
                    "dependencies": deps,
                    "risks": risks,
                    "evaluation": plan_eval,
                },
            },
            metadata={"task_type": "full_plan"},
        )

    def get_eval_levels(self) -> list[EvalLevel]:
        return _eval_levels.get_eval_levels()

    def teach(self, topic: str, student_level: str = "beginner") -> TeachingResult:
        plans = {
            "decomposition": (
                "1. Why task decomposition matters\n"
                "2. Breaking work into manageable pieces\n"
                "3. Estimating effort per task\n"
                "4. Assigning ownership\n"
                "5. Practice decomposing"
            ),
            "dependency": (
                "1. What are task dependencies?\n"
                "2. Types: finish-to-start, start-to-start\n"
                "3. Critical path identification\n"
                "4. Parallel execution opportunities\n"
                "5. Practice analysis"
            ),
            "risk": (
                "1. Types of project risks\n"
                "2. Risk assessment techniques\n"
                "3. Mitigation strategies\n"
                "4. Risk monitoring\n"
                "5. Practice assessment"
            ),
        }
        instructions = {
            "decomposition": (
                "When decomposing projects:\n\n"
                "1. **Start with phases**: Design -> Implement -> Test -> Deploy\n"
                "   Bad: One big task 'Build the system'\n"
                "   Good: Separate tasks for each component and phase\n\n"
                "2. **Right granularity**: Each task should be 1-5 days of work\n"
                "   Bad: 'Build entire backend' (too big)\n"
                "   Good: 'Implement user auth endpoint' (right size)\n\n"
                "3. **Clear ownership**: Every task needs a clear owner\n\n"
                "4. **Complexity tags**: Label tasks low/medium/high"
            ),
            "dependency": (
                "When analyzing dependencies:\n\n"
                "1. **Sequential**: Design MUST finish before implementation starts\n\n"
                "2. **Parallel**: Multiple implementation tasks can run simultaneously\n"
                "   Example: Frontend and backend can be built in parallel\n\n"
                "3. **Critical Path**: The longest chain of dependencies\n"
                "   This determines minimum project duration\n\n"
                "4. **Blocking Tasks**: Tasks that many others depend on"
            ),
            "risk": (
                "When assessing risks:\n\n"
                "1. **Technical Risks**: New technology, legacy integration\n"
                "   Mitigation: Proof of concept, prototyping\n\n"
                "2. **Schedule Risks**: Too many complex tasks, unclear timeline\n"
                "   Mitigation: Buffer time, phased delivery\n\n"
                "3. **Resource Risks**: Single point of failure, unassigned work\n"
                "   Mitigation: Cross-training, clear ownership\n\n"
                "4. **Scope Risks**: Unclear requirements, scope creep\n"
                "   Mitigation: Requirements lock, change control"
            ),
        }

        key = topic.lower().split()[0] if topic else "decomposition"
        lesson_plan = plans.get(key, plans["decomposition"])
        if student_level == "advanced":
            lesson_plan += "\n6. Advanced: Agile estimation techniques"
        instruction = instructions.get(key, instructions["decomposition"])

        practice = "Build a REST API:\n- Design the API schema\n- Implement CRUD endpoints\n- Add authentication\n- Write integration tests\n- Deploy to cloud"
        decomp = decompose_project(practice)
        deps = analyze_dependencies(decomp.get("tasks", []))

        questions = [
            f"What are the key principles of project {topic}?",
            f"Can you show me an example of {topic}?",
        ]
        answers = [
            f"The key principles: break work into phases, estimate effort, assign owners, manage {topic}.",
            f"Example: 'Build REST API' decomposes into {decomp.get('task_count', 0)} tasks with {len(deps.get('dependencies', []))} dependencies.",
        ]

        attempt = (
            f"Student findings:\n"
            f"- Decomposed into {decomp.get('task_count', 0)} tasks\n"
            f"- Estimated effort: {decomp.get('estimated_effort', 'unknown')}\n"
            f"- Found {len(deps.get('dependencies', []))} dependencies"
        )

        return TeachingResult(
            lesson_plan=lesson_plan,
            instruction=instruction,
            student_questions=questions,
            agent_answers=answers,
            student_attempt=attempt,
        )
