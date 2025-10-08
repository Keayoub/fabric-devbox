#!/usr/bin/env python3
"""
Fabric Requirements Downloader
Downloads the latest requirements from Microsoft Synapse Spark Runtime repository
https://github.com/microsoft/synapse-spark-runtime/tree/main/Fabric
"""

import requests
import yaml
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional

def download_fabric_runtime_yaml(runtime_version: str) -> Optional[Dict]:
    """Download the YAML file from Microsoft Synapse Spark Runtime repository."""
    if runtime_version == "1.2":
        url = "https://raw.githubusercontent.com/microsoft/synapse-spark-runtime/main/Fabric/Runtime%201.2%20(Spark%203.4)/Fabric-Python310-CPU.yml"
        python_version = "3.10"
    elif runtime_version == "1.3":
        url = "https://raw.githubusercontent.com/microsoft/synapse-spark-runtime/main/Fabric/Runtime%201.3%20(Spark%203.5)/Fabric-Python311-CPU.yml"
        python_version = "3.11"
    else:
        print(f"Unsupported runtime version: {runtime_version}")
        return None
    
    print(f"Downloading Fabric Runtime {runtime_version} (Python {python_version}) from Microsoft repository...")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Parse YAML content
        yaml_content = yaml.safe_load(response.text)
        print(f"Successfully downloaded runtime specifications")
        return yaml_content
        
    except requests.exceptions.RequestException as e:
        print(f"Failed to download from {url}: {e}")
        return None
    except yaml.YAMLError as e:
        print(f"Failed to parse YAML content: {e}")
        return None

def extract_pip_packages(yaml_content: Dict) -> List[str]:
    """Extract pip packages from the YAML content."""
    pip_packages = []
    
    # Look for pip packages in dependencies
    dependencies = yaml_content.get('dependencies', [])
    
    for dep in dependencies:
        if isinstance(dep, dict) and 'pip' in dep:
            pip_packages.extend(dep['pip'])
            break
    
    return pip_packages

def extract_conda_packages(yaml_content: Dict) -> List[str]:
    """Extract conda packages from the YAML content."""
    conda_packages = []
    
    # Look for conda packages in dependencies
    dependencies = yaml_content.get('dependencies', [])
    
    for dep in dependencies:
        if isinstance(dep, str):
            conda_packages.append(dep)
    
    return conda_packages

def normalize_package_format(package: str) -> str:
    """Convert conda format to pip format."""
    # Convert conda format (package=version=build) to pip format (package==version)
    if '=' in package and '==' not in package:
        parts = package.split('=')
        if len(parts) >= 2:
            package_name = parts[0]
            version = parts[1]
            
            # Handle conda date-based versions that don't exist in pip
            # Use latest available version for these packages
            conda_packages_to_latest = {
                'azure-identity': '',  # Use latest
                'azure-keyvault': '',  # Use latest
                'azure-storage': '',   # Use latest
                'msal': '',           # Use latest
                'msal-extensions': '', # Use latest
            }
            
            if package_name in conda_packages_to_latest:
                return package_name  # Return without version to get latest
            
            return f"{package_name}=={version}"
    return package

def filter_azure_packages(packages: List[str]) -> List[str]:
    """Filter packages relevant to Azure and Log Analytics integration."""
    azure_keywords = [
        'azure-', 'msal', 'adal', 'requests', 'pandas', 'numpy', 'pyarrow',
        'jupyter', 'ipython', 'ipykernel', 'rich', 'matplotlib', 'seaborn',
        'plotly', 'scikit-learn', 'scipy', 'python-dateutil', 'json5',
        'python-dotenv', 'pyspark'
    ]
    
    filtered = []
    for package in packages:
        # Normalize format first
        normalized_package = normalize_package_format(package)
        package_name = normalized_package.split('==')[0].split('>=')[0].split('<=')[0].lower()
        if any(keyword in package_name for keyword in azure_keywords):
            filtered.append(normalized_package)
    
    return filtered

def create_requirements_file(runtime_version: str, pip_packages: List[str], conda_packages: List[str]) -> str:
    """Create a requirements.txt file content."""
    content = []
    
    # Header
    content.append(f"# Fabric Runtime {runtime_version} - Official Microsoft Dependencies")
    content.append(f"# Downloaded from: https://github.com/microsoft/synapse-spark-runtime")
    content.append(f"# Generated on: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    content.append("")
    
    # Azure SDK packages
    content.append("# Core Azure SDK packages for Log Analytics integration")
    azure_packages = [p for p in pip_packages + conda_packages if 'azure-' in p.lower()]
    content.extend(azure_packages)
    content.append("")
    
    # Authentication packages
    content.append("# Microsoft Authentication")
    auth_packages = [p for p in pip_packages + conda_packages if any(auth in p.lower() for auth in ['msal', 'adal'])]
    content.extend(auth_packages)
    content.append("")
    
    # Core packages
    content.append("# Core Python packages")
    core_packages = [p for p in pip_packages + conda_packages if any(core in p.lower() for core in ['requests', 'pandas', 'numpy', 'pyarrow'])]
    content.extend(core_packages)
    content.append("")
    
    # Development tools
    content.append("# Development and notebook tools")
    dev_packages = [p for p in pip_packages + conda_packages if any(dev in p.lower() for dev in ['jupyter', 'ipython', 'ipykernel', 'rich'])]
    content.extend(dev_packages)
    content.append("")
    
    # Data science packages
    content.append("# Data science packages")
    ds_packages = [p for p in pip_packages + conda_packages if any(ds in p.lower() for ds in ['matplotlib', 'seaborn', 'plotly', 'scikit-learn', 'scipy'])]
    content.extend(ds_packages)
    content.append("")
    
    # PySpark
    content.append("# PySpark")
    pyspark_packages = [p for p in pip_packages + conda_packages if 'pyspark' in p.lower()]
    content.extend(pyspark_packages)
    content.append("")
    
    # Fabric-specific note
    content.append("# Note: Fabric-specific packages are only available in Fabric runtime environment:")
    fabric_specific = [p for p in pip_packages if any(fabric in p.lower() for fabric in ['semantic-link', 'notebookutils', 'fabric-connection', 'powerbiclient'])]
    for pkg in fabric_specific:
        content.append(f"# - {pkg}")
    
    return '\n'.join(content)

def main():
    """Main function to download and create requirements files."""
    print("Fabric Requirements Downloader")
    print("=" * 50)
    
    # Ask user for runtime version
    while True:
        runtime_choice = input("Select Fabric Runtime version (1.2 or 1.3): ").strip()
        if runtime_choice in ["1.2", "1.3"]:
            break
        print("Please enter '1.2' or '1.3'")
    
    # Download YAML content
    yaml_content = download_fabric_runtime_yaml(runtime_choice)
    if not yaml_content:
        print("Failed to download runtime specifications")
        return False
    
    # Extract packages
    pip_packages = extract_pip_packages(yaml_content)
    conda_packages = extract_conda_packages(yaml_content)
    
    print(f"Found {len(pip_packages)} pip packages and {len(conda_packages)} conda packages")
    
    # Filter relevant packages
    filtered_pip = filter_azure_packages(pip_packages)
    filtered_conda = filter_azure_packages(conda_packages)
    
    print(f"🔍 Filtered to {len(filtered_pip)} pip packages and {len(filtered_conda)} conda packages relevant to Azure integration")
    
    # Create requirements file content
    requirements_content = create_requirements_file(runtime_choice, filtered_pip, filtered_conda)
    
    # Save to file
    filename = f"requirements-fabric-{runtime_choice}.txt"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(requirements_content)
        print(f"Created {filename}")
        
        # Also create a generic requirements.txt if it doesn't exist
        if not Path("requirements.txt").exists():
            with open("requirements.txt", 'w', encoding='utf-8') as f:
                f.write(requirements_content)
            print(f"Created requirements.txt")
        
        print(f"\nRequirements file created with {len(filtered_pip + filtered_conda)} packages")
        print(f"File location: {Path(filename).absolute()}")
        
        return True
        
    except Exception as e:
        print(f"Failed to save requirements file: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)