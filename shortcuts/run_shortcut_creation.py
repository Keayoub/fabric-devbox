import subprocess
import sys

if __name__ == "__main__":
    # Example: pass all arguments from this script to the bulk create script
    # Usage: python run_shortcut_creation.py --account-url ... --container ... --connection-id ... --workspace ... --lakehouse ...
    args = sys.argv[1:]
    cmd = [
        sys.executable, "adlsgen2_fabric_shortcut_bulk_create.py"
    ] + args
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)
