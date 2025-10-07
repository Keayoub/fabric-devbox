# Terraform Deployment for Fabric Log Analytics

This Terraform configuration deploys the complete Azure infrastructure required for Fabric monitoring with Log Analytics using **automatic table creation**.

## What Gets Deployed

### Core Infrastructure
1. **Resource Group**: Container for all resources
2. **Log Analytics Workspace**: Central log storage and analytics
3. **Data Collection Endpoint (DCE)**: Receives log data from notebooks
4. **Data Collection Rule (DCR)**: Defines custom streams and routing (without dataFlows for auto-table creation)

### What Does NOT Get Deployed (By Design)
- ❌ **Log Analytics Tables**: Tables are automatically created when data is first ingested
- ❌ **Manual Table Schemas**: Azure Monitor creates optimal schemas based on DCR stream definitions

## Prerequisites

1. **Azure CLI**: For authentication and deployment
2. **Terraform**: Version 1.0 or higher
3. **Proper Permissions**: Contributor access to the subscription

## Quick Start

### 1. Initialize Terraform
```bash
terraform init
```

### 2. Plan Deployment
```bash
terraform plan
```

### 3. Deploy Infrastructure
```bash
terraform apply
```

### 4. Note the Outputs
After deployment, note these important outputs for your notebooks:
- `data_collection_rule_immutable_id`: Required for notebook DCR configuration
- `data_collection_endpoint_logs_ingestion_endpoint`: DCE endpoint URL

## Configuration Variables

You can customize the deployment by modifying these variables in `main.tf`:

```hcl
variable "resource_group_name" {
  default = "fabric-loganalytics-rg"
}

variable "location" {
  default = "Canada Central"
}

variable "log_analytics_workspace_name" {
  default = "fabric-laworkspace"
}

variable "data_collection_endpoint_name" {
  default = "fabric-dce"
}

variable "data_collection_rule_name" {
  default = "fabric-dcr"
}
```

## Automatic Table Creation

### ✅ **How It Works:**
1. **DCR defines custom streams** without dataFlows to avoid table dependency
2. **Notebooks send data** to DCR endpoints using the Logs Ingestion API
3. **Azure Monitor validates** data against stream schemas
4. **Tables auto-create** with optimal schemas (`FabricPipelineRun_CL`, etc.)
5. **Data gets ingested** into the new tables

### ✅ **Benefits:**
- **Simpler deployment**: No table management needed
- **Schema consistency**: Tables match DCR stream definitions exactly
- **Azure best practices**: This is how custom logs are designed to work
- **Reduced complexity**: Less infrastructure code to maintain

## Custom Streams Available

| Stream Name | Purpose | Auto-Created Table |
|-------------|---------|-------------------|
| `Custom-FabricPipelineRun_CL` | Pipeline execution logs | `FabricPipelineRun_CL` |
| `Custom-FabricPipelineActivityRun_CL` | Activity execution details | `FabricPipelineActivityRun_CL` |
| `Custom-FabricDataflowRun_CL` | Dataflow execution logs | `FabricDataflowRun_CL` |
| `Custom-FabricUserActivity_CL` | User activity tracking | `FabricUserActivity_CL` |
| `Custom-FabricAccessRequests_CL` | Access request monitoring | `FabricAccessRequests_CL` |
| `Custom-FabricDatasetRefresh_CL` | Dataset refresh monitoring | `FabricDatasetRefresh_CL` |
| `Custom-FabricDatasetMetadata_CL` | Dataset metadata tracking | `FabricDatasetMetadata_CL` |
| `Custom-FabricCapacityMetrics_CL` | Capacity utilization | `FabricCapacityMetrics_CL` |
| `Custom-FabricCapacityWorkloads_CL` | Capacity workload tracking | `FabricCapacityWorkloads_CL` |
| `Custom-FabricCapacityThrottling_CL` | Capacity throttling events | `FabricCapacityThrottling_CL` |

## Next Steps

1. ✅ **Deploy this Terraform configuration**
2. ✅ **Note the DCR immutable ID from outputs**
3. ✅ **Configure notebooks with DCR details**
4. ✅ **Run notebooks to start data collection**
5. ✅ **Verify tables are created automatically in Log Analytics**

## Quick Setup with Parameter File

### 1. Configure Variables

Copy and customize the parameter file:

```cmd
copy terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and set your values:

```hcl
# Required: Your service principal object ID
service_principal_object_id = "12345678-1234-1234-1234-123456789abc"

# Optional: Customize names and location
location                      = "East US"
resource_group_name          = "rg-fabric-monitoring"
log_analytics_workspace_name = "law-fabric-monitoring"
```

### 2. Deploy with Parameter File

```cmd
terraform init
terraform plan
terraform apply
```

## Manual Deployment (Alternative)

If you prefer to specify variables manually:

To grant the required permissions to your existing service principal, provide its Object ID:

```bash
terraform apply -var="service_principal_object_id=your-service-principal-object-id"
```

### How to Get Your Service Principal Object ID

#### Option 1: Azure Portal

1. Go to **Azure Active Directory** → **Enterprise Applications**
2. Find your service principal
3. Copy the **Object ID** from the Overview page

#### Option 2: Azure CLI

```bash
# By display name
az ad sp list --display-name "your-service-principal-name" --query "[0].id" -o tsv

# By client ID (application ID)
az ad sp show --id "your-client-id" --query "id" -o tsv
```

#### Option 3: PowerShell

```powershell
# By display name
(Get-AzADServicePrincipal -DisplayName "your-service-principal-name").Id

# By client ID
(Get-AzADServicePrincipal -ServicePrincipalName "your-client-id").Id
```

### Required Permissions Summary

Your service principal needs these permissions:

- **DCR Access**: `Monitoring Metrics Publisher` role on the Data Collection Rule (assigned by Terraform)
- **Fabric API**: `Tenant.Read.All` permission for Microsoft Fabric Service (configure manually)
- **Microsoft Graph**: `User.Read` permission (basic access)

### Manual API Permission Setup

After deployment, you still need to configure Fabric API permissions manually:

1. Go to **Azure Active Directory** → **App registrations**
2. Find your application
3. Go to **API permissions**
4. **Add a permission** → **Power BI Service**
5. Select **Application permissions** → **Tenant.Read.All**
6. **Grant admin consent**

## File Structure

```
logAnalytics/
├── common/
│   └── dcr-template.json          # Shared DCR ARM template (used by both Bicep and Terraform)
├── bicep/
│   ├── deploy-LA-DCR.bicep        # Bicep deployment file
│   └── tables-module.bicep        # Table creation module  
├── terraform/
│   ├── main.tf                    # Terraform infrastructure
│   ├── terraform.tfvars           # Your configuration
│   └── README.md                  # This file
└── notebooks/                     # Python notebooks for data collection
```

## Template Sharing

Both Bicep and Terraform deployments use the same DCR template (`common/dcr-template.json`) to ensure consistency between deployment methods.

## Troubleshooting

### **DCR Deployment Issues**
- Verify Log Analytics workspace exists and is accessible
- Check Azure permissions for creating monitoring resources

### **Tables Not Appearing**
- Tables are created only when notebooks send data
- Run a notebook to trigger table creation
- Check DCR configuration in notebooks

### **Authentication Issues**
- Assign `Monitoring Metrics Publisher` role to service principal on the DCR
- Verify Fabric API permissions for data collection

## Architecture

```
Fabric Notebooks → DCE → DCR (Stream Validation) → Auto-Created Tables → Log Analytics Workspace
```

This approach follows Azure Monitor best practices and provides the cleanest deployment experience.

## What Gets Deployed

### Core Infrastructure
- **Resource Group**: Container for all monitoring resources
- **Log Analytics Workspace**: Central log storage and querying
- **Data Collection Endpoint (DCE)**: Secure ingestion endpoint for log data
- **Data Collection Rule (DCR)**: Defines data collection and routing rules

### Custom Log Streams
The deployment includes custom streams specifically for the `fabric_LA_collector.ipynb` notebook:

| Stream Name | Purpose | Target Table |
|-------------|---------|--------------|
| `Custom-FabricPipelineRun_CL` | Pipeline execution logs | `FabricPipelineRun_CL` |
| `Custom-FabricPipelineActivityRun_CL` | Activity-level execution details | `FabricPipelineActivityRun_CL` |
| `Custom-FabricDataflowRun_CL` | Dataflow execution logs | `FabricDataflowRun_CL` |

## Prerequisites

1. **Azure CLI**: Ensure Azure CLI is installed and authenticated
   ```cmd
   az login
   az account set --subscription "your-subscription-id"
   ```

2. **Terraform**: Install Terraform and initialize the configuration
   ```cmd
   terraform init
   ```

3. **PowerShell**: Required for the custom streams deployment script

## Deployment Steps

### 1. Plan the Deployment
```cmd
terraform plan
```

### 2. Deploy Infrastructure
```cmd
terraform apply -auto-approve
```

This will:
- Create the base infrastructure (Resource Group, Log Analytics, DCE, DCR)
- Automatically deploy custom streams using the ARM template via PowerShell script

### 3. Verify Deployment
```cmd
terraform output
```

Expected outputs:
- `data_collection_rule_immutable_id`: Use this in your notebook configuration
- `data_collection_endpoint_logs_ingestion_endpoint`: Use this for the DCR endpoint host
- `log_analytics_workspace_id`: Your workspace ID for monitoring

## Manual Custom Streams Deployment

If the automatic deployment fails, you can manually deploy the custom streams:

### Using PowerShell (Recommended)
```powershell
.\deploy-custom-streams.ps1
```

### Using Batch Script
```cmd
deploy-custom-streams.bat
```

### Using Azure CLI Directly
```cmd
az deployment group create ^
  --resource-group fabric-loganalytics-rg ^
  --template-file update-dcr-custom-streams.json ^
  --parameters dataCollectionRuleName=fabric-dcr ^
               logAnalyticsWorkspaceId="/subscriptions/your-sub/resourceGroups/fabric-loganalytics-rg/providers/Microsoft.OperationalInsights/workspaces/fabric-laworkspace" ^
               dataCollectionEndpointId="/subscriptions/your-sub/resourceGroups/fabric-loganalytics-rg/providers/Microsoft.Insights/dataCollectionEndpoints/fabric-dce"
```

## Configuration for Notebook

After successful deployment, configure your notebook with these values:

```python
# From terraform output data_collection_endpoint_logs_ingestion_endpoint
dcr_endpoint_host = "your-dce-endpoint.region.ingest.monitor.azure.com"

# From terraform output data_collection_rule_immutable_id  
dcr_immutable_id = "dcr-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Stream names (already configured in the notebook)
stream_pipeline = "Custom-FabricPipelineRun_CL"
stream_activity = "Custom-FabricPipelineActivityRun_CL"  
stream_dataflow = "Custom-FabricDataflowRun_CL"
```

## Troubleshooting

### Issue: Custom Streams Not Deployed
**Symptoms**: Notebook fails with stream not found errors
**Solution**: 
1. Check if PowerShell script ran successfully during `terraform apply`
2. Manually run `.\deploy-custom-streams.ps1`
3. Verify streams exist: `az monitor data-collection rule show --name fabric-dcr --resource-group fabric-loganalytics-rg`

### Issue: Authentication Errors During Deployment
**Symptoms**: `az deployment group create` fails with authentication errors
**Solution**:
1. Ensure you're logged in to Azure CLI: `az login`
2. Verify correct subscription: `az account show`
3. Check permissions: Ensure you have Contributor access to the subscription

### Issue: PowerShell Execution Policy
**Symptoms**: PowerShell script fails to run
**Solution**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue: Terraform State Issues
**Symptoms**: Terraform apply fails due to existing resources
**Solution**:
```cmd
terraform import azurerm_resource_group.log_analytics_rg /subscriptions/your-sub/resourceGroups/fabric-loganalytics-rg
```

## Customization

### Change Resource Names
Edit variables in `main.tf`:
```hcl
variable "resource_group_name" {
  default = "your-custom-rg-name"
}

variable "log_analytics_workspace_name" {
  default = "your-custom-workspace-name"
}
```

### Change Location
```hcl
variable "location" {
  default = "East US"  # Change to your preferred region
}
```

### Add Additional Streams
1. Edit `update-dcr-custom-streams.json`
2. Add new stream definitions in `streamDeclarations`
3. Add corresponding dataFlows entries
4. Redeploy: `terraform apply -auto-approve`

## Clean Up

To remove all deployed resources:
```cmd
terraform destroy -auto-approve
```

**Warning**: This will delete all data in the Log Analytics workspace and cannot be undone.

## Files in This Directory

- **`main.tf`**: Main Terraform configuration
- **`update-dcr-custom-streams.json`**: ARM template for custom DCR streams
- **`deploy-custom-streams.ps1`**: PowerShell deployment script
- **`deploy-custom-streams.bat`**: Batch deployment script (alternative)
- **`terraform.tfvars.example`**: Example variables file (optional)

## Next Steps

After successful deployment:
1. Configure authentication for your service principal
2. Assign "Monitoring Metrics Publisher" role to your service principal on the DCR
3. Update your notebook with the output values
4. Test data ingestion using the `fabric_LA_collector.ipynb` notebook
