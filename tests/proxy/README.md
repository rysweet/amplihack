# Azure OpenAI Proxy Test Suite

This directory contains comprehensive failing tests for Azure OpenAI proxy integration, following Test-Driven Development (TDD) principles to guide implementation.

## Test Structure

### 1. Configuration Tests (`test_azure_config.py`)

- **Azure vs OpenAI endpoint detection**
  - Detection from `AZURE_OPENAI_BASE_URL`
  - Detection from endpoint URL patterns (`azure.com`, `cognitive.microsoft.com`)
  - Default fallback to OpenAI for ambiguous configurations
  - Explicit Azure configuration variables

- **Azure-specific validation**
  - Required fields validation (endpoint, API key)
  - Azure endpoint URL format validation
  - API version format validation
  - Deployment name configuration validation

- **Backward compatibility**
  - Existing OpenAI configurations continue working
  - Mixed configuration handling with explicit type preference
  - Legacy configuration pattern support

- **Error handling**
  - Missing configuration file graceful handling
  - Invalid Azure URL error messages
  - Empty API key detection
  - Malformed configuration file parsing

- **Environment variable integration**
  - Environment variables override file configuration
  - Mixed file and environment variable handling

### 2. Integration Tests (`test_azure_integration.py`)

- **ProxyManager initialization**
  - Azure configuration detection and setup
  - Mixed Azure/OpenAI configuration handling
  - Deployment mapping configuration

- **Azure proxy startup**
  - Correct environment variable passing to proxy process
  - Azure deployment configuration passing
  - Configuration validation before startup
  - Azure-specific dependency installation

- **Request handling and transformation**
  - OpenAI-format request transformation to Azure format
  - Azure URL construction with deployment names
  - Azure response normalization to OpenAI format

- **Health checks and monitoring**
  - Azure endpoint health checking
  - Connection validation before startup
  - API key validation

- **Error handling**
  - Azure quota exceeded error transformation
  - Deployment not found error handling
  - Authentication error transformation

- **Environment integration**
  - Azure environment setup and restoration
  - Context manager support for Azure configurations

### 3. Model Mapping Tests (`test_model_mapping.py`)

- **Basic model mapping**
  - Standard OpenAI model names to Azure deployments
  - Custom model mapping patterns (BIG_MODEL, SMALL_MODEL, etc.)
  - Reasoning model mappings (o1-preview, o1-mini)
  - Fallback deployment handling
  - Model name normalization

- **Parameter conversion for reasoning models**
  - `max_tokens` → `max_completion_tokens` conversion
  - Parameter preservation for non-reasoning models
  - Reasoning model parameter restrictions (temperature, top_p, stream)
  - System message handling restrictions
  - Mixed model parameter handling

- **Advanced mapping features**
  - Dynamic deployment selection based on context
  - Model alias resolution
  - Model capability-based mapping (vision, code, reasoning)
  - Load balancing across multiple deployments

- **Error handling**
  - Missing deployment configuration
  - Invalid deployment name validation and sanitization
  - Parameter validation errors
  - Unsupported model graceful fallback

## Key Features Defined by Tests

### 1. Azure Endpoint Detection

```python
# Tests expect these methods to be implemented:
config.is_azure_endpoint() -> bool
config.get_endpoint_type() -> str  # "azure" | "openai"
config.get_azure_endpoint() -> str
config.get_azure_api_version() -> str
```

### 2. Azure Configuration Validation

```python
# Tests expect these validation methods:
config.validate_azure_config() -> bool
config.validate_azure_endpoint_format() -> bool
config.validate_azure_api_version() -> bool
config.validate_azure_deployments() -> bool
config.get_validation_errors() -> List[str]
```

### 3. ProxyManager Azure Integration

```python
# Tests expect these ProxyManager methods:
manager.is_azure_mode() -> bool
manager.get_active_config_type() -> str
manager.get_azure_deployments() -> Dict[str, str]
manager.transform_request_for_azure(request) -> dict
manager.construct_azure_url(model) -> str
manager.normalize_azure_response(response, original_model) -> dict
```

### 4. Model Mapping and Parameter Conversion

```python
# Tests expect these methods:
manager.get_azure_deployment(model) -> str | None
manager.is_reasoning_model(model) -> bool
manager.convert_parameters_for_model(request) -> dict
manager.select_optimal_deployment(request) -> str
manager.validate_deployment_name(name) -> bool
```

### 5. Health Checks and Error Handling

```python
# Tests expect these methods:
manager.check_azure_endpoint_health() -> bool
manager.validate_azure_connection() -> bool
manager.validate_azure_api_key() -> bool
manager.transform_azure_error(error) -> dict
```

## Running the Tests

```bash
# Run all Azure proxy tests
pytest tests/proxy/ -v

# Run specific test files
pytest tests/proxy/test_azure_config.py -v
pytest tests/proxy/test_azure_integration.py -v
pytest tests/proxy/test_model_mapping.py -v

# Run with coverage
pytest tests/proxy/ --cov=src/amplihack/proxy --cov-report=html
```

## Test Results Summary

- **Total Tests**: 57
- **Expected Status**: 52 failing, 5 passing (TDD approach)
- **Coverage Areas**:
  - Configuration parsing and validation
  - ProxyManager integration
  - Model mapping and parameter conversion
  - Error handling and edge cases
  - Backward compatibility

## Implementation Guidance

These tests define the exact interface and behavior expected for Azure OpenAI proxy integration. Implementation should focus on making these tests pass while maintaining the existing OpenAI proxy functionality.

### Priority Implementation Order:

1. **Azure endpoint detection** in `ProxyConfig`
2. **Basic Azure configuration validation**
3. **ProxyManager Azure mode initialization**
4. **Model mapping configuration parsing**
5. **Parameter conversion for reasoning models**
6. **Request/response transformation**
7. **Error handling and health checks**
8. **Advanced features** (load balancing, capability mapping)

The tests use comprehensive mocking to isolate units under test and provide clear expectations for the Azure OpenAI proxy integration functionality.
