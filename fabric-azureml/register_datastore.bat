@echo off
REM ============================================================================
REM Register OneLake Datastore in Azure ML - Quick Setup Script
REM ============================================================================

echo ========================================
echo Azure ML - OneLake Datastore Registration
echo ========================================
echo.

REM Check if Azure CLI is installed
where az >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Azure CLI not found. Please install it from:
    echo https://learn.microsoft.com/en-us/cli/azure/install-azure-cli
    exit /b 1
)

echo [INFO] Azure CLI found
echo.

REM Check if ML extension is installed
echo [INFO] Checking Azure ML extension...
az extension show --name ml >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Azure ML extension not installed. Installing...
    az extension add --name ml
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install Azure ML extension
        exit /b 1
    )
    echo [SUCCESS] Azure ML extension installed
) else (
    echo [INFO] Azure ML extension already installed
)
echo.

REM Prompt for Azure ML workspace details
echo ========================================
echo Enter your Azure ML workspace details:
echo ========================================
echo.

set /p SUBSCRIPTION_ID="Subscription ID: "
set /p RESOURCE_GROUP="Resource Group: "
set /p WORKSPACE_NAME="Workspace Name: "

echo.
echo [INFO] Configuration:
echo   Subscription: %SUBSCRIPTION_ID%
echo   Resource Group: %RESOURCE_GROUP%
echo   Workspace: %WORKSPACE_NAME%
echo.

REM Confirm
set /p CONFIRM="Proceed with registration? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo [INFO] Registration cancelled
    exit /b 0
)

echo.
echo [INFO] Setting active subscription...
az account set --subscription "%SUBSCRIPTION_ID%"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to set subscription. Please check your subscription ID
    exit /b 1
)

echo [INFO] Registering OneLake datastore...
echo.

REM Register the datastore from YAML file
az ml datastore create ^
  --file azml_onelakesp_datastore.yml ^
  --resource-group "%RESOURCE_GROUP%" ^
  --workspace-name "%WORKSPACE_NAME%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo [SUCCESS] Datastore registered successfully!
    echo ========================================
    echo.
    echo Datastore Details:
    echo   Name: "<REDACTED_WORKSPACE_ID>"
    echo   Type: OneLake (Fabric)
    echo   Workspace ID: "<REDACTED_WORKSPACE_ID>"
    echo   Lakehouse ID: "<REDACTED_LAKEHOUSE_ID>"
    echo.
    echo Next Steps:
    echo   1. Verify in Azure ML Studio: https://ml.azure.com
    echo   2. Navigate to Data ^> Datastores
    echo   3. Look for: "<REDACTED_WORKSPACE_ID>"
    echo.
    
    REM List all datastores
    echo [INFO] Listing all datastores in workspace...
    echo.
    az ml datastore list ^
      --resource-group "%RESOURCE_GROUP%" ^
      --workspace-name "%WORKSPACE_NAME%" ^
      --output table
    
) else (
    echo.
    echo ========================================
    echo [ERROR] Datastore registration failed
    echo ========================================
    echo.
    echo Troubleshooting:
    echo   1. Verify your Azure ML workspace exists
    echo   2. Check that you have Contributor permissions
    echo   3. Ensure you're logged in: az login
    echo   4. Verify the YAML file: azml_onelakesp_datastore.yml
    echo.
    echo For detailed logs, add --debug flag to the command
    exit /b 1
)

echo.
echo ========================================
echo Registration Complete!
echo ========================================
pause
