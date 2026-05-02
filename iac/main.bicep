targetScope = 'resourceGroup'

param location string = resourceGroup().location
param webAppName string = 'app-monitoring-es-iac'
param appServicePlanName string = 'asp-monitoring-es-iac'
param appServiceSku string = 'B1'
param postgresServerName string = 'pg-monitoring-es-iac'
param dbAdminUser string = 'pgadminbisera'

@secure()
param dbAdminPassword string

param appPrivateEndpointName string = 'pe-app-monitoring-es-iac'
param dbPrivateEndpointName string = 'pe-pg-monitoring-es-iac'
param appPrivateEndpointSubnetId string
param dbPrivateEndpointSubnetId string

module postgres './modules/postgres.bicep' = {
  name: 'deployPostgres'
  params: {
    location: location
    postgresServerName: postgresServerName
    dbAdminUser: dbAdminUser
    dbAdminPassword: dbAdminPassword
  }
}

module appservice './modules/appservice.bicep' = {
  name: 'deployAppService'
  params: {
    location: location
    webAppName: webAppName
    appServicePlanName: appServicePlanName
    appServiceSku: appServiceSku
    dbHost: postgres.outputs.postgresHost
    dbName: 'postgres'
    dbUser: dbAdminUser
    dbPassword: dbAdminPassword
    dbPort: '5432'
  }
}

module appPrivateEndpoint './modules/privateendpoint.bicep' = {
  name: 'deployAppPrivateEndpoint'
  params: {
    privateEndpointName: appPrivateEndpointName
    location: location
    subnetId: appPrivateEndpointSubnetId
    targetResourceId: appservice.outputs.webAppId
    groupId: 'sites'
    privateDnsZoneName: 'privatelink.azurewebsites.net'
  }
}

module dbPrivateEndpoint './modules/privateendpoint.bicep' = {
  name: 'deployDbPrivateEndpoint'
  params: {
    privateEndpointName: dbPrivateEndpointName
    location: location
    subnetId: dbPrivateEndpointSubnetId
    targetResourceId: postgres.outputs.postgresId
    groupId: 'postgresqlServer'
    privateDnsZoneName: 'privatelink.postgres.database.azure.com'
  }
}

output webAppUrl string = 'https://${webAppName}.azurewebsites.net'
output postgresHost string = postgres.outputs.postgresHost
