"""Session error handling improvements - Batch 230"""

def handle_session_error(error_type, context):
    """Enhanced error handling for session operations.

    Args:
        error_type: Type of error encountered
        context: Error context information

    Returns:
        Appropriate error response with recovery suggestions
    """
    error_handlers = {
        'timeout': lambda ctx: f"Session timeout: {ctx}. Retry with increased timeout.",
        'connection': lambda ctx: f"Connection failed: {ctx}. Check network settings.",
        'auth': lambda ctx: f"Authentication error: {ctx}. Verify credentials.",
        'permission': lambda ctx: f"Permission denied: {ctx}. Check file permissions.",
        'resource': lambda ctx: f"Resource unavailable: {ctx}. Free up system resources.",
    }

    handler = error_handlers.get(error_type, lambda ctx: f"Unknown error: {ctx}")
    return handler(context)
