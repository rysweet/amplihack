// Core data types for amplihack log parser
// 
// This module demonstrates Rust ownership and memory safety concepts

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Represents a single log entry
/// 
/// This struct demonstrates:
/// - Ownership of String data
/// - Borrowing with lifetimes (when we add them)
/// - Serialization with serde
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogEntry {
    /// Timestamp of the log entry
    pub timestamp: DateTime<Utc>,
    
    /// Type of log entry
    pub entry_type: EntryType,
    
    /// Log message content (owned String)
    pub message: String,
    
    /// Optional agent name if this is an agent invocation
    pub agent_name: Option<String>,
    
    /// Optional duration in milliseconds
    pub duration_ms: Option<u64>,
}

/// Types of log entries we can encounter
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum EntryType {
    /// Agent was invoked
    AgentInvocation,
    
    /// General info message
    Info,
    
    /// Warning message
    Warning,
    
    /// Error message
    Error,
    
    /// Decision record
    Decision,
    
    /// Unknown/other
    Unknown,
}

/// A complete log session
/// 
/// Demonstrates:
/// - Ownership of Vec (heap-allocated)
/// - Smart pointers if we add Arc/Rc later
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogSession {
    /// Session identifier
    pub id: String,
    
    /// All entries in this session (owned Vec)
    pub entries: Vec<LogEntry>,
    
    /// Session start time
    pub start_time: DateTime<Utc>,
    
    /// Session end time (if known)
    pub end_time: Option<DateTime<Utc>>,
}

/// Statistics about agent usage
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentStats {
    /// Agent name
    pub name: String,
    
    /// Number of invocations
    pub invocation_count: u32,
    
    /// Total duration in milliseconds
    pub total_duration_ms: u64,
    
    /// Average duration in milliseconds
    pub avg_duration_ms: f64,
}

impl AgentStats {
    /// Create new stats for an agent
    pub fn new(name: String) -> Self {
        Self {
            name,
            invocation_count: 0,
            total_duration_ms: 0,
            avg_duration_ms: 0.0,
        }
    }
    
    /// Add a duration measurement
    /// 
    /// Demonstrates: Mutable borrowing (&mut self)
    pub fn add_duration(&mut self, duration_ms: u64) {
        self.invocation_count += 1;
        self.total_duration_ms += duration_ms;
        self.avg_duration_ms = self.total_duration_ms as f64 / self.invocation_count as f64;
    }
}

/// Timing statistics for a session
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimingStats {
    /// Total session duration in seconds
    pub total_duration_secs: f64,
    
    /// Number of entries processed
    pub entry_count: usize,
    
    /// Average time between entries in seconds
    pub avg_time_between_entries: f64,
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_agent_stats_ownership() {
        // Demonstrates ownership and borrowing
        let mut stats = AgentStats::new("test-agent".to_string());
        
        // Mutable borrow to add duration
        stats.add_duration(100);
        stats.add_duration(200);
        
        // Check calculations
        assert_eq!(stats.invocation_count, 2);
        assert_eq!(stats.total_duration_ms, 300);
        assert_eq!(stats.avg_duration_ms, 150.0);
    }
    
    #[test]
    fn test_log_entry_creation() {
        // Demonstrates ownership of String
        let message = String::from("Test message");
        let entry = LogEntry {
            timestamp: Utc::now(),
            entry_type: EntryType::Info,
            message, // Ownership moves here
            agent_name: None,
            duration_ms: None,
        };
        
        // message is no longer accessible here (moved)
        assert_eq!(entry.message, "Test message");
    }
}
