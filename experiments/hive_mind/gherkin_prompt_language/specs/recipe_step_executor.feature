Feature: Recipe Step Executor
  As a workflow engine
  I need to execute recipe steps with conditions, dependencies, retries, timeouts, output capture, and sub-recipes
  So that complex multi-step workflows complete correctly even under partial failure

  Background:
    Given an empty execution context
    And the step executor is initialized

  # ==========================================================================
  # Conditional Step Execution
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
  # Step Dependencies
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
  # Retry with Backoff
  # ==========================================================================

  Scenario: Step with no retries fails immediately
    Given a recipe with steps:
      | id      | command   | max_retries |
      | step_a  | exit 1    | 0           |
    When the recipe executes
    Then step "step_a" status should be "failed"
    And step "step_a" attempt count should be 1

  Scenario: Step retries on failure with exponential backoff
    Given a recipe with steps:
      | id      | command                   | max_retries |
      | step_a  | fail_then_succeed(2)      | 3           |
    When the recipe executes
    Then step "step_a" status should be "completed"
    And step "step_a" attempt count should be 3
    And step "step_a" retry delays should be approximately [1, 2] seconds

  Scenario: Step exhausts all retries and fails
    Given a recipe with steps:
      | id      | command      | max_retries |
      | step_a  | always_fail  | 2           |
    When the recipe executes
    Then step "step_a" status should be "failed"
    And step "step_a" attempt count should be 3

  # ==========================================================================
  # Timeout Handling
  # ==========================================================================

  Scenario: Step completes within timeout
    Given a recipe with steps:
      | id      | command       | timeout_seconds |
      | step_a  | sleep(1)      | 10              |
    When the recipe executes
    Then step "step_a" status should be "completed"

  Scenario: Step exceeding timeout is terminated and marked timed_out
    Given a recipe with steps:
      | id      | command       | timeout_seconds |
      | step_a  | sleep(30)     | 2               |
    When the recipe executes
    Then step "step_a" status should be "timed_out"

  Scenario: Timed-out step is not retried even if max_retries > 0
    Given a recipe with steps:
      | id      | command       | timeout_seconds | max_retries |
      | step_a  | sleep(30)     | 2               | 3           |
    When the recipe executes
    Then step "step_a" status should be "timed_out"
    And step "step_a" attempt count should be 1

  Scenario: Timed-out step counts as failure for dependency propagation
    Given a recipe with steps:
      | id      | command          | timeout_seconds | blockedBy |
      | step_a  | sleep(30)        | 2               |           |
      | step_b  | echo "blocked"   |                 | step_a    |
    When the recipe executes
    Then step "step_a" status should be "timed_out"
    And step "step_b" status should be "failed"
    And step "step_b" failure reason should be "dependency_failed"

  # ==========================================================================
  # Output Capture
  # ==========================================================================

  Scenario: Step output is stored in context under its ID
    Given a recipe with steps:
      | id      | command           |
      | step_a  | echo "result_42"  |
    When the recipe executes
    Then the context should contain key "step_a" with value "result_42"

  Scenario: Subsequent step references prior output via template syntax
    Given a recipe with steps:
      | id      | command                           | blockedBy |
      | step_a  | echo "world"                      |           |
      | step_b  | echo "hello {{step_a}}"           | step_a    |
    When the recipe executes
    Then the context should contain key "step_b" with value "hello world"

  Scenario: Template referencing missing output resolves to empty string
    Given a recipe with steps:
      | id      | command                              |
      | step_a  | echo "value is: {{nonexistent}}"     |
    When the recipe executes
    Then the context should contain key "step_a" with value "value is: "

  # ==========================================================================
  # Sub-Recipe Delegation
  # ==========================================================================

  Scenario: Sub-recipe executes in child context inheriting parent values
    Given the context contains:
      | key       | value  |
      | base_url  | http://api.example.com |
    And a recipe with steps:
      | id      | sub_recipe                        |
      | step_a  | child_recipe_using_base_url       |
    And "child_recipe_using_base_url" is a recipe with steps:
      | id        | command                       |
      | child_1   | echo "url={{base_url}}"       |
    When the recipe executes
    Then step "step_a" status should be "completed"
    And in the child context of "step_a", key "child_1" should equal "url=http://api.example.com"

  Scenario: Child outputs do not propagate to parent by default
    Given a recipe with steps:
      | id      | sub_recipe         | propagate_outputs |
      | step_a  | child_recipe       | false             |
    And "child_recipe" is a recipe with steps:
      | id        | command            |
      | child_1   | echo "secret"      |
    When the recipe executes
    Then step "step_a" status should be "completed"
    And the context should not contain key "child_1"

  Scenario: Child outputs propagate to parent when propagate_outputs is true
    Given a recipe with steps:
      | id      | sub_recipe         | propagate_outputs |
      | step_a  | child_recipe       | true              |
    And "child_recipe" is a recipe with steps:
      | id        | command            |
      | child_1   | echo "visible"     |
    When the recipe executes
    Then step "step_a" status should be "completed"
    And the context should contain key "child_1" with value "visible"

  Scenario: Failed sub-recipe does not propagate outputs even with propagate_outputs true
    Given a recipe with steps:
      | id      | sub_recipe         | propagate_outputs |
      | step_a  | failing_recipe     | true              |
    And "failing_recipe" is a recipe with steps:
      | id        | command            |
      | child_1   | echo "before_fail" |
      | child_2   | exit 1             |
    When the recipe executes
    Then step "step_a" status should be "failed"
    And the context should not contain key "child_1"

  # ==========================================================================
  # Cross-Feature Interactions
  # ==========================================================================

  Scenario: Condition references output from a retried step (uses final successful value)
    Given a recipe with steps:
      | id      | command                        | max_retries | blockedBy |
      | step_a  | fail_then_return(2, "ready")   | 3           |           |
      | step_b  | echo "proceeding"              |             | step_a    |
    And step "step_b" has condition: step_a == 'ready'
    When the recipe executes
    Then step "step_a" status should be "completed"
    And the context should contain key "step_a" with value "ready"
    And step "step_b" status should be "completed"

  Scenario: Timed-out step blocks a conditional step (blocked step fails, not skipped)
    Given a recipe with steps:
      | id      | command          | timeout_seconds | blockedBy |
      | step_a  | sleep(30)        | 2               |           |
      | step_b  | echo "gated"     |                 | step_a    |
    And step "step_b" has condition: step_a == 'done'
    When the recipe executes
    Then step "step_a" status should be "timed_out"
    And step "step_b" status should be "failed"
    And step "step_b" failure reason should be "dependency_failed"

  Scenario: Condition referencing a skipped step evaluates to false (step is skipped)
    Given the context contains:
      | key     | value   |
      | env     | staging |
    And a recipe with steps:
      | id      | command          | condition       | blockedBy |
      | step_a  | echo "prod_cfg"  | env == 'prod'   |           |
      | step_b  | echo "use_cfg"   |                 | step_a    |
    And step "step_b" has condition: step_a is not None
    When the recipe executes
    Then step "step_a" status should be "skipped"
    And step "step_b" status should be "skipped"

  Scenario: Sub-recipe failure triggers parent retry (entire sub-recipe re-runs)
    Given a recipe with steps:
      | id      | sub_recipe                     | max_retries |
      | step_a  | intermittent_child_recipe      | 2           |
    And "intermittent_child_recipe" is a recipe that fails on first run but succeeds on second
    When the recipe executes
    Then step "step_a" status should be "completed"
    And step "step_a" attempt count should be 2

  Scenario: Retry of step whose condition references a skipped prior step
    Given the context contains:
      | key     | value   |
      | env     | staging |
    And a recipe with steps:
      | id      | command          | condition       |
      | step_a  | echo "config"    | env == 'prod'   |
      | step_b  | fail_then_succeed(1) | max_retries | blockedBy |
    And step "step_b" has max_retries 2 and condition: step_a == 'config'
    When the recipe executes
    Then step "step_a" status should be "skipped"
    And step "step_b" status should be "skipped"

  Scenario: Output template in a step that depends on a retried step
    Given a recipe with steps:
      | id      | command                        | max_retries | blockedBy |
      | step_a  | fail_then_return(1, "v2")      | 2           |           |
      | step_b  | echo "got {{step_a}}"          |             | step_a    |
    When the recipe executes
    Then step "step_a" status should be "completed"
    And the context should contain key "step_a" with value "v2"
    And the context should contain key "step_b" with value "got v2"

  Scenario: Sub-recipe with child timeout does not timeout the parent
    Given a recipe with steps:
      | id      | sub_recipe         | timeout_seconds |
      | step_a  | slow_child_recipe  | 60              |
    And "slow_child_recipe" is a recipe with steps:
      | id        | command       | timeout_seconds |
      | child_1   | sleep(30)     | 2               |
      | child_2   | echo "after"  |                 |
    When the recipe executes
    Then in the child context of "step_a", step "child_1" status should be "timed_out"
    And in the child context of "step_a", step "child_2" status should be "failed"
    And step "step_a" status should be "failed"

  Scenario: Parallel-eligible steps with no mutual dependencies run concurrently
    Given a recipe with steps:
      | id      | command          | blockedBy |
      | step_a  | sleep(2)         |           |
      | step_b  | sleep(2)         |           |
      | step_c  | echo "join"      | step_a,step_b |
    When the recipe executes
    Then step "step_a" and step "step_b" should execute concurrently
    And the total execution time should be less than 4 seconds
    And step "step_c" status should be "completed"
