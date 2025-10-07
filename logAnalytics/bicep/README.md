# Bicep Deployment for Fabric Log Analytics

This Bicep template deploys the Azure infrastructure required for Fabric monitoring with Log Analytics.

## What Gets Deployed

### Core Resources
- **Data Collection Endpoint (DCE)**: Receives log data from the notebooks
- **Data Collection Rule (DCR)**: Defines custom streams and routing to Log Analytics

### What Does NOT Get Deployed
- ❌ **Log Analytics Tables**: Tables are automatically created when data is first ingested
- ❌ **Log Analytics Workspace**: Must exist before running this deployment

## Prerequisites

1. **Existing Log Analytics Workspace**: The workspace must already exist
2. **Azure CLI or PowerShell**: For deployment
3. **Proper Permissions**: Contributor access to the resource group

## Deployment

### Option 1: Azure CLI
```bash
az deployment group create \
  --resource-group your-resource-group \
  --template-file deploy-LA-DCR.bicep \
  --parameters @params.json
```

### Option 2: PowerShell
```powershell
New-AzResourceGroupDeployment `
  -ResourceGroupName "your-resource-group" `
  -TemplateFile "deploy-LA-DCR.bicep" `
  -TemplateParameterFile "params.json"
```

## Configuration

Update `params.json` with your values:

```json
{
  "lawId": {
    "value": "/subscriptions/{subscription-id}/resourceGroups/{rg}/providers/Microsoft.OperationalInsights/workspaces/{workspace-name}"
  },
  "location": { "value": "westus3" },
  "dceName": { "value": "fabric-logs-dce" },
  "dcrName": { "value": "fabric-logs-dcr" }
}
```

## Custom Streams Created

The DCR creates these custom streams for data ingestion:

| Stream Name | Purpose | Target Table |
|-------------|---------|--------------|
| `Custom-FabricPipelineRun_CL` | Pipeline execution logs | `FabricPipelineRun_CL` |
| `Custom-FabricPipelineActivityRun_CL` | Activity execution details | `FabricPipelineActivityRun_CL` |
| `Custom-FabricDataflowRun_CL` | Dataflow execution logs | `FabricDataflowRun_CL` |
| `Custom-FabricUserActivity_CL` | User activity tracking | `FabricUserActivity_CL` |
| `Custom-FabricDatasetRefresh_CL` | Dataset refresh monitoring | `FabricDatasetRefresh_CL` |
| `Custom-FabricCapacityMetrics_CL` | Capacity utilization | `FabricCapacityMetrics_CL` |

## Table Auto-Creation

✅ **Tables are automatically created** when:
1. Notebooks send their first data to the DCR endpoints
2. Azure Monitor validates the data against the stream schema
3. Corresponding `_CL` tables are created in Log Analytics

This approach:
- ✅ Simplifies deployment (no table management needed)
- ✅ Ensures schema consistency between DCR and tables
- ✅ Follows Azure Monitor best practices

## Optional: Manual Table Creation

If you need to pre-create tables (e.g., for custom retention), you can use the `tables-module.bicep`:

```bash
# Deploy only the tables module
az deployment group create \
  --resource-group your-log-analytics-rg \
  --template-file tables-module.bicep \
  --parameters lawName="your-workspace-name"
```

**Note**: This is rarely needed for normal operations.

## Outputs

The deployment provides these outputs for use in notebooks:

- `dcrImmutableId`: Required for the notebooks' DCR configuration

## Next Steps

1. ✅ Deploy this Bicep template
2. ✅ Note the `dcrImmutableId` from the deployment output
3. ✅ Configure the notebooks with the DCR details
4. ✅ Run the notebooks to start data collection
5. ✅ Verify tables are created automatically in Log Analytics

## Troubleshooting

### Common Issues

**DCR Deployment Fails**
- Verify the Log Analytics workspace ID is correct
- Ensure you have proper permissions on both resource groups

**Tables Not Created**
- Run the notebooks - tables are created on first data ingestion
- Check notebook authentication and DCR configuration

**Permission Errors**
- Assign `Monitoring Metrics Publisher` role to your service principal on the DCR
- Ensure proper API permissions for Fabric access
