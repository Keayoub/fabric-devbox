// OPTIONAL MODULE: Pre-create Log Analytics tables for custom logs
// 
// NOTE: This module is NOT required for normal operation.
// Tables will be automatically created by Azure Monitor when data is first ingested via the DCR.
// 
// Use this module only if you need:
// - Custom retention policies different from the default
// - Specific table configurations before data ingestion
// - Pre-defined schema validation
//
// For most use cases, let Azure Monitor auto-create the tables.

param lawName string

// The module is deployed at resource-group scope; the module's resourceGroup() will be the target RG.
resource law 'Microsoft.OperationalInsights/workspaces@2025-02-01' existing = {
  scope: resourceGroup()
  name: lawName
}

resource pipelineRun 'Microsoft.OperationalInsights/workspaces/tables@2025-02-01' = {
  parent: law
  name: 'FabricPipelineRun_CL'
  properties: {
    plan: 'Analytics'
    retentionInDays: 30
    schema: {
      name: 'FabricPipelineRun_CL'
      columns: [
        { name: 'TimeGenerated', type: 'datetime' }
        { name: 'WorkspaceId', type: 'string' }
        { name: 'ItemId', type: 'string' }
        { name: 'ItemType', type: 'string' }
        { name: 'RunId', type: 'string' }
        { name: 'PipelineName', type: 'string' }
        { name: 'TriggerType', type: 'string' }
        { name: 'Status', type: 'string' }
        { name: 'StartTimeUtc', type: 'datetime' }
        { name: 'EndTimeUtc', type: 'datetime' }
        { name: 'DurationMs', type: 'long' }
        { name: 'ErrorCode', type: 'string' }
        { name: 'ErrorMessage', type: 'string' }
      ]
    }
  }
}

resource activityRun 'Microsoft.OperationalInsights/workspaces/tables@2025-02-01' = {
  parent: law
  name: 'FabricPipelineActivityRun_CL'
  properties: {
    plan: 'Analytics'
    retentionInDays: 30
    schema: {
      name: 'FabricPipelineActivityRun_CL'
      columns: [
        { name: 'TimeGenerated', type: 'datetime' }
        { name: 'WorkspaceId', type: 'string' }
        { name: 'PipelineName', type: 'string' }
        { name: 'ActivityName', type: 'string' }
        { name: 'ActivityType', type: 'string' }
        { name: 'RunId', type: 'string' }
        { name: 'Status', type: 'string' }
        { name: 'StartTimeUtc', type: 'datetime' }
        { name: 'EndTimeUtc', type: 'datetime' }
        { name: 'DurationMs', type: 'long' }
        { name: 'RowsRead', type: 'long' }
        { name: 'RowsWritten', type: 'long' }
        { name: 'ErrorCode', type: 'string' }
        { name: 'ErrorMessage', type: 'string' }
      ]
    }
  }
}

resource dataflowRun 'Microsoft.OperationalInsights/workspaces/tables@2025-02-01' = {
  parent: law
  name: 'FabricDataflowRun_CL'
  properties: {
    plan: 'Analytics'
    retentionInDays: 30
    schema: {
      name: 'FabricDataflowRun_CL'
      columns: [
        { name: 'TimeGenerated', type: 'datetime' }
        { name: 'WorkspaceId', type: 'string' }
        { name: 'DataflowId', type: 'string' }
        { name: 'DataflowName', type: 'string' }
        { name: 'ExecutionId', type: 'string' }
        { name: 'ComputeMode', type: 'string' }
        { name: 'Status', type: 'string' }
        { name: 'StartTimeUtc', type: 'datetime' }
        { name: 'EndTimeUtc', type: 'datetime' }
        { name: 'DurationMs', type: 'long' }
        { name: 'RowsRead', type: 'long' }
        { name: 'RowsWritten', type: 'long' }
        { name: 'ErrorCode', type: 'string' }
        { name: 'ErrorMessage', type: 'string' }
      ]
    }
  }
}

resource userActivity 'Microsoft.OperationalInsights/workspaces/tables@2025-02-01' = {
  parent: law
  name: 'FabricUserActivity_CL'
  properties: {
    plan: 'Analytics'
    retentionInDays: 30
    schema: {
      name: 'FabricUserActivity_CL'
      columns: [
        { name: 'TimeGenerated', type: 'datetime' }
        { name: 'UserId', type: 'string' }
        { name: 'UserEmail', type: 'string' }
        { name: 'Activity', type: 'string' }
        { name: 'WorkspaceId', type: 'string' }
        { name: 'ItemId', type: 'string' }
        { name: 'ItemName', type: 'string' }
        { name: 'ItemType', type: 'string' }
        { name: 'OperationName', type: 'string' }
        { name: 'ActivityId', type: 'string' }
      ]
    }
  }
}

resource accessRequests 'Microsoft.OperationalInsights/workspaces/tables@2025-02-01' = {
  parent: law
  name: 'FabricAccessRequests_CL'
  properties: {
    plan: 'Analytics'
    retentionInDays: 30
    schema: {
      name: 'FabricAccessRequests_CL'
      columns: [
        { name: 'TimeGenerated', type: 'datetime' }
        { name: 'RequestId', type: 'string' }
        { name: 'RequesterUserId', type: 'string' }
        { name: 'RequesterEmail', type: 'string' }
        { name: 'WorkspaceId', type: 'string' }
        { name: 'WorkspaceName', type: 'string' }
        { name: 'RequestType', type: 'string' }
        { name: 'Status', type: 'string' }
        { name: 'ApproverUserId', type: 'string' }
        { name: 'RequestedDate', type: 'datetime' }
        { name: 'ResponseDate', type: 'datetime' }
      ]
    }
  }
}

resource datasetRefresh 'Microsoft.OperationalInsights/workspaces/tables@2025-02-01' = {
  parent: law
  name: 'FabricDatasetRefresh_CL'
  properties: {
    plan: 'Analytics'
    retentionInDays: 30
    schema: {
      name: 'FabricDatasetRefresh_CL'
      columns: [
        { name: 'TimeGenerated', type: 'datetime' }
        { name: 'WorkspaceId', type: 'string' }
        { name: 'DatasetId', type: 'string' }
        { name: 'DatasetName', type: 'string' }
        { name: 'RefreshType', type: 'string' }
        { name: 'Status', type: 'string' }
        { name: 'StartTimeUtc', type: 'datetime' }
        { name: 'EndTimeUtc', type: 'datetime' }
        { name: 'DurationMs', type: 'long' }
        { name: 'ErrorCode', type: 'string' }
        { name: 'ErrorMessage', type: 'string' }
      ]
    }
  }
}

resource datasetMetadata 'Microsoft.OperationalInsights/workspaces/tables@2025-02-01' = {
  parent: law
  name: 'FabricDatasetMetadata_CL'
  properties: {
    plan: 'Analytics'
    retentionInDays: 30
    schema: {
      name: 'FabricDatasetMetadata_CL'
      columns: [
        { name: 'TimeGenerated', type: 'datetime' }
        { name: 'WorkspaceId', type: 'string' }
        { name: 'DatasetId', type: 'string' }
        { name: 'DatasetName', type: 'string' }
        { name: 'DatasetOwner', type: 'string' }
        { name: 'CreatedDate', type: 'datetime' }
        { name: 'ModifiedDate', type: 'datetime' }
        { name: 'SizeBytes', type: 'long' }
        { name: 'TableCount', type: 'int' }
        { name: 'IsRefreshable', type: 'boolean' }
      ]
    }
  }
}

resource capacityMetrics 'Microsoft.OperationalInsights/workspaces/tables@2025-02-01' = {
  parent: law
  name: 'FabricCapacityMetrics_CL'
  properties: {
    plan: 'Analytics'
    retentionInDays: 30
    schema: {
      name: 'FabricCapacityMetrics_CL'
      columns: [
        { name: 'TimeGenerated', type: 'datetime' }
        { name: 'CapacityId', type: 'string' }
        { name: 'CapacityName', type: 'string' }
        { name: 'MetricName', type: 'string' }
        { name: 'MetricValue', type: 'real' }
        { name: 'MetricUnit', type: 'string' }
        { name: 'WorkspaceId', type: 'string' }
        { name: 'ItemId', type: 'string' }
        { name: 'Operation', type: 'string' }
      ]
    }
  }
}

resource capacityWorkloads 'Microsoft.OperationalInsights/workspaces/tables@2025-02-01' = {
  parent: law
  name: 'FabricCapacityWorkloads_CL'
  properties: {
    plan: 'Analytics'
    retentionInDays: 30
    schema: {
      name: 'FabricCapacityWorkloads_CL'
      columns: [
        { name: 'TimeGenerated', type: 'datetime' }
        { name: 'CapacityId', type: 'string' }
        { name: 'WorkloadName', type: 'string' }
        { name: 'State', type: 'string' }
        { name: 'MaxMemoryPercentage', type: 'int' }
        { name: 'MaxBackgroundRefreshes', type: 'int' }
      ]
    }
  }
}

resource capacityThrottling 'Microsoft.OperationalInsights/workspaces/tables@2025-02-01' = {
  parent: law
  name: 'FabricCapacityThrottling_CL'
  properties: {
    plan: 'Analytics'
    retentionInDays: 30
    schema: {
      name: 'FabricCapacityThrottling_CL'
      columns: [
        { name: 'TimeGenerated', type: 'datetime' }
        { name: 'CapacityId', type: 'string' }
        { name: 'WorkspaceId', type: 'string' }
        { name: 'ItemId', type: 'string' }
        { name: 'OperationType', type: 'string' }
        { name: 'ThrottlingReason', type: 'string' }
        { name: 'ThrottledTimeMs', type: 'int' }
        { name: 'BackgroundOperationId', type: 'string' }
      ]
    }
  }
}
