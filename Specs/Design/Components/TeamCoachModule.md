# Team Coach Module Design

## Overview

The Team Coach Module implements a self-reflection and continuous improvement system that analyzes AgenticCoding usage patterns, identifies friction points, and automatically generates improvements to the system itself. It operates asynchronously through hooks, ensuring zero impact on user experience while driving system evolution.

## Requirements Coverage

This module addresses the following requirements:
- **TC-AGENT-***: Sub-agent session reflection and analysis
- **TC-TOOL-***: Tool usage pattern analysis
- **TC-REPL-***: REPL session analysis (highest priority)
- **TC-PATTERN-***: Pattern detection across sessions
- **TC-IMPROVE-***: Improvement generation and implementation
- **TC-HOOK-***: Hook system integration
- **TC-RECUR-***: Recursion prevention mechanisms

## Module Structure

```
team_coach/
├── __init__.py              # Public API exports
├── models.py               # Data models for reflection
├── hooks.py                # Hook integration points
├── analyzer.py             # Session analysis engine
├── pattern_detector.py     # Pattern detection across sessions
├── improver.py             # Improvement generation
├── store.py                # Insight persistence
├── recursion_guard.py      # Recursion prevention
├── config.py               # Configuration management
└── tests/                  # Module tests
    ├── test_hooks.py
    ├── test_analyzer.py
    ├── test_improver.py
    └── test_recursion.py
```

## Component Specifications

### Hooks Component

**Purpose**: Capture reflection events from system hooks

**Class Design**:
```python
class ReflectionHooks:
    """Hook handlers for reflection events"""

    def __init__(self, config: TeamCoachConfig):
        self.config = config
        self.guard = RecursionGuard()
        self.analyzer = SessionAnalyzer()
        self.async_executor = AsyncTaskExecutor()

    async def on_agent_stop(
        self,
        session_data: Dict[str, Any]
    ) -> None:
        """Handle sub-agent session completion"""
        if self.guard.should_reflect(session_data):
            await self.async_executor.submit(
                self.analyzer.analyze_agent_session,
                session_data
            )

    async def on_tool_use(
        self,
        tool_data: Dict[str, Any]
    ) -> None:
        """Handle tool execution events"""
        if self.guard.should_reflect(tool_data):
            await self.async_executor.submit(
                self.analyzer.analyze_tool_usage,
                tool_data
            )

    async def on_repl_stop(
        self,
        session_data: Dict[str, Any]
    ) -> None:
        """Handle REPL session completion (priority)"""
        if self.guard.should_reflect(session_data):
            await self.async_executor.submit(
                self.analyzer.analyze_repl_session,
                session_data,
                priority=True
            )
```

**Hook Registration**:
```python
def register_hooks():
    """Register all Team Coach hooks"""
    hooks = ReflectionHooks(load_config())

    # Register with Claude Code hook system
    register_hook("agent_stop", hooks.on_agent_stop)
    register_hook("tool_use", hooks.on_tool_use)
    register_hook("repl_stop", hooks.on_repl_stop)
```

### Analyzer Component

**Purpose**: Extract insights from session data

**Class Design**:
```python
class SessionAnalyzer:
    """Analyze sessions for improvement insights"""

    def __init__(self):
        self.claude_client = ClaudeSDKClient()
        self.friction_detector = FrictionDetector()
        self.store = InsightStore()

    async def analyze_agent_session(
        self,
        session_data: Dict
    ) -> AgentInsight:
        """Analyze agent session for improvements"""

        # Extract metrics
        metrics = self.extract_agent_metrics(session_data)

        # Detect friction points
        friction = self.friction_detector.detect_agent_friction(
            session_data,
            metrics
        )

        # Use Claude for deep analysis
        if friction.severity > self.config.analysis_threshold:
            analysis = await self.claude_analysis(
                session_data,
                "agent_session"
            )

            insight = AgentInsight(
                session_id=session_data['id'],
                friction_points=friction.points,
                suggestions=analysis.suggestions,
                severity=friction.severity,
                context_issues=analysis.context_issues,
                capability_gaps=analysis.capability_gaps
            )

            await self.store.save_insight(insight)
            return insight

    async def analyze_repl_session(
        self,
        session_data: Dict,
        priority: bool = True
    ) -> ReplInsight:
        """Analyze REPL session (highest priority)"""

        # Complex analysis for user sessions
        user_metrics = self.extract_user_metrics(session_data)

        # Detect user frustration
        frustration = self.detect_user_frustration(
            session_data,
            user_metrics
        )

        # Identify improvement opportunities
        opportunities = await self.identify_opportunities(
            session_data,
            frustration
        )

        insight = ReplInsight(
            session_id=session_data['id'],
            frustration_level=frustration.level,
            task_complexity=user_metrics.complexity,
            agent_usage=user_metrics.agents_used,
            redirection_count=user_metrics.redirections,
            opportunities=opportunities,
            priority=priority
        )

        await self.store.save_insight(insight)
        return insight
```

**Friction Detection**:
```python
class FrictionDetector:
    """Detect friction points in sessions"""

    def detect_agent_friction(
        self,
        session: Dict,
        metrics: AgentMetrics
    ) -> FrictionResult:
        """Identify agent friction indicators"""

        friction_points = []

        # Check for retries
        if metrics.retry_count > 2:
            friction_points.append(
                FrictionPoint("excessive_retries", metrics.retry_count)
            )

        # Check for context issues
        if metrics.context_requests > 3:
            friction_points.append(
                FrictionPoint("insufficient_context", metrics.context_requests)
            )

        # Check for timeouts
        if metrics.timeout_count > 0:
            friction_points.append(
                FrictionPoint("performance_timeout", metrics.timeout_count)
            )

        severity = self.calculate_severity(friction_points)
        return FrictionResult(points=friction_points, severity=severity)
```

### Pattern Detector Component

**Purpose**: Identify patterns across multiple sessions

**Class Design**:
```python
class PatternDetector:
    """Detect patterns across reflection insights"""

    def __init__(self):
        self.store = InsightStore()
        self.pattern_algorithms = [
            FrequencyPatternDetector(),
            SequencePatternDetector(),
            CorrelationPatternDetector()
        ]

    async def detect_patterns(
        self,
        time_window: int = 24  # hours
    ) -> List[Pattern]:
        """Find patterns in recent insights"""

        # Get recent insights
        insights = await self.store.get_recent_insights(time_window)

        patterns = []
        for algorithm in self.pattern_algorithms:
            detected = algorithm.detect(insights)
            patterns.extend(detected)

        # Rank by impact
        patterns.sort(key=lambda p: p.impact_score, reverse=True)

        return patterns

    def correlate_patterns(
        self,
        patterns: List[Pattern]
    ) -> List[CorrelatedPattern]:
        """Find relationships between patterns"""

        correlations = []
        for i, p1 in enumerate(patterns):
            for p2 in patterns[i+1:]:
                if self.are_correlated(p1, p2):
                    correlations.append(
                        CorrelatedPattern(p1, p2, self.correlation_strength(p1, p2))
                    )

        return correlations
```

### Improver Component

**Purpose**: Generate and implement improvements

**Class Design**:
```python
class ImprovementGenerator:
    """Generate improvements from insights and patterns"""

    def __init__(self):
        self.claude_client = ClaudeSDKClient()
        self.github_client = GitHubClient()
        self.validator = ImprovementValidator()
        self.store = InsightStore()

    async def generate_improvements(
        self,
        patterns: List[Pattern],
        insights: List[Insight]
    ) -> List[ImprovementPlan]:
        """Create improvement plans from patterns"""

        # Group related patterns and insights
        groups = self.group_related(patterns, insights)

        improvements = []
        for group in groups:
            # Generate improvement with Claude
            plan = await self.generate_plan(group)

            # Validate safety and feasibility
            if self.validator.is_safe(plan):
                improvements.append(plan)

        # Prioritize by ROI
        improvements.sort(key=lambda i: i.roi_score, reverse=True)

        return improvements

    async def implement_improvement(
        self,
        plan: ImprovementPlan
    ) -> PullRequest:
        """Create PR for improvement"""

        # Generate code changes
        changes = await self.generate_code_changes(plan)

        # Create branch
        branch_name = f"team-coach/improvement-{plan.id}"
        await self.github_client.create_branch(branch_name)

        # Apply changes
        for change in changes:
            await self.github_client.create_or_update_file(
                path=change.path,
                content=change.content,
                branch=branch_name,
                message=f"Team Coach: {change.description}"
            )

        # Create PR
        pr = await self.github_client.create_pull_request(
            title=f"Team Coach: {plan.title}",
            body=self.generate_pr_description(plan),
            branch=branch_name
        )

        # Track application
        await self.store.mark_improvement_applied(plan.id, pr.url)

        return pr
```

### Recursion Guard Component

**Purpose**: Prevent recursive reflection loops

**Class Design**:
```python
class RecursionGuard:
    """Prevent recursive reflection loops"""

    def __init__(self):
        self.reflection_sessions = set()
        self.last_reflection_time = {}
        self.min_interval = 300  # 5 minutes

    def should_reflect(self, event_data: Dict) -> bool:
        """Check if reflection should occur"""

        # Check environment variable
        if os.environ.get("TEAM_COACH_ACTIVE") == "true":
            return False

        # Check session prefix
        session_id = event_data.get('session_id', '')
        if session_id.startswith('tc_'):
            return False

        # Check if already reflecting
        if session_id in self.reflection_sessions:
            return False

        # Check time since last reflection
        event_type = event_data.get('type', 'unknown')
        if event_type in self.last_reflection_time:
            elapsed = time.time() - self.last_reflection_time[event_type]
            if elapsed < self.min_interval:
                return False

        # Mark as reflecting
        self.mark_reflecting(session_id, event_type)
        return True

    def mark_reflecting(self, session_id: str, event_type: str):
        """Mark session as under reflection"""
        self.reflection_sessions.add(session_id)
        self.last_reflection_time[event_type] = time.time()

    def clear_reflection(self, session_id: str):
        """Clear reflection status"""
        self.reflection_sessions.discard(session_id)
```

### Store Component

**Purpose**: Persist insights and improvements

**Class Design**:
```python
class InsightStore:
    """Storage for reflection insights"""

    def __init__(self, storage_path: Path = Path(".data/team_coach/")):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.index = self.load_index()

    async def save_insight(self, insight: Insight) -> None:
        """Save insight to storage"""

        # Generate filename
        timestamp = datetime.now().isoformat()
        filename = f"insight_{insight.type}_{timestamp}.json"

        # Save to file
        file_path = self.storage_path / filename
        with open(file_path, 'w') as f:
            json.dump(insight.to_dict(), f, indent=2)

        # Update index
        self.index[insight.id] = {
            'file': filename,
            'type': insight.type,
            'timestamp': timestamp,
            'severity': insight.severity
        }
        self.save_index()

    async def get_recent_insights(
        self,
        hours: int = 24
    ) -> List[Insight]:
        """Retrieve recent insights"""

        cutoff = datetime.now() - timedelta(hours=hours)
        recent = []

        for insight_id, metadata in self.index.items():
            timestamp = datetime.fromisoformat(metadata['timestamp'])
            if timestamp > cutoff:
                insight = self.load_insight(metadata['file'])
                recent.append(insight)

        return recent
```

## Data Models

### Core Models

```python
@dataclass
class Insight:
    """Base insight class"""
    id: str
    session_id: str
    type: str  # agent, tool, repl
    timestamp: datetime
    severity: float  # 0-1

@dataclass
class AgentInsight(Insight):
    """Agent-specific insight"""
    friction_points: List[FrictionPoint]
    context_issues: List[str]
    capability_gaps: List[str]
    suggestions: List[str]

@dataclass
class ReplInsight(Insight):
    """REPL session insight (priority)"""
    frustration_level: float
    task_complexity: float
    agent_usage: List[str]
    redirection_count: int
    opportunities: List[Opportunity]
    priority: bool = True

@dataclass
class Pattern:
    """Detected pattern across insights"""
    id: str
    type: str
    frequency: int
    impact_score: float
    affected_sessions: List[str]
    description: str

@dataclass
class ImprovementPlan:
    """Plan for system improvement"""
    id: str
    title: str
    description: str
    patterns: List[Pattern]
    insights: List[Insight]
    changes: List[CodeChange]
    roi_score: float
    complexity: str  # low, medium, high

@dataclass
class FrictionPoint:
    """Identified friction in session"""
    type: str
    value: Any
    description: str
    suggestion: Optional[str]
```

## Processing Flows

### Reflection Flow

```
1. Event Occurs
   │
   ├─→ Hook Triggered
   │   ├─→ Recursion Check
   │   └─→ Event Capture
   │
   ├─→ Async Task Spawned
   │   ├─→ Non-blocking
   │   └─→ Background Processing
   │
   ├─→ Session Analysis
   │   ├─→ Metric Extraction
   │   ├─→ Friction Detection
   │   └─→ Claude Analysis
   │
   └─→ Insight Storage
       ├─→ Save to File
       └─→ Update Index
```

### Improvement Flow

```
1. Pattern Detection
   │
   ├─→ Insight Aggregation
   │   ├─→ Time Window
   │   └─→ Correlation
   │
   ├─→ Improvement Generation
   │   ├─→ Claude Planning
   │   ├─→ Validation
   │   └─→ Prioritization
   │
   ├─→ Implementation
   │   ├─→ Code Generation
   │   ├─→ Branch Creation
   │   └─→ PR Submission
   │
   └─→ Tracking
       ├─→ Mark Applied
       └─→ Impact Measurement
```

## Hook Integration

### Hook Registration

```python
# In .claude/hooks/python/on_repl_stop.py
import asyncio
from team_coach.hooks import ReflectionHooks

hooks = ReflectionHooks()

def execute_hook(context):
    """Hook entry point"""
    try:
        # Non-blocking reflection
        asyncio.create_task(
            hooks.on_repl_stop(context)
        )
    except Exception as e:
        # Never break user flow
        logger.error(f"Team Coach hook failed: {e}")

    # Continue normal hook processing
    return context
```

### Hook Configuration

```yaml
# .claude/hooks/config.yaml
team_coach:
  enabled: true
  hooks:
    agent_stop: true
    tool_use: true
    repl_stop: true  # Priority

  thresholds:
    min_session_duration: 60  # seconds
    analysis_threshold: 0.3   # severity
    pattern_min_frequency: 3

  recursion_prevention:
    session_prefix: "tc_"
    min_interval: 300  # seconds
    check_env_var: true
```

## Configuration

### Module Configuration

```yaml
team_coach:
  analysis:
    use_claude_sdk: true
    batch_size: 10
    max_retries: 3
    timeout: 30

  pattern_detection:
    time_window: 24  # hours
    min_pattern_frequency: 3
    correlation_threshold: 0.7

  improvements:
    auto_generate: true
    auto_create_pr: false  # Require approval
    max_improvements_per_day: 5
    complexity_limit: "medium"

  storage:
    path: .data/team_coach/
    retention_days: 90
    compression: true
    max_size_mb: 1000

  github:
    repository: "AgenticCoding"
    branch_prefix: "team-coach/"
    pr_labels: ["team-coach", "auto-improvement"]
```

## Performance Considerations

### Optimization Strategies

1. **Async Everything**: All reflection operations are async
2. **Fire and Forget**: Hooks return immediately
3. **Batch Processing**: Group insights for pattern detection
4. **Selective Analysis**: Only analyze high-severity friction
5. **Caching**: Cache Claude SDK responses

### Performance Targets

- Hook execution: < 100ms
- Async task spawn: < 10ms
- Insight analysis: < 5 seconds
- Pattern detection: < 10 seconds
- Improvement generation: < 30 seconds

## Testing Strategy

### Unit Tests

```python
class TestRecursionGuard:
    """Test recursion prevention"""

    def test_detects_reflection_session(self):
        """Verify reflection session detection"""

    def test_enforces_time_interval(self):
        """Verify time-based prevention"""

    def test_environment_check(self):
        """Verify environment variable check"""
```

### Integration Tests

```python
class TestTeamCoachIntegration:
    """Test complete flow"""

    async def test_repl_reflection_flow(self):
        """Test REPL session reflection"""

    async def test_pattern_to_pr_flow(self):
        """Test improvement generation"""

    async def test_recursion_prevention(self):
        """Verify no recursive loops"""
```

## Security Considerations

### Data Protection
- Sanitize user code from insights
- Never expose private information in PRs
- Encrypt sensitive session data
- Validate all generated code

### Access Control
- Restrict improvement generation
- Require approval for PRs
- Audit all improvements
- Control hook activation

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
1. Implement recursion guard
2. Create basic hooks
3. Set up insight storage
4. Basic session analysis

### Phase 2: Analysis (Week 2)
1. Implement Claude SDK integration
2. Build friction detection
3. Create pattern detector
4. Develop insight aggregation

### Phase 3: Improvement (Week 3)
1. Build improvement generator
2. Implement GitHub integration
3. Create PR automation
4. Add validation layer

### Phase 4: Polish (Week 4)
1. Optimize performance
2. Add configuration UI
3. Create dashboards
4. Complete testing

## Success Metrics

### Key Performance Indicators
- Zero impact on user performance (< 1% overhead)
- Generate 1+ improvement per 100 sessions
- 80% of improvements successfully merged
- 50% reduction in friction points over 3 months

### Quality Metrics
- 100% recursion prevention effectiveness
- < 5% false positive friction detection
- 90% improvement validation accuracy
- 95% PR build success rate

## Future Enhancements

### Planned Features
1. **ML Pattern Prediction**: Predict issues before they occur
2. **Team Insights**: Aggregate across team members
3. **Real-time Suggestions**: Offer improvements during sessions
4. **Visual Analytics**: Dashboard for insight exploration
5. **External Integrations**: Connect to other dev tools

### Extension Points
- Custom analyzers for specific workflows
- Plugin system for improvement generators
- Additional hook points
- External data sources

## Module Contract

### Inputs
- Hook event data (agent, tool, REPL sessions)
- Session contexts and metrics
- Configuration parameters

### Outputs
- Reflection insights with severity scores
- Detected patterns across sessions
- Improvement plans and PRs
- Performance metrics

### Side Effects
- Creates async background tasks
- Writes to `.data/team_coach/`
- Creates GitHub branches and PRs
- Emits metrics and logs

### Guarantees
- Never blocks user interactions
- Prevents recursive reflection loops
- Graceful degradation on failures
- Maintains data consistency
