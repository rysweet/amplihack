from __future__ import annotations

from pathlib import Path

_ASPIRE_DIR = Path(__file__).parent.parent / "aspire"
_APPHOST = _ASPIRE_DIR / "apphost.cs"
_NUGET_CONFIG = _ASPIRE_DIR / "NuGet.config"
_HEARTBEAT = _ASPIRE_DIR / "telemetry_heartbeat.py"
_DEPLOY_SH = Path(__file__).parent.parent / "deploy.sh"
_BICEP = Path(__file__).parent.parent / "main.bicep"
_DOCKERFILE = Path(__file__).parent.parent / "Dockerfile"


class TestAspireAppHost:
    def test_apphost_exists(self):
        assert _APPHOST.exists()

    def test_apphost_uses_file_based_sdk(self):
        assert "#:sdk Aspire.AppHost.Sdk@" in _APPHOST.read_text()

    def test_apphost_wires_grpc_otel_for_local_dashboard(self):
        content = _APPHOST.read_text()
        assert "builder.AppHostDirectory" in content
        assert (
            'GetConfig(builder, "telemetry:protocol", "OTEL_EXPORTER_OTLP_PROTOCOL", "grpc")'
            in content
        )
        assert (
            'GetConfig(builder, "telemetry:endpoint", "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")'
            in content
        )
        assert 'WithEnvironment("OTEL_EXPORTER_OTLP_PROTOCOL", otlpProtocol)' in content
        assert 'WithEnvironment("OTEL_EXPORTER_OTLP_ENDPOINT", otlpEndpoint)' in content
        assert 'OTEL_SERVICE_NAME", "amplihack.aspire.telemetry-heartbeat"' in content

    def test_apphost_models_real_azure_commands(self):
        content = _APPHOST.read_text()
        assert "deploy/azure_hive/deploy.sh" in content
        assert "deploy/azure_hive/eval_monitor.py" in content
        assert "deploy/azure_hive/eval_distributed.py" in content
        assert "deploy/azure_hive/eval_distributed_security.py" in content
        assert "AMPLIHACK_ASPIRE_ENABLE_AZURE_DEPLOY" in content
        assert "AMPLIHACK_ASPIRE_ENABLE_EVAL_MONITOR" in content
        assert "AMPLIHACK_ASPIRE_ENABLE_LONG_HORIZON_EVAL" in content
        assert "AMPLIHACK_ASPIRE_ENABLE_SECURITY_EVAL" in content

    def test_apphost_exposes_monitor_spotcheck_thresholds(self):
        content = _APPHOST.read_text()
        assert "AMPLIHACK_ASPIRE_MONITOR_WAIT_FOR_ONLINE" in content
        assert "AMPLIHACK_ASPIRE_MONITOR_WAIT_FOR_READY" in content
        assert "AMPLIHACK_ASPIRE_MONITOR_WAIT_FOR_PROGRESS" in content
        assert "AMPLIHACK_ASPIRE_MONITOR_WAIT_FOR_ANSWERS" in content
        assert "AMPLIHACK_ASPIRE_MONITOR_MAX_WAIT_SECONDS" in content

    def test_nuget_config_exists(self):
        assert _NUGET_CONFIG.exists()
        assert "https://api.nuget.org/v3/index.json" in _NUGET_CONFIG.read_text()

    def test_heartbeat_script_exists(self):
        assert _HEARTBEAT.exists()
        content = _HEARTBEAT.read_text()
        assert "configure_otel" in content
        assert "start_span" in content


class TestAzureOtlpProtocolWiring:
    def test_deploy_sh_accepts_otel_protocol(self):
        content = _DEPLOY_SH.read_text()
        assert 'OTEL_OTLP_PROTOCOL="${HIVE_OTEL_OTLP_PROTOCOL:-http/protobuf}"' in content
        assert 'otelOtlpProtocol="${OTEL_OTLP_PROTOCOL}"' in content

    def test_bicep_exports_otel_protocol(self):
        content = _BICEP.read_text()
        assert "param otelOtlpProtocol string = 'http/protobuf'" in content
        assert "name: 'OTEL_EXPORTER_OTLP_PROTOCOL'" in content

    def test_dockerfile_installs_grpc_exporter(self):
        assert "opentelemetry-exporter-otlp-proto-grpc" in _DOCKERFILE.read_text()
