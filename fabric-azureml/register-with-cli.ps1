# ==============================================================================
# Register OneLake Datastore using Azure CLI (PowerShell)
# Following: https://learn.microsoft.com/en-us/azure/machine-learning/how-to-datastore
# ==============================================================================

<#
.SYNOPSIS
    Registers an OneLake datastore in Azure Machine Learning workspace.

.DESCRIPTION
    This script registers a Microsoft Fabric OneLake lakehouse as a datastore
    in Azure ML, following the official Microsoft documentation.

.PARAMETER SubscriptionId
    Azure subscription ID where the Azure ML workspace is located.

.PARAMETER ResourceGroup
    Resource group name containing the Azure ML workspace.

.PARAMETER WorkspaceName
    Name of the Azure ML workspace.

.PARAMETER DatastoreFile
    Path to the datastore YAML configuration file. Default: azml_onelakesp_datastore.yml

.EXAMPLE
    .\register-with-cli.ps1

.EXAMPLE
    .\register-with-cli.ps1 -SubscriptionId "12345678-1234-1234-1234-123456789abc" -ResourceGroup "my-rg" -WorkspaceName "my-workspace"

.EXAMPLE
    .\register-with-cli.ps1 -s "12345678-1234-1234-1234-123456789abc" -g "my-rg" -w "my-workspace"

.EXAMPLE
    .\register-with-cli.ps1 -sub "12345678-1234-1234-1234-123456789abc" -rg "my-rg" -workspace "my-workspace" -file "custom-datastore.yml"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false, HelpMessage="Azure subscription ID")]
    [Alias("s", "sub", "subscription")]
    [string]$SubscriptionId,
    
    [Parameter(Mandatory=$false, HelpMessage="Resource group name")]
    [Alias("g", "rg")]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$false, HelpMessage="Azure ML workspace name")]
    [Alias("w", "workspace")]
    [string]$WorkspaceName,
    
    [Parameter(Mandatory=$false, HelpMessage="Path to datastore YAML file")]
    [Alias("f", "file")]
    [string]$DatastoreFile = "azml_onelakesp_datastore.yml"
)

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "Azure ML - Register OneLake Datastore (Azure CLI Method)" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script follows the official Microsoft documentation:" -ForegroundColor Yellow
Write-Host "https://learn.microsoft.com/en-us/azure/machine-learning/how-to-datastore" -ForegroundColor Yellow
Write-Host ""

# ==============================================================================
# Step 1: Check prerequisites
# ==============================================================================

Write-Host "[Step 1/4] Checking prerequisites..." -ForegroundColor Cyan
Write-Host ""

# Check Azure CLI
if (!(Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Host "  [ERROR] Azure CLI not found!" -ForegroundColor Red
    Write-Host "  Please install from: https://aka.ms/installazurecliwindows" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  [OK] Azure CLI installed" -ForegroundColor Green

# Check ML extension
az extension show --name ml 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [WARN] Azure ML extension not found. Installing..." -ForegroundColor Yellow
    az extension add --name ml
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERROR] Failed to install ML extension" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "  [OK] Azure ML extension installed" -ForegroundColor Green
} else {
    Write-Host "  [OK] Azure ML extension installed" -ForegroundColor Green
}

Write-Host ""

# ==============================================================================
# Step 2: Get Azure ML workspace details
# ==============================================================================

Write-Host "[Step 2/4] Azure ML Workspace Configuration" -ForegroundColor Cyan
Write-Host ""

# Use parameters if provided, otherwise prompt
if ([string]::IsNullOrWhiteSpace($SubscriptionId)) {
    Write-Host "Please enter your Azure ML workspace details:" -ForegroundColor Yellow
    Write-Host ""
    $SubscriptionId = Read-Host "  Subscription ID"
} else {
    Write-Host "Using provided parameters..." -ForegroundColor Green
}

if ([string]::IsNullOrWhiteSpace($ResourceGroup)) {
    $ResourceGroup = Read-Host "  Resource Group"
}

if ([string]::IsNullOrWhiteSpace($WorkspaceName)) {
    $WorkspaceName = Read-Host "  Workspace Name"
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Subscription: $SubscriptionId"
Write-Host "  Resource Group: $ResourceGroup"
Write-Host "  Workspace: $WorkspaceName"
Write-Host "  Datastore File: $DatastoreFile"
Write-Host ""

# Only confirm if running interactively (not when parameters provided)
if ($PSBoundParameters.Count -eq 0) {
    $confirm = Read-Host "Continue? (y/n)"
    if ($confirm -ne 'y' -and $confirm -ne 'Y') {
        Write-Host "Operation cancelled." -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 0
    }
} else {
    Write-Host "Auto-confirming with provided parameters..." -ForegroundColor Green
}

# ==============================================================================
# Step 3: Set active subscription and verify workspace
# ==============================================================================

Write-Host ""
Write-Host "[Step 3/4] Verifying workspace..." -ForegroundColor Cyan
Write-Host ""

# Set subscription
az account set --subscription $SubscriptionId 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [ERROR] Failed to set subscription. Please verify your subscription ID." -ForegroundColor Red
    Write-Host ""
    Write-Host "  Tip: List your subscriptions with: az account list --output table" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  [OK] Subscription set" -ForegroundColor Green

# Verify workspace exists
az ml workspace show --name $WorkspaceName --resource-group $ResourceGroup 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [ERROR] Workspace not found or you don't have access." -ForegroundColor Red
    Write-Host ""
    Write-Host "  Please verify:" -ForegroundColor Yellow
    Write-Host "    - Workspace name: $WorkspaceName"
    Write-Host "    - Resource group: $ResourceGroup"
    Write-Host "    - You have Contributor or Owner permissions"
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  [OK] Workspace verified" -ForegroundColor Green

# ==============================================================================
# Step 4: Register OneLake datastore from YAML
# ==============================================================================

Write-Host ""
Write-Host "[Step 4/4] Registering OneLake datastore..." -ForegroundColor Cyan
Write-Host ""

Write-Host "Running command:" -ForegroundColor Yellow
Write-Host "  az ml datastore create --file $DatastoreFile \"
Write-Host "    --resource-group $ResourceGroup \"
Write-Host "    --workspace-name $WorkspaceName"
Write-Host ""

# Verify datastore file exists
if (-not (Test-Path $DatastoreFile)) {
    Write-Host "  [ERROR] Datastore file not found: $DatastoreFile" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Please ensure the file exists in the current directory." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Register the datastore
az ml datastore create `
  --file $DatastoreFile `
  --resource-group $ResourceGroup `
  --workspace-name $WorkspaceName

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==============================================================================" -ForegroundColor Green
    Write-Host "[SUCCESS] OneLake Datastore Registered!" -ForegroundColor Green
    Write-Host "==============================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Datastore Details:" -ForegroundColor Cyan
    Write-Host "  Name: '<REDACTED_WORKSPACE_ID>'"
    Write-Host "  Type: OneLake (Microsoft Fabric)"
    Write-Host "  Workspace ID: '<REDACTED_WORKSPACE_ID>'"
    Write-Host "  Lakehouse ID: '<REDACTED_LAKEHOUSE_ID>'"
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "  1. View in Azure ML Studio: https://ml.azure.com"
    Write-Host "  2. Navigate to: Data > Datastores"
    Write-Host "  3. Look for: '<REDACTED_WORKSPACE_ID>'"
    Write-Host ""
    
    # Show the registered datastore
    Write-Host "==============================================================================" -ForegroundColor Cyan
    Write-Host "Verifying Registration..." -ForegroundColor Cyan
    Write-Host "==============================================================================" -ForegroundColor Cyan
    Write-Host ""
    
            az ml datastore show `
                --name "<REDACTED_WORKSPACE_ID>" `
            --resource-group $ResourceGroup `
            --workspace-name $WorkspaceName
    
    Write-Host ""
    Write-Host "==============================================================================" -ForegroundColor Cyan
    Write-Host "All Datastores in Workspace:" -ForegroundColor Cyan
    Write-Host "==============================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    az ml datastore list `
      --resource-group $ResourceGroup `
      --workspace-name $WorkspaceName `
      --output table
    
} else {
    Write-Host ""
    Write-Host "==============================================================================" -ForegroundColor Red
    Write-Host "[ERROR] Registration Failed" -ForegroundColor Red
    Write-Host "==============================================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Verify service principal has access to:"
    Write-Host "     - Azure ML workspace (Contributor role)"
    Write-Host "     - Fabric workspace (Admin or Member role)"
    Write-Host ""
    Write-Host "  2. Check your YAML file: azml_onelakesp_datastore.yml"
    Write-Host ""
    Write-Host "  3. Verify the lakehouse exists in Fabric"
    Write-Host ""
    Write-Host "  4. Try with --debug flag:"
    Write-Host "     az ml datastore create --file $DatastoreFile \"
    Write-Host "       --resource-group $ResourceGroup \"
    Write-Host "       --workspace-name $WorkspaceName --debug"
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit"
