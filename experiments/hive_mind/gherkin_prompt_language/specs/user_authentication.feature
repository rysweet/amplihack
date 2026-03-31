Feature: User Authentication REST API
  As a client application
  I need a secure authentication system
  So that users can register, log in, and access protected resources

  Background:
    Given the authentication service is running
    And the user database is empty

  # --- Registration ---

  Scenario: Successful user registration
    When I register with email "alice@example.com" and password "Str0ng!Pass"
    Then the response status should be 201
    And the response should contain a user ID
    And the response should not contain the password

  Scenario: Registration rejects duplicate email
    Given a user exists with email "alice@example.com"
    When I register with email "alice@example.com" and password "AnotherPass1!"
    Then the response status should be 409
    And the response should contain error "email already registered"

  Scenario: Registration rejects weak password
    When I register with email "bob@example.com" and password "123"
    Then the response status should be 400
    And the response should contain error "password too weak"

  Scenario: Registration rejects invalid email
    When I register with email "not-an-email" and password "Str0ng!Pass"
    Then the response status should be 400
    And the response should contain error "invalid email"

  # --- Login ---

  Scenario: Successful login returns access and refresh tokens
    Given a user exists with email "alice@example.com" and password "Str0ng!Pass"
    When I login with email "alice@example.com" and password "Str0ng!Pass"
    Then the response status should be 200
    And the response should contain an "access_token"
    And the response should contain a "refresh_token"
    And the access token should expire in 15 minutes

  Scenario: Login with wrong password
    Given a user exists with email "alice@example.com" and password "Str0ng!Pass"
    When I login with email "alice@example.com" and password "WrongPass1!"
    Then the response status should be 401
    And the response should contain error "invalid credentials"

  Scenario: Login with non-existent email
    When I login with email "nobody@example.com" and password "Str0ng!Pass"
    Then the response status should be 401
    And the response should contain error "invalid credentials"

  Scenario: Account locks after 5 failed login attempts
    Given a user exists with email "alice@example.com" and password "Str0ng!Pass"
    When I fail to login 5 times with email "alice@example.com"
    And I login with email "alice@example.com" and password "Str0ng!Pass"
    Then the response status should be 423
    And the response should contain error "account locked"

  # --- Token refresh ---

  Scenario: Refresh token returns new access token
    Given I am logged in as "alice@example.com"
    When I refresh my access token using a valid refresh token
    Then the response status should be 200
    And the response should contain a new "access_token"

  Scenario: Expired refresh token is rejected
    Given I have an expired refresh token
    When I refresh my access token using the expired refresh token
    Then the response status should be 401
    And the response should contain error "refresh token expired"

  # --- Protected resource access ---

  Scenario: Valid access token grants access to protected resource
    Given I am logged in as "alice@example.com"
    When I request GET /me with a valid access token
    Then the response status should be 200
    And the response should contain the user profile for "alice@example.com"

  Scenario: Missing access token is rejected
    When I request GET /me without an access token
    Then the response status should be 401
    And the response should contain error "missing authorization"

  Scenario: Expired access token is rejected
    Given I have an expired access token
    When I request GET /me with the expired access token
    Then the response status should be 401
    And the response should contain error "token expired"

  # --- Password hashing ---

  Scenario: Passwords are stored hashed, not plaintext
    When I register with email "alice@example.com" and password "Str0ng!Pass"
    Then the stored password should not equal "Str0ng!Pass"
    And the stored password should be a bcrypt hash
