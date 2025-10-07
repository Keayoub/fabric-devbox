param lawId string // required: full resourceId('/subscriptions/.../resourceGroups/{rg}/providers/Microsoft.OperationalInsights/workspaces/{workspaceName}')
param workspaceName string // required: Log Analytics Workspace name

// Parameters for DCE and DCR
param dceName string = 'fabric-logs-dce'
param dcrName string = 'fabric-logs-dcr'
param location string = resourceGroup().location

// Data Collection Endpoint (DCE)
resource dce 'Microsoft.Insights/dataCollectionEndpoints@2022-06-01' = {
  name: dceName
  location: location
  properties: {
    networkAcls: {
      publicNetworkAccess: 'Enabled'
    }
  }
}

// Create all Log Analytics custom tables using the tables module
module fabricTables 'tables-module.bicep' = {
  name: 'deployFabricTables'
  params: {
    lawName: workspaceName
  }
}

// Data Collection Rule (DCR) - Deploy using ARM template for custom streams support
// Note: DCR depends on tables being created first
module dcrModule '../common/dcr-template.json' = {
  name: 'deployDCR'
  params: {
    dcrName: dcrName
    location: location
    dceResourceId: dce.id
    lawResourceId: lawId
  }
  dependsOn: [
    fabricTables
  ]
}

output dcrImmutableId string = dcrModule.outputs.dcrImmutableId
output dceId string = dce.id
output dceLogsIngestionUri string = dce.properties.logsIngestion.endpoint
output tableNames array = [
  'FabricPipelineRun_CL'
  'FabricPipelineActivityRun_CL'
  'FabricDataflowRun_CL'
  'FabricUserActivity_CL'
  'FabricAccessRequests_CL'
  'FabricDatasetRefresh_CL'
  'FabricDatasetMetadata_CL'
  'FabricCapacityMetrics_CL'
  'FabricCapacityWorkloads_CL'
  'FabricCapacityThrottling_CL'
]
