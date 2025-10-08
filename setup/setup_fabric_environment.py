#!/usr/bin/env python3
"""
Azure & Fabric Python Environment Setup Script
This script creates and configures a Python environment for Azure and Fabric development.
Downloads latest requirements from official Microsoft Synapse Spark Runtime repository:
https://github.com/microsoft/synapse-spark-runtime/tree/main/Fabric
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors gracefully."""
    print(f"Running: {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"Success: {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {description} failed: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False

def setup_virtual_environment(runtime_version="1.3"):
    """Create and activate a virtual environment with version-specific naming."""
    env_name = f"../.fabric-env-{runtime_version}"

    # Create virtual environment
    if not run_command(f"python -m venv {env_name}", f"Creating virtual environment '{env_name}'"):
        return False, None

    # Determine activation script path
    if sys.platform == "win32":
        activate_script = f"{env_name}\\Scripts\\activate.bat"
        pip_path = f'"{Path(env_name).absolute()}\\Scripts\\pip"'
    else:
        activate_script = f"{env_name}/bin/activate"
        pip_path = f'"{Path(env_name).absolute()}/bin/pip"'

    print(f"Virtual environment created at: {Path(env_name).absolute()}")
    print(f"To activate manually, run: {activate_script}")

    return pip_path, env_name

def download_requirements(runtime_version="1.3"):
    """Download latest requirements from Microsoft repository."""
    print(f"Downloading latest requirements for Fabric Runtime {runtime_version}...")
    
    # First install required packages for the downloader
    downloader_packages = ["requests", "pyyaml"]
    for package in downloader_packages:
        if not run_command(f"python -m pip install {package}", f"Installing {package} for downloader"):
            return False
    
    # Run the download script
    return run_command(
        f"python download_fabric_requirements.py", 
        f"Downloading Fabric Runtime {runtime_version} requirements from Microsoft repository"
    )

def install_packages(pip_path, runtime_version="1.3"):
    """Install required packages using pip based on selected Fabric runtime."""
    requirements_file = f"requirements-fabric-{runtime_version}.txt"
    python_version = "3.10" if runtime_version == "1.2" else "3.11"
    
    print(f"Installing packages for Fabric Runtime {runtime_version} (Python {python_version})")
    
    # Check if requirements file exists, if not download it
    if not Path(requirements_file).exists():
        print(f"Requirements file {requirements_file} not found, downloading from Microsoft repository...")
        if not download_requirements(runtime_version):
            print("Failed to download requirements, using fallback packages")
            return install_fallback_packages(pip_path)
    
    if Path(requirements_file).exists():
        return run_command(
            f"{pip_path} install -r {requirements_file}", 
            f"Installing packages from {requirements_file}"
        )
    elif Path("../requirements.txt").exists():
        return run_command(
            f"{pip_path} install -r ../requirements.txt", 
            "Installing packages from requirements.txt (fallback)"
        )
    else:
        return install_fallback_packages(pip_path)

def install_fallback_packages(pip_path):
    """Install core packages if requirements download fails."""
    print("Installing core packages (fallback)...")
    packages = [
        "azure-identity>=1.16.0",
        "azure-keyvault-secrets>=4.8.0",
        "azure-monitor-ingestion>=1.0.3",
        "msal>=1.28.0",
        "requests>=2.31.0",
        "pandas>=2.1.0",
        "jupyter>=1.0.0",
        "rich>=13.3.0"
    ]
    
    for package in packages:
        if not run_command(f"{pip_path} install {package}", f"Installing {package}"):
            return False
    return True

def create_env_file():
    """Create a sample .env file for environment variables."""
    env_content = """# Azure & Fabric Environment Variables
# Copy this file to .env and fill in your actual values

# Azure AD App Registration
FABRIC_TENANT_ID=your-tenant-id-here
FABRIC_APP_ID=your-app-id-here
FABRIC_APP_SECRET=your-app-secret-here

# Azure Key Vault (optional)
KEY_VAULT_URI=https://your-keyvault.vault.azure.net/
KEY_VAULT_SECRET_NAME=your-secret-name

# Azure Subscription
AZURE_SUBSCRIPTION_ID=your-subscription-id-here

# Fabric Workspace
FABRIC_WORKSPACE_ID=your-workspace-id-here

# Log Analytics
LOG_ANALYTICS_WORKSPACE_ID=your-log-analytics-workspace-id
DCR_ENDPOINT_HOST=your-dce-endpoint.region.ingest.monitor.azure.com
DCR_IMMUTABLE_ID=dcr-your-dcr-id-here
"""
    
    try:
        with open("../.env.example", "w") as f:
            f.write(env_content)
        print("Created .env.example file")
        print("Copy .env.example to .env and fill in your actual values")
        return True
    except Exception as e:
        print(f"Failed to create .env.example: {e}")
        return False

def main():
    """Main setup function."""
    print("Setting up Azure & Fabric Python Environment")
    print("Based on official Microsoft Synapse Spark Runtime")
    print("=" * 50)
    
    # Ask for runtime version
    while True:
        runtime_choice = input("\nSelect Fabric Runtime version:\n1. Runtime 1.2 (Python 3.10, Spark 3.4)\n2. Runtime 1.3 (Python 3.11, Spark 3.5)\nEnter choice (1 or 2): ").strip()
        if runtime_choice == "1":
            runtime_version = "1.2"
            break
        elif runtime_choice == "2":
            runtime_version = "1.3"
            break
        print("Please enter '1' or '2'")
    
    print(f"\nSelected Fabric Runtime {runtime_version}")
    
    # Setup virtual environment
    pip_path, env_name = setup_virtual_environment(runtime_version)
    if not pip_path:
        print("Failed to create virtual environment")
        return False
    
    # Install packages
    if not install_packages(pip_path, runtime_version):
        print("Failed to install some packages")
        return False
    
    # Create environment file template
    create_env_file()
    
    print(f"\nEnvironment setup complete for Fabric Runtime {runtime_version}!")
    print(f"\nEnvironment Details:")
    print(f"- Runtime Version: {runtime_version}")
    print(f"- Virtual Environment: {env_name}")
    print(f"- Requirements File: requirements-fabric-{runtime_version}.txt")
    print("\nNext steps:")
    print("1. Activate the virtual environment:")
    if sys.platform == "win32":
        print(f"   {env_name}\\Scripts\\activate.bat")
    else:
        print(f"   source {env_name}/bin/activate")
    print("2. Copy .env.example to .env and fill in your credentials")
    print("3. Start Jupyter: jupyter notebook")
    print("4. Open your Fabric notebooks and run the cells")
    print(f"\nRequirements downloaded from official Microsoft repository")
    print(f"See requirements-fabric-{runtime_version}.txt for package details")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
