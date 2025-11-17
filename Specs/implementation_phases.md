# Implementation Phases

## Purpose

Break power-steering implementation into manageable phases with clear milestones.

## Phase 0: Foundation (Prerequisites)

**Goal**: Ensure all prerequisites are in place

**Tasks**:

- [ ] Verify stop hook pattern understanding
- [ ] Review existing stop.py implementation
- [ ] Understand transcript JSONL format
- [ ] Document current stop hook flow
- [ ] Identify integration points

**Deliverables**:

- Architecture specification (this document)
- Module specifications
- Integration plan

**Validation**:

- All specs reviewed by architect
- Builder agent has clear implementation path
- No ambiguities in design

---

## Phase 1: MVP - Core Functionality

**Goal**: Basic power-steering that blocks/allows with minimal consideration set

**Duration**: 2-3 days

### Tasks

#### 1.1 Core Module (power_steering_checker.py)

- [ ] Create `PowerSteeringChecker` class
- [ ] Implement `check()` main entry point
- [ ] Add config loading (with defaults)
- [ ] Add disable mechanism checks (env var, semaphore)
- [ ] Implement semaphore handling (prevent recursion)
- [ ] Add transcript loading
- [ ] Implement Q&A session detection (simple heuristics)

#### 1.2 Consideration Framework

- [ ] Hardcode 21 considerations in CONSIDERATIONS list
- [ ] Implement `ConsiderationAnalysis` dataclass
- [ ] Create `_analyze_considerations()` method
- [ ] Implement `_check_consideration()` dispatcher

#### 1.3 Priority Checkers (Top 5 Most Critical)

Implement these checkers first:

1. **\_check_autonomous_question** (Session Completion)
   - Check if last message asks question
   - Look for "?" in assistant message
   - Check if answer could be in files

2. **\_check_objective_complete** (Session Completion)
   - Extract objective from first user message
   - Check for completion indicators
   - Compare with last assistant message

3. **\_check_todos_complete** (Session Completion)
   - Find last TodoWrite tool call
   - Check all todos are "completed"

4. **\_check_local_testing** (Testing)
   - Look for pytest/npm test/cargo test calls
   - Verify exit code = 0
   - Check for "PASSED" in output

5. **\_check_ci_status** (CI/CD)
   - Look for CI status checks
   - Verify all green or waiting
   - Check for failures

#### 1.4 Output Generation

- [ ] Implement `_generate_continuation_prompt()`
- [ ] Basic prompt generation grouped by category
- [ ] Implement `_generate_summary()` (minimal version)
- [ ] Add summary writing to file

#### 1.5 Integration with stop.py

- [ ] Add import of PowerSteeringChecker
- [ ] Add `_should_run_power_steering()` method
- [ ] Add power-steering check after reflection
- [ ] Add error handling (fail-open)
- [ ] Add metric logging

#### 1.6 Control Mechanisms (Basic)

- [ ] Environment variable support
- [ ] Semaphore file support
- [ ] Create `/amplihack:disable-power-steering` command
- [ ] Create `/amplihack:enable-power-steering` command

### Deliverables

- [ ] `power_steering_checker.py` with core functionality
- [ ] Modified `stop.py` with integration
- [ ] Two slash commands
- [ ] Basic unit tests for top 5 checkers

### Validation Criteria

- [ ] Power-steering runs on session stop
- [ ] Blocks when TODO incomplete
- [ ] Blocks when tests not run
- [ ] Allows when work complete
- [ ] Can be disabled via env var
- [ ] Can be disabled via slash command
- [ ] Doesn't crash stop hook
- [ ] Fail-open on errors

### Success Metrics

- [ ] 80% of incomplete sessions correctly blocked
- [ ] 0% false positives (blocking complete sessions)
- [ ] <100ms overhead on stop hook
- [ ] Zero crashes in testing

---

## Phase 2: Full Consideration Set

**Goal**: Implement all 21 consideration checkers

**Duration**: 3-4 days

### Tasks

#### 2.1 Session Completion Checkers (3 remaining)

- [ ] \_check_docs_updated
- [ ] \_check_tutorial_needed
- [ ] \_check_powerpoint_needed
- [ ] \_check_next_steps_scope
- [ ] \_check_docs_organized

#### 2.2 Workflow Checkers (2 total)

- [ ] \_check_investigation_workflow
- [ ] \_check_dev_workflow_complete

#### 2.3 Code Quality Checkers (2 total)

- [ ] \_check_philosophy_adherence
- [ ] \_check_no_shortcuts

#### 2.4 Testing Checker (1 remaining)

- [ ] \_check_ui_testing

#### 2.5 PR Content Checkers (4 total)

- [ ] \_check_no_unrelated_changes
- [ ] \_check_no_root_files
- [ ] \_check_pr_description_current
- [ ] \_check_review_addressed

#### 2.6 CI/CD Checkers (2 remaining)

- [ ] \_check_branch_current
- [ ] \_check_precommit_ci_match

### Deliverables

- [ ] All 21 checkers implemented
- [ ] Comprehensive unit tests for each checker
- [ ] Test fixtures for various transcript patterns
- [ ] Integration tests with real transcripts

### Validation Criteria

- [ ] All checkers execute without errors
- [ ] Each checker has >80% accuracy on test data
- [ ] False positive rate <5%
- [ ] Performance: <500ms for full analysis

---

## Phase 3: Enhanced Output & UX

**Goal**: Improve user experience with rich output and summaries

**Duration**: 2 days

### Tasks

#### 3.1 Enhanced Continuation Prompts

- [ ] Add specific actions for each consideration
- [ ] Include relevant file paths
- [ ] Add links to documentation
- [ ] Format with markdown for readability

#### 3.2 Rich Session Summaries

- [ ] Extract objective clearly
- [ ] Summarize key actions taken
- [ ] List files changed with context
- [ ] Include test results with details
- [ ] Add metrics (LOC changed, files touched)
- [ ] Generate satisfaction checklist

#### 3.3 Summary Display

- [ ] Format summary with ASCII art borders
- [ ] Color coding (if terminal supports)
- [ ] Write to both console and file
- [ ] Add summary to session log directory

#### 3.4 Status Command

- [ ] Implement `/amplihack:power-steering-status`
- [ ] Show current enabled/disabled state
- [ ] Display configuration values
- [ ] Show statistics (blocked/approved counts)
- [ ] Recent activity log

### Deliverables

- [ ] Enhanced prompt generation
- [ ] Rich summary generation
- [ ] Pretty console output
- [ ] Status command

### Validation Criteria

- [ ] Prompts are actionable and specific
- [ ] Summaries accurately reflect session
- [ ] Output is readable and helpful
- [ ] Status command shows correct state

---

## Phase 4: Configuration & External Data

**Goal**: Move to external configuration and consideration files

**Duration**: 2 days

### Tasks

#### 4.1 Configuration File Support

- [ ] Create default `.power_steering_config`
- [ ] Implement config loading with defaults
- [ ] Add config validation
- [ ] Support for all config options
- [ ] Config merge logic (defaults + file + env)

#### 4.2 External Considerations File

- [ ] Define JSON schema for considerations
- [ ] Create `default.json` with all 21 considerations
- [ ] Implement consideration loading from file
- [ ] Add validation (required fields, valid enums)
- [ ] Support for custom consideration files

#### 4.3 Configuration Management

- [ ] Implement `/amplihack:power-steering-config` command
- [ ] Support show/set/reset operations
- [ ] Validate config changes
- [ ] Persist changes to file

### Deliverables

- [ ] Configuration file format specification
- [ ] Considerations JSON schema
- [ ] Config management command
- [ ] Default consideration files
- [ ] Migration from hardcoded to file-based

### Validation Criteria

- [ ] Config file loads correctly
- [ ] Defaults used when file missing
- [ ] Invalid config doesn't crash
- [ ] Custom consideration files work
- [ ] Config changes persist

---

## Phase 5: Advanced Features & Polish

**Goal**: Add advanced features and production hardening

**Duration**: 2-3 days

### Tasks

#### 5.1 Enhanced Q&A Detection

- [ ] ML-based session type classification (if feasible)
- [ ] Configurable Q&A detection thresholds
- [ ] Whitelist/blacklist for session types
- [ ] Manual override mechanism

#### 5.2 Performance Optimization

- [ ] Profile consideration checkers
- [ ] Optimize transcript parsing (streaming?)
- [ ] Cache transcript analysis
- [ ] Parallel consideration checking (if beneficial)
- [ ] Add timeout mechanism (30s default)

#### 5.3 Metrics & Monitoring

- [ ] Log all metrics to runtime directory
- [ ] Track consideration failure rates
- [ ] Monitor performance (timing)
- [ ] Error tracking and reporting
- [ ] Weekly summary reports

#### 5.4 CLI Integration

- [ ] Add `--no-power-steering` flag (if possible)
- [ ] Update help text
- [ ] Add to CLI documentation

#### 5.5 Documentation

- [ ] User guide for power-steering
- [ ] Configuration reference
- [ ] Consideration catalog with examples
- [ ] Troubleshooting guide
- [ ] FAQ

### Deliverables

- [ ] Optimized checkers
- [ ] Metrics system
- [ ] CLI integration (if possible)
- [ ] Complete documentation
- [ ] Production monitoring setup

### Validation Criteria

- [ ] <200ms average execution time
- [ ] All metrics tracked correctly
- [ ] CLI flag works (if added)
- [ ] Documentation is comprehensive
- [ ] Error handling is robust

---

## Phase 6: Production Rollout

**Goal**: Safe production deployment with monitoring

**Duration**: 1 week

### Tasks

#### 6.1 Testing & Validation

- [ ] End-to-end testing with real sessions
- [ ] Load testing (1000+ session scenarios)
- [ ] Edge case testing
- [ ] User acceptance testing with beta group

#### 6.2 Gradual Rollout

- [ ] Deploy with `enabled: false` by default
- [ ] Enable for internal team (opt-in)
- [ ] Monitor metrics for 1 week
- [ ] Enable for beta testers (opt-in)
- [ ] Monitor metrics for 1 week
- [ ] Enable by default for all users

#### 6.3 Monitoring & Feedback

- [ ] Set up alerting for errors
- [ ] Track user feedback
- [ ] Monitor false positive rate
- [ ] Track user disable rate
- [ ] Collect improvement suggestions

#### 6.4 Iteration

- [ ] Analyze failure patterns
- [ ] Tune consideration thresholds
- [ ] Add new considerations based on feedback
- [ ] Improve checker accuracy

### Deliverables

- [ ] Production-ready code
- [ ] Monitoring dashboards
- [ ] Rollout plan executed
- [ ] Feedback collection system
- [ ] Iteration roadmap

### Validation Criteria

- [ ] <1% error rate in production
- [ ] <10% user disable rate
- [ ] > 50% user satisfaction
- [ ] False positive rate <2%
- [ ] Performance targets met

---

## Rollback Plan

At any phase, if issues arise:

### Immediate Rollback (< 5 minutes)

```bash
export AMPLIHACK_SKIP_POWER_STEERING=1
```

### Short-term Rollback (< 1 hour)

Edit config:

```json
{ "enabled": false }
```

### Long-term Rollback (< 1 day)

Remove power-steering call from stop.py

---

## Success Criteria (Overall)

### Technical Metrics

- [ ] 95% uptime in production
- [ ] <300ms P95 latency
- [ ] Zero crashes causing stop hook failure
- [ ] <5% false positive rate

### User Metrics

- [ ] > 70% of incomplete sessions correctly identified
- [ ] <15% user disable rate
- [ ] Positive feedback from >60% users
- [ ] Reduction in incomplete PRs by >30%

### Code Quality

- [ ] > 90% test coverage
- [ ] All checkers documented
- [ ] Philosophy-compliant implementation
- [ ] Zero-BS (no stubs or TODOs)

---

## Resource Requirements

### Development Time

- Total: 15-20 days
- Can be parallelized with 2 developers

### Testing Time

- Unit tests: 3 days
- Integration tests: 2 days
- User testing: 1 week

### Documentation Time

- 2-3 days

### Total Time to Production

- 5-6 weeks with testing and rollout

---

## Dependencies

### External Dependencies

- Stop hook system must be working
- Transcript files must be accessible
- Runtime directory must be writable

### Internal Dependencies

- HookProcessor base class
- Session ID detection
- Metric logging system

### Nice-to-Have (Not Blocking)

- Claude Code CLI access (for --no-power-steering flag)
- ML models for session classification
- Advanced transcript analysis tools

---

## Risk Mitigation

### Risk 1: Performance Impact

- **Mitigation**: Implement timeout, cache results, optimize hot paths
- **Fallback**: Disable by default if overhead >500ms

### Risk 2: False Positives

- **Mitigation**: Conservative thresholds, allow user override, fail-open
- **Fallback**: Reduce to warning-only mode

### Risk 3: User Annoyance

- **Mitigation**: Easy disable mechanism, helpful prompts, learn from feedback
- **Fallback**: Opt-in mode only

### Risk 4: Integration Issues

- **Mitigation**: Fail-open design, comprehensive testing, gradual rollout
- **Fallback**: Quick rollback via env var

---

## Next Steps

1. **Review this specification** with team/stakeholders
2. **Get approval** for architecture and phases
3. **Delegate to builder agent** for Phase 1 implementation
4. **Set up testing infrastructure** before coding
5. **Create tracking issues** for each phase
