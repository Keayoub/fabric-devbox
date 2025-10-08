@echo off
setlocal enabledelayedexpansion

REM Azure & Fabric Python Environment Setup Script for Windows
REM Downloads latest requirements from Microsoft Synapse Spark Runtime repository
REM https://github.com/microsoft/synapse-spark-runtime/tree/main/Fabric

echo Setting up Azure and Fabric Python Environment
echo Based on official Microsoft Synapse Spark Runtime
echo ==================================================

REM Fabric Runtime Selection
echo.
echo Please select your Fabric Runtime version:
echo 1. Fabric Runtime 1.2 (Stable)
echo 2. Fabric Runtime 1.3 (Latest)
echo.
set /p runtime_choice="Enter your choice (1 or 2): "

if "!runtime_choice!"=="1" (
    set FABRIC_RUNTIME=1.2
    set REQUIREMENTS_FILE=requirements-fabric-1.2.txt
    set ENV_NAME=..\.fabric-env-1.2
    echo Selected Fabric Runtime 1.2
    echo Note: Environment will be created as ..\.fabric-env-1.2
    goto continue_setup
)
if "!runtime_choice!"=="2" (
    set FABRIC_RUNTIME=1.3
    set REQUIREMENTS_FILE=requirements-fabric-1.3.txt
    set ENV_NAME=..\.fabric-env-1.3
    echo Selected Fabric Runtime 1.3
    echo Note: Environment will be created as ..\.fabric-env-1.3
    goto continue_setup
)
echo Invalid choice. Please run the script again and select 1 or 2.
pause
exit /b 1

:continue_setup

echo.

REM Check if Python 3.11 or 3.10 is installed
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.11 not found, checking for Python 3.10...
    py -3.10 --version >nul 2>&1
    if errorlevel 1 (
        echo Neither Python 3.11 nor 3.10 is installed or in PATH
        echo Please install Python 3.10 or 3.11 from https://python.org
        pause
        exit /b 1
    ) else (
        echo Python 3.10 found and will be used
    )
) else (
    echo Python 3.11 found and will be used
)

REM Create virtual environment
echo Creating virtual environment for Fabric Runtime !FABRIC_RUNTIME!...

REM Try Python 3.11 first, then 3.10
py -3.11 -m venv !ENV_NAME! >nul 2>&1
if errorlevel 1 (
    echo Python 3.11 failed, trying Python 3.10...
    py -3.10 -m venv !ENV_NAME! >nul 2>&1
    if errorlevel 1 (
        echo Both Python 3.11 and 3.10 failed. Trying default python...
        python -m venv !ENV_NAME! >nul 2>&1
        if errorlevel 1 (
            echo Failed to create virtual environment
            echo Please ensure Python 3.10 or 3.11 is installed and accessible
            echo You may need to run this script as Administrator
            pause
            exit /b 1
        ) else (
            echo Successfully created virtual environment with default Python
        )
    ) else (
        echo Successfully created virtual environment with Python 3.10
    )
) else (
    echo Successfully created virtual environment with Python 3.11
)

REM Activate virtual environment
echo Activating virtual environment...
call !ENV_NAME!\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Download requirements from Microsoft repository
echo Downloading requirements for Fabric Runtime !FABRIC_RUNTIME! from Microsoft repository...
echo Installing downloader dependencies...
pip install requests pyyaml

echo Running requirements downloader...
echo !FABRIC_RUNTIME! | python download_fabric_requirements.py

REM Install packages
echo Installing packages for Fabric Runtime !FABRIC_RUNTIME!...
if exist !REQUIREMENTS_FILE! (
    echo Installing from !REQUIREMENTS_FILE!
    pip install -r !REQUIREMENTS_FILE!
) else if exist ..\requirements.txt (
    echo Installing from ..\requirements.txt ^(fallback^)
    pip install -r ..\requirements.txt
) else (
    echo Installing basic packages (fallback)
    pip install azure-identity azure-keyvault-secrets azure-monitor-ingestion msal requests pandas jupyter rich
)

if errorlevel 1 (
    echo Some packages failed to install
    pause
    exit /b 1
)

REM Create .env.example if it doesn't exist
if not exist ..\.env.example (
    echo Creating .env.example file...
    (
        echo # Azure and Fabric Environment Variables
        echo # Copy this file to .env and fill in your actual values
        echo # Fabric Runtime: !FABRIC_RUNTIME!
        echo.
        echo # Azure AD App Registration
        echo FABRIC_TENANT_ID=your-tenant-id-here
        echo FABRIC_APP_ID=your-app-id-here
        echo FABRIC_APP_SECRET=your-app-secret-here
        echo.
        echo # Azure Subscription
        echo AZURE_SUBSCRIPTION_ID=your-subscription-id-here
        echo.
        echo # Fabric Workspace
        echo FABRIC_WORKSPACE_ID=your-workspace-id-here
        echo FABRIC_RUNTIME_VERSION=!FABRIC_RUNTIME!
        echo.
        echo # Log Analytics
        echo LOG_ANALYTICS_WORKSPACE_ID=your-log-analytics-workspace-id
        echo DCR_ENDPOINT_HOST=your-dce-endpoint.region.ingest.monitor.azure.com
        echo DCR_IMMUTABLE_ID=dcr-your-dcr-id-here
    ) > ..\.env.example
)

echo.
echo Environment setup complete for Fabric Runtime !FABRIC_RUNTIME!!
echo.
echo Environment Details:
echo - Runtime Version: !FABRIC_RUNTIME!
echo - Virtual Environment: !ENV_NAME!
echo - Requirements File: !REQUIREMENTS_FILE!
echo - Downloaded from: https://github.com/microsoft/synapse-spark-runtime
echo.
echo Next steps:
echo 1. Copy .env.example to .env and fill in your credentials
echo 2. Start Jupyter: jupyter notebook
echo 3. Open your Fabric notebooks and run the cells
echo.
echo To activate this environment in the future, run:
echo !ENV_NAME!\Scripts\activate.bat
echo.
echo VS Code Integration:
echo 1. Press Ctrl+Shift+P in VS Code
echo 2. Type "Python: Select Interpreter"
echo 3. Choose the interpreter from !ENV_NAME!\Scripts\python.exe
echo.
pause
