"""Lesson 2 content builder."""

from __future__ import annotations

import textwrap

from amplihack.agents.teaching.models import Exercise, Lesson, QuizQuestion


def _build_lesson_2() -> Lesson:
    """Lesson 2: Your First Agent (CLI basics)."""
    return Lesson(
        id="L02",
        title="Your First Agent (CLI Basics)",
        description="Write a prompt file and use the CLI to generate your first agent.",
        content=textwrap.dedent("""\
            # Lesson 2: Your First Agent

            ## Step 1 -- Write a Prompt File

            Create a file called `my_goal.md`:

            ```markdown
            # Goal: Learn and Summarize Python Best Practices

            ## Objective
            Build an agent that reads Python style guides and can answer
            questions about best practices.

            ## Domain
            software-engineering

            ## Constraints
            - Focus on PEP-8 and type-hinting
            - Keep answers concise

            ## Success Criteria
            - Can explain PEP-8 naming conventions
            - Can describe when to use type hints
            ```

            The file needs four sections: Goal/Objective, Domain, Constraints,
            and Success Criteria.

            ## Step 2 -- Run the CLI

            ```bash
            amplihack new --file my_goal.md
            ```

            This runs the full pipeline and creates a directory under
            `./goal_agents/` with a runnable `main.py`.

            ## Step 3 -- Run Your Agent

            ```bash
            cd goal_agents/<agent-name>
            python main.py
            ```

            ## What Happens Under the Hood

            1. PromptAnalyzer parses `my_goal.md` and extracts:
               - goal = "Learn and Summarize Python Best Practices"
               - domain = "software-engineering"
               - complexity = "moderate"
            2. ObjectivePlanner creates an ExecutionPlan with phases.
            3. SkillSynthesizer matches skills from `.claude/agents/amplihack/`.
            4. AgentAssembler builds the GoalAgentBundle.
            5. GoalAgentPackager writes the agent directory to disk.
        """),
        prerequisites=["L01"],
        exercises=[
            Exercise(
                id="E02-01",
                instruction=(
                    "Write a complete prompt.md file for an agent that learns about "
                    "Docker container security. Include all four required sections."
                ),
                expected_output=(
                    "# Goal: Learn Docker Container Security\n\n"
                    "## Objective\nBuild an agent that learns Docker security...\n\n"
                    "## Constraints\n- Focus on container isolation...\n\n"
                    "## Success Criteria\n- Can explain Docker namespaces..."
                ),
                hint="You need: # Goal, ## Constraints, ## Success Criteria at minimum.",
                validation_fn="validate_prompt_file",
            ),
            Exercise(
                id="E02-02",
                instruction=(
                    "Write the exact CLI command to generate an agent from "
                    "a file called docker_security.md with verbose output."
                ),
                expected_output="amplihack new --file docker_security.md --verbose",
                hint="Use the --file flag and --verbose for extra output.",
                validation_fn="validate_cli_command",
            ),
        ],
        quiz=[
            QuizQuestion(
                question="What are the four required sections in a prompt.md file?",
                correct_answer="Goal/Objective, Domain, Constraints, Success Criteria",
                wrong_answers=[
                    "Title, Body, Footer, Appendix",
                    "Input, Output, Config, Tests",
                    "Goal, Steps, Results, Metrics",
                ],
                explanation="The PromptAnalyzer expects these specific sections.",
            ),
            QuizQuestion(
                question="Where does the CLI output the generated agent by default?",
                correct_answer="./goal_agents/<agent-name>/",
                wrong_answers=[
                    "./agents/output/",
                    "./build/agents/",
                    "~/.amplihack/agents/",
                ],
                explanation="The default output directory is ./goal_agents/.",
            ),
            QuizQuestion(
                question="Which flag overrides the default output directory?",
                correct_answer="--output or -o",
                wrong_answers=["--dir", "--target", "--path"],
                explanation="Use --output or -o to specify a custom output path.",
            ),
        ],
    )
