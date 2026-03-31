# User Authentication REST API — English Baseline

## Goal

Implement a user authentication REST API with registration, login, token
management, and protected resource access.

## Required deliverables

1. **Registration endpoint** (`POST /register`): Accept email and password.
   Validate email format and password strength (minimum 8 characters, mixed
   case, number, special character). Return 201 with user ID on success. Reject
   duplicate emails with 409. Store passwords hashed with bcrypt, never
   plaintext.

2. **Login endpoint** (`POST /login`): Accept email and password. Return 200
   with an access token (JWT, 15-minute expiry) and a refresh token on success.
   Return 401 for wrong password or non-existent email — use the same error
   message for both to prevent user enumeration. Lock the account after 5
   consecutive failed login attempts, returning 423.

3. **Token refresh endpoint** (`POST /refresh`): Accept a refresh token. Return
   200 with a new access token. Reject expired refresh tokens with 401.

4. **Protected resource endpoint** (`GET /me`): Require a valid access token in
   the Authorization header. Return the user profile (email, user ID) on
   success. Return 401 for missing, invalid, or expired tokens.

5. **Focused tests** covering: successful registration, duplicate email
   rejection, weak password rejection, invalid email rejection, successful
   login, wrong password, non-existent email, account lockout after 5 failures,
   token refresh, expired refresh token, protected access with valid token,
   missing token, expired token, and password hashing verification.

## Non-goals

- Do not build a full user management system (roles, permissions, admin panel).
- Do not implement OAuth2 or social login.
- Do not add email verification or password reset flows.
- Do not set up a production database — use in-memory storage.

## Success criteria

- All endpoints return correct HTTP status codes
- Passwords are never stored or returned in plaintext
- Token expiry is enforced
- Account lockout works after 5 failed attempts
- Tests cover both happy path and error cases
