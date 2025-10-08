#!/usr/bin/env python3
"""
Fabric Environment Upload Tool

This script uploads a package file (wheel, sdist, egg, zip, etc.) to a Fabric
Environment's staging libraries and optionally publishes the environment.

Key behaviors:
- Supported file types: any file type accepted by Fabric (we set the multipart
    Content-Type using Python's mimetypes.guess_type). Typical uses are .whl,
    .tar.gz (sdist), .zip, and eggs.
- Authentication precedence (highest -> lowest):
        1) --token (explicit bearer token)
        2) Service principal via --client-id/--client-secret/--tenant-id
        3) DefaultAzureCredential when requested via --use-default-credential
             (uses Azure CLI, Managed Identity, or environment credentials)

Behavioral details:
- Retries with exponential backoff on transient failures (configurable via
    --retries).
- Uploads to the Fabric staging libraries endpoint. If --publish is provided,
    the tool will attempt to publish the environment after a successful upload.
- Exit codes: 0 on success (upload and optional publish); non-zero when upload
    or publish fails.

Dependencies:
- requests (required)
- azure-identity (only required when using service principal or
    DefaultAzureCredential)

Examples:
        # Upload with bearer token
        python tools/upload_wheel_to_fabric.py --workspace-id <ws> --environment-id <env> --file dist/pkg.whl --token <bearer>

        # Upload using DefaultAzureCredential (requires --use-default-credential)
        python tools/upload_wheel_to_fabric.py --workspace-id <ws> --environment-id <env> --file dist/pkg.whl --use-default-credential

        # Upload using service principal
        python tools/upload_wheel_to_fabric.py --workspace-id <ws> --environment-id <env> --file dist/pkg.whl --client-id <id> --client-secret <secret> --tenant-id <tenant>
"""

import argparse
import os
import sys
import time
import json
import requests
from typing import Dict, Any, Optional

def safe_print(*args, **kwargs):
    """Print function that handles encoding issues on Windows."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Fall back to ASCII-only output
        ascii_args = []
        for arg in args:
            if isinstance(arg, str):
                # Remove or replace all Unicode characters
                arg = arg.encode('ascii', 'replace').decode('ascii')
            ascii_args.append(arg)
        print(*ascii_args, **kwargs)

try:
    from azure.identity import DefaultAzureCredential, ClientSecretCredential
    AZURE_IDENTITY_AVAILABLE = True
except ImportError:
    DefaultAzureCredential = None
    ClientSecretCredential = None
    AZURE_IDENTITY_AVAILABLE = False

class FabricEnvironmentManager:
    """Enhanced Fabric Environment manager with upload, publish capabilities, and retry logic."""
    
    def __init__(self, workspace_id: str, environment_id: str, 
                 token: Optional[str] = None, client_id: Optional[str] = None, 
                 client_secret: Optional[str] = None, tenant_id: Optional[str] = None,
                 use_default_credential: bool = False):
        self.workspace_id = workspace_id
        self.environment_id = environment_id
        self.base_url = "https://api.fabric.microsoft.com/v1"
        
        # Authentication
        self.use_default_credential = use_default_credential
        self.token = self._get_token(token, client_id, client_secret, tenant_id)
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'User-Agent': 'FabricLA-Connector/1.0.0'
        })
    
    def _get_token(self, token: Optional[str], client_id: Optional[str], client_secret: Optional[str], tenant_id: Optional[str]) -> str:
        """Get authentication token using various methods."""
        
        if token:
            safe_print("🔑 Using provided bearer token")
            return token
        
        if client_id and client_secret and tenant_id:
            if not AZURE_IDENTITY_AVAILABLE:
                raise Exception(
                    "Service principal authentication requires the 'azure-identity' package. "
                    "Install it in your environment with: pip install azure-identity"
                )

            safe_print("Using service principal authentication")
            # Construct credential at runtime to avoid static import issues when azure-identity is not installed
            from azure.identity import ClientSecretCredential as _ClientSecretCredential
            credential = _ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
            return credential.get_token("https://api.fabric.microsoft.com/.default").token

        if self.use_default_credential:
            if not AZURE_IDENTITY_AVAILABLE:
                raise Exception(
                    "DefaultAzureCredential requires the 'azure-identity' package. "
                    "Install it with: pip install azure-identity and ensure you have a valid login (az login) or managed identity."
                )

            safe_print("Using DefaultAzureCredential (Azure CLI / Managed Identity / Environment)")
            from azure.identity import DefaultAzureCredential as _DefaultAzureCredential
            credential = _DefaultAzureCredential()
            return credential.get_token("https://api.fabric.microsoft.com/.default").token
        
        raise Exception(
            "No authentication method available. Provide --token, or supply service principal credentials "
            "(--client-id, --client-secret, --tenant-id), or install 'azure-identity' and use --use-default-credential."
        )
    
    def upload_wheel(self, wheel_path: str, max_retries: int = 3) -> Dict[str, Any]:
        """Upload wheel file to staging libraries with retry logic."""
        
        if not os.path.exists(wheel_path):
            raise FileNotFoundError(f"Wheel file not found: {wheel_path}")
        
        wheel_name = os.path.basename(wheel_path)
        wheel_size = os.path.getsize(wheel_path)
        
        safe_print(f"📦 Uploading {wheel_name} ({wheel_size / 1024:.1f} KB)")
        
        for attempt in range(max_retries):
            try:
                result = self._attempt_upload(wheel_path, wheel_name)
                if result['success']:
                    return result
                
                # If this was the last attempt, return the error
                if attempt == max_retries - 1:
                    return result
                
                # Wait before retry
                wait_time = 2 ** attempt  # Exponential backoff
                safe_print(f"⏳ Upload attempt {attempt + 1} failed, retrying in {wait_time}s...")
                time.sleep(wait_time)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    return {
                        'success': False,
                        'error': f'Upload failed after {max_retries} attempts: {str(e)}',
                        'wheel_name': wheel_name
                    }
                
                wait_time = 2 ** attempt
                safe_print(f"❌ Upload attempt {attempt + 1} failed with exception: {str(e)}")
                safe_print(f"⏳ Retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        return {
            'success': False,
            'error': f'Upload failed after {max_retries} attempts',
            'wheel_name': wheel_name
        }
    
    def _attempt_upload(self, wheel_path: str, wheel_name: str) -> Dict[str, Any]:
        """Single upload attempt."""
        url = f"{self.base_url}/workspaces/{self.workspace_id}/environments/{self.environment_id}/staging/libraries"
        import mimetypes

        # Create proper multipart form data
        content_type = mimetypes.guess_type(wheel_path)[0] or 'application/octet-stream'
        with open(wheel_path, 'rb') as f:
            files = {
                'file': (wheel_name, f, content_type)
            }
            
            # Create new headers without Content-Type (requests will set it automatically for multipart)
            headers = {
                'Authorization': f'Bearer {self.token}',
                'User-Agent': 'FabricLA-Connector/1.0.0'
            }
            
            # Use fresh post request instead of session to avoid header conflicts
            response = requests.post(url, files=files, headers=headers, timeout=120)
        
        if response.status_code == 200:
            safe_print(f"✅ Upload successful: {wheel_name} (staged)")
            return {
                'success': True,
                'message': f'Library {wheel_name} uploaded to staging',
                'status_code': response.status_code,
                'wheel_name': wheel_name
            }
        else:
            error_msg = f"Upload failed: HTTP {response.status_code}"
            try:
                error_detail = response.json()
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {response.text[:200]}"  # Limit error text length
            
            safe_print(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'status_code': response.status_code,
                'wheel_name': wheel_name
            }
    
    def publish_environment(self) -> Dict[str, Any]:
        """Publish the environment to make staging changes effective."""
        
        safe_print("🚀 Publishing environment...")
        
        url = f"{self.base_url}/workspaces/{self.workspace_id}/environments/{self.environment_id}/staging/publish"
        
        response = self.session.post(url, timeout=120)
        
        if response.status_code in [200, 202]:
            safe_print("✅ Publish initiated successfully")
            
            # Check if it's a long-running operation
            if response.status_code == 202:
                operation_id = response.headers.get('x-ms-operation-id')
                safe_print(f"📊 Long-running operation ID: {operation_id}")
                
                # Wait for completion (optional)
                if operation_id:
                    return self._wait_for_publish_completion(operation_id)
                else:
                    return {
                        'success': True,
                        'message': 'Environment published successfully (no operation ID)',
                        'status_code': response.status_code
                    }
            
            return {
                'success': True,
                'message': 'Environment published successfully',
                'status_code': response.status_code
            }
        else:
            error_msg = f"Publish failed: HTTP {response.status_code}"
            try:
                error_detail = response.json()
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {response.text}"
            
            safe_print(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'status_code': response.status_code
            }
    
    def _wait_for_publish_completion(self, operation_id: str, max_wait: int = 300) -> Dict[str, Any]:
        """Wait for publish operation to complete."""
        
        if not operation_id:
            return {'success': True, 'message': 'Publish completed (no operation ID)'}
        
        operation_url = f"{self.base_url}/operations/{operation_id}"
        safe_print(f"⏳ Waiting for publish completion (max {max_wait}s)...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = self.session.get(operation_url)
                if response.status_code == 200:
                    operation_status = response.json()
                    status = operation_status.get('status', 'Unknown')
                    
                    if status == 'Succeeded':
                        safe_print("✅ Publish completed successfully")
                        return {
                            'success': True,
                            'message': 'Environment published and active',
                            'operation_status': operation_status
                        }
                    elif status == 'Failed':
                        error_msg = operation_status.get('error', 'Unknown error')
                        safe_print(f"❌ Publish failed: {error_msg}")
                        return {
                            'success': False,
                            'error': f'Publish operation failed: {error_msg}',
                            'operation_status': operation_status
                        }
                    elif status in ['Running', 'NotStarted']:
                        safe_print(f"⏳ Status: {status}")
                        time.sleep(10)
                    else:
                        safe_print(f"⚠️ Unknown status: {status}")
                        time.sleep(10)
                else:
                    safe_print(f"⚠️ Unable to check operation status: HTTP {response.status_code}")
                    time.sleep(10)
            except Exception as e:
                safe_print(f"⚠️ Error checking operation status: {e}")
                time.sleep(10)
        
        safe_print("⏰ Timeout waiting for publish completion")
        return {
            'success': False,
            'error': 'Timeout waiting for publish completion',
            'message': 'Check Fabric UI for publish status'
        }

def main():
    parser = argparse.ArgumentParser(description='Upload packages (whl, sdist, etc.) to Fabric Environment with optional publish and retry logic')
    parser.add_argument('--workspace-id', required=True, help='Fabric workspace ID')
    parser.add_argument('--environment-id', required=True, help='Fabric environment ID')
    parser.add_argument('--file', required=True, help='Path to package file')
    parser.add_argument('--publish', action='store_true', help='Publish environment after upload')
    parser.add_argument('--retries', type=int, default=3, help='Number of retry attempts (default: 3)')
    
    # Authentication options
    parser.add_argument('--token', help='Bearer token for authentication')
    parser.add_argument('--client-id', help='Service principal client ID')
    parser.add_argument('--client-secret', help='Service principal client secret')
    parser.add_argument('--tenant-id', help='Azure tenant ID')
    parser.add_argument('--use-default-credential', action='store_true', help='Use DefaultAzureCredential when available')
    
    args = parser.parse_args()
    
    try:
        # Initialize manager
        manager = FabricEnvironmentManager(
            workspace_id=args.workspace_id,
            environment_id=args.environment_id,
            token=args.token,
            client_id=args.client_id,
            client_secret=args.client_secret,
            tenant_id=args.tenant_id,
            use_default_credential=args.use_default_credential
        )
        
        # Upload wheel
        upload_result = manager.upload_wheel(args.file, max_retries=args.retries)
        
        if not upload_result['success']:
            sys.exit(1)
        
        # Publish if requested
        if args.publish:
            safe_print("🔄 Auto-publish enabled")
            publish_result = manager.publish_environment()
            
            if not publish_result['success']:
                safe_print("⚠️ Upload succeeded but publish failed")
                safe_print("💡 Package is in staging - you can publish manually from Fabric UI")
                sys.exit(1)
            else:
                safe_print("🎉 Upload and publish completed successfully!")
        else:
            safe_print("📋 Package uploaded to staging")
            safe_print("💡 Use Fabric UI or add --publish flag to make it active")
        
        safe_print(f"🎯 Workspace: {args.workspace_id}")
        safe_print(f"🎯 Environment: {args.environment_id}")
        
    except Exception as e:
        safe_print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()