/**
 * Goal-Seeking Agent using GitHub Copilot SDK
 *
 * This example demonstrates how to build an autonomous goal-seeking agent
 * that can adapt its approach based on intermediate results.
 *
 * The agent receives a high-level goal and:
 * 1. Plans execution phases
 * 2. Executes each phase with custom tools
 * 3. Adapts strategy based on results
 * 4. Self-assesses progress toward goal
 *
 * Prerequisites:
 * - npm install @github/copilot-sdk
 * - Copilot CLI installed and authenticated
 */

import { CopilotClient, defineTool, SessionEvent } from "@github/copilot-sdk";

// ============================================================================
// PHASE 1: Define Goal-Seeking Tools
// ============================================================================

/**
 * Tool: Analyze current state and plan next steps
 */
const planExecution = defineTool("plan_execution", {
  description: "Analyze the current goal and state, then plan the next execution phases",
  parameters: {
    type: "object",
    properties: {
      goal: { type: "string", description: "The high-level goal to achieve" },
      currentState: {
        type: "string",
        description: "Current state of progress",
      },
      completedPhases: {
        type: "array",
        items: { type: "string" },
        description: "List of completed phases",
      },
    },
    required: ["goal"],
  },
  handler: async ({ goal, currentState, completedPhases }) => {
    // Goal-seeking logic: determine next phases based on context
    const phases = [];

    if (!completedPhases?.includes("research")) {
      phases.push({
        phase: "research",
        description: "Gather information about the problem space",
        priority: 1,
      });
    }

    if (!completedPhases?.includes("design")) {
      phases.push({
        phase: "design",
        description: "Design solution approach",
        priority: 2,
      });
    }

    if (!completedPhases?.includes("implement")) {
      phases.push({
        phase: "implement",
        description: "Implement the solution",
        priority: 3,
      });
    }

    if (!completedPhases?.includes("verify")) {
      phases.push({
        phase: "verify",
        description: "Verify solution meets goal",
        priority: 4,
      });
    }

    return {
      goal,
      currentState: currentState || "initial",
      nextPhases: phases,
      recommendedAction: phases.length > 0 ? `Execute phase: ${phases[0].phase}` : "Goal achieved!",
    };
  },
});

/**
 * Tool: Execute a specific phase and report results
 */
const executePhase = defineTool("execute_phase", {
  description: "Execute a specific phase and return results",
  parameters: {
    type: "object",
    properties: {
      phase: { type: "string", description: "Phase name to execute" },
      context: { type: "string", description: "Additional context for phase" },
    },
    required: ["phase"],
  },
  handler: async ({ phase, context }) => {
    // Simulate phase execution with varying success rates
    const success = Math.random() > 0.2; // 80% success rate

    const results: Record<string, { output: string; artifacts: string[]; nextSteps: string[] }> = {
      research: {
        output: "Identified key requirements and constraints",
        artifacts: ["requirements.md", "constraints.json"],
        nextSteps: ["Proceed to design phase"],
      },
      design: {
        output: "Created solution architecture",
        artifacts: ["architecture.md", "api-spec.yaml"],
        nextSteps: ["Proceed to implementation"],
      },
      implement: {
        output: "Implemented core functionality",
        artifacts: ["src/main.ts", "tests/main.test.ts"],
        nextSteps: ["Run verification"],
      },
      verify: {
        output: "All tests passing, solution validated",
        artifacts: ["test-results.json"],
        nextSteps: ["Goal complete!"],
      },
    };

    const phaseResult = results[phase] || {
      output: `Executed ${phase}`,
      artifacts: [],
      nextSteps: [],
    };

    return {
      phase,
      success,
      ...phaseResult,
      failureReason: success ? null : "Recoverable error - retry recommended",
    };
  },
});

/**
 * Tool: Assess progress toward goal
 */
const assessProgress = defineTool("assess_progress", {
  description: "Evaluate progress toward the goal and determine if complete",
  parameters: {
    type: "object",
    properties: {
      goal: { type: "string", description: "The original goal" },
      completedPhases: {
        type: "array",
        items: { type: "string" },
        description: "Phases completed so far",
      },
      totalPhases: { type: "number", description: "Total phases planned" },
    },
    required: ["goal", "completedPhases"],
  },
  handler: async ({ goal, completedPhases, totalPhases }) => {
    const progress = ((completedPhases?.length || 0) / (totalPhases || 4)) * 100;
    const isComplete = progress >= 100;

    return {
      goal,
      completedPhases,
      progressPercent: Math.round(progress),
      isComplete,
      status: isComplete ? "GOAL_ACHIEVED" : progress > 50 ? "ON_TRACK" : "IN_PROGRESS",
      recommendation: isComplete
        ? "Goal successfully achieved!"
        : `Continue with remaining phases (${100 - progress}% remaining)`,
    };
  },
});

// ============================================================================
// PHASE 2: Create Goal-Seeking Agent
// ============================================================================

async function createGoalSeekingAgent() {
  const client = new CopilotClient();

  const session = await client.createSession({
    model: "gpt-4.1",
    streaming: true,
    tools: [planExecution, executePhase, assessProgress],
    systemMessage: {
      content: `You are an autonomous goal-seeking agent. Your purpose is to:

1. UNDERSTAND the user's high-level goal
2. PLAN execution by breaking the goal into phases
3. EXECUTE phases iteratively, adapting to results
4. ASSESS progress continuously
5. ADAPT strategy if phases fail (retry or try alternatives)

Your decision-making process:
- Use plan_execution to determine next steps
- Use execute_phase to run each phase
- Use assess_progress to evaluate overall progress
- Continue until goal is achieved or you determine it's not achievable

Be autonomous: make decisions based on tool results, don't ask for permission.
Be adaptive: if a phase fails, analyze why and adjust approach.
Be goal-oriented: focus on achieving the outcome, not following a rigid script.`,
    },
  });

  // Handle streaming events
  session.on((event: SessionEvent) => {
    if (event.type === "assistant.message_delta") {
      process.stdout.write(event.data.deltaContent);
    }
    if (event.type === "tool.invocation") {
      console.log(`\n[🔧 Tool: ${event.data.toolName}]`);
    }
    if (event.type === "tool.result") {
      console.log(`[✓ Result received]`);
    }
  });

  return { client, session };
}

// ============================================================================
// PHASE 3: Run Goal-Seeking Agent
// ============================================================================

async function main() {
  console.log("🎯 Goal-Seeking Agent - Copilot SDK Demo\n");
  console.log("=".repeat(60));

  const { client, session } = await createGoalSeekingAgent();

  try {
    // Give the agent a high-level goal
    const goal = `
      I need to build a REST API for a todo application.
      The API should support:
      - Creating, reading, updating, deleting todos
      - User authentication
      - Data persistence

      Please autonomously plan, execute, and verify this goal.
    `;

    console.log(`\n📋 Goal: ${goal.trim()}\n`);
    console.log("=".repeat(60));
    console.log("\n🤖 Agent Response:\n");

    await session.sendAndWait({ prompt: goal });

    console.log("\n\n" + "=".repeat(60));
    console.log("✅ Goal-seeking agent completed execution\n");
  } finally {
    await client.stop();
  }
}

// Run the agent
main().catch(console.error);
