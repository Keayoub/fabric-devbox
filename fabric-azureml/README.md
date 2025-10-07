# Azure ML to Fabric OneLake Connection

A short, practical guide with copy-paste examples for reading from and writing to OneLake from Azure Machine Learning (or from local/dev environments). It focuses on two common patterns, authentication, encoding pitfalls, networking (OAP), and a tiny checklist to help you get started quickly.

![OneLake connection diagram](../media/Fabric-AzureML.jpeg)
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

## Companion guide: Connecting Azure ML to Microsoft Fabric OneLake

This repository includes a short companion article that summarizes practical guidance and copy-paste examples for reading from and writing to OneLake from Azure ML. The article is also available as a standalone document at `ARTICLES/azureml-onelake.md`.

### TL;DR

- Two common patterns:
  - Datastore-backed (register OneLake as an Azure ML datastore): simpler inside Azure ML jobs.
  - Direct SDK access (DataLake/Blob SDKs): more flexible across environments.
- Auth: prefer Managed Identity on Azure ML compute; use Azure CLI locally; use Environment/Service Principal for CI.
- Use full `azureml://` URIs on compute clusters. Paths for datastores are relative to `Files/` (don't include `Files/` in datastore paths).
- Watch CSV encodings (utf-8 → latin1/cp1252 → utf-16) and add retry/backoff for large writes.

### Quick start — three steps

1. Grant the compute identity read/write access to the lakehouse (managed identity or service principal).
2. Choose a pattern: datastore-backed for Azure-ML-centric workflows, or SDK for cross-environment flexibility.
3. Run a small connectivity test (list + head) before running larger training jobs to catch encoding or allowlist/OAP issues early.

### Patterns (short)

#### Datastore-backed

- Register OneLake as an Azure ML datastore and reference files with `azureml://` URIs. Good for centralized config and simpler job code. Watch for regional/preview differences.

#### Direct SDK access

- Use `DataLakeServiceClient` or `BlobServiceClient` directly. Works everywhere (local, Azure ML, Fabric compute) and is easier to debug locally, but you manage credentials and retries.

### Authentication (recommended)

1. ManagedIdentityCredential — preferred on Azure ML compute.
2. AzureCliCredential — for local development (`az login`).
3. EnvironmentCredential / ClientSecretCredential — for CI/CD.

### Encoding and reliability tips

- Try encoding fallbacks for CSVs: utf-8 → latin1/iso-8859-1 → cp1252 → utf-16.
- Chunk large writes and implement exponential backoff for 429/5xx responses. Log correlation IDs for troubleshooting.
- Paths: use folder/file relative to `Files/` (e.g., `RawData/AddressData.csv`) for datastore paths.

### Networking (OAP)

Fabric workspaces with Outbound Access Protection (OAP) may block outbound connections. If you hit connectivity issues, ask admins to allow OneLake hostnames (for example `*.dfs.fabric.microsoft.com`) and any Azure ML service principals, and run a small list/head test to validate allowlist rules.

### Minimal code examples (copy/paste)

Construct a full azureml:// URI (use on compute clusters):

```python
datastore_uri = (
  f"azureml://subscriptions/{SUBSCRIPTION_ID}/resourcegroups/{RESOURCE_GROUP}/"
  f"workspaces/{WORKSPACE_NAME}/datastores/{DATASTORE_NAME}/paths/{file_path}"
)
```

Read a CSV with encoding fallbacks:

```python
import pandas as pd

def read_with_fallback(uri_or_path):
  try:
    return pd.read_csv(uri_or_path)
  except UnicodeDecodeError:
    for enc in ["latin1", "iso-8859-1", "cp1252", "utf-16"]:
      try:
        return pd.read_csv(uri_or_path, encoding=enc)
      except Exception:
        continue
    raise

# Example: df = read_with_fallback(datastore_uri)
```

Quick checklist

- Grant the compute identity read/write access to the lakehouse.
- If registering a datastore, ensure the registering principal has Contributor on the Azure ML workspace.
- Use full `azureml://` URIs on compute clusters and pass paths relative to `Files/` for datastores.
- Add a small connectivity test (list + head) in CI before running full training.
- Implement encoding fallbacks and retries/backoff for bulk writes.

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
  --name <your-datastore-name>
    --resource-group <your-rg> \
    --workspace-name <your-workspace>
```

---

## 📋 Your Configuration

From `azml_onelakesp_datastore.yml`:

```yaml
Datastore Name:        <REDACTED_WORKSPACE_ID>
Type:                  one_lake
OneLake Workspace:     <REDACTED_WORKSPACE_ID>
Lakehouse ID:          <REDACTED_LAKEHOUSE_ID>
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

1. Go to: [Azure ML Studio](https://ml.azure.com)
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

Install from: [Install Azure CLI](https://aka.ms/installazurecliwindows)

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

1. Go to: [Microsoft Fabric portal](https://app.fabric.microsoft.com)
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
