"""
Example: Using OneLake Datastore in Azure ML Training Job

This example demonstrates how to:
1. Connect to Azure ML workspace
2. Reference data from OneLake datastore
3. Submit a training job that reads from Fabric OneLake
"""

from azure.ai.ml import MLClient, command, Input, Output
from azure.ai.ml.entities import Environment, Data
from azure.ai.ml.constants import AssetTypes
from azure.identity import DefaultAzureCredential
import os

# Configuration
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID", "<your-subscription-id>")
RESOURCE_GROUP = os.getenv("AZURE_RESOURCE_GROUP", "<your-resource-group>")
WORKSPACE_NAME = os.getenv("AZURE_ML_WORKSPACE", "<your-workspace-name>")
COMPUTE_NAME = os.getenv("AZURE_ML_COMPUTE", "cpu-cluster")

# OneLake datastore name (from your YAML)
ONELAKE_DATASTORE = "fb53fbfb-d8e9-4797-b2f5-ba80bb9a7388"


def get_ml_client():
    """Initialize Azure ML client"""
    print("🔐 Connecting to Azure ML workspace...")
    return MLClient(
        credential=DefaultAzureCredential(),
        subscription_id=SUBSCRIPTION_ID,
        resource_group_name=RESOURCE_GROUP,
        workspace_name=WORKSPACE_NAME
    )


def example_1_simple_command_job(ml_client):
    """
    Example 1: Simple command job reading from OneLake
    """
    print("\n" + "=" * 70)
    print("Example 1: Simple Command Job with OneLake Data")
    print("=" * 70)
    
    # Define input data from OneLake
    training_data = Input(
        type=AssetTypes.URI_FOLDER,
        path=f"azureml://datastores/{ONELAKE_DATASTORE}/paths/training-data/"
    )
    
    # Define output location (can also be in OneLake)
    output_data = Output(
        type=AssetTypes.URI_FOLDER,
        path=f"azureml://datastores/{ONELAKE_DATASTORE}/paths/outputs/"
    )
    
    # Create command job
    job = command(
        name="onelake-training-job",
        display_name="Training with OneLake Data",
        description="Example job that reads data from Fabric OneLake",
        
        # Training script
        code="./src",  # Local directory with your training script
        command="python train.py --input ${{inputs.data}} --output ${{outputs.result}}",
        
        # Inputs and outputs
        inputs={
            "data": training_data,
        },
        outputs={
            "result": output_data,
        },
        
        # Environment
        environment="AzureML-sklearn-1.0-ubuntu20.04-py38-cpu:1",
        
        # Compute
        compute=COMPUTE_NAME,
        
        # Job settings
        experiment_name="onelake-experiments",
    )
    
    print("📋 Job Configuration:")
    print(f"   Input: {training_data.path}")
    print(f"   Output: {output_data.path}")
    print(f"   Compute: {COMPUTE_NAME}")
    
    # Submit job
    print("\n🚀 Submitting job...")
    submitted_job = ml_client.jobs.create_or_update(job)
    
    print(f"✅ Job submitted: {submitted_job.name}")
    print(f"   Status: {submitted_job.status}")
    print(f"   Studio URL: {submitted_job.studio_url}")
    
    return submitted_job


def example_2_create_data_asset(ml_client):
    """
    Example 2: Create a reusable data asset from OneLake
    """
    print("\n" + "=" * 70)
    print("Example 2: Create Data Asset from OneLake")
    print("=" * 70)
    
    # Create data asset
    my_data_asset = Data(
        name="onelake-training-dataset",
        version="1",
        description="Training dataset from Fabric OneLake lakehouse",
        path=f"azureml://datastores/{ONELAKE_DATASTORE}/paths/datasets/training/",
        type=AssetTypes.URI_FOLDER,
        tags={
            "source": "fabric-onelake",
            "lakehouse_id": "b5607519-ec4b-4a83-ac2a-5443c8887e2a",
            "purpose": "training"
        }
    )
    
    print("📦 Creating data asset...")
    created_asset = ml_client.data.create_or_update(my_data_asset)
    
    print(f"✅ Data asset created: {created_asset.name}")
    print(f"   Version: {created_asset.version}")
    print(f"   Path: {created_asset.path}")
    
    # Now use the data asset in a job
    job = command(
        code="./src",
        command="python train.py --data ${{inputs.training_data}}",
        inputs={
            "training_data": Input(
                type=AssetTypes.URI_FOLDER,
                path=f"azureml:{created_asset.name}:{created_asset.version}"
            )
        },
        environment="AzureML-sklearn-1.0-ubuntu20.04-py38-cpu:1",
        compute=COMPUTE_NAME,
    )
    
    print("\n📋 Job using data asset:")
    print(f"   Data: azureml:{created_asset.name}:{created_asset.version}")
    
    return created_asset


def example_3_list_onelake_files(ml_client):
    """
    Example 3: List files in OneLake datastore
    """
    print("\n" + "=" * 70)
    print("Example 3: Browse OneLake Datastore")
    print("=" * 70)
    
    try:
        # Get datastore details
        datastore = ml_client.datastores.get(ONELAKE_DATASTORE)
        
        print(f"📁 Datastore Details:")
        print(f"   Name: {datastore.name}")
        print(f"   Type: {datastore.type}")
        print(f"   Description: {datastore.description}")
        
        if hasattr(datastore, 'endpoint'):
            print(f"   Endpoint: {datastore.endpoint}")
        
        if hasattr(datastore, 'one_lake_workspace_name'):
            print(f"   OneLake Workspace: {datastore.one_lake_workspace_name}")
        
        print("\n💡 To browse files:")
        print("   1. Go to Azure ML Studio: https://ml.azure.com")
        print("   2. Navigate to Data → Datastores")
        print(f"   3. Click on: {datastore.name}")
        print("   4. Browse the files in your lakehouse")
        
    except Exception as e:
        print(f"❌ Error accessing datastore: {str(e)}")


def example_4_pipeline_with_onelake(ml_client):
    """
    Example 4: Create a pipeline that uses OneLake data
    """
    print("\n" + "=" * 70)
    print("Example 4: Multi-Step Pipeline with OneLake")
    print("=" * 70)
    
    from azure.ai.ml.dsl import pipeline
    
    # Define pipeline components
    @pipeline(
        name="onelake_pipeline",
        description="Multi-step pipeline using OneLake data",
        default_compute=COMPUTE_NAME,
    )
    def onelake_training_pipeline(pipeline_input_data):
        """Pipeline definition"""
        
        # Step 1: Data preprocessing
        preprocess_step = command(
            name="preprocess",
            display_name="Preprocess Data",
            code="./src",
            command="python preprocess.py --input ${{inputs.raw_data}} --output ${{outputs.processed_data}}",
            inputs={
                "raw_data": pipeline_input_data,
            },
            outputs={
                "processed_data": Output(type=AssetTypes.URI_FOLDER)
            },
            environment="AzureML-sklearn-1.0-ubuntu20.04-py38-cpu:1",
        )
        
        # Step 2: Model training
        train_step = command(
            name="train",
            display_name="Train Model",
            code="./src",
            command="python train.py --input ${{inputs.training_data}} --output ${{outputs.model}}",
            inputs={
                "training_data": preprocess_step.outputs.processed_data,
            },
            outputs={
                "model": Output(type=AssetTypes.URI_FOLDER)
            },
            environment="AzureML-sklearn-1.0-ubuntu20.04-py38-cpu:1",
        )
        
        # Step 3: Model evaluation
        evaluate_step = command(
            name="evaluate",
            display_name="Evaluate Model",
            code="./src",
            command="python evaluate.py --model ${{inputs.model}} --output ${{outputs.metrics}}",
            inputs={
                "model": train_step.outputs.model,
            },
            outputs={
                "metrics": Output(type=AssetTypes.URI_FOLDER)
            },
            environment="AzureML-sklearn-1.0-ubuntu20.04-py38-cpu:1",
        )
        
        return {
            "processed_data": preprocess_step.outputs.processed_data,
            "trained_model": train_step.outputs.model,
            "evaluation_metrics": evaluate_step.outputs.metrics,
        }
    
    # Create pipeline instance with OneLake data
    pipeline_job = onelake_training_pipeline(
        pipeline_input_data=Input(
            type=AssetTypes.URI_FOLDER,
            path=f"azureml://datastores/{ONELAKE_DATASTORE}/paths/raw-data/"
        )
    )
    
    print("📋 Pipeline Configuration:")
    print("   Steps: preprocess → train → evaluate")
    print(f"   Input: OneLake datastore")
    print(f"   Compute: {COMPUTE_NAME}")
    
    print("\n🚀 To submit this pipeline:")
    print("   submitted_pipeline = ml_client.jobs.create_or_update(pipeline_job)")
    
    return pipeline_job


def main():
    """Main execution"""
    print("\n" + "=" * 70)
    print("Azure ML + Fabric OneLake Integration Examples")
    print("=" * 70)
    print("\nThese examples show how to use your OneLake datastore in Azure ML")
    print(f"Datastore: {ONELAKE_DATASTORE}")
    print("=" * 70)
    
    # Initialize ML client
    try:
        ml_client = get_ml_client()
        print(f"✅ Connected to workspace: {WORKSPACE_NAME}")
    except Exception as e:
        print(f"❌ Failed to connect: {str(e)}")
        print("\nMake sure you've set:")
        print("  - AZURE_SUBSCRIPTION_ID")
        print("  - AZURE_RESOURCE_GROUP")
        print("  - AZURE_ML_WORKSPACE")
        return
    
    # Run examples (commented out to avoid accidental job submission)
    
    # Example 1: Simple command job
    # job1 = example_1_simple_command_job(ml_client)
    
    # Example 2: Create data asset
    # asset = example_2_create_data_asset(ml_client)
    
    # Example 3: Browse datastore
    example_3_list_onelake_files(ml_client)
    
    # Example 4: Pipeline
    # pipeline = example_4_pipeline_with_onelake(ml_client)
    
    print("\n" + "=" * 70)
    print("📚 Examples Overview")
    print("=" * 70)
    print("\nUncomment the example you want to run in the main() function:")
    print("  - example_1_simple_command_job: Submit a single training job")
    print("  - example_2_create_data_asset: Create reusable data asset")
    print("  - example_3_list_onelake_files: Browse datastore details")
    print("  - example_4_pipeline_with_onelake: Multi-step ML pipeline")
    print()


if __name__ == "__main__":
    main()
