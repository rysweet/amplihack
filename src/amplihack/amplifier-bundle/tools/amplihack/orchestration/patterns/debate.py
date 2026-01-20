"""Multi-Agent Debate orchestrator.

Implements structured multi-perspective debate for important architectural decisions,
design trade-offs, and complex problems where multiple valid approaches exist.

Based on: .claude/workflow/DEBATE_WORKFLOW.md
"""

from pathlib import Path
from typing import Any

from ..execution import run_parallel
from ..session import OrchestratorSession

# Standard perspective profiles
DEFAULT_PERSPECTIVES = [
    {
        "name": "security",
        "focus": "Vulnerabilities, attack vectors, data protection",
        "questions": "What could go wrong? How do we prevent breaches?",
    },
    {
        "name": "performance",
        "focus": "Speed, scalability, resource efficiency",
        "questions": "Will this scale? What are the bottlenecks?",
    },
    {
        "name": "simplicity",
        "focus": "Minimal complexity, ruthless simplification",
        "questions": "Is this the simplest solution? Can we remove abstractions?",
    },
    {
        "name": "maintainability",
        "focus": "Long-term evolution, technical debt",
        "questions": "Can future developers understand this? How hard to change?",
    },
    {
        "name": "user_experience",
        "focus": "API design, usability, developer experience",
        "questions": "Is this intuitive? How will users interact with this?",
    },
]


def run_debate(
    decision_question: str,
    perspectives: list[str] | None = None,
    rounds: int = 3,
    model: str | None = None,
    working_dir: Path | None = None,
    timeout: int | None = None,
) -> dict[str, Any]:
    """Execute multi-agent debate pattern.

    Conducts a structured debate with multiple perspectives to reach consensus
    on complex decisions.

    Steps:
    1. Initialize perspectives (security, performance, simplicity, etc.)
    2. Round 1: Each perspective forms initial position (parallel)
    3. Rounds 2-N: Challenge and respond (parallel per round)
    4. Synthesize consensus

    Args:
        decision_question: The decision/question to debate
        perspectives: List of perspective names to include (default: ["security", "performance", "simplicity"])
        rounds: Number of debate rounds (default: 3)
        model: Claude model to use for all processes (default: None = CLI default)
        working_dir: Working directory for processes (default: current dir)
        timeout: Timeout per process in seconds (default: None = no timeout)

    Returns:
        Dict containing:
        - rounds: List[dict] - each round's results
        - positions: Dict[str, List[str]] - position history per perspective
        - synthesis: ProcessResult - final consensus
        - confidence: str - HIGH/MEDIUM/LOW
        - session_id: str - session identifier for logs
        - success: bool - whether operation completed successfully

    Example:
        >>> result = run_debate(
        ...     decision_question="Should we use PostgreSQL or Redis?",
        ...     perspectives=["security", "performance", "simplicity"],
        ...     rounds=3
        ... )
        >>> print(f"Consensus: {result['synthesis'].output}")
        >>> print(f"Confidence: {result['confidence']}")
    """
    # Setup
    working_dir = working_dir or Path.cwd()
    perspectives = perspectives or ["security", "performance", "simplicity"]

    # Create session
    session = OrchestratorSession(
        pattern_name="debate",
        working_dir=working_dir,
        model=model,
    )

    session.log("Starting Multi-Agent Debate")
    session.log(f"Decision: {decision_question}")
    session.log(f"Perspectives: {', '.join(perspectives)}")
    session.log(f"Rounds: {rounds}")

    # Get perspective profiles
    perspective_profiles = {p["name"]: p for p in DEFAULT_PERSPECTIVES}

    # Validate perspectives
    for p in perspectives:
        if p not in perspective_profiles:
            session.log(
                f"WARNING: Unknown perspective '{p}', using default profile", level="WARNING"
            )
            perspective_profiles[p] = {
                "name": p,
                "focus": f"{p} considerations",
                "questions": f"What {p} aspects should we consider?",
            }

    # Track debate history
    debate_history = {p: [] for p in perspectives}
    round_results = []

    # Step 1 & 2: Round 1 - Initial Positions
    session.log("Round 1: Forming initial positions")

    processes = []
    for perspective_name in perspectives:
        profile = perspective_profiles[perspective_name]

        prompt = f"""You are participating in a structured multi-agent debate.

DECISION QUESTION:
{decision_question}

YOUR ROLE: {profile["name"]} Perspective
FOCUS: {profile["focus"]}
KEY QUESTIONS: {profile["questions"]}

This is ROUND 1: Form your initial position on this decision.

Your task:
1. State your recommended approach to this decision
2. Provide 3-5 supporting arguments from your perspective
3. Identify risks of alternative approaches
4. Quantify claims where possible with data or evidence

Be specific and evidence-based. Challenge assumptions. Focus on YOUR perspective
but be intellectually honest.

Format your response as:

## Recommendation
[Your recommended approach]

## Supporting Arguments
1. [Argument with evidence]
2. [Argument with evidence]
3. [Argument with evidence]

## Risks of Alternatives
- [Alternative approach]: [Specific concerns]

## Assumptions
- [Key assumption 1]
- [Key assumption 2]
"""

        process = session.create_process(
            prompt=prompt,
            process_id=f"round1_{perspective_name}",
            timeout=timeout,
        )
        processes.append((perspective_name, process))

    # Run Round 1 in parallel
    session.log(f"Executing Round 1: {len(processes)} perspectives in parallel")
    round1_results = run_parallel([p[1] for p in processes])

    # Store Round 1 results
    round1_data = {}
    for (perspective_name, _), result in zip(processes, round1_results, strict=False):
        debate_history[perspective_name].append(result.output)
        round1_data[perspective_name] = result

    round_results.append(
        {
            "round": 1,
            "type": "initial_positions",
            "results": round1_data,
        }
    )

    successful_round1 = sum(1 for r in round1_results if r.exit_code == 0)
    session.log(f"Round 1 complete: {successful_round1}/{len(perspectives)} perspectives succeeded")

    if successful_round1 == 0:
        session.log("ERROR: All perspectives failed in Round 1", level="ERROR")
        return {
            "rounds": round_results,
            "positions": debate_history,
            "synthesis": None,
            "confidence": "NONE",
            "session_id": session.session_id,
            "success": False,
        }

    # Rounds 2-N: Challenge and Respond
    for round_num in range(2, rounds + 1):
        session.log(f"Round {round_num}: Challenge and respond")

        # Build context from previous rounds
        previous_context = "\n\n".join(
            [
                f"## {name} Perspective (Previous Round):\n{debate_history[name][-1]}"
                for name in perspectives
                if debate_history[name]  # Only include if has history
            ]
        )

        processes = []
        for perspective_name in perspectives:
            profile = perspective_profiles[perspective_name]

            prompt = f"""You are participating in a structured multi-agent debate.

DECISION QUESTION:
{decision_question}

YOUR ROLE: {profile["name"]} Perspective
FOCUS: {profile["focus"]}

This is ROUND {round_num}: Challenge other perspectives and defend your position.

PREVIOUS ROUND POSITIONS:
{previous_context}

Your task:
1. Challenge arguments from other perspectives that conflict with yours
2. Defend your position against potential criticisms
3. Acknowledge valid points from other perspectives (concessions)
4. Refine your position based on the debate
5. Identify common ground where possible

Be intellectually honest. Concede when others make valid points.
Adjust your position if evidence warrants it.

Format your response as:

## Challenges to Other Perspectives
[Challenge arguments that conflict with your perspective]

## Defense of My Position
[Address potential criticisms]

## Concessions
[Points where you agree with others or adjust your view]

## Refined Position
[Your updated recommendation considering the debate]

## Common Ground Identified
[Areas of agreement across perspectives]
"""

            process = session.create_process(
                prompt=prompt,
                process_id=f"round{round_num}_{perspective_name}",
                timeout=timeout,
            )
            processes.append((perspective_name, process))

        # Run round in parallel
        session.log(f"Executing Round {round_num}: {len(processes)} perspectives in parallel")
        round_results_raw = run_parallel([p[1] for p in processes])

        # Store results
        round_data = {}
        for (perspective_name, _), result in zip(processes, round_results_raw, strict=False):
            debate_history[perspective_name].append(result.output)
            round_data[perspective_name] = result

        round_results.append(
            {
                "round": round_num,
                "type": "challenge_respond",
                "results": round_data,
            }
        )

        successful_round = sum(1 for r in round_results_raw if r.exit_code == 0)
        session.log(
            f"Round {round_num} complete: {successful_round}/{len(perspectives)} perspectives succeeded"
        )

    # Step 6: Facilitator Synthesis
    session.log("Final Step: Facilitator synthesis")

    # Build complete debate transcript
    debate_transcript = []
    for round_data in round_results:
        round_num = round_data["round"]
        debate_transcript.append(f"\n{'=' * 80}\nROUND {round_num}\n{'=' * 80}\n")

        for perspective_name, result in round_data["results"].items():
            if result.exit_code == 0:
                debate_transcript.append(f"\n## {perspective_name.upper()} PERSPECTIVE:\n")
                debate_transcript.append(result.output[:3000])  # Limit to avoid huge prompt
                if len(result.output) > 3000:
                    debate_transcript.append("\n...(truncated)")

    synthesis_prompt = f"""You are a neutral facilitator synthesizing a multi-perspective debate.

DECISION QUESTION:
{decision_question}

PERSPECTIVES INVOLVED:
{", ".join(perspectives)}

COMPLETE DEBATE TRANSCRIPT:
{"".join(debate_transcript)}

Your task as facilitator:
1. Identify strongest evidence-based arguments across all perspectives
2. Determine consensus level (unanimous, majority, split)
3. Make a clear recommendation with confidence level
4. Document dissenting views explicitly
5. Provide implementation guidance
6. Define success metrics and revisit triggers

Format your response as:

## Recommendation
[Clear statement of recommended approach]

## Confidence Level
[HIGH/MEDIUM/LOW] based on:
- Consensus level: [X% of perspectives agree or description]
- Evidence quality: [Strong/Moderate/Weak]
- Risk level: [Low/Medium/High if wrong]

## Rationale
[Why this recommendation, referencing key arguments]

## Key Arguments That Won
1. [Argument that swayed decision]
2. [Argument that swayed decision]

## Dissenting Views
[Strongest counter-arguments and remaining concerns]

## Implementation Guidance
[Concrete steps to execute this decision]

## Success Metrics
[How to measure if this was the right choice]

## Revisit Triggers
[Conditions requiring reconsideration of this decision]
"""

    synthesis_process = session.create_process(
        prompt=synthesis_prompt,
        process_id="facilitator_synthesis",
        timeout=timeout,
    )

    session.log("Running facilitator synthesis...")
    synthesis_result = synthesis_process.run()

    # Determine confidence level
    confidence = "MEDIUM"  # Default
    if synthesis_result.exit_code == 0:
        output_lower = synthesis_result.output.lower()
        if "confidence level" in output_lower:
            if "high" in output_lower:
                confidence = "HIGH"
            elif "low" in output_lower:
                confidence = "LOW"

        # Also check consensus
        successful_perspectives = sum(
            1
            for p_results in [r["results"] for r in round_results]
            for result in p_results.values()
            if result.exit_code == 0
        )
        total_perspective_runs = len(perspectives) * rounds

        if successful_perspectives == total_perspective_runs:
            confidence = "HIGH"  # All perspectives participated successfully
        elif successful_perspectives < total_perspective_runs * 0.5:
            confidence = "LOW"  # Many failures
    else:
        confidence = "LOW"
        session.log("WARNING: Synthesis failed", level="WARNING")

    session.log(f"Debate complete. Confidence: {confidence}")
    session.log(f"Session logs: {session.log_dir}")

    return {
        "rounds": round_results,
        "positions": debate_history,
        "synthesis": synthesis_result,
        "confidence": confidence,
        "session_id": session.session_id,
        "success": synthesis_result.exit_code == 0,
    }
