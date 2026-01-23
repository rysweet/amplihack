# Power-Steering Mode Architecture

## Executive Summary

Power-steering mode is a stop hook enhancement that analyzes session transcripts against 21 considerations to determine if work is truly complete before allowing session termination. It blocks incomplete sessions with actionable continuation prompts and generates comprehensive summaries for completed sessions.

## Design Philosophy

- **Ruthlessly Simple**: Single-purpose module with clear contract
- **Fail-Open**: Never block users due to bugs - always allow stop on errors
- **Zero-BS**: No stubs, no TODOs, every function works or doesn't exist
- **Modular**: Self-contained "brick" that plugs into existing stop hook

## System Architecture

```
┌─────────────────────────────────────────────────┐
│ Claude Code Session Stop Request               │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ stop.py (Hook Orchestrator)                    │
│                                                 │
│  1. Lock Check                                  │
│  2. Reflection Check                            │
│  3. Power-Steering Check ◄── NEW               │
│  4. Neo4j Cleanup                               │
│                                                 │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ PowerSteeringChecker Module                    │
│                                                 │
│  Input: transcript_path, session_id            │
│  Output: PowerSteeringResult                    │
│                                                 │
│  Flow:                                          │
│  1. Check if disabled                           │
│  2. Check semaphore (prevent recursion)        │
│  3. Detect Q&A session                          │
│  4. Load transcript                             │
│  5. Analyze against 21 considerations          │
│  6. Generate decision + prompt OR summary      │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Core Components

### 1. PowerSteeringChecker (Main Module)

**File**: `~/.amplihack/.claude/tools/amplihack/hooks/power_steering_checker.py`

**Responsibilities**:

- Analyze session transcript completeness
- Evaluate 21 considerations across 5 categories
- Generate continuation prompts for incomplete work
- Generate summaries for completed sessions
- Manage semaphores to prevent recursion

**Key Methods**:

- `check(transcript_path, session_id) -> PowerSteeringResult`
- `_analyze_considerations(transcript, session_id) -> ConsiderationAnalysis`
- `_generate_continuation_prompt(analysis) -> str`
- `_generate_summary(transcript, analysis) -> str`

### 2. Stop Hook Integration

**File**: `~/.amplihack/.claude/tools/amplihack/hooks/stop.py` (MODIFIED)

**Changes**:

- Add `PowerSteeringChecker` import
- Add `_should_run_power_steering()` method
- Add power-steering check after reflection
- Add error handling (fail-open)
- Add summary display

### 3. Configuration System

**File**: `~/.amplihack/.claude/tools/amplihack/.power_steering_config` (NEW)

**Format**: JSON with defaults

```json
{
  "enabled": true,
  "skip_qa_sessions": true,
  "considerations_file": "default.json",
  "summary_enabled": true,
  "timeout_seconds": 30
}
```

### 4. Control Mechanisms

**Three-Layer Disable System** (priority order):

1. Semaphore file: `~/.amplihack/.claude/runtime/power-steering/.disabled` (highest)
2. Environment variable: `AMPLIHACK_SKIP_POWER_STEERING` (medium)
3. Config file: `{"enabled": false}` (lowest)

**Slash Commands**:

- `/amplihack:disable-power-steering` - Create semaphore
- `/amplihack:enable-power-steering` - Remove semaphore
- `/amplihack:power-steering-status` - Show status
- `/amplihack:power-steering-config` - Manage config

## 21 Considerations Framework

### Category 1: Session Completion & Progress (8 checks)

1. Autonomous question detection
2. Objective completion verification
3. TODO items completion
4. Documentation updates
5. Tutorial creation for large features
6. PowerPoint overview for large features
7. Next steps scope validation
8. Documentation organization

### Category 2: Workflow Process Adherence (2 checks)

9. Investigation workflow completion
10. Development workflow adherence

### Category 3: Code Quality & Philosophy (2 checks)

11. Philosophy adherence (zero-BS)
12. No shortcuts (disabled checks)

### Category 4: Testing & Local Validation (2 checks)

13. Local testing execution
14. UI interactive testing

### Category 5: PR Content & Quality (4 checks)

15. No unrelated changes
16. No root directory files
17. PR description currency
18. Review concern resolution

### Category 6: CI/CD & Mergeability (3 checks)

19. Branch currency (rebase needed?)
20. Pre-commit/CI alignment
21. CI status and mergeability

## Data Flow

### Input

- **transcript_path**: Path to session JSONL transcript
- **session_id**: Unique session identifier

### Output (PowerSteeringResult)

```python
@dataclass
class PowerSteeringResult:
    decision: Literal["approve", "block"]
    reasons: List[str]
    continuation_prompt: Optional[str]
    summary: Optional[str]
```

### Transcript Analysis

1. Load JSONL file
2. Parse messages (role, content, tool_calls)
3. Extract metadata (files changed, tests run, git operations)
4. Apply 21 checkers
5. Aggregate results by severity (blocker vs warning)

### Decision Logic

```python
if any_blocker_failed:
    return block_with_continuation_prompt
elif only_warnings_failed:
    return approve_with_warnings_in_summary
else:
    return approve_with_summary
```

## File Structure

```
.claude/
├── tools/amplihack/
│   ├── hooks/
│   │   ├── power_steering_checker.py   # NEW: Main module
│   │   └── stop.py                     # MODIFIED: Integration
│   ├── .power_steering_config          # NEW: Configuration
│   └── considerations/                 # NEW: Phase 2
│       └── default.json                # 21 considerations
├── commands/
│   ├── amplihack_disable_power_steering.md  # NEW
│   ├── amplihack_enable_power_steering.md   # NEW
│   ├── amplihack_power_steering_status.md   # NEW
│   └── amplihack_power_steering_config.md   # NEW
└── runtime/power-steering/             # NEW: Runtime data
    ├── .disabled                       # Disable semaphore
    ├── .{session_id}_completed         # Per-session semaphore
    └── {session_id}/
        └── summary.md                  # Session summary

Specs/                                  # Architecture specs
├── power_steering_architecture.md      # This file
├── power_steering_checker.md           # Module spec
├── power_steering_config.md            # Config spec
├── considerations_format.md            # Considerations spec
├── stop_py_integration.md              # Integration spec
├── control_mechanisms.md               # Control system spec
├── implementation_phases.md            # Implementation plan
└── edge_cases.md                       # Edge case handling
```

## Implementation Phases

### Phase 1: MVP (2-3 days)

- Core PowerSteeringChecker module
- Top 5 critical checkers
- Basic integration with stop.py
- Environment variable and semaphore disable
- Slash commands for enable/disable

**Deliverables**: Working power-steering with essential checks

### Phase 2: Full Implementation (3-4 days)

- All 21 consideration checkers
- Comprehensive test coverage
- Enhanced Q&A detection
- Rich continuation prompts

**Deliverables**: Complete consideration set

### Phase 3: Enhanced UX (2 days)

- Rich session summaries
- Status command
- Pretty console output
- Statistics tracking

**Deliverables**: Production-quality user experience

### Phase 4: External Configuration (2 days)

- Config file support with validation
- External considerations JSON
- Config management command
- Custom consideration files

**Deliverables**: Flexible configuration system

### Phase 5: Production Hardening (2-3 days)

- Performance optimization (<300ms target)
- Comprehensive error handling
- Metrics and monitoring
- Documentation

**Deliverables**: Production-ready system

### Phase 6: Rollout (1 week)

- Gradual enablement (disabled → opt-in → default)
- User feedback collection
- Iteration based on metrics

**Deliverables**: Successfully deployed feature

**Total Time**: 5-6 weeks

## Error Handling Strategy

### Core Principle: Fail-Open

Power-steering NEVER blocks users due to bugs. On any error:

1. Log error with full context
2. Track metric for monitoring
3. Return `approve` decision
4. Continue session stop

### Error Categories

- **Transcript errors**: Missing, malformed, too large → approve
- **Checker crashes**: Individual checker fails → treat as satisfied
- **Timeouts**: Analysis too slow → approve
- **File system errors**: Can't write semaphore/summary → continue
- **Configuration errors**: Invalid config → use defaults

### Timeout Protection

- Per-checker timeout: 5 seconds
- Total analysis timeout: 30 seconds (configurable)
- On timeout: approve and log

## Security Considerations

### Path Safety

- Validate all file paths within project_root
- Prevent directory traversal attacks
- Resolve symlinks safely

### Transcript Privacy

- Transcripts may contain sensitive data
- Never send to external services
- All analysis local-only

### Semaphore Files

- Check age to prevent staleness
- Handle race conditions gracefully
- Clean up old semaphores periodically

## Performance Targets

### Latency

- **P50**: <100ms
- **P95**: <300ms
- **P99**: <1000ms
- **Timeout**: 30 seconds (hard limit)

### Resource Usage

- **Memory**: <50MB for transcript analysis
- **Disk**: <1MB per session (summary + semaphores)
- **CPU**: Minimal (mostly I/O bound)

### Optimizations

- Stream large transcripts instead of loading all
- Cache transcript metadata
- Parallel checker execution (if beneficial)
- Early exit on disable checks

## Testing Strategy

### Unit Tests

- Each consideration checker independently
- Configuration loading with edge cases
- Semaphore handling (creation, detection, staleness)
- Q&A session detection
- Prompt and summary generation

### Integration Tests

- Full flow with real transcript files
- stop.py integration
- Disable mechanisms
- Error handling paths

### Edge Case Tests

- Malformed transcripts
- Missing files
- Permission errors
- Timeouts
- Concurrent execution

### Performance Tests

- Large transcripts (>10MB)
- Many considerations
- Timeout scenarios
- Stress testing (1000+ sessions)

## Success Metrics

### Technical

- **Uptime**: >95% (no crashes)
- **Latency**: P95 <300ms
- **Error rate**: <1%
- **False positive rate**: <5%

### User Experience

- **Correct blocks**: >70% of incomplete sessions identified
- **False positives**: <5% (blocking complete sessions)
- **Disable rate**: <15% (users disabling feature)
- **User satisfaction**: >60% positive feedback

### Impact

- **Incomplete PRs**: Reduce by >30%
- **Review cycles**: Reduce by >20%
- **CI failures**: Reduce by >15%

## Rollback Strategy

### Immediate (<5 min)

```bash
export AMPLIHACK_SKIP_POWER_STEERING=1
```

### Short-term (<1 hour)

```json
{ "enabled": false }
```

### Long-term (<1 day)

Remove power-steering call from stop.py

## Dependencies

### Required

- Stop hook system working
- Transcript files accessible
- Runtime directory writable
- Session ID available

### Optional

- Claude Code CLI access (for --no-power-steering flag)
- Configuration file (defaults work without)
- External considerations file (hardcoded fallback)

## Integration Points

### Upstream (What Calls Us)

- `stop.py` hook orchestrator

### Downstream (What We Call)

- Transcript JSONL parser (built-in)
- File system operations (stdlib)
- Logging and metrics (HookProcessor pattern)

### External Systems (None)

- All analysis is local
- No network calls
- No external services

## Extensibility

### Adding New Considerations

1. Add to CONSIDERATIONS list (Phase 1) or JSON file (Phase 2)
2. Implement `_check_<consideration_id>()` method
3. Add unit tests
4. Update documentation

### Custom Consideration Files

1. Copy `default.json` to `custom.json`
2. Modify metadata (severity, description)
3. Update config: `"considerations_file": "custom.json"`
4. Note: Custom checkers require code changes

### Plugin Architecture (Future)

- Consider allowing external checker plugins
- Dynamic loading of checker modules
- Versioning and compatibility checks

## Documentation

### User-Facing

- Feature overview and benefits
- How to enable/disable
- Configuration reference
- Troubleshooting guide
- FAQ

### Developer-Facing

- Architecture (this document)
- Module specifications
- Integration guide
- Testing guide
- Contribution guidelines

### Operational

- Deployment procedures
- Monitoring and alerting
- Incident response
- Performance tuning

## Related Documents

1. **power_steering_checker.md**: Detailed module specification
2. **power_steering_config.md**: Configuration file format
3. **considerations_format.md**: 21 considerations structure
4. **stop_py_integration.md**: Integration with existing stop hook
5. **control_mechanisms.md**: Enable/disable system
6. **implementation_phases.md**: Development roadmap
7. **edge_cases.md**: Edge case handling and error recovery

## Conclusion

Power-steering mode follows amplihack's philosophy of ruthless simplicity:

- **Single Responsibility**: Determine if work is complete
- **Clear Contract**: Input transcript, output decision + prompt/summary
- **Fail-Open**: Never block users on bugs
- **Modular**: Self-contained brick that plugs into stop hook
- **Zero-BS**: No stubs, every function works

The architecture is designed for:

- **Reliability**: Comprehensive error handling
- **Performance**: <300ms P95 latency
- **Maintainability**: Clear module boundaries
- **Extensibility**: Easy to add considerations
- **User Control**: Multiple disable mechanisms

Ready for builder agent implementation.
