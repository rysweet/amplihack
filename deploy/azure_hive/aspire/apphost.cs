#:sdk Aspire.AppHost.Sdk@13.1.0

using System;
using System.Collections.Generic;
using System.IO;

var builder = DistributedApplication.CreateBuilder(args);

var repoRoot = Path.GetFullPath(Path.Combine(builder.AppHostDirectory, "..", "..", ".."));
var srcPath = Path.Combine(repoRoot, "src");
var deploymentProfile = GetConfig(builder, "azure:deploymentProfile", "HIVE_DEPLOYMENT_PROFILE", "federated-100");
var hiveName = GetConfig(builder, "azure:hiveName", "HIVE_NAME", "amplihive");
var agentCount = GetConfig(builder, "azure:agentCount", "HIVE_AGENT_COUNT", "100");
// Default to "true" to match deploy.sh — distributed retrieval must be
// enabled for 100-agent topology where each agent only holds ~1% of the
// total corpus.  Set HIVE_ENABLE_DISTRIBUTED_RETRIEVAL=false or
// azure:enableDistributedRetrieval=false to disable (smoke-10 profile).
var enableDistributedRetrieval = GetConfig(
    builder,
    "azure:enableDistributedRetrieval",
    "HIVE_ENABLE_DISTRIBUTED_RETRIEVAL",
    "true"
);
var otlpProtocol = GetConfig(builder, "telemetry:protocol", "OTEL_EXPORTER_OTLP_PROTOCOL", "grpc");
var otlpEndpoint = GetConfig(builder, "telemetry:endpoint", "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317");

builder
    .AddExecutable("otel-heartbeat", "python", repoRoot)
    .WithArgs("deploy/azure_hive/aspire/telemetry_heartbeat.py")
    .WithEnvironment("PYTHONPATH", srcPath)
    .WithEnvironment("PYTHONUNBUFFERED", "1")
    .WithEnvironment("AMPLIHACK_OTEL_ENABLED", "true")
    .WithEnvironment("OTEL_EXPORTER_OTLP_PROTOCOL", otlpProtocol)
    .WithEnvironment("OTEL_EXPORTER_OTLP_ENDPOINT", otlpEndpoint)
    .WithEnvironment("OTEL_SERVICE_NAMESPACE", "amplihack")
    .WithEnvironment("OTEL_SERVICE_NAME", "amplihack.aspire.telemetry-heartbeat");

if (GetBool(builder, "azure:enableDeployCommand", "AMPLIHACK_ASPIRE_ENABLE_AZURE_DEPLOY"))
{
    builder
        .AddExecutable("azure-hive-deploy", "bash", repoRoot)
        .WithArgs("deploy/azure_hive/deploy.sh")
        .WithEnvironment("PYTHONUNBUFFERED", "1")
        .WithEnvironment("HIVE_DEPLOYMENT_PROFILE", deploymentProfile)
        .WithEnvironment("HIVE_NAME", hiveName)
        .WithEnvironment("HIVE_AGENT_COUNT", agentCount)
        .WithEnvironment("HIVE_ENABLE_DISTRIBUTED_RETRIEVAL", enableDistributedRetrieval)
        .WithEnvironment("AMPLIHACK_OTEL_ENABLED", "true")
        .WithEnvironment("OTEL_EXPORTER_OTLP_PROTOCOL", otlpProtocol)
        .WithEnvironment("OTEL_EXPORTER_OTLP_ENDPOINT", otlpEndpoint)
        .WithEnvironment("OTEL_SERVICE_NAMESPACE", "amplihack")
        .WithEnvironment("OTEL_SERVICE_NAME", "amplihack.aspire.azure-hive-deploy");
}

var eventHubConnectionString = GetConfig(
    builder,
    "azure:eventHubsConnectionString",
    "EH_CONN",
    ""
);
var inputHub = GetConfig(builder, "azure:inputHub", "AMPLIHACK_EH_INPUT_HUB", "");
var responseHub = GetConfig(builder, "azure:responseHub", "AMPLIHACK_EH_RESPONSE_HUB", "");

if (!string.IsNullOrWhiteSpace(eventHubConnectionString) && !string.IsNullOrWhiteSpace(responseHub))
{
    if (GetBool(builder, "eval:enableMonitor", "AMPLIHACK_ASPIRE_ENABLE_EVAL_MONITOR"))
    {
        builder
            .AddExecutable("azure-hive-eval-monitor", "python", repoRoot)
            .WithArgs(BuildMonitorArgs(builder, eventHubConnectionString, responseHub))
            .WithEnvironment("PYTHONPATH", srcPath)
            .WithEnvironment("PYTHONUNBUFFERED", "1")
            .WithEnvironment("AMPLIHACK_OTEL_ENABLED", "true")
            .WithEnvironment("OTEL_EXPORTER_OTLP_PROTOCOL", otlpProtocol)
            .WithEnvironment("OTEL_EXPORTER_OTLP_ENDPOINT", otlpEndpoint)
            .WithEnvironment("OTEL_SERVICE_NAMESPACE", "amplihack")
            .WithEnvironment("OTEL_SERVICE_NAME", "amplihack.aspire.azure-hive-monitor");
    }
}

if (
    !string.IsNullOrWhiteSpace(eventHubConnectionString)
    && !string.IsNullOrWhiteSpace(inputHub)
    && !string.IsNullOrWhiteSpace(responseHub)
)
{
    if (GetBool(builder, "eval:enableLongHorizon", "AMPLIHACK_ASPIRE_ENABLE_LONG_HORIZON_EVAL"))
    {
        builder
            .AddExecutable("azure-hive-long-horizon-eval", "python", repoRoot)
            .WithArgs(BuildLongHorizonArgs(builder, eventHubConnectionString, inputHub, responseHub))
            .WithEnvironment("PYTHONPATH", srcPath)
            .WithEnvironment("PYTHONUNBUFFERED", "1")
            .WithEnvironment("AMPLIHACK_OTEL_ENABLED", "true")
            .WithEnvironment("OTEL_EXPORTER_OTLP_PROTOCOL", otlpProtocol)
            .WithEnvironment("OTEL_EXPORTER_OTLP_ENDPOINT", otlpEndpoint)
            .WithEnvironment("OTEL_SERVICE_NAMESPACE", "amplihack")
            .WithEnvironment("OTEL_SERVICE_NAME", "amplihack.aspire.azure-hive-long-horizon");
    }

    if (GetBool(builder, "eval:enableSecurity", "AMPLIHACK_ASPIRE_ENABLE_SECURITY_EVAL"))
    {
        builder
            .AddExecutable("azure-hive-security-eval", "python", repoRoot)
            .WithArgs(BuildSecurityEvalArgs(builder, eventHubConnectionString, inputHub, responseHub))
            .WithEnvironment("PYTHONPATH", srcPath)
            .WithEnvironment("PYTHONUNBUFFERED", "1")
            .WithEnvironment("AMPLIHACK_OTEL_ENABLED", "true")
            .WithEnvironment("OTEL_EXPORTER_OTLP_PROTOCOL", otlpProtocol)
            .WithEnvironment("OTEL_EXPORTER_OTLP_ENDPOINT", otlpEndpoint)
            .WithEnvironment("OTEL_SERVICE_NAMESPACE", "amplihack")
            .WithEnvironment("OTEL_SERVICE_NAME", "amplihack.aspire.azure-hive-security");
    }
}

builder.Build().Run();

static string GetConfig(
    IDistributedApplicationBuilder builder,
    string configKey,
    string envKey,
    string defaultValue
)
{
    return builder.Configuration[configKey]
        ?? Environment.GetEnvironmentVariable(envKey)
        ?? defaultValue;
}

static bool GetBool(
    IDistributedApplicationBuilder builder,
    string configKey,
    string envKey,
    bool defaultValue = false
)
{
    var value = GetConfig(builder, configKey, envKey, defaultValue ? "true" : "false");
    return value.Equals("1", StringComparison.OrdinalIgnoreCase)
        || value.Equals("yes", StringComparison.OrdinalIgnoreCase)
        || value.Equals("on", StringComparison.OrdinalIgnoreCase)
        || bool.TryParse(value, out var parsed) && parsed;
}

static void AddOptionalPositiveArg(
    IDistributedApplicationBuilder builder,
    List<string> args,
    string argName,
    string configKey,
    string envKey
)
{
    var value = GetConfig(builder, configKey, envKey, "0");
    if (int.TryParse(value, out var parsed) && parsed > 0)
    {
        args.Add(argName);
        args.Add(parsed.ToString());
    }
}

static string[] BuildMonitorArgs(
    IDistributedApplicationBuilder builder,
    string connectionString,
    string responseHub
)
{
    var args = new List<string>
    {
        "deploy/azure_hive/eval_monitor.py",
        "--connection-string",
        connectionString,
        "--response-hub",
        responseHub,
        "--consumer-group",
        GetConfig(
            builder,
            "eval:monitorConsumerGroup",
            "AMPLIHACK_EVAL_MONITOR_CONSUMER_GROUP",
            "eval-reader"
        ),
        "--agents",
        GetConfig(builder, "azure:agentCount", "HIVE_AGENT_COUNT", "100"),
        "--output",
        GetConfig(
            builder,
            "eval:monitorOutput",
            "AMPLIHACK_ASPIRE_MONITOR_OUTPUT",
            "aspire_eval_monitor_progress.json"
        ),
    };

    AddOptionalPositiveArg(
        builder,
        args,
        "--wait-for-online",
        "eval:monitorWaitForOnline",
        "AMPLIHACK_ASPIRE_MONITOR_WAIT_FOR_ONLINE"
    );
    AddOptionalPositiveArg(
        builder,
        args,
        "--wait-for-ready",
        "eval:monitorWaitForReady",
        "AMPLIHACK_ASPIRE_MONITOR_WAIT_FOR_READY"
    );
    AddOptionalPositiveArg(
        builder,
        args,
        "--wait-for-progress",
        "eval:monitorWaitForProgress",
        "AMPLIHACK_ASPIRE_MONITOR_WAIT_FOR_PROGRESS"
    );
    AddOptionalPositiveArg(
        builder,
        args,
        "--wait-for-answers",
        "eval:monitorWaitForAnswers",
        "AMPLIHACK_ASPIRE_MONITOR_WAIT_FOR_ANSWERS"
    );
    AddOptionalPositiveArg(
        builder,
        args,
        "--max-wait-seconds",
        "eval:monitorMaxWaitSeconds",
        "AMPLIHACK_ASPIRE_MONITOR_MAX_WAIT_SECONDS"
    );

    return args.ToArray();
}

static string[] BuildLongHorizonArgs(
    IDistributedApplicationBuilder builder,
    string connectionString,
    string inputHub,
    string responseHub
)
{
    var args = new List<string>
    {
        "deploy/azure_hive/eval_distributed.py",
        "--connection-string",
        connectionString,
        "--input-hub",
        inputHub,
        "--response-hub",
        responseHub,
        "--turns",
        GetConfig(builder, "eval:turns", "AMPLIHACK_ASPIRE_EVAL_TURNS", "5000"),
        "--questions",
        GetConfig(builder, "eval:questions", "AMPLIHACK_ASPIRE_EVAL_QUESTIONS", "50"),
        "--agents",
        GetConfig(builder, "azure:agentCount", "HIVE_AGENT_COUNT", "100"),
        "--seed",
        GetConfig(builder, "eval:seed", "AMPLIHACK_ASPIRE_EVAL_SEED", "42"),
        "--answer-timeout",
        GetConfig(builder, "eval:answerTimeout", "AMPLIHACK_ASPIRE_ANSWER_TIMEOUT", "120"),
        "--grader-model",
        GetConfig(
            builder,
            "eval:graderModel",
            "GRADER_MODEL",
            "claude-haiku-4-5-20251001"
        ),
    };

    if (
        GetBool(
            builder,
            "eval:replicateLearnToAllAgents",
            "AMPLIHACK_ASPIRE_REPLICATE_LEARN",
            true
        )
    )
    {
        args.Add("--replicate-learn-to-all-agents");
    }

    args.Add("--question-failover-retries");
    args.Add(GetConfig(builder, "eval:questionFailoverRetries", "AMPLIHACK_ASPIRE_FAILOVER_RETRIES", "2"));

    return args.ToArray();
}

static string[] BuildSecurityEvalArgs(
    IDistributedApplicationBuilder builder,
    string connectionString,
    string inputHub,
    string responseHub
)
{
    var args = new List<string>
    {
        "deploy/azure_hive/eval_distributed_security.py",
        "--connection-string",
        connectionString,
        "--input-hub",
        inputHub,
        "--response-hub",
        responseHub,
        "--turns",
        GetConfig(builder, "securityEval:turns", "AMPLIHACK_ASPIRE_SECURITY_TURNS", "300"),
        "--questions",
        GetConfig(builder, "securityEval:questions", "AMPLIHACK_ASPIRE_SECURITY_QUESTIONS", "50"),
        "--campaigns",
        GetConfig(builder, "securityEval:campaigns", "AMPLIHACK_ASPIRE_SECURITY_CAMPAIGNS", "12"),
        "--agents",
        GetConfig(builder, "azure:agentCount", "HIVE_AGENT_COUNT", "100"),
        "--seed",
        GetConfig(builder, "securityEval:seed", "AMPLIHACK_ASPIRE_SECURITY_SEED", "42"),
        "--answer-timeout",
        GetConfig(
            builder,
            "securityEval:answerTimeout",
            "AMPLIHACK_ASPIRE_SECURITY_ANSWER_TIMEOUT",
            "120"
        ),
    };

    if (
        GetBool(
            builder,
            "securityEval:replicateLearnToAllAgents",
            "AMPLIHACK_ASPIRE_REPLICATE_LEARN",
            true
        )
    )
    {
        args.Add("--replicate-learn-to-all-agents");
    }

    args.Add("--question-failover-retries");
    args.Add(
        GetConfig(
            builder,
            "securityEval:questionFailoverRetries",
            "AMPLIHACK_ASPIRE_FAILOVER_RETRIES",
            "2"
        )
    );

    return args.ToArray();
}
