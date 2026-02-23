"""Project planning domain tools. Pure functions for task decomposition, dependency analysis, and risk assessment."""

from __future__ import annotations

import re
from typing import Any


def decompose_project(description: str, max_depth: int = 2) -> dict[str, Any]:
    """Decompose a project description into tasks.

    Parses natural language project descriptions and extracts work items.

    Args:
        description: Project description text
        max_depth: Maximum task hierarchy depth

    Returns:
        Dict with tasks list, task_count, estimated_effort
    """
    if not description or not description.strip():
        return {
            "tasks": [],
            "task_count": 0,
            "estimated_effort": "unknown",
        }

    lines = description.strip().split("\n")
    tasks: list[dict[str, Any]] = []
    task_id = 0

    # Extract tasks from bullet points, numbered lists, or action phrases
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check for list items
        list_match = re.match(r"^(?:\d+[.)]\s*|[-*+]\s*|>\s*)(.*)", stripped)
        if list_match:
            task_text = list_match.group(1).strip()
        elif any(word in stripped.lower() for word in ["need to", "should", "must", "will", "create", "build", "implement", "design", "test", "deploy"]):
            task_text = stripped
        else:
            continue

        if not task_text or len(task_text) < 5:
            continue

        task_id += 1

        # Estimate complexity from keywords
        complexity = "medium"
        if any(w in task_text.lower() for w in ["simple", "quick", "update", "fix", "minor"]):
            complexity = "low"
        elif any(w in task_text.lower() for w in ["architecture", "redesign", "migrate", "integrate", "complex"]):
            complexity = "high"

        # Estimate effort
        effort_map = {"low": "1-2 days", "medium": "3-5 days", "high": "1-2 weeks"}

        # Extract owner if mentioned
        owner_match = re.search(r"(?:assigned to|owner:|by)\s+(\w+)", task_text, re.IGNORECASE)
        owner = owner_match.group(1) if owner_match else ""

        tasks.append({
            "id": f"T{task_id:03d}",
            "title": task_text[:200],
            "complexity": complexity,
            "estimated_effort": effort_map[complexity],
            "owner": owner,
            "status": "planned",
        })

    # Estimate total effort
    total_days = sum(
        {"low": 1.5, "medium": 4, "high": 10}.get(t["complexity"], 4)
        for t in tasks
    )
    if total_days <= 5:
        estimated_effort = f"~{total_days:.0f} days"
    elif total_days <= 20:
        estimated_effort = f"~{total_days / 5:.0f} weeks"
    else:
        estimated_effort = f"~{total_days / 20:.0f} months"

    return {
        "tasks": tasks,
        "task_count": len(tasks),
        "estimated_effort": estimated_effort,
        "total_estimated_days": round(total_days, 1),
    }


def analyze_dependencies(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze dependencies between tasks.

    Identifies sequential dependencies, parallel opportunities,
    and critical path elements.

    Args:
        tasks: List of task dicts (from decompose_project)

    Returns:
        Dict with dependencies, critical_path, parallel_groups
    """
    if not tasks:
        return {
            "dependencies": [],
            "critical_path": [],
            "parallel_groups": [],
            "blocking_tasks": [],
        }

    dependencies: list[dict[str, str]] = []
    task_titles = {t["id"]: t.get("title", "").lower() for t in tasks}

    # Heuristic dependency detection based on task content
    design_tasks = [t for t in tasks if any(w in task_titles.get(t["id"], "") for w in ["design", "architecture", "plan", "spec"])]
    impl_tasks = [t for t in tasks if any(w in task_titles.get(t["id"], "") for w in ["implement", "build", "create", "develop", "code"])]
    test_tasks = [t for t in tasks if any(w in task_titles.get(t["id"], "") for w in ["test", "verify", "validate", "qa"])]
    deploy_tasks = [t for t in tasks if any(w in task_titles.get(t["id"], "") for w in ["deploy", "release", "launch", "ship"])]

    # Design before implementation
    for d in design_tasks:
        for i in impl_tasks:
            dependencies.append({
                "from": d["id"],
                "to": i["id"],
                "type": "finish-to-start",
                "reason": "Design must precede implementation",
            })

    # Implementation before testing
    for i in impl_tasks:
        for t in test_tasks:
            dependencies.append({
                "from": i["id"],
                "to": t["id"],
                "type": "finish-to-start",
                "reason": "Implementation must precede testing",
            })

    # Testing before deployment
    for t in test_tasks:
        for d in deploy_tasks:
            dependencies.append({
                "from": t["id"],
                "to": d["id"],
                "type": "finish-to-start",
                "reason": "Testing must precede deployment",
            })

    # Critical path (sequential chain)
    critical_path = []
    if design_tasks:
        critical_path.append(design_tasks[0]["id"])
    if impl_tasks:
        critical_path.append(impl_tasks[0]["id"])
    if test_tasks:
        critical_path.append(test_tasks[0]["id"])
    if deploy_tasks:
        critical_path.append(deploy_tasks[0]["id"])

    # Parallel groups (tasks at same phase)
    parallel_groups = []
    if len(impl_tasks) > 1:
        parallel_groups.append({
            "phase": "implementation",
            "tasks": [t["id"] for t in impl_tasks],
            "can_parallel": True,
        })
    if len(test_tasks) > 1:
        parallel_groups.append({
            "phase": "testing",
            "tasks": [t["id"] for t in test_tasks],
            "can_parallel": True,
        })

    # Blocking tasks (tasks that many others depend on)
    dependency_counts: dict[str, int] = {}
    for dep in dependencies:
        from_id = dep["from"]
        dependency_counts[from_id] = dependency_counts.get(from_id, 0) + 1

    blocking_tasks = [
        {"task_id": tid, "blocks_count": count}
        for tid, count in dependency_counts.items()
        if count >= 2
    ]

    return {
        "dependencies": dependencies,
        "critical_path": critical_path,
        "parallel_groups": parallel_groups,
        "blocking_tasks": blocking_tasks,
        "dependency_count": len(dependencies),
    }


def assess_risks(tasks: list[dict[str, Any]], context: str = "") -> dict[str, Any]:
    """Assess project risks based on tasks and context.

    Identifies technical, schedule, resource, and scope risks.

    Args:
        tasks: List of task dicts
        context: Additional project context

    Returns:
        Dict with risks list, risk_score, mitigation_strategies
    """
    if not tasks:
        return {
            "risks": [{"type": "scope", "severity": "high", "description": "No tasks defined"}],
            "risk_score": 0.0,
            "mitigation_strategies": ["Define project scope and tasks"],
        }

    risks: list[dict[str, Any]] = []
    combined_text = " ".join(t.get("title", "") for t in tasks) + " " + context

    # Technical risks
    if any(w in combined_text.lower() for w in ["migrate", "legacy", "integrate"]):
        risks.append({
            "type": "technical",
            "severity": "high",
            "description": "Integration with legacy systems carries technical risk",
            "likelihood": "medium",
        })
    if any(w in combined_text.lower() for w in ["new technology", "prototype", "experiment"]):
        risks.append({
            "type": "technical",
            "severity": "medium",
            "description": "New technology adoption may require learning curve",
            "likelihood": "medium",
        })

    # Schedule risks
    high_complexity_count = sum(1 for t in tasks if t.get("complexity") == "high")
    if high_complexity_count >= 3:
        risks.append({
            "type": "schedule",
            "severity": "high",
            "description": f"{high_complexity_count} high-complexity tasks increase schedule risk",
            "likelihood": "high",
        })
    elif len(tasks) > 10:
        risks.append({
            "type": "schedule",
            "severity": "medium",
            "description": f"Large number of tasks ({len(tasks)}) may cause estimation errors",
            "likelihood": "medium",
        })

    # Resource risks
    owners = {t.get("owner", "") for t in tasks if t.get("owner")}
    unassigned = sum(1 for t in tasks if not t.get("owner"))
    if unassigned > len(tasks) * 0.5:
        risks.append({
            "type": "resource",
            "severity": "medium",
            "description": f"{unassigned} of {len(tasks)} tasks are unassigned",
            "likelihood": "high",
        })
    if len(owners) == 1 and len(tasks) > 3:
        risks.append({
            "type": "resource",
            "severity": "medium",
            "description": "Single point of failure: all tasks assigned to one person",
            "likelihood": "medium",
        })

    # Scope risks
    if any(w in combined_text.lower() for w in ["tbd", "unclear", "maybe", "possibly"]):
        risks.append({
            "type": "scope",
            "severity": "high",
            "description": "Scope contains uncertain elements",
            "likelihood": "high",
        })

    # If no specific risks found, add a baseline
    if not risks:
        risks.append({
            "type": "general",
            "severity": "low",
            "description": "Standard project execution risk",
            "likelihood": "low",
        })

    # Risk score
    severity_weights = {"high": 3, "medium": 2, "low": 1}
    total_risk = sum(severity_weights.get(r["severity"], 1) for r in risks)
    max_risk = len(risks) * 3
    risk_score = round(total_risk / max(max_risk, 1), 3)

    # Mitigation strategies
    mitigations: list[str] = []
    risk_types = {r["type"] for r in risks}
    if "technical" in risk_types:
        mitigations.append("Create proof-of-concept for high-risk technical components")
    if "schedule" in risk_types:
        mitigations.append("Add buffer time and break complex tasks into smaller deliverables")
    if "resource" in risk_types:
        mitigations.append("Assign clear ownership and identify backup resources")
    if "scope" in risk_types:
        mitigations.append("Clarify uncertain requirements before implementation begins")
    if not mitigations:
        mitigations.append("Monitor project progress regularly")

    return {
        "risks": risks,
        "risk_score": risk_score,
        "risk_count": len(risks),
        "mitigation_strategies": mitigations,
    }


def evaluate_plan(tasks: list[dict[str, Any]], dependencies: dict[str, Any], risks: dict[str, Any]) -> dict[str, Any]:
    """Evaluate overall plan quality.

    Scores the plan across multiple dimensions: completeness, feasibility,
    clarity, and risk management.

    Args:
        tasks: List of task dicts
        dependencies: Output from analyze_dependencies
        risks: Output from assess_risks

    Returns:
        Dict with plan_score, dimension_scores, recommendations
    """
    if not tasks:
        return {
            "plan_score": 0.0,
            "dimension_scores": {},
            "recommendations": ["Create a project plan with defined tasks"],
            "quality_level": "insufficient",
        }

    recommendations: list[str] = []

    # Completeness: are all phases covered?
    task_text = " ".join(t.get("title", "").lower() for t in tasks)
    has_design = any(w in task_text for w in ["design", "architecture", "plan"])
    has_impl = any(w in task_text for w in ["implement", "build", "create", "develop"])
    has_test = any(w in task_text for w in ["test", "verify", "qa"])
    has_deploy = any(w in task_text for w in ["deploy", "release", "launch"])
    phases_covered = sum([has_design, has_impl, has_test, has_deploy])
    completeness = phases_covered / 4

    if not has_design:
        recommendations.append("Add design/architecture phase")
    if not has_test:
        recommendations.append("Add testing phase")
    if not has_deploy:
        recommendations.append("Add deployment/release tasks")

    # Feasibility: reasonable task count and complexity mix
    complexity_counts = {}
    for t in tasks:
        c = t.get("complexity", "medium")
        complexity_counts[c] = complexity_counts.get(c, 0) + 1

    too_many_high = complexity_counts.get("high", 0) > len(tasks) * 0.6
    feasibility = 1.0
    if too_many_high:
        feasibility = 0.6
        recommendations.append("Too many high-complexity tasks - consider breaking down further")
    if len(tasks) > 20:
        feasibility = max(0.5, feasibility - 0.2)
        recommendations.append("Large number of tasks - consider phasing")

    # Clarity: tasks have clear titles and assignments
    assigned = sum(1 for t in tasks if t.get("owner"))
    clarity = 0.5 + 0.5 * (assigned / max(len(tasks), 1))
    if assigned < len(tasks) * 0.5:
        recommendations.append("Assign owners to unassigned tasks")

    # Risk management
    risk_score_raw = risks.get("risk_score", 0.5)
    has_mitigations = len(risks.get("mitigation_strategies", [])) > 0
    risk_management = (1.0 - risk_score_raw) * 0.7 + 0.3 * (1.0 if has_mitigations else 0.0)

    # Overall
    plan_score = (
        0.30 * completeness
        + 0.25 * feasibility
        + 0.20 * clarity
        + 0.25 * risk_management
    )

    if plan_score >= 0.8:
        quality_level = "excellent"
    elif plan_score >= 0.6:
        quality_level = "good"
    elif plan_score >= 0.4:
        quality_level = "fair"
    else:
        quality_level = "needs_improvement"

    if not recommendations:
        recommendations.append("Plan appears well-structured")

    return {
        "plan_score": round(plan_score, 3),
        "dimension_scores": {
            "completeness": round(completeness, 3),
            "feasibility": round(feasibility, 3),
            "clarity": round(clarity, 3),
            "risk_management": round(risk_management, 3),
        },
        "recommendations": recommendations,
        "quality_level": quality_level,
        "task_count": len(tasks),
        "phases_covered": phases_covered,
    }
