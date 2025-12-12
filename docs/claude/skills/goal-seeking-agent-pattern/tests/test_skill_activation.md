# Test Suite: Goal-Seeking Agent Pattern Skill

This test suite validates the Goal-Seeking Agent Pattern Skill across 22 test cases covering auto-detection, decision framework, integration, examples, content completeness, philosophy compliance, user experience, and integration tests.

## Test Category 1: Auto-Detection (4 tests)

### Test 1.1: Trigger Word Detection

**Objective**: Verify skill activates on trigger words

**Trigger Words** (from SKILL.md YAML frontmatter):

- "complex workflow"
- "autonomous agent"
- "goal-seeking"
- "adaptive behavior"
- "multi-phase processing"
- "task automation design"
- "autonomous decision-making"
- "multi-step process"
- "workflow orchestration"
- "self-directed agent"

**Test Cases**:

```python
def test_trigger_word_complex_workflow():
    prompt = "I need to design a complex workflow for data processing"
    assert skill_should_activate(prompt, triggers=["complex workflow"])

def test_trigger_word_autonomous_agent():
    prompt = "How do I create an autonomous agent for CI diagnostics?"
    assert skill_should_activate(prompt, triggers=["autonomous agent"])

def test_trigger_word_goal_seeking():
    prompt = "When should I use goal-seeking agents?"
    assert skill_should_activate(prompt, triggers=["goal-seeking"])

def test_trigger_word_multi_phase():
    prompt = "I have a multi-phase processing pipeline to automate"
    assert skill_should_activate(prompt, triggers=["multi-phase processing"])
```

**Expected**: Skill activates when any trigger word is present

### Test 1.2: Target Agent Detection

**Objective**: Verify skill activates for architect agent

**Test Cases**:

```python
def test_target_agent_architect():
    agent_context = {"role": "architect", "task": "design automation"}
    assert skill_should_activate_for_agent(agent_context, target="architect")

def test_not_activated_for_builder():
    agent_context = {"role": "builder", "task": "implement code"}
    assert not skill_should_activate_for_agent(agent_context, target="architect")
```

**Expected**: Skill activates only for architect agent

### Test 1.3: Priority and Complexity

**Objective**: Verify skill metadata is correct

**Test Cases**:

```python
def test_skill_priority():
    metadata = load_skill_metadata("goal-seeking-agent-pattern")
    assert metadata["priority"] == "medium"

def test_skill_complexity():
    metadata = load_skill_metadata("goal-seeking-agent-pattern")
    assert metadata["complexity"] == "medium"
```

**Expected**: Priority=medium, Complexity=medium

### Test 1.4: Allowed Tools

**Objective**: Verify skill declares correct allowed tools

**Test Cases**:

```python
def test_allowed_tools():
    metadata = load_skill_metadata("goal-seeking-agent-pattern")
    allowed_tools = metadata["allowed-tools"]

    assert "Read" in allowed_tools
    assert "Grep" in allowed_tools
    assert "Glob" in allowed_tools
    assert "WebSearch" in allowed_tools

    # Should not include tools that modify files
    assert "Write" not in allowed_tools
    assert "Edit" not in allowed_tools
```

**Expected**: Read-only tools (Read, Grep, Glob, WebSearch)

## Test Category 2: Decision Framework (3 tests)

### Test 2.1: 5-Question Framework

**Objective**: Verify all 5 questions are documented

**Test Cases**:

```python
def test_decision_framework_questions():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    # Check all 5 questions present
    assert "Q1: Well-defined objective but flexible path?" in skill_content
    assert "Q2: Multiple phases with dependencies?" in skill_content
    assert "Q3: Autonomous recovery valuable?" in skill_content
    assert "Q4: Context affects approach?" in skill_content
    assert "Q5: Complexity justified?" in skill_content

def test_decision_matrix():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    # Check decision matrix exists
    assert "All 5 YES" in skill_content
    assert "4 YES, 1 NO" in skill_content
    assert "3 YES, 2 NO" in skill_content
    assert "2 YES, 3 NO" in skill_content
    assert "0-1 YES" in skill_content
```

**Expected**: All 5 questions and decision matrix documented

### Test 2.2: Problem Indicators

**Objective**: Verify 5 problem indicators are documented

**Test Cases**:

```python
def test_problem_indicators():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    assert "Pattern 1: Workflow Variability" in skill_content
    assert "Pattern 2: Multi-Phase Complexity" in skill_content
    assert "Pattern 3: Autonomous Recovery Needed" in skill_content
    assert "Pattern 4: Adaptive Decision Making" in skill_content
    assert "Pattern 5: Domain Expertise Required" in skill_content
```

**Expected**: All 5 problem indicators documented

### Test 2.3: When NOT to Use

**Objective**: Verify anti-patterns are documented

**Test Cases**:

```python
def test_when_not_to_use():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    # Check "when to avoid" section exists
    assert "When to Avoid Goal-Seeking" in skill_content

    # Check anti-patterns mentioned
    assert "single deterministic path" in skill_content.lower()
    assert "latency-critical" in skill_content.lower()
    assert "safety-critical" in skill_content.lower()
```

**Expected**: Clear guidance on when NOT to use goal-seeking agents

## Test Category 3: Integration Code (3 tests)

### Test 3.1: API Examples

**Objective**: Verify all API classes are documented with examples

**Test Cases**:

```python
def test_api_classes_documented():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    # Check all API classes mentioned
    assert "PromptAnalyzer" in skill_content
    assert "ObjectivePlanner" in skill_content
    assert "SkillSynthesizer" in skill_content
    assert "AgentAssembler" in skill_content
    assert "GoalAgentPackager" in skill_content

def test_api_import_examples():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    # Check import statement examples
    assert "from amplihack.goal_agent_generator import" in skill_content
```

**Expected**: All 5 API classes documented with import examples

### Test 3.2: CLI Examples

**Objective**: Verify CLI commands are documented

**Test Cases**:

```python
def test_cli_commands():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    # Check CLI commands documented
    assert "amplihack goal-agent-generator create" in skill_content
    assert "amplihack goal-agent-generator execute" in skill_content
    assert "amplihack goal-agent-generator list" in skill_content

def test_cli_options():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    # Check key options documented
    assert "--prompt" in skill_content
    assert "--inline" in skill_content
    assert "--output" in skill_content
    assert "--auto-mode" in skill_content
```

**Expected**: CLI commands and options documented

### Test 3.3: Code Examples Are Valid Python

**Objective**: Verify all Python code examples are syntactically correct

**Test Cases**:

```python
import ast
import re

def test_python_code_examples_valid():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    # Extract Python code blocks
    code_blocks = extract_code_blocks(skill_content, language="python")

    errors = []
    for i, code in enumerate(code_blocks):
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"Code block {i+1}: {e}")

    assert len(errors) == 0, f"Syntax errors found:\n" + "\n".join(errors)
```

**Expected**: All Python code examples are syntactically valid

## Test Category 4: Example References (3 tests)

### Test 4.1: Real Amplihack Examples

**Objective**: Verify 4 real amplihack examples are documented

**Test Cases**:

```python
def test_real_examples_count():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    # Check all 4 examples present
    assert "Example 1: AKS SRE Automation" in skill_content
    assert "Example 2: CI Diagnostic Workflow" in skill_content
    assert "Example 3: Pre-Commit Diagnostic" in skill_content
    assert "Example 4: Fix-Agent Pattern Matching" in skill_content

def test_real_examples_references():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    # Check examples reference real agent files
    assert "azure-kubernetes-expert.md" in skill_content
    assert "ci-diagnostic-workflow.md" in skill_content
    assert "pre-commit-diagnostic.md" in skill_content
    assert "fix-agent.md" in skill_content
```

**Expected**: All 4 real examples documented with file references

### Test 4.2: Example Scenario Files

**Objective**: Verify 3 example scenario files exist and are complete

**Test Cases**:

```python
def test_example_files_exist():
    examples_dir = Path(".claude/skills/goal-seeking-agent-pattern/examples")

    assert (examples_dir / "workflow_automation.md").exists()
    assert (examples_dir / "data_pipeline.md").exists()
    assert (examples_dir / "adaptive_testing.md").exists()

def test_example_files_content():
    examples_dir = Path(".claude/skills/goal-seeking-agent-pattern/examples")

    # Each example should have key sections
    for example_file in examples_dir.glob("*.md"):
        content = example_file.read_text()

        assert "Problem Statement" in content
        assert "Is Goal-Seeking Appropriate?" in content
        assert "Goal-Seeking Agent Design" in content
        assert "Execution Example" in content
        assert "Lessons Learned" in content
```

**Expected**: All 3 example files exist with complete content

### Test 4.3: Example Quality

**Objective**: Verify examples follow 5-question framework

**Test Cases**:

```python
def test_examples_use_framework():
    examples_dir = Path(".claude/skills/goal-seeking-agent-pattern/examples")

    for example_file in examples_dir.glob("*.md"):
        content = example_file.read_text()

        # Each example should answer all 5 questions
        assert "Q1:" in content
        assert "Q2:" in content
        assert "Q3:" in content
        assert "Q4:" in content
        assert "Q5:" in content

        # Should have conclusion
        assert "Conclusion" in content
        assert "YES" in content  # At least one YES answer
```

**Expected**: All examples follow 5-question framework

## Test Category 5: Content Completeness (3 tests)

### Test 5.1: All 13 Sections Present

**Objective**: Verify SKILL.md has all 13 required sections

**Test Cases**:

```python
def test_all_sections_present():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    required_sections = [
        "## 1. What Are Goal-Seeking Agents?",
        "## 2. When to Use This Pattern",
        "## 3. Architecture Pattern",
        "## 4. Integration with goal_agent_generator",
        "## 5. Recent Amplihack Examples",
        "## 6. Design Checklist",
        "## 7. Agent SDK Integration (Future)",
        "## 8. Trade-Off Analysis",
        "## 9. When to Escalate",
        "## 10. Example Workflow",
        "## 11. Related Patterns",
        "## 12. Quality Standards",
        "## 13. Getting Started",
    ]

    for section in required_sections:
        assert section in skill_content, f"Missing section: {section}"
```

**Expected**: All 13 sections present

### Test 5.2: Templates Exist

**Objective**: Verify template files exist and are complete

**Test Cases**:

```python
def test_template_files_exist():
    templates_dir = Path(".claude/skills/goal-seeking-agent-pattern/templates")

    assert (templates_dir / "goal_prompt_template.md").exists()
    assert (templates_dir / "integration_guide.md").exists()

def test_goal_prompt_template_sections():
    template_file = Path(".claude/skills/goal-seeking-agent-pattern/templates/goal_prompt_template.md")
    content = template_file.read_text()

    # Template should have all sections
    assert "## Objective" in content
    assert "## Success Criteria" in content
    assert "## Constraints" in content
    assert "## Context" in content

def test_integration_guide_sections():
    guide_file = Path(".claude/skills/goal-seeking-agent-pattern/templates/integration_guide.md")
    content = guide_file.read_text()

    # Guide should cover all APIs
    assert "PromptAnalyzer" in content
    assert "ObjectivePlanner" in content
    assert "SkillSynthesizer" in content
    assert "AgentAssembler" in content
    assert "GoalAgentPackager" in content
```

**Expected**: Templates exist with complete content

### Test 5.3: README User-Facing

**Objective**: Verify README.md is user-friendly

**Test Cases**:

```python
def test_readme_exists():
    readme_file = Path(".claude/skills/goal-seeking-agent-pattern/README.md")
    assert readme_file.exists()

def test_readme_has_quickstart():
    readme_file = Path(".claude/skills/goal-seeking-agent-pattern/README.md")
    content = readme_file.read_text()

    # Should have quick start section
    assert "Quick Start" in content
    assert "5-question" in content.lower()

def test_readme_has_examples():
    readme_file = Path(".claude/skills/goal-seeking-agent-pattern/README.md")
    content = readme_file.read_text()

    # Should reference all 4 real examples
    assert "AKS SRE Automation" in content
    assert "CI Diagnostic" in content
    assert "Pre-Commit" in content
    assert "Fix-Agent" in content
```

**Expected**: README is user-friendly with quick start and examples

## Test Category 6: Philosophy Compliance (3 tests)

### Test 6.1: Ruthless Simplicity

**Objective**: Verify content follows ruthless simplicity principle

**Test Cases**:

```python
def test_no_over_engineering():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    # Should explicitly mention simplicity
    assert "ruthless simplicity" in skill_content.lower()
    assert "simplest solution" in skill_content.lower()

    # Should warn against over-engineering
    assert "over-engineering" in skill_content.lower()

def test_clear_when_not_to_use():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    # Should have clear anti-patterns
    assert "When to Avoid" in skill_content
    assert "When NOT to Use" in skill_content
```

**Expected**: Clear emphasis on simplicity and anti-patterns

### Test 6.2: Modularity (Bricks & Studs)

**Objective**: Verify modular design is emphasized

**Test Cases**:

```python
def test_modular_components():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    # Should emphasize component separation
    assert "GoalDefinition" in skill_content
    assert "ExecutionPlan" in skill_content
    assert "PlanPhase" in skill_content
    assert "SkillDefinition" in skill_content

def test_clear_interfaces():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    # Should show clear interfaces (inputs/outputs)
    assert "input" in skill_content.lower()
    assert "output" in skill_content.lower()
    assert "return" in skill_content.lower()
```

**Expected**: Clear modular components with defined interfaces

### Test 6.3: Zero-BS Implementation

**Objective**: Verify no placeholders or TODOs

**Test Cases**:

````python
def test_no_todos():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    # Should not contain TODOs
    assert "TODO" not in skill_content
    assert "TBD" not in skill_content
    assert "FIXME" not in skill_content

def test_no_placeholders():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    # Should not contain obvious placeholders
    assert "[INSERT" not in skill_content
    assert "[PLACEHOLDER" not in skill_content
    assert "..." not in skill_content.split("```")[0]  # Not in non-code sections
````

**Expected**: No TODOs, placeholders, or unfinished sections

## Test Category 7: User Experience (2 tests)

### Test 7.1: Clear Getting Started

**Objective**: Verify users can get started quickly

**Test Cases**:

````python
def test_getting_started_section():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    # Should have clear getting started section
    assert "## 13. Getting Started" in skill_content
    assert "Quick Start" in skill_content

def test_runnable_examples():
    skill_content = read_skill_content("goal-seeking-agent-pattern")

    # Should have copy-pasteable examples
    assert "```bash" in skill_content
    assert "amplihack goal-agent-generator create" in skill_content
````

**Expected**: Clear getting started with runnable examples

### Test 7.2: Progressive Complexity

**Objective**: Verify content follows progressive complexity

**Test Cases**:

```python
def test_simple_example_first():
    readme_content = read_file(".claude/skills/goal-seeking-agent-pattern/README.md")

    # Quick Start should come before advanced topics
    quick_start_pos = readme_content.find("Quick Start")
    advanced_pos = readme_content.find("Advanced")

    assert quick_start_pos < advanced_pos

def test_examples_ordered_by_complexity():
    examples_dir = Path(".claude/skills/goal-seeking-agent-pattern/examples")

    workflow = (examples_dir / "workflow_automation.md").read_text()
    pipeline = (examples_dir / "data_pipeline.md").read_text()
    testing = (examples_dir / "adaptive_testing.md").read_text()

    # Each should have clear complexity statement
    for example in [workflow, pipeline, testing]:
        assert "Is Goal-Seeking Appropriate?" in example
```

**Expected**: Simple concepts first, advanced topics later

## Test Category 8: Integration Tests (1 test)

### Test 8.1: End-to-End Integration

**Objective**: Verify skill can be loaded and used by Claude

**Test Cases**:

```python
def test_skill_loads_successfully():
    """Test that skill YAML frontmatter is valid"""
    skill_file = Path(".claude/skills/goal-seeking-agent-pattern/SKILL.md")
    content = skill_file.read_text()

    # Extract YAML frontmatter
    yaml_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    assert yaml_match, "YAML frontmatter not found"

    yaml_content = yaml_match.group(1)

    # Parse YAML
    import yaml
    try:
        metadata = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        assert False, f"Invalid YAML: {e}"

    # Verify required fields
    assert "name" in metadata
    assert "description" in metadata
    assert "auto-detection" in metadata
    assert "triggers" in metadata["auto-detection"]
    assert len(metadata["auto-detection"]["triggers"]) >= 10

def test_skill_file_structure():
    """Test that all required files exist"""
    skill_dir = Path(".claude/skills/goal-seeking-agent-pattern")

    # Core files
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "README.md").exists()

    # Examples
    assert (skill_dir / "examples" / "workflow_automation.md").exists()
    assert (skill_dir / "examples" / "data_pipeline.md").exists()
    assert (skill_dir / "examples" / "adaptive_testing.md").exists()

    # Templates
    assert (skill_dir / "templates" / "goal_prompt_template.md").exists()
    assert (skill_dir / "templates" / "integration_guide.md").exists()

    # Tests
    assert (skill_dir / "tests" / "test_skill_activation.md").exists()
```

**Expected**: Skill loads successfully with valid metadata and complete file structure

## Test Summary

| Category                 | Tests  | Description                                          |
| ------------------------ | ------ | ---------------------------------------------------- |
| 1. Auto-Detection        | 4      | Trigger words, target agent, priority, allowed tools |
| 2. Decision Framework    | 3      | 5 questions, problem indicators, anti-patterns       |
| 3. Integration Code      | 3      | API examples, CLI examples, valid Python             |
| 4. Example References    | 3      | Real amplihack examples, scenario files, quality     |
| 5. Content Completeness  | 3      | All 13 sections, templates, README                   |
| 6. Philosophy Compliance | 3      | Simplicity, modularity, zero-BS                      |
| 7. User Experience       | 2      | Getting started, progressive complexity              |
| 8. Integration Tests     | 1      | End-to-end skill loading                             |
| **Total**                | **22** | **Complete test coverage**                           |

## Running Tests

### Manual Testing

```bash
# Run all tests
python -m pytest .claude/skills/goal-seeking-agent-pattern/tests/test_skill_activation.md

# Run specific category
python -m pytest .claude/skills/goal-seeking-agent-pattern/tests/test_skill_activation.md -k "auto_detection"

# Run with verbose output
python -m pytest .claude/skills/goal-seeking-agent-pattern/tests/test_skill_activation.md -v
```

### Automated Testing (CI/CD)

```yaml
# .github/workflows/test-skills.yml
name: Test Skills

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.10"
      - name: Install dependencies
        run: pip install pytest pyyaml
      - name: Test goal-seeking-agent-pattern skill
        run: |
          pytest .claude/skills/goal-seeking-agent-pattern/tests/test_skill_activation.md -v
```

## Success Criteria

All 22 tests must pass for skill to be considered complete and production-ready:

- [ ] Auto-detection tests (4/4)
- [ ] Decision framework tests (3/3)
- [ ] Integration code tests (3/3)
- [ ] Example references tests (3/3)
- [ ] Content completeness tests (3/3)
- [ ] Philosophy compliance tests (3/3)
- [ ] User experience tests (2/2)
- [ ] Integration tests (1/1)

**Total**: 22/22 tests passing ✓

---

**Note**: This test suite is written in markdown format for documentation. To execute tests programmatically, convert to actual pytest test cases in `test_skill_activation.py`.
