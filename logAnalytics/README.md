# Fabric Monitoring Solution for Azure Log Analytics

A comprehensive monitoring solution that collects data from Microsoft Fabric REST APIs and sends it to Azure Log Analytics for analysis, alerting, and dashboarding.

**🚀 Complete Solution**: Infrastructure deployment + Data collection notebooks + Environment setup

## 📊 Monitoring Capabilities

This solution provides end-to-end monitoring for:
- **Pipeline & Dataflow Executions**: Success/failure rates, performance metrics, activity runs
- **Dataset Refresh Operations**: Refresh status, duration, error tracking, metadata
- **User Activity Tracking**: Access patterns, usage analytics, security monitoring  
- **Capacity Utilization**: Resource consumption, workload distribution, throttling events

## 📁 Solution Components

### 🔧 **Data Collection Notebooks** (`/notebooks/`)
| Notebook | Purpose | Key Features |
|----------|---------|--------------|
| `fabric_pipeline_dataflow_collector.ipynb` | **Pipeline & Dataflow Monitoring** | Activity runs, performance metrics, error tracking |
| `fabric_dataset_refresh_monitoring.ipynb` | **Dataset Refresh Operations** | Refresh history, metadata collection, auto-discovery |
| `fabric_user_activity_monitoring.ipynb` | **User Activity Tracking** | Access logs, usage patterns, security monitoring |
| `fabric_capacity_utilization_monitoring.ipynb` | **Capacity & Workload Monitoring** | Resource utilization, throttling, workload distribution |

### 🏗️ **Infrastructure Deployment**
| Component | Technology | Purpose |
|-----------|------------|---------|
| `/bicep/main.bicep` | **Bicep** | Log Analytics workspace, DCR, custom tables |
| `/terraform/main.tf` | **Terraform** | Complete infrastructure with Azure provider |
| `/bicep/tables-module.bicep` | **Bicep Module** | Custom Log Analytics table definitions |

### ⚙️ **Environment Setup**
| File | Purpose |
|------|---------|
| `setup_fabric_environment.bat` | Python environment setup with runtime selection |
| `requirements-fabric-1.2.txt` / `requirements-fabric-1.3.txt` | Package dependencies for different Fabric runtimes |
| `validate_environment.ipynb` | Environment validation and connectivity testing |
| `.env.example` | Environment variables template |

### 📋 **Custom Log Analytics Tables**
The solution creates these custom tables in Log Analytics:
- `FabricPipelineRun_CL` - Pipeline execution data
- `FabricPipelineActivityRun_CL` - Detailed activity run information  
- `FabricDataflowRun_CL` - Dataflow execution data
- `FabricDatasetRefresh_CL` - Dataset refresh operations
- `FabricDatasetMetadata_CL` - Dataset configuration and metadata
- `FabricUserActivity_CL` - User activity and access logs
- `FabricCapacityMetrics_CL` - Capacity utilization metrics
- `FabricCapacityWorkloads_CL` - Workload distribution data

## 🚀 Quick Start

### 1. **Deploy Infrastructure**

**Option A: Using Bicep**
```bash
# Deploy Log Analytics workspace and DCR
az deployment group create \
  --resource-group <your-rg> \
  --template-file bicep/main.bicep \
  --parameters @bicep/params.json
```

**Option B: Using Terraform**
```bash
# Initialize and deploy
cd terraform/
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply
```

### 2. **Set Up Environment**

**For Local Development:**
```bash
# Set up Python environment
setup_fabric_environment.bat

# Configure credentials
copy .env.example .env
# Edit .env with your values

# Validate setup
# Run validate_environment.ipynb
```

**For Microsoft Fabric:**
1. Upload notebooks to your Fabric workspace
2. Configure authentication (environment variables or Key Vault)
3. Mark parameter cells for dynamic execution

### 3. **Configure Authentication**

Set these environment variables in your `.env` file:
```bash
# Required
FABRIC_TENANT_ID=your-tenant-id
FABRIC_APP_ID=your-service-principal-id  
FABRIC_APP_SECRET=your-service-principal-secret
FABRIC_WORKSPACE_ID=your-fabric-workspace-id

# Log Analytics & DCR (from infrastructure deployment)
DCR_ENDPOINT_HOST=your-dcr-endpoint.monitor.azure.com
DCR_IMMUTABLE_ID=dcr-xxxxxxxxxxxxxxxxxxxxxxxx

# Optional: Key Vault (recommended for production)
AZURE_KEY_VAULT_URI=https://your-keyvault.vault.azure.net/
AZURE_KEY_VAULT_SECRET_NAME=FabricServicePrincipal
```

### 4. **Run Monitoring**

Execute the notebooks based on your monitoring needs:
- **Start with**: `fabric_pipeline_dataflow_collector.ipynb` (most comprehensive)
- **For dataset monitoring**: `fabric_dataset_refresh_monitoring.ipynb`
- **For user analytics**: `fabric_user_activity_monitoring.ipynb`  
- **For capacity monitoring**: `fabric_capacity_utilization_monitoring.ipynb`

## 🔐 Authentication Methods

The solution supports multiple authentication approaches:

### **1. Environment Variables** *(Simple - Local Development)*
```python
use_key_vault = False
# Uses FABRIC_APP_SECRET from environment
```

### **2. Azure Key Vault + Managed Identity** *(Recommended - Production)*
```python
use_key_vault = True
use_managed_identity = True
# Perfect for Azure VMs, Container Apps, Function Apps
```

### **3. Azure Key Vault + Service Principal** *(Hybrid)*
```python
use_key_vault = True
use_managed_identity = False
# Uses Key Vault but authenticates with service principal
```

### **4. Fabric Workspace Identity** *(Fabric Runtime)*
- Automatically detected when running in Fabric
- Uses built-in `notebookutils.credentials` when available

## 📊 Sample KQL Queries

Once data is flowing, use these queries in Log Analytics:

**Pipeline Success Rate:**
```kql
FabricPipelineRun_CL
| where TimeGenerated > ago(7d)
| summarize 
    Total = count(),
    Successful = countif(Status == "Succeeded"),
    Failed = countif(Status == "Failed")
| extend SuccessRate = round(100.0 * Successful / Total, 2)
```

**Dataset Refresh Performance:**
```kql
FabricDatasetRefresh_CL
| where TimeGenerated > ago(24h) and isnotnull(DurationMs)
| summarize 
    AvgDuration = avg(DurationMs/1000),
    P95Duration = percentile(DurationMs/1000, 95)
    by DatasetName
| order by AvgDuration desc
```

**User Activity Trends:**
```kql
FabricUserActivity_CL
| where TimeGenerated > ago(30d)
| summarize ActivityCount = count() by 
    UserId, 
    bin(TimeGenerated, 1d)
| render timechart
```

## 🔧 Configuration Options

### **Lookback Windows**
- **Pipeline/Dataflow**: 1200 minutes (20 hours) for regular monitoring
- **Dataset Refresh**: 24 hours for recent operations
- **User Activity**: 24 hours for recent access patterns
- **Capacity**: 24 hours with 15-minute intervals

### **Data Collection Modes**
- **Incremental**: Short lookback for regular scheduled runs
- **Bulk**: Large lookback for historical data collection
- **Activity Runs**: Detailed activity monitoring (can be disabled for large volumes)

### **Auto-Discovery**
All notebooks support auto-discovery:
- **Workspaces**: Leave `workspace_ids = []` to monitor all accessible workspaces
- **Datasets**: Leave `dataset_ids = []` to monitor all datasets
- **Capacities**: Leave `capacity_ids = []` to monitor all accessible capacities

## 📋 Prerequisites

### **Service Principal Permissions**
- **Fabric API**: `Fabric.ReadAll` application permission
- **Azure Monitor**: `Monitoring Metrics Publisher` role on DCR
- **Key Vault** *(if used)*: `Key Vault Secrets User` role

### **Required Azure Resources**
- Azure Log Analytics workspace
- Data Collection Rule (DCR) with custom streams
- Data Collection Endpoint (DCE)
- Service Principal with appropriate permissions

### **Fabric Requirements**
- Microsoft Fabric workspace with appropriate access
- Pipelines, dataflows, or datasets to monitor
- Fabric capacity (for capacity monitoring)

## 🚨 Troubleshooting

### **Empty Log Analytics Tables**
1. **Wait 10-15 minutes** - ingestion delay is normal
2. **Check DCR configuration** - ensure streams match notebook configuration
3. **Verify permissions** - service principal needs DCR write access
4. **Check data collection summary** - notebooks show ingestion results

### **Authentication Errors**
1. **Verify service principal permissions** in Azure AD
2. **Check tenant ID and client ID** in environment variables
3. **Test Key Vault access** if using Key Vault authentication
4. **Ensure admin consent** granted for Fabric API permissions

### **API Rate Limits**
1. **Reduce lookback window** for bulk collections
2. **Disable activity runs** for pipeline monitoring during bulk loads
3. **Spread execution times** across different notebooks
4. **Monitor API response times** and adjust accordingly

## 🔄 Regular Maintenance

### **Scheduled Execution**
- Set up **Fabric pipelines** or **Azure Logic Apps** for regular execution
- **Recommended frequency**: Every 2-4 hours for incremental monitoring
- **Bulk updates**: Weekly or monthly for historical analysis

### **Monitoring Health**
- Set up **Log Analytics alerts** for failed ingestions
- Monitor **DCR ingestion quotas** and costs
- Track **API rate limit usage** across all notebooks

### **Performance Optimization**
- Adjust **lookback windows** based on data volume
- Use **dataset/workspace filtering** for targeted monitoring
- Consider **parallel execution** for large environments

---

**📅 Last Updated**: September 2025
**🔧 Version**: v2.0 - Streamlined 5-cell architecture with auto-discovery
**📚 Documentation**: See individual notebook README files for detailed configuration

**💡 Need Help?** Check the troubleshooting sections in individual notebooks or create an issue in the repository.

Choose your authentication method based on your deployment environment:

### Option 1: Environment Variables (Recommended for Local Development)

Create a `.env` file in your workspace root with:

```env
FABRIC_TENANT_ID=your-tenant-id
FABRIC_APP_ID=your-app-id  
FABRIC_APP_SECRET=your-app-secret
DCR_ENDPOINT_HOST=your-dce-endpoint.region.ingest.monitor.azure.com
DCR_IMMUTABLE_ID=your-dcr-immutable-id
FABRIC_WORKSPACE_ID=your-workspace-id
```

### Option 2: Key Vault with Managed Identity (Recommended for Production)

Best for Azure VMs, Container Apps, Function Apps, and Fabric workspaces:

```python
# Configure in notebook parameters cell
use_key_vault = True
use_managed_identity = True  # No client secret needed!
```

Store secrets in Key Vault with these names:
- `TenantId`: Azure tenant ID
- `ClientId`: Service principal client ID
- `ClientSecret`: Service principal client secret
- `DCREndpointHost`: DCR endpoint host
- `DCRImmutableId`: DCR immutable ID

### Option 3: Key Vault with Client Secret

For environments where managed identity is not available:

```python
# Configure in notebook parameters cell
use_key_vault = True
use_managed_identity = False
key_vault_uri = "https://your-keyvault.vault.azure.net/"
```

**Note**: This approach has a circular dependency where the service principal needs a secret to authenticate to Key Vault to retrieve the same secret.

### Option 4: Direct Configuration (Not Recommended for Production)

Set credentials directly in the parameters cell:

```python
# Configure in notebook parameters cell
tenant_id = "your-tenant-id"
client_id = "your-app-id"
client_secret_env = "your-app-secret"
```

**Security Risk**: Credentials are visible in the notebook and version control.

## Required Permissions

### Service Principal Permissions
- **Fabric API**: `Fabric.ReadAll` application permission
- **Azure Monitor**: `Monitoring Metrics Publisher` role on the DCR
- **Key Vault**: `Key Vault Secrets User` role on the Key Vault scope (if using Key Vault)

### Azure Role Assignments
- Assign the service principal the `Monitoring Metrics Publisher` role on the Data Collection Rule
- For Key Vault access, assign `Key Vault Secrets User` role on the Key Vault resource

## Configuration Parameters

### Workspace and Item Configuration
- **workspace_id**: Target Fabric workspace ID (auto-detected in Fabric)
- **pipeline_item_ids**: List of specific pipeline IDs to monitor (empty list monitors all)
- **dataflow_item_ids**: List of specific dataflow IDs to monitor (empty list monitors all)

### Collection Modes

#### Bulk Ingestion Mode (Historical Data)
```python
lookback_minutes = 43200  # 30 days
collect_activity_runs = False  # Disabled to avoid API limits
```

#### Incremental Collection Mode (Regular Monitoring)
```python
lookback_minutes = 1200  # 20 hours
collect_activity_runs = True  # Enabled for detailed insights
```

#### Activity Runs Backfill Mode
```python
lookback_minutes = 10080  # 7 days
collect_activity_runs = True  # Enabled for detailed data
```

### Data Collection Endpoint Configuration
- **dcr_endpoint_host**: Your Data Collection Endpoint hostname
- **dcr_immutable_id**: Your Data Collection Rule immutable ID
- **stream_pipeline**: Custom stream name for pipeline data
- **stream_activity**: Custom stream name for activity data
- **stream_dataflow**: Custom stream name for dataflow data

## Log Analytics Tables

This notebook creates and populates the following Log Analytics tables:

| Table Name | Description | Key Fields |
|------------|-------------|------------|
| `FabricPipelineRun_CL` | Pipeline execution logs | Status, Duration, ItemName, WorkspaceName |
| `FabricDataflowRun_CL` | Dataflow execution logs | Status, Duration, ItemName, WorkspaceName |
| `FabricPipelineActivityRun_CL` | Activity-level execution details | ActivityType, Status, Duration, ErrorDetails |

## Troubleshooting

### Common Issues

#### Authentication Failures
- Verify service principal credentials and permissions
- Check that the service principal has the required API permissions
- Ensure proper role assignments on Azure resources

#### Data Collection Issues
- Verify DCR endpoint and immutable ID are correct
- Check that the service principal has `Monitoring Metrics Publisher` role on the DCR
- Validate network connectivity to Azure Monitor endpoints

#### Environment Issues
- Run `validate_environment.ipynb` to check configuration
- Verify all required environment variables are set
- Check Python package dependencies are installed

### Performance Considerations
- Use appropriate lookback windows to balance completeness and performance
- Monitor API rate limits when collecting large datasets
- Consider running during off-peak hours for large historical collections

### Security Best Practices
- Use managed identity in production environments
- Store secrets in Azure Key Vault
- Apply principle of least privilege for service principal permissions
- Regular rotation of authentication credentials

## Sample KQL Queries

### Pipeline Success Rate
```kql
FabricPipelineRun_CL
| where TimeGenerated >= ago(24h)
| summarize 
    Total = count(),
    Success = countif(Status == "Completed"),
    Failed = countif(Status == "Failed")
| extend SuccessRate = (Success * 100.0) / Total
```

### Pipeline Performance Analysis
```kql
FabricPipelineRun_CL
| where TimeGenerated >= ago(7d)
| where Status == "Succeeded"
| summarize AvgDuration = avg(DurationMs) by ItemId
| order by AvgDuration desc
```

### Failed Pipeline Analysis
```kql
FabricPipelineRun_CL
| where TimeGenerated >= ago(24h)
| where Status == "Failed"
| project TimeGenerated, ItemId, WorkspaceId, ErrorMessage
| order by TimeGenerated desc
```

## Integration with Other Tools

### Power BI Dashboard
Create operational dashboards using the collected data in Log Analytics as a data source.

### Azure Alerts
Set up automated alerts based on pipeline failures or performance degradation.

### Fabric Data Activator
Use collected data to trigger automated responses to operational events.
