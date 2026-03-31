# User Authentication REST API — Gherkin + English Guidance

## Goal

Implement a user authentication REST API with registration, login, token
management, and protected resource access.

The behavioral specification below defines the exact acceptance criteria.
Each Gherkin scenario is a required behavior. The English guidance provides
implementation context.

## Implementation guidance

- Use Python with Flask or FastAPI
- Use in-memory storage (dict-based), no external database
- Hash passwords with bcrypt
- Use JWT for access tokens (15-minute expiry) and opaque refresh tokens
- Account lockout: track failed attempts per email, lock after 5 consecutive failures
- Return consistent error messages for wrong-password and unknown-email to prevent user enumeration
- Token validation: check signature, expiry, and presence in Authorization header

## Required output

- Code for all endpoints described in the scenarios
- Focused tests covering every scenario
- Both happy-path and error-path coverage

## Non-goals

- No OAuth2 or social login
- No email verification or password reset
- No production database
- No admin panel or role management
