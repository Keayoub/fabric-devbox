@echo off
REM ==============================================================================
REM Register OneLake Datastore using Azure CLI
REM Following: https://learn.microsoft.com/en-us/azure/machine-learning/how-to-datastore
REM ==============================================================================

echo.
echo ==============================================================================
echo Azure ML - Register OneLake Datastore (Azure CLI Method)
echo ==============================================================================
echo.
echo This script follows the official Microsoft documentation:
echo https://learn.microsoft.com/en-us/azure/machine-learning/how-to-datastore
echo.

REM ============================================================================
REM Step 1: Check prerequisites
REM ============================================================================

echo [Step 1/4] Checking prerequisites...
echo.

where az >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Azure CLI not found!
    echo Please install from: https://aka.ms/installazurecliwindows
    pause
    exit /b 1
)
echo   [OK] Azure CLI installed

az extension show --name ml >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   [WARN] Azure ML extension not found. Installing...
    az extension add --name ml
    if %ERRORLEVEL% NEQ 0 (
        echo   [ERROR] Failed to install ML extension
        pause
        exit /b 1
    )
    echo   [OK] Azure ML extension installed
) else (
    echo   [OK] Azure ML extension installed
)

echo.

REM ============================================================================
REM Step 2: Get your Azure ML workspace details
REM ============================================================================

echo [Step 2/4] Azure ML Workspace Configuration
echo.
echo Please enter your Azure ML workspace details:
echo.

set /p SUBSCRIPTION_ID="  Subscription ID: "
set /p RESOURCE_GROUP="  Resource Group: "
set /p WORKSPACE_NAME="  Workspace Name: "

echo.
echo Configuration:
echo   Subscription: %SUBSCRIPTION_ID%
echo   Resource Group: %RESOURCE_GROUP%
echo   Workspace: %WORKSPACE_NAME%
echo.

set /p CONFIRM="Continue? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo Operation cancelled.
    pause
    exit /b 0
)

REM ============================================================================
REM Step 3: Set active subscription and verify workspace
REM ============================================================================

echo.
echo [Step 3/4] Verifying workspace...
echo.

az account set --subscription "%SUBSCRIPTION_ID%" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to set subscription. Please verify your subscription ID.
    echo.
    echo Tip: List your subscriptions with: az account list --output table
    pause
    exit /b 1
)
echo   [OK] Subscription set

az ml workspace show --name "%WORKSPACE_NAME%" --resource-group "%RESOURCE_GROUP%" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Workspace not found or you don't have access.
    echo.
    echo Please verify:
    echo   - Workspace name: %WORKSPACE_NAME%
    echo   - Resource group: %RESOURCE_GROUP%
    echo   - You have Contributor or Owner permissions
    echo.
    pause
    exit /b 1
)
echo   [OK] Workspace verified

REM ============================================================================
REM Step 4: Register OneLake datastore from YAML
REM ============================================================================

echo.
echo [Step 4/4] Registering OneLake datastore...
echo.

echo Running command:
echo   az ml datastore create --file azml_onelakesp_datastore.yml \
echo     --resource-group %RESOURCE_GROUP% \
echo     --workspace-name %WORKSPACE_NAME%
echo.

az ml datastore create ^
  --file azml_onelakesp_datastore.yml ^
  --resource-group "%RESOURCE_GROUP%" ^
  --workspace-name "%WORKSPACE_NAME%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ==============================================================================
    echo [SUCCESS] OneLake Datastore Registered!
    echo ==============================================================================
    echo.
    echo Datastore Details:
    echo   Name: "<REDACTED_WORKSPACE_ID>"
    echo   Type: OneLake (Microsoft Fabric)
    echo   Workspace ID: "<REDACTED_WORKSPACE_ID>"
    echo   Lakehouse ID: "<REDACTED_LAKEHOUSE_ID>"
    echo.
    echo Next Steps:
    echo   1. View in Azure ML Studio: https://ml.azure.com
    echo   2. Navigate to: Data ^> Datastores
    echo   3. Look for: "<REDACTED_WORKSPACE_ID>"
    echo.
    
    REM Show the registered datastore
    echo ==============================================================================
    echo Verifying Registration...
    echo ==============================================================================
    echo.
    
        az ml datastore show ^
            --name "<REDACTED_WORKSPACE_ID>" ^
            --resource-group "%RESOURCE_GROUP%" ^
            --workspace-name "%WORKSPACE_NAME%"
    
    echo.
    echo ==============================================================================
    echo All Datastores in Workspace:
    echo ==============================================================================
    echo.
    
    az ml datastore list ^
      --resource-group "%RESOURCE_GROUP%" ^
      --workspace-name "%WORKSPACE_NAME%" ^
      --output table
    
) else (
    echo.
    echo ==============================================================================
    echo [ERROR] Registration Failed
    echo ==============================================================================
    echo.
    echo Troubleshooting:
    echo   1. Verify service principal has access to:
    echo      - Azure ML workspace (Contributor role)
    echo      - Fabric workspace (Admin or Member role)
    echo.
    echo   2. Check your YAML file: azml_onelakesp_datastore.yml
    echo.
    echo   3. Verify the lakehouse exists in Fabric
    echo.
    echo   4. Try with --debug flag:
    echo      az ml datastore create --file azml_onelakesp_datastore.yml \
    echo        --resource-group %RESOURCE_GROUP% \
    echo        --workspace-name %WORKSPACE_NAME% --debug
    echo.
    pause
    exit /b 1
)

echo.
echo ==============================================================================
echo Setup Complete!
echo ==============================================================================
echo.
pause
