#!/usr/bin/env python3
"""
Fabric Environment Discovery Tool

This script helps you discover available environments in your Fabric workspace
and provides detailed information about each environment's status and capabilities.
"""

import argparse
import requests
import json
import sys
from typing import Dict, Any, List, Optional

def safe_print(*args, **kwargs):
    """Print function that handles encoding issues on Windows."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        ascii_args = []
        for arg in args:
            if isinstance(arg, str):
                arg = arg.encode('ascii', 'replace').decode('ascii')
            ascii_args.append(arg)
        print(*ascii_args, **kwargs)

try:
    from azure.identity import DefaultAzureCredential, ClientSecretCredential
    AZURE_IDENTITY_AVAILABLE = True
except ImportError:
    AZURE_IDENTITY_AVAILABLE = False


class FabricEnvironmentDiscovery:
    """Fabric Environment discovery and validation tool."""
    
    def __init__(self, token: Optional[str] = None, client_id: Optional[str] = None, 
                 client_secret: Optional[str] = None, tenant_id: Optional[str] = None):
        self.base_url = "https://api.fabric.microsoft.com/v1"
        self.token = self._get_token(token, client_id, client_secret, tenant_id)
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}',
            'User-Agent': 'FabricLA-Connector-Discovery/1.0.0'
        })
    
    def _get_token(self, token: Optional[str], client_id: Optional[str], 
                   client_secret: Optional[str], tenant_id: Optional[str]) -> str:
        """Get authentication token."""
        if token:
            safe_print("🔑 Using provided bearer token")
            return token
        
        if client_id and client_secret and tenant_id:
            safe_print("🔑 Using service principal authentication")
            if not AZURE_IDENTITY_AVAILABLE:
                raise ImportError("azure-identity package required for service principal auth")
            
            from azure.identity import ClientSecretCredential
            credential = ClientSecretCredential(tenant_id, client_id, client_secret)
            token_result = credential.get_token("https://api.fabric.microsoft.com/.default")
            return token_result.token
        
        safe_print("🔑 Using DefaultAzureCredential (Azure CLI)")
        if not AZURE_IDENTITY_AVAILABLE:
            raise ImportError("azure-identity package required for DefaultAzureCredential")
        
        from azure.identity import DefaultAzureCredential
        credential = DefaultAzureCredential()
        token_result = credential.get_token("https://api.fabric.microsoft.com/.default")
        return token_result.token
    
    def list_workspaces(self) -> List[Dict[str, Any]]:
        """List all accessible workspaces."""
        safe_print("🔍 Discovering workspaces...")
        
        url = f"{self.base_url}/workspaces"
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                workspaces = response.json().get('value', [])
                safe_print(f"✅ Found {len(workspaces)} workspace(s)")
                return workspaces
            else:
                safe_print(f"❌ Failed to list workspaces: HTTP {response.status_code}")
                return []
        except Exception as e:
            safe_print(f"❌ Error listing workspaces: {e}")
            return []
    
    def get_workspace_info(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific workspace."""
        url = f"{self.base_url}/workspaces/{workspace_id}"
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                safe_print(f"❌ Failed to get workspace info: HTTP {response.status_code}")
                return None
        except Exception as e:
            safe_print(f"❌ Error getting workspace info: {e}")
            return None
    
    def list_environments(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List all environments in a workspace."""
        safe_print(f"🔍 Discovering environments in workspace {workspace_id}...")
        
        url = f"{self.base_url}/workspaces/{workspace_id}/environments"
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                environments = response.json().get('value', [])
                safe_print(f"✅ Found {len(environments)} environment(s)")
                return environments
            else:
                safe_print(f"❌ Failed to list environments: HTTP {response.status_code}")
                if response.status_code == 404:
                    safe_print("   This workspace may not exist or you may not have access")
                return []
        except Exception as e:
            safe_print(f"❌ Error listing environments: {e}")
            return []
    
    def get_environment_details(self, workspace_id: str, environment_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific environment."""
        url = f"{self.base_url}/workspaces/{workspace_id}/environments/{environment_id}"
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            return None
    
    def display_workspace_summary(self, workspace_id: Optional[str] = None):
        """Display a comprehensive summary of workspaces and environments."""
        safe_print("🏢 FABRIC WORKSPACE & ENVIRONMENT DISCOVERY")
        safe_print("=" * 60)
        
        if workspace_id:
            # Show specific workspace
            workspace_info = self.get_workspace_info(workspace_id)
            if workspace_info:
                safe_print(f"\n📁 Workspace: {workspace_info.get('displayName', 'N/A')}")
                safe_print(f"   ID: {workspace_id}")
                safe_print(f"   Type: {workspace_info.get('type', 'N/A')}")
                
                environments = self.list_environments(workspace_id)
                if environments:
                    safe_print(f"\n🏗️ Environments ({len(environments)}):")
                    for env in environments:
                        self._display_environment_info(env, workspace_id)
                else:
                    safe_print("\n❌ No environments found in this workspace")
            else:
                safe_print(f"\n❌ Workspace {workspace_id} not found or inaccessible")
        else:
            # Show all workspaces
            workspaces = self.list_workspaces()
            if workspaces:
                for workspace in workspaces:
                    ws_id = workspace.get('id')
                    safe_print(f"\n📁 Workspace: {workspace.get('displayName', 'N/A')}")
                    safe_print(f"   ID: {ws_id}")
                    safe_print(f"   Type: {workspace.get('type', 'N/A')}")
                    
                    environments = self.list_environments(ws_id)
                    if environments:
                        safe_print(f"\n🏗️ Environments ({len(environments)}):")
                        for env in environments:
                            self._display_environment_info(env, ws_id)
                    else:
                        safe_print("   No environments found")
            else:
                safe_print("\n❌ No workspaces found or accessible")
    
    def _display_environment_info(self, env: Dict[str, Any], workspace_id: str):
        """Display detailed environment information."""
        env_id = env.get('id', 'N/A')
        env_name = env.get('displayName', 'N/A')
        env_status = env.get('runningStatus', 'Unknown')
        env_type = env.get('type', 'Unknown')
        
        # Get additional details
        details = self.get_environment_details(workspace_id, env_id)
        
        safe_print(f"\n   🏗️ {env_name}")
        safe_print(f"      ID: {env_id}")
        safe_print(f"      Status: {env_status}")
        safe_print(f"      Type: {env_type}")
        
        if details:
            # Show additional details if available
            spark_settings = details.get('sparkSettings', {})
            if spark_settings:
                driver_cores = spark_settings.get('driverCores', 'N/A')
                driver_memory = spark_settings.get('driverMemory', 'N/A')
                executor_cores = spark_settings.get('executorCores', 'N/A')
                executor_memory = spark_settings.get('executorMemory', 'N/A')
                
                safe_print(f"      Spark Driver: {driver_cores} cores, {driver_memory}")
                safe_print(f"      Spark Executor: {executor_cores} cores, {executor_memory}")
            
            # Check if environment supports staging
            if env_status in ['Running', 'ReadyForStaging']:
                safe_print(f"      📦 Staging: Ready for library uploads")
            else:
                safe_print(f"      ⚠️ Staging: Not ready (status: {env_status})")
        
        safe_print(f"      📋 Upload Command:")
        safe_print(f"         python tools/upload_wheel_to_fabric_enhanced.py \\")
        safe_print(f"             --workspace-id {workspace_id} \\")
        safe_print(f"             --environment-id {env_id} \\")
        safe_print(f"             --file dist/fabricla_connector-1.0.0-py3-none-any.whl")


def main():
    parser = argparse.ArgumentParser(description='Fabric Environment Discovery Tool')
    parser.add_argument('--workspace-id', help='Specific workspace ID to examine')
    parser.add_argument('--format', choices=['summary', 'json'], default='summary', 
                        help='Output format (default: summary)')
    
    # Authentication options
    parser.add_argument('--token', help='Bearer token for authentication')
    parser.add_argument('--client-id', help='Service principal client ID')
    parser.add_argument('--client-secret', help='Service principal client secret')
    parser.add_argument('--tenant-id', help='Azure tenant ID')
    
    args = parser.parse_args()
    
    try:
        discovery = FabricEnvironmentDiscovery(
            token=args.token,
            client_id=args.client_id,
            client_secret=args.client_secret,
            tenant_id=args.tenant_id
        )
        
        if args.format == 'json':
            # JSON output for programmatic use
            if args.workspace_id:
                workspace_info = discovery.get_workspace_info(args.workspace_id)
                environments = discovery.list_environments(args.workspace_id)
                result = {
                    'workspace': workspace_info,
                    'environments': environments
                }
            else:
                workspaces = discovery.list_workspaces()
                result = []
                for workspace in workspaces:
                    ws_id = workspace.get('id')
                    environments = discovery.list_environments(ws_id)
                    result.append({
                        'workspace': workspace,
                        'environments': environments
                    })
            
            print(json.dumps(result, indent=2))
        else:
            # Human-readable summary
            discovery.display_workspace_summary(args.workspace_id)
        
        sys.exit(0)
    
    except Exception as e:
        safe_print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()