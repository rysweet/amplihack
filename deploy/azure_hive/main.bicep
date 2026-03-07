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


// ---------- Naming ----------
var suffix = uniqueString(resourceGroup().id)
var acrNameResolved = empty(acrName) ? 'acr${suffix}' : acrName
var logAnalyticsName = 'hive-logs-${suffix}'
var envName = 'hive-env-${hiveName}'
var sbNamespaceName = 'hive-sb-prem-${suffix}'
var sbTopicName = 'hive-graph'
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


// ---------- Service Bus (Premium for production workloads) ----------
resource sbNamespace 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: sbNamespaceName
  location: location
  sku: {
    name: 'Premium'
    tier: 'Premium'
    capacity: 1
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
        ]
        registries: [
          {
            server: '${acrNameResolved}.azurecr.io'
            username: acrCredentials.username
            passwordSecretRef: 'acr-password'
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
                secretRef: 'sb-connection-string'
              }
              {
                name: 'AMPLIHACK_MEMORY_STORAGE_PATH'
                value: '/data/agent-${appIdx * agentsPerApp + agentOffset}'
              }
              {
                name: 'ANTHROPIC_API_KEY'
                secretRef: 'anthropic-api-key'
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
