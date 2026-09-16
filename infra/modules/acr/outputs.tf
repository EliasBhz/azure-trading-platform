output "id" {
  description = "Registry resource id."
  value       = azurerm_container_registry.this.id
}

output "name" {
  description = "Registry name."
  value       = azurerm_container_registry.this.name
}

output "login_server" {
  description = "Registry host name, used as the image prefix."
  value       = azurerm_container_registry.this.login_server
}
