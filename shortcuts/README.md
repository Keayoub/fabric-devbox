# Fabric Shortcut Automation

This folder contains scripts to automate the creation of Microsoft Fabric shortcuts to ADLS Gen2 containers.

## Scripts Overview

- **adlsgen2_fabric_shortcut_bulk_create.py**
  - Lists folders in an ADLS Gen2 container.
  - For each folder, creates a shortcut in the specified Fabric workspace/lakehouse using the Fabric CLI (`fab ln`).
  - Generates a `shortcuts.csv` file with all shortcut definitions processed.
  - Accepts all parameters via command-line arguments for easy automation.

- **run_shortcut_creation.py**
  - Root script to call the bulk create script with parameters.
  - Example usage:
    ```sh
    python run_shortcut_creation.py --account-url https://<account>.dfs.core.windows.net --container <container> --connection-id <connectionId> --workspace <workspace> --lakehouse <lakehouse>
    ```

## Prerequisites
- Python 3.10+
- `pip install azure-identity azure-storage-blob`
- Fabric CLI (`fab`) installed and authenticated (`fab auth login`)
- Contributor or Admin permissions on the target workspace and lakehouse

## What happens when you run the script?
- The script connects to your ADLS Gen2 container and lists all folders.
- For each folder, it creates a shortcut in Fabric and records the details in `shortcuts.csv`.
- You get both the actual shortcuts in Fabric and a CSV for record-keeping or future use.

## Customization
- You can adjust the script to only generate the CSV or only create shortcuts from an existing CSV if needed.
- All parameters can be provided via command-line for flexible automation.

## New Features

- **Recursive folder discovery:** The script can now recursively discover all folders in your ADLS Gen2 container. Use `--max-depth` to control recursion depth (or omit for unlimited depth).
- **YAML config file support:** You can provide all parameters in a YAML config file using `--config shortcut_config.yaml`. CLI arguments override config file values.
- **Parallel shortcut creation:** Use `--parallel` to set the number of parallel shortcut creations for faster processing of large data lakes.
- **Shortcut name templating:** Use `--shortcut-template` or set `shortcut_template` in your config to control how shortcut names are generated.

**Example YAML config (`shortcut_config.yaml`):**

```yaml
account_url: "https://<your-storage-account>.dfs.core.windows.net"
container: "<your-container>"
connection_id: "<your-connection-id>"
workspace: "<your-workspace>"
lakehouse: "<your-lakehouse>"
lakehouse_folder: "<target-folder>"
shortcut_type: "adlsGen2"
root_path: ""
skip_folders: "domain1/skip_this,domain2/skip_that"
max_depth: 3
parallel: 8
shortcut_template: "shortcut_{folder}"
```

**Run with config file:**

```sh
python adlsgen2_fabric_shortcut_bulk_create.py --config shortcut_config.yaml
```

**Or override any value with CLI args:**

```sh
python adlsgen2_fabric_shortcut_bulk_create.py --config shortcut_config.yaml --parallel 16 --max-depth 2
```

**You can still use all previous options, including:**
- `--lakehouse-folder` to specify the destination folder in your lakehouse
- `--skip-folders` as a comma-separated list or file

## Supported Shortcut Types

- **adlsGen2** (default):
  - Use for Azure Data Lake Storage Gen2 containers.
  - Required config: `account_url` (e.g., `https://<account>.dfs.core.windows.net`), `connection_id` (Fabric connection for ADLS Gen2).
  - Folder discovery and shortcut creation are fully automated.

- **storage** (Azure Blob Storage):
  - Use for standard Azure Blob Storage accounts.
  - Required config: `account_url` (e.g., `https://<account>.blob.core.windows.net`), `connection_id` (Fabric connection for Blob Storage).
  - Folder discovery and shortcut creation are fully automated (same logic as adlsGen2).

- **onedrive**:
  - Use for OneDrive or SharePoint document libraries.
  - Required config: `drive_id`, `item_id`, `connection_id` (Fabric connection for OneDrive/SharePoint).
  - Folder discovery is not automated; you must provide the correct IDs for the shortcut.

### How to Set the Shortcut Type

- Set globally with `--shortcut-type` on the command line or `shortcut_type` in your YAML config file.
- The script will build the correct shortcut JSON for each type.

### Example YAML Config for Storage Account

```yaml
shortcut_type: "storage"
account_url: "https://<your-storage-account>.blob.core.windows.net"
connection_id: "<your-blob-connection-id>"
workspace: "<your-workspace>"
lakehouse: "<your-lakehouse>"
lakehouse_folder: "<target-folder>"
```

### Example YAML Config for OneDrive

```yaml
shortcut_type: "onedrive"
drive_id: "<your-drive-id>"
item_id: "<your-item-id>"
connection_id: "<your-onedrive-connection-id>"
workspace: "<your-workspace>"
lakehouse: "<your-lakehouse>"
lakehouse_folder: "<target-folder>"
```

### Example YAML Config for ADLS Gen2 (default)

```yaml
shortcut_type: "adlsGen2"
account_url: "https://<your-storage-account>.dfs.core.windows.net"
connection_id: "<your-adls-connection-id>"
workspace: "<your-workspace>"
lakehouse: "<your-lakehouse>"
lakehouse_folder: "<target-folder>"
```

---

**Note:** For `adlsGen2` and `storage`, the script will automatically discover all folders (recursively, if enabled) and create shortcuts for each. For `onedrive`, you must specify the folder/item IDs manually.

For more details on the Fabric CLI, see: <https://microsoft.github.io/fabric-cli/>
