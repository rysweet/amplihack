from __future__ import annotations

from pathlib import Path

_ASPIRE_DIR = Path(__file__).parent.parent / "aspire"
_APPHOST = _ASPIRE_DIR / "apphost.cs"
_LAUNCH_SETTINGS = _ASPIRE_DIR / "Properties" / "launchSettings.json"
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

    def test_apphost_wires_http_otel_for_local_dashboard(self):
        content = _APPHOST.read_text()
        assert "builder.AppHostDirectory" in content
        assert '"ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL"' in content
        assert '"telemetry:protocol"' in content
        assert '"OTEL_EXPORTER_OTLP_PROTOCOL"' in content
        assert '"http/protobuf"' in content
        assert '"grpc"' in content
        assert '"telemetry:endpoint"' in content
        assert '"OTEL_EXPORTER_OTLP_ENDPOINT"' in content
        assert '"http://localhost:4318"' in content
        assert 'WithEnvironment("OTEL_EXPORTER_OTLP_PROTOCOL", otlpProtocol)' in content
        assert 'WithEnvironment("OTEL_EXPORTER_OTLP_ENDPOINT", otlpEndpoint)' in content
        assert 'WithEnvironment("OTEL_EXPORTER_OTLP_CERTIFICATE", certPath)' in content
        assert "ResolveTrustedDevCertPath()" in content
        assert 'OTEL_SERVICE_NAME", "amplihack.aspire.telemetry-heartbeat"' in content

    def test_launch_settings_expose_aspire_dashboard_otlp_http_endpoint(self):
        assert _LAUNCH_SETTINGS.exists()
        content = _LAUNCH_SETTINGS.read_text()
        assert '"ASPIRE_ALLOW_UNSECURED_TRANSPORT": "true"' in content
        assert '"ASPIRE_DASHBOARD_UNSECURED_ALLOW_ANONYMOUS": "true"' in content
        assert '"ASPIRE_DASHBOARD_OTLP_HTTP_ENDPOINT_URL": "http://localhost:4318"' in content

    def test_apphost_models_real_azure_commands(self):
        content = _APPHOST.read_text()
        assert "deploy/azure_hive/deploy.sh" in content
        assert "deploy/azure_hive/eval_monitor.py" in content
        assert "deploy/azure_hive/eval_retrieval_smoke.py" in content
        assert "deploy/azure_hive/eval_distributed.py" in content
        assert "deploy/azure_hive/eval_distributed_security.py" in content
        assert "AMPLIHACK_ASPIRE_ENABLE_AZURE_DEPLOY" in content
        assert "AMPLIHACK_ASPIRE_ENABLE_EVAL_MONITOR" in content
        assert "AMPLIHACK_ASPIRE_ENABLE_RETRIEVAL_SMOKE" in content
        assert "AMPLIHACK_ASPIRE_ENABLE_LONG_HORIZON_EVAL" in content
        assert "AMPLIHACK_ASPIRE_ENABLE_SECURITY_EVAL" in content

    def test_apphost_long_horizon_uses_scale_aware_answer_timeout(self):
        content = _APPHOST.read_text()
        assert "GetDefaultEvalAnswerTimeout(" in content
        assert '"AMPLIHACK_ASPIRE_ANSWER_TIMEOUT"' in content

    def test_apphost_pythonpath_includes_eval_repo_src(self):
        content = _APPHOST.read_text()
        assert 'Path.Combine(repoRoot, "..", "amplihack-agent-eval")' in content
        assert 'WithEnvironment("PYTHONPATH", pythonPath)' in content

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
