#!/usr/bin/env python3
"""
Azure & Fabric Python Environment Setup Script
This script creates and configures a Python environment for Azure and Fabric development.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors gracefully."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False

def setup_virtual_environment():
    """Create and activate a virtual environment."""
    env_name = "azure-fabric-env"
    
    # Create virtual environment
    if not run_command(f"python -m venv {env_name}", f"Creating virtual environment '{env_name}'"):
        return False
    
    # Determine activation script path
    if sys.platform == "win32":
        activate_script = f"{env_name}\\Scripts\\activate.bat"
        pip_path = f"{env_name}\\Scripts\\pip"
    else:
        activate_script = f"{env_name}/bin/activate"
        pip_path = f"{env_name}/bin/pip"
    
    print(f"📍 Virtual environment created at: {Path(env_name).absolute()}")
    print(f"📍 To activate manually, run: {activate_script}")
    
    return pip_path

def install_packages(pip_path):
    """Install required packages using pip."""
    requirements_file = "requirements.txt"
    
    if Path(requirements_file).exists():
        return run_command(
            f"{pip_path} install -r {requirements_file}", 
            "Installing packages from requirements.txt"
        )
    else:
        # Install packages individually if requirements.txt doesn't exist
        packages = [
            "azure-identity>=1.15.0",
            "azure-keyvault-secrets>=4.7.0",
            "azure-monitor-ingestion>=1.0.0",
            "msal>=1.24.0",
            "requests>=2.31.0",
            "pandas>=2.0.0",
            "jupyter>=1.0.0",
            "rich>=13.0.0"
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
        with open(".env.example", "w") as f:
            f.write(env_content)
        print("✅ Created .env.example file")
        print("📝 Copy .env.example to .env and fill in your actual values")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env.example: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 Setting up Azure & Fabric Python Environment")
    print("=" * 50)
    
    # Setup virtual environment
    pip_path = setup_virtual_environment()
    if not pip_path:
        print("❌ Failed to create virtual environment")
        return False
    
    # Install packages
    if not install_packages(pip_path):
        print("❌ Failed to install some packages")
        return False
    
    # Create environment file template
    create_env_file()
    
    print("\n🎉 Environment setup complete!")
    print("\nNext steps:")
    print("1. Activate the virtual environment:")
    if sys.platform == "win32":
        print("   azure-fabric-env\\Scripts\\activate.bat")
    else:
        print("   source azure-fabric-env/bin/activate")
    print("2. Copy .env.example to .env and fill in your credentials")
    print("3. Start Jupyter: jupyter notebook")
    print("4. Open fabric_LA_collector.ipynb and run the cells")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
