# Analyzer Module

High-performance log analysis for amplihack session logs, demonstrating advanced Rust concepts.

## Overview

The analyzer module provides trait-based, pluggable analyzers for extracting insights from log sessions. It showcases:

- **Trait-based design** for polymorphic behavior
- **Iterator patterns** for efficient processing
- **Borrowing** for zero-copy analysis
- **Result types** for robust error handling

## Analyzers

### TimingAnalyzer

Calculates timing statistics for log sessions.

**Output**: `TimingStats`

- `total_duration_secs` - Total session duration
- `entry_count` - Number of log entries
- `avg_time_between_entries` - Average gap between entries

**Example**:

```rust
let analyzer = TimingAnalyzer::new();
let stats = analyzer.analyze(&session)?;

println!("Session lasted {:.2}s", stats.total_duration_secs);
println!("Processed {} entries", stats.entry_count);
```

**Rust Concepts**:

- Zero-sized type (no fields)
- Iterator `min()`/`max()` for duration calculation
- Iterator `windows()` for pairwise operations

### AgentAnalyzer

Tracks agent invocations and durations.

**Output**: `Vec<AgentStats>`

- `name` - Agent name
- `invocation_count` - Number of times invoked
- `total_duration_ms` - Total execution time
- `avg_duration_ms` - Average execution time

**Example**:

```rust
let analyzer = AgentAnalyzer::new();
let stats = analyzer.analyze(&session)?;

for agent in stats {
    println!("{}: {} calls, avg {:.2}ms",
        agent.name,
        agent.invocation_count,
        agent.avg_duration_ms);
}
```

**Rust Concepts**:

- Stateful analyzer with `HashMap`
- Mutable borrowing for aggregation
- `filter_map` chains for processing

### PatternAnalyzer

Detects common patterns in logs.

**Output**: `PatternAnalysis` containing `Vec<LogPattern>`

**Patterns Detected**:

- `ErrorBurst` - Multiple errors in short time
- `LongGap` - Long silence between entries
- `AgentActivity` - High agent usage
- `NoAgentActivity` - Session without agents

**Example**:

```rust
let analyzer = PatternAnalyzer::new();
let analysis = analyzer.analyze(&session)?;

for pattern in analysis.patterns {
    match pattern {
        LogPattern::ErrorBurst { count, duration_secs } => {
            println!("⚠️  {} errors in {:.2}s", count, duration_secs);
        }
        LogPattern::LongGap { duration_secs } => {
            println!("⏸️  {:.2}s gap detected", duration_secs);
        }
        LogPattern::AgentActivity { agent, count } => {
            println!("📈 High activity: {} ({} calls)", agent, count);
        }
        LogPattern::NoAgentActivity => {
            println!("🤖 No agents used");
        }
    }
}
```

**Configurable Thresholds**:

```rust
let analyzer = PatternAnalyzer::with_thresholds(
    5.0,   // error_burst_threshold (errors/sec)
    300.0, // long_gap_threshold (seconds)
    10     // agent_activity_threshold (count)
);
```

**Rust Concepts**:

- Configurable analyzer with fields
- Complex pattern matching
- Time-based windowing with iterators

## Trait Design

All analyzers implement the `Analyzer` trait:

```rust
pub trait Analyzer {
    type Output;

    fn analyze(&self, session: &LogSession) -> ParseResult<Self::Output>;
    fn name(&self) -> &str;
}
```

This enables:

- Polymorphic usage via trait objects
- Associated types for different outputs
- Consistent API across analyzers

## Performance Characteristics

- **Zero-copy**: Analyzers borrow log sessions (`&LogSession`)
- **Lazy evaluation**: Iterators only process what's needed
- **Memory efficient**: No unnecessary cloning
- **Scalable**: HashMap-based aggregation for agent stats

## Testing

Comprehensive test coverage demonstrates:

- Ownership and borrowing patterns
- Iterator usage
- Edge cases (empty sessions, single entries)
- Pattern detection accuracy

Run tests:

```bash
cargo test analyzer
```

## Advanced Usage

### Stateful Analysis Across Sessions

`AgentAnalyzer` can track stats across multiple sessions:

```rust
let mut analyzer = AgentAnalyzer::new();

for session in sessions {
    analyzer.process_entries(&session.entries);
}

let all_stats = analyzer.get_all_stats();
```

### Trait Objects for Polymorphism

```rust
let analyzers: Vec<Box<dyn Analyzer<Output = String>>> = vec![
    Box::new(custom_analyzer1),
    Box::new(custom_analyzer2),
];

for analyzer in &analyzers {
    let result = analyzer.analyze(&session)?;
    println!("{}: {}", analyzer.name(), result);
}
```

## Key Rust Concepts Demonstrated

1. **Traits** - Polymorphic analyzer interface
2. **Associated Types** - Different output types per analyzer
3. **Borrowing** - `&LogSession` avoids unnecessary copying
4. **Lifetimes** - Implicit lifetimes in trait methods
5. **Iterators** - `filter`, `map`, `windows`, `fold`
6. **Option/Result** - Robust error handling
7. **Pattern Matching** - Type-safe enum handling
8. **HashMap** - Efficient aggregation
9. **Zero-Sized Types** - `TimingAnalyzer` has no fields
10. **Trait Objects** - `Box<dyn Analyzer>`

## Extension Points

To create a custom analyzer:

```rust
pub struct CustomAnalyzer {
    // your fields
}

impl Analyzer for CustomAnalyzer {
    type Output = YourOutputType;

    fn analyze(&self, session: &LogSession) -> ParseResult<Self::Output> {
        // your analysis logic
    }

    fn name(&self) -> &str {
        "CustomAnalyzer"
    }
}
```

The trait-based design makes the analyzer system easily extensible without modifying existing code.
