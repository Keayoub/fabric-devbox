terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~>2.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Get current client configuration
data "azurerm_client_config" "current" {}

# Variables for customization
variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "rg-fabric-monitoring"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "Canada Central"
}

variable "log_analytics_workspace_name" {
  description = "Name of the Log Analytics workspace"
  type        = string
  default     = "law-fabric-monitoring"
}

variable "data_collection_endpoint_name" {
  description = "Name of the Data Collection Endpoint"
  type        = string
  default     = "dce-fabric-monitoring"
}

variable "data_collection_rule_name" {
  description = "Name of the Data Collection Rule"
  type        = string
  default     = "dcr-fabric-monitoring"
}

# Resource Group
resource "azurerm_resource_group" "log_analytics_rg" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    Environment = "Production"
    Purpose     = "Fabric Monitoring"
    CreatedBy   = "Terraform"
  }
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "la" {
  name                = var.log_analytics_workspace_name
  location            = azurerm_resource_group.log_analytics_rg.location
  resource_group_name = azurerm_resource_group.log_analytics_rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = {
    Environment = "Production"
    Purpose     = "Fabric Monitoring"
    CreatedBy   = "Terraform"
  }
}

# Custom Log Analytics Tables for Fabric Monitoring
# Deploy tables using external ARM template (consistent with DCR approach)
resource "azurerm_resource_group_template_deployment" "fabric_tables" {
  name                = "fabric-tables-deployment"
  resource_group_name = azurerm_resource_group.log_analytics_rg.name
  deployment_mode     = "Incremental"

  template_content = file("${path.module}/../common/tables-template.json")
  parameters_content = jsonencode({
    workspaceName = {
      value = azurerm_log_analytics_workspace.la.name
    }
  })
}

# Data Collection Endpoint
resource "azurerm_monitor_data_collection_endpoint" "dce" {
  name                = var.data_collection_endpoint_name
  location            = azurerm_resource_group.log_analytics_rg.location
  resource_group_name = azurerm_resource_group.log_analytics_rg.name

  tags = {
    Environment = "Production"
    Purpose     = "Fabric Monitoring"
    CreatedBy   = "Terraform"
  }
}

# Data Collection Rule with custom streams using ARM template
resource "azurerm_resource_group_template_deployment" "dcr" {
  name                = "fabric-dcr-deployment"
  resource_group_name = azurerm_resource_group.log_analytics_rg.name
  deployment_mode     = "Incremental"

  template_content = file("${path.module}/../common/dcr-template.json")

  parameters_content = jsonencode({
    dcrName = {
      value = var.data_collection_rule_name
    }
    location = {
      value = azurerm_resource_group.log_analytics_rg.location
    }
    dceResourceId = {
      value = azurerm_monitor_data_collection_endpoint.dce.id
    }
    lawResourceId = {
      value = azurerm_log_analytics_workspace.la.id
    }
  })

  depends_on = [
    azurerm_monitor_data_collection_endpoint.dce,
    azurerm_log_analytics_workspace.la,
    azurerm_resource_group_template_deployment.fabric_tables
  ]
}

# Service Principal configuration
variable "service_principal_object_id" {
  description = "Object ID of the existing service principal to grant DCR permissions"
  type        = string
  default     = ""
}

# Assign Monitoring Metrics Publisher role to the provided service principal
resource "azurerm_role_assignment" "dcr_monitoring_metrics_publisher" {
  count                = var.service_principal_object_id != "" ? 1 : 0
  scope                = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${azurerm_resource_group.log_analytics_rg.name}/providers/Microsoft.Insights/dataCollectionRules/${var.data_collection_rule_name}"
  role_definition_name = "Monitoring Metrics Publisher"
  principal_id         = var.service_principal_object_id

  depends_on = [azurerm_resource_group_template_deployment.dcr]
}

# Add DCR resource ID output for role assignment reference
output "data_collection_rule_resource_id" {
  value       = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${azurerm_resource_group.log_analytics_rg.name}/providers/Microsoft.Insights/dataCollectionRules/${var.data_collection_rule_name}"
  description = "The full resource ID of the Data Collection Rule"
}

# Outputs
output "resource_group_name" {
  value       = azurerm_resource_group.log_analytics_rg.name
  description = "The name of the resource group"
}

output "log_analytics_workspace_id" {
  value       = azurerm_log_analytics_workspace.la.id
  description = "The ID of the Log Analytics workspace"
}

output "log_analytics_workspace_name" {
  value       = azurerm_log_analytics_workspace.la.name
  description = "The name of the Log Analytics workspace"
}

output "data_collection_endpoint_id" {
  value       = azurerm_monitor_data_collection_endpoint.dce.id
  description = "The ID of the Data Collection Endpoint"
}

output "data_collection_endpoint_logs_ingestion_endpoint" {
  value       = azurerm_monitor_data_collection_endpoint.dce.logs_ingestion_endpoint
  description = "The logs ingestion endpoint URL for the DCE"
}

output "data_collection_rule_id" {
  value       = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${azurerm_resource_group.log_analytics_rg.name}/providers/Microsoft.Insights/dataCollectionRules/${var.data_collection_rule_name}"
  description = "The ID of the Data Collection Rule"
}

output "data_collection_rule_immutable_id" {
  value       = jsondecode(azurerm_resource_group_template_deployment.dcr.output_content)["dcrImmutableId"]["value"]
  description = "The immutable ID of the Data Collection Rule (used for API calls)"
}

output "service_principal_role_assignment" {
  value       = var.service_principal_object_id != "" ? "Monitoring Metrics Publisher role assigned to service principal ${var.service_principal_object_id}" : "No service principal provided - set service_principal_object_id variable"
  description = "Status of the service principal role assignment"
}

output "tenant_id" {
  value       = data.azurerm_client_config.current.tenant_id
  description = "The tenant ID for authentication"
}

