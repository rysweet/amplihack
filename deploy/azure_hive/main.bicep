// main.bicep -- Azure infrastructure for distributed hive mind deployment.
//
// Resources created:
//   - Container Registry (Basic, admin-enabled for image pull)
//   - Log Analytics workspace
//   - Container Apps Environment (Consumption tier)
//   - Event Hubs Namespace (Standard, 1 TU) with 3 hubs:
//       hive-events-{hiveName}   -- LEARN_CONTENT / INPUT messages (per-agent consumer groups)
//       hive-shards-{hiveName}   -- SHARD_QUERY / SHARD_RESPONSE cross-shard DHT protocol
//       eval-responses-{hiveName}-- EVAL_ANSWER answers from agents to eval harness
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
@allowed(['local', 'azure_event_hubs'])
param memoryTransport string = 'azure_event_hubs'

@description('Memory backend type')
@allowed(['cognitive', 'hierarchical'])
param memoryBackend string = 'cognitive'

@description('LLM model for agents (e.g. claude-sonnet-4-6, claude-opus-4-6)')
param agentModel string = 'claude-sonnet-4-6'


// ---------- Naming ----------
var suffix = uniqueString(resourceGroup().id)
var acrNameResolved = empty(acrName) ? 'acr${suffix}' : acrName
var logAnalyticsName = 'hive-logs-${suffix}'
var envName = 'hive-env-${hiveName}'
var ehNamespaceName = 'hive-eh-${suffix}'
var ehEventsHubName = 'hive-events-${hiveName}'
var ehShardsHubName = 'hive-shards-${hiveName}'
var ehResponsesHubName = 'eval-responses-${hiveName}'
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


// ---------- Event Hubs Namespace (Standard, 1 TU) ----------
// Single namespace for all three hubs. CBS-free AMQP — no auth failures in
// Container Apps unlike Azure Service Bus Standard.
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

// Hub 1: hive-events — receives LEARN_CONTENT / INPUT messages from eval harness.
// Each agent gets a dedicated consumer group (cg-agent-N) for independent delivery.
resource ehEventsHub 'Microsoft.EventHub/namespaces/eventhubs@2023-01-01-preview' = {
  name: ehEventsHubName
  parent: ehNamespace
  properties: {
    partitionCount: agentCount + 4
    messageRetentionInDays: 1
  }
}

resource ehEventsConsumerGroups 'Microsoft.EventHub/namespaces/eventhubs/consumergroups@2023-01-01-preview' = [
  for i in range(0, agentCount): {
    name: 'cg-agent-${i}'
    parent: ehEventsHub
  }
]

// Hub 2: hive-shards — SHARD_QUERY / SHARD_RESPONSE cross-shard DHT protocol.
// Each agent gets a dedicated consumer group for partition-key-routed delivery.
resource ehShardsHub 'Microsoft.EventHub/namespaces/eventhubs@2023-01-01-preview' = {
  name: ehShardsHubName
  parent: ehNamespace
  properties: {
    partitionCount: agentCount + 4
    messageRetentionInDays: 1
  }
}

resource ehShardsConsumerGroups 'Microsoft.EventHub/namespaces/eventhubs/consumergroups@2023-01-01-preview' = [
  for i in range(0, agentCount): {
    name: 'cg-agent-${i}'
    parent: ehShardsHub
  }
]

// Hub 3: eval-responses — agents publish EVAL_ANSWER events.
// eval harness reads via cg-eval-reader consumer group.
resource ehResponsesHub 'Microsoft.EventHub/namespaces/eventhubs@2023-01-01-preview' = {
  name: ehResponsesHubName
  parent: ehNamespace
  properties: {
    partitionCount: agentCount + 4
    messageRetentionInDays: 1
  }
}

resource ehResponsesEvalReader 'Microsoft.EventHub/namespaces/eventhubs/consumergroups@2023-01-01-preview' = {
  name: 'cg-eval-reader'
  parent: ehResponsesHub
}

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
                name: 'AMPLIHACK_MEMORY_STORAGE_PATH'
                value: '/data/agent-${appIdx * agentsPerApp + agentOffset}'
              }
              {
                name: 'AMPLIHACK_MODEL'
                value: agentModel
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
                name: 'AMPLIHACK_EH_CONNECTION_STRING'
                secretRef: 'eh-connection-string' // pragma: allowlist secret
              }
              {
                name: 'AMPLIHACK_EH_NAME'
                value: ehShardsHubName
              }
              {
                name: 'AMPLIHACK_EH_EVENTS_HUB'
                value: ehEventsHubName
              }
              {
                name: 'AMPLIHACK_EH_RESPONSES_HUB'
                value: ehResponsesHubName
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
output containerAppNames array = [for appIdx in range(0, appCount): '${hiveName}-app-${appIdx}']
output ehNamespaceName string = ehNamespaceName
output ehEventsHubName string = ehEventsHubName
output ehShardsHubName string = ehShardsHubName
output ehResponsesHubName string = ehResponsesHubName
output ehConnectionStringSecretName string = 'eh-connection-string'
