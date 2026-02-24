# Session-to-Agent: Reference

Complete technical reference for the session-to-agent skill. Covers the
extraction algorithm, prompt template, memory export, CLI integration, and
configuration options.

## 1. Extraction Algorithm

The skill follows a five-stage pipeline to convert a session transcript into a
goal-seeking agent.

### Stage 1: Locate Session Transcript

Session transcripts are stored as JSONL files under the Claude projects
directory. The skill finds the current or most recent session file.

```python
from pathlib import Path
import json

def find_session_transcript(project_dir: str | None = None) -> Path | None:
    """Find the most recent session JSONL file for this project.

    Claude Code stores session transcripts as JSONL files in:
      ~/.claude/projects/<project-slug>/<session-id>.jsonl

    The project slug is derived from the working directory path with
    slashes replaced by dashes.
    """
    if project_dir is None:
        # Derive from cwd
        cwd = Path.cwd().resolve()
        slug = str(cwd).replace("/", "-").lstrip("-")
        project_dir = Path.home() / ".claude" / "projects" / slug

    project_path = Path(project_dir)
    if not project_path.exists():
        return None

    jsonl_files = sorted(
        project_path.glob("*.jsonl"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return jsonl_files[0] if jsonl_files else None


def parse_transcript(path: Path) -> list[dict]:
    """Parse a session JSONL file into a list of message entries."""
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries
```

### Stage 2: Extract Session Context

From the parsed transcript, extract structured information about the session's
goals, constraints, tools, and patterns.

```python
EXTRACTION_PROMPT = """
Analyze this session transcript and extract structured information for
generating a reusable goal-seeking agent.

Return a JSON object with these fields:

{
  "primary_goal": "One sentence describing the main objective",
  "sub_goals": ["List of specific sub-tasks accomplished or attempted"],
  "constraints": ["Technical, operational, or time constraints observed"],
  "tools_used": ["CLI tools, APIs, libraries, and Claude Code tools used"],
  "patterns_observed": ["Strategies, approaches, and problem-solving patterns"],
  "domain_knowledge": ["Domain-specific facts and insights gained"],
  "success_criteria": ["How success was measured or should be measured"],
  "failure_modes": ["What went wrong and how it was recovered"],
  "estimated_complexity": "simple | moderate | complex",
  "suggested_agent_name": "kebab-case name for the agent"
}

IMPORTANT:
- Focus on REPEATABLE aspects of the workflow
- Omit session-specific details (specific file paths, temp values)
- Generalize constraints where possible
- Include both explicit and implicit goals

Transcript (last 5000 characters):
{transcript_tail}
"""


def extract_session_context(entries: list[dict]) -> dict:
    """Extract structured context from transcript entries.

    This function builds a text representation of the session and
    uses the extraction prompt above to produce structured output.
    In practice, Claude Code itself performs this extraction as part
    of skill execution -- the prompt is provided here as reference.
    """
    # Build text from human and assistant messages
    text_parts = []
    for entry in entries:
        role = entry.get("role", "")
        content = entry.get("content", "")
        if isinstance(content, list):
            # Handle content blocks (text, tool_use, tool_result)
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(f"[{role}] {block['text']}")
        elif isinstance(content, str):
            text_parts.append(f"[{role}] {content}")

    transcript_text = "\n".join(text_parts)

    # Take the last ~5000 chars to stay within token limits
    transcript_tail = transcript_text[-5000:]

    # In actual execution, Claude reads the transcript and applies
    # the extraction prompt internally. The result is a dict matching
    # the schema above.
    return {
        "transcript_tail": transcript_tail,
        "prompt": EXTRACTION_PROMPT.format(transcript_tail=transcript_tail),
    }
```

### Stage 3: Generate Prompt File

Transform the extracted context into a `prompt.md` file suitable for
`amplihack new --file`.

```python
PROMPT_TEMPLATE = """# Goal: {primary_goal}

## Objective

{primary_goal}

### Sub-Goals

{sub_goals_md}

## Success Criteria

{success_criteria_md}

## Constraints

{constraints_md}

## Domain Knowledge

{domain_knowledge_md}

## Patterns and Strategies

{patterns_md}

## Tools and Capabilities Required

{tools_md}

## Failure Modes and Recovery

{failure_modes_md}
"""


def generate_prompt_file(context: dict, output_path: Path) -> Path:
    """Generate a prompt.md file from extracted session context.

    Args:
        context: Structured extraction result (see Stage 2 schema).
        output_path: Where to write the prompt file.

    Returns:
        Path to the generated prompt.md file.
    """
    def to_md_list(items: list[str]) -> str:
        if not items:
            return "- None identified\n"
        return "\n".join(f"- {item}" for item in items) + "\n"

    content = PROMPT_TEMPLATE.format(
        primary_goal=context.get("primary_goal", "Unnamed goal"),
        sub_goals_md=to_md_list(context.get("sub_goals", [])),
        success_criteria_md=to_md_list(context.get("success_criteria", [])),
        constraints_md=to_md_list(context.get("constraints", [])),
        domain_knowledge_md=to_md_list(context.get("domain_knowledge", [])),
        patterns_md=to_md_list(context.get("patterns_observed", [])),
        tools_md=to_md_list(context.get("tools_used", [])),
        failure_modes_md=to_md_list(context.get("failure_modes", [])),
    )

    output_path.write_text(content)
    return output_path
```

### Stage 4: Run Agent Generator

Invoke the `amplihack new` CLI to create the goal-seeking agent.

```bash
amplihack new \
  --file /tmp/session-agent-prompt.md \
  --name "${suggested_agent_name}" \
  --sdk copilot \
  --enable-memory \
  --output ./goal_agents/${suggested_agent_name}
```

The CLI pipeline:

1. `PromptAnalyzer` -- parses the prompt.md into a `GoalDefinition`
2. `ObjectivePlanner` -- generates a multi-phase `ExecutionPlan`
3. `SkillSynthesizer` -- maps capabilities to skills and SDK tools
4. `AgentAssembler` -- creates a `GoalAgentBundle`
5. `GoalAgentPackager` -- writes the agent directory

### Stage 5: Memory Export (Optional)

When `--enable-memory` is set, the skill offers to export the current
session's Kuzu memory database as the agent's initial knowledge base.

```python
import shutil
from pathlib import Path


def export_memory_to_agent(
    agent_dir: Path,
    kuzu_db_path: Path | None = None,
) -> bool:
    """Copy the current Kuzu DB into the agent's data directory.

    Args:
        agent_dir: Root directory of the generated agent.
        kuzu_db_path: Path to the Kuzu database directory.
            Defaults to .amplihack/kuzu_db in the project root.

    Returns:
        True if export succeeded, False otherwise.
    """
    if kuzu_db_path is None:
        # Default location in amplihack projects
        kuzu_db_path = Path(".amplihack") / "kuzu_db"

    if not kuzu_db_path.exists():
        return False

    dest = agent_dir / "data" / "initial_memory"
    dest.mkdir(parents=True, exist_ok=True)

    try:
        shutil.copytree(kuzu_db_path, dest / "kuzu_db", dirs_exist_ok=True)
        return True
    except Exception:
        return False
```

## 2. Configuration Options

| Option              | Default         | Description                                             |
| ------------------- | --------------- | ------------------------------------------------------- |
| `--sdk`             | `copilot`       | Target SDK: copilot, claude, microsoft, mini            |
| `--enable-memory`   | `false`         | Enable Kuzu memory backend for the agent                |
| `--multi-agent`     | `false`         | Generate coordinator + sub-agent architecture           |
| `--enable-spawning` | `false`         | Allow dynamic sub-agent spawning (requires multi-agent) |
| `--name`            | auto            | Custom agent name (kebab-case)                          |
| `--output`          | `./goal_agents` | Output directory for the generated agent                |
| `--verbose`         | `false`         | Show detailed generation logs                           |

## 3. Integration Points

### With goal-seeking-agent-pattern Skill

The session-to-agent skill produces agents that follow the goal-seeking agent
pattern. The extracted goals map to `GoalDefinition`, execution phases map to
`ExecutionPlan`, and tools map to `SkillDefinition` objects.

### With knowledge-extractor Skill

Before generating the agent, the skill can invoke the knowledge-extractor to
capture discoveries and patterns from the session. These feed into the agent's
initial memory when `--enable-memory` is used.

### With session-learning Skill

Session learnings (from `~/.amplihack/.claude/data/learnings/`) can be
injected into the generated agent's prompt as domain knowledge, ensuring
cross-session insights are preserved.

### With self-improving-agent-builder Skill

After generating the agent, the self-improving-agent-builder can run eval
loops to measure and improve the agent's performance over time.

## 4. Session Transcript Format

Claude Code stores session transcripts as JSONL files. Each line is a JSON
object representing a message or event:

```json
{"type": "human", "role": "user", "content": "Add JWT auth to the API"}
{"type": "assistant", "role": "assistant", "content": [{"type": "text", "text": "I'll implement..."}]}
{"type": "assistant", "role": "assistant", "content": [{"type": "tool_use", "name": "Read", ...}]}
{"type": "tool_result", "content": "file contents..."}
```

The extraction algorithm processes both text content and tool usage to
understand the full scope of the session's work.

## 5. Error Handling

| Scenario                           | Handling                                          |
| ---------------------------------- | ------------------------------------------------- |
| No session transcript found        | Report error, suggest running from active session |
| Transcript too short (<10 entries) | Warn that extraction may be incomplete            |
| `amplihack new` fails              | Show error, preserve prompt.md for manual retry   |
| Kuzu DB not found                  | Skip memory export, agent works without it        |
| Extraction returns empty goals     | Prompt user for manual goal description           |

## 6. Output Structure

After successful generation, the agent directory contains:

```
goal_agents/<agent-name>/
  agent.md           # Agent definition with goal and phases
  prompt.md          # The goal prompt (editable for re-generation)
  main.py            # Entry point for running the agent
  plan.yaml          # Multi-phase execution plan
  skills.yaml        # Required skills and tool mappings
  metadata.json      # SDK, memory, and configuration metadata
  data/
    initial_memory/  # (Optional) Exported Kuzu DB snapshot
      kuzu_db/
```
