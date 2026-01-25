# Power-Steering Mode Architecture - Summary

## Overview

I've designed a complete architecture for power-steering mode that follows amplihack's philosophy of ruthless simplicity. The system analyzes session transcripts against 21 considerations to prevent premature session stops, ensuring work is truly complete before allowing termination.

## Key Design Decisions

### 1. Hybrid Architecture (Option C)

**Decision**: Extract power-steering into separate module, call from stop.py

**Rationale**:

- Clean separation follows "brick" philosophy
- Guaranteed execution order (after reflection)
- Easy to test, disable, and maintain
- No risk of execution order issues

**Alternatives Considered**:

- Modify stop.py directly (rejected: increases complexity)
- Separate stop hook (rejected: coordination issues)

### 2. Fail-Open Error Handling

**Decision**: Always approve stop on errors, never block users due to bugs

**Rationale**:

- Power-steering is enhancement, not critical path
- Better false negatives than false positives
- User experience paramount

**Implementation**:

- Try-catch around all operations
- Timeout protection (5s per checker, 30s total)
- Detailed error logging for debugging

### 3. Three-Layer Control System

**Decision**: Semaphore file > Environment variable > Config file

**Rationale**:

- Multiple disable methods for different use cases
- Clear priority ordering
- Easy emergency disable
- Persistent and session-based options

**Use Cases**:

- Semaphore: Persistent project disable
- Env var: Session-specific or global disable
- Config: Project preferences

### 4. Hardcoded Then External Considerations

**Decision**: Phase 1 hardcoded, Phase 2 external JSON file

**Rationale**:

- MVP faster with hardcoded
- External file enables customization without code changes
- Validation ensures safety

**Migration Path**: Seamless - external file takes precedence, hardcoded fallback

## Architecture Components

### Core Module: PowerSteeringChecker

**Location**: `~/.amplihack/.claude/tools/amplihack/hooks/power_steering_checker.py`

**Contract**:

```python
Input:  transcript_path: Path, session_id: str
Output: PowerSteeringResult(decision, reasons, continuation_prompt, summary)
```

**Flow**:

1. Check disabled (config/env/semaphore) → skip if disabled
2. Check semaphore (recursion prevention) → skip if already ran
3. Detect Q&A session → skip if informational
4. Load transcript → fail-open if errors
5. Analyze 21 considerations → parallel evaluation
6. Generate decision:
   - Block + continuation prompt (if blockers failed)
   - Approve + summary (if all satisfied)

### Integration Point: stop.py Modification

**Changes Required**:

1. Import PowerSteeringChecker
2. Add `_should_run_power_steering()` helper
3. Add power-steering check after reflection
4. Display summary on approval
5. Log metrics

**Execution Order**:
Lock → Reflection → **Power-Steering (NEW)** → Neo4j → Approve

### 21 Considerations Framework

**5 Categories**:

1. Session Completion & Progress (8 checks)
2. Workflow Process Adherence (2 checks)
3. Code Quality & Philosophy (2 checks)
4. Testing & Local Validation (2 checks)
5. PR Content & Quality (4 checks)
6. CI/CD & Mergeability (3 checks)

**Priority Checks (MVP Phase 1)**:

1. Autonomous question - Can agent answer without asking user?
2. Objective complete - Was original request fulfilled?
3. TODOs complete - Any incomplete TODO items?
4. Local testing - Were tests run and passing?
5. CI status - Is CI passing or PR mergeable?

**Severity Levels**:

- **Blocker**: Must be satisfied to allow stop
- **Warning**: Inform user but don't block

## File Structure

```
.claude/tools/amplihack/
├── hooks/
│   ├── power_steering_checker.py   # NEW: 800+ line module
│   └── stop.py                     # MODIFIED: +50 lines
├── .power_steering_config          # NEW: JSON config
└── considerations/                 # NEW: Phase 2
    └── default.json                # 21 considerations metadata

.claude/commands/
├── amplihack_disable_power_steering.md   # NEW
├── amplihack_enable_power_steering.md    # NEW
├── amplihack_power_steering_status.md    # NEW
└── amplihack_power_steering_config.md    # NEW

.claude/runtime/power-steering/
├── .disabled                       # Disable semaphore
├── .{session_id}_completed         # Per-session semaphore
└── {session_id}/summary.md         # Session summary

Specs/
├── power_steering_architecture.md      # Complete architecture (THIS)
├── power_steering_checker.md           # 800+ line module spec
├── power_steering_config.md            # Config format
├── considerations_format.md            # 21 considerations details
├── stop_py_integration.md              # Integration guide
├── control_mechanisms.md               # Control system
├── implementation_phases.md            # 6-phase roadmap
└── edge_cases.md                       # Error handling
```

## Implementation Phases (5-6 Weeks)

### Phase 1: MVP (2-3 days)

- Core module with top 5 checkers
- Basic stop.py integration
- Disable mechanisms
- Enable/disable commands

**Validation**: Blocks incomplete work, allows complete work, doesn't crash

### Phase 2: Full Implementation (3-4 days)

- All 21 consideration checkers
- Comprehensive tests
- Enhanced Q&A detection

**Validation**: All checkers working, <5% false positives

### Phase 3: Enhanced UX (2 days)

- Rich summaries
- Status command
- Pretty output
- Statistics

**Validation**: User-friendly output, helpful prompts

### Phase 4: External Configuration (2 days)

- Config file support
- External considerations JSON
- Config management

**Validation**: Customizable without code changes

### Phase 5: Production Hardening (2-3 days)

- Performance optimization (<300ms)
- Error handling
- Metrics
- Documentation

**Validation**: Production-ready quality

### Phase 6: Rollout (1 week)

- Disabled by default → Opt-in → Default enabled
- User feedback
- Iteration

**Validation**: Successful deployment, positive user feedback

## Control Mechanisms

### Disable Methods (Priority Order)

1. **Semaphore File** (Highest Priority)

   ```bash
   /amplihack:disable-power-steering
   # Creates .claude/runtime/power-steering/.disabled
   ```

2. **Environment Variable** (Medium Priority)

   ```bash
   export AMPLIHACK_SKIP_POWER_STEERING=1
   ```

3. **Config File** (Lowest Priority)
   ```json
   { "enabled": false }
   ```

### Enable/Disable Commands

```bash
/amplihack:disable-power-steering    # Create semaphore
/amplihack:enable-power-steering     # Remove semaphore
/amplihack:power-steering-status     # Show current state
/amplihack:power-steering-config     # Manage config
```

### CLI Flag (If Possible)

```bash
claude --no-power-steering
```

## Error Handling Strategy

### Core Principle: Fail-Open

All errors result in **approve** decision with logging.

### Error Categories & Responses

| Error Type           | Response           | Rationale                          |
| -------------------- | ------------------ | ---------------------------------- |
| Missing transcript   | Approve            | Can't analyze what doesn't exist   |
| Malformed transcript | Approve            | Don't block on bad data            |
| Checker crash        | Treat as satisfied | One bug shouldn't break system     |
| Timeout (checker)    | Treat as satisfied | Don't hang stop hook               |
| Timeout (overall)    | Approve            | User must be able to stop          |
| File system error    | Continue           | Semaphore/summary are nice-to-have |
| Config error         | Use defaults       | Bad config shouldn't crash         |

### Timeout Protection

- **Per-checker**: 5 seconds
- **Total analysis**: 30 seconds (configurable)
- **On timeout**: Approve and log

## Performance Targets

| Metric       | Target  | Max   |
| ------------ | ------- | ----- |
| P50 latency  | <100ms  | -     |
| P95 latency  | <300ms  | -     |
| P99 latency  | <1000ms | -     |
| Hard timeout | 30s     | 60s   |
| Memory usage | <50MB   | 100MB |

## Success Metrics

### Technical

- Uptime: >95%
- Error rate: <1%
- False positive rate: <5%
- P95 latency: <300ms

### User Experience

- Correct blocks: >70%
- False positives: <5%
- Disable rate: <15%
- User satisfaction: >60%

### Impact

- Reduce incomplete PRs by >30%
- Reduce review cycles by >20%
- Reduce CI failures by >15%

## Edge Cases Handled

### Transcript Issues

- Missing file → approve
- Empty file → approve
- Malformed JSON → parse what we can, approve if too broken
- Very large (>10MB) → skip analysis, approve
- Wrong structure → skip invalid messages, continue

### Session Issues

- Missing session ID → generate fallback
- Duplicate IDs → first write wins
- Stale semaphores → ignore if >1 hour old

### Checker Issues

- Missing method → skip checker, don't block
- Checker crash → treat as satisfied
- Checker timeout → treat as satisfied
- All timeout → approve

### File System Issues

- Permission errors → log and continue
- Disk full → log and continue
- Symlink attacks → validate paths

### Recursive Power-Steering

- Already ran → skip via semaphore
- Power-steering prompt detected → skip
- Infinite loop → broken by semaphore

## Security Considerations

1. **Path Safety**: Validate all paths within project_root
2. **Transcript Privacy**: All analysis local, never sent externally
3. **Semaphore Safety**: Check age, handle race conditions
4. **Input Validation**: Sanitize all config values

## Testing Strategy

### Unit Tests

- Each of 21 checkers independently
- Configuration loading edge cases
- Semaphore handling
- Q&A detection
- Prompt/summary generation

### Integration Tests

- Full flow with real transcripts
- stop.py integration
- Disable mechanisms
- Error paths

### Edge Case Tests

- All error scenarios
- Concurrent execution
- Large transcripts
- Timeouts

### Performance Tests

- Large transcripts (>10MB)
- Many checkers
- 1000+ session scenarios

## Rollback Strategy

### Immediate (<5 min)

```bash
export AMPLIHACK_SKIP_POWER_STEERING=1
```

### Short-term (<1 hour)

```bash
/amplihack:disable-power-steering
# or edit config: {"enabled": false}
```

### Long-term (<1 day)

Remove power-steering call from stop.py

## Dependencies

### Required

- Stop hook system working
- Transcript files in JSONL format
- Runtime directory writable
- Session ID available

### Optional

- Claude Code CLI access (for --no-power-steering)
- Config file (defaults without)
- External considerations (hardcoded fallback)

## What's NOT Included (Clarifications)

1. **No Claude Code Agent SDK**: Investigation showed it's not actually used - stop hooks are just Python scripts returning JSON
2. **No External Services**: All analysis is local, no network calls
3. **No ML Models (Phase 1)**: Simple heuristics for Q&A detection, ML optional in Phase 5
4. **No Complex Frameworks**: Just Python stdlib + existing patterns

## Specification Documents

I've created 8 comprehensive specification documents:

1. **power_steering_architecture.md** (185 lines)
   - Executive summary and complete architecture
   - System design and integration points
   - Success metrics and rollout strategy

2. **power_steering_checker.md** (486 lines)
   - Complete module specification
   - All 21 consideration checkers
   - Implementation details and contract

3. **power_steering_config.md** (91 lines)
   - Configuration file format
   - Disable methods
   - Slash commands

4. **considerations_format.md** (343 lines)
   - Phase 1: Hardcoded structure
   - Phase 2: External JSON schema
   - All 21 considerations with details

5. **stop_py_integration.md** (133 lines)
   - Exact changes to stop.py
   - Integration points
   - Error handling

6. **control_mechanisms.md** (367 lines)
   - Three-layer disable system
   - Slash command implementations
   - CLI flag integration

7. **implementation_phases.md** (581 lines)
   - 6-phase implementation plan
   - Task breakdown with checklists
   - Validation criteria per phase

8. **edge_cases.md** (784 lines)
   - 9 categories of edge cases
   - Error handling patterns
   - Recovery procedures

**Total**: 2,970 lines of detailed specifications

## Next Steps

### 1. Review & Approval

- Review this architecture with stakeholders
- Validate design decisions
- Approve phases and timeline

### 2. Delegation to Builder Agent

- Hand off specifications to builder agent
- Builder implements Phase 1 (MVP)
- Architect reviews for philosophy compliance

### 3. Testing Infrastructure

- Set up test fixtures (transcript files)
- Create test scenarios
- Prepare integration test environment

### 4. Gradual Rollout

- Deploy with `enabled: false`
- Internal team testing
- Beta user testing
- Production enablement

## Questions for Stakeholder Review

1. **Scope**: Is the 21-consideration set comprehensive? Missing anything critical?
2. **Timeline**: Is 5-6 weeks acceptable for full implementation?
3. **Phasing**: Should we deploy Phase 1 (5 checkers) first or wait for all 21?
4. **Defaults**: Should power-steering be enabled or disabled by default initially?
5. **CLI**: Do we have access to modify Claude Code CLI for --no-power-steering flag?

## Conclusion

The power-steering architecture is:

- **Simple**: Single-purpose module with clear boundaries
- **Safe**: Fail-open design, never blocks users on bugs
- **Flexible**: Multiple control mechanisms, customizable
- **Fast**: <300ms P95 latency target
- **Testable**: Comprehensive test strategy
- **Maintainable**: Clean module structure, extensive documentation

All specifications are complete and ready for builder agent implementation.

---

**Architecture Files Created**:

- /home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/Specs/power_steering_architecture.md
- /home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/Specs/power_steering_checker.md
- /home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/Specs/power_steering_config.md
- /home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/Specs/considerations_format.md
- /home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/Specs/stop_py_integration.md
- /home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/Specs/control_mechanisms.md
- /home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/Specs/implementation_phases.md
- /home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/Specs/edge_cases.md
- /home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/Specs/POWER_STEERING_SUMMARY.md (this file)
