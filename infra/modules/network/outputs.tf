output "vnet_id" {
  description = "Virtual network resource id."
  value       = azurerm_virtual_network.this.id
}

output "container_apps_subnet_id" {
  description = "Subnet the Container Apps environment is injected into."
  value       = azurerm_subnet.container_apps.id
}

output "postgres_subnet_id" {
  description = "Delegated subnet for PostgreSQL Flexible Server."
  value       = azurerm_subnet.postgres.id
}

output "postgres_private_dns_zone_id" {
  description = "Private DNS zone resolving the PostgreSQL FQDN inside the VNet."
  value       = azurerm_private_dns_zone.postgres.id
}

output "postgres_private_dns_zone_link_id" {
  description = "VNet link on the private DNS zone. Depend on this to order server creation after DNS is resolvable."
  value       = azurerm_private_dns_zone_virtual_network_link.postgres.id
}
