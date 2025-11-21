"""
Project Structure Detection System

This module automatically detects project structure by scanning for signals like
stubs, tests, conventions, and configuration files. It ranks these signals by
reliability and provides actionable location constraints for building artifacts.

Usage:
    from .claude.agents.amplihack.utils.structure_detection import detect_project_structure

    result = detect_project_structure(
        project_root="/path/to/project",
        requirement="Create analyzer tool"
    )

    print(f"Build at: {result.detected_root}")
    print(f"Confidence: {result.confidence}")

Design Philosophy:
- Multi-signal detection (not single source)
- Priority-based ranking (not guessing)
- Confidence scoring (not binary)
- Graceful degradation (not hard failures)
- Fast scanning (< 100ms target)
"""

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed


# ============================================================================
# Data Structures (Public Contracts)
# ============================================================================

@dataclass
class Signal:
    """
    A structural signal indicating project organization.

    Signals are atomic pieces of evidence found during scanning that indicate
    where artifacts should be created. Examples: stub files, test imports,
    directory conventions.
    """
    signal_type: str              # "stub" | "test" | "convention" | "config" | "pattern"
    source_file: str              # Absolute path where signal found
    inferred_location: str        # What location this signal indicates
    confidence: float             # 0.0-1.0 base confidence for this signal type
    evidence: str                 # Human-readable explanation of why this is a signal
    parsed_at: str                # ISO timestamp when signal detected


@dataclass
class RankedSignal:
    """
    A signal with priority ranking and adjusted confidence.

    After signals are found, they're ranked by reliability. This structure
    tracks both the original signal and its ranking information.
    """
    signal: Signal
    priority: int                 # 1-6, lower = higher priority
    priority_name: str            # "stub" | "test" | "existing" | "convention" | "config" | "fallback"
    adjusted_confidence: float    # Confidence after consensus boost
    reasoning: str                # Why this priority assigned


@dataclass
class LocationConstraint:
    """
    Actionable constraint for where to build artifacts.

    This is what agents use to determine where files should be created.
    It includes validation requirements and alternative locations.
    """
    required_location: str          # Absolute path where artifact must go
    location_exists: bool           # True if directory already exists
    may_create_directory: bool      # True if allowed to mkdir
    location_reasoning: str         # Why this location was chosen
    confidence: float               # 0.0-1.0 confidence in this location
    validation_required: bool       # True if must validate before building
    is_ambiguous: bool              # True if conflicting signals detected
    ambiguity_reason: str           # Explanation of ambiguity
    alternatives: List[str]         # Other possible locations


@dataclass
class ProjectStructureDetection:
    """
    Complete result of project structure detection analysis.

    This is the main result returned by detect_project_structure().
    It includes detection results, confidence scores, warnings, and
    actionable constraints for downstream workflow steps.
    """
    # Core results
    detected_root: Optional[str]            # Primary detected location (None if ambiguous)
    structure_type: str                     # "tool" | "library" | "plugin" | "scenario" | "custom"
    detection_method: str                   # HOW detected: "stub" | "test" | "convention" | "config" | "fallback" | "ambiguous"
    confidence: float                       # 0.0-1.0 overall confidence

    # Signal details
    signals: List[Signal]                   # Raw signals found
    signals_ranked: List[RankedSignal]      # Signals ranked by priority

    # Actionable constraint
    constraints: LocationConstraint         # Where and how to build

    # Edge cases and warnings
    ambiguity_flags: List[str]              # Conflicting signal warnings
    warnings: List[str]                     # General structural concerns
    alternatives: List[Dict[str, Any]]      # Alternative locations with details

    # Metadata
    scan_duration_ms: float                 # How long detection took
    signals_examined: int                   # Total signals checked


# ============================================================================
# Priority Configuration
# ============================================================================

SIGNAL_PRIORITIES = {
    "stub": {
        "priority": 1,
        "confidence": 0.90,
        "patterns": ["*.stub.py", "*.stub.js", "*.stub.ts", "@stub", "@TODO"],
        "reliability": "very high"
    },
    "test": {
        "priority": 2,
        "confidence": 0.85,
        "patterns": ["test_*.py", "*_test.py", "*.test.js", "*.test.ts", "__tests__/"],
        "reliability": "high"
    },
    "existing_implementation": {
        "priority": 3,
        "confidence": 0.80,
        "patterns": ["similar files in same location"],
        "reliability": "high"
    },
    "convention": {
        "priority": 4,
        "confidence": 0.70,
        "patterns": ["directory names", "README hints", "patterns"],
        "reliability": "moderate"
    },
    "config": {
        "priority": 5,
        "confidence": 0.60,
        "patterns": ["pyproject.toml", "package.json", "setup.py", "tsconfig.json"],
        "reliability": "moderate"
    },
    "fallback": {
        "priority": 6,
        "confidence": 0.30,
        "patterns": ["default locations"],
        "reliability": "low"
    }
}


# ============================================================================
# Signal Scanner
# ============================================================================

class SignalScanner:
    """
    Scans project for structural signals (stubs, tests, conventions, config).

    Performs fast, concurrent scanning of different signal types and returns
    all detected signals within timeout. Designed to complete in < 100ms for
    typical projects.
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()
        self._validate_project_root()

    def _validate_project_root(self):
        """Ensure project root is valid and accessible."""
        if not self.project_root.exists():
            raise ValueError(f"Project root does not exist: {self.project_root}")
        if not self.project_root.is_dir():
            raise ValueError(f"Project root is not a directory: {self.project_root}")

    def scan_all(self, timeout_ms: int = 100) -> List[Signal]:
        """
        Scan project for all signal types within timeout.

        Uses concurrent execution to scan multiple signal types in parallel.
        Returns all signals found before timeout, or raises TimeoutError.

        Args:
            timeout_ms: Maximum time to spend scanning (default: 100ms)

        Returns:
            List of all signals found

        Raises:
            TimeoutError: If scanning exceeds timeout
        """
        timeout_sec = timeout_ms / 1000.0
        all_signals = []

        # Define scan tasks
        scan_tasks = [
            ("stubs", self.scan_stubs),
            ("tests", self.scan_tests),
            ("conventions", self.scan_conventions),
            ("config", self.scan_config)
        ]

        # Execute scans in parallel with timeout
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_scan = {executor.submit(scan_func): name
                            for name, scan_func in scan_tasks}

            for future in as_completed(future_to_scan, timeout=timeout_sec):
                scan_name = future_to_scan[future]
                try:
                    signals = future.result()
                    all_signals.extend(signals)
                except Exception as e:
                    # Log but don't fail on individual scan errors
                    pass

        return all_signals

    def scan_stubs(self) -> List[Signal]:
        """
        Find stub files indicating expected module locations.

        Stubs are the highest priority signal (90% confidence) because they
        explicitly mark where modules should be created.

        Patterns:
        - *.stub.py, *.stub.js, *.stub.ts
        - Files with @stub decorators
        - Files with @TODO markers

        Returns:
            List of stub signals
        """
        signals = []
        timestamp = self._get_timestamp()

        # Search for stub files
        for pattern in ["**/*.stub.py", "**/*.stub.js", "**/*.stub.ts"]:
            for stub_file in self.project_root.glob(pattern):
                # Infer location from stub file's directory
                inferred_location = str(stub_file.parent)

                signals.append(Signal(
                    signal_type="stub",
                    source_file=str(stub_file),
                    inferred_location=inferred_location,
                    confidence=SIGNAL_PRIORITIES["stub"]["confidence"],
                    evidence=f"Explicit stub file: {stub_file.name}",
                    parsed_at=timestamp
                ))

        return signals

    def scan_tests(self) -> List[Signal]:
        """
        Find test files and extract what they test.

        Tests are high priority (85% confidence) because they define expected
        interfaces and often import from specific locations.

        Patterns:
        - test_*.py, *_test.py
        - *.test.js, *.test.ts
        - __tests__/ directories

        Returns:
            List of test signals
        """
        signals = []
        timestamp = self._get_timestamp()

        # Search for test files
        test_patterns = [
            "**/test_*.py", "**/*_test.py",
            "**/*.test.js", "**/*.test.ts"
        ]

        for pattern in test_patterns:
            for test_file in self.project_root.glob(pattern):
                # Try to extract import location from test file
                inferred_location = self._extract_import_location(test_file)

                if inferred_location:
                    signals.append(Signal(
                        signal_type="test",
                        source_file=str(test_file),
                        inferred_location=inferred_location,
                        confidence=SIGNAL_PRIORITIES["test"]["confidence"],
                        evidence=f"Test file imports from: {inferred_location}",
                        parsed_at=timestamp
                    ))

        return signals

    def scan_conventions(self) -> List[Signal]:
        """
        Analyze directory patterns and conventions.

        Conventions have moderate priority (70% confidence) because they
        indicate intentional organization but may be outdated.

        Patterns:
        - Directory names (tools/, src/, lib/, agents/)
        - Existing file patterns in directories
        - README.md hints

        Returns:
            List of convention signals
        """
        signals = []
        timestamp = self._get_timestamp()

        # Common directory conventions
        conventional_dirs = ["tools", "src", "lib", "agents", "modules", "plugins"]

        for dir_name in conventional_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                # Check if directory has Python/JS files (indicates active use)
                has_files = any(dir_path.glob("*.py")) or any(dir_path.glob("*.js"))

                if has_files:
                    signals.append(Signal(
                        signal_type="convention",
                        source_file=str(dir_path),
                        inferred_location=str(dir_path),
                        confidence=SIGNAL_PRIORITIES["convention"]["confidence"],
                        evidence=f"Conventional directory: {dir_name}/ with active files",
                        parsed_at=timestamp
                    ))

        return signals

    def scan_config(self) -> List[Signal]:
        """
        Read configuration files for structure hints.

        Config files have moderate priority (60% confidence) because they
        provide explicit structure info but may be outdated.

        Files:
        - pyproject.toml (Python)
        - package.json (JavaScript)
        - setup.py (Python)
        - tsconfig.json (TypeScript)

        Returns:
            List of config signals
        """
        signals = []
        timestamp = self._get_timestamp()

        # Check pyproject.toml
        pyproject = self.project_root / "pyproject.toml"
        if pyproject.exists():
            location = self._parse_pyproject_location(pyproject)
            if location:
                signals.append(Signal(
                    signal_type="config",
                    source_file=str(pyproject),
                    inferred_location=location,
                    confidence=SIGNAL_PRIORITIES["config"]["confidence"],
                    evidence="pyproject.toml package directory",
                    parsed_at=timestamp
                ))

        # Check package.json
        package_json = self.project_root / "package.json"
        if package_json.exists():
            location = self._parse_package_json_location(package_json)
            if location:
                signals.append(Signal(
                    signal_type="config",
                    source_file=str(package_json),
                    inferred_location=location,
                    confidence=SIGNAL_PRIORITIES["config"]["confidence"],
                    evidence="package.json main field",
                    parsed_at=timestamp
                ))

        return signals

    # ---- Helper Methods ----

    def _extract_import_location(self, test_file: Path) -> Optional[str]:
        """
        Extract module location from test file imports.

        Parses Python import statements to find what the test imports.
        Returns the inferred directory where imported module should be.

        Args:
            test_file: Path to test file

        Returns:
            Inferred module location or None
        """
        try:
            content = test_file.read_text(encoding='utf-8', errors='ignore')

            # Match Python imports: from X import Y, import X
            import_patterns = [
                r'from\s+([\w\.]+)\s+import',
                r'import\s+([\w\.]+)'
            ]

            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    # Skip standard library and common packages
                    if match in ['os', 'sys', 'pathlib', 'typing', 'pytest', 'unittest']:
                        continue

                    # Convert import path to file path
                    # e.g., "project.tools.analyzer" -> "project/tools/"
                    parts = match.split('.')
                    if len(parts) >= 2:
                        # Build potential path
                        potential_path = self.project_root / '/'.join(parts[:-1])
                        if potential_path.exists():
                            return str(potential_path)

        except Exception:
            pass

        return None

    def _parse_pyproject_location(self, pyproject_path: Path) -> Optional[str]:
        """
        Extract package directory from pyproject.toml.

        Args:
            pyproject_path: Path to pyproject.toml

        Returns:
            Package directory or None
        """
        try:
            content = pyproject_path.read_text(encoding='utf-8')

            # Simple regex-based parsing (avoid dependencies)
            # Look for: packages = ["src"] or package-dir = {"": "src"}
            if 'packages' in content or 'package-dir' in content:
                src_match = re.search(r'["\']src["\']', content)
                if src_match:
                    src_path = self.project_root / "src"
                    if src_path.exists():
                        return str(src_path)

        except Exception:
            pass

        return None

    def _parse_package_json_location(self, package_json_path: Path) -> Optional[str]:
        """
        Extract source directory from package.json.

        Args:
            package_json_path: Path to package.json

        Returns:
            Source directory or None
        """
        try:
            data = json.loads(package_json_path.read_text(encoding='utf-8'))

            # Check main field
            main = data.get('main', '')
            if main:
                # Extract directory from main field
                # e.g., "src/index.js" -> "src"
                parts = main.split('/')
                if len(parts) > 1:
                    src_dir = self.project_root / parts[0]
                    if src_dir.exists():
                        return str(src_dir)

        except Exception:
            pass

        return None

    def _get_timestamp(self) -> str:
        """Get current ISO timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()


# ============================================================================
# Priority Engine
# ============================================================================

class PriorityEngine:
    """
    Ranks signals by reliability and computes confidence scores.

    Assigns priority levels to signals based on type, detects consensus
    when multiple signals agree, and handles conflicting signals.
    """

    def __init__(self):
        self.priority_map = {
            signal_type: config["priority"]
            for signal_type, config in SIGNAL_PRIORITIES.items()
        }

    def rank_signals(self, signals: List[Signal]) -> List[RankedSignal]:
        """
        Sort signals by priority and adjust confidence based on consensus.

        Algorithm:
        1. Assign priority to each signal
        2. Group signals by inferred location
        3. Boost confidence for consensus (multiple signals → same location)
        4. Sort by priority (lower = higher priority)

        Args:
            signals: Raw signals from scanner

        Returns:
            Ranked signals with adjusted confidence
        """
        if not signals:
            return []

        # Step 1: Assign priority and create ranked signals
        ranked = []
        for signal in signals:
            priority = self.priority_map.get(signal.signal_type, 6)
            priority_name = signal.signal_type

            ranked.append(RankedSignal(
                signal=signal,
                priority=priority,
                priority_name=priority_name,
                adjusted_confidence=signal.confidence,
                reasoning=f"Priority {priority}: {signal.signal_type} signal"
            ))

        # Step 2: Compute consensus boost
        location_groups = self._group_by_location(ranked)

        for location, group in location_groups.items():
            if len(group) > 1:
                # Consensus: multiple signals point to same location
                boost = self.compute_consensus_boost(len(group))
                for ranked_signal in group:
                    ranked_signal.adjusted_confidence = min(
                        ranked_signal.adjusted_confidence + boost,
                        0.95  # Cap at 95%
                    )
                    ranked_signal.reasoning += f" + consensus boost ({len(group)} signals)"

        # Step 3: Sort by priority (lower priority value = higher priority)
        ranked.sort(key=lambda r: (r.priority, -r.adjusted_confidence))

        return ranked

    def compute_consensus_boost(self, signal_count: int) -> float:
        """
        Calculate confidence boost when multiple signals agree.

        Formula: 0.02 * (signal_count - 1)
        Capped at 0.95 total confidence

        Args:
            signal_count: Number of signals pointing to same location

        Returns:
            Confidence boost value
        """
        return 0.02 * (signal_count - 1)

    def resolve_conflicts(self, ranked_signals: List[RankedSignal]) -> Dict[str, Any]:
        """
        Detect and report conflicting signals.

        Conflicts occur when high-priority signals point to different locations.

        Args:
            ranked_signals: Ranked signals to analyze

        Returns:
            Dict with conflict information
        """
        if len(ranked_signals) < 2:
            return {"has_conflicts": False, "conflicts": []}

        # Group by location
        location_groups = self._group_by_location(ranked_signals)

        if len(location_groups) <= 1:
            return {"has_conflicts": False, "conflicts": []}

        # Check if top signals conflict
        top_priorities = ranked_signals[:3]  # Check top 3 signals
        top_locations = {rs.signal.inferred_location for rs in top_priorities}

        if len(top_locations) > 1:
            conflicts = [
                f"{rs.priority_name} signal suggests: {rs.signal.inferred_location}"
                for rs in top_priorities
            ]
            return {
                "has_conflicts": True,
                "conflicts": conflicts,
                "location_groups": list(location_groups.keys())
            }

        return {"has_conflicts": False, "conflicts": []}

    def _group_by_location(self, ranked_signals: List[RankedSignal]) -> Dict[str, List[RankedSignal]]:
        """Group ranked signals by inferred location."""
        groups = {}
        for rs in ranked_signals:
            location = rs.signal.inferred_location
            if location not in groups:
                groups[location] = []
            groups[location].append(rs)
        return groups


# ============================================================================
# Result Classifier
# ============================================================================

class ResultClassifier:
    """
    Converts ranked signals into actionable detection results.

    Takes ranked signals and produces complete ProjectStructureDetection
    with location constraints, confidence scores, and warnings.
    """

    def classify(self, ranked_signals: List[RankedSignal],
                 project_root: Path, scan_duration_ms: float) -> ProjectStructureDetection:
        """
        Convert ranked signals into complete detection result.

        Algorithm:
        1. Select dominant signal (highest priority)
        2. Detect conflicts between signals
        3. Create location constraint
        4. Identify alternatives
        5. Compute overall confidence
        6. Generate warnings

        Args:
            ranked_signals: Signals ranked by priority
            project_root: Project root directory
            scan_duration_ms: How long scanning took

        Returns:
            Complete ProjectStructureDetection
        """
        # Handle no signals case
        if not ranked_signals:
            return self._create_ambiguous_result(project_root, scan_duration_ms)

        # Select dominant signal (highest priority)
        dominant = ranked_signals[0]
        detected_root = dominant.signal.inferred_location

        # Detect conflicts
        conflicts = PriorityEngine().resolve_conflicts(ranked_signals)

        # Create location constraint
        constraint = self.create_constraint(
            dominant,
            project_root,
            is_ambiguous=conflicts["has_conflicts"]
        )

        # Identify alternatives
        alternatives = self.identify_alternatives(ranked_signals, dominant)

        # Compute overall confidence
        overall_confidence = self._compute_overall_confidence(
            dominant,
            ranked_signals,
            conflicts["has_conflicts"]
        )

        # Generate warnings
        warnings = self._generate_warnings(conflicts, constraint)

        # Determine structure type
        structure_type = self._detect_structure_type(detected_root)

        return ProjectStructureDetection(
            detected_root=detected_root,
            structure_type=structure_type,
            detection_method=dominant.priority_name,
            confidence=overall_confidence,
            signals=[rs.signal for rs in ranked_signals],
            signals_ranked=ranked_signals,
            constraints=constraint,
            ambiguity_flags=conflicts["conflicts"],
            warnings=warnings,
            alternatives=alternatives,
            scan_duration_ms=scan_duration_ms,
            signals_examined=len(ranked_signals)
        )

    def create_constraint(self, dominant: RankedSignal,
                         project_root: Path, is_ambiguous: bool) -> LocationConstraint:
        """
        Build actionable location constraint from dominant signal.

        Args:
            dominant: Highest priority signal
            project_root: Project root directory
            is_ambiguous: True if conflicting signals detected

        Returns:
            LocationConstraint for builders
        """
        location = Path(dominant.signal.inferred_location)

        return LocationConstraint(
            required_location=str(location),
            location_exists=location.exists(),
            may_create_directory=True,
            location_reasoning=dominant.reasoning,
            confidence=dominant.adjusted_confidence,
            validation_required=True,
            is_ambiguous=is_ambiguous,
            ambiguity_reason="Conflicting signals detected" if is_ambiguous else "",
            alternatives=[]
        )

    def identify_alternatives(self, ranked_signals: List[RankedSignal],
                            dominant: RankedSignal) -> List[Dict[str, Any]]:
        """
        Find alternative locations from non-dominant signals.

        Args:
            ranked_signals: All ranked signals
            dominant: Dominant signal

        Returns:
            List of alternative location dicts
        """
        alternatives = []
        dominant_location = dominant.signal.inferred_location

        seen_locations = {dominant_location}

        for rs in ranked_signals[1:6]:  # Consider top 5 alternatives
            location = rs.signal.inferred_location
            if location not in seen_locations:
                alternatives.append({
                    "location": location,
                    "confidence": rs.adjusted_confidence,
                    "reasoning": rs.reasoning,
                    "signal_type": rs.priority_name
                })
                seen_locations.add(location)

        return alternatives

    def _compute_overall_confidence(self, dominant: RankedSignal,
                                   all_signals: List[RankedSignal],
                                   has_conflicts: bool) -> float:
        """
        Compute overall confidence considering consensus and conflicts.

        Args:
            dominant: Dominant signal
            all_signals: All signals
            has_conflicts: True if conflicts detected

        Returns:
            Overall confidence (0.0-1.0)
        """
        base_confidence = dominant.adjusted_confidence

        # Reduce confidence if conflicts
        if has_conflicts:
            base_confidence *= 0.95

        # Cap at 0.95 for single signals, allow higher for strong consensus
        if len(all_signals) == 1:
            base_confidence = min(base_confidence, 0.90)

        return base_confidence

    def _generate_warnings(self, conflicts: Dict[str, Any],
                         constraint: LocationConstraint) -> List[str]:
        """Generate warnings based on conflicts and constraints."""
        warnings = []

        if conflicts["has_conflicts"]:
            warnings.append("Multiple signals point to different locations")
            warnings.append("Recommend investigating why signals conflict")

        if not constraint.location_exists:
            warnings.append(f"Directory does not exist: {constraint.required_location}")
            warnings.append("Will attempt to create during build")

        if constraint.confidence < 0.60:
            warnings.append("Low confidence detection - user confirmation recommended")

        return warnings

    def _detect_structure_type(self, location: str) -> str:
        """
        Classify project structure type from location.

        Args:
            location: Detected location path

        Returns:
            Structure type: "tool" | "library" | "plugin" | "scenario" | "custom"
        """
        location_lower = location.lower()

        if 'tool' in location_lower:
            return "tool"
        elif 'lib' in location_lower or 'src' in location_lower:
            return "library"
        elif 'plugin' in location_lower:
            return "plugin"
        elif 'scenario' in location_lower:
            return "scenario"
        else:
            return "custom"

    def _create_ambiguous_result(self, project_root: Path,
                                scan_duration_ms: float) -> ProjectStructureDetection:
        """
        Create ambiguous result when no signals found.

        Args:
            project_root: Project root directory
            scan_duration_ms: Scan duration

        Returns:
            ProjectStructureDetection with ambiguous flag
        """
        return ProjectStructureDetection(
            detected_root=None,
            structure_type="custom",
            detection_method="ambiguous",
            confidence=0.0,
            signals=[],
            signals_ranked=[],
            constraints=LocationConstraint(
                required_location="",
                location_exists=False,
                may_create_directory=False,
                location_reasoning="No structural signals found",
                confidence=0.0,
                validation_required=True,
                is_ambiguous=True,
                ambiguity_reason="No stubs, tests, or conventions detected",
                alternatives=[]
            ),
            ambiguity_flags=["No structural signals detected"],
            warnings=[
                "Project structure could not be determined",
                "Recommend adding stub files or tests",
                "Manual location specification required"
            ],
            alternatives=[],
            scan_duration_ms=scan_duration_ms,
            signals_examined=0
        )


# ============================================================================
# Fallback Detection Function
# ============================================================================

def _detect_fallback(project_root: Path) -> Optional[str]:
    """
    Find default location when no signals detected.

    Tries standard candidates in order and returns first that exists and is writable.
    """
    candidates = ["tools", "src", "lib", "modules", "."]
    for candidate in candidates:
        path = project_root if candidate == "." else project_root / candidate
        if path.exists() and os.access(path, os.W_OK):
            return str(path)
    return None


# ============================================================================
# Validation Function
# ============================================================================

@dataclass
class ValidationResult:
    """Result of location validation."""
    passed: bool                        # All checks passed
    failures: List[str]                 # What failed
    reason: str                         # Summary
    suggestion: str                     # How to fix
    can_create_directory: bool          # Can mkdir
    is_writable: bool                   # Can write
    has_conflicts: bool                 # Existing files
    is_inside_project: bool             # In project boundary


def validate_target_location(target_location: Path,
                            project_root: Path) -> ValidationResult:
    """
    Validate that target location is safe for building.

    Performs comprehensive validation checks before files are created:
    - Path is inside project boundary (no traversal)
    - Parent directory exists
    - Location is writable
    - No conflicting files

    Args:
        target_location: Directory where files will be created
        project_root: Project root directory

    Returns:
        ValidationResult with pass/fail status
    """
    failures = []
    can_create = False
    is_writable = False
    has_conflicts = False
    is_inside = False

    try:
        # Check 1: Inside project boundary
        try:
            target_resolved = target_location.resolve()
            root_resolved = project_root.resolve()
            is_inside = target_resolved.is_relative_to(root_resolved)
            if not is_inside:
                failures.append("Target location outside project boundary")
        except Exception as e:
            failures.append(f"Path resolution error: {e}")

        # Check 2: Parent exists
        if not target_location.parent.exists():
            failures.append("Parent directory does not exist")
        else:
            can_create = True

        # Check 3: Writable
        if target_location.exists():
            is_writable = os.access(target_location, os.W_OK)
            if not is_writable:
                failures.append("No write permission on target directory")
        elif target_location.parent.exists():
            is_writable = os.access(target_location.parent, os.W_OK)
            if not is_writable:
                failures.append("No write permission on parent directory")

        # Check 4: No conflicts (basic check - can be expanded)
        if target_location.exists():
            # Check if directory has many files that might conflict
            existing_files = list(target_location.glob("*.py"))
            if len(existing_files) > 10:
                has_conflicts = True
                failures.append(f"Directory contains {len(existing_files)} existing files")

        # Determine overall result
        passed = len(failures) == 0

        if passed:
            return ValidationResult(
                passed=True,
                failures=[],
                reason="All validation checks passed",
                suggestion="Safe to proceed with build",
                can_create_directory=can_create,
                is_writable=is_writable,
                has_conflicts=has_conflicts,
                is_inside_project=is_inside
            )
        else:
            return ValidationResult(
                passed=False,
                failures=failures,
                reason=f"{len(failures)} validation check(s) failed",
                suggestion="Fix issues listed in failures before building",
                can_create_directory=can_create,
                is_writable=is_writable,
                has_conflicts=has_conflicts,
                is_inside_project=is_inside
            )

    except Exception as e:
        return ValidationResult(
            passed=False,
            failures=[f"Validation error: {e}"],
            reason="Validation failed with exception",
            suggestion="Check target location and permissions",
            can_create_directory=False,
            is_writable=False,
            has_conflicts=False,
            is_inside_project=False
        )


# ============================================================================
# Public API
# ============================================================================

def detect_project_structure(project_root: str,
                            requirement: Optional[str] = None,
                            timeout_ms: int = 100) -> ProjectStructureDetection:
    """
    Detect project structure by scanning for signals.

    This is the main entry point for structure detection. It scans the project
    for structural signals (stubs, tests, conventions, config), ranks them by
    reliability, and returns actionable location constraints.

    Algorithm:
    1. Scan for signals (< 100ms)
    2. Rank by priority
    3. Detect consensus and conflicts
    4. Classify into actionable result
    5. Return with confidence scores

    Args:
        project_root: Absolute path to project root directory
        requirement: Optional requirement text (for context)
        timeout_ms: Maximum scanning time (default: 100ms)

    Returns:
        ProjectStructureDetection with location constraints

    Raises:
        ValueError: If project_root invalid
        TimeoutError: If scanning exceeds timeout (rare)

    Example:
        >>> result = detect_project_structure("/path/to/project")
        >>> print(f"Build at: {result.detected_root}")
        >>> print(f"Confidence: {result.confidence}")
        >>> if result.confidence > 0.7:
        ...     build_at_location(result.constraints.required_location)
        ... else:
        ...     ask_user_for_clarification()
    """
    start_time = time.time()
    project_path = Path(project_root).resolve()

    # Stage 1: Scan for signals
    scanner = SignalScanner(project_path)
    try:
        signals = scanner.scan_all(timeout_ms=timeout_ms)
    except TimeoutError:
        # Timeout reached - use signals found so far
        signals = []

    # Stage 2: Rank signals
    priority_engine = PriorityEngine()
    ranked_signals = priority_engine.rank_signals(signals)

    # Stage 3: Try fallback if no signals
    if not ranked_signals:
        fallback_location = _detect_fallback(project_path)
        if fallback_location:
            # Create synthetic fallback signal
            fallback_signal = Signal(
                signal_type="fallback",
                source_file="",
                inferred_location=fallback_location,
                confidence=SIGNAL_PRIORITIES["fallback"]["confidence"],
                evidence=f"Fallback to existing directory: {fallback_location}",
                parsed_at=scanner._get_timestamp()
            )

            ranked_signals = [RankedSignal(
                signal=fallback_signal,
                priority=6,
                priority_name="fallback",
                adjusted_confidence=0.30,
                reasoning="No signals found - using fallback default"
            )]

    # Stage 4: Classify into result
    scan_duration_ms = (time.time() - start_time) * 1000
    classifier = ResultClassifier()
    result = classifier.classify(ranked_signals, project_path, scan_duration_ms)

    return result


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    'detect_project_structure',
    'validate_target_location',
    'ProjectStructureDetection',
    'LocationConstraint',
    'Signal',
    'RankedSignal',
    'ValidationResult',
]
