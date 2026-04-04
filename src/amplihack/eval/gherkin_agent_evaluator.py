"""Agent-based consensus evaluator for the Gherkin v2 experiment.

Replaces regex/keyword heuristic scoring with N independent LLM evaluators
that read the generated code against the acceptance criteria and .feature
spec, then vote pass/fail on each of the 6 behavioral features.

Consensus score per feature = fraction of agents that voted PASS.

Supports two backends:
- Direct Anthropic API (requires ANTHROPIC_API_KEY env var)
- Goal-seeking agent runtime (uses Claude Code SDK auth, no API key needed)
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from amplihack.eval.tla_prompt_experiment import ConditionMetrics

# The 6 features we evaluate, in canonical order.
FEATURES = (
    "conditional_execution",
    "dependency_handling",
    "retry_logic",
    "timeout_semantics",
    "output_capture",
    "sub_recipe_delegation",
)

EVALUATION_KIND = "agent_consensus_v1"

# Each evaluator gets a slightly different persona to reduce correlated errors.
_EVALUATOR_PERSONAS = (
    "You are a senior software engineer reviewing code for correctness.",
    "You are a QA engineer testing whether an implementation meets its specification.",
    "You are a systems architect evaluating whether behavioral contracts are satisfied.",
)

_EVALUATION_PROMPT_TEMPLATE = """\
{persona}

You are evaluating a code-generation experiment. A model was given a prompt and \
produced the **Generated Code** below. Your job is to judge whether the generated \
code correctly implements each of 6 behavioral features defined in the \
**Acceptance Criteria**.

## Acceptance Criteria (the rubric)

{acceptance_criteria}

## Gherkin Specification (behavioral scenarios)

{feature_spec}

## Reference Implementation (known-correct, for comparison)

{reference_impl}

## Generated Code (the artifact to evaluate)

{generated_code}

## Instructions

For each of the 6 features below, determine whether the generated code \
correctly implements the feature as described in the acceptance criteria. \
A feature PASSES only if the code handles ALL sub-requirements listed for \
that feature (including edge cases). Partial implementation = FAIL.

Return ONLY a JSON object with this exact structure (no markdown, no commentary):

{{
  "conditional_execution": {{"pass": true/false, "reasoning": "..."}},
  "dependency_handling": {{"pass": true/false, "reasoning": "..."}},
  "retry_logic": {{"pass": true/false, "reasoning": "..."}},
  "timeout_semantics": {{"pass": true/false, "reasoning": "..."}},
  "output_capture": {{"pass": true/false, "reasoning": "..."}},
  "sub_recipe_delegation": {{"pass": true/false, "reasoning": "..."}}
}}
"""


@dataclass
class AgentVote:
    """One evaluator agent's pass/fail verdict per feature."""

    agent_id: str
    persona: str
    features: dict[str, bool]
    reasoning: dict[str, str]
    input_tokens: int
    output_tokens: int
    wall_clock_seconds: float
    parse_failed: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = {
            "agent_id": self.agent_id,
            "persona": self.persona,
            "features": dict(self.features),
            "reasoning": dict(self.reasoning),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "wall_clock_seconds": round(self.wall_clock_seconds, 2),
        }
        if self.parse_failed:
            data["parse_failed"] = True
            data["error"] = self.error
        return data


@dataclass
class ConsensusEvaluation:
    """Consensus result across multiple evaluator agents."""

    metrics: ConditionMetrics
    consensus_scores: dict[str, float]
    agent_votes: list[AgentVote]
    total_input_tokens: int
    total_output_tokens: int
    total_wall_clock_seconds: float
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluation_kind": EVALUATION_KIND,
            "metrics": self.metrics.to_dict(),
            "consensus_scores": {k: round(v, 4) for k, v in self.consensus_scores.items()},
            "agent_votes": [v.to_dict() for v in self.agent_votes],
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_wall_clock_seconds": round(self.total_wall_clock_seconds, 2),
            "notes": list(self.notes),
        }


def _parse_agent_response(text: str) -> dict[str, Any]:
    """Extract JSON from agent response, stripping markdown fences if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Strip ```json ... ``` wrapper
        lines = cleaned.split("\n")
        # Find opening and closing fence
        start = 1 if lines[0].startswith("```") else 0
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        cleaned = "\n".join(lines[start:end]).strip()
    return json.loads(cleaned)


def _extract_vote(raw: dict[str, Any], agent_id: str, persona: str) -> AgentVote:
    """Build an AgentVote from parsed JSON, tolerating minor schema deviations."""
    features: dict[str, bool] = {}
    reasoning: dict[str, str] = {}
    for feat in FEATURES:
        entry = raw.get(feat, {})
        if isinstance(entry, dict):
            features[feat] = bool(entry.get("pass", False))
            reasoning[feat] = str(entry.get("reasoning", ""))
        else:
            # If agent returned a bare bool or something unexpected
            features[feat] = bool(entry)
            reasoning[feat] = ""
    return AgentVote(
        agent_id=agent_id,
        persona=persona,
        features=features,
        reasoning=reasoning,
        input_tokens=0,  # filled in by caller
        output_tokens=0,
        wall_clock_seconds=0.0,
    )


def _has_anthropic_api_key() -> bool:
    """Check if direct Anthropic API access is available."""
    if os.environ.get("ANTHROPIC_DISABLED", "").lower() == "true":
        return False
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


async def _run_single_evaluator_api(
    client: Any,
    model: str,
    agent_id: str,
    persona: str,
    prompt: str,
) -> AgentVote:
    """Run one evaluator agent via direct Anthropic API and return its vote."""
    t0 = time.monotonic()
    response = await client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}],
    )
    elapsed = time.monotonic() - t0

    response_text = ""
    for block in response.content:
        if block.type == "text":
            response_text += block.text

    parse_failed = False
    error_msg = ""
    try:
        parsed = _parse_agent_response(response_text)
    except (json.JSONDecodeError, ValueError) as exc:
        parsed = {}
        parse_failed = True
        error_msg = f"API response JSON parse failed: {exc}"

    vote = _extract_vote(parsed, agent_id, persona)
    vote.input_tokens = response.usage.input_tokens
    vote.output_tokens = response.usage.output_tokens
    vote.wall_clock_seconds = elapsed
    vote.parse_failed = parse_failed
    vote.error = error_msg
    return vote


def _run_single_evaluator_cli(
    agent_id: str,
    persona: str,
    prompt: str,
    work_dir: Path,
) -> AgentVote:
    """Run one evaluator agent via claude CLI subprocess (uses Claude Code auth)."""
    import subprocess

    t0 = time.monotonic()
    workspace_path = work_dir / f"{agent_id}_workspace"
    workspace_path.mkdir(parents=True, exist_ok=True)

    # Build the system prompt incorporating persona
    system_prompt = (
        f"{persona}\n\n"
        "CRITICAL: Return ONLY a JSON object. No markdown, no commentary, no explanation. "
        "Just the raw JSON."
    )

    try:
        result = subprocess.run(
            [
                "claude",
                "--print",
                "--output-format",
                "text",
                "--max-turns",
                "1",
                "--system-prompt",
                system_prompt,
            ],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(workspace_path),
        )
        response_text = result.stdout.strip()
        if result.returncode != 0 and not response_text:
            response_text = result.stderr.strip()
    except subprocess.TimeoutExpired:
        vote = _extract_vote({}, agent_id, persona)
        vote.wall_clock_seconds = time.monotonic() - t0
        vote.parse_failed = True
        vote.error = "CLI subprocess timed out after 300s"
        return vote
    except FileNotFoundError:
        raise RuntimeError(
            "claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
        )

    elapsed = time.monotonic() - t0

    parse_failed = False
    error_msg = ""
    try:
        parsed = _parse_agent_response(response_text)
    except (json.JSONDecodeError, ValueError) as exc:
        parsed = {}
        parse_failed = True
        error_msg = f"CLI response JSON parse failed: {exc}"

    vote = _extract_vote(parsed, agent_id, persona)
    vote.input_tokens = 0  # CLI doesn't report token counts
    vote.output_tokens = 0
    vote.wall_clock_seconds = elapsed
    vote.parse_failed = parse_failed
    vote.error = error_msg
    return vote


async def _evaluate_with_api(
    prompts: list[tuple[str, str, str]],
    model: str,
) -> list[AgentVote]:
    """Run evaluators using direct Anthropic API (parallel async)."""
    import anthropic  # pyright: ignore[reportMissingImports]

    client = anthropic.AsyncAnthropic()
    tasks = [
        _run_single_evaluator_api(client, model, agent_id, persona, prompt)
        for agent_id, persona, prompt in prompts
    ]
    return list(await asyncio.gather(*tasks))


def _evaluate_with_cli(
    prompts: list[tuple[str, str, str]],
    work_dir: Path,
) -> list[AgentVote]:
    """Run evaluators using claude CLI (parallel subprocess, Claude Code auth)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _run_one(args: tuple[str, str, str]) -> AgentVote:
        agent_id, persona, prompt = args
        return _run_single_evaluator_cli(agent_id, persona, prompt, work_dir)

    # Run evaluators in parallel threads (each spawns a claude subprocess)
    votes: list[AgentVote] = [None] * len(prompts)  # type: ignore[list-item]
    with ThreadPoolExecutor(max_workers=len(prompts)) as executor:
        futures = {executor.submit(_run_one, p): i for i, p in enumerate(prompts)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                votes[idx] = future.result()
            except Exception as exc:
                agent_id, persona, _ = prompts[idx]
                failed_vote = _extract_vote({}, agent_id, persona)
                failed_vote.parse_failed = True
                failed_vote.error = f"Evaluator thread failed: {exc}"
                votes[idx] = failed_vote

    return votes


def evaluate_with_consensus(
    generated_code: str,
    acceptance_criteria: str,
    feature_spec: str,
    reference_impl: str,
    *,
    num_agents: int = 3,
    model: str = "claude-sonnet-4-20250514",
    work_dir: Path | None = None,
) -> ConsensusEvaluation:
    """Evaluate generated code using N independent evaluator agents.

    Automatically selects backend:
    - Direct Anthropic API if ANTHROPIC_API_KEY is set (parallel, faster)
    - Goal-seeking runtime otherwise (sequential, uses Claude Code SDK auth)

    Args:
        generated_code: The model-generated artifact to evaluate.
        acceptance_criteria: The acceptance criteria markdown (the rubric).
        feature_spec: The .feature Gherkin specification.
        reference_impl: The reference implementation for comparison.
        num_agents: Number of independent evaluators (default 3).
        model: Model to use for evaluation agents (API backend only).
        work_dir: Working directory for runtime backend (auto-created if None).
    """
    personas = list(_EVALUATOR_PERSONAS)
    while len(personas) < num_agents:
        personas.append(personas[len(personas) % len(_EVALUATOR_PERSONAS)])

    # Build prompts for each evaluator
    evaluator_prompts: list[tuple[str, str, str]] = []
    for i in range(num_agents):
        prompt = _EVALUATION_PROMPT_TEMPLATE.format(
            persona=personas[i],
            acceptance_criteria=acceptance_criteria,
            feature_spec=feature_spec,
            reference_impl=reference_impl,
            generated_code=generated_code,
        )
        evaluator_prompts.append((f"evaluator_{i}", personas[i], prompt))

    t0 = time.monotonic()

    if _has_anthropic_api_key():
        votes = asyncio.run(_evaluate_with_api(evaluator_prompts, model))
    else:
        resolved_work_dir = work_dir or Path(".gherkin_eval_work")
        resolved_work_dir.mkdir(parents=True, exist_ok=True)
        votes = _evaluate_with_cli(evaluator_prompts, resolved_work_dir)

    total_elapsed = time.monotonic() - t0

    # Exclude parse-failed votes from consensus (they're missing data, not FAIL verdicts)
    valid_votes = [v for v in votes if not v.parse_failed]
    failed_votes = [v for v in votes if v.parse_failed]

    notes: list[str] = []
    for v in failed_votes:
        notes.append(f"EXCLUDED {v.agent_id}: {v.error}")

    consensus: dict[str, float] = {}
    if not valid_votes:
        notes.append("ALL evaluator votes failed — scores are 0.0 (no valid data)")
        for feat in FEATURES:
            consensus[feat] = 0.0
    else:
        n_valid = len(valid_votes)
        for feat in FEATURES:
            pass_count = sum(1 for v in valid_votes if v.features.get(feat, False))
            consensus[feat] = pass_count / n_valid
            if pass_count > 0 and pass_count < n_valid:
                notes.append(f"Split vote on {feat}: {pass_count}/{n_valid} PASS")
        if n_valid < num_agents:
            notes.append(f"Consensus based on {n_valid}/{num_agents} valid votes")

    # Map to ConditionMetrics (same 6 slots as before)
    metrics = ConditionMetrics(
        baseline_score=round(consensus["conditional_execution"], 4),
        invariant_compliance=round(consensus["dependency_handling"], 4),
        proof_alignment=round(consensus["retry_logic"], 4),
        local_protocol_alignment=round(consensus["timeout_semantics"], 4),
        progress_signal=round(consensus["output_capture"], 4),
        specification_coverage=round(consensus["sub_recipe_delegation"], 4),
    )

    total_in = sum(v.input_tokens for v in votes)
    total_out = sum(v.output_tokens for v in votes)

    return ConsensusEvaluation(
        metrics=metrics,
        consensus_scores=consensus,
        agent_votes=list(votes),
        total_input_tokens=total_in,
        total_output_tokens=total_out,
        total_wall_clock_seconds=total_elapsed,
        notes=notes,
    )
