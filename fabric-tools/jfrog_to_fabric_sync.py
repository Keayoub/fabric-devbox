#!/usr/bin/env python3
"""
Mirror packages from a JFrog Artifactory (or any PyPI-compatible/simple index) into a Fabric Environment.

Features:
- Enumerates packages via PyPI "simple" index or Artifactory /api/storage listing
- Downloads distributions into a local cache directory
- Tracks uploaded artifacts in a JSON state file to avoid re-uploading
- Uploads wheel files to Fabric staging using FabricEnvironmentManager from tools/upload_wheel_to_fabric.py

Auth for JFrog:
- API key via X-JFrog-Art-Api header
- Basic auth (username/password)

Only wheel files are uploaded by default. Sdists are downloaded but skipped unless you add a build step.

Usage (Windows cmd.exe):
  python tools\jfrog_to_fabric_sync.py --jfrog-base https://myjfrog.example/artifactory --repo my-repo --package-name mypkg --workspace-id <WS> --environment-id <ENV> --jfrog-api-key <API_KEY> --fabric-token <FABRIC_TOKEN>

"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from typing import Any, Dict, Iterable, List, Optional

import requests

# Try to import the Fabric manager
try:
    from tools.upload_wheel_to_fabric import FabricEnvironmentManager
except Exception:
    try:
        from upload_wheel_to_fabric import FabricEnvironmentManager
    except Exception:
        FabricEnvironmentManager = None

STATE_FILENAME = "jfrog_mirror_state.json"
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
                safe_print("WARNING: Could not read existing state file; starting fresh")
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


def artifactory_list(repo_base: str, repo: str, session: requests.Session) -> Iterable[Dict[str, Any]]:
    """
    List files in an Artifactory repository using the storage API.
    Calls: GET {repo_base}/api/storage/{repo}?list&deep=1&listFolders=0
    Yields entries with at least 'uri' and 'size'.
    """
    base = repo_base.rstrip("/")
    api_url = f"{base}/api/storage/{repo}"
    params = {"list": "1", "deep": "1", "listFolders": "0"}
    safe_print(f"INFO: Listing Artifactory repo {repo} via {api_url}")
    r = session.get(api_url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    for f in data.get("files", []):
        yield f


def pypi_simple_list(base: str, pkg_name: str, session: requests.Session) -> List[str]:
    idx = base.rstrip("/") + f"/simple/{pkg_name}/"
    safe_print(f"INFO: Fetching simple index {idx}")
    r = session.get(idx, timeout=30)
    r.raise_for_status()
    html = r.text
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    out = []
    for u in hrefs:
        if u.startswith("http"):
            out.append(u)
        else:
            out.append(idx.rstrip("/") + "/" + u.lstrip("/"))
    return out


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
            safe_print(f"WARNING: Download attempt {attempts}/{max_retries} failed for {url}: {e}")
            if attempts >= max_retries:
                raise
            time.sleep(2 ** (attempts - 1))


def determine_files_from_artifactory_entry(base_url: str, repo: str, entry: dict) -> Optional[Dict[str, str]]:
    uri = entry.get("uri")
    if not uri:
        return None
    full_url = base_url.rstrip("/") + f"/{repo}" + uri
    filename = os.path.basename(uri)
    return {"url": full_url, "filename": filename}


def mirror_package_from_jfrog(pkg_name: str, jfrog_base: str, repo: str, session: requests.Session,
                             cache_dir: str, state: MirrorState, fabric_mgr: FabricEnvironmentManager,
                             upload_wheels_only: bool = True, publish_after: bool = False) -> None:
    os.makedirs(cache_dir, exist_ok=True)
    safe_print(f"INFO: Mirroring package: {pkg_name}")

    entries: List[Dict[str, str]] = []
    # Try simple index first
    try:
        urls = pypi_simple_list(jfrog_base.rstrip('/') + f"/{repo}", pkg_name, session)
        for u in urls:
            fname = os.path.basename(u.split('?')[0])
            entries.append({"url": u, "filename": fname})
    except Exception:
        safe_print("WARNING: Simple index fetch failed, falling back to Artifactory storage API")
        for entry in artifactory_list(jfrog_base, repo, session):
            info = determine_files_from_artifactory_entry(jfrog_base, repo, entry)
            if info:
                entries.append(info)

    safe_print(f"INFO: Found {len(entries)} items for {pkg_name}")
    entries = [e for e in entries if e["filename"].lower().endswith(VALID_DISTS)]
    if not entries:
        safe_print("WARNING: No distribution files found; skipping")
        return

    for e in entries:
        filename = e["filename"]
        url = e["url"]
        local_path = os.path.join(cache_dir, filename)

        if not os.path.exists(local_path):
            safe_print(f"Downloading {filename} from {url}")
            try:
                download_url_to_path(session, url, local_path)
            except Exception as ex:
                safe_print(f"ERROR: Failed to download {url}: {ex}")
                continue

        sha256 = sha256_of_file(local_path)
        if state.is_uploaded(pkg_name, filename, sha256):
            safe_print(f"INFO: Already uploaded {filename}, skipping")
            continue

        if upload_wheels_only and not filename.lower().endswith('.whl'):
            safe_print(f"INFO: Skipping non-wheel {filename} (enable sdist handling if needed)")
            continue
        safe_print(f"Uploading {filename} to Fabric (workspace={fabric_mgr.workspace_id})")
        try:
            upload_result = fabric_mgr.upload_wheel(local_path, max_retries=3)
            if upload_result.get("success"):
                state.mark_uploaded(pkg_name, filename, sha256, upload_result)
                safe_print(f"INFO: Uploaded and recorded: {filename}")
            else:
                safe_print(f"ERROR: Upload failed for {filename}: {upload_result.get('error')}")
        except Exception as ex:
            safe_print(f"ERROR: Exception during upload of {filename}: {ex}")

    if publish_after:
        safe_print("INFO: Publishing environment after uploads")
        try:
            pub = fabric_mgr.publish_environment()
            if pub.get("success"):
                safe_print("INFO: Publish succeeded")
            else:
                safe_print(f"WARNING: Publish returned error: {pub.get('error')}")
        except Exception as e:
            safe_print(f"ERROR: Publish failed: {e}")


def build_jfrog_session(api_key: Optional[str], username: Optional[str], password: Optional[str]) -> requests.Session:
    s = requests.Session()
    if api_key:
        s.headers.update({"X-JFrog-Art-Api": api_key})
    if username and password:
        s.auth = (username, password)
    return s


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Mirror packages from JFrog/Artifactory into Fabric Environment.")
    parser.add_argument("--jfrog-base", required=True, help="Artifactory base URL (e.g. https://myjfrog.example/artifactory)")
    parser.add_argument("--repo", required=True, help="Repository name in Artifactory")
    parser.add_argument("--package-name", help="Single package name to mirror")
    parser.add_argument("--package-list-file", help="File with package names (one per line)")
    parser.add_argument("--jfrog-api-key", help="JFrog API key (X-JFrog-Art-Api header)")
    parser.add_argument("--jfrog-user", help="JFrog username for basic auth")
    parser.add_argument("--jfrog-pass", help="JFrog password for basic auth")
    parser.add_argument("--cache", default=".jfrog_mirror_cache", help="Local cache directory")
    parser.add_argument("--workspace-id", required=True, help="Fabric workspace id")
    parser.add_argument("--environment-id", required=True, help="Fabric environment id")
    parser.add_argument("--publish", action="store_true", help="Publish environment after uploads")
    parser.add_argument("--upload-wheels-only", action="store_true", default=True, help="Upload only wheel files (default True)")
    parser.add_argument("--fabric-token", help="Fabric bearer token")
    parser.add_argument("--fabric-client-id", help="Fabric service principal client id")
    parser.add_argument("--fabric-client-secret", help="Fabric service principal client secret")
    parser.add_argument("--fabric-tenant-id", help="Fabric tenant id")
    args = parser.parse_args(argv)

    if FabricEnvironmentManager is None:
        safe_print("ERROR: Could not import FabricEnvironmentManager from tools/upload_wheel_to_fabric.py. Ensure you run this from the repo root and the file exists.")
        sys.exit(2)

    session = build_jfrog_session(args.jfrog_api_key, args.jfrog_user, args.jfrog_pass)

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
        safe_print("ERROR: No package source provided. Use --package-name or --package-list-file.")
        sys.exit(2)

    for pkg in pkg_iter:
        safe_print(f"Processing package {pkg}")
        mirror_package_from_jfrog(pkg, args.jfrog_base, args.repo, session, cache_dir, state, fabric_mgr, upload_wheels_only=args.upload_wheels_only, publish_after=args.publish)

    safe_print("Mirror run complete")


if __name__ == "__main__":
    main()
