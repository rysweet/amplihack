// main.bicep -- Azure infrastructure for distributed hive mind deployment.
//
// Resources created:
//   - Container Registry (Basic, admin-enabled for image pull)
//   - Log Analytics workspace
//   - Container Apps Environment (Consumption tier)
//   - Service Bus Namespace (Premium) + Topic + Subscriptions (one per agent)
//   - N Container Apps (ceil(agentCount / agentsPerApp) apps, each with
//     up to agentsPerApp agent containers)
//
// Note: EmptyDir volumes used for /data (Kuzu storage). Kuzu requires POSIX
// file locks which Azure Files SMB does not support. Every deploy is from
// scratch — agents are fed content fresh after deployment.
//
// Usage:
//   az deployment group create \
//     --resource-group <rg> \
//     --template-file deploy/azure_hive/main.bicep \
//     --parameters hiveName=my-hive agentCount=20 anthropicApiKey=<key>

@description('Name of the hive deployment')
param hiveName string = 'amplihive'

@description('Azure region for all resources — always pass explicitly to ensure single-region deployment')
param location string = resourceGroup().location

@description('Total number of agents to deploy')
param agentCount int = 5

@description('Max agents per Container App (default: 5)')
param agentsPerApp int = 5

@description('Container image to deploy (e.g. myacr.azurecr.io/amplihive:latest)')
param image string = ''

@description('Name of the Azure Container Registry')
param acrName string = ''

@description('Anthropic API key for Claude SDK agents')
@secure()
param anthropicApiKey string = ''

@description('Agent system prompt base (agent index appended)')
param agentPromptBase string = 'You are a distributed hive mind agent.'

@description('Memory transport type')
@allowed(['local', 'redis', 'azure_service_bus'])
param memoryTransport string = 'azure_service_bus'

@description('Memory backend type')
@allowed(['cognitive', 'hierarchical'])
param memoryBackend string = 'cognitive'

@description('LLM model for agents (e.g. claude-sonnet-4-6, claude-opus-4-6)')
param agentModel string = 'claude-sonnet-4-6'

@description('Service Bus topic name override (default: hive-events-<hiveName>)')
param sbTopicNameParam string = ''


// ---------- Naming ----------
var suffix = uniqueString(resourceGroup().id)
var sbTopicName = empty(sbTopicNameParam) ? 'hive-events-${hiveName}' : sbTopicNameParam
var acrNameResolved = empty(acrName) ? 'acr${suffix}' : acrName
var logAnalyticsName = 'hive-logs-${suffix}'
var envName = 'hive-env-${hiveName}'
var sbNamespaceName = 'hive-sb-${suffix}'
var ehNamespaceName = 'hive-eh-${suffix}'
var ehName = 'hive-shards-${hiveName}'
var appCount = (agentCount + agentsPerApp - 1) / agentsPerApp

// ---------- Container Registry ----------
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = if (empty(acrName)) {
  name: acrNameResolved
  location: location
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: true
  }
}

resource acrExisting 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = if (!empty(acrName)) {
  name: acrName
}

// ---------- Log Analytics ----------
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}


// ---------- Service Bus (Standard — for hive-events topic only) ----------
// Note: Service Bus is retained only for the main hive-events topic
// (LEARN_CONTENT, INPUT, AGENT_READY) and eval response collection.
// Shard transport (SHARD_QUERY/SHARD_RESPONSE) moved to Event Hubs below.
resource sbNamespace 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: sbNamespaceName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
}

resource sbTopic 'Microsoft.ServiceBus/namespaces/topics@2022-10-01-preview' = {
  name: sbTopicName
  parent: sbNamespace
  properties: {
    enablePartitioning: false
    defaultMessageTimeToLive: 'PT1H'
  }
}

// One subscription per agent for targeted message delivery
resource sbSubscriptions 'Microsoft.ServiceBus/namespaces/topics/subscriptions@2022-10-01-preview' = [
  for i in range(0, agentCount): {
    name: 'agent-${i}'
    parent: sbTopic
    properties: {
      defaultMessageTimeToLive: 'PT1H'
      lockDuration: 'PT30S'
      maxDeliveryCount: 3
    }
  }
]

// Eval subscription for query_hive.py to collect agent responses
resource sbEvalSubscription 'Microsoft.ServiceBus/namespaces/topics/subscriptions@2022-10-01-preview' = {
  name: 'eval-query-agent'
  parent: sbTopic
  properties: {
    defaultMessageTimeToLive: 'PT1H'
    lockDuration: 'PT30S'
    maxDeliveryCount: 3
  }
}

// Eval response topic for distributed eval answer collection
resource sbEvalResponseTopic 'Microsoft.ServiceBus/namespaces/topics@2022-10-01-preview' = {
  name: 'eval-responses-${hiveName}'
  parent: sbNamespace
  properties: {
    enablePartitioning: false
    defaultMessageTimeToLive: 'PT1H'
  }
}

// Single subscription for the eval harness to read answers
resource sbEvalReaderSubscription 'Microsoft.ServiceBus/namespaces/topics/subscriptions@2022-10-01-preview' = {
  name: 'eval-reader'
  parent: sbEvalResponseTopic
  properties: {
    defaultMessageTimeToLive: 'PT1H'
    lockDuration: 'PT30S'
    maxDeliveryCount: 3
  }
}

// ---------- Event Hubs (shard transport — replaces Service Bus shard topic) ----------
// Event Hubs is more reliable than Service Bus Standard for container-to-container
// messaging in Azure Container Apps (no CBS auth failures, no connection drops).
// Each agent gets a dedicated consumer group for partition-key-routed delivery.
resource ehNamespace 'Microsoft.EventHub/namespaces@2023-01-01-preview' = {
  name: ehNamespaceName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
    capacity: 1
  }
  properties: {
    isAutoInflateEnabled: false
    maximumThroughputUnits: 0
  }
}

// One Event Hub for all shard queries — partition-key routes to target agent
resource ehShardsHub 'Microsoft.EventHub/namespaces/eventhubs@2023-01-01-preview' = {
  name: ehName
  parent: ehNamespace
  properties: {
    // N+4 partitions: agentCount partitions for agents, 4 spare for headroom.
    // partition_key=agent-N routes consistently to one partition via hash.
    partitionCount: agentCount + 4
    messageRetentionInDays: 1
  }
}

// Per-agent consumer group: each agent reads from its own consumer group
// so it receives all events (filtering by target_agent happens client-side).
resource ehConsumerGroups 'Microsoft.EventHub/namespaces/eventhubs/consumergroups@2023-01-01-preview' = [
  for i in range(0, agentCount): {
    name: 'cg-agent-${i}'
    parent: ehShardsHub
  }
]

// ---------- Container Apps Environment ----------
resource containerEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: envName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

// ---------- Container Apps (agentsPerApp agents per app) ----------
// Uses EmptyDir volumes at /data for Kuzu storage. Kuzu requires POSIX locks.
// Data is ephemeral — every deploy is from scratch (content fed after deploy).
var sbConnectionString = listKeys('${sbNamespace.id}/AuthorizationRules/RootManageSharedAccessKey', '2022-10-01-preview').primaryConnectionString
var ehConnectionString = listKeys('${ehNamespace.id}/AuthorizationRules/RootManageSharedAccessKey', '2023-01-01-preview').primaryConnectionString
var acrCredentials = empty(acrName) ? acr.listCredentials() : acrExisting.listCredentials()
var resolvedImage = empty(image) ? '${acrNameResolved}.azurecr.io/amplihive:latest' : image

resource containerApps 'Microsoft.App/containerApps@2024-03-01' = [
  for appIdx in range(0, appCount): {
    name: '${hiveName}-app-${appIdx}'
    location: location
    properties: {
      managedEnvironmentId: containerEnv.id
      workloadProfileName: 'Consumption'
      configuration: {
        activeRevisionsMode: 'Single'
        secrets: [
          {
            name: 'acr-password'
            value: acrCredentials.passwords[0].value
          }
          {
            name: 'anthropic-api-key'
            value: anthropicApiKey
          }
          {
            name: 'sb-connection-string'
            value: memoryTransport == 'azure_service_bus' ? sbConnectionString : ''
          }
          {
            name: 'eh-connection-string'
            value: ehConnectionString
          }
        ]
        registries: [
          {
            server: '${acrNameResolved}.azurecr.io'
            username: acrCredentials.username
            passwordSecretRef: 'acr-password' // pragma: allowlist secret
          }
        ]
      }
      template: {
        volumes: [
          {
            name: 'hive-data'
            storageType: 'EmptyDir'
          }
        ]
        containers: [
          for agentOffset in range(0, agentsPerApp): {
            name: 'agent-${appIdx * agentsPerApp + agentOffset}'
            image: resolvedImage
            resources: {
              cpu: json('0.5')
              memory: '1Gi'
            }
            env: [
              {
                name: 'AMPLIHACK_AGENT_NAME'
                value: 'agent-${appIdx * agentsPerApp + agentOffset}'
              }
              {
                name: 'AMPLIHACK_AGENT_PROMPT'
                value: '${agentPromptBase} You are agent ${appIdx * agentsPerApp + agentOffset}.'
              }
              {
                name: 'AMPLIHACK_MEMORY_BACKEND'
                value: memoryBackend
              }
              {
                name: 'AMPLIHACK_MEMORY_TRANSPORT'
                value: memoryTransport
              }
              {
                name: 'AMPLIHACK_MEMORY_CONNECTION_STRING'
                secretRef: 'sb-connection-string' // pragma: allowlist secret
              }
              {
                name: 'AMPLIHACK_MEMORY_STORAGE_PATH'
                value: '/data/agent-${appIdx * agentsPerApp + agentOffset}'
              }
              {
                name: 'AMPLIHACK_MODEL'
                value: agentModel
              }
              {
                name: 'AMPLIHACK_SB_TOPIC'
                value: sbTopicName
              }
              {
                name: 'AMPLIHACK_HIVE_NAME'
                value: hiveName
              }
              {
                name: 'AMPLIHACK_AGENT_COUNT'
                value: '${agentCount}'
              }
              {
                name: 'AMPLIHACK_EVAL_RESPONSE_TOPIC'
                value: 'eval-responses-${hiveName}'
              }
              {
                name: 'AMPLIHACK_EH_CONNECTION_STRING'
                secretRef: 'eh-connection-string' // pragma: allowlist secret
              }
              {
                name: 'AMPLIHACK_EH_NAME'
                value: ehName
              }
              {
                name: 'ANTHROPIC_API_KEY'
                secretRef: 'anthropic-api-key' // pragma: allowlist secret
              }
            ]
            volumeMounts: [
              {
                volumeName: 'hive-data'
                mountPath: '/data'
              }
            ]
          }
        ]
        scale: {
          minReplicas: 1
          maxReplicas: 1
        }
      }
    }
  }
]

// ---------- Outputs ----------
output acrLoginServer string = empty(acrName) ? acr.properties.loginServer : acrExisting.properties.loginServer
output sbNamespaceFqdn string = sbNamespace.properties.serviceBusEndpoint
output containerAppNames array = [for appIdx in range(0, appCount): '${hiveName}-app-${appIdx}']
output sbConnectionStringSecretName string = 'sb-connection-string'
output sbTopicNameOutput string = sbTopicName
output evalResponseTopicName string = 'eval-responses-${hiveName}'
output ehNamespaceName string = ehNamespaceName
output ehName string = ehName
