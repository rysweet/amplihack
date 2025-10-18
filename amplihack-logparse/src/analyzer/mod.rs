// Analyzer module for amplihack log parser
//
// Demonstrates advanced Rust concepts:
// - Trait-based design for pluggable analyzers
// - Iterator patterns for efficient processing
// - Borrowing and lifetimes for zero-copy analysis
// - Result types for robust error handling

use crate::error::ParseResult;
use crate::types::{AgentStats, LogEntry, LogSession, TimingStats};
use std::collections::HashMap;

/// Trait for analyzers that can process log sessions
///
/// Demonstrates:
/// - Trait definition for polymorphic behavior
/// - Associated types for flexibility
/// - Borrowing with lifetime 'a
pub trait Analyzer {
    /// The type of result this analyzer produces
    type Output;

    /// Analyze a log session
    ///
    /// Takes a borrowed reference to avoid unnecessary copying
    fn analyze(&self, session: &LogSession) -> ParseResult<Self::Output>;

    /// Get analyzer name for reporting
    fn name(&self) -> &str;
}

/// Analyzer for timing statistics
///
/// Demonstrates:
/// - Zero-sized type (no fields)
/// - Trait implementation
pub struct TimingAnalyzer;

impl TimingAnalyzer {
    /// Create a new timing analyzer
    pub fn new() -> Self {
        Self
    }

    /// Calculate session duration from entries
    ///
    /// Demonstrates:
    /// - Iterator usage with min()/max()
    /// - Option handling
    /// - Borrowing entries
    fn calculate_duration(entries: &[LogEntry]) -> Option<f64> {
        let first = entries.iter().map(|e| &e.timestamp).min()?;
        let last = entries.iter().map(|e| &e.timestamp).max()?;

        let duration = (*last - *first).num_milliseconds() as f64 / 1000.0;
        Some(duration)
    }

    /// Calculate average time between entries
    ///
    /// Demonstrates:
    /// - Iterator windows for pairwise operations
    /// - Fold for aggregation
    /// - Borrowing
    fn avg_time_between_entries(entries: &[LogEntry]) -> f64 {
        if entries.len() < 2 {
            return 0.0;
        }

        // Use windows to get consecutive pairs
        let total_ms: i64 = entries
            .windows(2)
            .map(|window| {
                let delta = window[1].timestamp - window[0].timestamp;
                delta.num_milliseconds()
            })
            .sum();

        let count = entries.len() - 1;
        (total_ms as f64 / 1000.0) / count as f64
    }
}

impl Default for TimingAnalyzer {
    fn default() -> Self {
        Self::new()
    }
}

impl Analyzer for TimingAnalyzer {
    type Output = TimingStats;

    fn analyze(&self, session: &LogSession) -> ParseResult<Self::Output> {
        let total_duration_secs =
            Self::calculate_duration(&session.entries).unwrap_or(0.0);

        let avg_time_between_entries =
            Self::avg_time_between_entries(&session.entries);

        Ok(TimingStats {
            total_duration_secs,
            entry_count: session.entries.len(),
            avg_time_between_entries,
        })
    }

    fn name(&self) -> &str {
        "TimingAnalyzer"
    }
}

/// Analyzer for agent usage statistics
///
/// Demonstrates:
/// - Stateful analyzer (has fields)
/// - HashMap for aggregation
/// - Mutable borrowing
pub struct AgentAnalyzer {
    /// Track agents across multiple sessions
    agent_map: HashMap<String, AgentStats>,
}

impl AgentAnalyzer {
    /// Create a new agent analyzer
    pub fn new() -> Self {
        Self {
            agent_map: HashMap::new(),
        }
    }

    /// Process entries to extract agent information
    ///
    /// Demonstrates:
    /// - Iterator filter/map chains
    /// - Option handling with filter_map
    /// - Mutable borrowing with &mut self
    fn process_entries(&mut self, entries: &[LogEntry]) {
        // Find all agent invocations
        for entry in entries
            .iter()
            .filter(|e| e.agent_name.is_some())
        {
            let agent_name = entry.agent_name.as_ref().unwrap();

            // Get or create agent stats
            let stats = self.agent_map
                .entry(agent_name.clone())
                .or_insert_with(|| AgentStats::new(agent_name.clone()));

            // Add duration if available
            if let Some(duration_ms) = entry.duration_ms {
                stats.add_duration(duration_ms);
            } else {
                // Count invocation even without duration
                stats.invocation_count += 1;
            }
        }
    }

    /// Get all agent statistics
    ///
    /// Demonstrates:
    /// - Borrowing self
    /// - Collecting into Vec
    /// - Cloning for ownership transfer
    pub fn get_all_stats(&self) -> Vec<AgentStats> {
        self.agent_map.values().cloned().collect()
    }

    /// Get stats for a specific agent
    ///
    /// Demonstrates:
    /// - Borrowing with Option return
    /// - HashMap lookup
    pub fn get_agent_stats(&self, agent_name: &str) -> Option<&AgentStats> {
        self.agent_map.get(agent_name)
    }

    /// Clear all accumulated statistics
    ///
    /// Demonstrates:
    /// - Mutable borrowing
    pub fn clear(&mut self) {
        self.agent_map.clear();
    }
}

impl Default for AgentAnalyzer {
    fn default() -> Self {
        Self::new()
    }
}

impl Analyzer for AgentAnalyzer {
    type Output = Vec<AgentStats>;

    fn analyze(&self, session: &LogSession) -> ParseResult<Self::Output> {
        // Create a temporary analyzer for this session
        let mut temp_analyzer = Self::new();
        temp_analyzer.process_entries(&session.entries);
        Ok(temp_analyzer.get_all_stats())
    }

    fn name(&self) -> &str {
        "AgentAnalyzer"
    }
}

/// Pattern types detected in logs
#[derive(Debug, Clone, PartialEq)]
pub enum LogPattern {
    /// Rapid error sequence (multiple errors in short time)
    ErrorBurst { count: usize, duration_secs: f64 },

    /// Long gap between entries
    LongGap { duration_secs: f64 },

    /// High agent activity
    AgentActivity { agent: String, count: usize },

    /// Session without agent usage
    NoAgentActivity,
}

/// Pattern detection results
#[derive(Debug, Clone)]
pub struct PatternAnalysis {
    pub patterns: Vec<LogPattern>,
}

/// Analyzer for detecting patterns in logs
///
/// Demonstrates:
/// - Configurable analyzer with thresholds
/// - Complex pattern detection
pub struct PatternAnalyzer {
    /// Threshold for error burst detection (errors per second)
    error_burst_threshold: f64,

    /// Threshold for long gap detection (seconds)
    long_gap_threshold: f64,

    /// Threshold for agent activity (invocation count)
    agent_activity_threshold: usize,
}

impl PatternAnalyzer {
    /// Create a new pattern analyzer with default thresholds
    pub fn new() -> Self {
        Self {
            error_burst_threshold: 5.0,
            long_gap_threshold: 300.0,
            agent_activity_threshold: 10,
        }
    }

    /// Create with custom thresholds
    pub fn with_thresholds(
        error_burst_threshold: f64,
        long_gap_threshold: f64,
        agent_activity_threshold: usize,
    ) -> Self {
        Self {
            error_burst_threshold,
            long_gap_threshold,
            agent_activity_threshold,
        }
    }

    /// Detect error bursts
    ///
    /// Demonstrates:
    /// - Iterator filtering
    /// - Time-based windowing
    /// - Pattern matching
    fn detect_error_bursts(&self, entries: &[LogEntry]) -> Vec<LogPattern> {
        let mut patterns = Vec::new();

        if entries.len() < 2 {
            return patterns;
        }

        // Find sequences of errors
        let error_entries: Vec<_> = entries
            .iter()
            .enumerate()
            .filter(|(_, e)| matches!(e.entry_type, crate::types::EntryType::Error))
            .collect();

        if error_entries.len() < 2 {
            return patterns;
        }

        // Check for bursts (3+ errors within short time)
        for window in error_entries.windows(3) {
            let first_time = window.first().unwrap().1.timestamp;
            let last_time = window.last().unwrap().1.timestamp;
            let duration_secs = (last_time - first_time).num_milliseconds() as f64 / 1000.0;

            if duration_secs > 0.0 && (3.0 / duration_secs) >= self.error_burst_threshold {
                patterns.push(LogPattern::ErrorBurst {
                    count: 3,
                    duration_secs,
                });
            }
        }

        patterns
    }

    /// Detect long gaps between entries
    ///
    /// Demonstrates:
    /// - Iterator windows
    /// - Time calculations
    fn detect_long_gaps(&self, entries: &[LogEntry]) -> Vec<LogPattern> {
        entries
            .windows(2)
            .filter_map(|window| {
                let gap = (window[1].timestamp - window[0].timestamp).num_milliseconds() as f64
                    / 1000.0;

                if gap > self.long_gap_threshold {
                    Some(LogPattern::LongGap { duration_secs: gap })
                } else {
                    None
                }
            })
            .collect()
    }

    /// Detect high agent activity
    ///
    /// Demonstrates:
    /// - HashMap aggregation
    /// - Iterator chains
    fn detect_agent_activity(&self, entries: &[LogEntry]) -> Vec<LogPattern> {
        let mut agent_counts: HashMap<String, usize> = HashMap::new();

        for entry in entries.iter().filter(|e| e.agent_name.is_some()) {
            let agent = entry.agent_name.as_ref().unwrap();
            *agent_counts.entry(agent.clone()).or_insert(0) += 1;
        }

        agent_counts
            .into_iter()
            .filter(|(_, count)| *count >= self.agent_activity_threshold)
            .map(|(agent, count)| LogPattern::AgentActivity { agent, count })
            .collect()
    }

    /// Check if session has no agent activity
    fn detect_no_agent_activity(&self, entries: &[LogEntry]) -> Option<LogPattern> {
        let has_agents = entries.iter().any(|e| e.agent_name.is_some());

        if !has_agents && !entries.is_empty() {
            Some(LogPattern::NoAgentActivity)
        } else {
            None
        }
    }
}

impl Default for PatternAnalyzer {
    fn default() -> Self {
        Self::new()
    }
}

impl Analyzer for PatternAnalyzer {
    type Output = PatternAnalysis;

    fn analyze(&self, session: &LogSession) -> ParseResult<Self::Output> {
        let mut patterns = Vec::new();

        // Detect various patterns
        patterns.extend(self.detect_error_bursts(&session.entries));
        patterns.extend(self.detect_long_gaps(&session.entries));
        patterns.extend(self.detect_agent_activity(&session.entries));

        if let Some(pattern) = self.detect_no_agent_activity(&session.entries) {
            patterns.push(pattern);
        }

        Ok(PatternAnalysis { patterns })
    }

    fn name(&self) -> &str {
        "PatternAnalyzer"
    }
}

/// Composite analyzer that runs multiple analyzers
///
/// Demonstrates:
/// - Trait objects (Box<dyn Analyzer>)
/// - Polymorphism
pub struct CompositeAnalyzer {
    analyzers: Vec<Box<dyn Analyzer<Output = String>>>,
}

impl CompositeAnalyzer {
    pub fn new() -> Self {
        Self {
            analyzers: Vec::new(),
        }
    }

    pub fn add_analyzer<A>(&mut self, analyzer: A)
    where
        A: Analyzer<Output = String> + 'static,
    {
        self.analyzers.push(Box::new(analyzer));
    }

    pub fn run_all(&self, session: &LogSession) -> Vec<(String, ParseResult<String>)> {
        self.analyzers
            .iter()
            .map(|analyzer| {
                let name = analyzer.name().to_string();
                let result = analyzer.analyze(session);
                (name, result)
            })
            .collect()
    }
}

impl Default for CompositeAnalyzer {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::EntryType;
    use chrono::{Duration, Utc};

    fn create_test_session() -> LogSession {
        let now = Utc::now();

        let entries = vec![
            LogEntry {
                timestamp: now,
                entry_type: EntryType::Info,
                message: "Start".to_string(),
                agent_name: None,
                duration_ms: None,
            },
            LogEntry {
                timestamp: now + Duration::seconds(10),
                entry_type: EntryType::AgentInvocation,
                message: "Agent called".to_string(),
                agent_name: Some("test-agent".to_string()),
                duration_ms: Some(100),
            },
            LogEntry {
                timestamp: now + Duration::seconds(20),
                entry_type: EntryType::AgentInvocation,
                message: "Agent called again".to_string(),
                agent_name: Some("test-agent".to_string()),
                duration_ms: Some(200),
            },
            LogEntry {
                timestamp: now + Duration::seconds(30),
                entry_type: EntryType::Info,
                message: "End".to_string(),
                agent_name: None,
                duration_ms: None,
            },
        ];

        LogSession {
            id: "test-session".to_string(),
            entries,
            start_time: now,
            end_time: Some(now + Duration::seconds(30)),
        }
    }

    #[test]
    fn test_timing_analyzer() {
        let analyzer = TimingAnalyzer::new();
        let session = create_test_session();

        let result = analyzer.analyze(&session);
        assert!(result.is_ok());

        let stats = result.unwrap();
        assert_eq!(stats.entry_count, 4);
        assert_eq!(stats.total_duration_secs, 30.0);
        assert_eq!(stats.avg_time_between_entries, 10.0);
    }

    #[test]
    fn test_agent_analyzer() {
        let analyzer = AgentAnalyzer::new();
        let session = create_test_session();

        let result = analyzer.analyze(&session);
        assert!(result.is_ok());

        let stats = result.unwrap();
        assert_eq!(stats.len(), 1);

        let agent_stats = &stats[0];
        assert_eq!(agent_stats.name, "test-agent");
        assert_eq!(agent_stats.invocation_count, 2);
        assert_eq!(agent_stats.total_duration_ms, 300);
        assert_eq!(agent_stats.avg_duration_ms, 150.0);
    }

    #[test]
    fn test_agent_analyzer_stateful() {
        let mut analyzer = AgentAnalyzer::new();
        let session = create_test_session();

        // Process entries directly
        analyzer.process_entries(&session.entries);

        let stats = analyzer.get_agent_stats("test-agent");
        assert!(stats.is_some());

        let stats = stats.unwrap();
        assert_eq!(stats.invocation_count, 2);
        assert_eq!(stats.total_duration_ms, 300);

        // Test clear
        analyzer.clear();
        assert!(analyzer.get_agent_stats("test-agent").is_none());
    }

    #[test]
    fn test_pattern_analyzer_error_burst() {
        let analyzer = PatternAnalyzer::new();
        let now = Utc::now();

        let entries = vec![
            LogEntry {
                timestamp: now,
                entry_type: EntryType::Error,
                message: "Error 1".to_string(),
                agent_name: None,
                duration_ms: None,
            },
            LogEntry {
                timestamp: now + Duration::milliseconds(100),
                entry_type: EntryType::Error,
                message: "Error 2".to_string(),
                agent_name: None,
                duration_ms: None,
            },
            LogEntry {
                timestamp: now + Duration::milliseconds(200),
                entry_type: EntryType::Error,
                message: "Error 3".to_string(),
                agent_name: None,
                duration_ms: None,
            },
        ];

        let session = LogSession {
            id: "error-session".to_string(),
            entries,
            start_time: now,
            end_time: Some(now + Duration::milliseconds(200)),
        };

        let result = analyzer.analyze(&session);
        assert!(result.is_ok());

        let analysis = result.unwrap();
        let has_error_burst = analysis
            .patterns
            .iter()
            .any(|p| matches!(p, LogPattern::ErrorBurst { .. }));

        assert!(has_error_burst);
    }

    #[test]
    fn test_pattern_analyzer_no_agent_activity() {
        let analyzer = PatternAnalyzer::new();
        let now = Utc::now();

        let entries = vec![LogEntry {
            timestamp: now,
            entry_type: EntryType::Info,
            message: "No agents here".to_string(),
            agent_name: None,
            duration_ms: None,
        }];

        let session = LogSession {
            id: "no-agent-session".to_string(),
            entries,
            start_time: now,
            end_time: Some(now + Duration::seconds(10)),
        };

        let result = analyzer.analyze(&session);
        assert!(result.is_ok());

        let analysis = result.unwrap();
        let has_no_agent = analysis
            .patterns
            .iter()
            .any(|p| matches!(p, LogPattern::NoAgentActivity));

        assert!(has_no_agent);
    }

    #[test]
    fn test_analyzer_trait_polymorphism() {
        // Demonstrates trait usage
        let timing: Box<dyn Analyzer<Output = TimingStats>> = Box::new(TimingAnalyzer::new());
        let session = create_test_session();

        let result = timing.analyze(&session);
        assert!(result.is_ok());
        assert_eq!(timing.name(), "TimingAnalyzer");
    }

    #[test]
    fn test_zero_entries_session() {
        let analyzer = TimingAnalyzer::new();
        let session = LogSession {
            id: "empty".to_string(),
            entries: vec![],
            start_time: Utc::now(),
            end_time: None,
        };

        let result = analyzer.analyze(&session);
        assert!(result.is_ok());

        let stats = result.unwrap();
        assert_eq!(stats.entry_count, 0);
        assert_eq!(stats.total_duration_secs, 0.0);
    }

    #[test]
    fn test_single_entry_session() {
        let analyzer = TimingAnalyzer::new();
        let now = Utc::now();

        let session = LogSession {
            id: "single".to_string(),
            entries: vec![LogEntry {
                timestamp: now,
                entry_type: EntryType::Info,
                message: "Only one".to_string(),
                agent_name: None,
                duration_ms: None,
            }],
            start_time: now,
            end_time: None,
        };

        let result = analyzer.analyze(&session);
        assert!(result.is_ok());

        let stats = result.unwrap();
        assert_eq!(stats.entry_count, 1);
        assert_eq!(stats.avg_time_between_entries, 0.0);
    }
}
