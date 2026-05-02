param location string
param webAppName string
param appServicePlanName string
param appServiceSku string
param dbHost string
param dbName string
param dbUser string

@secure()
param dbPassword string

param dbPort string

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: appServiceSku
    tier: 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

resource site 'Microsoft.Web/sites@2023-12-01' = {
  name: webAppName
  location: location
  kind: 'app,linux'
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.13'
      appSettings: [
        {
          name: 'DB_HOST'
          value: dbHost
        }
        {
          name: 'DB_NAME'
          value: dbName
        }
        {
          name: 'DB_USER'
          value: dbUser
        }
        {
          name: 'DB_PASSWORD'
          value: dbPassword
        }
        {
          name: 'DB_PORT'
          value: dbPort
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: '1'
        }
      ]
    }
  }
}

output webAppId string = site.id
output webAppNameOut string = site.name
