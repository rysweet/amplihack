# Structure Detection Agent Integration Guide

## Overview

This document specifies how structure detection integrates with existing amplihack agents and workflow steps. It provides specific guidance for agent developers implementing this feature.

## Agent Responsibilities

### prompt-writer Agent

**Current Role**: Clarify user requirements and remove ambiguity

**New Responsibility**: Add structure context to clarification

**Integration Point**: Step 1 - Rewrite and Clarify Requirements

**What to Add**:

1. **Automatic Structure Detection**

   ```markdown
   ### New Step 1A: Project Structure Analysis (AUTOMATIC)

   Before writing the clarification prompt:

   1. Scan project for structural signals (stubs, tests, conventions)
   2. Analyze signal priorities (stub > test > convention > config)
   3. Rank results by confidence
   4. Return ProjectStructureDetection with:
      - detected_root: Inferred project location
      - confidence: How sure are we
      - signals: What signals we found
      - warnings: Any concerns
   ```

2. **Include Structure in Clarification**

   ```markdown
   When clarifying user requirement, include:

   "### Project Structure Context

   Based on scanning your project structure:

   **Detected Location**: {detection.detected_root}
   **Detection Method**: {detection.detection_method} (stub/test/convention/config/fallback)
   **Confidence**: {detection.confidence * 100}%
   **Signals Found**:
   - {signal_1}
   - {signal_2}
   ...

   {warnings_if_any}
   "

   Then ask clarifying question:

   "Should this artifact be created in {detection.detected_root}?
   - If yes, we'll use that location
   - If no, where should it go? (And let's understand why structure suggests elsewhere)"
   ```

3. **Capture User's Location Choice**

   ```markdown
   Extract from user response:

   clarified_requirement.structure_location = user_choice or default_to_detected

   Pass to next steps:
   - clarified_requirement.detected_structure
   - clarified_requirement.structure_location
   - clarified_requirement.structure_confidence
   - clarified_requirement.location_ambiguous (if true)
   ```

**Implementation Checklist**:

- [ ] Call `detect_project_structure(project_root, requirement)` early
- [ ] Include detection results in clarification output
- [ ] Ask user to confirm location
- [ ] Capture user's location choice
- [ ] Pass all structure data to Step 4
- [ ] Document location in acceptance criteria

**Input Contract**:

```python
{
    user_requirement: str,
    project_root: Path,
    explicit_constraints: Optional[List[str]]
}
```

**Output Contract**:

```python
{
    user_requirement: str,              # Original
    requirement_clarified: str,         # Clearer statement
    acceptance_criteria: List[str],
    constraints: List[str],

    # NEW: Structure information
    detected_structure: ProjectStructureDetection,   # Detection result
    structure_location: str,                         # User-confirmed location
    structure_confidence: float,                     # Confidence in location
    location_clarified: bool,                        # If user clarified it
    location_ambiguous_flag: bool                    # If ambiguous
}
```

**Example Output**:

```markdown
## Clarified Requirement

### Original Request
"Add a new analyzer tool to the project"

### Clarification
"Create a code analyzer tool that scans Python files and reports issues. The tool should:
- Be reusable across projects
- Support multiple analysis passes
- Cache results between runs"

### Project Structure Context

Based on project scanning:

**Detected Location**: `/project/tools/`
**Method**: Stub file found (analyzer.stub.py)
**Confidence**: 90%
**Signals**:
- Stub file at /project/tools/analyzer.stub.py
- Existing analyzer tools in /project/tools/

**Your confirmation**: Use /project/tools/ ✓

### Acceptance Criteria

- [ ] Analyzer created at `/project/tools/analyzer.py`
- [ ] Scans Python files for issues
- [ ] Results cached between runs
- [ ] All tests passing
- [ ] Documentation complete

### Location Constraints

**Primary Location**: `/project/tools/`
**Reason**: Explicit stub file indicates this location
**Confidence**: 90%
**Validation Required**: Yes
```

### architect Agent

**Current Role**: Design system architecture and solution components

**New Responsibility**: Include location as design constraint

**Integration Point**: Step 4 - Research and Design with TDD

**What to Add**:

1. **Read Structure Constraint**

   ```markdown
   ### New Step 4A: Receive Location Constraint (AUTOMATIC)

   From clarified requirement, extract:
   - detected_structure: ProjectStructureDetection
   - structure_location: User-confirmed location
   - location_confidence: How confident are we

   This becomes a DESIGN CONSTRAINT, not an option.
   ```

2. **Incorporate in Design**

   ```markdown
   ### Modified Step 4B: Design with Location (REQUIRED)

   When designing solution:

   1. Include location decision in architecture:
      - Where should each component go?
      - Why that location?
      - Dependencies on location choice?

   2. Document location reasoning:
      - "Main artifact goes to {detected_location}"
      - "Why: {reason}"
      - "If location changes, update {these things}"

   3. For ambiguous cases:
      - Design for multiple locations
      - Document pros/cons
      - Recommend primary location
   ```

3. **Return Location Constraint**

   ```markdown
   In solution design, include:

   design.structure_constraint = {
       required_location: structure_location,
       confidence: detection.confidence,
       detection_method: detection.detection_method,
       reasoning: location_reasoning,
       validation_required: True,
       alternatives: [alt1, alt2]
   }

   design.location_section = """
   ## Location Strategy

   ### Primary Location
   {required_location}

   ### Reasoning
   {reasoning}

   ### Confidence
   {confidence}% - Based on {detection_method}

   ### Validation
   This location will be validated before building.

   ### Alternatives (if primary location unavailable)
   {alternatives}
   """
   ```

**Implementation Checklist**:

- [ ] Extract `detected_structure` from clarified requirement
- [ ] Use `structure_location` as location constraint
- [ ] Include location decision in architecture
- [ ] Document why location was chosen
- [ ] For low-confidence cases, include alternatives
- [ ] Pass structure_constraint to Step 5
- [ ] Include location section in design spec

**Input Contract**:

```python
{
    clarified_requirement: {
        user_requirement: str,
        detected_structure: ProjectStructureDetection,
        structure_location: str,
        structure_confidence: float,
        ...
    }
}
```

**Output Contract**:

```python
{
    architecture: str,
    modules: List[ModuleSpec],
    implementation_plan: str,

    # NEW: Location constraint and reasoning
    structure_constraint: {
        required_location: str,
        confidence: float,
        reasoning: str,
        detection_method: str,
        validation_required: bool,
        alternatives: List[str]
    },
    location_section: str,
    location_alternatives_explored: bool
}
```

**Example Output**:

```markdown
## Solution Architecture

### Location Strategy

**Primary Location**: `/project/tools/`

**Reasoning**:
- Stub file `analyzer.stub.py` explicitly indicates this location
- Existing analyzer tools already in this directory
- Project convention: all tools in `/project/tools/`

**Confidence**: 90% (Based on stub file signal)

**What Goes Where**:
1. Main analyzer: `/project/tools/analyzer.py`
2. Utilities: `/project/tools/analyzer_utils.py`
3. Tests: `/project/tests/test_analyzer.py`

**Design Implications**:
- Utils module must be importable from main analyzer
- Tests should import from `/project/tools/analyzer.py`
- If location changes, update import statements

### Module Specifications

#### Module 1: Analyzer
- Location: `/project/tools/analyzer.py`
- Purpose: Main analysis orchestration
- ...

[Rest of architecture]
```

### builder Agent

**Current Role**: Implement code from specifications

**New Responsibility**: Validate location before building and create at correct location

**Integration Point**: Step 5 - Implement the Solution

**What to Add**:

1. **Pre-Build Location Validation** (CRITICAL - FIRST THING)

   ```markdown
   ### New Step 5A: Validate Target Location (MANDATORY - FIRST STEP)

   BEFORE creating ANY files:

   1. Extract `structure_constraint` from design
   2. Get target location: `structure_constraint.required_location`
   3. Call `validate_target_location(target, project_root, design)`
   4. Validation checks:
      - Path is inside project boundary
      - Location is writable
      - No existing conflicts
      - Parent directory exists or can create
      - Structure matches similar artifacts
   5. If validation FAILS:
      - Report specific failure reason
      - Do NOT create any files
      - Recommend fix
      - Abort build
   6. If validation PASSES:
      - Proceed to building
      - Create files at validated location
   ```

2. **Build at Validated Location Only**

   ```markdown
   ### Modified Step 5B: Build at Correct Location (REQUIRED)

   After validation passes:

   1. Create directory if needed: `mkdir -p {target_location}`
   2. Create all files in: `{target_location}`
   3. Verify files created in correct location
   4. Report actual location used

   RULE: Never create files at different location than validated
   ```

3. **Post-Build Verification**

   ```markdown
   ### New Step 5C: Verify Structure (AUTOMATIC)

   After building:

   1. Verify all files in required location
   2. Check imports reference correct location
   3. Verify tests can find and import modules
   4. Report: "All files created in {location}"
   ```

**Implementation Checklist**:

- [ ] Extract structure_constraint from design
- [ ] Call validate_target_location() BEFORE ANY file creation
- [ ] If validation fails, report error and abort
- [ ] Create all files at validated location
- [ ] Verify files in correct location after creation
- [ ] Update test imports to use correct location
- [ ] Report actual location used in results

**Pre-Build Validation Pseudo-code**:

```python
def implement_solution(solution_design, project_root):
    # FIRST: Validate location
    constraint = solution_design.structure_constraint
    target_location = Path(constraint.required_location)

    validation_result = validate_target_location(
        target_location=target_location,
        project_root=project_root,
        design=solution_design
    )

    if not validation_result.passed:
        raise BuildError(
            phase="pre-build-validation",
            reason=validation_result.reason,
            specific_issues=validation_result.failures,
            recommendation=validation_result.suggestion,
            location_attempted=target_location,
            abort=True  # Do not proceed
        )

    # SECOND: Create directory if needed
    target_location.mkdir(parents=True, exist_ok=True)

    # THIRD: Build at validated location
    for module_spec in solution_design.modules:
        file_path = target_location / module_spec.filename
        create_file(file_path, module_spec.code)

    # FOURTH: Verify all in correct location
    for file_created in files:
        assert file_created.parent == target_location

    return {
        files_created: files,
        location_used: target_location,
        location_validated: True,
        structure_verified: True
    }
```

**Input Contract**:

```python
{
    solution_design: {
        architecture: str,
        modules: List[ModuleSpec],
        structure_constraint: {
            required_location: str,
            confidence: float,
            validation_required: bool,
            ...
        },
        ...
    },
    project_root: Path
}
```

**Output Contract**:

```python
{
    files_created: List[str],
    location_used: str,
    location_validated: bool,
    validation_errors: Optional[List[str]],
    structure_verified: bool,
    all_tests_passing: bool,
    ...
}
```

**Example Build Flow**:

```python
# Step 5A: Validate Location
target_location = Path("/project/tools/analyzer.py").parent
validation = validate_target_location(target_location, project_root)
if not validation.passed:
    raise BuildError(
        f"Location validation failed: {validation.reason}",
        f"Issues: {validation.failures}"
    )

# Step 5B: Create Directory
target_location.mkdir(parents=True, exist_ok=True)

# Step 5C: Create Files
create_file(target_location / "analyzer.py", analyzer_code)
create_file(target_location / "analyzer_utils.py", utils_code)

# Step 5D: Verify
assert (target_location / "analyzer.py").exists()
assert (target_location / "analyzer_utils.py").exists()

# Report
print(f"✓ Created at: {target_location}")
```

## Validation Function Contract

### Function: `validate_target_location()`

**Purpose**: Verify target location is valid and safe before building

**Location**: `.claude/tools/structure-detection/validator.py`

**Signature**:

```python
def validate_target_location(
    target_location: Path,
    project_root: Path,
    design: SolutionDesign
) -> ValidationResult:
    """
    Validate that target location is safe for building.

    Args:
        target_location: Directory where files will be created
        project_root: Project root directory
        design: Solution design with file specifications

    Returns:
        ValidationResult with passed/failed status and reasons

    Raises:
        ValueError: If inputs invalid
        PermissionError: If cannot check permissions
    """
```

**Validation Checks**:

```python
class ValidationResult:
    passed: bool                        # All checks passed
    failures: List[str]                 # What failed
    reason: str                         # Summary
    suggestion: str                     # How to fix
    can_create_directory: bool          # Can we mkdir
    is_writable: bool                   # Can we write
    has_conflicts: bool                 # Existing files
    is_inside_project: bool             # In project boundary

checks = {
    "inside_project": {
        description: "Target is inside project",
        check: target.resolve().is_relative_to(project_root.resolve()),
        on_failure: "Target location outside project boundary"
    },
    "parent_exists": {
        description: "Parent directory exists",
        check: target.parent.exists(),
        on_failure: "Parent directory does not exist"
    },
    "writable": {
        description: "Can write files",
        check: check_write_permission(target),
        on_failure: "No write permission"
    },
    "no_conflicts": {
        description: "No existing conflicts",
        check: not has_conflicting_files(target, design),
        on_failure: f"Existing files: {conflicting_files}"
    },
    "structure_match": {
        description: "Consistent with project",
        check: matches_project_structure(target, design),
        on_failure: "Location inconsistent with project structure"
    }
}
```

**Example Usage**:

```python
# In builder agent
validation = validate_target_location(
    target_location=Path("/project/tools/"),
    project_root=Path("/project/"),
    design=solution_design
)

if not validation.passed:
    print(f"Validation failed: {validation.reason}")
    for failure in validation.failures:
        print(f"  - {failure}")
    print(f"Suggestion: {validation.suggestion}")
    raise BuildError(validation.reason)

# Safe to build now
create_files(target_location, design)
```

## Integration Pattern Summary

```
User Requirement
    ↓
prompt-writer (Step 1)
├── Detect structure: detect_project_structure()
├── Clarify requirement
├── Ask about location
├── Return: clarified_requirement with detected_structure
    ↓
architect (Step 4)
├── Read: clarified_requirement.detected_structure
├── Design with location as constraint
├── Document location reasoning
├── Return: solution_design with structure_constraint
    ↓
builder (Step 5)
├── Extract: solution_design.structure_constraint
├── PRE-BUILD: validate_target_location()
├── If valid: Create files at location
├── If invalid: Abort with error
├── Return: files_created with location_verified=true
    ↓
✓ Correct Location
```

## Error Handling Guide

### When Validation Fails

**Scenario 1: Location Outside Project**

```python
validation_result = {
    passed: False,
    reason: "Path traversal detected",
    failures: ["Target location outside project boundary"],
    suggestion: "Ensure target is within project directory"
}

# Agent action: Raise BuildError and abort
```

**Scenario 2: No Write Permission**

```python
validation_result = {
    passed: False,
    reason: "Permission denied",
    failures: ["No write permission on target directory"],
    suggestion: "Check file permissions or change target directory"
}

# Agent action: Raise BuildError, suggest alternatives
```

**Scenario 3: Conflicting Files**

```python
validation_result = {
    passed: False,
    reason: "Existing files would be overwritten",
    failures: [
        "File already exists: /project/tools/analyzer.py",
        "File already exists: /project/tools/analyzer_test.py"
    ],
    suggestion: "Remove existing files or choose different location"
}

# Agent action: Raise BuildError, ask user
```

## Testing Guidelines

### Test Location Validation

```python
def test_validation_inside_project():
    """Validates target inside project"""
    result = validate_target_location(
        target_location=Path("/project/tools/"),
        project_root=Path("/project/"),
        design=sample_design
    )
    assert result.passed

def test_validation_outside_project():
    """Rejects target outside project"""
    result = validate_target_location(
        target_location=Path("/external/"),
        project_root=Path("/project/"),
        design=sample_design
    )
    assert not result.passed
    assert "outside project" in result.reason
```

### Test Integration

```python
def test_prompt_writer_includes_structure():
    """Step 1 includes detected structure"""
    result = prompt_writer.clarify(
        requirement="Add analyzer",
        project_root=test_project
    )
    assert result.detected_structure is not None
    assert result.structure_location is not None

def test_architect_uses_constraint():
    """Step 4 uses structure constraint"""
    design = architect.design(clarified_requirement)
    assert design.structure_constraint is not None
    assert design.structure_constraint.required_location == expected_location

def test_builder_validates_before_creating():
    """Step 5 validates before creating files"""
    with patch('validate_target_location', return_value=VALID):
        files = builder.implement(solution_design)
        assert all(f.parent == expected_location for f in files)

    with patch('validate_target_location', return_value=INVALID):
        with pytest.raises(BuildError):
            builder.implement(solution_design)
```

## Summary

This integration guide ensures:

1. **prompt-writer**: Detects structure and includes in clarification
2. **architect**: Uses structure as design constraint
3. **builder**: Validates location before building
4. **Validation**: Prevents structural errors
5. **Testing**: Verifies integration works correctly
6. **Error Handling**: Clear failures with suggestions

Agents implementing these changes will prevent issue #1464: building in wrong project locations.
