# Phase 2: AI-Powered Custom Skill Generation

Phase 2 extends the Goal Agent Generator with AI-powered capabilities to automatically generate custom skills when existing skills don't provide sufficient coverage.

## Overview

Phase 2 adds four core components:

1. **SkillGapAnalyzer** - Analyzes gaps between required and available capabilities
2. **SkillValidator** - Validates generated skills meet quality standards
3. **AISkillGenerator** - Generates custom skills using Claude SDK
4. **SkillRegistry** - Central registry for all skills with persistence

## Architecture

```
Phase 1: Match Existing Skills
     ↓
SkillGapAnalyzer: Analyze Coverage
     ↓
Coverage < 70%?
     ↓ YES
AISkillGenerator: Generate Custom Skills
     ↓
SkillValidator: Validate Quality
     ↓
SkillRegistry: Register & Persist
     ↓
Combined Skills (Existing + Generated)
```

## Components

### 1. SkillGapAnalyzer

Analyzes which capabilities need custom skills vs existing skills.

```python
from amplihack.goal_agent_generator import SkillGapAnalyzer

analyzer = SkillGapAnalyzer()
report = analyzer.analyze_gaps(execution_plan, existing_skills)

print(f"Coverage: {report.coverage_percentage}%")
print(f"Missing: {report.missing_capabilities}")
print(f"Recommendation: {report.recommendation}")
```

**Features:**
- Calculates coverage percentage (0-100%)
- Identifies missing capabilities
- Ranks gaps by criticality (core, validation, integration, etc.)
- Recommends action: use_existing, generate_custom, or mixed

### 2. SkillValidator

Validates generated skills meet quality standards.

```python
from amplihack.goal_agent_generator import SkillValidator

validator = SkillValidator()
result = validator.validate_skill(skill_content, skill_name)

if result.passed:
    print(f"Quality score: {result.quality_score}")
else:
    print(f"Issues: {result.issues}")
```

**Checks:**
- Markdown structure (headings, sections, formatting)
- No placeholder text (TODO, FIXME, XXX, etc.)
- Required sections (description, capabilities, usage)
- Content quality (length, detail, examples)

### 3. AISkillGenerator

Generates custom skills using Claude SDK with few-shot prompting.

```python
from amplihack.goal_agent_generator import AISkillGenerator

generator = AISkillGenerator(
    api_key="your-api-key",  # or set ANTHROPIC_API_KEY env var
    model="claude-sonnet-4-5-20250929"
)

skills = generator.generate_skills(
    required_capabilities=["custom-process", "transform-data"],
    domain="data-processing",
    context="ETL pipeline for financial data",
    validate=True  # Auto-validate generated skills
)

for skill in skills:
    print(f"Generated: {skill.name}")
    print(f"Validation: {skill.validation_result.passed}")
```

**Features:**
- Uses Claude SDK (anthropic library)
- Few-shot prompting with existing skills as examples
- Generates amplihack-format skill markdown
- Optional automatic validation
- Regenerate failed skills

### 4. SkillRegistry

Central registry for all skills (existing + generated) with disk persistence.

```python
from amplihack.goal_agent_generator import SkillRegistry

registry = SkillRegistry()

# Register skills
registry.register(skill)
registry.register_batch(skills)

# Search
results = registry.search_by_capability("analyze")
results = registry.search_by_capabilities(["test", "validate"])
results = registry.search_by_domain("security")

# Persistence
registry.save()  # Saves to ~/.claude/skills_registry.json
registry.load()  # Loads from disk

# Statistics
stats = registry.get_statistics()
print(f"Total skills: {stats['total_skills']}")
print(f"Generated: {stats['generated_skills']}")
```

**Features:**
- In-memory cache with disk persistence
- Indexed by name, capabilities, domain
- Supports existing and generated skills
- JSON format for portability

## Integration with Phase 1

Phase 2 is seamlessly integrated into the existing SkillSynthesizer:

```python
from amplihack.goal_agent_generator import SkillSynthesizer

# Enable Phase 2
synthesizer = SkillSynthesizer(
    enable_phase2=True,
    phase2_coverage_threshold=70.0  # Generate if coverage < 70%
)

# Phase 1: Match existing skills
# Phase 2: Auto-generate if needed
skills = synthesizer.synthesize_skills(execution_plan, domain="data-processing")
```

**Behavior:**
1. First tries to match existing skills (Phase 1)
2. If coverage < threshold, analyzes gaps
3. Generates custom skills for missing capabilities
4. Validates generated skills
5. Registers all skills in registry
6. Returns combined list (existing + generated)

## Data Models

### SkillGapReport

```python
@dataclass
class SkillGapReport:
    execution_plan_id: uuid.UUID
    coverage_percentage: float  # 0-100
    missing_capabilities: List[str]
    gaps_by_phase: Dict[str, List[str]]
    criticality_ranking: List[Tuple[str, float]]
    recommendation: Literal["use_existing", "generate_custom", "mixed"]
```

### GeneratedSkillDefinition

```python
@dataclass
class GeneratedSkillDefinition(SkillDefinition):
    generation_prompt: str
    generation_model: str
    validation_result: Optional[ValidationResult]
    provenance: Literal["ai_generated"] = "ai_generated"
    generated_at: datetime
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    passed: bool
    issues: List[str]
    warnings: List[str]
    quality_score: float  # 0-1
```

## Usage Examples

### Example 1: Basic Phase 2 Usage

```python
from amplihack.goal_agent_generator import (
    ExecutionPlan,
    PlanPhase,
    SkillGapAnalyzer,
    AISkillGenerator,
    SkillRegistry
)

# Create execution plan
plan = ExecutionPlan(
    goal_id=uuid.uuid4(),
    phases=[
        PlanPhase(
            name="Custom Processing",
            description="Process data with custom logic",
            required_capabilities=["custom-process", "transform"],
            estimated_duration="15 min"
        )
    ],
    total_estimated_duration="15 min"
)

# Analyze gaps
analyzer = SkillGapAnalyzer()
report = analyzer.analyze_gaps(plan, existing_skills=[])

# Generate custom skills
generator = AISkillGenerator()
generated = generator.generate_skills(
    required_capabilities=report.missing_capabilities,
    domain="data-processing",
    validate=True
)

# Register skills
registry = SkillRegistry()
registry.register_batch(generated)
registry.save()
```

### Example 2: Integrated with SkillSynthesizer

```python
from amplihack.goal_agent_generator import SkillSynthesizer

synthesizer = SkillSynthesizer(
    enable_phase2=True,
    phase2_coverage_threshold=70.0
)

# Automatically handles Phase 1 + Phase 2
skills = synthesizer.synthesize_skills(
    execution_plan=plan,
    domain="security-analysis"
)

# skills now contains both existing and generated skills
print(f"Total skills: {len(skills)}")
```

### Example 3: Manual Skill Validation

```python
from amplihack.goal_agent_generator import SkillValidator

validator = SkillValidator()

# Validate single skill
result = validator.validate_skill(skill_content, "my-skill")

if not result.passed:
    print("Issues found:")
    for issue in result.issues:
        print(f"  - {issue}")

# Validate batch
results = validator.validate_batch([
    ("skill1", content1),
    ("skill2", content2),
])

summary = validator.get_validation_summary(results)
print(f"Pass rate: {summary['pass_rate']:.1%}")
```

## Configuration

### Environment Variables

- `ANTHROPIC_API_KEY` - Your Anthropic API key for skill generation

### Customization

```python
# Custom coverage threshold
synthesizer = SkillSynthesizer(
    enable_phase2=True,
    phase2_coverage_threshold=60.0  # More aggressive generation
)

# Custom model
generator = AISkillGenerator(
    model="claude-sonnet-4-5-20250929",  # Specific model version
    api_key="your-key"
)

# Custom registry path
registry = SkillRegistry(
    registry_path=Path("/custom/path/registry.json")
)
```

## Testing

Phase 2 includes comprehensive tests with >80% coverage:

```bash
# Run Phase 2 tests
pytest src/amplihack/goal_agent_generator/tests/phase2/ -v

# Run specific test
pytest src/amplihack/goal_agent_generator/tests/phase2/test_skill_gap_analyzer.py -v

# Run integration tests
pytest src/amplihack/goal_agent_generator/tests/phase2/test_phase2_integration.py -v
```

**Test Coverage:**
- `test_skill_gap_analyzer.py` - Gap analysis logic
- `test_skill_validator.py` - Validation rules
- `test_ai_skill_generator.py` - Skill generation (mocked API)
- `test_skill_registry.py` - Registry operations and persistence
- `test_phase2_integration.py` - End-to-end integration

## Architecture Decisions

### Why Lazy Loading?

Phase 2 components use lazy loading in SkillSynthesizer to:
- Avoid importing Anthropic SDK unless Phase 2 is enabled
- Reduce startup time for Phase 1-only usage
- Allow graceful degradation if Phase 2 dependencies missing

### Why Coverage Threshold?

The 70% coverage threshold balances:
- Cost of API calls for skill generation
- Quality of existing skill matches
- Likelihood of successful generation

Can be adjusted based on needs:
- **Higher (80%+)**: More conservative, use existing skills when possible
- **Lower (50-60%)**: More aggressive generation, ensure comprehensive coverage

### Why Separate Registry?

SkillRegistry is separate from SkillSynthesizer to:
- Enable reuse across multiple synthesis operations
- Provide centralized skill management
- Support skill discovery and search
- Persist generated skills for future use

## Error Handling

Phase 2 includes comprehensive error handling:

```python
try:
    skills = synthesizer.synthesize_skills(plan, domain="test")
except Exception as e:
    # Phase 2 errors are caught and logged
    # Falls back to Phase 1 skills only
    print(f"Phase 2 failed: {e}")
```

**Graceful Degradation:**
- API errors → Fall back to Phase 1
- Validation failures → Still return skills (with warnings)
- Registry errors → Continue without persistence

## Performance

**Typical Performance:**
- Gap analysis: <100ms
- Skill validation: <50ms per skill
- Skill generation: 2-5 seconds per skill (API call)
- Registry operations: <10ms

**Optimization Tips:**
- Cache AISkillGenerator instance to reuse API client
- Use batch validation for multiple skills
- Set appropriate coverage threshold to minimize API calls
- Persist registry to avoid regenerating known skills

## Limitations

1. **API Dependency**: Requires Anthropic API key and network access
2. **Generation Cost**: API calls incur costs (tokens used)
3. **Quality Variance**: Generated skills may vary in quality
4. **Domain Specificity**: Works best for well-defined domains

## Future Enhancements

Potential Phase 3 features:
- Fine-tuned models for domain-specific generation
- Skill combination and composition
- Feedback loop for skill improvement
- Multi-model generation and comparison
- Skill evolution and versioning

## Support

For issues or questions:
1. Check test files for usage examples
2. Review integration tests for end-to-end flows
3. Examine existing generated skills in registry
4. Enable debug logging for detailed output

## License

Part of the amplihack Goal Agent Generator system.
