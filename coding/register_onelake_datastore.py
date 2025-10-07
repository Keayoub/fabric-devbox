"""
Register OneLake Datastore in Azure Machine Learning
Based on: https://learn.microsoft.com/en-us/azure/machine-learning/how-to-datastore
"""

from azure.ai.ml import MLClient
from azure.ai.ml.entities import OneLakeDatastore, ServicePrincipalConfiguration
from azure.identity import DefaultAzureCredential
import os

def register_onelake_datastore():
    """
    Register the OneLake datastore from azml_onelakesp_datastore.yml configuration
    """
    
    # TODO: Update these values for your Azure ML workspace
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID", "<your-subscription-id>")
    resource_group_name = os.getenv("AZURE_RESOURCE_GROUP", "<your-resource-group>")
    workspace_name = os.getenv("AZURE_ML_WORKSPACE", "<your-azureml-workspace>")
    
    # Initialize ML Client with DefaultAzureCredential
    # This will use your Azure CLI credentials or managed identity
    print("🔐 Authenticating to Azure ML...")
    ml_client = MLClient(
        credential=DefaultAzureCredential(),
        subscription_id=subscription_id,
        resource_group_name=resource_group_name,
        workspace_name=workspace_name
    )
    
    # OneLake configuration from your YAML file
    workspace_id = "fb53fbfb-d8e9-4797-b2f5-ba80bb9a7388"
    lakehouse_id = "b5607519-ec4b-4a83-ac2a-5443c8887e2a"
    
    # Service Principal credentials
    # SECURITY NOTE: Consider moving these to Azure Key Vault
    tenant_id = "c869cf92-11d8-4fbc-a7cf-6114d160dd71"
    client_id = "f4b66b80-24d3-4498-9cdf-02f47c776315"
    client_secret = os.getenv("ONELAKE_CLIENT_SECRET", "Pn28Q~Rz~IMklN-wBXYE-IfVwJWfLQbhpDOLoaOW")
    
    # Create OneLake Datastore
    print("📦 Creating OneLake datastore configuration...")
    onelake_datastore = OneLakeDatastore(
        name="fabric_onelake_lakehouse",
        description="Datastore pointing to Fabric OneLake lakehouse",
        one_lake_workspace_name=workspace_id,
        endpoint="msit-onelake.dfs.fabric.microsoft.com",
        artifact={
            "type": "lake_house",
            "name": f"{lakehouse_id}/Files"
        },
        credentials=ServicePrincipalConfiguration(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
    )
    
    # Register the datastore
    print("🚀 Registering datastore in Azure ML workspace...")
    try:
        created_datastore = ml_client.datastores.create_or_update(onelake_datastore)
        print(f"✅ Datastore '{created_datastore.name}' registered successfully!")
        print(f"   Type: {created_datastore.type}")
        print(f"   Workspace: {workspace_id}")
        print(f"   Lakehouse: {lakehouse_id}")
        return created_datastore
    except Exception as e:
        print(f"❌ Error registering datastore: {str(e)}")
        raise

def test_datastore_access():
    """
    Test accessing data from the registered OneLake datastore
    """
    from azure.ai.ml import Input
    from azure.ai.ml.constants import AssetTypes
    
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID", "<your-subscription-id>")
    resource_group_name = os.getenv("AZURE_RESOURCE_GROUP", "<your-resource-group>")
    workspace_name = os.getenv("AZURE_ML_WORKSPACE", "<your-azureml-workspace>")
    
    ml_client = MLClient(
        credential=DefaultAzureCredential(),
        subscription_id=subscription_id,
        resource_group_name=resource_group_name,
        workspace_name=workspace_name
    )
    
    print("\n🔍 Testing datastore access...")
    try:
        # Get the datastore
        datastore = ml_client.datastores.get("fabric_onelake_lakehouse")
        print(f"✅ Datastore found: {datastore.name}")
        print(f"   Endpoint: {datastore.endpoint}")
        
        # Example: Create a data input reference
        # Replace 'your-folder' with an actual path in your lakehouse
        data_input = Input(
            type=AssetTypes.URI_FOLDER,
            path="azureml://datastores/fabric_onelake_lakehouse/paths/your-folder/"
        )
        print(f"✅ Data path configured: {data_input.path}")
        
    except Exception as e:
        print(f"❌ Error accessing datastore: {str(e)}")

def list_datastores():
    """
    List all datastores in the Azure ML workspace
    """
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID", "<your-subscription-id>")
    resource_group_name = os.getenv("AZURE_RESOURCE_GROUP", "<your-resource-group>")
    workspace_name = os.getenv("AZURE_ML_WORKSPACE", "<your-azureml-workspace>")
    
    ml_client = MLClient(
        credential=DefaultAzureCredential(),
        subscription_id=subscription_id,
        resource_group_name=resource_group_name,
        workspace_name=workspace_name
    )
    
    print("\n📋 Listing all datastores in workspace...")
    try:
        datastores = ml_client.datastores.list()
        for ds in datastores:
            print(f"  - {ds.name} (Type: {ds.type})")
    except Exception as e:
        print(f"❌ Error listing datastores: {str(e)}")

if __name__ == "__main__":
    print("=" * 60)
    print("Azure ML - OneLake Datastore Registration")
    print("=" * 60)
    print("\n⚙️  Setup Instructions:")
    print("1. Set environment variables:")
    print("   - AZURE_SUBSCRIPTION_ID")
    print("   - AZURE_RESOURCE_GROUP")
    print("   - AZURE_ML_WORKSPACE")
    print("   - ONELAKE_CLIENT_SECRET (optional, will use hardcoded if not set)")
    print("\n2. Ensure you're logged in: az login")
    print("3. Run this script: python register_onelake_datastore.py")
    print("=" * 60)
    
    try:
        # Register the datastore
        datastore = register_onelake_datastore()
        
        # Test access
        test_datastore_access()
        
        # List all datastores
        list_datastores()
        
        print("\n" + "=" * 60)
        print("✅ All operations completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Script failed: {str(e)}")
        print("\nTroubleshooting:")
        print("- Verify your Azure ML workspace details")
        print("- Check that you're logged in: az account show")
        print("- Ensure the service principal has access to the OneLake workspace")
        print("- Verify the workspace and lakehouse IDs are correct")
