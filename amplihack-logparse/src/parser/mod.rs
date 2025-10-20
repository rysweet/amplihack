// Log parser module
//
// Implements log parsing using Rust concepts from knowledge base:
// - Ownership: LogEntry owns its Strings
// - Borrowing: parse functions borrow input
// - Lifetimes: Potential for zero-copy with &'a str
// - Error handling: Result with custom ParseError
// - Iterators: Processing lines efficiently

use crate::error::{ParseError, ParseResult};
use crate::types::{LogEntry, EntryType};
use chrono::{DateTime, Utc};
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;

/// Parse a log file and return all entries
///
/// Demonstrates:
/// - Borrowing: Takes &Path, doesn't need ownership
/// - Error handling: Returns Result with ?
/// - Iterators: Chain operations efficiently
pub fn parse_log_file(path: &Path) -> ParseResult<Vec<LogEntry>> {
    let file = File::open(path)
        .map_err(|_| ParseError::FileNotFound(path.to_path_buf()))?;

    let reader = BufReader::new(file);
    let mut entries = Vec::new();

    for (line_num, line_result) in reader.lines().enumerate() {
        let line = line_result?;  // ? operator for error propagation

        // Skip empty lines
        if line.trim().is_empty() {
            continue;
        }

        // Parse each line into a LogEntry
        match parse_log_entry(&line) {
            Ok(entry) => entries.push(entry),
            Err(e) => {
                // Log parsing error but continue (resilient parsing)
                eprintln!("Warning: Failed to parse line {}: {}", line_num + 1, e);
            }
        }
    }

    Ok(entries)
}

/// Parse a single log line into a LogEntry
///
/// Demonstrates:
/// - Borrowing: Takes &str, doesn't need ownership of line
/// - Error handling: Returns Result
/// - String handling: Parses and creates owned Strings
fn parse_log_entry(line: &str) -> ParseResult<LogEntry> {
    // Simple log format: [TIMESTAMP] LEVEL: MESSAGE
    // Example: [2025-10-18T14:30:45Z] INFO: Starting analysis

    if !line.starts_with('[') {
        return Err(ParseError::MalformedEntry {
            line: 0,
            details: "Line doesn't start with '['".to_string(),
        });
    }

    // Find timestamp end
    let timestamp_end = line.find(']')
        .ok_or_else(|| ParseError::MalformedEntry {
            line: 0,
            details: "No closing ']' for timestamp".to_string(),
        })?;

    // Extract and parse timestamp
    let timestamp_str = &line[1..timestamp_end];
    let timestamp = parse_timestamp(timestamp_str)?;

    // Rest of line after timestamp
    let rest = &line[timestamp_end + 1..].trim();

    // Parse level and message
    let (entry_type, message) = if let Some(colon_pos) = rest.find(':') {
        let level_str = &rest[..colon_pos].trim();
        let msg = rest[colon_pos + 1..].trim().to_string();
        let entry_type = parse_entry_type(level_str);
        (entry_type, msg)
    } else {
        (EntryType::Unknown, rest.to_string())
    };

    Ok(LogEntry {
        timestamp,
        entry_type,
        message,
        agent_name: None,  // Could be extracted from message
        duration_ms: None, // Could be extracted from message
    })
}

/// Parse timestamp string into DateTime
///
/// Demonstrates:
/// - Borrowing: Takes &str
/// - Error handling: Maps parse errors to our error type
fn parse_timestamp(s: &str) -> ParseResult<DateTime<Utc>> {
    use chrono::NaiveDateTime;

    // Try standard ISO 8601 format first
    if let Ok(dt) = s.parse::<DateTime<Utc>>() {
        return Ok(dt);
    }

    // Try format with microseconds without timezone (e.g., "2025-10-18T11:25:37.950859")
    // Parse as naive datetime and assume UTC
    if let Ok(naive_dt) = NaiveDateTime::parse_from_str(s, "%Y-%m-%dT%H:%M:%S%.f") {
        return Ok(DateTime::<Utc>::from_naive_utc_and_offset(naive_dt, Utc));
    }

    // Try format with Z timezone
    if let Ok(dt) = DateTime::parse_from_str(s, "%Y-%m-%dT%H:%M:%S%.fZ") {
        return Ok(dt.with_timezone(&Utc));
    }

    Err(ParseError::InvalidTimestamp(s.to_string()))
}

/// Parse entry type from level string
///
/// Demonstrates:
/// - Borrowing: Takes &str
/// - Pattern matching: Match string to enum variant
fn parse_entry_type(s: &str) -> EntryType {
    match s.to_uppercase().as_str() {
        "INFO" => EntryType::Info,
        "WARN" | "WARNING" => EntryType::Warning,
        "ERROR" => EntryType::Error,
        "AGENT" => EntryType::AgentInvocation,
        "DECISION" => EntryType::Decision,
        _ => EntryType::Unknown,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_entry_type() {
        assert_eq!(parse_entry_type("INFO"), EntryType::Info);
        assert_eq!(parse_entry_type("info"), EntryType::Info);
        assert_eq!(parse_entry_type("ERROR"), EntryType::Error);
        assert_eq!(parse_entry_type("unknown"), EntryType::Unknown);
    }

    #[test]
    fn test_parse_timestamp() {
        let result = parse_timestamp("2025-10-18T14:30:45Z");
        assert!(result.is_ok());
    }

    #[test]
    fn test_parse_log_entry() {
        let line = "[2025-10-18T14:30:45Z] INFO: Test message";
        let result = parse_log_entry(line);

        assert!(result.is_ok());
        let entry = result.unwrap();
        assert_eq!(entry.entry_type, EntryType::Info);
        assert_eq!(entry.message, "Test message");
    }

    #[test]
    fn test_parse_malformed_entry() {
        let line = "This is not a valid log line";
        let result = parse_log_entry(line);
        assert!(result.is_err());
    }
}
