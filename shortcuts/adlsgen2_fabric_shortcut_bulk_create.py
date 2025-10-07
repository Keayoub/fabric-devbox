import os
import argparse
import csv
import subprocess
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


def load_config(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def discover_folders_recursive(container_client, prefix='', max_depth=None, current_depth=0):
    folders = set()
    for blob in container_client.walk_blobs(name_starts_with=prefix, delimiter='/'):
        if hasattr(blob, 'name') and blob.name.endswith('/'):
            folder_name = blob.name.rstrip('/')
            folders.add(folder_name)
            if max_depth is None or current_depth < max_depth:
                folders.update(discover_folders_recursive(container_client, prefix=blob.name, max_depth=max_depth, current_depth=current_depth+1))
    return folders

def create_shortcut(args, folder_name, skip_folders, lakehouse_folder):
    if folder_name in skip_folders:
        print(f"Skipping folder: {folder_name}")
        return None
    shortcut_name = args.get('shortcut_template', 'shortcut_{folder}').format(folder=folder_name.replace('/', '_'))
    target = folder_name
    subpath = folder_name
    shortcut_type = args.get('shortcut_type', 'adlsGen2')
    # Build shortcut JSON based on type
    if shortcut_type == "adlsGen2" or shortcut_type == "storage":
        shortcut_json = {
            "location": args['account_url'],
            "subpath": f"/{subpath}",
            "connectionId": args['connection_id']
        }
    elif shortcut_type == "onedrive":
        shortcut_json = {
            "driveId": args['drive_id'],
            "itemId": args['item_id'],
            "connectionId": args['connection_id']
        }
    else:
        raise ValueError(f"Unsupported shortcut type: {shortcut_type}")
    shortcut_full_path = f"{args['workspace']}.workspace/{args['lakehouse']}.lakehouse/Files/{lakehouse_folder}/{target}/{shortcut_name}.Shortcut"
    fab_cmd = [
        "fab", "ln", shortcut_full_path,
        "--type", shortcut_type,
        "-i", str(shortcut_json).replace("'", '"'),
        "-f"
    ]
    print(f"Creating shortcut: {shortcut_full_path}")
    try:
        result = subprocess.run(fab_cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
    except Exception as e:
        print(f"Error running fab CLI: {e}")
    return {
        "location": args.get('account_url', ''),
        "subpath": subpath,
        "connectionId": args['connection_id'],
        "workspace": args['workspace'],
        "lakehouse": args['lakehouse'],
        "target": target,
        "shortcutName": shortcut_name
    }

def main():
    parser = argparse.ArgumentParser(description="Bulk create Fabric shortcuts from ADLS Gen2 folders.")
    parser.add_argument('--config', help='Path to YAML config file')
    parser.add_argument('--account-url', help='ADLS Gen2 account URL')
    parser.add_argument('--container', help='ADLS Gen2 container name')
    parser.add_argument('--connection-id', help='Fabric connectionId')
    parser.add_argument('--workspace', help='Fabric workspace name')
    parser.add_argument('--lakehouse', help='Fabric lakehouse name')
    parser.add_argument('--lakehouse-folder', help='Target folder in the lakehouse')
    parser.add_argument('--shortcut-type', default='adlsGen2', help='Shortcut type')
    parser.add_argument('--root-path', default='', help='Root path in the container to scan')
    parser.add_argument('--skip-folders', default='', help='Comma-separated list or file with folders to skip')
    parser.add_argument('--max-depth', type=int, default=None, help='Max recursion depth for folder discovery')
    parser.add_argument('--parallel', type=int, default=4, help='Number of parallel shortcut creations')
    parser.add_argument('--shortcut-template', default='shortcut_{folder}', help='Template for shortcut names')
    args = parser.parse_args()

    # Load config file if provided
    config = {}
    if args.config:
        config = load_config(args.config)
    # Merge CLI args over config file
    cli_args = {k: v for k, v in vars(args).items() if v is not None}
    config.update(cli_args)

    # Build skip list
    skip_folders = set()
    skip_val = config.get('skip_folders', '')
    if skip_val:
        if ',' in skip_val or not os.path.isfile(skip_val):
            skip_folders = set([f.strip() for f in skip_val.split(',') if f.strip()])
        else:
            with open(skip_val, 'r') as f:
                skip_folders = set([line.strip() for line in f if line.strip()])

    credential = DefaultAzureCredential()
    service_client = BlobServiceClient(account_url=config['account_url'], credential=credential)
    container_client = service_client.get_container_client(config['container'])

    # Recursive folder discovery
    folders = discover_folders_recursive(container_client, prefix=config.get('root_path', ''), max_depth=config.get('max_depth'))

    # Parallel shortcut creation
    results = []
    with ThreadPoolExecutor(max_workers=config.get('parallel', 4)) as executor:
        futures = [executor.submit(create_shortcut, config, folder, skip_folders, config['lakehouse_folder']) for folder in sorted(folders)]
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    # Write shortcuts.csv
    with open("shortcuts.csv", "w", newline='') as csvfile:
        fieldnames = ["location", "subpath", "connectionId", "workspace", "lakehouse", "target", "shortcutName"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print("All shortcuts created and shortcuts.csv written.")

if __name__ == "__main__":
    main()
