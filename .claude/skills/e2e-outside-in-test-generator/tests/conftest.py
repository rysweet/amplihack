"""Pytest configuration and shared fixtures for E2E test generator tests."""

from pathlib import Path

import pytest


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project structure for testing."""
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # Create package.json
    package_json = project_root / "package.json"
    package_json.write_text("""
{
  "name": "test-app",
  "dependencies": {
    "next": "14.0.0",
    "react": "18.0.0"
  }
}
    """)

    # Create Next.js app structure
    app_dir = project_root / "app"
    app_dir.mkdir()

    (app_dir / "page.tsx").write_text("""
export default function Home() {
  return <h1>Home</h1>;
}
    """)

    pages_dir = app_dir / "dashboard"
    pages_dir.mkdir()
    (pages_dir / "page.tsx").write_text("""
export default function Dashboard() {
  return <h1>Dashboard</h1>;
}
    """)

    return project_root


@pytest.fixture
def sample_stack_config():
    """Create a sample stack configuration for testing."""
    from generator.models import APIEndpoint, Field, Model, Route, StackConfig

    return StackConfig(
        frontend_framework="nextjs",
        frontend_dir=Path("/test/project"),
        backend_framework="fastapi",
        backend_dir=Path("/test/project"),
        api_base_url="http://localhost:3000",
        database_type="postgresql",
        auth_mechanism="jwt",
        routes=[
            Route(path="/", component="Home", requires_auth=False),
            Route(path="/dashboard", component="Dashboard", requires_auth=True),
            Route(path="/login", component="Login", requires_auth=False),
        ],
        api_endpoints=[
            APIEndpoint(path="/api/users", method="GET", requires_auth=True),
            APIEndpoint(path="/api/users", method="POST", requires_auth=False),
        ],
        models=[
            Model(
                name="User",
                fields=[
                    Field(name="id", type="int", required=True),
                    Field(name="email", type="str", required=True),
                    Field(name="name", type="str", required=True),
                ],
            )
        ],
    )
