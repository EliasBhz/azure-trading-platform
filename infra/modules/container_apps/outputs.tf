output "environment_id" {
  description = "Container Apps environment resource id."
  value       = azurerm_container_app_environment.this.id
}

output "environment_default_domain" {
  description = "Default domain of the environment, used later by the dashboard ingress."
  value       = azurerm_container_app_environment.this.default_domain
}

output "trading_cycle_job_name" {
  description = "Scheduled job running one trading cycle."
  value       = one(azurerm_container_app_job.trading_cycle[*].name)
}

output "migrate_job_name" {
  description = "Manually triggered job running Alembic migrations."
  value       = one(azurerm_container_app_job.migrate[*].name)
}

output "dashboard_fqdn" {
  description = "Public host name of the dashboard. Null when the dashboard is disabled."
  value       = one(azurerm_container_app.dashboard[*].ingress[0].fqdn)
}

output "dashboard_name" {
  description = "Dashboard Container App name."
  value       = one(azurerm_container_app.dashboard[*].name)
}
