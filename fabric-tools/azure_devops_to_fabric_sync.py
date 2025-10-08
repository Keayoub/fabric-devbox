#!/usr/bin/env python3
"""
Mirror packages from an Azure DevOps Artifacts PyPI feed into a Fabric Environment.

This script supports:
- PyPI-style simple index served by Azure Artifacts (recommended):
  https://pkgs.dev.azure.com/{org}/{project}/_packaging/{feed}/pypi/simple/
- Azure DevOps Packaging REST API fallback to enumerate packages in a feed.
- Downloads distributions into a local cache, tracks uploaded artifacts in a JSON state file,
  and uploads wheel files to Fabric staging using `FabricEnvironmentManager` from
  `tools/upload_wheel_to_fabric.py`.

Auth for Azure DevOps: Personal Access Token (PAT). The script sends it as Basic auth
(username can be empty) or as header when calling the simple index.

Only wheel files are uploaded by default. Sdists are downloaded but skipped unless you
add a build step to turn them into wheels.

Usage (Windows cmd.exe):
  python tools\azure_devops_to_fabric_sync.py \
    --org myorg --project myproj --feed myfeed --package-name mypkg \
    --pat <PERSONAL_ACCESS_TOKEN> --workspace-id <WS> --environment-id <ENV> --cache .\cache

"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import sys
import time
from typing import Any, Dict, Iterable, List, Optional

import requests
try:
    from azure.identity import DefaultAzureCredential, ClientSecretCredential
    AZURE_IDENTITY_AVAILABLE = True
except Exception:
    DefaultAzureCredential = None
    ClientSecretCredential = None
    AZURE_IDENTITY_AVAILABLE = False

# Try to import the Fabric manager from your tools file.
try:
    from tools.upload_wheel_to_fabric import FabricEnvironmentManager
except Exception:
    try:
        from upload_wheel_to_fabric import FabricEnvironmentManager
    except Exception:
        FabricEnvironmentManager = None

STATE_FILENAME = "azure_devops_mirror_state.json"
VALID_DISTS = (".whl", ".tar.gz", ".zip")


def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        out = []
        for a in args:
            if isinstance(a, str):
                out.append(a.encode("ascii", "replace").decode("ascii"))
            else:
                out.append(str(a))
        print(*out, **kwargs)


def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class MirrorState:
    def __init__(self, path: str):
        self.path = path
        self._data: Dict[str, Dict[str, Any]] = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                safe_print("⚠️ Could not read existing state file; starting fresh")
                self._data = {}

    def save(self) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, sort_keys=True)
        shutil.move(tmp, self.path)

    def is_uploaded(self, pkg_name: str, filename: str, sha256: str) -> bool:
        key = f"{pkg_name}:{filename}"
        rec = self._data.get(key)
        return bool(rec and rec.get("sha256") == sha256 and rec.get("uploaded") is True)

    def mark_uploaded(self, pkg_name: str, filename: str, sha256: str, upload_meta: dict) -> None:
        key = f"{pkg_name}:{filename}"
        self._data[key] = {
            "sha256": sha256,
            "uploaded": True,
            "upload_meta": upload_meta,
            "ts": int(time.time()),
        }
        self.save()


def azure_pypi_simple_index(base: str, org: str, project: Optional[str], feed: str, pkg_name: str, session: requests.Session) -> List[str]:
    """
    Build the simple index URL for Azure Artifacts and return all hrefs found.
    Example simple index URL:
      https://pkgs.dev.azure.com/{org}/{project}/_packaging/{feed}/pypi/simple/{pkg}/
    If `project` is None, omit it: https://pkgs.dev.azure.com/{org}/_packaging/{feed}/pypi/simple/{pkg}/
    """
    base = base.rstrip("/") if base else "https://pkgs.dev.azure.com"
    if project:
        idx = f"{base}/{org}/{project}/_packaging/{feed}/pypi/simple/{pkg_name}/"
    else:
        idx = f"{base}/{org}/_packaging/{feed}/pypi/simple/{pkg_name}/"
    safe_print(f"📡 Fetching simple index {idx}")
    r = session.get(idx, timeout=30)
    r.raise_for_status()
    html = r.text
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    out: List[str] = []
    for u in hrefs:
        if u.startswith("http"):
            out.append(u)
        else:
            out.append(idx.rstrip("/") + "/" + u.lstrip("/"))
    return out


def azure_devops_list_packages_via_api(base: str, org: str, project: Optional[str], feed: str, session: requests.Session) -> List[str]:
    """
    Use Azure DevOps Packaging REST API to enumerate packages in a feed.
    API endpoint (example):
      GET https://feeds.dev.azure.com/{org}/{project}/_apis/packaging/feeds/{feed}/packages?api-version=6.0-preview.1

    Returns a list of package names (for pypi, names as registered).
    """
    base = base.rstrip("/") if base else "https://feeds.dev.azure.com"
    if project:
        api = f"{base}/{org}/{project}/_apis/packaging/feeds/{feed}/packages"
    else:
        api = f"{base}/{org}/_apis/packaging/feeds/{feed}/packages"
    params = {"api-version": "6.0-preview.1", "protocolType": "pypi"}
    safe_print(f"📡 Listing feed packages via API: {api}")
    r = session.get(api, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    names: List[str] = []
    for pkg in data.get("value", []):
        # package name is in 'name' or 'normalizedName' depending on API
        name = pkg.get("name") or pkg.get("normalizedName")
        if name:
            names.append(name)
    return names


def download_url_to_path(session: requests.Session, url: str, dest_path: str, max_retries: int = 3) -> None:
    attempts = 0
    while attempts < max_retries:
        attempts += 1
        try:
            with session.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                tmp = dest_path + ".part"
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                shutil.move(tmp, dest_path)
            return
        except Exception as e:
            safe_print(f"⚠️ Download attempt {attempts}/{max_retries} failed for {url}: {e}")
            if attempts >= max_retries:
                raise
            time.sleep(2 ** (attempts - 1))


def mirror_package_from_azure(pkg_name: str, base: str, org: str, project: Optional[str], feed: str,
                              session: requests.Session, cache_dir: str, state: MirrorState,
                              fabric_mgr: Any, upload_wheels_only: bool = True,
                              publish_after: bool = False) -> None:
    os.makedirs(cache_dir, exist_ok=True)
    safe_print(f"🔎 Mirroring package: {pkg_name}")

    # Try simple index first
    entries: List[Dict[str, str]] = []
    try:
        urls = azure_pypi_simple_index(base, org, project, feed, pkg_name, session)
        for u in urls:
            fname = os.path.basename(u.split("?")[0])
            entries.append({"url": u, "filename": fname})
    except Exception:
        safe_print("⚠️ Simple index fetch failed, falling back to REST API listing")
        try:
            names = azure_devops_list_packages_via_api(base, org, project, feed, session)
            # If API listing returns names, we need to query simple index per package
            if pkg_name not in names:
                safe_print(f"⚠️ Package {pkg_name} not found in feed via API; skipping")
                return
            # Try simple index again but using session (in case earlier session lacked auth/header)
            urls = azure_pypi_simple_index(base, org, project, feed, pkg_name, session)
            for u in urls:
                fname = os.path.basename(u.split("?")[0])
                entries.append({"url": u, "filename": fname})
        except Exception as e:
            safe_print(f"❌ Could not enumerate package files: {e}")
            return

    safe_print(f"ℹ️ Found {len(entries)} items for {pkg_name}")
    entries = [e for e in entries if e["filename"].lower().endswith(VALID_DISTS)]
    if not entries:
        safe_print("⚠️ No distribution files found matching known extensions; skipping")
        return

    for e in entries:
        filename = e["filename"]
        url = e["url"]
        local_path = os.path.join(cache_dir, filename)

        if not os.path.exists(local_path):
            safe_print(f"⬇️ Downloading {filename} from {url}")
            try:
                download_url_to_path(session, url, local_path)
            except Exception as ex:
                safe_print(f"❌ Failed to download {url}: {ex}")
                continue

        sha256 = sha256_of_file(local_path)
        if state.is_uploaded(pkg_name, filename, sha256):
            safe_print(f"✅ Already uploaded {filename}, skipping")
            continue

        if upload_wheels_only and not filename.lower().endswith(".whl"):
            safe_print(f"ℹ️ Skipping non-wheel {filename} (enable sdist handling to upload these)")
            continue

        safe_print(f"⬆️ Uploading {filename} to Fabric (workspace={fabric_mgr.workspace_id})")
        try:
            upload_result = fabric_mgr.upload_wheel(local_path, max_retries=3)
            if upload_result.get("success"):
                state.mark_uploaded(pkg_name, filename, sha256, upload_result)
                safe_print(f"✅ Uploaded and recorded: {filename}")
            else:
                safe_print(f"❌ Upload failed for {filename}: {upload_result.get('error')}")
        except Exception as ex:
            safe_print(f"❌ Exception during upload of {filename}: {ex}")

    if publish_after:
        safe_print("🔄 Publishing environment after uploads")
        try:
            pub = fabric_mgr.publish_environment()
            if pub.get("success"):
                safe_print("✅ Publish OK")
            else:
                safe_print(f"⚠️ Publish returned error: {pub.get('error')}")
        except Exception as e:
            safe_print(f"❌ Publish failed: {e}")


def build_azure_session(pat: Optional[str], client_id: Optional[str] = None, client_secret: Optional[str] = None, tenant_id: Optional[str] = None, use_aad: bool = False) -> requests.Session:
    """
    Build a requests.Session for Azure DevOps access.

    Priority:
      - If --use-aad is False and PAT provided -> Basic auth with PAT
      - If client_id/client_secret/tenant_id provided -> ClientSecretCredential
      - Else if azure-identity available -> DefaultAzureCredential
      - Else fall back to PAT if provided, otherwise unauthenticated
    """
    s = requests.Session()
    # If PAT provided and user didn't force AAD, use Basic auth
    if pat and not use_aad:
        token = base64.b64encode(f":{pat}".encode("utf-8")).decode("ascii")
        s.headers.update({"Authorization": f"Basic {token}"})
        return s

    # Prefer explicit client secret credential when provided
    if client_id and client_secret and tenant_id:
        if ClientSecretCredential is None:
            safe_print("❌ ClientSecretCredential not available; install azure-identity to use service principal auth")
        else:
            try:
                safe_print("🔑 Acquiring AAD token via ClientSecretCredential for Azure DevOps")
                cred = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
                token = cred.get_token("499b84ac-1321-427f-aa17-267ca6975798/.default").token
                s.headers.update({"Authorization": f"Bearer {token}"})
                return s
            except Exception as e:
                safe_print(f"⚠️ ClientSecretCredential token acquisition failed: {e}")

    # If azure-identity is available, try DefaultAzureCredential
    if AZURE_IDENTITY_AVAILABLE and DefaultAzureCredential is not None:
        try:
            safe_print("🔑 Acquiring AAD token via DefaultAzureCredential for Azure DevOps")
            cred = DefaultAzureCredential()
            token = cred.get_token("499b84ac-1321-427f-aa17-267ca6975798/.default").token
            s.headers.update({"Authorization": f"Bearer {token}"})
            return s
        except Exception as e:
            safe_print(f"⚠️ DefaultAzureCredential token acquisition failed: {e}")

    # Last resort: use PAT if provided
    if pat:
        token = base64.b64encode(f":{pat}".encode("utf-8")).decode("ascii")
        s.headers.update({"Authorization": f"Basic {token}"})
        return s

    safe_print("ℹ️ No credentials available for Azure DevOps; API calls will be unauthenticated and likely fail")
    return s


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Mirror packages from an Azure DevOps Artifacts PyPI feed into Fabric Environment.")
    parser.add_argument("--base", help="Base URL for Azure DevOps (default https://pkgs.dev.azure.com)", default="https://pkgs.dev.azure.com")
    parser.add_argument("--org", required=True, help="Azure DevOps organization")
    parser.add_argument("--project", help="Azure DevOps project (optional)")
    parser.add_argument("--feed", required=True, help="Feed name or id")
    parser.add_argument("--package-name", help="Single package name to mirror")
    parser.add_argument("--package-list-file", help="File with package names (one per line)")
    parser.add_argument("--pat", help="Azure DevOps Personal Access Token (PAT)")
    parser.add_argument("--cache", default=".azure_devops_mirror_cache", help="Local cache directory")
    parser.add_argument("--workspace-id", required=True, help="Fabric workspace id")
    parser.add_argument("--environment-id", required=True, help="Fabric environment id")
    parser.add_argument("--publish", action="store_true", help="Publish environment after uploads")
    parser.add_argument("--upload-wheels-only", action="store_true", default=True, help="Upload only wheel files (default True)")
    # Fabric auth options (passed to FabricEnvironmentManager)
    parser.add_argument("--fabric-token", help="Fabric bearer token")
    parser.add_argument("--fabric-client-id", help="Fabric service principal client id")
    parser.add_argument("--fabric-client-secret", help="Fabric service principal client secret")
    parser.add_argument("--fabric-tenant-id", help="Fabric tenant id")
    args = parser.parse_args(argv)

    if FabricEnvironmentManager is None:
        safe_print("❌ Could not import FabricEnvironmentManager from tools/upload_wheel_to_fabric.py. Ensure you run this from the repo root and the file exists.")
        sys.exit(2)

    s = build_azure_session(args.pat)

    fabric_mgr = FabricEnvironmentManager(
        workspace_id=args.workspace_id,
        environment_id=args.environment_id,
        token=args.fabric_token,
        client_id=args.fabric_client_id,
        client_secret=args.fabric_client_secret,
        tenant_id=args.fabric_tenant_id,
    )

    cache_dir = args.cache
    os.makedirs(cache_dir, exist_ok=True)
    state = MirrorState(os.path.join(cache_dir, STATE_FILENAME))

    pkg_iter: Iterable[str] = ()
    if args.package_name:
        pkg_iter = [args.package_name]
    elif args.package_list_file:
        with open(args.package_list_file, "r", encoding="utf-8") as f:
            pkg_iter = [ln.strip() for ln in f if ln.strip()]
    else:
        safe_print("❌ No package source provided. Use --package-name or --package-list-file.")
        sys.exit(2)

    for pkg in pkg_iter:
        safe_print(f"➡️ Processing package {pkg}")
        mirror_package_from_azure(pkg, args.base, args.org, args.project, args.feed, s, cache_dir, state, fabric_mgr, upload_wheels_only=args.upload_wheels_only, publish_after=args.publish)

    safe_print("🎯 Mirror run complete")


if __name__ == "__main__":
    main()
