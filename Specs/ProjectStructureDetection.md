# Project Structure Detection System

## Executive Summary

This document specifies a reusable structure detection system that prevents agents from building tools in wrong project locations. The root cause of issue #1464 was agents ignoring project structure signals (stubs, test files, conventions) that indicate where artifacts should be created.

This system provides:

1. **Detection Algorithm** - Multi-signal priority analysis to identify project structure
2. **Workflow Integration** - Integration points for clarification, design, and implementation phases
3. **Data Structures** - Contracts for passing detection results between workflow steps
4. **Edge Case Handling** - Strategies for ambiguous or missing signals
5. **Validation Approach** - Pre-build verification to prevent structural errors

## Problem Statement

### Current Issue

When agents clarify requirements or design solutions, they often lack awareness of project conventions:

- **Symptom**: Tools built in `.claude/scenarios/` instead of `/project/root/`
- **Root Cause**: No examination of test files, stubs, or existing directory conventions
- **Impact**: 0-score benchmarks, incorrect directory structures, wasted implementation effort

### Why This Matters

Project structure communicates intent:

- **Stubs/Placeholders**: "This is where this module belongs"
- **Test Files**: "This is the expected location and interface"
- **Directory Conventions**: "We put X type of code in Y location"
- **Existing Patterns**: "This is how we do things here"

Ignoring these signals means building in wrong locations despite clearer signals than user requirements.

## System Architecture

### High-Level Overview

```
User Requirements
        ↓
Structure Detection System
    ├── Signal Scanner (2-5 second scan)
    ├── Signal Priority Engine (analyze & rank)
    └── Result Classifier
        ↓
Detection Results (with confidence & signals)
        ↓
Agent Workflow Integration
    ├── Step 1 (Clarify): Use for context
    ├── Step 4 (Design): Constraint on solution design
    └── Step 5 (Implement): Verify before building
        ↓
Project Location + Structure Constraints
```

### Key Components

#### 1. Signal Scanner

Quickly identifies structural signals without deep analysis:

```
Input: Project root path
├── Scan for stubs (15ms)
│   └── Find *.stub.py, *.stub.js, TODO markers, @TODO decorators
├── Scan for test files (10ms)
│   └── Find test_*.py, *.test.js, __tests__, .test.ts patterns
├── Scan for conventions (20ms)
│   └── Analyze existing directory structure, patterns
└── Scan for configuration (10ms)
    └── Find pyproject.toml, package.json, project metadata

Output: Signal Set {type, location, confidence, source_file}
```

#### 2. Signal Priority Engine

Ranks signals by reliability (highest to lowest):

```
Priority 1: Stubs (90% confidence)
  └── Explicit placeholder indicating expected location

Priority 2: Test Files (85% confidence)
  └── Tests define expected interface and location

Priority 3: Existing Implementations (80% confidence)
  └── Similar code patterns in same location

Priority 4: Directory Conventions (70% confidence)
  └── Consistent patterns across project

Priority 5: Configuration Files (60% confidence)
  └── pyproject.toml, package.json hints
```

#### 3. Result Classifier

Produces actionable detection results:

```python
class ProjectStructureDetection:
    detected_root: str                 # Base directory for project
    structure_type: str                # (tool|library|plugin|scenario|custom)
    detection_method: str              # (stub|test|convention|config|fallback)
    confidence: float                  # 0.0-1.0
    signals: List[Signal]              # Raw signals found
    constraints: Dict[str, str]        # Location constraints
    warnings: List[str]                # Ambiguity warnings
```

## Detection Algorithm

### Algorithm: Multi-Signal Detection with Priority Ranking

```
FUNCTION detect_project_structure(project_root, requirement):

  signals = {}
  confidence_scores = []

  # Stage 1: Quick Scan (< 100ms)
  stubs = scan_for_stubs(project_root)
  tests = scan_for_tests(project_root)
  conventions = analyze_conventions(project_root)
  config = scan_config_files(project_root)

  # Stage 2: Priority Analysis
  FOR each signal_type IN [stubs, tests, conventions, config]:
    signals_found = signals[signal_type]
    IF signals_found is not empty:
      score = calculate_priority_score(signal_type, signals_found)
      confidence_scores.append((signal_type, score, signals_found))

  # Stage 3: Classification
  IF confidence_scores is empty:
    RETURN fallback_detection(project_root, requirement)

  SORT confidence_scores BY score DESC

  dominant_signal = confidence_scores[0]
  IF dominant_signal.score >= CONFIDENCE_THRESHOLD:
    RETURN classify_from_signal(dominant_signal)

  # Stage 4: Ambiguity Resolution
  IF multiple_signals_conflict(confidence_scores):
    RETURN ambiguous_result(confidence_scores)

  RETURN confident_result(dominant_signal)
```

### Priority Ranking Rules

#### Level 1: Stubs (90% confidence)

**What to scan:**

```python
# Python stubs
"*.stub.py"                    # Explicit stub convention
"__{module}_stub__.py"         # Special stub pattern
# Decorated stubs
"@stub" or "@TODO" decorators  # Explicit markers

# JavaScript/TypeScript stubs
"*.stub.js"
"*.stub.ts"
".stubs/" directory
```

**Signal interpretation:**

```
stub_location = /path/to/module_name.stub.py
detected_location = parent_directory_of(stub_location)
confidence = 0.90
reason = "Explicit stub indicates expected location"
```

**Example:**

```
Project Structure:
  /project/
  ├── tools/
  │   ├── my_tool.stub.py        ← SIGNAL: Tool should go in /project/tools/
  │   └── existing_tool.py
  └── requirements.txt

Detection Result:
  detected_root: /project/tools/
  detection_method: stub
  confidence: 0.90
  signals: [Stub("my_tool.stub.py", "/project/tools/")]
```

#### Level 2: Test Files (85% confidence)

**What to scan:**

```python
# Python tests
"test_{module_name}.py"        # Standard pytest convention
"{module_name}_test.py"        # Alternative convention
"tests/test_{module_name}.py"  # Tests directory

# JavaScript/TypeScript tests
"{module}.test.js"
"{module}.test.ts"
"__tests__/{module}.js"
".test.js" / ".test.ts" suffix
```

**Signal interpretation:**

```
test_location = /path/to/test_my_tool.py
# Extract what module is being tested
module_name = extract_module_name(test_location)
detected_location = infer_module_location(module_name, test_location)
confidence = 0.85
reason = "Test location implies module location"
```

**Example:**

```
Project Structure:
  /project/
  ├── src/
  │   ├── modules/
  │   │   └── my_tool.py        ← TEST FILE imports this
  └── tests/
      └── test_my_tool.py       ← SIGNAL: Tool should be in /project/src/modules/

Detection:
  test_location: /project/tests/test_my_tool.py
  imports: from src.modules import my_tool
  detected_root: /project/src/modules/
  confidence: 0.85
  signals: [TestFile("test_my_tool.py", imports=[...])]
```

#### Level 3: Existing Implementations (80% confidence)

**What to scan:**

```python
# Analyze existing directory structure
- Directories with similar modules
- Existing tool implementations
- Pattern of where similar code lives
```

**Signal interpretation:**

```
# Requirement: "Add new security analysis tool"
# Existing: /project/tools/performance_analyzer.py

similar_tools = find_similar_implementations(requirement)
FOR tool IN similar_tools:
  location = directory_of(tool)
  # If pattern consistent, use as signal
detected_location = most_common_location(similar_tools)
confidence = 0.80
```

**Example:**

```
Project Structure:
  /project/tools/
  ├── analyzer_security.py         ← Existing security tool
  ├── analyzer_performance.py       ← Existing performance tool
  ├── analyzer_quality.py           ← Existing quality tool
  └── shared_utils.py

Requirement: "Create a new analyzer for code duplication"

Detection:
  similar_implementations: [
    analyzer_security.py,
    analyzer_performance.py,
    analyzer_quality.py
  ]
  detected_root: /project/tools/
  pattern: "All analyzers in /project/tools/"
  confidence: 0.80
  signals: [ExistingPattern("/project/tools/", 3 similar items)]
```

#### Level 4: Directory Conventions (70% confidence)

**What to scan:**

```python
# Analyze directory structure semantics
- README.md hints ("tools in this directory", "agents go here")
- Directory names that indicate purpose (tools/, agents/, lib/, src/)
- Consistent patterns in similar directories
```

**Signal interpretation:**

```
# If project has /project/tools/ directory with many tool-like files
convention = analyze_directory_purpose("/project/tools/")
# If convention suggests "tools go here", use for new tools
detected_location = "/project/tools/"
confidence = 0.70
reason = "Directory convention pattern"
```

**Example:**

```
Project Structure with Convention:
  /project/
  ├── .claude/
  │   └── scenarios/          ← Amplihack convention for scenarios
  ├── src/
  │   └── custom_tools/       ← Custom tool location
  └── tools/                  ← Generic tool location

README.md:
  "Tools should go in /tools/ or /src/custom_tools/"

Detection:
  conventions: [
    DirectoryHint("/.claude/scenarios/ - amplihack tools"),
    DirectoryHint("/tools/ - custom tools"),
    README hint matches conventions
  ]
  detected_root: /tools/ or /src/custom_tools/
  confidence: 0.70
```

#### Level 5: Configuration Files (60% confidence)

**What to scan:**

```python
# Read project metadata
pyproject.toml → [project] package-dir
package.json → main, type: module
setup.py → packages configuration
tsconfig.json → compilerOptions.rootDir
```

**Signal interpretation:**

```
config_data = parse_config_files(project_root)
IF config_data contains package paths:
  detected_location = config_data["package_location"]
  confidence = 0.60
  reason = "Configuration file hints"
```

### Fallback Strategy

If no signals detected:

```
FUNCTION fallback_detection(project_root, requirement):

  # Try sensible defaults in order of likelihood
  candidates = [
    project_root/tools/,
    project_root/src/,
    project_root/lib/,
    project_root/modules/,
    project_root/,
  ]

  FOR candidate IN candidates:
    IF candidate exists AND is_writable:
      RETURN FallbackDetection(
        detected_root: candidate,
        detection_method: "fallback",
        confidence: 0.30,
        warnings: [
          "No structural signals found - using fallback",
          "Recommend creating stub or test file for clarity",
          "Actual location may differ from user intent"
        ]
      )

  # Last resort: ask for clarification
  RETURN {
    detected_root: None,
    detection_method: "ambiguous",
    confidence: 0.0,
    warnings: [
      "Unable to detect project structure",
      "Requires manual clarification from user"
    ]
  }
```

## Workflow Integration

### Integration Points

#### Step 1: Rewrite and Clarify Requirements

**Purpose**: Use structure detection for context during requirement clarification

**Actions**:

```python
# During prompt-writer analysis
def clarify_requirements(user_requirement, project_root):

    # Scan project structure
    detection = detect_project_structure(project_root, user_requirement)

    # Add structure context to clarification
    clarification = {
        user_requirement: user_requirement,
        detected_structure: detection,
        context: f"""
        Based on project structure analysis:
        - Detected location: {detection.detected_root}
        - Detection method: {detection.detection_method}
        - Confidence: {detection.confidence}
        - Signals found: {format_signals(detection.signals)}

        {format_warnings(detection.warnings)}
        """,
        questions_to_clarify: [
            "Should this artifact be created at: {detection.detected_root}?",
            "If not, where should it go? (And why does structure suggest otherwise?)"
        ]
    }
    return clarification
```

**Data passed to next steps**: `clarified_requirement` includes `detected_structure`

#### Step 4: Research and Design

**Purpose**: Use structure detection as constraint on solution design

**Actions**:

```python
# During architect analysis
def design_solution(clarified_requirement, project_root):

    detection = clarified_requirement.detected_structure

    # Validate detection confidence
    if detection.confidence < 0.50:
        # Low confidence - design should include structure exploration
        design_constraint = {
            recommendation: "Structure ambiguous - include multiple options",
            default_location: detection.detected_root,
            alternative_locations: detect_alternative_locations(project_root),
            exploration_needed: True
        }
    else:
        # High confidence - use as design constraint
        design_constraint = {
            required_location: detection.detected_root,
            reason: f"Strong signal from {detection.detection_method}",
            confidence: detection.confidence,
            validation_required: True  # Verify before building
        }

    return design_constraint
```

**Key design principle**: "Where" is as important as "what"

**Data passed to next steps**: `solution_design` includes `structure_constraint`

#### Step 5: Implement the Solution

**Purpose**: Validate structure before building

**Actions**:

```python
# Before builder creates any files
def validate_structure_before_build(solution_design, project_root):

    structure_constraint = solution_design.structure_constraint
    target_location = structure_constraint.required_location

    # Perform pre-build validation
    validation = validate_target_location(target_location, project_root, solution_design)

    if not validation.is_valid:
        return BuildBlockedError(
            reason: validation.reason,
            detected_issue: validation.issue,
            recommendation: validation.fix,
            abort_build: True
        )

    # If valid, proceed with building at target location
    builder.create_at_location(target_location, solution_design)
```

**Pre-build validation checks**:

```
- Location exists or can be created
- Location matches structure signals
- Location consistent with similar artifacts
- No conflicting artifacts in location
- Location permissions allow writing
```

### Workflow Step Integration Details

```
Step 1: Clarify Requirements
├── Run: detect_project_structure(project_root, requirement)
├── Output: detection_result
├── Pass to Step 4: requirement.structure_detection = detection_result
└── Clarify: "Should this go in {detected_location}?"

Step 4: Design Solution
├── Input: requirement.structure_detection
├── Constraint: "Design must place artifact at detected_location"
├── Validate: If confidence < 0.5, design should explore alternatives
├── Pass to Step 5: design.structure_constraint = constraint
└── Document: "Artifact should be placed in: {location}"

Step 5: Implement Solution
├── Input: design.structure_constraint
├── Pre-build check: validate_target_location(constraint.location)
├── On failure: Report validation error, abort build
├── On success: Create artifact at target_location
└── Verify: "Artifact created at: {actual_location}"
```

## Data Structures

### Detection Result Structure

```python
@dataclass
class ProjectStructureDetection:
    """Result of project structure detection analysis"""

    # Core detection results
    detected_root: str                      # Absolute path to detected root
    structure_type: str                     # (tool|library|plugin|scenario|custom)
    detection_method: str                   # HOW we detected it
    confidence: float                       # 0.0 (guess) to 1.0 (certain)

    # Detailed signal information
    signals: List[Signal]                   # Raw signals found
    signals_ranked: List[Tuple[Signal, float]]  # Signals with scores

    # Location constraints for downstream steps
    constraints: LocationConstraint         # Where artifact must go

    # Context and warnings
    ambiguity_flags: List[str]              # Conflicting signals
    warnings: List[str]                     # Structure concerns

    # Alternative locations (for ambiguous cases)
    alternatives: List[AlternativeLocation] # Other possible locations

    # Metadata for logging/debugging
    scan_duration_ms: float                 # How long detection took
    signals_examined: int                   # Number of signals checked

@dataclass
class Signal:
    """A structural signal indicating project organization"""

    signal_type: str                        # (stub|test|convention|config|pattern)
    source_file: str                        # Where signal came from
    source_location: str                    # Absolute path
    inferred_location: str                  # What location this implies
    confidence: float                       # How reliable this signal is
    evidence: str                           # WHY this is a signal

    # For debugging
    parsed_at: str                          # Timestamp
    scan_method: str                        # HOW we found it

@dataclass
class LocationConstraint:
    """How the detected structure constrains artifact creation"""

    required_location: str                  # Absolute path artifact must go in
    required_location_exists: bool          # If true, must use existing dir
    may_create_directory: bool              # If true, ok to mkdir
    location_reasoning: str                 # WHY this location
    confidence: float                       # How confident about this location
    validation_required: bool               # Must validate before build

    # For ambiguous cases
    is_ambiguous: bool
    ambiguity_reason: str
    alternatives: List[str]                 # Other possible locations

@dataclass
class AlternativeLocation:
    """Possible alternative locations for artifact"""

    location: str                           # Absolute path
    signals: List[Signal]                   # Signals pointing here
    confidence: float                       # Confidence for this location
    reasoning: str                          # Why consider this alternative
```

### Signal Priority Mapping

```python
SIGNAL_PRIORITIES = {
    "stub": {
        "priority": 1,
        "confidence": 0.90,
        "pattern": ["*.stub.py", "*.stub.js", "@stub decorator"],
        "reliability": "very high"
    },
    "test": {
        "priority": 2,
        "confidence": 0.85,
        "pattern": ["test_*.py", "*.test.js", "__tests__/"],
        "reliability": "high"
    },
    "existing_implementation": {
        "priority": 3,
        "confidence": 0.80,
        "pattern": ["similar files in same location"],
        "reliability": "high"
    },
    "convention": {
        "priority": 4,
        "confidence": 0.70,
        "pattern": ["directory names, READMEs, patterns"],
        "reliability": "moderate"
    },
    "config": {
        "priority": 5,
        "confidence": 0.60,
        "pattern": ["pyproject.toml, package.json"],
        "reliability": "moderate"
    },
    "fallback": {
        "priority": 6,
        "confidence": 0.30,
        "pattern": ["default locations"],
        "reliability": "low"
    }
}
```

## Edge Case Handling

### Case 1: No Signals Detected (Ambiguous)

**Scenario**: New project with no stubs, tests, or clear conventions

**Handling**:

```python
detection_result = {
    detected_root: None,
    detection_method: "ambiguous",
    confidence: 0.0,
    warnings: [
        "No structural signals found",
        "Project structure unclear",
        "Recommend manual location specification"
    ],
    next_step: "Ask user for explicit location"
}

# In Step 1, clarification asks:
# "No structure signals found. Where should this artifact go?"
```

### Case 2: Conflicting Signals

**Scenario**: Stubs suggest `/tools/` but tests suggest `/src/`

**Handling**:

```python
detection_result = {
    detected_root: "/tools/",  # Highest priority signal
    detection_method: "stub",
    confidence: 0.90,
    ambiguity_flags: [
        "CONFLICT: Stubs suggest /tools/ (priority 1)",
        "CONFLICT: Tests suggest /src/ (priority 2)",
        "Using highest priority signal (stubs)"
    ],
    warnings: [
        "Structure signals conflicting",
        "Recommend investigating why stub/test locations differ"
    ],
    alternatives: ["/src/"]
}

# In Step 1, clarification asks:
# "Signals conflict: stubs suggest /tools/, tests suggest /src/. Which is correct?"
```

### Case 3: Multiple Similar Signals (Consensus)

**Scenario**: 5 stubs all pointing to `/project/tools/`

**Handling**:

```python
detection_result = {
    detected_root: "/project/tools/",
    detection_method: "stub",
    confidence: 0.95,  # HIGHER confidence due to consensus
    consensus: {
        signal_count: 5,
        agreement_level: "unanimous",
        reasoning: "All 5 stubs point to same location"
    }
}

# In Step 1: High confidence, minimal clarification needed
# In Step 4: Strong constraint, no alternatives needed
# In Step 5: Can proceed with confidence
```

### Case 4: Location Doesn't Exist

**Scenario**: Signals point to `/project/new_section/` which doesn't exist yet

**Handling**:

```python
detection_result = {
    detected_root: "/project/new_section/",
    detection_method: "stub",
    confidence: 0.85,
    location_exists: False,
    constraints: {
        required_location: "/project/new_section/",
        may_create_directory: True,
        location_reasoning: "Stub indicates new section needed",
        validation_required: True
    }
}

# In Step 5, pre-build validation checks:
# - Parent directory (/project/) exists
# - Can create /project/new_section/
# - No conflicting artifacts there
# - Then creates directory and builds
```

### Case 5: Stub Points Outside Project

**Scenario**: Stub path is `/external/location/module.stub.py`

**Handling**:

```python
detection_result = {
    detected_root: None,
    detection_method: "invalid_stub",
    confidence: 0.0,
    error: "Stub points outside project root",
    warnings: [
        "VALIDATION FAILED: Stub at /external/location/",
        "Stub must be within project boundaries",
        "Check if stub path is correct"
    ]
}

# In Step 1: Clarification raises error and asks user to fix
```

### Case 6: Ambiguous Convention (Multiple Possible Locations)

**Scenario**: Project has both `/tools/` and `/src/modules/` with similar patterns

**Handling**:

```python
detection_result = {
    detected_root: "/tools/",  # Pick most likely
    detection_method: "convention",
    confidence: 0.65,  # Lower confidence due to ambiguity
    alternatives: [
        {location: "/src/modules/", confidence: 0.60, reason: "Similar pattern"}
    ],
    ambiguity_flags: [
        "Multiple locations follow similar patterns",
        "Recommend using stubs or tests to disambiguate"
    ],
    warnings: [
        "Convention ambiguous: consider adding stub files"
    ]
}

# In Step 1: Clarification offers both options
# In Step 4: Design explores both, makes recommendation
```

## Validation Approach

### Pre-Build Validation

**Purpose**: Prevent structural errors before any files are created

**When**: Called at start of Step 5 (Implement)

**Checks**:

```python
def validate_target_location(target_location, project_root, design):
    """Validate that target location is safe for building"""

    checks = {
        "path_safety": validate_path_safety(target_location, project_root),
        "location_exists": validate_location_exists(target_location),
        "writable": validate_writable(target_location),
        "no_conflicts": validate_no_conflicts(target_location, design),
        "structure_match": validate_structure_consistency(target_location, design),
        "parent_exists": validate_parent_exists(target_location)
    }

    failures = [check for check in checks if not check.passed]

    if failures:
        return ValidationFailure(
            reason: "Pre-build validation failed",
            failures: failures,
            recommendation: suggest_fix(failures)
        )

    return ValidationSuccess()
```

**Individual validation rules**:

```python
# Path Safety: Target is within project, no traversal
validate_path_safety(target, root):
  return target.resolve().is_relative_to(root.resolve())

# Location Exists: Either directory exists or can be created
validate_location_exists(target):
  return target.exists() OR target.parent.exists()

# Writable: Can write files there
validate_writable(target):
  if target.exists():
    return os.access(target, os.W_OK)
  else:
    return os.access(target.parent, os.W_OK)

# No Conflicts: No existing artifact would be overwritten
validate_no_conflicts(target, design):
  existing_at_location = find_files_in(target, design.file_patterns)
  return len(existing_at_location) == 0

# Structure Consistency: Location matches project patterns
validate_structure_consistency(target, design):
  similar_artifacts = find_similar_in_project(design.artifact_type)
  expected_locations = extract_locations(similar_artifacts)
  return target in expected_locations OR similar_artifacts.empty()

# Parent Exists: Can create directory if needed
validate_parent_exists(target):
  return target.parent.exists()
```

## Testing Strategy

### Unit Tests

**Test Categories**:

```python
# 1. Signal Detection Tests
test_stub_signal_detection()           # Finds .stub.py files
test_test_file_detection()             # Finds test files
test_convention_detection()            # Analyzes directory patterns
test_config_detection()                # Reads configuration

# 2. Priority Ranking Tests
test_stub_highest_priority()           # Stubs ranked first
test_test_second_priority()            # Tests ranked second
test_confidence_calculation()          # Correct confidence scores
test_priority_order()                  # Signals ranked correctly

# 3. Fallback Tests
test_fallback_when_no_signals()        # Uses defaults
test_fallback_directory_exists()       # Picks existing directory
test_fallback_last_resort()            # Asks for clarification

# 4. Edge Case Tests
test_conflicting_signals()             # Handles conflicts
test_consensus_signals()               # Increases confidence
test_missing_location()                # Creates if allowed
test_external_stub()                   # Rejects invalid stubs
test_ambiguous_convention()            # Handles ambiguity
```

### Integration Tests

**Workflow Integration**:

```python
# Step 1 Integration
test_step1_adds_structure_context()    # Clarification includes structure
test_step1_asks_about_location()       # Asks user confirmation

# Step 4 Integration
test_step4_uses_structure_constraint() # Design respects location
test_step4_explores_alternatives()     # Explores if ambiguous

# Step 5 Integration
test_step5_validates_before_build()    # Pre-build check runs
test_step5_blocks_invalid_location()   # Prevents wrong structure
test_step5_creates_at_correct_location() # Builds at right spot
```

### End-to-End Tests

**Realistic Scenarios**:

```python
# Scenario 1: Well-Structured Project
test_e2e_stub_clear_detection()        # Stub → location → build
test_e2e_test_clear_detection()        # Test → location → build

# Scenario 2: Ambiguous Projects
test_e2e_ambiguous_requires_clarification()
test_e2e_conflicting_signals_handled()

# Scenario 3: New Projects
test_e2e_new_project_with_fallback()
test_e2e_creates_missing_directory()

# Scenario 4: Edge Cases
test_e2e_stub_outside_project()        # Rejected
test_e2e_permission_denied()           # Handled gracefully
test_e2e_no_signals_asks_user()        # Defers to user
```

### Performance Tests

```python
test_detection_completes_under_100ms() # Quick scan
test_handles_large_projects()          # Scales to big codebases
test_no_unnecessary_scanning()         # Only scans needed paths
```

### Data Validation Tests

```python
test_detection_result_schema()         # All fields populated
test_signal_data_structure()           # Signals well-formed
test_constraint_data_structure()       # Constraints consistent
test_serializable_for_logging()        # Can be logged/debugged
```

## Implementation Roadmap

### Phase 1: Core Detection Engine

- Implement signal scanner (stubs, tests, conventions, config)
- Implement priority ranking algorithm
- Implement fallback strategy
- Create data structures

### Phase 2: Workflow Integration

- Integrate with Step 1 (Clarify)
- Integrate with Step 4 (Design)
- Integrate with Step 5 (Implement)
- Add pre-build validation

### Phase 3: Agent Integration

- Update prompt-writer agent
- Update architect agent
- Update builder agent
- Document in agent contracts

### Phase 4: Testing and Refinement

- Comprehensive test suite
- Edge case handling
- Performance optimization
- Documentation

## Usage Examples

### Example 1: Clear Stub Signal

```
Project:
  /project/
  ├── tools/
  │   ├── analyzer.stub.py        ← STUB
  │   └── optimizer.py
  └── README.md

Requirement: "Create a code analyzer tool"

Detection Flow:
1. Scan finds: /project/tools/analyzer.stub.py
2. Signal Type: stub (priority 1, confidence 0.90)
3. Inferred Location: /project/tools/
4. Result: HIGH CONFIDENCE, location is /project/tools/

Step 1 Result:
  User requirement: "Create a code analyzer"
  Detected location: /project/tools/
  Question: "Should this go in /project/tools/?"

Step 4 Result:
  Design constraint: "Artifact must go in /project/tools/"
  Validation required: Yes
  Alternatives: None

Step 5 Result:
  Pre-build check: PASS (directory exists, writable, no conflicts)
  Create at: /project/tools/analyzer.py
  ✓ Correct location
```

### Example 2: Test File Signal

```
Project:
  /project/
  ├── src/
  │   └── security/
  │       └── validator.py
  ├── tests/
  │   └── test_validator.py       ← TEST FILE imports from src/security/
  └── setup.py

Requirement: "Enhance security validator"

Detection Flow:
1. Scan finds: test_validator.py imports src.security.validator
2. Signal Type: test (priority 2, confidence 0.85)
3. Inferred Location: /project/src/security/
4. Result: HIGH CONFIDENCE, location is /project/src/security/

Step 1 Result:
  Detected location: /project/src/security/
  Note: "Test imports indicate module at /project/src/security/"

Step 5 Result:
  Pre-build check: PASS
  Create at: /project/src/security/validator.py
  ✓ Correct location
```

### Example 3: Conflicting Signals

```
Project:
  /project/
  ├── src/
  │   └── modules/
  │       └── analyzer.py
  ├── tools/
  │   └── analyzer.stub.py        ← STUB says /tools/
  └── tests/
      └── test_analyzer.py        ← TEST says /src/modules/

Requirement: "Improve analyzer"

Detection Flow:
1. Scan finds:
   - /project/tools/analyzer.stub.py (priority 1, confidence 0.90)
   - /project/tests/test_analyzer.py (priority 2, confidence 0.85)
2. Conflict detected: stubs vs tests disagree
3. Use highest priority: stub wins
4. Result: MEDIUM-HIGH CONFIDENCE, location is /project/tools/

Step 1 Result:
  PRIMARY SIGNAL: Stub at /project/tools/ (confidence 0.90)
  CONFLICT: Test suggests /project/src/modules/ (confidence 0.85)
  Question: "Signals conflict. Should analyzer go in /project/tools/ or /src/modules/?"

Step 4 Result:
  Design must handle both options
  Recommendation: Ask user for clarification
  Note: "Structure signals conflicting - investigation recommended"

Step 5 Result:
  After user clarifies: build at specified location
  ✓ Prevents wrong location due to conflicting signals
```

### Example 4: No Signals (Ambiguous)

```
Project (new):
  /project/
  ├── src/
  │   ├── main.py
  │   └── utils.py
  └── README.md
  (No stubs, tests, or clear patterns)

Requirement: "Add a new reporting module"

Detection Flow:
1. Scan finds: No stubs, no tests, unclear patterns
2. Fallback: Try default locations
3. Result: LOW CONFIDENCE, needs user input

Step 1 Result:
  WARNING: "No structural signals found"
  Fallback locations: /project/src/, /project/, others
  Question: "Where should the reporting module go?"

Step 4 Result:
  Design explores multiple locations
  Recommendation: "User clarification recommended"

Step 5 Result:
  Build only after user specifies location
  ✓ Prevents guessing at structure
```

## Summary

This structure detection system provides:

1. **Reliability**: Multi-signal approach prevents missing structure clues
2. **Clarity**: Priority ranking ensures consistent decisions
3. **Flexibility**: Handles ambiguous and edge cases gracefully
4. **Integration**: Works seamlessly with existing workflow steps
5. **Debuggability**: Clear signals, reasoning, and alternatives
6. **Scalability**: Fast, efficient scanning and analysis

By implementing this system, agents will no longer ignore project structure signals and will build artifacts in correct locations with high confidence.
