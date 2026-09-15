terraform {
  required_version = ">= 1.9.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

resource "azurerm_log_analytics_workspace" "this" {
  name                = "log-${var.name_prefix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"

  # Ingestion is the dominant cost of this workspace, and the daily cap is the
  # only control that stops a log loop from spending money overnight. Hitting
  # the cap loses telemetry, which is the correct trade in a dev environment
  # and would be the wrong one in production.
  retention_in_days          = var.retention_in_days
  daily_quota_gb             = var.daily_quota_gb
  internet_ingestion_enabled = true
  internet_query_enabled     = true

  tags = var.tags
}

resource "azurerm_application_insights" "this" {
  name                = "appi-${var.name_prefix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  application_type    = "other"

  # Workspace-based rather than classic: telemetry lands in the same workspace
  # as the container logs, so a single KQL query can join an order to the log
  # line that produced it.
  workspace_id = azurerm_log_analytics_workspace.this.id

  sampling_percentage = 100
  tags                = var.tags
}
