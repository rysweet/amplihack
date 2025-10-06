import uvicorn

from .fastapi import app


def main():
    """Entry point for the application script"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Run with: uvicorn server:app --reload --host 0.0.0.0 --port 8082")
        sys.exit(0)

    print("Starting claude-code-proxy on http://localhost:8082")

    # Configure uvicorn to run with minimal logs
    uvicorn.run(app, host="0.0.0.0", port=8082, log_level="error")
