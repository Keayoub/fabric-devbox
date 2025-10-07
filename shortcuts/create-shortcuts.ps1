# PowerShell script to bulk create Fabric shortcuts from a CSV file
# Place this script in the shortcuts folder and run it from the project root
# Ensure you have a CSV file named shortcuts.csv in the shortcuts folder with columns: location,subpath,connectionId,workspace,lakehouse,shortcutName

param(
    [string]$CsvPath = "shortcuts.csv",
    [string]$shortcutType = "adlsGen2"  # Default shortcut type
)

# Ensure user is connected to fab CLI
try {
    $fabStatus = fab account show 2>$null
}
catch {
    Write-Host "You are not connected to Fabric CLI. Please run 'fab auth login' and try again."
    exit 1
}


if (!(Test-Path $CsvPath)) {
    Write-Host "CSV file not found: $CsvPath"
    exit 1
}

$csvRows = Import-Csv -Path $CsvPath

foreach ($row in $csvRows) {
    # Validate required fields loop in ADLS GEN 2 entry folder / container
    if (-not $row.location -or -not $row.subpath -or -not $row.connectionId -or -not $row.workspace -or -not $row.lakehouse -or -not $row.target -or -not $row.shortcutName) {
        Write-Warning "Skipping row due to missing required fields: $($row | ConvertTo-Json -Compress)"
        continue

        # using python get_adls_gen2_entry_folder.py to get the ADLS GEN 2 entry folder / container
        # This part is not implemented in this script, assuming the CSV already has the required fields
        

        # loop on the ADLS GEN 2 entry folder / container        
        $workspaceName = $row.workspace
        $lakehouseName = $row.lakehouse
        $targetName = $row.subpath
        $shortcutName = $row.shortcutName
        $shortcutFullPath = "$workspaceName.workspace/$lakehouseName.lakehouse/Files/$targetName/$shortcutName.Shortcut"

        # Check if workspace exists
        $workspace = fab api -X get workspaces -q "text.value[?displayName=='$workspaceName'].{id:id, name:displayName}" | ConvertFrom-Json
        if (-not $workspace) {
            Write-Error "Workspace '$workspaceName' not found. Row: $($row | ConvertTo-Json -Compress)"
            continue
        }
        $workspaceId = $workspace.id
        Write-Host "Workspace ID for '$workspaceName': $workspaceId"

        # Check if lakehouse exists in the workspace
        $lakehouse = fab api -X get "workspaces/$workspaceId/lakehouses" -q  "text.value[?displayName=='$lakehouseName'].{id:id, name:displayName, type:type}" | ConvertFrom-Json
        if (-not $lakehouse) {
            Write-Error "Lakehouse '$lakehouseName' not found in workspace '$workspaceName'. Row: $($row | ConvertTo-Json -Compress)"
            continue
        }
        $lakehouseId = $lakehouse.id
        Write-Host "Lakehouse ID for '$lakehouseName': $lakehouseId"

        # Check if destination folder exists, create if not
        $folderPath = "$workspaceName.workspace/$lakehouseName.lakehouse/Files/$targetName"
        $folderExists = fab exists "$folderPath" 2>$null
        if ($folderExists -eq $false -or $folderExists -eq $null) {
            Write-Host "Destination folder '$folderPath' does not exist. Creating..." -ForegroundColor Yellow
            fab mkdir "$folderPath"
            Write-Host "Folder created: $folderPath" -ForegroundColor Green
        }
        else {
            Write-Host "Destination folder '$folderPath' exists." -ForegroundColor Green
        }

        # create the shortcut on the lakehouse
        $json = @{ location = $row.location; subpath = "/$($row.subpath)"; connectionId = $row.connectionId } | ConvertTo-Json -Compress
        Write-Host "Creating shortcut: $shortcutFullPath" -ForegroundColor Cyan
        $fablncmd = "fab ln '$shortcutFullPath' --type $shortcutType -i '$json' -f"
        Write-Host $fablncmd -ForegroundColor Yellow
        $lsResult = Invoke-Expression $fablncmd
        if ($lsResult) {
            Write-Host $lsResult
        }
        Write-Host "Shortcut created successfully: $shortcutFullPath" -ForegroundColor Green
        Write-Host "--------------------------------------------------"
    }


    
}