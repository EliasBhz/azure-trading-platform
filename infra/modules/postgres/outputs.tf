output "id" {
  description = "Flexible Server resource id."
  value       = azurerm_postgresql_flexible_server.this.id
}

output "fqdn" {
  description = "Server FQDN. Resolves only inside a VNet linked to the private DNS zone."
  value       = azurerm_postgresql_flexible_server.this.fqdn
}

output "database_name" {
  description = "Application database name."
  value       = azurerm_postgresql_flexible_server_database.this.name
}

output "administrator_login" {
  description = "Administrator user name."
  value       = azurerm_postgresql_flexible_server.this.administrator_login
}
