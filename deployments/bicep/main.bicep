@description('Student name for resource naming')
param studentName string = 'your-unique-name'

@description('Environment name')
param environment string = 'production'

// Location inherited from resource group
@description('Location for all resources')
param location string = resourceGroup().location

@description('App Service Plan SKU')
param appServicePlanSku string = 'B3'

@description('Event Hub Namespace SKU')
param eventHubSku string = 'Standard'

// Variables
var appServicePlanName = '${studentName}-plan'
var webAppName = '${studentName}-order-service'
var eventHubNamespaceName = '${studentName}-events'
var eventHubName = 'orders'

// App Service Plan
resource appServicePlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: appServicePlanSku
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

// Event Hub Namespace
resource eventHubNamespace 'Microsoft.EventHub/namespaces@2022-01-01-preview' = {
  name: eventHubNamespaceName
  location: location
  sku: {
    name: eventHubSku
    tier: eventHubSku
    capacity: 1
  }
}

// Event Hub
resource eventHub 'Microsoft.EventHub/namespaces/eventhubs@2022-01-01-preview' = {
  parent: eventHubNamespace
  name: eventHubName
  properties: {
    messageRetentionInDays: 1
    partitionCount: 1
  }
}

// Event Hub Authorization Rule
resource eventHubAuthRule 'Microsoft.EventHub/namespaces/eventhubs/authorizationrules@2022-01-01-preview' = {
  parent: eventHub
  name: 'orders-access-key'
  properties: {
    rights: [
      'Listen'
      'Send'
    ]
  }
}

// Web App
resource webApp 'Microsoft.Web/sites@2022-03-01' = {
  name: webAppName
  location: location
  kind: 'app,linux'
  properties: {
    serverFarmId: appServicePlan.id
    reserved: true
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.9'
      appCommandLine: 'uvicorn main:app --host 0.0.0.0 --port 8000'
      alwaysOn: true
      appSettings: [
        {
          name: 'EVENT_HUB_CONNECTION_STRING'
          value: eventHubAuthRule.listKeys().primaryConnectionString
        }
        {
          name: 'EVENT_HUB_NAME'
          value: eventHubName
        }
        {
          name: 'ENVIRONMENT'
          value: environment
        }
      ]
    }
  }
}

// Outputs
output webAppName string = webApp.name
output webAppUrl string = 'https://${webApp.properties.defaultHostName}'
output eventHubConnectionString string = eventHubAuthRule.listKeys().primaryConnectionString
