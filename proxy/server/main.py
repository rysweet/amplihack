import uvicorn

from .fastapi import app


def main():
    """Entry point for the application script"""
    import os
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Run with: uvicorn server:app --reload --host 127.0.0.1 --port 8082")
        sys.exit(0)

    # Read PORT from environment variable, default to 8082
    # Default to localhost (127.0.0.1) for security - no public binding
    port = int(os.environ.get("PORT", 8082))
    host = os.environ.get("HOST", "127.0.0.1")

    print(f"Starting claude-code-proxy on http://{host}:{port}")

    # Configure uvicorn to run with minimal logs
    uvicorn.run(app, host=host, port=port, log_level="error")
