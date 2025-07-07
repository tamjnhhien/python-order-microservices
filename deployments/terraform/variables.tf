variable "student_name" {
  description = "Student name for resource naming"
  type        = string
  default     = "student01"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "East US"
}

variable "app_service_plan_sku" {
  description = "App Service Plan SKU"
  type        = string
  default     = "B3"
}

variable "eventhub_sku" {
  description = "Event Hub Namespace SKU"
  type        = string
  default     = "Standard"
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}
