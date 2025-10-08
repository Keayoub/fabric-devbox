#!/usr/bin/env python3
"""Create a Microsoft Fabric pipeline via REST API.

This tool posts a pipeline definition (JSON) to a Fabric workspace.

Authentication precedence (highest->lowest):
  1) --token (explicit bearer token)
  2) Service principal via --client-id/--client-secret/--tenant-id
  3) DefaultAzureCredential via --use-default-credential

Usage examples:
  python tools/create_fabric_pipeline.py --workspace-id <ws> --pipeline-file my_pipeline.json --use-default-credential
  python tools/create_fabric_pipeline.py --workspace-id <ws> --pipeline-file my_pipeline.json --token <bearer>

Note: The script guesses a common Fabric pipelines endpoint but you can override it with --endpoint if your Fabric API differs.
"""

from __future__ import annotations

import argparse
import json
import sys
import base64
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
        self.base_url = base_url.rstrip("/")
        self.use_default_credential = use_default_credential
        self.token = self._get_token(token, client_id, client_secret, tenant_id)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "User-Agent": "FabricLA-Connector/1.0.0"
        })

    def _get_token(self, token: Optional[str], client_id: Optional[str], client_secret: Optional[str], tenant_id: Optional[str]) -> str:
        if token:
            safe_print("Using provided bearer token")
            return token

        if client_id and client_secret and tenant_id:
            if not AZURE_IDENTITY_AVAILABLE:
                raise RuntimeError("Service principal auth requires 'azure-identity' package")
            safe_print("Using service principal credentials")
            from azure.identity import ClientSecretCredential as _ClientSecret
            cred = _ClientSecret(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
            return cred.get_token("https://api.fabric.microsoft.com/.default").token

        if self.use_default_credential:
            if not AZURE_IDENTITY_AVAILABLE:
                raise RuntimeError("DefaultAzureCredential requires 'azure-identity'")
            safe_print("Using DefaultAzureCredential (Azure CLI / Managed Identity / Environment)")
            from azure.identity import DefaultAzureCredential as _DefaultAzure
            cred = _DefaultAzure()
            return cred.get_token("https://api.fabric.microsoft.com/.default").token

        raise RuntimeError("No authentication provided. Use --token or service principal or --use-default-credential")

    def create_pipeline(self, pipeline_json: dict, endpoint_override: Optional[str] = None) -> dict:
        """Post a pipeline definition to the Fabric API and return the parsed response.

        By default the tool will POST to:
          {base_url}/workspaces/{workspace_id}/pipelines

        If the API shape is different in your tenant, pass --endpoint to override the full path.
        """
        # Per Fabric docs, create pipeline items via the Items API:
        # POST {base_url}/workspaces/{workspaceId}/items
        tried = []

        # Build payload suitable for Items API. If the caller already provided an Items-shaped payload
        # (has 'displayName' and 'type' or 'definition'), use it as-is. Otherwise, wrap the provided
        # pipeline JSON as a base64 'definition' part.
        if isinstance(pipeline_json, dict) and (pipeline_json.get('displayName') and pipeline_json.get('type')):
            item_payload = pipeline_json
        elif isinstance(pipeline_json, dict) and 'definition' in pipeline_json:
            item_payload = pipeline_json
        else:
            # Wrap the entire pipeline_json as a single InlineBase64 part
            try:
                encoded = base64.b64encode(json.dumps(pipeline_json).encode('utf-8')).decode('ascii')
            except Exception:
                # fallback: stringify
                encoded = base64.b64encode(str(pipeline_json).encode('utf-8')).decode('ascii')

            item_payload = {
                "displayName": pipeline_json.get('displayName') or pipeline_json.get('name') or pipeline_json.get('id') or "Pipeline",
                "description": (pipeline_json.get('properties', {}).get('description') if isinstance(pipeline_json.get('properties'), dict) else None) or pipeline_json.get('description'),
                "type": "DataPipeline",
                "definition": {
                    "parts": [
                        {
                            "path": "pipeline-content.json",
                            "payload": encoded,
                            "payloadType": "InlineBase64"
                        }
                    ]
                }
            }

        if endpoint_override:
            candidates = [endpoint_override]
        else:
            candidates = [f"{self.base_url}/workspaces/{self.workspace_id}/items"]

        def _post_to(url: str):
            safe_print(f"Posting pipeline to: {url}")
            resp = self.session.post(url, json=item_payload, timeout=90)
            try:
                data = resp.json()
            except Exception:
                data = {"text": resp.text}
            return resp.status_code, data

        for url in candidates:
            status, data = _post_to(url)
            tried.append((url, status, data))
            if status in (200, 201, 202):
                safe_print("Pipeline created/accepted successfully")
                return {"success": True, "status_code": status, "data": data}

        # If POST to items fails, fall back to earlier environment discovery attempts for diagnostics
        safe_print("Initial POST to items failed; attempting environment-level discovery for diagnostics")
        envs_url = f"{self.base_url}/workspaces/{self.workspace_id}/environments"
        safe_print(f"Attempting to list environments at: {envs_url}")
        try:
            r = self.session.get(envs_url, timeout=30)
            envs = []
            if r.status_code == 200:
                try:
                    env_data = r.json()
                    if isinstance(env_data, dict) and 'value' in env_data and isinstance(env_data['value'], list):
                        envs = env_data['value']
                    elif isinstance(env_data, list):
                        envs = env_data
                except Exception:
                    envs = []
            else:
                safe_print(f"Unable to list environments: HTTP {r.status_code}")
        except Exception as e:
            safe_print(f"Error when listing environments: {e}")
            envs = []

        if envs:
            safe_print(f"Found {len(envs)} environment(s); probing environment endpoints for diagnostics")
            for env in envs:
                env_id = None
                if isinstance(env, dict):
                    env_id = env.get('id') or env.get('environmentId') or env.get('name')
                if not env_id:
                    continue
                env_url = f"{self.base_url}/workspaces/{self.workspace_id}/environments/{env_id}/items"
                status, data = _post_to(env_url)
                tried.append((env_url, status, data))
                if status in (200, 201, 202):
                    safe_print(f"Pipeline created under environment {env_id}")
                    return {"success": True, "status_code": status, "data": data}

        safe_print("Pipeline creation failed for all attempted endpoints. Diagnostic information follows:")
        diagnostic = {"attempts": []}
        for url, status, data in tried:
            diagnostic['attempts'].append({"url": url, "status": status, "data": data})

        return {"success": False, "status_code": tried[-1][1] if tried else None, "data": diagnostic}

    def discover_endpoints(self):
        """Discover common Fabric endpoints for this workspace and environments (GET only)."""
        results = {}
        def _get(url):
            safe_print(f"GET {url}")
            try:
                r = self.session.get(url, timeout=30)
                try:
                    data = r.json()
                except Exception:
                    data = r.text[:1000]
                return (r.status_code, data)
            except Exception as e:
                return (None, str(e))

        # workspace root
        ws_url = f"{self.base_url}/workspaces/{self.workspace_id}"
        results['workspace'] = _get(ws_url)

        # workspace-level pipelines (GET)
        results['workspace_pipelines'] = _get(f"{ws_url}/pipelines")

        # environments list
        envs_url = f"{ws_url}/environments"
        envs_status, envs_data = _get(envs_url)
        results['environments'] = (envs_status, envs_data)

        env_list = []
        if isinstance(envs_data, dict) and 'value' in envs_data and isinstance(envs_data['value'], list):
            env_list = envs_data['value']
        elif isinstance(envs_data, list):
            env_list = envs_data

        # probe each environment for common subresources
        results['environment_details'] = []
        for env in env_list:
            env_id = None
            if isinstance(env, dict):
                env_id = env.get('id') or env.get('environmentId') or env.get('name')
            if not env_id:
                continue
            env_entry = {'id': env_id}
            env_base = f"{ws_url}/environments/{env_id}"
            env_entry['self'] = _get(env_base)
            env_entry['pipelines'] = _get(f"{env_base}/pipelines")
            env_entry['jobs'] = _get(f"{env_base}/jobs")
            env_entry['notebooks'] = _get(f"{env_base}/notebooks")
            env_entry['dataPipelines'] = _get(f"{env_base}/dataPipelines")
            results['environment_details'].append(env_entry)

        return results


def main():
    p = argparse.ArgumentParser(description="Create a Fabric pipeline from JSON using Fabric REST API")
    p.add_argument("--workspace-id", required=True, help="Fabric workspace ID")
    p.add_argument("--pipeline-file", required=True, help="Path to pipeline JSON file")
    p.add_argument("--endpoint", help="Full API endpoint to POST the pipeline to (overrides default)")

    # auth
    p.add_argument("--token", help="Bearer token")
    p.add_argument("--client-id", help="Service principal client id")
    p.add_argument("--client-secret", help="Service principal client secret")
    p.add_argument("--tenant-id", help="Azure tenant id")
    p.add_argument("--use-default-credential", action="store_true", help="Use DefaultAzureCredential")

    p.add_argument("--dry-run", action="store_true", help="Validate payload locally and don't call API")
    p.add_argument("--discover", action="store_true", help="Run discovery of common Fabric endpoints (GET only)")
    p.add_argument("--try-put", action="store_true", help="If POST fails, try PUT to create/replace pipeline at a deterministic id")
    args = p.parse_args()

    # load JSON
    try:
        with open(args.pipeline_file, "r", encoding="utf-8") as fh:
            pipeline_json = json.load(fh)
    except Exception as e:
        safe_print(f"Error reading pipeline file: {e}")
        sys.exit(2)

    # Basic validation: require a displayName or id
    if not args.dry_run:
        if not isinstance(pipeline_json, dict):
            safe_print("Pipeline payload must be a JSON object")
            sys.exit(3)
        if "displayName" not in pipeline_json and "name" not in pipeline_json and "id" not in pipeline_json:
            safe_print("Warning: pipeline JSON does not contain 'displayName', 'name', or 'id'. Continuing but check payload.")

    if args.discover:
        try:
            client = FabricAPI(
                workspace_id=args.workspace_id,
                token=args.token,
                client_id=args.client_id,
                client_secret=args.client_secret,
                tenant_id=args.tenant_id,
                use_default_credential=args.use_default_credential
            )
            res = client.discover_endpoints()
            safe_print(json.dumps(res, indent=2))
            sys.exit(0)
        except Exception as e:
            safe_print(f"Discovery failed: {e}")
            sys.exit(1)

    if args.dry_run:
        safe_print("Dry run: payload OK, not sending to API")
        safe_print(json.dumps(pipeline_json, indent=2))
        sys.exit(0)

    # If user asked to try PUT, we'll attempt to PUT to workspace and environment endpoints
    if args.try_put:
        pipeline_id = None
        if isinstance(pipeline_json, dict):
            pipeline_id = pipeline_json.get('id') or pipeline_json.get('name')
        if not pipeline_id:
            safe_print("No pipeline id found in payload to use for PUT; please include an 'id' field in the JSON")
            sys.exit(2)

        try:
            client = FabricAPI(
                workspace_id=args.workspace_id,
                token=args.token,
                client_id=args.client_id,
                client_secret=args.client_secret,
                tenant_id=args.tenant_id,
                use_default_credential=args.use_default_credential
            )

            # Try workspace-level PUT
            ws_put_url = f"{client.base_url}/workspaces/{client.workspace_id}/pipelines/{pipeline_id}"
            safe_print(f"Attempting PUT to: {ws_put_url}")
            resp = client.session.put(ws_put_url, json=pipeline_json, timeout=60)
            try:
                resp_data = resp.json()
            except Exception:
                resp_data = resp.text

            safe_print(f"PUT {ws_put_url} -> {resp.status_code}")
            safe_print(json.dumps(resp_data, indent=2) if isinstance(resp_data, (dict, list)) else str(resp_data))

            if resp.status_code in (200, 201, 202):
                safe_print("Pipeline created/replaced successfully via workspace-level PUT")
                sys.exit(0)

            # If not successful, try environment-level PUTs
            envs_url = f"{client.base_url}/workspaces/{client.workspace_id}/environments"
            r = client.session.get(envs_url, timeout=30)
            envs = []
            if r.status_code == 200:
                try:
                    ed = r.json()
                    if isinstance(ed, dict) and 'value' in ed:
                        envs = ed['value']
                    elif isinstance(ed, list):
                        envs = ed
                except Exception:
                    envs = []

            for env in envs:
                env_id = None
                if isinstance(env, dict):
                    env_id = env.get('id') or env.get('environmentId') or env.get('name')
                if not env_id:
                    continue
                env_put_url = f"{client.base_url}/workspaces/{client.workspace_id}/environments/{env_id}/pipelines/{pipeline_id}"
                safe_print(f"Attempting PUT to: {env_put_url}")
                r2 = client.session.put(env_put_url, json=pipeline_json, timeout=60)
                try:
                    r2d = r2.json()
                except Exception:
                    r2d = r2.text
                safe_print(f"PUT {env_put_url} -> {r2.status_code}")
                safe_print(json.dumps(r2d, indent=2) if isinstance(r2d, (dict, list)) else str(r2d))
                if r2.status_code in (200, 201, 202):
                    safe_print(f"Pipeline created/replaced successfully under environment {env_id}")
                    sys.exit(0)

            safe_print("PUT attempts completed; pipeline not created. See above responses for details.")
            sys.exit(1)

        except Exception as e:
            safe_print(f"Exception during PUT attempts: {e}")
            sys.exit(1)

    try:
        client = FabricAPI(
            workspace_id=args.workspace_id,
            token=args.token,
            client_id=args.client_id,
            client_secret=args.client_secret,
            tenant_id=args.tenant_id,
            use_default_credential=args.use_default_credential
        )

        result = client.create_pipeline(pipeline_json, endpoint_override=args.endpoint)
        if not result.get("success"):
            safe_print("ERROR: pipeline creation failed")
            safe_print(json.dumps(result.get("data", {}), indent=2))
            sys.exit(1)

        safe_print("Result:")
        safe_print(json.dumps(result.get("data", {}), indent=2))
        sys.exit(0)

    except Exception as e:
        safe_print(f"Exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
