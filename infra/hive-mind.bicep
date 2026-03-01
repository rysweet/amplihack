// Hive Mind Infrastructure
// Provisions Azure Database for PostgreSQL Flexible Server with Apache AGE
// plus Container Apps Environment for running agents.
//
// Deploy: az deployment group create -g hive-mind-rg --template-file infra/hive-mind.bicep
//         --parameters adminPassword='<password>'

@description('Deployment name prefix')
param hiveName string = 'hivemind'

@description('Azure region')
param location string = resourceGroup().location

@description('PostgreSQL admin login')
param adminLogin string = 'hiveadmin'

@description('PostgreSQL admin password')
@secure()
param adminPassword string

@description('PostgreSQL SKU (Burstable B1ms is cheapest)')
param pgSku string = 'Standard_B1ms'

@description('PostgreSQL storage in GB')
param pgStorageGB int = 32

// ---------- PostgreSQL Flexible Server ----------

resource pgServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: '${hiveName}-pg'
  location: location
  sku: {
    name: pgSku
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: adminLogin
    administratorLoginPassword: adminPassword
    storage: {
      storageSizeGB: pgStorageGB
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

// Enable AGE extension
resource ageConfig 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-06-01-preview' = {
  parent: pgServer
  name: 'azure.extensions'
  properties: {
    value: 'AGE'
    source: 'user-override'
  }
}

resource agePreload 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-06-01-preview' = {
  parent: pgServer
  name: 'shared_preload_libraries'
  properties: {
    value: 'age'
    source: 'user-override'
  }
}

// Allow Azure services to connect
resource pgFirewall 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-06-01-preview' = {
  parent: pgServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// Create hivemind database
resource pgDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-06-01-preview' = {
  parent: pgServer
  name: 'hivemind'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// ---------- Container Apps Environment ----------

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${hiveName}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource containerEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${hiveName}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// ---------- Outputs ----------

output pgServerFqdn string = pgServer.properties.fullyQualifiedDomainName
output pgConnectionString string = 'host=${pgServer.properties.fullyQualifiedDomainName} port=5432 dbname=hivemind user=${adminLogin} password=<password> sslmode=require'
output containerEnvId string = containerEnv.id
output containerEnvName string = containerEnv.name
