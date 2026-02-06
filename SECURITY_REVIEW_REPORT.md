# Security Review Report: Power Steering Loop Prevention (Issue #2196)

**Date**: 2026-02-06
**Reviewer**: Claude (Security Agent)
**Scope**: Loop detection fingerprinting and circuit breaker implementation

---

## Executive Summary

The power steering loop prevention implementation introduces SHA-256 fingerprinting for detecting repeated failure patterns. Overall security posture is **GOOD** with proper input validation and fail-open design. However, there are **3 MEDIUM-RISK** and **2 LOW-RISK** issues that should be addressed.

**Risk Level**: MEDIUM (not critical, but improvements recommended)

---

## 1. Input Validation

### 1.1 Consideration IDs (Input to Fingerprinting)

**Status**: ✅ SECURE

**Analysis**:
- Consideration IDs are validated at schema level (`_validate_consideration_schema`)
- Required fields enforced: `id`, `category`, `question`, `severity`, `checker`, `enabled`
- IDs come from YAML configuration with strict schema validation
- No user-controlled input directly influences fingerprint generation

**Code Reference** (`power_steering_checker.py:580-609`):
```python
def _validate_consideration_schema(self, consideration: Any) -> bool:
    if not isinstance(consideration, dict):
        return False

    required_fields = ["id", "category", "question", "severity", "checker", "enabled"]
    if not all(field in consideration for field in required_fields):
        return False

    # Validate severity
    if consideration["severity"] not in ["blocker", "warning"]:
        return False
```

**Verdict**: Input validation is robust. Configuration-driven IDs prevent injection risks.

### 1.2 Transcript Message Handling

**Status**: ⚠️ MEDIUM RISK - DoS Protection Present But Limited

**Issue**: MAX_TRANSCRIPT_LINES is set to 50,000 lines, which could still allow large memory consumption.

**Code Reference** (`power_steering_checker.py:100-101`):
```python
# Security: Maximum transcript size to prevent memory exhaustion
MAX_TRANSCRIPT_LINES = 50000  # Limit transcript to 50K lines (~10-20MB typical)
```

**Risk**:
- 50K lines @ ~200 chars/line = ~10MB text
- JSON parsing overhead could amplify memory usage to 30-50MB per session
- Multiple concurrent sessions could exhaust memory

**Recommendation**:
1. Add per-line size limit (e.g., 10KB max per line) to prevent malformed JSON attacks
2. Consider reducing MAX_TRANSCRIPT_LINES to 25,000 for better defense-in-depth
3. Add total byte size limit in addition to line count

**Exploit Scenario**:
An attacker could craft extremely long single-line messages to bypass line limit while consuming excessive memory.

---

## 2. SHA-256 Fingerprinting Security

### 2.1 Hash Collision Resistance

**Status**: ✅ SECURE

**Analysis**:
- Uses Python's `hashlib.sha256()` (cryptographically secure)
- 16-character truncation (64 bits) provides sufficient collision resistance for small session sizes
- Collision probability: ~1 in 10^19 for typical session (< 1000 blocks)

**Code Reference** (`power_steering_state.py:257-280`):
```python
def generate_failure_fingerprint(self, failed_consideration_ids: list[str]) -> str:
    import hashlib

    # Sort IDs for consistent hashing regardless of order
    sorted_ids = sorted(failed_consideration_ids)

    # Generate SHA-256 hash
    hash_input = "|".join(sorted_ids).encode("utf-8")
    full_hash = hashlib.sha256(hash_input).hexdigest()

    # Truncate to 16 characters (64 bits) - sufficient for loop detection
    return full_hash[:16]
```

**Strengths**:
1. Deterministic: Sorted IDs ensure consistent hashing
2. Separator (`|`) prevents concatenation ambiguity (e.g., "a|bc" vs "ab|c")
3. UTF-8 encoding handles international characters safely

**Verdict**: Cryptographic properties are sound. No practical collision risk.

### 2.2 Truncation Safety

**Status**: ✅ ACCEPTABLE

**Analysis**:
- 64-bit truncation (16 hex chars) balances security and storage
- Birthday paradox: ~4 billion hashes before 50% collision probability
- Actual session sizes: ~10-100 blocks (negligible collision risk)

**Math**:
```
P(collision) ≈ n²/2^(bits+1)
For n=100 blocks, 64 bits: P ≈ 100²/2^65 ≈ 2.7×10^-16 (negligible)
```

**Verdict**: Truncation is safe for intended use case.

---

## 3. User Input Handling

### 3.1 Removed User Override Prompt (Issue #2196 Fix)

**Status**: ✅ SECURITY IMPROVEMENT

**Analysis**:
The implementation **correctly removes** user override prompts during cleanup, preventing potential input blocking issues during shutdown.

**Evidence**: No `input()` calls or user interaction in fingerprinting code paths.

**Security Benefit**: Eliminates hang risks during `atexit` cleanup where stdin may be closed.

**Verdict**: Good security practice. Fail-open design prevents user lockout.

---

## 4. DoS Vulnerabilities

### 4.1 Fingerprint Storage Growth

**Status**: ⚠️ MEDIUM RISK - Unbounded Growth

**Issue**: The `failure_fingerprints` list grows without bounds throughout a session.

**Code Reference** (`power_steering_checker.py:968`):
```python
turn_state.failure_fingerprints.append(current_fingerprint)
```

**Risk**:
- Each block adds one 16-character fingerprint
- No cleanup or rotation policy
- Long sessions (100+ blocks) accumulate significant state
- Persistent state file grows linearly: ~16 bytes × blocks

**Attack Scenario**:
1. Attacker triggers repeated blocks (e.g., by never completing CI)
2. After 10,000 blocks: ~160KB of fingerprints in memory/disk
3. Multiple sessions could exhaust storage

**Current Mitigations**:
- Circuit breaker auto-approves at 10 blocks (limits growth per session)
- Turn state resets between sessions (ephemeral per session_id)

**Recommendation**:
1. Add maximum fingerprint history limit (e.g., keep last 50 fingerprints)
2. Implement circular buffer/ring structure
3. Add state file size monitoring

**Severity**: MEDIUM (mitigated by circuit breaker, but still unbounded in theory)

### 4.2 Timeout Protection

**Status**: ✅ SECURE

**Analysis**:
- CHECKER_TIMEOUT: 25 seconds per SDK call
- PARALLEL_TIMEOUT: 60 seconds for all checks
- HOOK_TIMEOUT: 120 seconds (framework-level)
- Hierarchy prevents cascading timeouts

**Code Reference** (`power_steering_checker.py:103-109`):
```python
# Timeout hierarchy: HOOK_TIMEOUT (120s) > PARALLEL_TIMEOUT (60s) > CHECKER_TIMEOUT (25s)
CHECKER_TIMEOUT = 25
PARALLEL_TIMEOUT = 60
```

**Verdict**: Timeout mechanisms effectively prevent DoS via long-running operations.

---

## 5. Race Conditions

### 5.1 Concurrent Access to Turn State

**Status**: ✅ SECURE (with caveats)

**Analysis**:
- File locking implemented via `fcntl.flock()` (Issue #2155)
- Atomic write pattern: temp file → fsync → rename
- 2-second lock timeout prevents indefinite hangs
- Fail-open on lock acquisition failure

**Code Reference** (`power_steering_state.py:764-772`):
```python
# File Locking (Issue #2155):
# - fcntl.flock() for exclusive access during read-modify-write
# - 2-second timeout prevents indefinite hangs
# - LOCK_EX | LOCK_NB for non-blocking exclusive lock
# - Fail-open: Timeout/error proceeds without lock
```

**Strengths**:
1. Exclusive lock (LOCK_EX) prevents simultaneous writes
2. Atomic rename ensures readers see consistent state
3. fsync forces durability before visibility

**Weakness**:
- **Fail-open on lock failure**: If lock acquisition fails, operation proceeds WITHOUT lock protection
- This could theoretically allow race condition if two processes both fail to acquire lock

**Risk Assessment**:
- **Probability**: LOW (lock acquisition rarely fails in practice)
- **Impact**: MEDIUM (could cause turn_count corruption)
- **Detection**: Monotonicity checks detect and warn about corruption

**Recommendation**:
Consider retry logic before falling back to fail-open:
```python
# Pseudocode
for attempt in range(3):
    try:
        with lock:
            save_state()
            return
    except LockTimeout:
        if attempt < 2:
            time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
        else:
            # Final attempt: fail-open
            save_state_without_lock()
```

**Verdict**: ACCEPTABLE with documented risk. Fail-open philosophy prioritizes availability over consistency.

### 5.2 Fingerprint Append Atomicity

**Status**: ✅ SECURE

**Analysis**:
- Fingerprint generation is deterministic and idempotent
- Append happens in-memory before state save
- State save is atomic (file lock + atomic write)

**Code Reference** (`power_steering_checker.py:964-968`):
```python
failed_ids = [r.consideration_id for r in blockers_to_record]
current_fingerprint = turn_state.generate_failure_fingerprint(failed_ids)

# Add fingerprint to history
turn_state.failure_fingerprints.append(current_fingerprint)
```

**Verdict**: No race conditions. Append is protected by file lock during save.

---

## 6. Injection Risks

### 6.1 Regex Patterns for Next Steps

**Status**: ✅ SECURE (No user input in patterns)

**Analysis**:
- Regex patterns are hardcoded in fallback heuristics
- No user-controlled regex compilation
- `re.match()` and `re.search()` used safely

**Verdict**: No ReDoS or injection risk from consideration analysis.

### 6.2 Command Injection

**Status**: ✅ SECURE

**Analysis**:
- No `subprocess`, `exec()`, `eval()`, or `compile()` calls in fingerprinting code
- Only file I/O and JSON serialization operations

**Grep Results**: No shell command execution found in power_steering_state.py or power_steering_checker.py

**Verdict**: No command injection surface.

---

## 7. Information Disclosure

### 7.1 Fingerprints in Logs

**Status**: ⚠️ LOW RISK - Verbose Logging

**Issue**: Fingerprints and failure IDs are logged to stderr, which could leak session state.

**Code Reference** (`power_steering_checker.py:972-981`):
```python
self._log(
    f"Loop detected: Same failures repeating (fingerprint={current_fingerprint})",
    "WARNING",
)
self._emit_progress(
    progress_callback,
    "loop_detected",
    f"Same issues repeating {turn_state.failure_fingerprints.count(current_fingerprint)} times",
    {"fingerprint": current_fingerprint, "failed_ids": failed_ids},
)
```

**Risk**:
- Fingerprints are 16-character hex strings (not sensitive cryptographic material)
- Failure IDs are configuration-defined (e.g., "todos_complete", "ci_status")
- Logs might be shared or stored insecurely

**Severity**: LOW (fingerprints are not cryptographically sensitive, more like session diagnostics)

**Recommendation**:
- Consider sanitizing logs in production environments
- Add opt-in verbose logging flag for debugging
- Truncate fingerprints to 8 characters in user-facing messages

**Verdict**: ACCEPTABLE for development use. Consider log sanitization for production.

### 7.2 State File Permissions

**Status**: ⚠️ MEDIUM RISK - No Explicit Permission Setting

**Issue**: Turn state files are created with default umask permissions.

**Code Reference** (`power_steering_state.py:663-667`):
```python
fd, temp_path = tempfile.mkstemp(
    dir=state_file.parent,
    prefix="turn_state_",
    suffix=".tmp",
)
```

**Risk**:
- Default umask on shared systems may allow world-readable files
- Turn state contains session metadata and failure history
- `.claude/runtime/power-steering/{session_id}/turn_state.json` could be exposed

**Current Mitigations**:
- Files stored in user's home directory (typically protected by filesystem permissions)
- No sensitive user data (just workflow state)

**Recommendation**:
Add explicit permission setting:
```python
fd, temp_path = tempfile.mkstemp(
    dir=state_file.parent,
    prefix="turn_state_",
    suffix=".tmp",
)
os.fchmod(fd, 0o600)  # Owner read/write only
```

**Severity**: MEDIUM (defense-in-depth improvement)

---

## 8. Additional Security Observations

### 8.1 Fail-Open Design Philosophy

**Status**: ✅ SECURITY BY DESIGN

**Analysis**:
The entire power-steering system follows a "fail-open" philosophy:
- Lock acquisition failures proceed without lock
- State save errors allow session to continue
- Validation failures use fallback defaults

**Security Benefit**:
- Prevents denial-of-service via security mechanism failures
- Users always retain control (can stop session even if hook fails)
- Availability prioritized over strict consistency

**Trade-off**:
- Potential for state corruption (mitigated by monotonicity checks)
- Might mask underlying issues (mitigated by diagnostic logging)

**Verdict**: Appropriate for user-facing tool. Documented risks are acceptable.

### 8.2 Circuit Breaker Threshold

**Status**: ✅ SECURE

**Analysis**:
- MAX_CONSECUTIVE_BLOCKS = 10 (increased from 3)
- Auto-approves after 10 repeated blocks
- Loop detection (3 identical fingerprints) triggers early auto-approval

**Security Consideration**:
- Prevents infinite blocking loops (DoS against user)
- Threshold is high enough to allow legitimate retries
- Low enough to prevent user frustration

**Verdict**: Well-balanced threshold. No security concerns.

---

## 9. Summary of Findings

### Critical Issues: 0
None identified.

### High-Risk Issues: 0
None identified.

### Medium-Risk Issues: 3

1. **Unbounded Fingerprint Storage Growth**
   - Impact: Memory/disk exhaustion in long sessions
   - Likelihood: LOW (circuit breaker limits blocks)
   - Recommendation: Add fingerprint history limit (max 50-100 entries)

2. **Transcript DoS Protection Incomplete**
   - Impact: Memory exhaustion via large messages
   - Likelihood: LOW (requires malicious transcript crafting)
   - Recommendation: Add per-line size limit + total byte limit

3. **State File Permissions Not Explicitly Set**
   - Impact: Potential information disclosure on shared systems
   - Likelihood: LOW (files in user home directory)
   - Recommendation: Set explicit 0o600 permissions on state files

### Low-Risk Issues: 2

4. **Verbose Fingerprint Logging**
   - Impact: Session state disclosure in logs
   - Likelihood: LOW (fingerprints not cryptographically sensitive)
   - Recommendation: Sanitize logs for production, add verbose flag

5. **Fail-Open Lock Fallback**
   - Impact: Potential turn_count corruption under contention
   - Likelihood: VERY LOW (lock acquisition rarely fails)
   - Recommendation: Add retry logic before fail-open fallback

---

## 10. Recommendations

### Immediate (Before Merge)

1. ✅ **Input Validation**: Already robust, no changes needed
2. ✅ **Cryptographic Security**: SHA-256 usage is correct
3. ⚠️ **Add State File Permissions**: One-line fix for defense-in-depth

### Short-Term (Next Iteration)

4. Add fingerprint history limit (circular buffer, max 100 entries)
5. Add per-line size validation to transcript loading
6. Implement retry logic for lock acquisition before fail-open

### Long-Term (Future Enhancement)

7. Add configurable verbose logging flag
8. Monitor state file sizes in production
9. Consider log sanitization for production environments

---

## 11. Test Coverage Analysis

### Security Test Coverage: ✅ GOOD

**Identified Security Tests**:
1. `test_security_features.py:252` - Timeout DoS protection
2. `test_issue_2196_loop_detection.py` - Loop detection and fingerprinting
3. `test_issue_2196_circuit_breaker.py` - Circuit breaker thresholds

**Recommendations**:
- Add test for max transcript size enforcement
- Add test for state file permission verification
- Add test for fingerprint storage limits

---

## 12. Conclusion

**Overall Security Assessment**: ✅ ACCEPTABLE FOR PRODUCTION

The power steering loop prevention implementation demonstrates solid security practices:
- Proper input validation
- Cryptographically secure fingerprinting
- DoS protection via timeouts
- Race condition mitigation via file locking
- Fail-open design prevents user lockout

The identified issues are **non-critical** and primarily concern defense-in-depth hardening. The code can proceed to merge with confidence, though the recommended improvements should be addressed in follow-up work.

**Recommended Action**: APPROVE with minor improvements

---

## 13. Security Checklist

- [x] Password hashing (N/A - no authentication)
- [x] HTTPS enforcement (N/A - local tool)
- [x] CSRF protection (N/A - no web interface)
- [x] Input validation (✅ DONE - configuration schema validation)
- [x] SQL parameterization (N/A - no database)
- [x] Rate limiting (✅ DONE - circuit breaker + timeouts)
- [x] Session management (✅ DONE - turn state tracking)
- [x] Error message sanitization (✅ DONE - fail-open, no sensitive data in errors)
- [x] File permissions (⚠️ NEEDS IMPROVEMENT - add explicit 0o600)
- [x] Race conditions (✅ DONE - file locking with fail-open)
- [x] DoS protection (✅ DONE - timeouts + transcript limits)
- [x] Injection prevention (✅ DONE - no eval/exec/shell)
- [x] Information disclosure (⚠️ MINOR - verbose logging could be reduced)

**Final Score**: 11/13 fully implemented, 2/13 need minor improvements

---

**Reviewer Signature**: Claude (Security Agent)
**Review Date**: 2026-02-06
**Next Review**: After addressing medium-risk findings
