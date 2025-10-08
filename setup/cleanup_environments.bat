@echo off
setlocal enabledelayedexpansion

echo Fabric Environment Cleanup Utility
echo ==================================

echo Removing old environment directories...

if exist "..\azure-fabric-env" (
    echo Removing azure-fabric-env...
    rmdir /s /q "..\azure-fabric-env"
    echo ✅ Removed azure-fabric-env
)

if exist "..\.fabric-env-1.2" (
    echo Removing .fabric-env-1.2...
    rmdir /s /q "..\.fabric-env-1.2"
    echo ✅ Removed .fabric-env-1.2
)

if exist "..\.fabric-env-1.3" (
    echo Removing .fabric-env-1.3...
    rmdir /s /q "..\.fabric-env-1.3"
    echo ✅ Removed fabric-env-1.3
)

if exist "..\.venv" (
    echo Removing .venv...
    rmdir /s /q "..\.venv"
    echo ✅ Removed .venv
)

echo.
echo Current environment directories:
for /d %%d in (..\.fabric-env-*) do (
    echo - %%d
)

echo.
echo Cleanup complete! 
echo Use setup\setup_fabric_environment.bat to create new environments.
pause