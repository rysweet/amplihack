/*
 * Basic Agent Example (C#)
 *
 * Demonstrates:
 * - Creating a simple conversational agent
 * - Single-turn conversations
 * - Multi-turn conversations with thread
 * - Accessing response metadata
 */

using System;
using System.Threading.Tasks;
using Microsoft.Agents.AI;

namespace AgentFrameworkExamples
{
    class BasicAgentExample
    {
        static async Task SingleTurnExample()
        {
            Console.WriteLine("=== Single-Turn Conversation ===");

            // Create agent
            var agent = new Agent(
                name: "assistant",
                model: new ModelClient(
                    model: "gpt-4",
                    temperature: 0.7
                ),
                instructions: "You are a helpful assistant. Be concise and friendly."
            );

            // Send message
            var response = await agent.RunAsync("What is the capital of France?");

            Console.WriteLine("User: What is the capital of France?");
            Console.WriteLine($"Agent: {response.Content}");
            Console.WriteLine($"Tokens used: {response.Usage.TotalTokens}");
            Console.WriteLine();
        }

        static async Task MultiTurnExample()
        {
            Console.WriteLine("=== Multi-Turn Conversation ===");

            // Create agent
            var agent = new Agent(
                name: "assistant",
                model: new ModelClient(model: "gpt-4"),
                instructions: "You are a helpful assistant with good memory."
            );

            // Create thread to maintain conversation history
            var thread = new Thread();

            // Turn 1
            var response1 = await agent.RunAsync(
                thread: thread,
                message: "My name is Alice and I'm learning C#."
            );
            Console.WriteLine("User: My name is Alice and I'm learning C#.");
            Console.WriteLine($"Agent: {response1.Content}");
            Console.WriteLine();

            // Turn 2 - agent remembers context
            var response2 = await agent.RunAsync(
                thread: thread,
                message: "What's my name?"
            );
            Console.WriteLine("User: What's my name?");
            Console.WriteLine($"Agent: {response2.Content}");
            Console.WriteLine();

            // Turn 3 - agent remembers context
            var response3 = await agent.RunAsync(
                thread: thread,
                message: "What am I learning?"
            );
            Console.WriteLine("User: What am I learning?");
            Console.WriteLine($"Agent: {response3.Content}");
            Console.WriteLine();
        }

        static async Task ResponseMetadataExample()
        {
            Console.WriteLine("=== Response Metadata ===");

            var agent = new Agent(
                name: "assistant",
                model: new ModelClient(model: "gpt-4")
            );

            var response = await agent.RunAsync(
                "Explain quantum computing in one sentence."
            );

            Console.WriteLine($"Content: {response.Content}");
            Console.WriteLine($"Model: {response.Model}");
            Console.WriteLine($"Role: {response.Role}");
            Console.WriteLine($"Prompt tokens: {response.Usage.PromptTokens}");
            Console.WriteLine($"Completion tokens: {response.Usage.CompletionTokens}");
            Console.WriteLine($"Total tokens: {response.Usage.TotalTokens}");
            Console.WriteLine();
        }

        static async Task Main(string[] args)
        {
            // Check for API key
            if (string.IsNullOrEmpty(Environment.GetEnvironmentVariable("OPENAI_API_KEY")))
            {
                Console.WriteLine("ERROR: OPENAI_API_KEY environment variable not set");
                Console.WriteLine("Set it with: export OPENAI_API_KEY=sk-...");
                return;
            }

            await SingleTurnExample();
            await MultiTurnExample();
            await ResponseMetadataExample();

            Console.WriteLine("✓ All examples completed successfully");
        }
    }
}
