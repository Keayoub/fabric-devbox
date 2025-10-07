# Azure ML to Fabric OneLake Connection

Complete toolkit for connecting Azure Machine Learning to Microsoft Fabric OneLake, following the official Microsoft documentation.

## Official Documentation

This toolkit implements: [Create a OneLake (Microsoft Fabric) datastore](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-datastore?view=azureml-api-2&tabs=cli-onelake-sp#create-a-onelake-microsoft-fabric-datastore-preview)

---

## Quick Start

### Prerequisites

1. **Azure ML Workspace** - An existing Azure ML workspace
2. **Microsoft Fabric Lakehouse** - A lakehouse with data to access
3. **Service Principal** - With permissions to:
   - Azure ML workspace (Contributor or higher)
   - OneLake lakehouse (Storage Blob Data Contributor or higher)

### Setup Steps

**1. Configure Your Service Principal**

Update `azml_onelakesp_datastore.yml` with your details:

```yaml
account_name: <onelake-account-name>
endpoint: <onelake-endpoint>
container_name: <workspace-id>/<lakehouse-id>
credentials:
  tenant_id: <your-tenant-id>
  client_id: <your-client-id>
  client_secret: <your-client-secret>
```

**2. Register the Datastore**

```powershell
.\register-with-cli.ps1 -s "<subscription-id>" -g "<resource-group>" -w "<workspace-name>"
```

**3. Configure the Notebook**

Open `access_onelake_azureml.ipynb` and update the configuration:

```python
SUBSCRIPTION_ID = "<your-subscription-id>"
RESOURCE_GROUP = "<your-resource-group>"
WORKSPACE_NAME = "<your-workspace-name>"
DATASTORE_NAME = "onelakesp_datastore"
```

---

## Files in This Directory

### Registration Scripts
| File | Purpose |
|------|---------|
| `register-with-cli.ps1` | PowerShell script to register OneLake datastore |
| `azml_onelakesp_datastore.yml` | Datastore configuration template |

### Notebooks
| File | Purpose |
|------|---------|
| `access_onelake_azureml.ipynb` | Main notebook for accessing OneLake from Azure ML |

### Additional Scripts
| File | Purpose |
|------|---------|
| `register_onelake_datastore.py` | Python SDK registration script |
| `validate_datastore.py` | Connection validation tool |
| `onelake_training_examples.py` | Complete training examples |
| `ONELAKE_CONNECTION_GUIDE.md` | Comprehensive setup guide |
| `SETUP_SUMMARY.md` | Complete toolkit overview |

---

## ⚡ Manual Registration (Azure CLI)

If you prefer manual control:

```bash
# 1. Install ML extension
az extension add --name ml

# 2. Login and set subscription
az login
az account set --subscription "<your-subscription-id>"

# 3. Register datastore
az ml datastore create \
  --file azml_onelakesp_datastore.yml \
  --resource-group <your-rg> \
  --workspace-name <your-workspace>

# 4. Verify
az ml datastore show \
  --name fb53fbfb-d8e9-4797-b2f5-ba80bb9a7388 \
  --resource-group <your-rg> \
  --workspace-name <your-workspace>
```

---

## 📋 Your Configuration

From `azml_onelakesp_datastore.yml`:

```yaml
Datastore Name:        fb53fbfb-d8e9-4797-b2f5-ba80bb9a7388
Type:                  one_lake
OneLake Workspace:     fb53fbfb-d8e9-4797-b2f5-ba80bb9a7388
Lakehouse ID:          b5607519-ec4b-4a83-ac2a-5443c8887e2a
Endpoint:              msit-onelake.dfs.fabric.microsoft.com
Authentication:        Service Principal
```

---

## ✅ Prerequisites

Before running the scripts:

- [ ] **Azure CLI** installed - [Download](https://aka.ms/installazurecliwindows)
- [ ] **Azure ML CLI extension** - Automatically installed by scripts
- [ ] **Azure ML workspace** created
- [ ] **Service Principal** has permissions:
  - Azure ML workspace (Contributor role)
  - Fabric workspace (Admin or Member)
- [ ] Logged into Azure (`az login`)

---

## 🔍 Verify Registration

### In Azure ML Studio
1. Go to: https://ml.azure.com
2. Select your workspace
3. Navigate to: **Data** → **Datastores**
4. Look for: `fb53fbfb-d8e9-4797-b2f5-ba80bb9a7388`

### Via Azure CLI
```bash
az ml datastore list \
  --resource-group <your-rg> \
  --workspace-name <your-workspace> \
  --output table
```

---

## 💻 Use in Training Jobs

### Azure CLI Job
```bash
az ml job create --file job.yml
```

**job.yml:**
```yaml
$schema: https://azuremlschemas.azureedge.net/latest/commandJob.schema.json
command: python train.py --data ${{inputs.training_data}}
code: ./src
environment: azureml:AzureML-sklearn-1.0-ubuntu20.04-py38-cpu@latest
compute: azureml:cpu-cluster
inputs:
  training_data:
    type: uri_folder
    path: azureml://datastores/fb53fbfb-d8e9-4797-b2f5-ba80bb9a7388/paths/data/
```

### Python SDK
```python
from azure.ai.ml import MLClient, Input, command
from azure.ai.ml.constants import AssetTypes
from azure.identity import DefaultAzureCredential

ml_client = MLClient(
    DefaultAzureCredential(),
    subscription_id="<subscription-id>",
    resource_group_name="<resource-group>",
    workspace_name="<workspace-name>"
)

job = command(
    code="./src",
    command="python train.py --data ${{inputs.data}}",
    inputs={
        "data": Input(
            type=AssetTypes.URI_FOLDER,
            path="azureml://datastores/fb53fbfb-d8e9-4797-b2f5-ba80bb9a7388/paths/training-data/"
        )
    },
    environment="AzureML-sklearn-1.0-ubuntu20.04-py38-cpu:1",
    compute="cpu-cluster"
)

ml_client.jobs.create_or_update(job)
```

---

## 🆘 Troubleshooting

### "Azure CLI not found"
Install from: https://aka.ms/installazurecliwindows

### "Extension 'ml' not found"
```bash
az extension add --name ml
```

### "Workspace not found"
```bash
# Verify workspace exists
az ml workspace show \
  --name <workspace-name> \
  --resource-group <resource-group>

# List all workspaces
az ml workspace list --output table
```

### "Authentication failed"
```bash
# Re-login to Azure
az login

# Test service principal
az login --service-principal \
  --username f4b66b80-24d3-4498-9cdf-02f47c776315 \
  --password "Pn28Q~Rz~IMklN-wBXYE-IfVwJWfLQbhpDOLoaOW" \
  --tenant c869cf92-11d8-4fbc-a7cf-6114d160dd71
```

### "Access denied to OneLake"
1. Go to: https://app.fabric.microsoft.com
2. Open workspace: `fb53fbfb-d8e9-4797-b2f5-ba80bb9a7388`
3. Settings → Manage access
4. Add service principal: `f4b66b80-24d3-4498-9cdf-02f47c776315`
5. Role: **Admin** or **Member**

### Debug Mode
```bash
az ml datastore create \
  --file azml_onelakesp_datastore.yml \
  --resource-group <your-rg> \
  --workspace-name <your-workspace> \
  --debug
```

---

## 📖 More Information

- **Quick Reference**: See `QUICK_REFERENCE.md` for copy-paste commands
- **Comprehensive Guide**: See `ONELAKE_CONNECTION_GUIDE.md` for detailed setup
- **Complete Overview**: See `SETUP_SUMMARY.md` for all available tools
- **Training Examples**: See `onelake_training_examples.py` for usage patterns

---

## 🔗 Official Links

- [Azure ML Datastores Documentation](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-datastore)
- [Microsoft Fabric OneLake](https://learn.microsoft.com/en-us/fabric/onelake/onelake-overview)
- [Azure ML CLI v2](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-configure-cli)
- [Azure ML Python SDK v2](https://learn.microsoft.com/en-us/python/api/overview/azure/ai-ml-readme)

---

## 🎯 Next Steps

After successful registration:

1. ✅ **Verify** in Azure ML Studio
2. 📊 **Browse** your OneLake files
3. 🔧 **Create** a training script
4. 🚀 **Submit** your first job
5. 📦 **Create** reusable data assets
6. 🔒 **Secure** credentials in Key Vault

---

**Need help?** Check `QUICK_REFERENCE.md` for troubleshooting tips and examples.
