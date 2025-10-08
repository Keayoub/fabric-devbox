# Fabric Runtime Setup Scripts

This folder contains scripts for setting up Python environments compatible with Microsoft Fabric Runtime environments.

## Scripts Overview

### `setup_fabric_environment.py` 
**Primary Python Setup Script**
- Interactive Python script for creating Fabric runtime environments
- Downloads official requirements from Microsoft Synapse Spark Runtime repository
- Supports Fabric Runtime 1.2 (Python 3.10, Spark 3.4) and 1.3 (Python 3.11, Spark 3.5)
- Creates virtual environments in the project root directory
- Generates `.env.example` file with necessary environment variable templates

**Usage:**
```bash
cd setup
python setup_fabric_environment.py
```

### `setup_fabric_environment.bat`
**Windows Batch Setup Script**
- Windows-specific batch file equivalent of the Python script
- Same functionality as the Python version but optimized for Windows Command Prompt
- Automatically detects and uses appropriate Python version (3.10 or 3.11)

**Usage:**
```cmd
cd setup
setup_fabric_environment.bat
```

### `download_fabric_requirements.py`
**Requirements Downloader**
- Downloads the latest official requirements from Microsoft Synapse Spark Runtime repository
- Parses YAML files and converts them to pip-compatible requirements.txt format
- Filters packages relevant to Azure and Log Analytics integration
- Creates version-specific requirements files

**Usage:**
```bash
cd setup
python download_fabric_requirements.py
```

### `cleanup_environments.bat`
**Environment Cleanup Utility**
- Removes all created virtual environments
- Cleans up old environment directories
- Safe cleanup of `.fabric-env-*` directories

**Usage:**
```cmd
cd setup
cleanup_environments.bat
```

## Directory Structure After Setup

```
fabric-la-connector/
├── setup/                          # Setup scripts (this folder)
│   ├── setup_fabric_environment.py
│   ├── setup_fabric_environment.bat
│   ├── download_fabric_requirements.py
│   ├── cleanup_environments.bat
│   └── README.md
├── .fabric-env-1.2/                # Python 3.10 environment (if created)
├── .fabric-env-1.3/                # Python 3.11 environment (if created)  
├── .env.example                    # Environment variables template
├── requirements-fabric-1.2.txt     # Fabric 1.2 requirements (if generated)
├── requirements-fabric-1.3.txt     # Fabric 1.3 requirements (if generated)
└── ... (other project files)
```

## Quick Start

1. **Choose your preferred method:**
   - **Python**: `cd setup && python setup_fabric_environment.py`
   - **Windows Batch**: `cd setup && setup_fabric_environment.bat`

2. **Select runtime version:**
   - Runtime 1.2: Python 3.10 + Spark 3.4 (stable)
   - Runtime 1.3: Python 3.11 + Spark 3.5 (latest)

3. **Activate the environment:**
   ```bash
   # Windows
   .fabric-env-1.3\Scripts\activate.bat
   
   # Unix/Linux/macOS
   source .fabric-env-1.3/bin/activate
   ```

4. **Configure environment variables:**
   - Copy `.env.example` to `.env`
   - Fill in your Azure credentials and workspace details

5. **Start working:**
   ```bash
   jupyter notebook
   ```

## Environment Variables

The setup creates a `.env.example` file with the following required variables:

```env
# Azure AD App Registration
FABRIC_TENANT_ID=your-tenant-id-here
FABRIC_APP_ID=your-app-id-here
FABRIC_APP_SECRET=your-app-secret-here

# Azure Subscription
AZURE_SUBSCRIPTION_ID=your-subscription-id-here

# Fabric Workspace
FABRIC_WORKSPACE_ID=your-workspace-id-here

# Log Analytics
LOG_ANALYTICS_WORKSPACE_ID=your-log-analytics-workspace-id
DCR_ENDPOINT_HOST=your-dce-endpoint.region.ingest.monitor.azure.com
DCR_IMMUTABLE_ID=dcr-your-dcr-id-here
```

## Requirements Source

All requirements are downloaded from the official Microsoft repository:
- **Repository**: https://github.com/microsoft/synapse-spark-runtime
- **Fabric Runtime 1.2**: `Fabric/Runtime 1.2 (Spark 3.4)/Fabric-Python310-CPU.yml`
- **Fabric Runtime 1.3**: `Fabric/Runtime 1.3 (Spark 3.5)/Fabric-Python311-CPU.yml`

## VS Code Integration

After setup, configure VS Code to use the created environment:

1. Press `Ctrl+Shift+P` (Windows) or `Cmd+Shift+P` (macOS)
2. Type "Python: Select Interpreter"
3. Choose the interpreter from `.fabric-env-1.3\Scripts\python.exe` (Windows) or `.fabric-env-1.3/bin/python` (Unix/Linux/macOS)

## Troubleshooting

- **Python not found**: Install Python 3.10 or 3.11 from https://python.org
- **Permission errors**: Run as Administrator on Windows
- **Network issues**: Check internet connection for downloading requirements
- **Missing packages**: Use the fallback installation which installs core Azure packages

## Cleanup

To remove all created environments:
```cmd
cd setup
cleanup_environments.bat
```

This will safely remove all `.fabric-env-*` directories.