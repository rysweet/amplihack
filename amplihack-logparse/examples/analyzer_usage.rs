// Example demonstrating analyzer module usage
//
// This shows how to:
// - Create and use different analyzers
// - Process log sessions
// - Extract timing and agent statistics
// - Detect patterns in logs

use chrono::{Duration, Utc};

// We can't use the types directly in examples since they're in a binary crate
// This is a standalone example showing the API usage patterns

fn main() {
    println!("Analyzer Module Usage Examples");
    println!("==============================");
    println!();

    println!("1. TimingAnalyzer - Calculate session duration and timing stats");
    println!("   - Total session duration");
    println!("   - Entry count");
    println!("   - Average time between entries");
    println!();

    println!("2. AgentAnalyzer - Track agent invocations");
    println!("   - Count invocations per agent");
    println!("   - Calculate total and average duration");
    println!("   - Aggregate stats across sessions");
    println!();

    println!("3. PatternAnalyzer - Detect common patterns");
    println!("   - Error bursts (rapid error sequences)");
    println!("   - Long gaps between entries");
    println!("   - High agent activity");
    println!("   - Sessions without agent usage");
    println!();

    println!("Example API Usage:");
    println!("==================");
    println!();

    println!("// Create analyzers");
    println!("let timing_analyzer = TimingAnalyzer::new();");
    println!("let agent_analyzer = AgentAnalyzer::new();");
    println!("let pattern_analyzer = PatternAnalyzer::new();");
    println!();

    println!("// Analyze a session");
    println!("let timing_stats = timing_analyzer.analyze(&session)?;");
    println!("println!(\"Duration: {{:.2}}s\", timing_stats.total_duration_secs);");
    println!("println!(\"Entries: {{}}\", timing_stats.entry_count);");
    println!();

    println!("let agent_stats = agent_analyzer.analyze(&session)?;");
    println!("for stats in agent_stats {{");
    println!("    println!(\"Agent: {{}}\", stats.name);");
    println!("    println!(\"  Calls: {{}}\", stats.invocation_count);");
    println!("    println!(\"  Avg duration: {{:.2}}ms\", stats.avg_duration_ms);");
    println!("}}");
    println!();

    println!("let patterns = pattern_analyzer.analyze(&session)?;");
    println!("for pattern in patterns.patterns {{");
    println!("    match pattern {{");
    println!("        LogPattern::ErrorBurst {{ count, duration_secs }} => {{");
    println!("            println!(\"Error burst: {{}} errors in {{:.2}}s\", count, duration_secs);");
    println!("        }}");
    println!("        LogPattern::LongGap {{ duration_secs }} => {{");
    println!("            println!(\"Long gap: {{:.2}}s\", duration_secs);");
    println!("        }}");
    println!("        LogPattern::AgentActivity {{ agent, count }} => {{");
    println!("            println!(\"High activity: {{}} ({{}} calls)\", agent, count);");
    println!("        }}");
    println!("        LogPattern::NoAgentActivity => {{");
    println!("            println!(\"No agent activity detected\");");
    println!("        }}");
    println!("    }}");
    println!("}}");
    println!();

    println!("Key Rust Concepts Demonstrated:");
    println!("================================");
    println!("✓ Traits - Analyzer trait for polymorphic behavior");
    println!("✓ Iterators - Efficient log entry processing");
    println!("✓ Borrowing - All analyzers take &LogSession");
    println!("✓ Result types - Robust error handling");
    println!("✓ HashMap - Agent statistics aggregation");
    println!("✓ Pattern matching - Type-safe pattern detection");
    println!("✓ Zero-copy - No unnecessary data duplication");
}
