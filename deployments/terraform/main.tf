terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Data source for existing resource group
data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}

# Local values for resource naming
locals {
  app_service_plan_name    = "${var.student_name}-plan"
  web_app_name            = "${var.student_name}-order-service"
  eventhub_namespace_name = "${var.student_name}-events"
  eventhub_name           = "orders"
  common_tags = {
    Environment = var.environment
    Student     = var.student_name
    Project     = "order-service"
    ManagedBy   = "terraform"
  }
}

# App Service Plan
resource "azurerm_service_plan" "main" {
  name                = local.app_service_plan_name
  resource_group_name = data.azurerm_resource_group.main.name
  location            = data.azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = var.app_service_plan_sku

  tags = local.common_tags
}

# Event Hub Namespace
resource "azurerm_eventhub_namespace" "main" {
  name                = local.eventhub_namespace_name
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  sku                 = var.eventhub_sku
  capacity            = 1

  tags = local.common_tags
}

# Event Hub
resource "azurerm_eventhub" "orders" {
  name                = local.eventhub_name
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = data.azurerm_resource_group.main.name
  partition_count     = 1
  message_retention   = 1
}

# Event Hub Authorization Rule
resource "azurerm_eventhub_authorization_rule" "orders_access" {
  name                = "orders-access-key"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.orders.name
  resource_group_name = data.azurerm_resource_group.main.name

  listen = true
  send   = true
  manage = false
}

# Linux Web App
resource "azurerm_linux_web_app" "main" {
  name                = local.web_app_name
  resource_group_name = data.azurerm_resource_group.main.name
  location            = data.azurerm_resource_group.main.location
  service_plan_id     = azurerm_service_plan.main.id
  https_only          = true

  site_config {
    always_on                         = true
    application_stack {
      python_version = "3.9"
    }
    app_command_line = "uvicorn main:app --host 0.0.0.0 --port 8000"
  }

  app_settings = {
    "EVENT_HUB_CONNECTION_STRING" = azurerm_eventhub_authorization_rule.orders_access.primary_connection_string
    "EVENT_HUB_NAME"              = azurerm_eventhub.orders.name
    "ENVIRONMENT"                 = var.environment
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
  }

  tags = local.common_tags

  depends_on = [
    azurerm_service_plan.main,
    azurerm_eventhub_authorization_rule.orders_access
  ]
}