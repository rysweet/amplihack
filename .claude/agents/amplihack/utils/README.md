# Project Structure Detection System

Automated detection of project structure to prevent building artifacts in wrong locations.

**Problem Solved**: Agents no longer ignore structural signals (stubs, tests, conventions) when building tools.

**Issue**: #1464 - Structure Detection System

## Quick Start

```python
from structure_detection import detect_project_structure, validate_target_location
from pathlib import Path

# Detect where artifacts should be created
detection = detect_project_structure(
    project_root="/path/to/project",
    requirement="Create analyzer tool"
)

print(f"Build at: {detection.detected_root}")
print(f"Confidence: {detection.confidence}")
print(f"Method: {detection.detection_method}")

# Validate location before building
validation = validate_target_location(
    target_location=Path(detection.detected_root),
    project_root=Path("/path/to/project")
)

if validation.passed:
    # Safe to build
    create_files_at_location(detection.detected_root)
else:
    # Report errors
    print(f"Validation failed: {validation.reason}")
    for failure in validation.failures:
        print(f"  - {failure}")
```

## Features

### Multi-Signal Detection

Scans project for structural signals and ranks by reliability:

| Priority | Signal Type | Confidence | Description |
|----------|-------------|------------|-------------|
| 1 | Stubs | 90% | `*.stub.py` files indicating expected location |
| 2 | Tests | 85% | Test files with imports pointing to location |
| 3 | Existing | 80% | Similar implementations in same directory |
| 4 | Conventions | 70% | Directory patterns and organization |
| 5 | Config | 60% | Configuration file hints |
| 6 | Fallback | 30% | Default locations when no signals found |

### Workflow Integration

Integrates seamlessly with existing workflow:

```
Step 1 (prompt-writer):
  → Detect structure automatically
  → Include location context in requirements

Step 4 (architect):
  → Use detected location as design constraint
  → Document location reasoning

Step 5 (builder):
  → Validate location before building
  → Create files at validated location
  → Verify correct placement
```

### Pre-Build Validation

Comprehensive validation checks before file creation:

- ✓ Path inside project boundary (no traversal)
- ✓ Parent directory exists
- ✓ Location is writable
- ✓ No conflicting files
- ✓ Consistent with project structure

## API Reference

### detect_project_structure()

Main entry point for structure detection.

```python
def detect_project_structure(
    project_root: str,
    requirement: Optional[str] = None,
    timeout_ms: int = 100
) -> ProjectStructureDetection
```

**Args**:
- `project_root`: Absolute path to project root directory
- `requirement`: Optional requirement text for context
- `timeout_ms`: Maximum scanning time (default: 100ms)

**Returns**: `ProjectStructureDetection` with:
- `detected_root`: Where artifact should be created
- `confidence`: 0.0-1.0 confidence score
- `detection_method`: How detected (stub/test/convention/config/fallback/ambiguous)
- `signals`: Raw signals found
- `constraints`: Actionable location constraint
- `warnings`: Any structural concerns
- `alternatives`: Other possible locations

**Example**:

```python
detection = detect_project_structure("/path/to/project")

if detection.confidence > 0.7:
    # High confidence - use detected location
    build_at(detection.detected_root)
elif detection.confidence > 0.5:
    # Medium confidence - ask user to confirm
    if confirm_location(detection.detected_root):
        build_at(detection.detected_root)
    else:
        # Use alternative
        build_at(detection.alternatives[0]["location"])
else:
    # Low confidence - ask user
    location = ask_user_for_location()
    build_at(location)
```

### validate_target_location()

Validates location before building.

```python
def validate_target_location(
    target_location: Path,
    project_root: Path
) -> ValidationResult
```

**Args**:
- `target_location`: Directory where files will be created
- `project_root`: Project root directory

**Returns**: `ValidationResult` with:
- `passed`: True if all checks passed
- `failures`: List of what failed
- `reason`: Summary of result
- `suggestion`: How to fix failures
- `is_inside_project`: Path safety check
- `is_writable`: Permission check
- `can_create_directory`: If can mkdir

**Example**:

```python
validation = validate_target_location(
    target_location=Path("/project/tools"),
    project_root=Path("/project")
)

if not validation.passed:
    raise BuildError(
        f"Location validation failed: {validation.reason}\n"
        f"Issues: {validation.failures}\n"
        f"Suggestion: {validation.suggestion}"
    )

# Safe to build
create_files(target_location)
```

## Data Structures

### ProjectStructureDetection

Complete detection result with all information:

```python
@dataclass
class ProjectStructureDetection:
    # Core results
    detected_root: Optional[str]        # Primary location (None if ambiguous)
    structure_type: str                 # tool|library|plugin|scenario|custom
    detection_method: str               # HOW detected
    confidence: float                   # 0.0-1.0

    # Signal details
    signals: List[Signal]               # Raw signals found
    signals_ranked: List[RankedSignal]  # Ranked by priority

    # Actionable constraint
    constraints: LocationConstraint     # Where to build

    # Edge cases
    ambiguity_flags: List[str]          # Conflicts detected
    warnings: List[str]                 # Structural concerns
    alternatives: List[Dict]            # Other possible locations

    # Metadata
    scan_duration_ms: float             # Performance
    signals_examined: int               # Diagnostics
```

### LocationConstraint

Actionable constraint for builders:

```python
@dataclass
class LocationConstraint:
    required_location: str          # Where artifact must go
    location_exists: bool           # If directory exists
    may_create_directory: bool      # If can mkdir
    location_reasoning: str         # Why this location
    confidence: float               # 0.0-1.0
    validation_required: bool       # Must validate first
    is_ambiguous: bool              # If conflicting signals
    ambiguity_reason: str           # Why ambiguous
    alternatives: List[str]         # Other options
```

### Signal

Atomic piece of structural evidence:

```python
@dataclass
class Signal:
    signal_type: str              # stub|test|convention|config|pattern
    source_file: str              # Where found
    inferred_location: str        # What location this indicates
    confidence: float             # 0.0-1.0
    evidence: str                 # Why this is a signal
    parsed_at: str                # Timestamp
```

## Common Scenarios

### Scenario 1: Clear Stub Signal

```python
# Project has: /project/tools/analyzer.stub.py
detection = detect_project_structure("/project")

# Result:
# detected_root: "/project/tools/"
# confidence: 0.90
# detection_method: "stub"
# warnings: []

# Action: Build at /project/tools/ with confidence
```

### Scenario 2: Conflicting Signals

```python
# Stub in /tools/, test imports from /src/
detection = detect_project_structure("/project")

# Result:
# detected_root: "/project/tools/" (highest priority)
# confidence: 0.90
# ambiguity_flags: ["Stub says /tools/, test says /src/"]
# alternatives: [{"location": "/project/src/", ...}]

# Action: Ask user "Use /tools/ or /src/?"
```

### Scenario 3: No Signals (Ambiguous)

```python
# New project with no structure signals
detection = detect_project_structure("/project")

# Result:
# detected_root: None
# confidence: 0.0
# detection_method: "ambiguous"
# warnings: ["No structural signals found"]

# Action: Ask user "Where should this go?"
```

### Scenario 4: Multiple Signals Agree (Consensus)

```python
# 5 stubs, 3 tests, all pointing to /project/tools/
detection = detect_project_structure("/project")

# Result:
# detected_root: "/project/tools/"
# confidence: 0.95 (boosted by consensus)
# detection_method: "stub"
# warnings: []

# Action: Build at /project/tools/ with very high confidence
```

## Performance

- **Target**: < 100ms total detection time
- **Typical**: 40-60ms for most projects
- **Concurrent**: Parallel scanning of signal types
- **Caching**: Results can be cached for repeated calls

Performance characteristics:

```
Signal Type    | Scan Time
---------------|----------
Stubs          | ~15ms
Tests          | ~10ms
Conventions    | ~20ms
Config         | ~10ms
Total          | ~55ms (concurrent)
```

## Edge Cases

### Case 1: Location Doesn't Exist

```python
# Stub points to /project/new_section/ which doesn't exist
detection = detect_project_structure("/project")

# Result includes:
# constraints.location_exists: False
# constraints.may_create_directory: True

# Validation checks:
validation = validate_target_location(...)
# validation.can_create_directory: True if parent exists

# Builder can create directory
```

### Case 2: Multiple Similar Signals

```python
# 3 stubs all in /tools/ → consensus boost
detection = detect_project_structure("/project")

# confidence: 0.92 (0.90 + 0.02 boost)
# Higher confidence when multiple signals agree
```

### Case 3: Stub Outside Project

```python
# Invalid stub at /external/location/
detection = detect_project_structure("/project")

# Validation fails:
validation = validate_target_location(Path("/external/location"), ...)
# validation.passed: False
# validation.is_inside_project: False
# validation.failures: ["Target location outside project boundary"]
```

## Testing

Run comprehensive test suite:

```bash
cd .claude/agents/amplihack/utils
python -m pytest test_structure_detection.py -v
```

Test categories:
- Signal detection (stubs, tests, conventions, config)
- Priority ranking and consensus
- Conflict resolution
- Fallback behavior
- Validation
- Performance (< 100ms)
- Edge cases

## Integration Examples

### Integration with prompt-writer (Step 1)

```python
# In prompt-writer agent
from structure_detection import detect_project_structure

def clarify_requirements(user_requirement, project_root):
    # Detect structure first
    detection = detect_project_structure(
        project_root=project_root,
        requirement=user_requirement
    )

    # Include in clarification
    clarification = {
        "user_requirement": user_requirement,
        "detected_structure": detection,
        "structure_location": detection.detected_root,
        "location_context": f"""
        Based on project structure analysis:
        - Detected location: {detection.detected_root}
        - Confidence: {detection.confidence * 100}%
        - Method: {detection.detection_method}

        Should artifact be created at {detection.detected_root}?
        """
    }

    return clarification
```

### Integration with architect (Step 4)

```python
# In architect agent
def design_solution(clarified_requirement):
    # Extract structure info
    detection = clarified_requirement.detected_structure
    location = clarified_requirement.structure_location

    # Design with location constraint
    design = {
        "architecture": "...",
        "modules": [...],
        "structure_constraint": {
            "required_location": location,
            "confidence": detection.confidence,
            "reasoning": f"Detected via {detection.detection_method}",
            "validation_required": True
        }
    }

    return design
```

### Integration with builder (Step 5)

```python
# In builder agent
from structure_detection import validate_target_location
from pathlib import Path

def implement_solution(solution_design):
    # Extract location constraint
    constraint = solution_design.structure_constraint
    target_location = Path(constraint.required_location)
    project_root = Path.cwd()

    # PRE-BUILD VALIDATION
    validation = validate_target_location(target_location, project_root)

    if not validation.passed:
        raise BuildError(
            f"Location validation failed: {validation.reason}\n"
            f"Issues: {validation.failures}\n"
            f"Suggestion: {validation.suggestion}"
        )

    # Safe to build
    create_files_at(target_location, solution_design)

    # Verify location
    verify_files_at(target_location)

    return {
        "files_created": [...],
        "location_used": str(target_location),
        "location_validated": True
    }
```

## Design Principles

1. **Multi-Signal Detection**: Don't rely on single signal
2. **Priority-Based Ranking**: Always use highest priority signal
3. **Confidence Scoring**: Track how sure we are
4. **Workflow Integration**: Affects Steps 1, 4, 5
5. **Graceful Degradation**: Handle ambiguity properly
6. **Clear Contracts**: Data flows predictably
7. **Pre-Build Validation**: Never build at wrong location
8. **Debuggability**: Always know why decision was made

## Troubleshooting

### Detection returns None

**Cause**: No signals found (new/empty project)

**Solution**: Use fallback locations or ask user

```python
if detection.detected_root is None:
    # Offer defaults
    defaults = ["/project/tools", "/project/src"]
    location = ask_user_to_choose(defaults)
```

### Low confidence (< 50%)

**Cause**: Ambiguous structure, conflicting signals

**Solution**: Present alternatives to user

```python
if detection.confidence < 0.5:
    options = [detection.detected_root] + [
        alt["location"] for alt in detection.alternatives
    ]
    location = ask_user_to_choose(options)
```

### Validation fails

**Cause**: Location outside project, no permissions, conflicts

**Solution**: Report specific failures and suggestions

```python
if not validation.passed:
    print(f"Validation failed: {validation.reason}")
    for failure in validation.failures:
        print(f"  - {failure}")
    print(f"Suggestion: {validation.suggestion}")

    # Try alternative
    if detection.alternatives:
        alt_location = Path(detection.alternatives[0]["location"])
        alt_validation = validate_target_location(alt_location, project_root)
        if alt_validation.passed:
            use_alternative(alt_location)
```

## Related Documentation

- **Complete Specification**: `/Specs/ProjectStructureDetection.md`
- **Implementation Guide**: `/Specs/StructureDetectionImplementation.md`
- **Agent Integration**: `/Specs/StructureDetectionAgentIntegration.md`
- **Summary**: `/Specs/StructureDetectionSummary.md`

## Issue Reference

- **Issue #1464**: Project Structure Detection
- **Root Cause**: Agents ignored structural signals when building
- **Impact**: 0-score benchmarks, incorrect project structure
- **Solution**: Automated detection with workflow integration

## Version

- **Version**: 1.0
- **Created**: November 21, 2025
- **Status**: Production Ready
- **Python**: 3.9+
- **Dependencies**: None (stdlib only)
