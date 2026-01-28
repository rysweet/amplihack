"""Registry of all amplihack-managed skills.

This module provides a single source of truth for skills managed by amplihack.
Used by staging_safety.py to determine if a skill directory is safe to delete.

IMPORTANT: This registry is generated from the actual filesystem at
~/.amplihack/.claude/skills/ to ensure it matches reality.
"""

# All amplihack-managed skills (directory names)
# Generated from ~/.amplihack/.claude/skills/ filesystem contents
AMPLIHACK_SKILLS: frozenset[str] = frozenset(
    [
        "agent-sdk",
        "anthropologist-analyst",
        "azure-admin",
        "azure-devops",
        "azure-devops-cli",
        "backlog-curator",
        "biologist-analyst",
        "cascade-workflow",
        "chemist-analyst",
        "code-smell-detector",
        "code-visualizer",
        "collaboration",
        "common",
        "computer-scientist-analyst",
        "consensus-voting",
        "context-management",
        "cybersecurity-analyst",
        "debate-workflow",
        "default-workflow",
        "dependency-resolver",
        "design-patterns-expert",
        "development",
        "documentation-writing",
        "docx",
        "dotnet-install",
        "dotnet10-pack-tool",
        "dynamic-debugger",
        "economist-analyst",
        "email-drafter",
        "engineer-analyst",
        "environmentalist-analyst",
        "epidemiologist-analyst",
        "ethicist-analyst",
        "eval-recipes-runner",
        "futurist-analyst",
        "github",
        "github-copilot-cli-expert",
        "github-copilot-sdk",
        "goal-seeking-agent-pattern",
        "historian-analyst",
        "indigenous-leader-analyst",
        "investigation-workflow",
        "journalist-analyst",
        "knowledge-extractor",
        "lawyer-analyst",
        "learning-path-builder",
        "lsp-setup",
        "mcp-manager",
        "meeting-synthesizer",
        "mermaid-diagram-generator",
        "meta-cognitive",
        "microsoft-agent-framework",
        "model-evaluation-benchmark",
        "module-spec-generator",
        "multi-repo",
        "n-version-workflow",
        "novelist-analyst",
        "outside-in-testing",
        "pdf",
        "philosopher-analyst",
        "philosophy-compliance-workflow",
        "physicist-analyst",
        "pm-architect",
        "poet-analyst",
        "political-scientist-analyst",
        "pptx",
        "pr-review-assistant",
        "psychologist-analyst",
        "quality",
        "quality-audit-workflow",
        "remote-work",
        "research",
        "roadmap-strategist",
        "session-learning",
        "session-replay",
        "skill-builder",
        "smart-test",
        "sociologist-analyst",
        "socratic-review",
        "storytelling-synthesizer",
        "test-gap-analyzer",
        "ultrathink-orchestrator",
        "urban-planner-analyst",
        "work-delegator",
        "work-iq",
        "workflow-enforcement",
        "workstream-coordinator",
        "xlsx",
    ]
)


def is_amplihack_skill(skill_name: str) -> bool:
    """Check if skill name is managed by amplihack.

    Args:
        skill_name: Directory name of skill (e.g., "agent-sdk")

    Returns:
        True if skill is in amplihack registry (O(1) lookup)
    """
    return skill_name in AMPLIHACK_SKILLS
