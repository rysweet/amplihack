// amplihack-logparse - High-performance log parser for amplihack session logs
//
// This tool demonstrates Rust's memory safety and ownership system by providing
// fast, safe parsing of amplihack log files.

mod types;
mod error;
mod parser;
mod analyzer;

use std::path::PathBuf;
use std::time::Instant;
use clap::{Parser, Subcommand};
use chrono::Utc;

use crate::analyzer::{Analyzer, TimingAnalyzer, AgentAnalyzer, PatternAnalyzer};
use crate::error::ParseResult;
use crate::parser::parse_log_file;
use crate::types::{LogSession, EntryType};

#[derive(Parser)]
#[command(name = "amplihack-logparse")]
#[command(about = "High-performance log parser for amplihack session logs", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Parse a single session log
    Parse {
        /// Path to the session directory
        session_path: PathBuf,
    },
    /// Analyze logs and generate statistics
    Analyze {
        /// Path to logs directory (default: .claude/runtime/logs)
        #[arg(short, long, default_value = ".claude/runtime/logs")]
        logs_dir: PathBuf,

        /// Only analyze sessions from last N days
        #[arg(short, long)]
        since: Option<u32>,
    },
    /// Query logs with filters
    Query {
        /// Filter by agent name
        #[arg(short, long)]
        agent: Option<String>,

        /// Search for text in messages
        #[arg(short, long)]
        contains: Option<String>,
    },
    /// Run performance benchmarks
    Bench {
        /// Number of iterations
        #[arg(short, long, default_value = "100")]
        iterations: u32,
    },
}

fn main() {
    let cli = Cli::parse();

    let result = match &cli.command {
        Commands::Parse { session_path } => handle_parse(session_path),
        Commands::Analyze { logs_dir, since } => handle_analyze(logs_dir, *since),
        Commands::Query { agent, contains } => handle_query(agent.as_deref(), contains.as_deref()),
        Commands::Bench { iterations } => handle_bench(*iterations),
    };

    if let Err(e) = result {
        eprintln!("Error: {}", e);
        std::process::exit(1);
    }
}

fn handle_parse(session_path: &PathBuf) -> ParseResult<()> {
    println!("Parsing session: {:?}", session_path);

    let entries = parse_log_file(session_path)?;

    println!("\nParsed {} log entries:", entries.len());
    println!("{:-<80}", "");

    for (idx, entry) in entries.iter().enumerate().take(10) {
        println!(
            "[{}] {} | {:?} | {}",
            idx + 1,
            entry.timestamp.format("%Y-%m-%d %H:%M:%S"),
            entry.entry_type,
            if entry.message.len() > 60 {
                format!("{}...", &entry.message[..60])
            } else {
                entry.message.clone()
            }
        );

        if let Some(ref agent) = entry.agent_name {
            println!("    Agent: {}", agent);
        }

        if let Some(duration) = entry.duration_ms {
            println!("    Duration: {}ms", duration);
        }
    }

    if entries.len() > 10 {
        println!("\n... and {} more entries", entries.len() - 10);
    }

    println!("\nSummary:");
    println!("  Total entries: {}", entries.len());

    let entry_type_counts = count_entry_types(&entries);
    for (entry_type, count) in entry_type_counts {
        println!("  {:?}: {}", entry_type, count);
    }

    Ok(())
}

fn handle_analyze(logs_dir: &PathBuf, since: Option<u32>) -> ParseResult<()> {
    println!("Analyzing logs in: {:?}", logs_dir);

    if let Some(days) = since {
        println!("Only analyzing last {} days", days);
    }

    if !logs_dir.exists() {
        return Err(crate::error::ParseError::FileNotFound(logs_dir.clone()));
    }

    let log_files = std::fs::read_dir(logs_dir)?
        .filter_map(|entry| entry.ok())
        .filter(|entry| {
            let path = entry.path();
            path.is_file() && path.extension().and_then(|s| s.to_str()) == Some("log")
        })
        .collect::<Vec<_>>();

    if log_files.is_empty() {
        println!("No .log files found in directory");
        return Ok(());
    }

    println!("\nFound {} log files to analyze", log_files.len());
    println!("{:=<80}", "");

    let mut all_entries = Vec::new();

    for file_entry in log_files {
        let path = file_entry.path();
        match parse_log_file(&path) {
            Ok(entries) => {
                println!("Parsed {}: {} entries", path.display(), entries.len());
                all_entries.extend(entries);
            }
            Err(e) => {
                eprintln!("Warning: Failed to parse {}: {}", path.display(), e);
            }
        }
    }

    if all_entries.is_empty() {
        println!("\nNo entries found to analyze");
        return Ok(());
    }

    let session = create_session_from_entries("aggregate", all_entries);

    println!("\n{:=<80}", "");
    println!("ANALYSIS RESULTS");
    println!("{:=<80}", "");

    let timing_analyzer = TimingAnalyzer::new();
    if let Ok(timing_stats) = timing_analyzer.analyze(&session) {
        println!("\nTiming Statistics:");
        println!("  Total duration: {:.2} seconds", timing_stats.total_duration_secs);
        println!("  Entry count: {}", timing_stats.entry_count);
        println!("  Avg time between entries: {:.2}s", timing_stats.avg_time_between_entries);
    }

    let agent_analyzer = AgentAnalyzer::new();
    if let Ok(agent_stats) = agent_analyzer.analyze(&session) {
        println!("\nAgent Statistics:");
        if agent_stats.is_empty() {
            println!("  No agent invocations found");
        } else {
            for stats in agent_stats {
                println!("  {}", stats.name);
                println!("    Invocations: {}", stats.invocation_count);
                println!("    Total duration: {}ms", stats.total_duration_ms);
                println!("    Avg duration: {:.2}ms", stats.avg_duration_ms);
            }
        }
    }

    let pattern_analyzer = PatternAnalyzer::new();
    if let Ok(pattern_analysis) = pattern_analyzer.analyze(&session) {
        println!("\nPattern Detection:");
        if pattern_analysis.patterns.is_empty() {
            println!("  No significant patterns detected");
        } else {
            for pattern in pattern_analysis.patterns {
                println!("  {:?}", pattern);
            }
        }
    }

    println!("\n{:=<80}", "");

    Ok(())
}

fn handle_query(agent: Option<&str>, contains: Option<&str>) -> ParseResult<()> {
    println!("Querying logs");

    let logs_dir = PathBuf::from(".claude/runtime/logs");

    if !logs_dir.exists() {
        return Err(crate::error::ParseError::FileNotFound(logs_dir));
    }

    let log_files = std::fs::read_dir(&logs_dir)?
        .filter_map(|entry| entry.ok())
        .filter(|entry| {
            let path = entry.path();
            path.is_file() && path.extension().and_then(|s| s.to_str()) == Some("log")
        })
        .collect::<Vec<_>>();

    let mut all_entries = Vec::new();

    for file_entry in log_files {
        let path = file_entry.path();
        if let Ok(entries) = parse_log_file(&path) {
            all_entries.extend(entries);
        }
    }

    let filtered_entries: Vec<_> = all_entries
        .iter()
        .filter(|entry| {
            let agent_match = agent
                .map(|a| entry.agent_name.as_ref().map_or(false, |name| name.contains(a)))
                .unwrap_or(true);

            let text_match = contains
                .map(|text| entry.message.to_lowercase().contains(&text.to_lowercase()))
                .unwrap_or(true);

            agent_match && text_match
        })
        .collect();

    println!("\nQuery Filters:");
    if let Some(agent_name) = agent {
        println!("  Agent: {}", agent_name);
    }
    if let Some(search_text) = contains {
        println!("  Contains: {}", search_text);
    }

    println!("\nFound {} matching entries:", filtered_entries.len());
    println!("{:-<80}", "");

    for (idx, entry) in filtered_entries.iter().enumerate().take(20) {
        println!(
            "[{}] {} | {:?}",
            idx + 1,
            entry.timestamp.format("%Y-%m-%d %H:%M:%S"),
            entry.entry_type
        );
        println!("    {}", entry.message);

        if let Some(ref agent_name) = entry.agent_name {
            println!("    Agent: {}", agent_name);
        }
        println!();
    }

    if filtered_entries.len() > 20 {
        println!("... and {} more entries", filtered_entries.len() - 20);
    }

    Ok(())
}

fn handle_bench(iterations: u32) -> ParseResult<()> {
    println!("Running benchmarks with {} iterations", iterations);

    let logs_dir = PathBuf::from(".claude/runtime/logs");

    if !logs_dir.exists() {
        return Err(crate::error::ParseError::FileNotFound(logs_dir));
    }

    let log_file = std::fs::read_dir(&logs_dir)?
        .filter_map(|entry| entry.ok())
        .find(|entry| {
            let path = entry.path();
            path.is_file() && path.extension().and_then(|s| s.to_str()) == Some("log")
        })
        .map(|e| e.path());

    let test_file = match log_file {
        Some(path) => path,
        None => {
            println!("No log files found for benchmarking");
            return Ok(());
        }
    };

    println!("Benchmarking with file: {}", test_file.display());
    println!("{:=<80}", "");

    let mut parse_times = Vec::new();

    println!("\nRunning parse benchmarks...");
    for i in 0..iterations {
        let start = Instant::now();
        let entries = parse_log_file(&test_file)?;
        let elapsed = start.elapsed();
        parse_times.push(elapsed.as_micros() as f64 / 1000.0);

        if i == 0 {
            println!("  First run parsed {} entries", entries.len());
        }

        if (i + 1) % 10 == 0 {
            print!(".");
            if (i + 1) % 50 == 0 {
                println!(" {}/{}", i + 1, iterations);
            }
        }
    }
    println!();

    let avg_time = parse_times.iter().sum::<f64>() / parse_times.len() as f64;
    let min_time = parse_times.iter().cloned().fold(f64::INFINITY, f64::min);
    let max_time = parse_times.iter().cloned().fold(f64::NEG_INFINITY, f64::max);

    println!("\n{:=<80}", "");
    println!("BENCHMARK RESULTS");
    println!("{:=<80}", "");
    println!("Parse Performance:");
    println!("  Iterations: {}", iterations);
    println!("  Average time: {:.2}ms", avg_time);
    println!("  Min time: {:.2}ms", min_time);
    println!("  Max time: {:.2}ms", max_time);

    if let Ok(entries) = parse_log_file(&test_file) {
        let session = create_session_from_entries("bench", entries);

        let mut analyzer_times = Vec::new();

        println!("\nRunning analyzer benchmarks...");
        for _ in 0..iterations {
            let start = Instant::now();

            let timing_analyzer = TimingAnalyzer::new();
            let _ = timing_analyzer.analyze(&session);

            let agent_analyzer = AgentAnalyzer::new();
            let _ = agent_analyzer.analyze(&session);

            let pattern_analyzer = PatternAnalyzer::new();
            let _ = pattern_analyzer.analyze(&session);

            let elapsed = start.elapsed();
            analyzer_times.push(elapsed.as_micros() as f64 / 1000.0);
        }

        let avg_analyzer_time = analyzer_times.iter().sum::<f64>() / analyzer_times.len() as f64;
        let min_analyzer_time = analyzer_times.iter().cloned().fold(f64::INFINITY, f64::min);
        let max_analyzer_time = analyzer_times.iter().cloned().fold(f64::NEG_INFINITY, f64::max);

        println!("\nAnalyzer Performance (all 3 analyzers):");
        println!("  Average time: {:.2}ms", avg_analyzer_time);
        println!("  Min time: {:.2}ms", min_analyzer_time);
        println!("  Max time: {:.2}ms", max_analyzer_time);
    }

    println!("{:=<80}", "");

    Ok(())
}

fn count_entry_types(entries: &[crate::types::LogEntry]) -> Vec<(EntryType, usize)> {
    use std::collections::HashMap;

    let mut counts = HashMap::new();

    for entry in entries {
        *counts.entry(entry.entry_type).or_insert(0) += 1;
    }

    let mut result: Vec<_> = counts.into_iter().collect();
    result.sort_by_key(|(_, count)| std::cmp::Reverse(*count));

    result
}

fn create_session_from_entries(id: &str, entries: Vec<crate::types::LogEntry>) -> LogSession {
    let start_time = entries
        .first()
        .map(|e| e.timestamp)
        .unwrap_or_else(Utc::now);

    let end_time = entries.last().map(|e| e.timestamp);

    LogSession {
        id: id.to_string(),
        entries,
        start_time,
        end_time,
    }
}
