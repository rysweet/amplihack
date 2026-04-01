Feature: Recipe Step Executor
  As a workflow engine
  I need to execute recipe steps with conditions, dependencies, retries, timeouts, output capture, and sub-recipes
  So that complex multi-step workflows complete correctly even under partial failure

  Background:
    Given an empty execution context
    And the step executor is initialized

  # ==========================================================================
  # Feature 1: Conditional Step Execution
  # ==========================================================================

  Scenario: Unconditional step always executes
    Given a recipe with steps:
      | id      | command          | condition |
      | step_a  | echo "hello"     |           |
    When the recipe executes
    Then step "step_a" status should be "completed"
    And the context should contain key "step_a" with value "hello"

  Scenario: Conditional step executes when condition is true
    Given the context contains:
      | key     | value |
      | env     | prod  |
    And a recipe with steps:
      | id      | command             | condition       |
      | step_a  | echo "deploying"    | env == 'prod'   |
    When the recipe executes
    Then step "step_a" status should be "completed"

  Scenario: Conditional step is skipped when condition is false
    Given the context contains:
      | key     | value   |
      | env     | staging |
    And a recipe with steps:
      | id      | command             | condition       |
      | step_a  | echo "deploying"    | env == 'prod'   |
    When the recipe executes
    Then step "step_a" status should be "skipped"
    And the context should not contain key "step_a"

  Scenario: Condition referencing missing key evaluates to false
    Given an empty execution context
    And a recipe with steps:
      | id      | command          | condition              |
      | step_a  | echo "go"        | feature_flag == True   |
    When the recipe executes
    Then step "step_a" status should be "skipped"

  # ==========================================================================
  # Feature 2: Step Dependencies
  # ==========================================================================

  Scenario: Step waits for dependency to complete before executing
    Given a recipe with steps:
      | id      | command          | blockedBy |
      | step_a  | echo "first"     |           |
      | step_b  | echo "second"    | step_a    |
    When the recipe executes
    Then step "step_a" should complete before step "step_b" starts
    And step "step_b" status should be "completed"

  Scenario: Step blocked by failed dependency is marked failed
    Given a recipe with steps:
      | id      | command            | blockedBy |
      | step_a  | exit 1             |           |
      | step_b  | echo "unreachable" | step_a    |
    When the recipe executes
    Then step "step_a" status should be "failed"
    And step "step_b" status should be "failed"
    And step "step_b" failure reason should be "dependency_failed"

  Scenario: Step blocked by skipped dependency executes normally
    Given the context contains:
      | key     | value   |
      | env     | staging |
    And a recipe with steps:
      | id      | command          | condition       | blockedBy |
      | step_a  | echo "skip me"   | env == 'prod'   |           |
      | step_b  | echo "runs"      |                 | step_a    |
    When the recipe executes
    Then step "step_a" status should be "skipped"
    And step "step_b" status should be "completed"

  Scenario: Diamond dependency graph executes in correct order
    Given a recipe with steps:
      | id      | command          | blockedBy     |
      | step_a  | echo "root"      |               |
      | step_b  | echo "left"      | step_a        |
      | step_c  | echo "right"     | step_a        |
      | step_d  | echo "join"      | step_b,step_c |
    When the recipe executes
    Then step "step_a" should complete before step "step_b" starts
    And step "step_a" should complete before step "step_c" starts
    And step "step_b" should complete before step "step_d" starts
    And step "step_c" should complete before step "step_d" starts
    And step "step_d" status should be "completed"

  # ==========================================================================
  # Feature 3: Retry with Exponential Backoff
  # ==========================================================================

  Scenario: Step with no retries fails immediately
    Given a recipe with steps:
      | id      | command  | max_retries |
      | step_a  | exit 1   | 0           |
    When the recipe executes
    Then step "step_a" status should be "failed"
    And step "step_a" attempt count should be 1

  Scenario: Step succeeds on second retry
    Given a recipe with steps:
      | id      | command               | max_retries |
      | step_a  | fail_then_succeed(1)  | 3           |
    When the recipe executes
    Then step "step_a" status should be "completed"
    And step "step_a" attempt count should be 2

  Scenario: Step exhausts all retries and fails
    Given a recipe with steps:
      | id      | command  | max_retries |
      | step_a  | exit 1   | 3           |
    When the recipe executes
    Then step "step_a" status should be "failed"
    And step "step_a" attempt count should be 4
    And retry delays should follow exponential backoff: 1s, 2s, 4s

  # ==========================================================================
  # Feature 4: Timeout Handling
  # ==========================================================================

  Scenario: Step that exceeds timeout is terminated and marked timed_out
    Given a recipe with steps:
      | id      | command     | timeout_seconds |
      | step_a  | sleep 30    | 2               |
    When the recipe executes
    Then step "step_a" status should be "timed_out"
    And step "step_a" execution time should be approximately 2 seconds

  Scenario: Timed-out step is NOT retried even if max_retries is set
    Given a recipe with steps:
      | id      | command     | timeout_seconds | max_retries |
      | step_a  | sleep 30    | 2               | 3           |
    When the recipe executes
    Then step "step_a" status should be "timed_out"
    And step "step_a" attempt count should be 1

  Scenario: Timed-out step counts as failure for dependency propagation
    Given a recipe with steps:
      | id      | command            | timeout_seconds | blockedBy |
      | step_a  | sleep 30           | 2               |           |
      | step_b  | echo "unreachable" |                 | step_a    |
    When the recipe executes
    Then step "step_a" status should be "timed_out"
    And step "step_b" status should be "failed"
    And step "step_b" failure reason should be "dependency_failed"

  # ==========================================================================
  # Feature 5: Output Capture
  # ==========================================================================

  Scenario: Step output is stored in context under step ID
    Given a recipe with steps:
      | id      | command                |
      | step_a  | echo "result_value"    |
    When the recipe executes
    Then the context should contain key "step_a" with value "result_value"

  Scenario: Subsequent step references prior output via template syntax
    Given a recipe with steps:
      | id      | command                        | blockedBy |
      | step_a  | echo "data_123"                |           |
      | step_b  | echo "processing {{step_a}}"   | step_a    |
    When the recipe executes
    Then the context should contain key "step_b" with value "processing data_123"

  # ==========================================================================
  # Feature 6: Sub-recipe Delegation
  # ==========================================================================

  Scenario: Sub-recipe runs in child context that inherits parent
    Given the context contains:
      | key         | value    |
      | parent_val  | shared   |
    And a recipe with steps:
      | id      | sub_recipe                                                    |
      | step_a  | [{"id": "child_1", "command": "echo {{parent_val}}"}]        |
    When the recipe executes
    Then step "step_a" status should be "completed"
    And sub-recipe step "child_1" should have access to "parent_val"

  Scenario: Sub-recipe outputs do NOT propagate to parent by default
    Given a recipe with steps:
      | id      | sub_recipe                                                    | propagate_outputs |
      | step_a  | [{"id": "child_1", "command": "echo secret"}]                | false             |
      | step_b  | echo "{{child_1}}"                                           |                   |
    When the recipe executes
    Then the context should not contain key "child_1"
    And step "step_b" output should contain literal "{{child_1}}"

  Scenario: Sub-recipe outputs propagate when propagate_outputs is true
    Given a recipe with steps:
      | id      | sub_recipe                                                    | propagate_outputs |
      | step_a  | [{"id": "child_1", "command": "echo visible"}]               | true              |
      | step_b  | echo "got {{child_1}}"                                       | step_a            |
    When the recipe executes
    Then the context should contain key "child_1" with value "visible"
    And the context should contain key "step_b" with value "got visible"

  # ==========================================================================
  # CROSS-FEATURE INTERACTIONS (the hard part)
  # ==========================================================================

  Scenario: Retried step output changes between attempts — conditional depends on final output
    Given a recipe with steps:
      | id      | command                          | max_retries | blockedBy |
      | step_a  | increment_counter()              | 2           |           |
      | step_b  | echo "done"                      |             | step_a    |
    And step_a fails on attempt 1 with output "attempt_1" and succeeds on attempt 2 with output "attempt_2"
    When the recipe executes
    Then step "step_a" status should be "completed"
    And the context should contain key "step_a" with value "attempt_2"
    And the context should NOT contain value "attempt_1" for key "step_a"

  Scenario: Timed-out step blocks a conditional step — blocked step fails, not skipped
    Given the context contains:
      | key     | value |
      | flag    | true  |
    And a recipe with steps:
      | id      | command            | timeout_seconds | condition      | blockedBy |
      | step_a  | sleep 30           | 2               |                |           |
      | step_b  | echo "conditional" |                 | flag == True   | step_a    |
    When the recipe executes
    Then step "step_a" status should be "timed_out"
    And step "step_b" status should be "failed"
    And step "step_b" failure reason should be "dependency_failed"
    And step "step_b" should NOT have status "skipped"

  Scenario: Sub-recipe child fails — parent step fails, parent is NOT retried
    Given a recipe with steps:
      | id      | sub_recipe                                              | max_retries |
      | step_a  | [{"id": "child_1", "command": "exit 1"}]                | 3           |
    When the recipe executes
    Then step "step_a" status should be "failed"
    And step "step_a" attempt count should be 1
    And step "step_a" should NOT be retried because sub-recipe failure is not a transient error

  Scenario: Retry of step whose condition references a skipped step
    Given the context contains:
      | key     | value   |
      | env     | staging |
    And a recipe with steps:
      | id      | command          | condition       | max_retries | blockedBy |
      | step_a  | echo "skip me"   | env == 'prod'   |             |           |
      | step_b  | fail_then_succeed(1) |             |             |           |
      | step_c  | echo "use {{step_a}}" |            | 2           | step_a,step_b |
    When the recipe executes
    Then step "step_a" status should be "skipped"
    And step "step_b" status should be "completed"
    And step "step_c" status should be "completed"
    And step "step_c" output should contain literal "{{step_a}}" because step_a was skipped and has no output

  Scenario: Output template referencing timed-out step resolves to empty or error marker
    Given a recipe with steps:
      | id      | command                       | timeout_seconds | blockedBy |
      | step_a  | sleep 30                      | 1               |           |
      | step_b  | echo "result: {{step_a}}"     |                 | step_a    |
    When the recipe executes
    Then step "step_a" status should be "timed_out"
    And step "step_b" status should be "failed"
    And step "step_b" failure reason should be "dependency_failed"

  Scenario: Diamond dependency with one branch retried and one branch timed out
    Given a recipe with steps:
      | id      | command               | blockedBy     | max_retries | timeout_seconds |
      | step_a  | echo "root"           |               |             |                 |
      | step_b  | fail_then_succeed(1)  | step_a        | 2           |                 |
      | step_c  | sleep 30              | step_a        |             | 1               |
      | step_d  | echo "join"           | step_b,step_c |             |                 |
    When the recipe executes
    Then step "step_a" status should be "completed"
    And step "step_b" status should be "completed"
    And step "step_c" status should be "timed_out"
    And step "step_d" status should be "failed"
    And step "step_d" failure reason should be "dependency_failed"

  Scenario: Sub-recipe with propagated outputs feeds parent conditional step
    Given a recipe with steps:
      | id      | sub_recipe                                                          | propagate_outputs | blockedBy |
      | step_a  | [{"id": "child_1", "command": "echo ready"}]                       | true              |           |
      | step_b  | echo "proceed"                                                     |                   | step_a    |
    And step "step_b" has condition: child_1 == 'ready'
    When the recipe executes
    Then step "step_a" status should be "completed"
    And step "step_b" status should be "completed"
    And the context should contain key "child_1" with value "ready"

  Scenario: Chained retries — step_b retries because step_a output changed on retry
    Given a recipe with steps:
      | id      | command                         | max_retries | blockedBy |
      | step_a  | fail_then_succeed(2)            | 3           |           |
      | step_b  | echo "got {{step_a}}"           |             | step_a    |
    When the recipe executes
    Then step "step_a" status should be "completed"
    And step "step_a" attempt count should be 3
    And step "step_b" status should be "completed"
    And step "step_b" should use the FINAL output of step_a, not intermediate attempts
