#!/usr/bin/env python3
"""Create a Microsoft Fabric warehouse via REST API (Items API).

This tool creates a Warehouse item in a Fabric workspace by POSTing to
  POST {base_url}/workspaces/{workspaceId}/items

Auth precedence (highest->lowest): --token, service principal, --use-default-credential

Usage examples:
  python tools/create_fabric_warehouse.py --workspace-id <ws> --size medium --use-default-credential --dry-run
  python tools/create_fabric_warehouse.py --workspace-id <ws> --warehouse-file my_wh.json --token <bearer>
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import requests
from typing import Optional


def safe_print(*args, **kwargs):
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
except Exception:
    DefaultAzureCredential = None
    ClientSecretCredential = None
    AZURE_IDENTITY_AVAILABLE = False


class FabricAPI:
    def __init__(self, workspace_id: str, token: Optional[str] = None,
                 client_id: Optional[str] = None, client_secret: Optional[str] = None,
                 tenant_id: Optional[str] = None, use_default_credential: bool = False,
                 base_url: str = "https://api.fabric.microsoft.com/v1"):
        self.workspace_id = workspace_id
        self.base_url = base_url.rstrip('/')
        self.use_default_credential = use_default_credential
        self.token = self._get_token(token, client_id, client_secret, tenant_id)
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'User-Agent': 'FabricLA-Connector/1.0.0'
        })

    def _get_token(self, token: Optional[str], client_id: Optional[str], client_secret: Optional[str], tenant_id: Optional[str]) -> str:
        if token:
            safe_print('Using provided bearer token')
            return token

        if client_id and client_secret and tenant_id:
            if not AZURE_IDENTITY_AVAILABLE:
                raise RuntimeError("Service principal auth requires 'azure-identity' package")
            safe_print('Using service principal credentials')
            from azure.identity import ClientSecretCredential as _ClientSecret
            cred = _ClientSecret(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
            return cred.get_token('https://api.fabric.microsoft.com/.default').token

        if self.use_default_credential:
            if not AZURE_IDENTITY_AVAILABLE:
                raise RuntimeError("DefaultAzureCredential requires 'azure-identity'")
            safe_print('Using DefaultAzureCredential (Azure CLI / Managed Identity / Environment)')
            from azure.identity import DefaultAzureCredential as _Default
            cred = _Default()
            return cred.get_token('https://api.fabric.microsoft.com/.default').token

        raise RuntimeError('No authentication provided. Use --token or service principal or --use-default-credential')

    def create_warehouse(self, warehouse_payload: dict, endpoint_override: Optional[str] = None) -> dict:
        """Create a warehouse by posting to /workspaces/{workspaceId}/items with type 'Warehouse'.

        The API accepts an item with 'displayName', 'type': 'Warehouse', and an optional 'definition' with InlineBase64 parts.
        """
        # Prepare item payload: if it's already an Items-shaped payload, use it. Otherwise wrap as definition.
        if isinstance(warehouse_payload, dict) and warehouse_payload.get('displayName') and warehouse_payload.get('type'):
            item_payload = warehouse_payload
        else:
            try:
                encoded = base64.b64encode(json.dumps(warehouse_payload).encode('utf-8')).decode('ascii')
            except Exception:
                encoded = base64.b64encode(str(warehouse_payload).encode('utf-8')).decode('ascii')

            item_payload = {
                'displayName': warehouse_payload.get('displayName') if isinstance(warehouse_payload, dict) else 'Warehouse',
                'type': 'Warehouse',
                'definition': {
                    'parts': [
                        {
                            'path': 'warehouse-content.json',
                            'payload': encoded,
                            'payloadType': 'InlineBase64'
                        }
                    ]
                }
            }

        url = endpoint_override or f"{self.base_url}/workspaces/{self.workspace_id}/items"
        safe_print(f'Posting warehouse item to: {url}')
        resp = self.session.post(url, json=item_payload, timeout=90)
        try:
            body = resp.json()
        except Exception:
            body = resp.text

        return {'status': resp.status_code, 'body': body}


def main():
    p = argparse.ArgumentParser(description='Create a Fabric warehouse via REST API (Items API)')
    p.add_argument('--workspace-id', required=True, help='Fabric workspace ID')
    p.add_argument('--warehouse-file', help='Path to a JSON file describing the warehouse (will be wrapped as definition if not Items-shaped)')
    p.add_argument('--size', choices=['small', 'medium', 'large'], default='small', help='Simple size shortcut to generate a warehouse configuration')
    p.add_argument('--endpoint', help='Override the full API endpoint to POST the item to')

    # auth
    p.add_argument('--token', help='Bearer token')
    p.add_argument('--client-id', help='Service principal client id')
    p.add_argument('--client-secret', help='Service principal client secret')
    p.add_argument('--tenant-id', help='Azure tenant id')
    p.add_argument('--use-default-credential', action='store_true', help='Use DefaultAzureCredential')

    p.add_argument('--dry-run', action='store_true', help='Validate payload locally and don\'t call API')
    args = p.parse_args()

    # Build warehouse payload
    warehouse_payload = None
    if args.warehouse_file:
        try:
            with open(args.warehouse_file, 'r', encoding='utf-8') as fh:
                warehouse_payload = json.load(fh)
        except Exception as e:
            safe_print(f'Error reading warehouse file: {e}')
            sys.exit(2)
    else:
        # Generate a simple warehouse configuration based on size
        size_map = {
            'small': {'sku': 'DW100c', 'capacity': 100},
            'medium': {'sku': 'DW200c', 'capacity': 200},
            'large': {'sku': 'DW400c', 'capacity': 400}
        }
        config = size_map.get(args.size, size_map['small'])
        warehouse_payload = {
            'displayName': f'Warehouse-{args.size}',
            'properties': {
                'sku': config['sku'],
                'capacity': config['capacity'],
                'description': f'Auto-created warehouse ({args.size}) by create_fabric_warehouse.py'
            }
        }

    if args.dry_run:
        safe_print('Dry run: would create warehouse with payload:')
        safe_print(json.dumps(warehouse_payload, indent=2))
        sys.exit(0)

    try:
        client = FabricAPI(
            workspace_id=args.workspace_id,
            token=args.token,
            client_id=args.client_id,
            client_secret=args.client_secret,
            tenant_id=args.tenant_id,
            use_default_credential=args.use_default_credential
        )

        res = client.create_warehouse(warehouse_payload, endpoint_override=args.endpoint)
        safe_print('Response status:', res.get('status'))
        try:
            safe_print(json.dumps(res.get('body'), indent=2))
        except Exception:
            safe_print(res.get('body'))

        if res.get('status') not in (200, 201, 202):
            safe_print('Warehouse creation may have failed. Check logs and permissions.')
            sys.exit(1)

        safe_print('Warehouse created/accepted successfully')
        sys.exit(0)

    except Exception as e:
        safe_print(f'Exception: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
