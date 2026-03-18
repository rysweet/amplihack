from __future__ import annotations

from amplihack import observability


def test_otel_env_overrides_uses_grpc_endpoint_without_trace_suffix(monkeypatch):
    monkeypatch.setenv("AMPLIHACK_OTEL_ENABLED", "true")
    monkeypatch.setenv("AMPLIHACK_OTEL_OTLP_PROTOCOL", "grpc")
    monkeypatch.setenv("AMPLIHACK_OTEL_OTLP_ENDPOINT", "http://localhost:4317")

    env = observability.otel_env_overrides(service_name="amplihack.test.grpc")

    assert env["OTEL_EXPORTER_OTLP_PROTOCOL"] == "grpc"
    assert env["OTEL_EXPORTER_OTLP_ENDPOINT"] == "http://localhost:4317"
    assert "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT" not in env


def test_otel_env_overrides_keeps_http_trace_suffix(monkeypatch):
    monkeypatch.setenv("AMPLIHACK_OTEL_ENABLED", "true")
    monkeypatch.setenv("AMPLIHACK_OTEL_OTLP_PROTOCOL", "http/protobuf")
    monkeypatch.setenv("AMPLIHACK_OTEL_OTLP_ENDPOINT", "http://collector:4318")

    env = observability.otel_env_overrides(service_name="amplihack.test.http")

    assert env["OTEL_EXPORTER_OTLP_PROTOCOL"] == "http/protobuf"
    assert env["OTEL_EXPORTER_OTLP_ENDPOINT"] == "http://collector:4318"
    assert env["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] == "http://collector:4318/v1/traces"
