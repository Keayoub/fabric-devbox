"""
Upload a wheel file to Azure Blob Storage.

Usage:
  python tools/upload_wheel_to_blob.py --file dist/your_package-1.0.0-py3-none-any.whl \
    --container <container> --connection-string "<conn>"

The script will print the blob URL. It can also generate a SAS token if requested (requires account key access).
"""
import argparse
import os
from datetime import datetime, timedelta
from typing import Optional, Any

try:
    from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
    AZURE_STORAGE_AVAILABLE = True
except Exception:
    BlobServiceClient = None
    generate_blob_sas = None
    BlobSasPermissions = None
    AZURE_STORAGE_AVAILABLE = False

try:
    # Prefer azure-identity for credential-based auth
    from azure.identity import DefaultAzureCredential, ClientSecretCredential
    AZURE_IDENTITY_AVAILABLE = True
except Exception:
    DefaultAzureCredential = None
    ClientSecretCredential = None
    AZURE_IDENTITY_AVAILABLE = False


def _build_blob_service_client(connection_string: Optional[str] = None, account_url: Optional[str] = None, credential: Optional[object] = None) -> Any:
    if not AZURE_STORAGE_AVAILABLE:
        raise RuntimeError("azure-storage-blob package is required. Install with 'pip install azure-storage-blob' to use this script")

    if credential is not None and account_url:
        # type: ignore[arg-type]
        return BlobServiceClient(account_url=account_url, credential=credential)
    if connection_string:
        # type: ignore[call-arg]
        return BlobServiceClient.from_connection_string(connection_string)
    raise ValueError("Either connection_string or (account_url and credential) must be provided")


def upload_wheel(file_path: str, container: str, *, connection_string: Optional[str] = None, account_url: Optional[str] = None, credential: Optional[object] = None) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Wheel not found: {file_path}")

    blob_name = os.path.basename(file_path)
    service = _build_blob_service_client(connection_string=connection_string, account_url=account_url, credential=credential)
    container_client = service.get_container_client(container)
    try:
        container_client.create_container()
    except Exception:
        # ignore if already exists or no permission
        pass

    blob_client = container_client.get_blob_client(blob_name)
    with open(file_path, "rb") as fh:
        blob_client.upload_blob(fh, overwrite=True)

    # Construct blob url
    account_url_used = service.url
    blob_url = f"{account_url_used}/{container}/{blob_name}"
    return blob_url


def generate_sas(blob_url: str, account_name: str, account_key: str, container: str, blob_name: str, hours: int = 24) -> str:
    if not AZURE_STORAGE_AVAILABLE or generate_blob_sas is None:
        raise RuntimeError("azure-storage-blob package is required for SAS generation. Install with 'pip install azure-storage-blob'")

    sas = generate_blob_sas(
        account_name=account_name,
        container_name=container,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=hours)
    )
    return f"{blob_url}?{sas}"


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to wheel file")
    parser.add_argument("--container", required=True, help="Blob container name")
    parser.add_argument("--connection-string", help="Azure Storage connection string")
    parser.add_argument("--account-url", help="Storage account URL (e.g. https://<acct>.blob.core.windows.net) - required for credential auth")
    parser.add_argument("--use-default-credential", action="store_true", help="Use DefaultAzureCredential to authenticate to Storage")
    parser.add_argument("--client-id", help="Service principal client id for Azure AD auth")
    parser.add_argument("--client-secret", help="Service principal client secret for Azure AD auth")
    parser.add_argument("--tenant-id", help="Azure tenant id for service principal auth")
    parser.add_argument("--generate-sas", action="store_true", help="Generate SAS token (requires account key in connection string)")
    parser.add_argument("--sas-hours", type=int, default=24, help="SAS expiry in hours")
    args = parser.parse_args()
    # Build credential if requested
    credential = None
    if args.client_id and args.client_secret and args.tenant_id:
        if ClientSecretCredential is None:
            raise RuntimeError("azure-identity is required for client secret credential authentication")
        credential = ClientSecretCredential(tenant_id=args.tenant_id, client_id=args.client_id, client_secret=args.client_secret)
    elif args.use_default_credential:
        if DefaultAzureCredential is None:
            raise RuntimeError("azure-identity is required for DefaultAzureCredential")
        credential = DefaultAzureCredential()

    # Decide whether to use connection string or account_url+credential
    if credential is not None:
        if not args.account_url:
            raise RuntimeError("--account-url is required when using credential-based authentication")
        url = upload_wheel(args.file, args.container, account_url=args.account_url, credential=credential)
    else:
        if not args.connection_string:
            raise RuntimeError("--connection-string is required when not using credential-based authentication")
        url = upload_wheel(args.file, args.container, connection_string=args.connection_string)

    print("Uploaded:", url)

    if args.generate_sas:
        # SAS generation requires the account key; only possible when connection string provided
        account_name = None
        account_key = None
        if args.connection_string:
            parts = dict(item.split("=", 1) for item in args.connection_string.split(";") if item)
            account_name = parts.get("AccountName")
            account_key = parts.get("AccountKey")

        if not account_key or not account_name:
            print("Cannot generate SAS: account key missing (SAS generation requires account key and cannot be done with AAD credentials)")
        else:
            blob_name = os.path.basename(args.file)
            sas_url = generate_sas(url, account_name, account_key, args.container, blob_name, args.sas_hours)
            print("SAS URL:", sas_url)
