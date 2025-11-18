# Telemetry & Monitoring

## OpenTelemetry Integration

Microsoft Agent Framework has built-in OpenTelemetry support for distributed tracing, metrics, and logging.

### Basic Setup

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from agents_framework import Agent, ModelClient

# Configure tracing
provider = TracerProvider()
processor = BatchSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# Create agent (automatically instrumented)
agent = Agent(model=ModelClient(model="gpt-4"))

# Agent operations are automatically traced
response = await agent.run(message="Hello")
```

### Exporting to Backend

```python
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Export to Jaeger, Zipkin, or other OTLP-compatible backend
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
processor = BatchSpanProcessor(otlp_exporter)
provider.add_span_processor(processor)
```

### Custom Spans

```python
tracer = trace.get_tracer(__name__)

async def process_workflow():
    with tracer.start_as_current_span("workflow-execution") as span:
        span.set_attribute("workflow.name", "research-pipeline")

        with tracer.start_as_current_span("research-phase"):
            result = await research_agent.run(message="Research AI")

        with tracer.start_as_current_span("writing-phase"):
            result = await writer_agent.run(message=f"Summarize: {result.content}")

        return result
```

### Automatic Instrumentation

The framework automatically traces:

- Agent initialization
- Message processing
- Tool calls
- Workflow execution
- Model API calls

```python
# All operations automatically create spans
response = await agent.run(message="What's 2+2?")

# Trace includes:
# - agent.run span
# - model.generate span
# - tool.calculate span (if tool used)
# - context.load span
```

## Metrics Collection

### Built-in Metrics

```python
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter

# Setup metrics
reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
provider = MeterProvider(metric_readers=[reader])
metrics.set_meter_provider(provider)

# Framework automatically collects:
# - agent.requests.count
# - agent.requests.duration
# - agent.tokens.prompt
# - agent.tokens.completion
# - agent.errors.count
# - tool.calls.count
# - tool.calls.duration
```

### Custom Metrics

```python
meter = metrics.get_meter(__name__)

request_counter = meter.create_counter(
    "custom_agent_requests",
    description="Custom request counter"
)

latency_histogram = meter.create_histogram(
    "custom_agent_latency",
    description="Request latency",
    unit="ms"
)

# Use in code
request_counter.add(1, {"agent": "researcher"})
latency_histogram.record(123.45, {"agent": "researcher"})
```

## Logging

### Structured Logging

```python
import logging
from agents_framework import configure_logging

# Configure framework logging
configure_logging(
    level=logging.INFO,
    format="json",  # or "console"
    output="file",  # or "stdout"
    file_path="./logs/agent.log"
)

# Framework logs include:
# - Agent lifecycle events
# - Tool invocations
# - Error traces
# - Performance metrics

agent = Agent(model=model)
response = await agent.run(message="Hello")
# Automatically logs: agent creation, message processing, model calls
```

### Custom Logging

```python
import logging

logger = logging.getLogger(__name__)

async def custom_workflow():
    logger.info("Starting workflow", extra={
        "workflow_id": "abc123",
        "user_id": "user456"
    })

    try:
        result = await agent.run(message="Process")
        logger.info("Workflow completed", extra={
            "workflow_id": "abc123",
            "tokens_used": result.usage.total_tokens
        })
    except Exception as e:
        logger.error("Workflow failed", extra={
            "workflow_id": "abc123",
            "error": str(e)
        }, exc_info=True)
```

## Performance Monitoring

### Token Usage Tracking

```python
class TokenTracker:
    def __init__(self):
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    async def run_with_tracking(self, agent, message):
        response = await agent.run(message=message)

        self.total_prompt_tokens += response.usage.prompt_tokens
        self.total_completion_tokens += response.usage.completion_tokens

        return response

    def get_costs(self, price_per_1k_prompt=0.01, price_per_1k_completion=0.03):
        prompt_cost = (self.total_prompt_tokens / 1000) * price_per_1k_prompt
        completion_cost = (self.total_completion_tokens / 1000) * price_per_1k_completion
        return prompt_cost + completion_cost

tracker = TokenTracker()
response = await tracker.run_with_tracking(agent, "Hello")
print(f"Total cost: ${tracker.get_costs():.4f}")
```

### Latency Monitoring

```python
import time

class LatencyMonitor:
    async def monitor(self, agent, message):
        start = time.time()

        try:
            response = await agent.run(message=message)
            duration = time.time() - start

            print(f"Request completed in {duration:.2f}s")
            print(f"Tokens: {response.usage.total_tokens}")
            print(f"Tokens/sec: {response.usage.total_tokens / duration:.2f}")

            return response
        except Exception as e:
            duration = time.time() - start
            print(f"Request failed after {duration:.2f}s: {e}")
            raise
```

### Tool Performance Tracking

```python
from agents_framework import function_tool
from functools import wraps
import time

def track_tool_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start
            print(f"Tool {func.__name__} completed in {duration:.2f}s")
            return result
        except Exception as e:
            duration = time.time() - start
            print(f"Tool {func.__name__} failed after {duration:.2f}s: {e}")
            raise
    return wrapper

@function_tool
@track_tool_performance
async def expensive_operation(param: str) -> str:
    """Long-running tool."""
    await asyncio.sleep(2)
    return "Result"
```

## Error Tracking

### Exception Monitoring

```python
from agents_framework import ErrorHandler

class SentryErrorHandler(ErrorHandler):
    def __init__(self, sentry_dsn: str):
        import sentry_sdk
        sentry_sdk.init(dsn=sentry_dsn)

    async def handle_error(self, error: Exception, context: dict):
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            scope.set_context("agent", context)
            sentry_sdk.capture_exception(error)

        # Return fallback response
        return "I encountered an error. Please try again."

agent = Agent(
    model=model,
    error_handler=SentryErrorHandler(sentry_dsn="https://...")
)
```

### Error Rate Monitoring

```python
class ErrorRateMonitor:
    def __init__(self):
        self.total_requests = 0
        self.failed_requests = 0

    async def run_with_monitoring(self, agent, message):
        self.total_requests += 1

        try:
            response = await agent.run(message=message)
            return response
        except Exception as e:
            self.failed_requests += 1
            raise

    def get_error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    def alert_if_high_error_rate(self, threshold: float = 0.1):
        rate = self.get_error_rate()
        if rate > threshold:
            print(f"ALERT: Error rate {rate:.1%} exceeds threshold {threshold:.1%}")
```

## Debugging Tools

### Request/Response Logging

```python
class DebugMiddleware:
    async def process_request(self, message: dict, context: dict):
        print("=" * 60)
        print("REQUEST:")
        print(f"Content: {message['content']}")
        print(f"Context: {context}")
        return message, context

    async def process_response(self, response: dict, context: dict):
        print("RESPONSE:")
        print(f"Content: {response['content']}")
        print(f"Model: {response.get('model')}")
        print(f"Tokens: {response.get('usage')}")
        print(f"Tool calls: {response.get('tool_calls')}")
        print("=" * 60)
        return response

agent = Agent(model=model, middleware=[DebugMiddleware()])
```

### Time-Travel Debugging (Workflows)

```python
result = await workflow.run(initial_state={"task": "debug me"})

# Inspect each step
for i, step in enumerate(result.history):
    print(f"\n--- Step {i}: {step.node_name} ---")
    print(f"Input: {step.input_state}")
    print(f"Output: {step.output_state}")
    print(f"Duration: {step.duration}s")

    if step.error:
        print(f"ERROR: {step.error}")
```

### DevUI Integration

```python
from agents_framework.devui import start_devui

# Start development UI
start_devui(port=8000)

# Access at http://localhost:8000
# - View agent conversations
# - Inspect tool calls
# - Debug workflows visually
# - Monitor performance
```

## Production Monitoring Stack

```python
# Complete production setup
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
import logging

# Tracing
trace_provider = TracerProvider()
trace_provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://jaeger:4317"))
)
trace.set_tracer_provider(trace_provider)

# Metrics
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint="http://prometheus:4317")
)
metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader]))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent.log'),
        logging.StreamHandler()
    ]
)

# Create agent with full observability
agent = Agent(model=model)

# All operations now fully instrumented
response = await agent.run(message="Hello")
```

## Best Practices

1. **Use structured logging**: Include context (user_id, session_id, etc.)
2. **Sample traces in production**: Use sampling to reduce overhead
3. **Set up alerts**: Monitor error rates, latency, and token usage
4. **Track costs**: Monitor token consumption per user/session
5. **Correlate logs**: Use trace IDs to connect logs across services
6. **Dashboard everything**: Visualize metrics in Grafana or similar
7. **Test monitoring**: Ensure telemetry works before production
