output "resource_group_name" {
  description = "Resource group holding the environment."
  value       = azurerm_resource_group.this.name
}

output "registry_login_server" {
  description = "Registry host name. Used to tag and push the bot image."
  value       = module.acr.login_server
}

output "registry_name" {
  description = "Registry name, for az acr login."
  value       = module.acr.name
}

output "key_vault_name" {
  description = "Key Vault name."
  value       = module.keyvault.name
}

output "key_vault_uri" {
  description = "Key Vault URI."
  value       = module.keyvault.uri
}

output "postgres_fqdn" {
  description = "Database FQDN. Resolves only inside the VNet."
  value       = module.postgres.fqdn
}

output "workload_identity_client_id" {
  description = "Client id of the identity the jobs run as."
  value       = azurerm_user_assigned_identity.workload.client_id
}

output "trading_cycle_job_name" {
  description = "Scheduled job running one trading cycle."
  value       = module.container_apps.trading_cycle_job_name
}

output "migrate_job_name" {
  description = "Manually triggered job running Alembic migrations."
  value       = module.container_apps.migrate_job_name
}

output "image_reference" {
  description = "Image the jobs expect. Build and push this before running them."
  value       = "${module.acr.login_server}/${var.image_repository}:${var.image_tag}"
}

output "workbook_id" {
  description = "Versioned Azure Workbook showing equity, drawdown, decisions and failures."
  value       = module.alerts.workbook_id
}

output "alert_names" {
  description = "Alert rules watching the bot."
  value       = module.alerts.alert_names
}

output "dashboard_url" {
  description = "Dashboard address. Protected by Entra ID once Easy Auth is configured."
  value       = module.container_apps.dashboard_fqdn != null ? "https://${module.container_apps.dashboard_fqdn}" : null
}
