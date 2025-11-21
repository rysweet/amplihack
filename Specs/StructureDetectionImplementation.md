# Structure Detection Implementation Guide

## Overview

This document provides step-by-step implementation guidance for the project structure detection system. It complements `ProjectStructureDetection.md` with concrete code patterns, integration points, and implementation checklists.

## Part 1: Core Implementation

### Module 1.1: Signal Scanner

**Purpose**: Quickly scan project for structural signals

**Location**: `.claude/tools/structure-detection/signal_scanner.py`

**Interface**:

```python
@dataclass
class Signal:
    signal_type: str              # "stub" | "test" | "convention" | "config" | "pattern"
    source_file: str              # Absolute path to where signal was found
    inferred_location: str        # What location this signal indicates
    confidence: float             # 0.0-1.0
    evidence: str                 # Why this is a signal
    parsed_at: str                # ISO timestamp

class SignalScanner:
    def __init__(self, project_root: Path):
        self.project_root = project_root

    def scan_all(self, timeout_ms: int = 100) -> List[Signal]:
        """Scan project for all signals, return within timeout"""
        # Implementation approach:
        # 1. Use concurrent.futures for parallel scanning
        # 2. Stop all operations at timeout
        # 3. Return best results found so far

    def scan_stubs(self) -> List[Signal]:
        """Find stub files and TODO markers"""
        # Scan for:
        # - *.stub.py, *.stub.js, *.stub.ts
        # - @stub decorators
        # - @TODO markers
        # Return: List of stub signals

    def scan_tests(self) -> List[Signal]:
        """Find test files and extract what they test"""
        # Scan for:
        # - test_*.py, *_test.py
        # - *.test.js, *.test.ts
        # - __tests__/ directories
        # Extract imports to find module locations
        # Return: List of test signals

    def scan_conventions(self) -> List[Signal]:
        """Analyze directory patterns"""
        # Analyze:
        # - Directory names (tools/, agents/, lib/, src/)
        # - Existing files in directories (type inference)
        # - README.md hints
        # Return: List of convention signals

    def scan_config(self) -> List[Signal]:
        """Read configuration files"""
        # Read:
        # - pyproject.toml (package-dir)
        # - package.json (main, type)
        # - setup.py (packages)
        # - tsconfig.json (rootDir)
        # Return: List of config signals
```

**Implementation Notes**:

- Use `pathlib.Path` for all file operations
- Make all scans fast (< 100ms total)
- Handle permission errors gracefully
- Cache results for repeated calls

**Key Functions**:

```python
def extract_import_from_test(test_file: Path) -> str:
    """Extract what module a test imports"""
    # Parse import statements
    # Return module path

def find_directory_purpose(dir_path: Path) -> str:
    """Infer what type of code goes in a directory"""
    # Analyze files in directory
    # Look at similar projects
    # Return "tools", "agents", "lib", "tests", etc.

def parse_pyproject_package_dir(pyproject_path: Path) -> str:
    """Extract package directory from pyproject.toml"""
    # Use tomllib (Python 3.11+)
    # Fall back to manual parsing
    # Return path or None

def read_readme_hints(readme_path: Path) -> List[str]:
    """Extract structural hints from README"""
    # Look for patterns like "tools go in..."
    # Return list of hints
```

### Module 1.2: Priority Engine

**Purpose**: Rank signals and compute confidence scores

**Location**: `.claude/tools/structure-detection/priority_engine.py`

**Interface**:

```python
@dataclass
class RankedSignal:
    signal: Signal
    priority: int                 # 1-6, lower = higher priority
    priority_name: str            # "stub" | "test" | "existing" | "convention" | "config" | "fallback"
    adjusted_confidence: float    # Takes into account consensus
    reasoning: str                # Why this priority

class PriorityEngine:
    def __init__(self):
        self.priority_map = {
            "stub": 1,
            "test": 2,
            "existing_implementation": 3,
            "convention": 4,
            "config": 5,
            "fallback": 6
        }

    def rank_signals(self, signals: List[Signal]) -> List[RankedSignal]:
        """Sort signals by priority and adjust confidence"""
        # Implementation approach:
        # 1. Assign priority to each signal
        # 2. Check for consensus (multiple signals same location)
        # 3. Adjust confidence based on consensus
        # 4. Return ranked list

    def compute_consensus(self, signals: List[Signal], location: str) -> float:
        """How much confidence increase for multiple signals agreeing"""
        # If N signals point to same location:
        # confidence += 0.02 * (N - 1), capped at 0.95

    def resolve_conflicts(self, ranked_signals: List[RankedSignal]) -> Dict:
        """Detect and report conflicting signals"""
        # Find signals pointing to different locations
        # Return conflict information for handling

    def apply_project_context(self, ranked_signals: List[RankedSignal],
                            project_context: Dict) -> List[RankedSignal]:
        """Adjust priorities based on project type"""
        # Amplihack project: scenarios/ higher priority
        # Tool project: tools/ higher priority
        # Library: src/ higher priority
```

**Implementation Notes**:

- Keep priority order simple and fixed
- Increase confidence for consensus (don't override priority)
- Report all conflicts clearly
- Support project-aware context (optional)

### Module 1.3: Result Classifier

**Purpose**: Turn ranked signals into actionable detection results

**Location**: `.claude/tools/structure-detection/result_classifier.py`

**Interface**:

```python
@dataclass
class LocationConstraint:
    required_location: str
    location_exists: bool
    may_create_directory: bool
    location_reasoning: str
    confidence: float
    validation_required: bool
    is_ambiguous: bool
    ambiguity_reason: str
    alternatives: List[str]

@dataclass
class ProjectStructureDetection:
    detected_root: str                      # Main result
    structure_type: str                     # "tool" | "library" | "plugin" | "scenario" | "custom"
    detection_method: str                   # HOW detected
    confidence: float                       # Overall confidence
    signals: List[Signal]                   # Raw signals
    signals_ranked: List[RankedSignal]      # Ranked signals
    constraints: LocationConstraint         # Actionable constraint
    ambiguity_flags: List[str]              # Warnings about conflicts
    warnings: List[str]                     # General warnings
    alternatives: List[Dict]                # Alternative locations
    scan_duration_ms: float
    signals_examined: int

class ResultClassifier:
    def classify(self, ranked_signals: List[RankedSignal],
                 project_root: Path) -> ProjectStructureDetection:
        """Convert ranked signals into detection result"""
        # Implementation approach:
        # 1. Check if signals found
        # 2. Select dominant signal
        # 3. Check for conflicts
        # 4. Create constraint
        # 5. Identify alternatives
        # 6. Return complete result

    def select_dominant_signal(self, ranked_signals: List[RankedSignal]) -> RankedSignal:
        """Pick highest priority signal"""
        # Return first in ranked list (highest priority)

    def create_constraint(self, signal: RankedSignal,
                         project_root: Path) -> LocationConstraint:
        """Build actionable location constraint"""
        # Extract location from signal
        # Check if location exists
        # Determine if can create directory
        # Assess validation needs

    def identify_alternatives(self, ranked_signals: List[RankedSignal],
                            dominant: RankedSignal) -> List[Dict]:
        """Find alternative locations for ambiguous cases"""
        # Return non-dominant signals as alternatives

    def detect_conflicts(self, ranked_signals: List[RankedSignal]) -> List[str]:
        """Find conflicting signals"""
        # Group by inferred_location
        # Report groups with multiple locations

    def detect_structure_type(self, signal: Signal) -> str:
        """Classify project structure"""
        # Based on detected location, classify as:
        # "tool", "library", "plugin", "scenario", "custom"
```

**Implementation Notes**:

- Always return complete result object (never None)
- Classify as "custom" when uncertain
- Include all signals for debugging
- Make result serializable for logging

### Module 1.4: Fallback Detector

**Purpose**: Provide sensible defaults when no signals found

**Location**: `.claude/tools/structure-detection/fallback_detector.py`

**Interface**:

```python
class FallbackDetector:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.candidates = [
            "tools/",
            "src/",
            "lib/",
            "modules/",
            ".",
        ]

    def detect_fallback(self) -> ProjectStructureDetection:
        """Find best default location"""
        # Try candidates in order
        # Return first that exists and is writable
        # If none work, ask for clarification

    def find_writable_location(self) -> Optional[Path]:
        """Find first writable candidate"""
        # Check each candidate
        # Return first writable one

    def create_ambiguous_result(self) -> ProjectStructureDetection:
        """Return "ambiguous" result when unable to decide"""
        # Set detected_root: None
        # confidence: 0.0
        # Add warning to clarify
```

**Implementation Notes**:

- Try standard locations first
- Check writability explicitly
- Fallback is last resort, not default
- Keep as simple as possible

## Part 2: Workflow Integration

### Integration 2.1: Step 1 Modification

**File**: `.claude/agents/amplihack/specialized/prompt-writer.md`

**Changes**:

```markdown
### Step 1A: Detect Project Structure (NEW)

Before clarifying requirements:

1. Call structure detection on project root
2. Get ProjectStructureDetection result
3. Include in clarification context

### Step 1B: Clarify with Structure Context (MODIFIED)

When clarifying, add:

"Based on analysis of project structure:
- Detected location: {detection.detected_root}
- Detection method: {detection.detection_method}
- Confidence: {detection.confidence}
- Signals found: {summarize_signals(detection.signals)}

{format_warnings(detection.warnings)}"

Ask user:
"Should this artifact be created at {detection.detected_root}?"

### Step 1C: Return Structure Info (NEW)

Pass to next steps:

clarified_requirement.detected_structure = ProjectStructureDetection
clarified_requirement.structure_location = user_confirmed_location or detection.detected_root
```

**Implementation Pattern**:

```python
# In prompt-writer agent execution
def clarify_with_structure(user_requirement, project_root):
    # 1. Detect structure
    detection = detect_project_structure(project_root, user_requirement)

    # 2. Clarify requirement
    clarification = prompt_writer_clarify(user_requirement)

    # 3. Merge structure info
    clarification.detected_structure = detection
    clarification.location_context = format_location_context(detection)

    # 4. Ask about location
    if detection.confidence > 0.7:
        clarification.location_confirmed = ask_user(
            f"Build in {detection.detected_root}?"
        )
    else:
        clarification.location_options = [
            detection.detected_root,
            *[alt.location for alt in detection.alternatives]
        ]

    return clarification
```

### Integration 2.2: Step 4 Modification

**File**: `.claude/agents/amplihack/core/architect.md`

**Changes**:

```markdown
### Step 4A: Read Structure Constraint (NEW)

From clarified requirement, extract:
- detected_structure: ProjectStructureDetection
- required_location: From user confirmation

### Step 4B: Design with Location Constraint (MODIFIED)

When designing solution:

1. Use detected location as primary constraint
2. If confidence low, design for multiple options
3. Document location reasoning in design spec

IMPORTANT: "Where" is as critical as "what"

Design must answer:
- Where should this artifact go?
- Why that location?
- What if location changes?

### Step 4C: Return Location Constraint (NEW)

Pass to implementation:

solution_design.structure_constraint = {
    required_location: detected_structure.detected_root,
    confidence: detected_structure.confidence,
    reasoning: detected_structure.location_reasoning,
    validation_required: True,
    alternatives: [alt.location for alt in detected_structure.alternatives]
}
```

**Implementation Pattern**:

```python
# In architect agent execution
def design_with_structure(clarified_requirement, project_root):
    # 1. Extract structure info
    detection = clarified_requirement.detected_structure
    location = clarified_requirement.structure_location

    # 2. Design solution
    design = architect_design(clarified_requirement)

    # 3. Add location constraint
    design.structure_constraint = {
        required_location: location,
        confidence: detection.confidence,
        reasoning: f"Detected via {detection.detection_method}",
        validation_required: True,
        alternatives: [alt.location for alt in detection.alternatives]
    }

    # 4. If low confidence, explore alternatives
    if detection.confidence < 0.6:
        design.location_options = detection.alternatives
        design.recommendation = "Structure ambiguous - user should confirm"

    return design
```

### Integration 2.3: Step 5 Modification

**File**: `.claude/agents/amplihack/core/builder.md`

**Changes**:

```markdown
### Step 5A: Pre-Build Validation (NEW)

BEFORE creating any files:

1. Extract structure_constraint from design
2. Validate target location
3. If validation fails, ABORT with explanation
4. If validation passes, PROCEED with build

### Step 5B: Validate Target Location (NEW)

Checks:

- Path safety: Inside project boundary
- Location exists: Directory exists or can create
- Writable: Can write files there
- No conflicts: No existing artifacts would be overwritten
- Structure match: Consistent with similar artifacts
- Parent exists: Parent directory exists or writable

### Step 5C: Build at Correct Location (MODIFIED)

After validation passes:

1. Create at required_location
2. Verify files in correct location
3. Report actual location used

NEVER build at different location than validated
```

**Implementation Pattern**:

```python
# In builder agent execution - FIRST THING
def build_solution(solution_design, project_root):
    # 1. Get structure constraint
    constraint = solution_design.structure_constraint
    target_location = constraint.required_location

    # 2. Pre-build validation
    validation = validate_target_location(
        target_location=target_location,
        project_root=project_root,
        design=solution_design
    )

    if not validation.passed:
        raise BuildError(
            reason="Location validation failed",
            issues=validation.failures,
            recommendation=validation.suggestion,
            abort=True
        )

    # 3. Build at validated location
    builder_build(
        solution_design,
        target_directory=target_location,
        create_if_needed=True
    )

    # 4. Verify location
    verify_files_location(target_location, solution_design)
```

## Part 3: Data Flow and Contracts

### Data Flow Through Workflow

```
Step 1: Clarify
├── INPUT: user_requirement: str, project_root: Path
├── ACTION: detect_project_structure(project_root, requirement)
├── OUTPUT: ClarifiedRequirement {
│   user_requirement: str,
│   acceptance_criteria: List[str],
│   detected_structure: ProjectStructureDetection,  ← NEW
│   structure_location: str,  ← NEW
│   ...
└── }

Step 4: Design
├── INPUT: ClarifiedRequirement {
│   detected_structure: ProjectStructureDetection,
│   structure_location: str,
│   ...
├── ACTION: architect_design(clarified_req)
├── OUTPUT: SolutionDesign {
│   architecture: str,
│   modules: List[ModuleSpec],
│   structure_constraint: LocationConstraint,  ← NEW
│   ...
└── }

Step 5: Implement
├── INPUT: SolutionDesign {
│   structure_constraint: LocationConstraint,
│   ...
├── VALIDATE: validate_target_location(constraint.required_location)
├── ACTION: builder_build(design, at_location=constraint.required_location)
├── OUTPUT: ImplementationResult {
│   files_created: List[str],
│   location_used: str,
│   validation_performed: bool,
│   structure_verified: bool,
│   ...
└── }
```

### Contract Definitions

**ClarifiedRequirement Contract**:

```python
@dataclass
class ClarifiedRequirement:
    # Existing fields
    user_requirement: str
    acceptance_criteria: List[str]
    constraints: List[str]
    technical_notes: str

    # NEW: Structure information
    detected_structure: ProjectStructureDetection
    structure_location: str                    # User-confirmed location
    structure_confidence: float                 # Confidence in location
    structure_warnings: List[str]              # Any ambiguities
```

**SolutionDesign Contract**:

```python
@dataclass
class SolutionDesign:
    # Existing fields
    architecture: str
    modules: List[ModuleSpec]
    implementation_plan: str

    # NEW: Location constraint
    structure_constraint: LocationConstraint
    location_reasoning: str                     # Why this location
    location_validated: bool                    # Will be validated
    alternative_locations: List[str]            # If ambiguous
```

**ImplementationResult Contract**:

```python
@dataclass
class ImplementationResult:
    # Existing fields
    files_created: List[str]
    all_tests_passing: bool

    # NEW: Verification
    location_validated: bool                    # Pre-build check passed
    location_used: str                          # Actual location
    structure_verified: bool                    # Files in right place
    validation_errors: List[str]                # If validation failed
```

## Part 4: Integration Checklist

### Phase 1: Core Implementation

- [ ] Create `signal_scanner.py` with all scan methods
  - [ ] `scan_stubs()` - Find .stub.py/.stub.js files
  - [ ] `scan_tests()` - Find test files and extract imports
  - [ ] `scan_conventions()` - Analyze directory patterns
  - [ ] `scan_config()` - Read configuration files
  - [ ] Performance: All scans complete < 100ms

- [ ] Create `priority_engine.py` with ranking
  - [ ] `rank_signals()` - Assign priorities
  - [ ] `compute_consensus()` - Boost confidence
  - [ ] `resolve_conflicts()` - Detect disagreements
  - [ ] Test: Priority order always stub > test > existing > convention > config

- [ ] Create `result_classifier.py` with classification
  - [ ] `classify()` - Main entry point
  - [ ] `select_dominant_signal()` - Pick highest priority
  - [ ] `create_constraint()` - Build actionable constraint
  - [ ] `identify_alternatives()` - Find options
  - [ ] Result always: Complete object, never None

- [ ] Create `fallback_detector.py` for edge cases
  - [ ] `detect_fallback()` - Default locations
  - [ ] Try candidates: tools/, src/, lib/, modules/, .
  - [ ] Create ambiguous result if nothing works

- [ ] Create public API module
  - [ ] `detect_project_structure(project_root, requirement)` → ProjectStructureDetection
  - [ ] Handle all exceptions gracefully
  - [ ] Return complete result always

### Phase 2: Workflow Integration

- [ ] Modify `prompt-writer.md` agent
  - [ ] Call structure detection in Step 1
  - [ ] Include location context in clarification
  - [ ] Ask user to confirm location
  - [ ] Pass detection result to Step 4

- [ ] Modify `architect.md` agent
  - [ ] Read structure constraint from requirement
  - [ ] Include location in design specification
  - [ ] Document location reasoning
  - [ ] Pass constraint to Step 5

- [ ] Modify `builder.md` agent
  - [ ] Extract structure constraint before building
  - [ ] Call validation before ANY file creation
  - [ ] Abort build if validation fails
  - [ ] Create files at validated location only

### Phase 3: Validation and Testing

- [ ] Pre-build validation function
  - [ ] `validate_target_location()` - All checks
  - [ ] Path safety check
  - [ ] Location exists check
  - [ ] Writable check
  - [ ] No conflicts check
  - [ ] Structure match check
  - [ ] Return success/failure with reasons

- [ ] Comprehensive test suite
  - [ ] Unit tests for each component
  - [ ] Integration tests for workflow
  - [ ] Edge case tests
  - [ ] Performance tests (< 100ms)
  - [ ] Data validation tests

- [ ] Documentation
  - [ ] API documentation
  - [ ] Usage examples
  - [ ] Integration guide
  - [ ] Troubleshooting guide

### Phase 4: Agent Updates

- [ ] Update agent descriptions
  - [ ] Document structure detection capability
  - [ ] Note integration points
  - [ ] Update example outputs

- [ ] Update CLAUDE.md
  - [ ] Document structure detection in workflow
  - [ ] Add to Step 1, Step 4, Step 5 descriptions
  - [ ] Explain location validation

- [ ] Update workflow documentation
  - [ ] Document new behavior
  - [ ] Explain structure constraint passing
  - [ ] Add examples

## Part 5: Error Handling

### Common Errors

**Error 1: No signals found**

```python
# In fallback_detector.py
if not signals:
    return {
        detected_root: None,
        detection_method: "ambiguous",
        confidence: 0.0,
        warnings: [
            "No structural signals found",
            "Project structure could not be determined",
            "Requires user clarification"
        ]
    }
    # In Step 1: Ask user "Where should this go?"
```

**Error 2: Conflicting signals**

```python
# In result_classifier.py
if conflicts_detected:
    return {
        detected_root: highest_priority_signal.location,
        confidence: confidence_adjusted_down,
        ambiguity_flags: [
            f"Conflict: {sig1.location} vs {sig2.location}",
            f"Using highest priority: {selected.location}"
        ],
        alternatives: [c.location for c in conflicting]
    }
    # In Step 1: Ask user "Which location is correct?"
```

**Error 3: Location doesn't exist and can't create**

```python
# In validate_target_location()
if not location.exists() and not location.parent.exists():
    return ValidationFailure(
        reason="Cannot create location",
        issue="Parent directory does not exist",
        suggestion="Create parent directory first"
    )
    # In Step 5: Abort build with clear error
```

**Error 4: Permission denied**

```python
# In validate_target_location()
if not os.access(location, os.W_OK):
    return ValidationFailure(
        reason="Permission denied",
        issue=f"Cannot write to {location}",
        suggestion="Check file permissions"
    )
    # In Step 5: Abort build with clear error
```

## Part 6: Testing Template

### Unit Test Template

```python
def test_stub_detection():
    """Test that stubs are detected correctly"""
    project = create_test_project({
        "tools/analyzer.stub.py": "# Stub",
        "tools/optimizer.py": "# Implementation"
    })

    scanner = SignalScanner(project.root)
    signals = scanner.scan_stubs()

    assert len(signals) == 1
    assert signals[0].signal_type == "stub"
    assert signals[0].inferred_location == project.root / "tools"
    assert signals[0].confidence == 0.90

def test_priority_ranking():
    """Test that signals ranked correctly"""
    signals = [
        Signal(signal_type="config", confidence=0.60, ...),
        Signal(signal_type="stub", confidence=0.90, ...),
        Signal(signal_type="test", confidence=0.85, ...),
    ]

    engine = PriorityEngine()
    ranked = engine.rank_signals(signals)

    assert ranked[0].signal_type == "stub"
    assert ranked[1].signal_type == "test"
    assert ranked[2].signal_type == "config"

def test_conflicting_signals():
    """Test conflict detection and reporting"""
    signals = [
        Signal(inferred_location="/tools/", ...),
        Signal(inferred_location="/src/", ...),
    ]

    engine = PriorityEngine()
    conflicts = engine.resolve_conflicts(signals)

    assert len(conflicts) > 0
    assert "conflict" in conflicts[0].lower()
```

### Integration Test Template

```python
def test_workflow_step1_step4_step5():
    """Test full workflow with structure detection"""
    project = create_test_project({
        "tools/analyzer.stub.py": "# Stub",
        "src/main.py": "# Main"
    })

    # Step 1: Clarify
    requirement = "Create analyzer"
    clarified = prompt_writer_clarify(
        requirement,
        project.root,
        with_structure_detection=True
    )

    assert clarified.detected_structure is not None
    assert clarified.structure_location == project.root / "tools"

    # Step 4: Design
    design = architect_design(clarified)

    assert design.structure_constraint.required_location == project.root / "tools"
    assert design.structure_constraint.confidence >= 0.85

    # Step 5: Implement
    validation = validate_target_location(
        design.structure_constraint.required_location,
        project.root
    )

    assert validation.passed

    # Build would happen here
    # Files would be created at correct location
```

## Summary

This implementation guide provides:

1. **Concrete interfaces** for each component
2. **Integration points** for workflow steps
3. **Data flow contracts** between steps
4. **Error handling** for edge cases
5. **Testing templates** for validation
6. **Checklist** for implementation phases

Follow this guide to implement structure detection cleanly and predictably.
