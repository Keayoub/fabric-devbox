# Connecting Azure Machine Learning to Microsoft Fabric OneLake

## Last updated: 2025-10-07

Short, practical guidance and copy-paste examples for reading from and writing to OneLake from Azure Machine Learning (or local/dev environments). Focus is on two patterns, authentication, encoding pitfalls, networking (OAP), and a small checklist to get you started.

## TL;DR (answer in 30 seconds)

- Two common patterns:
  - Datastore-backed (register OneLake as an Azure ML datastore): simpler inside Azure ML jobs.
  - Direct SDK access (azure-storage-file-datalake / blob SDKs): more flexible across environments.
- Auth: prefer Managed Identity on Azure ML compute; fall back to Azure CLI for local dev, or Environment (service principal) for CI.
- Use full azureml:// URIs on compute clusters. Omit an explicit `Files/` prefix for datastore paths (paths are relative to `Files`).
- Watch CSV encodings (utf-8 → latin1/cp1252 → utf-16) and add retry/backoff for large writes.

---

## Who this short guide is for

- Data scientists and MLOps engineers who need to read training data from OneLake and write back artifacts (predictions, feature outputs, models).
- Engineers building CI/CD for ML where jobs must access lakehouse files outside Fabric or across environments.

If you want a full narrative, examples, and a LinkedIn post, see the companion `ARTICLES/linkedin-azureml-onelake.md` in this repo.

---

## Quick Start (3 steps)

1. Confirm the compute identity has read/write access to the lakehouse (grant lakehouse access to the managed identity or service principal).
2. Choose a pattern: datastore-backed for Azure-ML-centric workloads, or SDK for cross-environment flexibility.
3. Test with a small read (list + head) before running larger training jobs; validate encoding and allowlist/networking if OAP is present.

---

## Patterns and when to use them

1) Datastore-backed (Azure ML datastore)

- What: register OneLake as a datastore in your Azure ML workspace so jobs/datasets can reference it with azureml:// URIs.
- Pros: centralized config, simpler job code, direct integration with Azure ML datasets and DataPath.
- Cons: feature/preview differences between regions; sometimes full azureml:// URIs are required on compute.
- When to use: primarily run in Azure ML and you want a single authoritative datastore config.

1) Direct SDK access (DataLake/Blob SDKs)

- What: use DataLakeServiceClient or BlobServiceClient directly from notebooks or jobs.
- Pros: works everywhere (local dev, Azure ML, Fabric compute), easier to debug locally, no datastore preview dependency.
- Cons: you manage credentials, paths, and retries in code.
- When to use: multi-environment workflows or when you need finer control over retries/streaming.

---

## Authentication (recommended order)

1. ManagedIdentityCredential — preferred on Azure ML compute (no secrets).
2. AzureCliCredential — local developer flow (requires `az login`).
3. EnvironmentCredential / ClientSecretCredential — CI/service principal (set via environment variables or Key Vault).

Note: ensure least-privilege access: grant the compute identity only the lakehouse data access roles it needs.

---

## Data handling: encodings and retries

- CSV encodings: Files exported from Excel/Windows often use cp1252 or latin1. Implement a fallback chain when reading CSVs: utf-8 → latin1/iso-8859-1 → cp1252 → utf-16.
- Large writes: chunk output and implement exponential backoff for transient 429/5xx responses. Log correlation IDs for easier troubleshooting.
- Path conventions: when using a datastore that maps to the lakehouse `Files` folder, pass the path relative to `Files/` (e.g., `RawData/AddressData.csv`). Don’t prepend `Files/` in datastore URIs.

---

## Networking: Outbound Access Protection (OAP)

Workspace Outbound Access Protection (OAP) limits outbound connections from Fabric workspace compute (initially Spark) to an allowlist of destinations. Key points:

- OAP helps prevent data exfiltration by restricting external endpoints and other workspaces.
- If OAP is enabled, Fabric-hosted compute may be blocked from reaching OneLake or other Azure services unless the endpoints or service principals are allowlisted.
- OAP uses managed private endpoints and allowlist rules; admins may need to add hostnames, IP ranges, or service principals.

Practical options when OAP affects you:

- Work with your Fabric admin to allow the OneLake account (for example `*.dfs.fabric.microsoft.com`) and any Azure ML service principals.
- Test connectivity with a small read/list job first to validate allowlist settings.
- If Fabric-hosted ML compute is blocked by OAP, consider running training on Azure ML compute and ensuring the Azure ML compute identity is allowed or can reach OneLake via a private endpoint.

Useful references:

- Fabric announcement (GA): [Outbound Access Protection for Spark — Fabric blog](https://blog.fabric.microsoft.com/en-us/blog/workspace-outbound-access-protection-for-spark-is-now-generally-available)
- Product docs: [Workspace outbound access protection overview](https://learn.microsoft.com/en-us/fabric/security/workspace-outbound-access-protection-overview)

---

## Minimal code examples (copy/paste)

### Construct the full azureml:// URI (use on compute clusters)

```python
datastore_uri = (
    f"azureml://subscriptions/{SUBSCRIPTION_ID}/resourcegroups/{RESOURCE_GROUP}/"
    f"workspaces/{WORKSPACE_NAME}/datastores/{DATASTORE_NAME}/paths/{file_path}"
)
```

### Read a CSV with encoding fallbacks (datastore or SDK)

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

### Direct SDK example (service principal shown for clarity)

```python
from azure.identity import ClientSecretCredential
from azure.storage.filedatalake import DataLakeServiceClient
import pandas as pd
import io
import os

credential = ClientSecretCredential(
    tenant_id=os.environ["AZURE_TENANT_ID"],
    client_id=os.environ["AZURE_CLIENT_ID"],
    client_secret=os.environ["AZURE_CLIENT_SECRET"],
)

service_client = DataLakeServiceClient(
    account_url="https://<your-onelake-account>.dfs.fabric.microsoft.com",
    credential=credential
)

file_system = "<lakehouse-id>"
file_path = "Files/RawData/AddressData.csv"

file_client = service_client.get_file_client(file_system, file_path)
raw = file_client.download_file().readall()
df = pd.read_csv(io.BytesIO(raw), encoding="utf-8")

# Write back
out_bytes = df.to_csv(index=False).encode("utf-8")
new_file_client = service_client.get_file_client(file_system, "Files/Processed/AddressData_processed.csv")
new_file_client.upload_data(out_bytes, overwrite=True)
```

---

## Quick checklist

- Grant the compute identity (or service principal) read/write access to the lakehouse.
- If registering a datastore, ensure the registering principal has Contributor on the Azure ML workspace.
- Use full `azureml://` URIs on compute clusters and pass paths relative to `Files/` for datastores.
- Add a small connectivity test (list + head) to CI before running full training.
- Implement encoding fallbacks and retries/backoff for bulk writes.

---

## How I can help

- Convert notebooks into GitHub-ready notebooks with placeholders and CI checks.
- Implement a small reusable utility module (safe read/write with encoding fallbacks and retries) — I already added a minimal helper in `src/ingest/onelake_utils.py`.
- Create an Azure ML job template that reads data, runs a training step, and writes results back to OneLake.
- Add CI checks to block secrets and PII in commits.

---

If you'd like, I can now:

- Publish the LinkedIn-ready post into `ARTICLES/linkedin-azureml-onelake.md` (already present) and polish the caption.
- Add a GitHub Actions workflow to run tests on push/PR.
- Expand the utility module into a fuller ingestion client and add integration tests (behind a feature flag).

Tell me which of those you'd like next and I'll implement it.
