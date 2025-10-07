"""
Validate OneLake Datastore Connection in Azure ML

This script validates that your OneLake datastore is properly configured
and accessible from Azure ML.
"""

import sys
import os

def check_imports():
    """Check if required packages are installed"""
    print("🔍 Checking dependencies...")
    required_packages = {
        'azure.ai.ml': 'azure-ai-ml',
        'azure.identity': 'azure-identity',
    }
    
    missing = []
    for module, package in required_packages.items():
        try:
            __import__(module)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - NOT INSTALLED")
            missing.append(package)
    
    if missing:
        print("\n❌ Missing packages. Install with:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    print("✅ All dependencies installed\n")
    return True

def validate_datastore():
    """Validate OneLake datastore registration and accessibility"""
    from azure.ai.ml import MLClient
    from azure.identity import DefaultAzureCredential
    
    # Get configuration from environment variables
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    resource_group = os.getenv("AZURE_RESOURCE_GROUP")
    workspace_name = os.getenv("AZURE_ML_WORKSPACE")
    
    if not all([subscription_id, resource_group, workspace_name]):
        print("❌ Missing required environment variables:")
        print("   - AZURE_SUBSCRIPTION_ID")
        print("   - AZURE_RESOURCE_GROUP")
        print("   - AZURE_ML_WORKSPACE")
        print("\nSet them with:")
        print("   set AZURE_SUBSCRIPTION_ID=<your-subscription-id>")
        print("   set AZURE_RESOURCE_GROUP=<your-resource-group>")
        print("   set AZURE_ML_WORKSPACE=<your-workspace-name>")
        return False
    
    print("=" * 70)
    print("OneLake Datastore Validation")
    print("=" * 70)
    print(f"\n📋 Configuration:")
    print(f"   Subscription: {subscription_id}")
    print(f"   Resource Group: {resource_group}")
    print(f"   Workspace: {workspace_name}")
    print()
    
    # Initialize ML Client
    print("🔐 Authenticating to Azure ML...")
    try:
        credential = DefaultAzureCredential()
        ml_client = MLClient(
            credential=credential,
            subscription_id=subscription_id,
            resource_group_name=resource_group,
            workspace_name=workspace_name
        )
        print("✅ Authentication successful\n")
    except Exception as e:
        print(f"❌ Authentication failed: {str(e)}")
        print("\nTry running: az login")
        return False
    
    # Check if datastore exists
    datastore_name = "<REDACTED_WORKSPACE_ID>"
    print(f"🔍 Checking for datastore: {datastore_name}...")
    
    try:
        datastore = ml_client.datastores.get(datastore_name)
        print(f"✅ Datastore found!")
        print(f"   Name: {datastore.name}")
        print(f"   Type: {datastore.type}")
        print(f"   Description: {datastore.description}")
        
        if hasattr(datastore, 'endpoint'):
            print(f"   Endpoint: {datastore.endpoint}")
        if hasattr(datastore, 'one_lake_workspace_name'):
            print(f"   OneLake Workspace: {datastore.one_lake_workspace_name}")
        
        print("\n✅ Datastore validation PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Datastore not found: {str(e)}")
        print("\nPossible reasons:")
        print("  1. Datastore not registered yet")
        print("  2. Incorrect datastore name")
        print("  3. Insufficient permissions")
        print("\nTo register, run:")
        print("  python register_onelake_datastore.py")
        print("  OR")
        print("  register_datastore.bat")
        return False

def list_all_datastores():
    """List all datastores in the workspace"""
    from azure.ai.ml import MLClient
    from azure.identity import DefaultAzureCredential
    
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    resource_group = os.getenv("AZURE_RESOURCE_GROUP")
    workspace_name = os.getenv("AZURE_ML_WORKSPACE")
    
    if not all([subscription_id, resource_group, workspace_name]):
        return
    
    print("\n" + "=" * 70)
    print("All Datastores in Workspace")
    print("=" * 70)
    
    try:
        ml_client = MLClient(
            credential=DefaultAzureCredential(),
            subscription_id=subscription_id,
            resource_group_name=resource_group,
            workspace_name=workspace_name
        )
        
        datastores = list(ml_client.datastores.list())
        
        if not datastores:
            print("\n⚠️  No datastores found in this workspace")
            return
        
        print(f"\nFound {len(datastores)} datastore(s):\n")
        
        for i, ds in enumerate(datastores, 1):
            print(f"{i}. Name: {ds.name}")
            print(f"   Type: {ds.type}")
            if hasattr(ds, 'description') and ds.description:
                print(f"   Description: {ds.description}")
            print()
            
    except Exception as e:
        print(f"❌ Error listing datastores: {str(e)}")

def test_data_reference():
    """Test creating a data reference to the OneLake datastore"""
    from azure.ai.ml import Input
    from azure.ai.ml.constants import AssetTypes
    
    print("\n" + "=" * 70)
    print("Testing Data Reference")
    print("=" * 70)
    
    try:
    datastore_name = "<REDACTED_WORKSPACE_ID>"
        
        # Create a data reference
        data_path = f"azureml://datastores/{datastore_name}/paths/your-data-path/"
        
        data_input = Input(
            type=AssetTypes.URI_FOLDER,
            path=data_path
        )
        
        print(f"\n✅ Data reference created successfully:")
        print(f"   Path: {data_input.path}")
        print(f"   Type: {data_input.type}")
        print("\nThis path can be used in Azure ML jobs and pipelines")
        
    except Exception as e:
        print(f"❌ Error creating data reference: {str(e)}")

def main():
    """Main validation flow"""
    print("\n" + "=" * 70)
    print("Azure ML - OneLake Datastore Validation Tool")
    print("=" * 70)
    print()
    
    # Step 1: Check dependencies
    if not check_imports():
        sys.exit(1)
    
    # Step 2: Validate datastore
    validation_passed = validate_datastore()
    
    # Step 3: List all datastores
    list_all_datastores()
    
    # Step 4: Test data reference (only if validation passed)
    if validation_passed:
        test_data_reference()
    
    print("\n" + "=" * 70)
    if validation_passed:
        print("✅ VALIDATION COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print("\nYour OneLake datastore is properly configured and ready to use!")
        print("\nNext steps:")
        print("  1. Create a training script that uses this datastore")
        print("  2. Submit a job to Azure ML")
        print("  3. Monitor job execution in Azure ML Studio")
    else:
        print("❌ VALIDATION FAILED")
        print("=" * 70)
        print("\nPlease fix the issues above and try again")
        print("\nFor help, see: ONELAKE_CONNECTION_GUIDE.md")
    print()

if __name__ == "__main__":
    main()
