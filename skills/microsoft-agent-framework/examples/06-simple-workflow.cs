/*
 * Simple Workflow Example (C#)
 *
 * Demonstrates:
 * - Creating graph-based workflows
 * - Sequential agent execution
 * - Parallel agent execution
 * - Conditional routing
 * - Workflow state management
 */

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.Agents.AI;
using Microsoft.Agents.AI.Workflows;

namespace AgentFrameworkExamples
{
    class SimpleWorkflowExample
    {
        static async Task SequentialWorkflow()
        {
            Console.WriteLine("=== Sequential Workflow ===");

            // Create specialized agents
            var researcher = new Agent(
                name: "researcher",
                model: new ModelClient(model: "gpt-4"),
                instructions: "Research topics and gather key facts. Be thorough."
            );

            var writer = new Agent(
                name: "writer",
                model: new ModelClient(model: "gpt-4"),
                instructions: "Write clear, concise content based on research."
            );

            var reviewer = new Agent(
                name: "reviewer",
                model: new ModelClient(model: "gpt-4"),
                instructions: "Review content for accuracy and clarity."
            );

            // Build workflow
            var workflow = new GraphWorkflow();

            workflow.AddNode("research", researcher);
            workflow.AddNode("write", writer);
            workflow.AddNode("review", reviewer);

            // Define sequential flow
            workflow.AddEdge("research", "write");
            workflow.AddEdge("write", "review");

            workflow.SetEntryPoint("research");

            // Execute workflow
            var result = await workflow.RunAsync(
                initialMessage: "Research and write about quantum computing"
            );

            Console.WriteLine($"Final output: {result.FinalOutput}");
            Console.WriteLine();
        }

        static async Task ParallelWorkflow()
        {
            Console.WriteLine("=== Parallel Workflow ===");

            // Create analyst agents
            var securityAnalyst = new Agent(
                name: "security",
                model: new ModelClient(model: "gpt-4"),
                instructions: "Analyze from security perspective."
            );

            var performanceAnalyst = new Agent(
                name: "performance",
                model: new ModelClient(model: "gpt-4"),
                instructions: "Analyze from performance perspective."
            );

            var uxAnalyst = new Agent(
                name: "ux",
                model: new ModelClient(model: "gpt-4"),
                instructions: "Analyze from user experience perspective."
            );

            var synthesizer = new Agent(
                name: "synthesizer",
                model: new ModelClient(model: "gpt-4"),
                instructions: "Synthesize all analyses into comprehensive report."
            );

            // Build workflow
            var workflow = new GraphWorkflow();

            workflow.AddNode("security", securityAnalyst);
            workflow.AddNode("performance", performanceAnalyst);
            workflow.AddNode("ux", uxAnalyst);
            workflow.AddNode("synthesize", synthesizer);

            // Parallel execution - all analysts run concurrently
            workflow.AddEdge("START", new[] { "security", "performance", "ux" });

            // Wait for all analysts, then synthesize
            workflow.AddEdge(new[] { "security", "performance", "ux" }, "synthesize");

            // Execute workflow
            var result = await workflow.RunAsync(
                initialState: new Dictionary<string, object>
                {
                    ["topic"] = "new authentication system"
                }
            );

            Console.WriteLine($"Synthesis: {result.FinalOutput}");
            Console.WriteLine();
        }

        static async Task ConditionalWorkflow()
        {
            Console.WriteLine("=== Conditional Workflow ===");

            // Create agents
            var classifier = new Agent(
                name: "classifier",
                model: new ModelClient(model: "gpt-4"),
                instructions: "Classify queries as 'simple' or 'complex'."
            );

            var simpleHandler = new Agent(
                name: "simple_handler",
                model: new ModelClient(model: "gpt-4"),
                instructions: "Handle simple queries quickly."
            );

            var complexHandler = new Agent(
                name: "complex_handler",
                model: new ModelClient(model: "gpt-4"),
                instructions: "Handle complex queries with detailed analysis."
            );

            // Build workflow
            var workflow = new GraphWorkflow();

            workflow.AddNode("classify", classifier);
            workflow.AddNode("simple", simpleHandler);
            workflow.AddNode("complex", complexHandler);

            // Route based on classification
            workflow.AddConditionalEdge(
                "classify",
                state =>
                {
                    var content = state.GetValueOrDefault("classification", "").ToString().ToLower();
                    return content.Contains("simple") ? "simple" : "complex";
                },
                new Dictionary<string, string>
                {
                    ["simple"] = "simple",
                    ["complex"] = "complex"
                }
            );

            workflow.SetEntryPoint("classify");

            // Test simple query
            var result1 = await workflow.RunAsync(initialMessage: "What's 2+2?");
            Console.WriteLine($"Simple query result: {result1.FinalOutput}");

            // Test complex query
            var result2 = await workflow.RunAsync(
                initialMessage: "Explain the implications of quantum entanglement"
            );
            Console.WriteLine($"Complex query result: {result2.FinalOutput}");
            Console.WriteLine();
        }

        static async Task StatefulWorkflow()
        {
            Console.WriteLine("=== Stateful Workflow ===");

            // Build workflow with state functions
            var workflow = new GraphWorkflow();

            workflow.AddNode("step1", (Dictionary<string, object> state) =>
            {
                state["step1_result"] = "Gathered data";
                state["count"] = (int)state.GetValueOrDefault("count", 0) + 1;
                return state;
            });

            workflow.AddNode("step2", (Dictionary<string, object> state) =>
            {
                state["step2_result"] = $"Processed {state.GetValueOrDefault("step1_result", "nothing")}";
                state["count"] = (int)state.GetValueOrDefault("count", 0) + 1;
                return state;
            });

            workflow.AddNode("step3", (Dictionary<string, object> state) =>
            {
                state["final_result"] = $"Completed {state.GetValueOrDefault("step2_result", "nothing")}";
                state["count"] = (int)state.GetValueOrDefault("count", 0) + 1;
                return state;
            });

            workflow.AddEdge("step1", "step2");
            workflow.AddEdge("step2", "step3");

            workflow.SetEntryPoint("step1");

            // Execute workflow
            var result = await workflow.RunAsync(
                initialState: new Dictionary<string, object> { ["count"] = 0 }
            );

            Console.WriteLine($"Final state: {string.Join(", ", result.State.Select(kv => $"{kv.Key}={kv.Value}"))}");
            Console.WriteLine($"Processing steps completed: {result.State.GetValueOrDefault("count", 0)}");
            Console.WriteLine();
        }

        static async Task Main(string[] args)
        {
            if (string.IsNullOrEmpty(Environment.GetEnvironmentVariable("OPENAI_API_KEY")))
            {
                Console.WriteLine("ERROR: OPENAI_API_KEY environment variable not set");
                return;
            }

            await SequentialWorkflow();
            await ParallelWorkflow();
            await ConditionalWorkflow();
            await StatefulWorkflow();

            Console.WriteLine("✓ All examples completed successfully");
        }
    }
}
