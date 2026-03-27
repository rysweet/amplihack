"""API test scenario generator.

Generates gadugi-agentic-test YAML scenarios for APIs
based on OpenAPI/Swagger specification files.
"""

import json
from pathlib import Path

from .models import APIConfig, APIEndpointSpec, GeneratedTest, TestCategory
from .template_manager import TemplateManager
from .utils import ensure_directory, write_file


def generate_api_tests(
    config: APIConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate all API test scenarios.

    Args:
        config: API configuration from OpenAPI spec
        template_mgr: Template manager
        output_dir: Output directory for generated test files

    Returns:
        List of GeneratedTest objects
    """
    generated = []
    generated.extend(_generate_api_smoke_tests(config, template_mgr, output_dir))
    generated.extend(_generate_api_crud_tests(config, template_mgr, output_dir))
    generated.extend(_generate_api_validation_tests(config, template_mgr, output_dir))
    generated.extend(_generate_api_auth_tests(config, template_mgr, output_dir))
    generated.extend(_generate_api_workflow_tests(config, template_mgr, output_dir))
    return generated


def _generate_api_smoke_tests(
    config: APIConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate API smoke tests for each endpoint."""
    tests_dir = output_dir / "api-smoke"
    ensure_directory(tests_dir)

    generated = []
    for endpoint in config.endpoints:
        path_slug = endpoint.path.replace("/", "-").strip("-") or "root"
        tag = endpoint.tags[0] if endpoint.tags else "general"

        # Build request body if POST/PUT/PATCH
        request_body = ""
        if endpoint.method in ("POST", "PUT", "PATCH") and endpoint.request_body_schema:
            sample = _generate_sample_data(endpoint.request_body_schema)
            request_body = f"      body: {json.dumps(sample, indent=8)}"
        elif endpoint.method in ("POST", "PUT", "PATCH"):
            request_body = '      body: {}'

        # Build auth header
        auth_header = ""
        if endpoint.requires_auth or config.auth_type != "none":
            if config.auth_type == "bearer":
                auth_header = '      headers:\n        Authorization: "Bearer <test-token>"'
            elif config.auth_type == "api_key":
                auth_header = '      headers:\n        X-API-Key: "<test-api-key>"'

        # Expected status
        expected_status = 200
        if endpoint.method == "POST":
            expected_status = 201

        # Validation steps
        validation_steps = ""
        if endpoint.method == "GET" and not endpoint.requires_auth:
            validation_steps = f"""    - action: http_request
      method: "{endpoint.method}"
      url: "{config.base_url}{endpoint.path}/nonexistent-id-xyz"
      description: "Request non-existent resource"
      timeout: 10s

    - action: verify_status_code
      expected: 404
      description: "Should return 404 for missing resource"
"""

        context = {
            "method": endpoint.method,
            "path": endpoint.path,
            "summary": endpoint.summary or f"{endpoint.method} {endpoint.path}",
            "method_lower": endpoint.method.lower(),
            "tag": tag,
            "base_url": config.base_url,
            "request_body": request_body,
            "auth_header": auth_header,
            "expected_status": expected_status,
            "response_pattern": ".*",
            "path_slug": path_slug,
            "validation_steps": validation_steps,
        }

        content = template_mgr.render("api_endpoint", context)
        test_file = tests_dir / f"{endpoint.method.lower()}-{path_slug}.yaml"
        write_file(test_file, content)

        generated.append(
            GeneratedTest(
                category=TestCategory.API_SMOKE,
                file_path=test_file,
                test_count=2 + (1 if validation_steps else 0),
                description=f"API smoke test: {endpoint.method} {endpoint.path}",
            )
        )

    return generated


def _generate_api_crud_tests(
    config: APIConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate CRUD workflow tests by grouping endpoints by resource."""
    tests_dir = output_dir / "api-crud"
    ensure_directory(tests_dir)

    generated = []

    # Group endpoints by resource path (first path segment after base)
    resources: dict[str, list[APIEndpointSpec]] = {}
    for ep in config.endpoints:
        parts = ep.path.strip("/").split("/")
        resource = parts[0] if parts else "root"
        resources.setdefault(resource, []).append(ep)

    for resource, endpoints in resources.items():
        methods = {ep.method for ep in endpoints}
        if len(methods) < 2:
            continue  # Skip resources with only one method

        # Build CRUD workflow steps
        steps = []
        step_num = 1

        # POST (Create)
        post_eps = [ep for ep in endpoints if ep.method == "POST"]
        if post_eps:
            ep = post_eps[0]
            sample = _generate_sample_data(ep.request_body_schema) if ep.request_body_schema else {"name": "test"}
            steps.append(f"""    - action: http_request
      method: "POST"
      url: "{config.base_url}{ep.path}"
      body: {json.dumps(sample)}
      description: "Step {step_num}: Create {resource}"
      timeout: 10s

    - action: verify_status_code
      expected: 201
      description: "Create should return 201"
""")
            step_num += 1

        # GET (Read)
        get_eps = [ep for ep in endpoints if ep.method == "GET"]
        if get_eps:
            ep = get_eps[0]
            steps.append(f"""    - action: http_request
      method: "GET"
      url: "{config.base_url}{ep.path}"
      description: "Step {step_num}: Read {resource}"
      timeout: 10s

    - action: verify_status_code
      expected: 200
      description: "Read should return 200"
""")
            step_num += 1

        # DELETE
        delete_eps = [ep for ep in endpoints if ep.method == "DELETE"]
        if delete_eps:
            ep = delete_eps[0]
            steps.append(f"""    - action: http_request
      method: "DELETE"
      url: "{config.base_url}{ep.path}"
      description: "Step {step_num}: Delete {resource}"
      timeout: 10s

    - action: verify_status_code
      expected: 200
      description: "Delete should succeed"
""")

        if steps:
            context = {
                "workflow_name": f"{resource.title()} CRUD",
                "base_url": config.base_url,
                "workflow_slug": resource,
                "workflow_steps": "\n".join(steps),
            }

            content = template_mgr.render("api_workflow", context)
            test_file = tests_dir / f"{resource}-crud.yaml"
            write_file(test_file, content)

            generated.append(
                GeneratedTest(
                    category=TestCategory.API_CRUD,
                    file_path=test_file,
                    test_count=len(steps),
                    description=f"API CRUD tests for {resource}",
                )
            )

    return generated


def _generate_api_validation_tests(
    config: APIConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate API input validation test scenarios."""
    tests_dir = output_dir / "api-validation"
    ensure_directory(tests_dir)

    generated = []
    # Find endpoints that accept request bodies
    body_endpoints = [
        ep for ep in config.endpoints if ep.method in ("POST", "PUT", "PATCH")
    ]

    for ep in body_endpoints:
        path_slug = ep.path.replace("/", "-").strip("-") or "root"

        content = f"""# API Validation Test - {ep.method} {ep.path}
# Auto-generated outside-in test scenario

scenario:
  name: "API Validation - {ep.method} {ep.path}"
  description: |
    Verifies that {ep.method} {ep.path} properly validates input
    and returns appropriate error responses for invalid data.
  type: api
  level: 2
  tags: [api, validation, {ep.method.lower()}, auto-generated]

  prerequisites:
    - "API server is running at {config.base_url}"

  steps:
    - action: http_request
      method: "{ep.method}"
      url: "{config.base_url}{ep.path}"
      body: {{}}
      description: "Send empty body"
      timeout: 10s

    - action: verify_status_code
      expected: 400
      description: "Should reject empty body with 400"

    - action: http_request
      method: "{ep.method}"
      url: "{config.base_url}{ep.path}"
      body: {{"invalid_field": "random_value"}}
      description: "Send body with unknown fields"
      timeout: 10s

    - action: verify_status_code
      expected: 400
      description: "Should reject unknown fields"

    - action: http_request
      method: "{ep.method}"
      url: "{config.base_url}{ep.path}"
      headers:
        Content-Type: "text/plain"
      body: "not json"
      description: "Send non-JSON body"
      timeout: 10s

    - action: verify_status_code
      expected: 415
      description: "Should reject non-JSON content type"

  cleanup:
    - action: log_response
      save_as: "validation-{ep.method.lower()}-{path_slug}.json"
"""
        test_file = tests_dir / f"validate-{ep.method.lower()}-{path_slug}.yaml"
        write_file(test_file, content)

        generated.append(
            GeneratedTest(
                category=TestCategory.API_VALIDATION,
                file_path=test_file,
                test_count=3,
                description=f"API validation test: {ep.method} {ep.path}",
            )
        )

    return generated


def _generate_api_auth_tests(
    config: APIConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate API authentication test scenarios."""
    if config.auth_type == "none":
        return []

    tests_dir = output_dir / "api-auth"
    ensure_directory(tests_dir)

    # Find protected endpoints
    protected = [ep for ep in config.endpoints if ep.requires_auth]
    if not protected:
        protected = config.endpoints

    steps = ""
    for ep in protected:
        steps += f"""    - action: http_request
      method: "{ep.method}"
      url: "{config.base_url}{ep.path}"
      description: "Request {ep.method} {ep.path} without auth"
      timeout: 10s

    - action: verify_status_code
      expected: 401
      description: "Should return 401 without authentication"

"""

    content = f"""# API Authentication Test
# Auto-generated outside-in test scenario

scenario:
  name: "API Auth - Unauthenticated Access"
  description: |
    Verifies that protected endpoints return 401 when accessed
    without authentication credentials.
  type: api
  level: 2
  tags: [api, auth, security, auto-generated]

  prerequisites:
    - "API server is running at {config.base_url}"

  steps:
{steps}
  cleanup:
    - action: log_response
      save_as: "auth-test-results.json"
"""
    test_file = tests_dir / "auth-unauthenticated.yaml"
    write_file(test_file, content)

    return [
        GeneratedTest(
            category=TestCategory.API_AUTH,
            file_path=test_file,
            test_count=len(protected) * 2,
            description="API authentication tests",
        )
    ]


def _generate_api_workflow_tests(
    config: APIConfig, template_mgr: TemplateManager, output_dir: Path
) -> list[GeneratedTest]:
    """Generate API multi-step workflow test scenarios."""
    tests_dir = output_dir / "api-workflows"
    ensure_directory(tests_dir)

    generated = []

    # Group by tags and create tag-based workflows
    tag_endpoints: dict[str, list[APIEndpointSpec]] = {}
    for ep in config.endpoints:
        for tag in ep.tags or ["general"]:
            tag_endpoints.setdefault(tag, []).append(ep)

    for tag, endpoints in tag_endpoints.items():
        if len(endpoints) < 2:
            continue

        steps = ""
        for i, ep in enumerate(endpoints):
            body_line = ""
            if ep.method in ("POST", "PUT", "PATCH"):
                sample = _generate_sample_data(ep.request_body_schema) if ep.request_body_schema else {}
                body_line = f"\n      body: {json.dumps(sample)}"

            expected = 201 if ep.method == "POST" else 200
            steps += f"""    - action: http_request
      method: "{ep.method}"
      url: "{config.base_url}{ep.path}"{body_line}
      description: "Step {i+1}: {ep.summary or ep.method + ' ' + ep.path}"
      timeout: 10s

    - action: verify_status_code
      expected: {expected}
      description: "Step {i+1} should succeed"

"""

        context = {
            "workflow_name": f"{tag.title()} Workflow",
            "base_url": config.base_url,
            "workflow_slug": tag.lower().replace(" ", "-"),
            "workflow_steps": steps,
        }

        content = template_mgr.render("api_workflow", context)
        test_file = tests_dir / f"workflow-{tag.lower().replace(' ', '-')}.yaml"
        write_file(test_file, content)

        generated.append(
            GeneratedTest(
                category=TestCategory.API_WORKFLOW,
                file_path=test_file,
                test_count=min(len(endpoints), 4) * 2,
                description=f"API workflow test for {tag}",
            )
        )

    return generated


def _generate_sample_data(schema: dict | None) -> dict:
    """Generate sample request data from a JSON schema."""
    if not schema or not isinstance(schema, dict):
        return {}

    sample: dict = {}
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return sample

    for prop_name, prop_def in properties.items():
        if not isinstance(prop_def, dict):
            continue
        prop_type = prop_def.get("type", "string")
        if prop_type == "string":
            if "email" in prop_name.lower():
                sample[prop_name] = "test@example.com"
            elif "name" in prop_name.lower():
                sample[prop_name] = "Test Name"
            elif "url" in prop_name.lower():
                sample[prop_name] = "https://example.com"
            elif "date" in prop_name.lower():
                sample[prop_name] = "2024-01-01"
            else:
                sample[prop_name] = f"test-{prop_name}"
        elif prop_type == "integer":
            sample[prop_name] = 1
        elif prop_type == "number":
            sample[prop_name] = 1.0
        elif prop_type == "boolean":
            sample[prop_name] = True
        elif prop_type == "array":
            sample[prop_name] = []
        elif prop_type == "object":
            sample[prop_name] = {}

    return sample
