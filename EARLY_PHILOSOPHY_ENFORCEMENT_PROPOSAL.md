# Early Philosophy Enforcement System

**Purpose:** Prevent YAGNI violations, complexity creep, and philosophy drift BEFORE code is written, not after.

**Lesson Learned:** The Goal-Seeking Agent Generator audit found 86% speculative code that could have been prevented with earlier checks.

---

## THE PROBLEM

**Current State:**
- Philosophy checks happen at **review time** (too late)
- Agent implements → Human reviews → Finds violations → Refactor/delete
- Wasted effort on code that shouldn't exist

**What Happened:**
1. Builder agents implemented Phases 2-4 without validation
2. All code passed Zero-BS checks (no stubs, real implementations)
3. Zen-architect reviewed AFTER implementation
4. Found 7,309 lines of speculative code (86% of codebase)
5. **Net Result:** High-quality code solving imaginary problems

**Root Cause:** Philosophy checks too late in cycle.

---

## SOLUTION: MULTI-LAYER PHILOSOPHY ENFORCEMENT

### Layer 1: Pre-Implementation Validation (PREVENTIVE)

**When:** Before any code is written
**Who:** Architect agent + Zen-architect agent (in parallel)
**What:** Validate necessity before design

#### Implementation

Add to **Step 4 (Research and Design)** of DEFAULT_WORKFLOW.md:

```markdown
## Step 4: Research and Design

**PHILOSOPHY CHECKPOINT 1: Necessity Validation**

Before designing ANY new feature:

1. **Invoke zen-architect with Necessity Questionnaire:**
   - Do we have evidence this problem exists? (user reports, data, failures)
   - Have we validated simpler solutions are insufficient?
   - What's the cost of building this now vs. waiting?
   - What's the risk of NOT building this now?
   - Is this solving today's problem or tomorrow's speculation?

2. **Zen-architect must approve with one of:**
   - ✅ APPROVED - Clear evidence of need
   - ⚠️ CONDITIONAL - Build minimal MVP, validate before expanding
   - ❌ REJECTED - Premature, wait for data
   - 🔄 DEFER - Good idea, not now

3. **If REJECTED or DEFER:**
   - Document in `.claude/runtime/deferred_features.md`
   - Continue with validated work only
   - DO NOT implement

4. **If CONDITIONAL:**
   - Define validation criteria (e.g., "After 20 users report skill gaps")
   - Build absolute minimum
   - Add feature flag (disabled by default)
   - Document validation plan

Only proceed to design if APPROVED or CONDITIONAL (with minimal scope).
```

#### Example Application

**What Should Have Happened with Phases 2-4:**

```
Designer: I'm designing Phase 2 (AI Skill Generation)

Zen-Architect Questionnaire:
- Evidence of need? NO - No user reports of skill gaps
- Simpler solutions tried? NO - Phase 1 not deployed to users yet
- Cost of waiting? ZERO - Can build later if needed
- Risk of NOT building? NONE - Can generate from prompt anytime
- Solving today or tomorrow? TOMORROW (speculative)

VERDICT: ❌ REJECTED - Premature

Action: Document in deferred_features.md, focus on Phase 1 excellence
```

---

### Layer 2: Design-Time Complexity Checks (CORRECTIVE)

**When:** During architecture/design phase
**Who:** Architect agent with complexity metrics
**What:** Measure and cap complexity before implementation

#### Complexity Metrics

```python
# .claude/tools/amplihack/philosophy/complexity_checker.py

class ComplexityChecker:
    """Checks design specs against complexity thresholds."""

    THRESHOLDS = {
        "max_modules_per_feature": 5,      # More = over-engineering
        "max_dependencies_per_module": 3,   # More = tight coupling
        "max_lines_per_module": 300,        # More = god object
        "max_abstraction_layers": 3,        # More = architecture astronaut
    }

    def check_design(self, spec: FeatureSpec) -> DesignApproval:
        """Check design against complexity thresholds."""
        violations = []

        # Check module count
        if len(spec.modules) > self.THRESHOLDS["max_modules_per_feature"]:
            violations.append(
                f"Too many modules: {len(spec.modules)} > {self.THRESHOLDS['max_modules_per_feature']}"
                f"\nQuestion: Can this be simplified? Each module adds maintenance cost."
            )

        # Check dependencies
        for module in spec.modules:
            if len(module.dependencies) > self.THRESHOLDS["max_dependencies_per_module"]:
                violations.append(
                    f"{module.name} has {len(module.dependencies)} dependencies"
                    f"\nQuestion: Why does this module need so many dependencies?"
                )

        # Check estimated lines
        for module in spec.modules:
            if module.estimated_lines > self.THRESHOLDS["max_lines_per_module"]:
                violations.append(
                    f"{module.name} estimated at {module.estimated_lines} lines"
                    f"\nQuestion: Can this be split into smaller modules?"
                )

        if violations:
            return DesignApproval(
                approved=False,
                violations=violations,
                recommendation="Simplify design before implementation"
            )

        return DesignApproval(approved=True)
```

#### Integration Point

Add to architect agent instructions:

```markdown
After creating design specification, MUST:

1. Run ComplexityChecker.check_design(spec)
2. If violations found:
   - Question each violation with user
   - Simplify design OR
   - Document why complexity justified
3. Only proceed with approved design
```

---

### Layer 3: Implementation-Time AST Analysis (DETECTIVE)

**When:** During code writing (pre-commit hook)
**Who:** Automated tools
**What:** Static analysis for philosophy violations

#### Pre-Commit Hook: Philosophy Validator

```python
# .claude/tools/amplihack/philosophy/ast_validator.py

import ast
from pathlib import Path
from typing import List, Tuple

class PhilosophyValidator:
    """AST-based philosophy compliance checker."""

    def validate_file(self, file_path: Path) -> List[str]:
        """Check Python file for philosophy violations."""
        issues = []

        with open(file_path) as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        # Check 1: No TODO/FIXME in code
        issues.extend(self._check_no_todos(tree, file_path))

        # Check 2: No NotImplementedError
        issues.extend(self._check_no_stubs(tree, file_path))

        # Check 3: No pass-only functions
        issues.extend(self._check_no_empty_functions(tree, file_path))

        # Check 4: No mocks outside tests/
        if "/tests/" not in str(file_path):
            issues.extend(self._check_no_mocks(tree, file_path))

        # Check 5: Complexity limits
        issues.extend(self._check_complexity(tree, file_path))

        return issues

    def _check_no_todos(self, tree, file_path):
        """Find TODO/FIXME comments."""
        issues = []
        source = Path(file_path).read_text()

        for lineno, line in enumerate(source.split('\n'), 1):
            if any(marker in line for marker in ['TODO', 'FIXME', 'XXX', 'HACK']):
                # Ignore if in string literals or test files
                if 'test_' not in str(file_path) and not line.strip().startswith('#'):
                    issues.append(
                        f"{file_path}:{lineno} - Found action item comment: {line.strip()}"
                        f"\n  Violation: Zero-BS principle requires all action items resolved"
                    )

        return issues

    def _check_no_stubs(self, tree, file_path):
        """Find NotImplementedError usage."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Raise):
                if isinstance(node.exc, ast.Call):
                    if isinstance(node.exc.func, ast.Name):
                        if node.exc.func.id == "NotImplementedError":
                            issues.append(
                                f"{file_path}:{node.lineno} - NotImplementedError found"
                                f"\n  Violation: Zero-BS requires complete implementations"
                            )

        return issues

    def _check_no_empty_functions(self, tree, file_path):
        """Find functions with only pass or docstring."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                body = node.body
                # Skip docstring
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                    body = body[1:]

                # Check if only pass statement
                if len(body) == 1 and isinstance(body[0], ast.Pass):
                    issues.append(
                        f"{file_path}:{node.lineno} - Empty function: {node.name}()"
                        f"\n  Violation: Zero-BS requires working implementations"
                    )

        return issues

    def _check_no_mocks(self, tree, file_path):
        """Find mock/fake implementations in production code."""
        issues = []

        for node in ast.walk(tree):
            # Check for mock imports
            if isinstance(node, ast.ImportFrom):
                if node.module and 'mock' in node.module.lower():
                    issues.append(
                        f"{file_path}:{node.lineno} - Mock import in production code"
                        f"\n  Violation: No fake implementations outside tests"
                    )

            # Check for fake data patterns
            if isinstance(node, ast.Assign):
                # Look for variables named 'fake_*' or 'mock_*'
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id.startswith(('fake_', 'mock_', 'dummy_', 'stub_')):
                            issues.append(
                                f"{file_path}:{node.lineno} - Fake data variable: {target.id}"
                                f"\n  Violation: Real data only in production code"
                            )

        return issues

    def _check_complexity(self, tree, file_path):
        """Check cyclomatic complexity and nesting depth."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Calculate cyclomatic complexity
                complexity = self._calculate_complexity(node)
                if complexity > 10:
                    issues.append(
                        f"{file_path}:{node.lineno} - High complexity: {node.name}() = {complexity}"
                        f"\n  Violation: Ruthless simplicity requires complexity < 10"
                    )

                # Calculate nesting depth
                depth = self._calculate_nesting_depth(node)
                if depth > 4:
                    issues.append(
                        f"{file_path}:{node.lineno} - Deep nesting: {node.name}() = {depth} levels"
                        f"\n  Violation: Ruthless simplicity requires max 4 levels"
                    )

        return issues

    def _calculate_complexity(self, node):
        """Calculate cyclomatic complexity."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def _calculate_nesting_depth(self, node, depth=0):
        """Calculate maximum nesting depth."""
        max_depth = depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.With, ast.Try)):
                child_depth = self._calculate_nesting_depth(child, depth + 1)
                max_depth = max(max_depth, child_depth)
        return max_depth
```

#### Usage in Pre-Commit Hook

```yaml
# .pre-commit-config.yaml

repos:
  - repo: local
    hooks:
      - id: philosophy-validator
        name: PHILOSOPHY.md Compliance Checker
        entry: python .claude/tools/amplihack/philosophy/ast_validator.py
        language: python
        types: [python]
        pass_filenames: true
        exclude: ^(tests/|examples/)
```

---

### Layer 4: Agent-Level Philosophy Prompting (PROACTIVE)

**When:** During agent task execution
**Who:** All builder/architect agents
**What:** Philosophy questions embedded in agent prompts

#### Enhanced Agent Instructions

Add to **ALL agents** (architect, builder, etc.):

```markdown
## MANDATORY PHILOSOPHY VALIDATION

Before implementing ANY feature, you MUST answer these questions:

### 1. Necessity Check
- **Evidence of Need:** What user reports, data, or failures prove this is needed NOW?
- **Simpler Alternatives:** Have simpler solutions been tried and failed?
- **Wait Cost:** What's the cost of waiting to build this?
- **Build Cost:** What's the cost of building this now?

**RULE:** If you cannot provide concrete evidence of current need, STOP and ask user to validate need first.

### 2. Complexity Check
- **Estimated LOC:** How many lines of code will this require?
- **Module Count:** How many new modules needed?
- **Dependencies:** What new dependencies does this add?
- **Comparison:** Compare to existing similar features - is this proportional?

**RULE:** If estimated complexity > 300 LOC or > 3 modules, question whether this can be simplified.

### 3. Value Check
- **User Value:** How does this help users TODAY (not tomorrow)?
- **Value/Complexity Ratio:** Is value > 3× the complexity cost?
- **Alternative Approaches:** What's the simplest thing that could work?

**RULE:** If value/complexity ratio < 3, seek simpler approach or defer.

### 4. Regenerability Check
- **Specification Clarity:** Can another agent rebuild this from spec?
- **Decision Complexity:** How many complex decisions does implementation require?
- **Domain Expertise:** How much specialized knowledge needed?

**RULE:** If implementation requires deep expertise not in spec, the spec is incomplete.

## STOP POINTS

If ANY of these are true, STOP and ask user before proceeding:

- ❌ No evidence of current need (only "might need" or "could be useful")
- ❌ Estimated complexity > 500 LOC for a single feature
- ❌ Value/complexity ratio < 3
- ❌ Solving problems that don't exist yet (YAGNI)
- ❌ Building "infrastructure for future features"
- ❌ More than 3 levels of abstraction
- ❌ Requires new database, framework, or major dependency
```

#### Example Application

**Before Implementing Phase 2:**

```
Builder Agent (with enhanced instructions):

User requested: "Implement Phase 2: AI-Powered Custom Skill Generation"

PHILOSOPHY VALIDATION:

1. Necessity Check:
   - Evidence of Need? ❌ NO - No users have reported skill gaps
   - Simpler Alternatives? ❌ NOT TRIED - Phase 1 not tested with real users
   - Wait Cost? ZERO - Can build later if gaps emerge
   - Build Cost? HIGH - 1,299 LOC + Claude SDK integration

   VERDICT: ❌ FAILS - No evidence of current need

2. Complexity Check:
   - Estimated LOC: 1,299 lines
   - Module Count: 4 new modules
   - Dependencies: anthropic SDK
   - Comparison: Phase 1 is 1,160 lines - this adds 112%

   VERDICT: ⚠️ WARNING - Complexity exceeds simple feature threshold

STOP POINT TRIGGERED: "No evidence of current need"

AGENT ACTION: Asking user for validation...

"Captain, I'm about to implement Phase 2 (AI Skill Generation), but philosophy
validation indicates this may be premature:

- No evidence users have skill gaps that Phase 1 can't fill
- Phase 1 hasn't been deployed to real users yet
- This adds 1,299 LOC (112% of Phase 1 size)
- We could wait and build only if gaps emerge

Should I:
A) Proceed anyway (you have evidence I don't know about)
B) Build minimal feature-flag version (disabled by default)
C) Defer until Phase 1 is validated with 10+ real users
D) Focus on Phase 1 excellence instead

Recommendation: C or D"
```

---

### Layer 3: Continuous Metrics Dashboard (VISIBILITY)

**When:** Real-time during development
**Who:** Automated metrics collection
**What:** Live dashboard showing philosophy metrics

#### Metrics to Track

```python
# .claude/tools/amplihack/philosophy/metrics_dashboard.py

class PhilosophyMetrics:
    """Real-time philosophy compliance metrics."""

    def calculate_project_metrics(self, src_dir: Path) -> dict:
        """Calculate current philosophy compliance metrics."""

        return {
            # YAGNI Metrics
            "total_loc": self._count_lines(src_dir),
            "production_code_used": self._estimate_used_code(src_dir),
            "speculative_code_pct": self._calculate_speculative_percentage(src_dir),

            # Simplicity Metrics
            "avg_function_complexity": self._calculate_avg_complexity(src_dir),
            "functions_over_threshold": self._count_complex_functions(src_dir),
            "max_nesting_depth": self._find_max_nesting(src_dir),

            # Modular Design Metrics
            "module_count": self._count_modules(src_dir),
            "avg_module_size": self._calculate_avg_module_size(src_dir),
            "coupling_score": self._calculate_coupling(src_dir),

            # Zero-BS Metrics
            "todo_count": self._count_todos(src_dir),
            "stub_count": self._count_stubs(src_dir),
            "pass_only_functions": self._count_pass_functions(src_dir),

            # Value Metrics
            "user_facing_features": self._count_user_features(src_dir),
            "value_complexity_ratio": self._calculate_value_ratio(src_dir),
        }

    def _estimate_used_code(self, src_dir: Path) -> int:
        """Estimate how much code is actually used vs speculative."""
        # Check for feature flags, lazy imports, experimental markers
        # Estimate based on: imports in __init__.py, feature flags, usage tracking
        pass

    def _calculate_speculative_percentage(self, src_dir: Path) -> float:
        """What percentage of code is for unvalidated features?"""
        total = self._count_lines(src_dir)
        used = self._estimate_used_code(src_dir)
        return ((total - used) / total) * 100 if total > 0 else 0
```

#### Dashboard Display

```bash
# .claude/runtime/philosophy_dashboard.txt (updated on every commit)

╔══════════════════════════════════════════════════════════════╗
║             PHILOSOPHY COMPLIANCE DASHBOARD                  ║
╠══════════════════════════════════════════════════════════════╣
║ YAGNI Status                                    ⚠️  WARNING   ║
║   Total LOC:           8,469                                 ║
║   Used Code:           1,160 (14%)                           ║
║   Speculative Code:    7,309 (86%)  ← DANGER                 ║
║                                                              ║
║ Simplicity Status                               ✅  GOOD     ║
║   Avg Complexity:      4.2 / 10                              ║
║   Complex Functions:   3 / 142 (2%)                          ║
║   Max Nesting:         4 levels                              ║
║                                                              ║
║ Modular Design                                  ✅  EXCELLENT║
║   Module Count:        26                                    ║
║   Avg Module Size:     195 lines                             ║
║   Coupling Score:      Low (0.15)                            ║
║                                                              ║
║ Zero-BS Status                                  ✅  PERFECT  ║
║   TODOs:               0                                     ║
║   Stubs:               0                                     ║
║   Pass-only:           0                                     ║
║                                                              ║
║ Value Metrics                                   ⚠️  WARNING  ║
║   User Features:       1 (Phase 1 only)                      ║
║   Value/Complexity:    0.14  ← TOO LOW                       ║
╚══════════════════════════════════════════════════════════════╝

⚠️  ALERT: Speculative code > 50% threshold!
    86% of codebase (7,309 lines) is for unvalidated features.

    Recommendation: Validate Phase 1 with real users before building more.

    Alternative: Move Phases 2-4 to /experimental directory.
```

#### When to Show Dashboard

- On every commit
- At workflow checkpoints (Step 4, Step 6, Step 14)
- When agent completes implementation
- Before creating PR

---

### Layer 4: Workflow Integration (SYSTEMATIC)

**When:** At specific workflow steps
**Who:** Mandatory agent invocations
**What:** Philosophy validation at key decision points

#### Enhanced DEFAULT_WORKFLOW.md

```markdown
## Step 4: Research and Design

**USE:** architect agent AND zen-architect agent IN PARALLEL

architect: Create technical design
zen-architect: Validate necessity and simplicity

**CHECKPOINT:**
- If zen-architect raises YAGNI concerns → discuss with user
- If value/complexity ratio < 3 → seek simpler approach
- If speculative code % > 30% → question scope

---

## Step 6: Cleanup and Simplification

**USE:** cleanup agent AND zen-architect agent IN PARALLEL

cleanup: Remove unnecessary code
zen-architect: Question every abstraction layer

**CHECKPOINT:**
- Review philosophy dashboard
- If any RED metrics → address before continuing
- If complexity increased > 20% → justify or simplify

---

## Step 13: Philosophy Compliance Review

**NEW MANDATORY STEP**

**USE:** zen-architect agent

**Goals:**
- Validate feature solves real problem (not speculative)
- Confirm simplicity maintained
- Check value/complexity ratio
- Verify YAGNI compliance

**CHECKPOINT:**
- zen-architect must APPROVE before proceeding
- If REJECTED → either simplify or defer
- If CONDITIONAL → add feature flags and validation plan

---

## Step 14: Final Validation

**USE:** cleanup agent (existing) AND philosophy-validator tool (new)

**Add:**
- Run automated philosophy checks
- Generate compliance report
- Check speculative code percentage
- Verify all TODO items resolved
```

---

### Layer 5: AI-Powered Pattern Detection (LEARNING)

**When:** Post-merge analysis
**Who:** Reflection system
**What:** Learn from past philosophy violations

#### Enhanced Reflection System

Add to `.claude/tools/amplihack/reflection/` a new analyzer:

```python
# philosophy_pattern_detector.py

class PhilosophyPatternDetector:
    """Detects patterns of philosophy violations for learning."""

    def analyze_session(self, session_transcript, codebase_state):
        """Analyze session for philosophy violation patterns."""

        patterns = []

        # Pattern 1: Speculative Feature Pattern
        if self._detect_speculative_build(session_transcript):
            patterns.append({
                "pattern": "Building features without validation",
                "evidence": self._extract_evidence(session_transcript),
                "prevention": "Ask for user data/evidence before design",
                "severity": "high"
            })

        # Pattern 2: Complexity Creep
        if self._detect_complexity_growth(codebase_state):
            patterns.append({
                "pattern": "Complexity growing without proportional value",
                "evidence": {
                    "loc_growth": codebase_state["loc_delta"],
                    "feature_growth": codebase_state["feature_delta"],
                    "ratio": codebase_state["loc_delta"] / max(1, codebase_state["feature_delta"])
                },
                "prevention": "Set LOC budget per feature, enforce in design",
                "severity": "medium"
            })

        # Pattern 3: Premature Abstraction
        if self._detect_early_abstraction(session_transcript):
            patterns.append({
                "pattern": "Abstracting before understanding problem",
                "evidence": self._find_abstract_classes(codebase_state),
                "prevention": "Require 3 concrete examples before abstracting",
                "severity": "medium"
            })

        return {
            "patterns_detected": patterns,
            "recommendations": self._generate_recommendations(patterns),
            "update_workflow": self._suggest_workflow_improvements(patterns)
        }
```

#### Integration with Reflection

After each session, reflection system:
1. Detects philosophy violation patterns
2. Updates `.claude/context/KNOWN_VIOLATIONS.md`
3. Suggests workflow improvements
4. Updates agent instructions automatically

---

## PRACTICAL IMPLEMENTATION PLAN

### Phase 1: Immediate (1 week)

**Add Pre-Commit Hook:**
```bash
# Install philosophy validator
pip install -e .
pre-commit install

# Add to .pre-commit-config.yaml
- repo: local
  hooks:
    - id: philosophy-ast
      name: Philosophy AST Validator
      entry: python -m amplihack.philosophy.ast_validator
      language: python
      types: [python]
```

**Update Workflow:**
- Add zen-architect to Step 4 (mandatory)
- Add philosophy dashboard to Step 6
- Add new Step 13: Philosophy Compliance Review

**Estimated Effort:** 8-12 hours

---

### Phase 2: Integration (2 weeks)

**Build Philosophy Toolkit:**
1. ComplexityChecker - Design validation
2. AST Validator - Code validation
3. Metrics Dashboard - Real-time visibility
4. Pattern Detector - Learning from violations

**Integrate into Agents:**
- Update all agent instructions
- Add mandatory checkpoints
- Embed necessity questionnaire

**Estimated Effort:** 40-60 hours

---

### Phase 3: Automation (1 month)

**CI/CD Integration:**
```yaml
# .github/workflows/philosophy-check.yml

name: Philosophy Compliance

on: [pull_request]

jobs:
  philosophy-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Check YAGNI Compliance
        run: |
          python scripts/check_speculative_code.py
          if [ $SPECULATIVE_PCT -gt 30 ]; then
            echo "::error::Speculative code > 30%"
            exit 1
          fi

      - name: Check Complexity
        run: |
          python scripts/check_complexity.py
          # Fails if avg complexity > 10

      - name: Check TODOs
        run: |
          python scripts/check_todos.py src/
          # Fails if any TODOs in production code

      - name: Generate Philosophy Report
        run: |
          python scripts/generate_philosophy_report.py
          # Posts comment to PR with metrics
```

**Estimated Effort:** 60-80 hours

---

## SPECIFIC TOOLS TO BUILD

### Tool 1: YAGNI Detector

```python
# .claude/tools/amplihack/philosophy/yagni_detector.py

class YagniDetector:
    """Detects You Aren't Gonna Need It violations."""

    def check_feature(self, feature_spec: dict) -> dict:
        """Check if feature is needed now."""

        # Red flags
        red_flags = []

        # Check for "future-proof" language
        keywords = ['future', 'might', 'could', 'potentially', 'extensible',
                   'scalable', 'flexible', 'generic']
        if any(kw in feature_spec['description'].lower() for kw in keywords):
            red_flags.append(
                "Future-oriented language detected - May be premature"
            )

        # Check for usage evidence
        if 'usage_data' not in feature_spec:
            red_flags.append(
                "No usage data provided - How do you know this is needed?"
            )

        # Check for alternative exploration
        if 'alternatives_considered' not in feature_spec:
            red_flags.append(
                "No alternatives documented - Why is this the right approach?"
            )

        # Check for validation plan
        if 'validation_criteria' not in feature_spec:
            red_flags.append(
                "No validation plan - How will you know this works?"
            )

        return {
            "approved": len(red_flags) == 0,
            "red_flags": red_flags,
            "recommendation": "Defer" if len(red_flags) > 2 else "Conditional"
        }
```

---

### Tool 2: Simplicity Enforcer

```python
# .claude/tools/amplihack/philosophy/simplicity_enforcer.py

class SimplicityEnforcer:
    """Enforces ruthless simplicity principle."""

    BUDGETS = {
        "simple_feature": 200,      # LOC
        "moderate_feature": 500,
        "complex_feature": 1000,
    }

    def check_implementation(self, files: List[Path]) -> dict:
        """Check if implementation is as simple as possible."""

        total_loc = sum(self._count_lines(f) for f in files)

        issues = []

        # Check against budget
        declared_complexity = self._get_declared_complexity()
        budget = self.BUDGETS.get(declared_complexity, 500)

        if total_loc > budget:
            issues.append(
                f"LOC {total_loc} exceeds {declared_complexity} budget ({budget})"
                f"\nQuestion: Can this be simplified? What can be removed?"
            )

        # Check abstraction layers
        layers = self._count_abstraction_layers(files)
        if layers > 3:
            issues.append(
                f"Found {layers} abstraction layers (max: 3)"
                f"\nQuestion: Are all these layers necessary?"
            )

        # Check for premature generalization
        if self._detect_premature_abstraction(files):
            issues.append(
                "Generic base classes found with single implementation"
                f"\nViolation: Don't abstract until you have 3+ concrete cases"
            )

        return {
            "approved": len(issues) == 0,
            "issues": issues,
            "suggestions": self._generate_simplifications(files)
        }
```

---

### Tool 3: Value/Complexity Ratio Calculator

```python
# .claude/tools/amplihack/philosophy/value_calculator.py

class ValueComplexityCalculator:
    """Calculates value delivered per unit of complexity."""

    def calculate_ratio(self, feature: FeatureImplementation) -> float:
        """Calculate value/complexity ratio (target: > 3.0)."""

        # Measure complexity
        complexity = self._measure_complexity(feature)

        # Measure value
        value = self._measure_value(feature)

        return value / complexity if complexity > 0 else 0

    def _measure_complexity(self, feature):
        """Complexity score (0-100)."""
        return (
            feature.lines_of_code * 0.3 +
            feature.module_count * 10 +
            feature.dependency_count * 15 +
            feature.abstraction_layers * 20 +
            feature.test_lines * 0.1
        )

    def _measure_value(self, feature):
        """Value score (0-100)."""
        return (
            feature.user_reports * 20 +          # Actual user requests
            feature.pain_point_severity * 15 +   # How bad is problem?
            feature.frequency_of_need * 25 +     # How often needed?
            feature.user_count_affected * 30 +   # How many users?
            feature.alternatives_exhausted * 10  # Tried simpler solutions?
        )
```

---

## HOW TO USE THESE TOOLS

### In Workflow

```markdown
## Step 4: Research and Design

1. **Create Design Spec** (architect agent)

2. **YAGNI Check** (automated):
   ```bash
   python -m amplihack.philosophy.yagni_detector design_spec.json
   ```

   If REJECTED:
   - Document in deferred_features.md
   - Focus on validated work
   - DO NOT implement

3. **Complexity Check** (automated):
   ```bash
   python -m amplihack.philosophy.simplicity_enforcer design_spec.json
   ```

   If over budget:
   - Simplify design OR
   - Justify complexity with user value data

4. **Value Check** (manual):
   ```bash
   python -m amplihack.philosophy.value_calculator design_spec.json
   ```

   If ratio < 3.0:
   - Reduce scope OR
   - Increase value (add user features) OR
   - Defer until value proven

Only proceed if ALL checks pass.
```

---

## SPECIFIC PREVENTIVE MEASURES

### For YAGNI Violations (The Phase 2-4 Problem)

**Prevent By:**

1. **Require Evidence Document** before any "Phase N" work:
   ```markdown
   # EVIDENCE_FOR_PHASE_2.md (REQUIRED)

   ## User Reports
   - User 1: "Phase 1 couldn't generate skill for X"
   - User 2: "Needed custom Y capability"
   - (Minimum: 10 user reports)

   ## Data
   - 73% of goals encountered skill gaps
   - Average coverage: 45% (below 70% threshold)

   ## Alternatives Tried
   - Manual skill creation: Too slow (2 hours/skill)
   - Skill templates: Too rigid, didn't fit needs

   ## Validation Criteria
   - After implementation: 90% coverage with AI skills
   - User satisfaction: 8/10 or higher
   - Generation time: < 30 seconds per skill
   ```

2. **Feature Flag by Default** for ALL speculative features:
   ```python
   # In skill_synthesizer.py
   def synthesize_skills(self, plan, enable_phase2=False):  # Default: False
       if enable_phase2 and self._phase2_validated():
           # Phase 2 logic
       else:
           # Phase 1 only
   ```

3. **Graduated Rollout** instead of big bang:
   - Week 1-2: Phase 1 only to 10 users
   - Week 3: Collect data on skill gaps
   - Week 4: IF gaps found → build minimal Phase 2
   - Month 2: IF coordination needed → build minimal Phase 3
   - Month 3: IF learning patterns found → build minimal Phase 4

---

### For Complexity Creep

**Prevent By:**

1. **LOC Budget in Issue Template:**
   ```markdown
   ## Feature Specification

   **Estimated Complexity:**
   - [ ] Simple (< 200 LOC)
   - [ ] Moderate (200-500 LOC)
   - [ ] Complex (500-1000 LOC)
   - [ ] Very Complex (> 1000 LOC) ← REQUIRES JUSTIFICATION

   **If Very Complex, answer:**
   - Why can't this be split into smaller features?
   - What's the minimum viable version?
   - Have simpler alternatives been exhausted?
   ```

2. **Complexity Budget Tracking:**
   ```bash
   # In PR template
   Current complexity budget: 5,000 LOC
   This PR adds: 1,299 LOC (Phase 2)
   Remaining budget: 3,701 LOC

   ⚠️ WARNING: This PR uses 26% of remaining complexity budget!

   Question: Is this feature worth the complexity investment?
   ```

---

### For Fake Data / Mock Implementations

**Prevent By:**

1. **Automated Mock Detector in Pre-Commit:**
   ```python
   # Already implemented in AST validator above
   # Checks for:
   - mock/fake/dummy variable names
   - Hardcoded data lists
   - Return values that look like placeholders
   ```

2. **Required Real Data Sources in Design:**
   ```markdown
   Every data source in design must specify:
   - [ ] Source: Real API / Database / File
   - [ ] Fallback: What happens if source unavailable?
   - [ ] Validation: How do we verify data is real?

   ❌ BLOCKED: Return hardcoded list
   ✅ ALLOWED: Return empty list if source unavailable
   ```

---

## RECOMMENDED IMPLEMENTATION ORDER

### Week 1: Quick Wins
1. Add philosophy questions to architect/builder agent instructions (4 hours)
2. Create pre-commit AST validator (8 hours)
3. Add zen-architect to Step 4 of workflow (2 hours)
4. Create philosophy metrics dashboard script (8 hours)

**Deliverable:** Automated checks catch obvious violations

---

### Week 2-3: Workflow Integration
5. Implement ComplexityChecker for designs (12 hours)
6. Implement YagniDetector (8 hours)
7. Create Value/Complexity calculator (8 hours)
8. Update all agent instructions with checkpoints (12 hours)
9. Add mandatory zen-architect reviews to workflow (4 hours)

**Deliverable:** Workflow enforces philosophy at key decision points

---

### Week 4: Learning System
10. Enhance reflection with philosophy pattern detection (16 hours)
11. Create automated workflow updates from violations (12 hours)
12. Build dashboard visualization (8 hours)
13. Integrate with CI/CD (12 hours)

**Deliverable:** System learns and prevents repeat violations

---

## MEASURING SUCCESS

### Before Implementation (Baseline)
- Speculative code: 86%
- YAGNI violations: Found post-implementation
- Time to detect: Hours/days after building

### After Implementation (Target)
- Speculative code: < 30%
- YAGNI violations: Blocked at design time
- Time to detect: Minutes (during design phase)

### Metrics to Track

```markdown
# .claude/runtime/philosophy_metrics.json

{
  "period": "2025-11",
  "features_proposed": 10,
  "features_approved": 3,
  "features_deferred": 5,
  "features_rejected": 2,

  "yagni_blocks": 7,           # How many times YAGNI check blocked work
  "yagni_validates": 3,        # How many later proved necessary
  "yagni_false_positives": 1,  # How many blocks were wrong

  "avg_value_complexity": 4.2, # Target: > 3.0
  "speculative_code_pct": 18,  # Target: < 30%

  "violations_prevented": 12,  # Caught at design time
  "violations_detected": 3,    # Caught at review time

  "prevention_rate": 80%       # 12/(12+3) = 80%
}
```

---

## EXAMPLE: How It Would Have Worked

### Scenario: Implementing Phase 2

**Step 1: User requests Phase 2**

**Step 2: Architect starts design**

**Step 3: YAGNI Detector runs automatically**
```
❌ YAGNI VIOLATION DETECTED

Feature: Phase 2 (AI-Powered Custom Skill Generation)
Evidence of need: NONE
Simpler alternatives tried: NONE (Phase 1 not tested with users)
Wait cost: ZERO
Build cost: HIGH (1,299 LOC + Claude SDK)

VERDICT: REJECTED - Premature

Action: Defer until Phase 1 validated with 10+ real users
```

**Step 4: Workflow BLOCKS implementation**
```
⛔ CHECKPOINT FAILED: Zen-Architect Validation

The zen-architect has flagged this feature as potentially premature.

Options:
A) Provide evidence of need (user reports, data showing gaps)
B) Build minimal feature-flag version
C) Defer and focus on Phase 1 excellence
D) Override (requires explicit user approval)

Recommendation: C or D

Waiting for user decision...
```

**Step 5: User makes informed choice**

User either:
- Provides evidence → Proceeds
- Agrees to defer → Saves 1,299 LOC of speculative code
- Overrides with awareness → Knows the risk

**Net Result:** No surprise "86% speculative code" finding at review time.

---

## BENEFITS OF EARLY ENFORCEMENT

### Time Savings
- **Before:** Build 7,309 lines → Review → Find violations → Debate → Maybe delete
- **After:** Validate → Build 1,160 lines → Review → Approve → Ship
- **Savings:** ~85% less wasted implementation time

### Quality Improvements
- Smaller codebase (easier to maintain)
- Higher value/complexity ratio
- Less security attack surface
- Faster test execution

### Learning
- Agents learn what NOT to build
- Workflow improves automatically
- Violations tracked and prevented

---

## CONCLUSION

Philosophy enforcement should happen at **FOUR CRITICAL POINTS:**

1. **Pre-Design (Necessity):** Before creating specs - "Do we need this?"
2. **Design Review (Complexity):** Before implementation - "Is this simple enough?"
3. **Pre-Commit (Technical):** During coding - "Any TODOs, stubs, fakes?"
4. **Post-Merge (Learning):** After shipping - "What patterns emerged?"

**Current State:** Only #3 and #4 exist (too late)
**Needed:** Add #1 and #2 (preventive, not detective)

**Implementation Priority:**
1. Add zen-architect to Step 4 (1 day)
2. Create automated YAGNI detector (1 week)
3. Build philosophy dashboard (1 week)
4. Integrate with CI/CD (2 weeks)

**Expected Outcome:** Catch 80% of violations at design time instead of review time.
