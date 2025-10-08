param(
  [string]$RequirementsFile = "requirements.txt",
  [string]$WheelsDir = "wheels",
  [switch]$FromDir
)

Write-Host "Wheel-only installer"
if ($FromDir) {
  Write-Host "Installing all .whl files from directory: $WheelsDir"
  if (-not (Test-Path $WheelsDir)) {
    Write-Error "Wheels directory '$WheelsDir' not found."
    exit 2
  }
  $whls = Get-ChildItem -Path $WheelsDir -Filter *.whl -File
  if ($whls.Count -eq 0) {
    Write-Error "No .whl files found in $WheelsDir"
    exit 3
  }
  foreach ($w in $whls) {
    Write-Host "Installing $($w.FullName)"
    python -m pip install --upgrade pip
    python -m pip install --no-deps --force-reinstall $w.FullName
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }
  Write-Host "Installed $($whls.Count) wheel(s) from $WheelsDir"
  exit 0
}

Write-Host "Installing from requirements file (wheel-only): $RequirementsFile"
if (-not (Test-Path $RequirementsFile)) {
  Write-Error "Requirements file '$RequirementsFile' not found."
  exit 4
}

python -m pip install --upgrade pip
python -m pip install --only-binary=:all: -r $RequirementsFile
exit $LASTEXITCODE
