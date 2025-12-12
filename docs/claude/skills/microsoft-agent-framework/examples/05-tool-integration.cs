/*
 * Tool Integration Example (C#)
 *
 * Demonstrates:
 * - Creating function tools
 * - Agent automatically calling tools
 * - Tools with multiple parameters
 * - Tool call inspection
 */

using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Microsoft.Agents.AI;

namespace AgentFrameworkExamples
{
    public class WeatherTools
    {
        [FunctionTool(Description = "Get current time for a timezone")]
        public static string GetCurrentTime(
            [Parameter(Description = "Timezone name")] string timezone = "UTC")
        {
            var now = DateTime.Now;
            return $"Current time in {timezone}: {now:yyyy-MM-dd HH:mm:ss}";
        }

        [FunctionTool(Description = "Evaluate a mathematical expression")]
        public static double Calculate(
            [Parameter(Description = "Math expression to evaluate")] string expression)
        {
            // Simple eval - real implementation would be more sophisticated
            var dataTable = new System.Data.DataTable();

            // SECURITY WARNING: DataTable.Compute() can execute arbitrary expressions.
            // In production code with untrusted input, use a safer calculation method
            // or validate/sanitize the expression thoroughly. This example uses a
            // hardcoded expression for demonstration purposes only.
            var result = dataTable.Compute(expression, string.Empty);
            return Convert.ToDouble(result);
        }

        [FunctionTool(Description = "Get weather for a location")]
        public static string GetWeather(
            [Parameter(Description = "City name or zip code")] string location,
            [Parameter(Description = "Temperature units")] string units = "fahrenheit")
        {
            // Mock implementation
            var weatherData = new Dictionary<string, (int temp, string conditions)>
            {
                ["Seattle"] = (62, "Rainy"),
                ["San Francisco"] = (68, "Foggy"),
                ["New York"] = (75, "Sunny")
            };

            var data = weatherData.ContainsKey(location)
                ? weatherData[location]
                : (70, "Clear");

            var temp = data.temp;
            if (units == "celsius")
            {
                temp = (int)((temp - 32) * 5.0 / 9.0);
            }

            return $"Weather in {location}: {data.conditions}, {temp}°{units[0]}";
        }
    }

    class ToolIntegrationExample
    {
        static async Task BasicToolUsage()
        {
            Console.WriteLine("=== Basic Tool Usage ===");

            var agent = new Agent(
                name: "assistant",
                model: new ModelClient(model: "gpt-4"),
                instructions: "You are a helpful assistant with access to tools.",
                tools: new[]
                {
                    typeof(WeatherTools).GetMethod("GetCurrentTime"),
                    typeof(WeatherTools).GetMethod("Calculate"),
                    typeof(WeatherTools).GetMethod("GetWeather")
                }
            );

            var queries = new[]
            {
                "What time is it?",
                "What's 23 times 45?",
                "What's the weather in Seattle?"
            };

            foreach (var query in queries)
            {
                var response = await agent.RunAsync(query);
                Console.WriteLine($"User: {query}");
                Console.WriteLine($"Agent: {response.Content}");
                Console.WriteLine();
            }
        }

        static async Task MultipleToolCalls()
        {
            Console.WriteLine("=== Multiple Tool Calls ===");

            var agent = new Agent(
                name: "assistant",
                model: new ModelClient(model: "gpt-4"),
                instructions: "You are a helpful assistant.",
                tools: new[]
                {
                    typeof(WeatherTools).GetMethod("GetWeather"),
                    typeof(WeatherTools).GetMethod("GetCurrentTime")
                },
                parallelToolCalls: true
            );

            var response = await agent.RunAsync(
                "What's the weather and current time in Seattle?"
            );

            Console.WriteLine("User: What's the weather and current time in Seattle?");
            Console.WriteLine($"Agent: {response.Content}");
            Console.WriteLine();
        }

        static async Task ToolCallInspection()
        {
            Console.WriteLine("=== Tool Call Inspection ===");

            var agent = new Agent(
                name: "assistant",
                model: new ModelClient(model: "gpt-4"),
                tools: new[]
                {
                    typeof(WeatherTools).GetMethod("Calculate"),
                    typeof(WeatherTools).GetMethod("GetWeather")
                }
            );

            var response = await agent.RunAsync(
                "What's 15 * 8 and what's the weather in San Francisco?"
            );

            Console.WriteLine("User: What's 15 * 8 and what's the weather in San Francisco?");
            Console.WriteLine($"Agent: {response.Content}");
            Console.WriteLine("\nTool Calls:");

            foreach (var toolCall in response.ToolCalls)
            {
                Console.WriteLine($"  - Function: {toolCall.Function.Name}");
                Console.WriteLine($"    Arguments: {toolCall.Function.Arguments}");
                Console.WriteLine($"    Result: {toolCall.Result}");
            }
            Console.WriteLine();
        }

        static async Task Main(string[] args)
        {
            if (string.IsNullOrEmpty(Environment.GetEnvironmentVariable("OPENAI_API_KEY")))
            {
                Console.WriteLine("ERROR: OPENAI_API_KEY environment variable not set");
                return;
            }

            await BasicToolUsage();
            await MultipleToolCalls();
            await ToolCallInspection();

            Console.WriteLine("✓ All examples completed successfully");
        }
    }
}
