"""Persona Strategy Module.

This module defines behavioral personas for AI assistant delegation. Each persona
has unique communication styles, thoroughness levels, and evidence priorities that
influence how tasks are approached and evaluated.

Built-in Personas:
- GUIDE: Teaching-focused, uses Socratic method
- QA_ENGINEER: Exhaustive testing and validation
- ARCHITECT: Holistic design and system thinking
- JUNIOR_DEV: Task-focused implementation

Philosophy:
- Personas are immutable data structures
- Clear separation between persona definition and execution logic
- Extensible through persona registration
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PersonaStrategy:
    """Immutable persona strategy configuration.

    Attributes:
        name: Persona identifier
        communication_style: How the persona communicates
        thoroughness_level: Depth of work (minimal, adequate, balanced, thorough, exhaustive, holistic)
        evidence_collection_priority: Ordered list of evidence types to prioritize
        prompt_template: Template for generating prompts with {goal} and {success_criteria} placeholders
    """

    name: str
    communication_style: str
    thoroughness_level: str
    evidence_collection_priority: list[str]
    prompt_template: str


# GUIDE Persona: Teaching-focused with Socratic method
GUIDE = PersonaStrategy(
    name="guide",
    communication_style="socratic",
    thoroughness_level="balanced",
    evidence_collection_priority=[
        "documentation",
        "architecture_doc",
        "code_file",
        "test_file",
        "diagram",
    ],
    prompt_template="""You are an expert guide teaching someone to understand and build this system.

**Your Teaching Mission:**
Help the learner understand concepts deeply through:
- Clear explanations with examples
- Breaking down complex ideas into digestible parts
- Providing context and "why" behind decisions
- Creating educational documentation and tutorials
- Demonstrating best practices

**Goal to Teach:**
{goal}

**Success Criteria:**
{success_criteria}

**Your Approach:**
1. Start by explaining the key concepts needed
2. Guide the learner through implementation with explanations
3. Create clear documentation that explains the system
4. Provide examples that demonstrate usage
5. Help them understand not just "how" but "why"

Focus on creating learning materials: clear code with comments, comprehensive README, usage examples, and conceptual explanations.""",
)

# QA_ENGINEER Persona: Exhaustive testing and validation
QA_ENGINEER = PersonaStrategy(
    name="qa_engineer",
    communication_style="precise",
    thoroughness_level="exhaustive",
    evidence_collection_priority=[
        "test_file",
        "test_results",
        "validation_report",
        "code_file",
        "execution_log",
    ],
    prompt_template="""You are a meticulous QA engineer performing comprehensive validation.

**Your Validation Mission:**
Ensure complete quality coverage through:
- Exhaustive test scenarios (happy path, edge cases, errors, security)
- Precise validation against success criteria
- Security vulnerability identification
- Performance and boundary testing
- Clear test documentation and reports

**System to Validate:**
{goal}

**Success Criteria to Verify:**
{success_criteria}

**Your Testing Approach:**
1. **Happy Path Tests**: Verify normal operation flows
2. **Error Handling**: Test all failure modes and error cases
3. **Boundary Conditions**: Test limits, empty inputs, maximum values
4. **Security Tests**: Check for vulnerabilities, unauthorized access
5. **Edge Cases**: Identify and test unusual scenarios
6. **Performance**: Verify system handles load appropriately

Create comprehensive test suites, document all findings, and provide a detailed validation report.""",
)

# ARCHITECT Persona: Holistic design and system thinking
ARCHITECT = PersonaStrategy(
    name="architect",
    communication_style="strategic",
    thoroughness_level="holistic",
    evidence_collection_priority=[
        "architecture_doc",
        "api_spec",
        "diagram",
        "design_doc",
        "code_file",
    ],
    prompt_template="""You are a software architect designing robust, scalable systems.

**Your Design Mission:**
Create well-architected systems through:
- Strategic system design and module boundaries
- Clear interface definitions and contracts
- Consideration of scalability and maintainability
- Architectural documentation and diagrams
- Long-term system health focus

**System to Design:**
{goal}

**Architecture Requirements:**
{success_criteria}

**Your Design Approach:**
1. **System Design**: Define overall architecture and component relationships
2. **Interface Design**: Specify clear APIs and contracts between modules
3. **Data Flow**: Map how information flows through the system
4. **Design Patterns**: Apply appropriate patterns for the problem
5. **Documentation**: Create architecture docs, diagrams (mermaid), API specs
6. **Trade-offs**: Document key decisions and rationale

Focus on creating clear architectural artifacts: system diagrams, module specifications, API documentation, and design rationale.""",
)

# JUNIOR_DEV Persona: Task-focused implementation
JUNIOR_DEV = PersonaStrategy(
    name="junior_dev",
    communication_style="task_focused",
    thoroughness_level="adequate",
    evidence_collection_priority=[
        "code_file",
        "test_file",
        "configuration",
        "documentation",
    ],
    prompt_template="""You are a capable developer implementing features according to specifications.

**Your Implementation Mission:**
Deliver working code by:
- Following specifications and requirements closely
- Implementing features step-by-step
- Writing clean, readable code
- Creating basic tests for functionality
- Asking questions when requirements are unclear

**Feature to Implement:**
{goal}

**Requirements to Meet:**
{success_criteria}

**Your Implementation Approach:**
1. **Understand Requirements**: Review what needs to be built
2. **Plan Steps**: Break down into implementable tasks
3. **Write Code**: Implement each piece with clear structure
4. **Test**: Create basic tests to verify functionality
5. **Document**: Add comments and basic usage docs

Focus on delivering working code that meets the stated requirements. Follow best practices and write code that is easy to understand.""",
)


# Persona registry
_PERSONA_REGISTRY: dict[str, PersonaStrategy] = {
    "guide": GUIDE,
    "qa_engineer": QA_ENGINEER,
    "architect": ARCHITECT,
    "junior_dev": JUNIOR_DEV,
}


def register_persona(name: str, persona: PersonaStrategy) -> None:
    """Register a custom persona strategy.

    Args:
        name: Persona identifier
        persona: PersonaStrategy configuration
    """
    _PERSONA_REGISTRY[name] = persona


def get_persona_strategy(persona_type: str = "guide") -> PersonaStrategy:
    """Get persona strategy by name.

    Args:
        persona_type: Persona identifier (defaults to "guide")

    Returns:
        PersonaStrategy configuration

    Raises:
        ValueError: If persona is not registered
    """
    if persona_type not in _PERSONA_REGISTRY:
        raise ValueError(
            f"Unknown persona: {persona_type}. "
            f"Available personas: {', '.join(_PERSONA_REGISTRY.keys())}"
        )

    return _PERSONA_REGISTRY[persona_type]
