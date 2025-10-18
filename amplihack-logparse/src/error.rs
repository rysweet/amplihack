// Error handling module
//
// Demonstrates Rust's error handling with Result and custom error types

use std::path::PathBuf;
use thiserror::Error;

/// Custom error type for log parsing
///
/// This demonstrates:
/// - Using thiserror for ergonomic error definitions
/// - Error composition with #[from]
/// - Enum variants for different error cases
#[derive(Error, Debug)]
pub enum ParseError {
    /// File not found at the specified path
    #[error("File not found: {0}")]
    FileNotFound(PathBuf),
    
    /// Invalid timestamp format in log entry
    #[error("Invalid timestamp format: {0}")]
    InvalidTimestamp(String),
    
    /// Malformed log entry
    #[error("Malformed log entry at line {line}: {details}")]
    MalformedEntry {
        line: usize,
        details: String,
    },
    
    /// IO error (automatically converted from std::io::Error)
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    
    /// JSON serialization/deserialization error
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    
    /// Unknown error
    #[error("Unknown error: {0}")]
    Unknown(String),
}

/// Result type alias for parse operations
///
/// This demonstrates:
/// - Type aliases for cleaner APIs
/// - Generic Result with our custom error type
pub type ParseResult<T> = Result<T, ParseError>;

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_error_display() {
        let err = ParseError::InvalidTimestamp("bad timestamp".to_string());
        assert_eq!(err.to_string(), "Invalid timestamp format: bad timestamp");
    }
    
    #[test]
    fn test_error_from_io() {
        // Demonstrates automatic conversion with #[from]
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "test");
        let parse_err: ParseError = io_err.into();
        
        match parse_err {
            ParseError::Io(_) => (),  // Expected
            _ => panic!("Wrong error type"),
        }
    }
}
