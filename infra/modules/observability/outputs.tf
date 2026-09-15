output "workspace_id" {
  description = "Log Analytics workspace resource id."
  value       = azurerm_log_analytics_workspace.this.id
}

output "workspace_customer_id" {
  description = "Workspace GUID, used by the Container Apps environment."
  value       = azurerm_log_analytics_workspace.this.workspace_id
}

output "workspace_primary_shared_key" {
  description = "Shared key the Container Apps environment uses to ship logs."
  value       = azurerm_log_analytics_workspace.this.primary_shared_key
  sensitive   = true
}

output "application_insights_connection_string" {
  description = "Connection string for the OpenTelemetry exporter."
  value       = azurerm_application_insights.this.connection_string
  sensitive   = true
}

output "application_insights_id" {
  description = "Application Insights resource id."
  value       = azurerm_application_insights.this.id
}
