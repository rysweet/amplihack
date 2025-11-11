"""Prompt templates for auto mode."""


class PromptTemplates:
    """Centralized prompt template management for auto mode sessions."""

    @staticmethod
    def build_philosophy_context() -> str:
        """Build comprehensive philosophy and decision-making context.

        Returns context string that instructs Claude on autonomous decision-making
        using project philosophy files.
        """
        return """AUTONOMOUS MODE: You are in auto mode. Do NOT ask questions. Make decisions using:
1. Explicit user requirements (HIGHEST PRIORITY - cannot be overridden)
2. @.claude/context/USER_PREFERENCES.md guidance (MANDATORY - must follow)
3. @.claude/context/PHILOSOPHY.md principles (ruthless simplicity, zero-BS, modular design)
4. @.claude/workflow/DEFAULT_WORKFLOW.md patterns
5. @.claude/context/USER_REQUIREMENT_PRIORITY.md for resolving conflicts

Decision Authority:
- YOU DECIDE: How to implement, what patterns to use, technical details, architecture
- YOU PRESERVE: Explicit user requirements, user preferences, "must have" constraints
- WHEN AMBIGUOUS: Apply philosophy principles to make the simplest, most modular choice

Document your decisions and reasoning in comments/logs."""

    @staticmethod
    def build_clarify_prompt(philosophy_context: str, user_prompt: str) -> str:
        """Build turn 1 clarification prompt.

        Args:
            philosophy_context: Philosophy and decision-making context
            user_prompt: Original user request

        Returns:
            Formatted clarification prompt
        """
        return f"""{philosophy_context}

Task: Analyze this user request and clarify the objective with evaluation criteria.

1. IDENTIFY EXPLICIT REQUIREMENTS: Extract any "must have", "all", "include everything", quoted specifications
2. IDENTIFY IMPLICIT PREFERENCES: What user likely wants based on @.claude/context/USER_PREFERENCES.md
3. APPLY PHILOSOPHY: Ruthless simplicity from @.claude/context/PHILOSOPHY.md, modular design, zero-BS implementation
4. DEFINE SUCCESS CRITERIA: Clear, measurable, aligned with philosophy

User Request:
{user_prompt}"""

    @staticmethod
    def build_planning_prompt(philosophy_context: str, objective: str) -> str:
        """Build turn 2 planning prompt.

        Args:
            philosophy_context: Philosophy and decision-making context
            objective: Clarified objective from turn 1

        Returns:
            Formatted planning prompt
        """
        return f"""{philosophy_context}

Reference:
- @.claude/context/PHILOSOPHY.md for design principles
- @.claude/workflow/DEFAULT_WORKFLOW.md for standard workflow steps
- @.claude/context/USER_PREFERENCES.md for user-specific preferences

Task: Create an execution plan that:
1. PRESERVES all explicit user requirements from objective
2. APPLIES ruthless simplicity and modular design principles
3. IDENTIFIES parallel execution opportunities (agents, tasks, operations)
4. FOLLOWS the brick philosophy (self-contained modules with clear contracts)
5. IMPLEMENTS zero-BS approach (no stubs, no TODOs, no placeholders)

Plan Structure:
- List explicit requirements that CANNOT be changed
- Break work into self-contained modules (bricks)
- Identify what can execute in parallel
- Define clear contracts between components
- Specify success criteria for each step

Objective:
{objective}"""

    @staticmethod
    def build_execution_prompt(
        philosophy_context: str,
        plan: str,
        objective: str,
        turn: int,
        max_turns: int,
        new_instructions: str = "",
    ) -> str:
        """Build execution prompt for turns 3+.

        Args:
            philosophy_context: Philosophy and decision-making context
            plan: Execution plan from turn 2
            objective: Original objective from turn 1
            turn: Current turn number
            max_turns: Maximum number of turns
            new_instructions: Additional instructions appended during session

        Returns:
            Formatted execution prompt
        """
        return f"""{philosophy_context}

Task: Execute the next part of the plan using specialized agents where possible.

Execution Guidelines:
- Use PARALLEL EXECUTION by default (multiple agents, multiple tasks)
- Apply @.claude/context/PHILOSOPHY.md principles throughout
- Delegate to specialized agents from .claude/agents/* when appropriate
- Implement COMPLETE features (no stubs, no TODOs, no placeholders)
- Make ALL implementation decisions autonomously
- Log your decisions and reasoning

Current Plan:
{plan}

Original Objective:
{objective}
{new_instructions}

Current Turn: {turn}/{max_turns}"""

    @staticmethod
    def build_evaluation_prompt(philosophy_context: str, objective: str, turn: int, max_turns: int) -> str:
        """Build evaluation prompt.

        Args:
            philosophy_context: Philosophy and decision-making context
            objective: Original objective
            turn: Current turn number
            max_turns: Maximum number of turns

        Returns:
            Formatted evaluation prompt
        """
        return f"""{philosophy_context}

Task: Evaluate if the objective is achieved based on:
1. All explicit user requirements met
2. Philosophy principles applied (simplicity, modularity, zero-BS)
3. Success criteria from Turn 1 satisfied
4. No placeholders or incomplete implementations remain
5. All work has actually been thoroughly tested and verified
6. The required workflow has been fully executed

Respond with one of:
- "auto-mode EVALUATION: COMPLETE" - All criteria met, objective achieved
- "auto-mode EVALUATION: IN PROGRESS" - Making progress, continue execution
- "auto-mode EVALUATION: NEEDS ADJUSTMENT" - Issues identified, plan adjustment needed

Include brief reasoning for your evaluation. If incomplete, specify next steps or adjustments needed.

Objective:
{objective}

Current Turn: {turn}/{max_turns}"""

    @staticmethod
    def build_summary_prompt(turn: int, objective: str) -> str:
        """Build summary prompt.

        Args:
            turn: Total number of turns completed
            objective: Original objective

        Returns:
            Formatted summary prompt
        """
        return f"Summarize auto mode session:\nTurns: {turn}\nObjective: {objective}"
