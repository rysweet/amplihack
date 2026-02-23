"""Stack detection for frontend, backend, and database.

Analyzes project structure to detect application stack.
Follows language_detector pattern from amplihack.
"""

import asyncio
from pathlib import Path
from typing import Any

from .models import (
    APIEndpoint,
    Route,
    StackConfig,
    StackDetectionError,
)
from .security import validate_project_root
from .utils import (
    find_files,
    get_framework_from_dependencies,
    parse_package_json,
    parse_route_from_file,
    read_file,
)

# Framework detection markers
FRONTEND_MARKERS = {
    "nextjs": ["next.config.js", "next.config.ts", "next.config.mjs"],
    "react": ["react", "react-dom"],  # in package.json dependencies
    "vue": ["vue", "nuxt"],  # in package.json dependencies
    "angular": ["angular.json", "@angular/core"],
    "svelte": ["svelte.config.js", "svelte"],
}

BACKEND_MARKERS = {
    "fastapi": ["from fastapi import", "import fastapi", "FastAPI("],
    "express": ["express()", "require('express')", "import express"],
    "django": ["django.conf", "from django", "INSTALLED_APPS"],
    "flask": ["from flask import", "import flask", "Flask(__name__)"],
    "nestjs": ["@nestjs/core", "@Module(", "@Controller("],
}

DATABASE_MARKERS = {
    "postgresql": ["psycopg2", "pg", "postgresql://", "postgres://"],
    "mysql": ["mysql", "pymysql", "mysql://", "mysql2"],
    "mongodb": ["mongodb", "mongoose", "mongodb://", "MongoClient"],
    "sqlite": ["sqlite3", "sqlite://", "better-sqlite3"],
}


async def detect_stack(project_root: Path) -> StackConfig:
    """Detect application stack configuration.

    Runs frontend, backend, and database analysis in parallel.

    Args:
        project_root: Path to project root

    Returns:
        StackConfig with detected stack information

    Raises:
        StackDetectionError: If detection fails
    """
    # Validate project root is within allowed boundaries
    try:
        project_root = validate_project_root(project_root)
    except Exception as e:
        raise StackDetectionError(f"Invalid project root: {e}")

    if not project_root.exists():
        raise StackDetectionError(f"Project root does not exist: {project_root}")

    # Run analysis in parallel for speed
    frontend_task = analyze_frontend(project_root)
    backend_task = analyze_backend(project_root)
    database_task = analyze_database(project_root)

    try:
        frontend, backend, database = await asyncio.gather(
            frontend_task, backend_task, database_task
        )
    except Exception as e:
        raise StackDetectionError(f"Stack detection failed: {e}")

    # Combine results into merged StackConfig
    return StackConfig(
        # Frontend
        frontend_framework=frontend["framework"],
        frontend_dir=project_root,
        routes=frontend["routes"],
        components=frontend.get("components", []),
        # Backend
        backend_framework=backend["framework"],
        backend_dir=project_root,
        api_base_url=backend["api_base_url"],
        api_endpoints=backend["endpoints"],
        # Database
        database_type=database["type"],
        schema_files=database.get("schema_files", []),
        models=backend.get("models", []) or database.get("models", []),
        # Authentication
        auth_mechanism=frontend.get("auth_mechanism", "none")
        or backend.get("auth_mechanism", "none"),
    )


async def analyze_frontend(project_root: Path) -> dict:
    """Analyze frontend framework and routes.

    Args:
        project_root: Path to project root

    Returns:
        Dict with detected framework and routes

    Raises:
        FrontendAnalysisError: If analysis fails
    """
    # Check for package.json
    package_data = parse_package_json(project_root)
    if not package_data:
        return {
            "framework": "unknown",
            "routes": [],
            "components": [],
            "auth_mechanism": "none",
        }

    # Detect framework from dependencies
    all_deps = {
        **package_data.get("dependencies", {}),
        **package_data.get("devDependencies", {}),
    }

    framework = get_framework_from_dependencies(all_deps)
    if not framework:
        # Check for config files
        for fw, markers in FRONTEND_MARKERS.items():
            for marker in markers:
                if (project_root / marker).exists():
                    framework = fw
                    break
            if framework:
                break

    if not framework:
        framework = "unknown"

    # Detect routes based on framework
    routes = await _detect_routes(project_root, framework)

    # Detect auth mechanism
    auth_mechanism = _detect_auth_mechanism(all_deps)

    return {
        "framework": framework,
        "routes": routes,
        "components": [],  # Component discovery is optional
        "auth_mechanism": auth_mechanism,
    }


async def analyze_backend(project_root: Path) -> dict:
    """Analyze backend API endpoints and structure.

    Args:
        project_root: Path to project root

    Returns:
        Dict with detected framework and endpoints

    Raises:
        BackendAnalysisError: If analysis fails
    """
    framework = "unknown"
    api_base_url = "http://localhost:3000"  # Default

    # Check for common backend entry points
    backend_files = []
    for pattern in [
        "main.py",
        "app.py",
        "server.ts",
        "server.js",
        "app.ts",
        "app.js",
        "index.ts",
        "index.js",
    ]:
        backend_files.extend(find_files(project_root, pattern))

    # Detect framework from file contents
    for file_path in backend_files:
        try:
            content = read_file(file_path)
            for fw, markers in BACKEND_MARKERS.items():
                if any(marker in content for marker in markers):
                    framework = fw
                    break
            if framework != "unknown":
                break
        except Exception:
            continue

    # Detect API endpoints (basic heuristic)
    endpoints = await _detect_api_endpoints(project_root, framework)

    # Detect auth mechanism
    auth_mechanism = _detect_backend_auth(project_root)

    return {
        "framework": framework,
        "api_base_url": api_base_url,
        "endpoints": endpoints,
        "models": [],  # Model discovery from code is complex
        "auth_mechanism": auth_mechanism,
    }


async def analyze_database(project_root: Path) -> dict:
    """Analyze database schema and models.

    Args:
        project_root: Path to project root

    Returns:
        Dict with detected database type

    Raises:
        DatabaseAnalysisError: If analysis fails
    """
    db_type = "unknown"

    # Check package.json dependencies
    package_data = parse_package_json(project_root)
    if package_data:
        all_deps = {
            **package_data.get("dependencies", {}),
            **package_data.get("devDependencies", {}),
        }

        for db, markers in DATABASE_MARKERS.items():
            if any(marker in all_deps for marker in markers):
                db_type = db
                break

    # Check for database config files
    if db_type == "unknown":
        db_config_files = ["prisma/schema.prisma", "drizzle.config.ts", "ormconfig.json"]
        for config in db_config_files:
            if (project_root / config).exists():
                content = read_file(project_root / config)
                for db, markers in DATABASE_MARKERS.items():
                    if any(marker in content for marker in markers):
                        db_type = db
                        break
                if db_type != "unknown":
                    break

    # Find schema files
    schema_files = []
    for pattern in ["schema.prisma", "*.sql", "migrations/*.sql"]:
        schema_files.extend(find_files(project_root, pattern))

    return {
        "type": db_type,
        "schema_files": schema_files[:5],  # Limit to first 5
        "models": [],  # Model extraction from schema is complex
    }


async def _detect_routes(project_root: Path, framework: str) -> list[Route]:
    """Detect frontend routes based on framework conventions.

    Args:
        project_root: Project root
        framework: Detected framework

    Returns:
        List of detected routes
    """
    routes = []

    if framework == "nextjs":
        # Check app router
        app_dir = project_root / "app"
        if app_dir.exists():
            page_files = find_files(app_dir, "**/page.tsx") + find_files(app_dir, "**/page.jsx")
            for page_file in page_files:
                route_path = parse_route_from_file(page_file, framework)
                if route_path:
                    routes.append(
                        Route(
                            path=route_path,
                            component=str(page_file.relative_to(project_root)),
                            requires_auth=_requires_auth(read_file(page_file)),
                        )
                    )

        # Check pages router
        pages_dir = project_root / "pages"
        if pages_dir.exists():
            page_files = find_files(pages_dir, "*.tsx") + find_files(pages_dir, "*.jsx")
            for page_file in page_files:
                if page_file.name.startswith("_"):  # Skip _app, _document
                    continue
                route_path = parse_route_from_file(page_file, framework)
                if route_path:
                    routes.append(
                        Route(
                            path=route_path,
                            component=str(page_file.relative_to(project_root)),
                            requires_auth=_requires_auth(read_file(page_file)),
                        )
                    )

    elif framework in ["react", "vue"]:
        # Look for routes/pages directories
        for dir_name in ["routes", "pages", "views"]:
            routes_dir = project_root / "src" / dir_name
            if routes_dir.exists():
                route_files = (
                    find_files(routes_dir, "*.tsx")
                    + find_files(routes_dir, "*.jsx")
                    + find_files(routes_dir, "*.vue")
                )
                for route_file in route_files:
                    routes.append(
                        Route(
                            path=f"/{route_file.stem.lower()}",
                            component=str(route_file.relative_to(project_root)),
                            requires_auth=_requires_auth(read_file(route_file)),
                        )
                    )

    # Deduplicate routes
    seen_paths = set()
    unique_routes = []
    for route in routes:
        if route.path not in seen_paths:
            seen_paths.add(route.path)
            unique_routes.append(route)

    return unique_routes


async def _detect_api_endpoints(project_root: Path, framework: str) -> list[APIEndpoint]:
    """Detect API endpoints based on backend framework.

    Args:
        project_root: Project root
        framework: Detected framework

    Returns:
        List of detected API endpoints
    """
    endpoints = []

    if framework == "fastapi":
        # Look for FastAPI route decorators
        api_files = find_files(project_root, "*.py")
        for api_file in api_files[:20]:  # Limit search
            try:
                content = read_file(api_file)
                # Match @app.get("/path"), @router.post("/path"), etc.
                import re

                pattern = r'@(?:app|router)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']\)'
                matches = re.findall(pattern, content)
                for method, path in matches:
                    endpoints.append(
                        APIEndpoint(
                            path=path,
                            method=method.upper(),
                            requires_auth=_requires_auth(content),
                        )
                    )
            except Exception:
                continue

    elif framework == "express":
        # Look for Express route definitions
        api_files = find_files(project_root, "*.js") + find_files(project_root, "*.ts")
        for api_file in api_files[:20]:
            try:
                content = read_file(api_file)
                # Match app.get('/path'), router.post('/path'), etc.
                import re

                pattern = r'(?:app|router)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']\)'
                matches = re.findall(pattern, content)
                for method, path in matches:
                    endpoints.append(
                        APIEndpoint(
                            path=path,
                            method=method.upper(),
                            requires_auth=_requires_auth(content),
                        )
                    )
            except Exception:
                continue

    # Deduplicate endpoints
    seen_endpoints = set()
    unique_endpoints = []
    for endpoint in endpoints:
        key = (endpoint.method, endpoint.path)
        if key not in seen_endpoints:
            seen_endpoints.add(key)
            unique_endpoints.append(endpoint)

    return unique_endpoints


def _requires_auth(content: str) -> bool:
    """Check if content requires authentication.

    Args:
        content: File content

    Returns:
        True if authentication is required
    """
    auth_markers = [
        "requireAuth",
        "useAuth",
        "withAuth",
        "authenticated",
        "@login_required",
        "Depends(get_current_user)",
        "auth.required",
        "isAuthenticated",
    ]
    return any(marker in content for marker in auth_markers)


def _detect_auth_mechanism(dependencies: dict[str, Any]) -> str:
    """Detect authentication mechanism from dependencies.

    Args:
        dependencies: Package dependencies

    Returns:
        Auth mechanism name
    """
    if "next-auth" in dependencies or "nextauth" in dependencies:
        return "next-auth"
    if "auth0" in dependencies:
        return "auth0"
    if "firebase" in dependencies:
        return "firebase"
    if "supabase" in dependencies:
        return "supabase"
    if "clerk" in dependencies:
        return "clerk"
    return "none"


def _detect_backend_auth(project_root: Path) -> str:
    """Detect backend authentication mechanism.

    Args:
        project_root: Project root

    Returns:
        Auth mechanism name
    """
    auth_files = find_files(project_root, "*auth*.py") + find_files(project_root, "*auth*.ts")
    for auth_file in auth_files[:5]:
        try:
            content = read_file(auth_file)
            if "JWT" in content or "jwt" in content:
                return "jwt"
            if "OAuth" in content or "oauth" in content:
                return "oauth"
            if "session" in content:
                return "session"
        except Exception:
            continue
    return "none"


def detect_stack_sync(project_root: Path) -> StackConfig:
    """Synchronous wrapper for detect_stack.

    Args:
        project_root: Path to project root

    Returns:
        StackConfig with detected stack information
    """
    return asyncio.run(detect_stack(project_root))
