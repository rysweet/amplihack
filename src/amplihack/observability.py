"""Shared OpenTelemetry helpers for amplihack runtimes and Azure evals."""

from __future__ import annotations

import contextlib
import importlib
import logging
import os
import threading
from collections.abc import Iterator, Mapping
from typing import Any

logger = logging.getLogger(__name__)

_CONFIG_LOCK = threading.Lock()
_CONFIGURED = False
_DISABLED_REASONS: set[str] = set()


def _truthy(value: str | None) -> bool:
    return bool(value and value.strip().lower() in {"1", "true", "yes", "on"})


def _log_disabled_once(reason: str) -> None:
    if reason in _DISABLED_REASONS:
        return
    _DISABLED_REASONS.add(reason)
    logger.info("OpenTelemetry disabled: %s", reason)


def _otlp_trace_endpoint() -> str:
    traces_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "").strip()
    if traces_endpoint:
        return traces_endpoint

    endpoint = (
        os.environ.get("AMPLIHACK_OTEL_OTLP_ENDPOINT", "")
        or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    ).strip()
    if not endpoint:
        return ""
    if endpoint.endswith("/v1/traces"):
        return endpoint
    return f"{endpoint.rstrip('/')}/v1/traces"


def _otlp_base_endpoint() -> str:
    return (
        os.environ.get("AMPLIHACK_OTEL_OTLP_ENDPOINT", "")
        or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    ).strip()


def _otlp_protocol() -> str:
    return (
        os.environ.get("AMPLIHACK_OTEL_OTLP_PROTOCOL", "")
        or os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL", "")
        or "http/protobuf"
    ).strip()


def _console_exporter_enabled() -> bool:
    return _truthy(os.environ.get("AMPLIHACK_OTEL_CONSOLE_EXPORTER"))


def telemetry_requested() -> bool:
    return (
        _truthy(os.environ.get("AMPLIHACK_OTEL_ENABLED"))
        or bool(_otlp_base_endpoint())
        or _console_exporter_enabled()
    )


def _parse_otlp_headers() -> dict[str, str]:
    raw = (
        os.environ.get("AMPLIHACK_OTEL_EXPORTER_HEADERS", "")
        or os.environ.get("OTEL_EXPORTER_OTLP_HEADERS", "")
    ).strip()
    if not raw:
        return {}

    headers: dict[str, str] = {}
    for part in raw.split(","):
        key, sep, value = part.partition("=")
        if not sep:
            continue
        header_key = key.strip()
        header_value = value.strip()
        if header_key and header_value:
            headers[header_key] = header_value
    return headers


def _normalize_attributes(
    attributes: Mapping[str, Any] | None,
) -> dict[str, str | bool | int | float]:
    normalized: dict[str, str | bool | int | float] = {}
    if not attributes:
        return normalized
    for key, value in attributes.items():
        if value is None:
            continue
        if isinstance(value, (bool, int, float, str)):
            if isinstance(value, str) and not value.strip():
                continue
            normalized[key] = value
            continue
        normalized[key] = str(value)
    return normalized


def otel_env_overrides(
    *,
    service_name: str = "",
    attributes: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """Return standard OTel env vars suitable for child SDK subprocesses."""
    env: dict[str, str] = {}
    for key in ("AMPLIHACK_OTEL_ENABLED", "AMPLIHACK_OTEL_CONSOLE_EXPORTER"):
        value = os.environ.get(key, "").strip()
        if value:
            env[key] = value

    endpoint = _otlp_trace_endpoint()
    base_endpoint = _otlp_base_endpoint()
    protocol = _otlp_protocol()
    if protocol:
        env["OTEL_EXPORTER_OTLP_PROTOCOL"] = protocol
    if protocol == "grpc":
        if base_endpoint:
            env["OTEL_EXPORTER_OTLP_ENDPOINT"] = base_endpoint
    else:
        if endpoint:
            env["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = endpoint
        if base_endpoint:
            env["OTEL_EXPORTER_OTLP_ENDPOINT"] = base_endpoint

    headers = (
        os.environ.get("AMPLIHACK_OTEL_EXPORTER_HEADERS", "").strip()
        or os.environ.get("OTEL_EXPORTER_OTLP_HEADERS", "").strip()
    )
    if headers:
        env["OTEL_EXPORTER_OTLP_HEADERS"] = headers

    service_namespace = (
        os.environ.get("OTEL_SERVICE_NAMESPACE", "").strip()
        or os.environ.get("AMPLIHACK_OTEL_SERVICE_NAMESPACE", "").strip()
    )
    if service_namespace:
        env["OTEL_SERVICE_NAMESPACE"] = service_namespace

    if service_name:
        env["OTEL_SERVICE_NAME"] = service_name

    existing_resource_attributes = os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "").strip()
    extra_attributes = ",".join(
        f"{key}={value}" for key, value in _normalize_attributes(attributes).items()
    )
    if existing_resource_attributes and extra_attributes:
        env["OTEL_RESOURCE_ATTRIBUTES"] = f"{existing_resource_attributes},{extra_attributes}"
    elif existing_resource_attributes:
        env["OTEL_RESOURCE_ATTRIBUTES"] = existing_resource_attributes
    elif extra_attributes:
        env["OTEL_RESOURCE_ATTRIBUTES"] = extra_attributes

    return env


def configure_otel(
    service_name: str,
    *,
    component: str = "",
    attributes: Mapping[str, Any] | None = None,
) -> bool:
    """Configure the process-wide OTel tracer provider when telemetry is enabled."""
    global _CONFIGURED

    if not telemetry_requested():
        return False

    with _CONFIG_LOCK:
        if _CONFIGURED:
            return True

        try:
            trace = importlib.import_module("opentelemetry.trace")
            resource_module = importlib.import_module("opentelemetry.sdk.resources")
            trace_sdk_module = importlib.import_module("opentelemetry.sdk.trace")
            export_module = importlib.import_module("opentelemetry.sdk.trace.export")
        except Exception as exc:  # pragma: no cover - import surface depends on env
            _log_disabled_once(f"opentelemetry SDK unavailable ({type(exc).__name__})")
            return False

        Resource = resource_module.Resource
        TracerProvider = trace_sdk_module.TracerProvider
        BatchSpanProcessor = export_module.BatchSpanProcessor
        ConsoleSpanExporter = export_module.ConsoleSpanExporter
        SimpleSpanProcessor = export_module.SimpleSpanProcessor

        current_provider = trace.get_tracer_provider()
        if current_provider.__class__.__name__ != "ProxyTracerProvider":
            _CONFIGURED = True
            return True

        resource_attrs: dict[str, Any] = {
            "service.name": os.environ.get("OTEL_SERVICE_NAME", "").strip() or service_name,
            "service.namespace": (
                os.environ.get("OTEL_SERVICE_NAMESPACE", "").strip()
                or os.environ.get("AMPLIHACK_OTEL_SERVICE_NAMESPACE", "").strip()
                or "amplihack"
            ),
        }
        if component:
            resource_attrs["amplihack.component"] = component
        resource_attrs.update(_normalize_attributes(attributes))

        provider = TracerProvider(resource=Resource.create(resource_attrs))
        exporter_configured = False

        protocol = _otlp_protocol()
        endpoint = _otlp_base_endpoint() if protocol == "grpc" else _otlp_trace_endpoint()
        if endpoint:
            try:
                module_name = (
                    "opentelemetry.exporter.otlp.proto.grpc.trace_exporter"
                    if protocol == "grpc"
                    else "opentelemetry.exporter.otlp.proto.http.trace_exporter"
                )
                otlp_module = importlib.import_module(module_name)
                OTLPSpanExporter = otlp_module.OTLPSpanExporter

                exporter_kwargs: dict[str, Any] = {"endpoint": endpoint}
                if protocol == "grpc" and endpoint.startswith("http://"):
                    exporter_kwargs["insecure"] = True
                headers = _parse_otlp_headers()
                if headers:
                    exporter_kwargs["headers"] = headers

                provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(**exporter_kwargs)))
                exporter_configured = True
            except Exception as exc:  # pragma: no cover - depends on optional exporter package
                logger.warning(
                    "Failed to configure OTLP %s span exporter for %s: %s",
                    protocol,
                    endpoint,
                    exc,
                )

        if not exporter_configured and _console_exporter_enabled():
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
            exporter_configured = True

        if not exporter_configured:
            _log_disabled_once("no OTLP endpoint or console exporter configured")
            return False

        trace.set_tracer_provider(provider)
        _CONFIGURED = True
        logger.info(
            "OpenTelemetry configured for service=%s component=%s exporter=%s",
            resource_attrs["service.name"],
            component or "unspecified",
            f"otlp:{protocol}" if endpoint else "console",
        )
        return True


@contextlib.contextmanager
def start_span(
    name: str,
    *,
    tracer_name: str,
    attributes: Mapping[str, Any] | None = None,
) -> Iterator[Any | None]:
    """Start a span when telemetry is enabled, otherwise yield ``None``."""
    if not telemetry_requested():
        yield None
        return

    if not configure_otel(
        service_name=os.environ.get("OTEL_SERVICE_NAME", "").strip() or "amplihack",
        component=os.environ.get("AMPLIHACK_OTEL_COMPONENT", "").strip(),
    ):
        yield None
        return

    try:
        trace = importlib.import_module("opentelemetry.trace")
    except Exception:  # pragma: no cover - depends on env
        yield None
        return

    with trace.get_tracer(tracer_name).start_as_current_span(name) as span:
        set_span_attributes(span, attributes)
        yield span


def set_span_attributes(span: Any | None, attributes: Mapping[str, Any] | None) -> None:
    """Best-effort attribute setter that accepts arbitrary mappings."""
    if span is None:
        return
    for key, value in _normalize_attributes(attributes).items():
        span.set_attribute(key, value)


def add_span_event(
    span: Any | None,
    name: str,
    attributes: Mapping[str, Any] | None = None,
) -> None:
    """Best-effort span event emission helper."""
    if span is None:
        return
    span.add_event(name, _normalize_attributes(attributes))


__all__ = [
    "add_span_event",
    "configure_otel",
    "otel_env_overrides",
    "set_span_attributes",
    "start_span",
    "telemetry_requested",
]
