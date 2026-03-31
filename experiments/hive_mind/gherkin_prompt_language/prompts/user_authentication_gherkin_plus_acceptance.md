# User Authentication REST API — Gherkin + Acceptance Criteria

Implement the user authentication REST API described by the behavioral
specification below.

Each Gherkin scenario is an acceptance criterion that must pass. The
acceptance criteria below provide additional verification requirements
beyond the scenario-level checks.

## Acceptance criteria

1. **Security invariant**: Passwords must never appear in any response body
   or log output. Stored passwords must be bcrypt hashes.

2. **Enumeration resistance**: Login failure for wrong-password and
   non-existent-email must return identical error messages and status codes.

3. **Token lifecycle**: Access tokens must be JWT with 15-minute expiry.
   Refresh tokens must be opaque and long-lived. Expired tokens must be
   rejected with 401.

4. **Lockout correctness**: Account locks after exactly 5 consecutive
   failed login attempts. A successful login resets the counter. A locked
   account rejects even correct credentials with 423.

5. **Idempotent registration rejection**: Attempting to register an
   already-registered email always returns 409 regardless of how many times
   it is attempted.

6. **Test completeness**: Every scenario in the feature file must have a
   corresponding test. Tests must verify both status codes and response
   body content.

## Required output

- Python code for the authentication REST API
- Focused tests covering every scenario and acceptance criterion
- In-memory user storage (no external database)

Do not widen scope beyond the specified scenarios and acceptance criteria.
