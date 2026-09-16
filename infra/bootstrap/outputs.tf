output "resource_group_name" {
  description = "Resource group holding the state storage account."
  value       = azurerm_resource_group.state.name
}

output "storage_account_name" {
  description = "State storage account name. Needed by every other stack's backend block."
  value       = azurerm_storage_account.state.name
}

output "container_name" {
  description = "Blob container holding the state files."
  value       = azurerm_storage_container.state.name
}

output "backend_config" {
  description = "Ready to paste into a backend block or to pass with -backend-config."
  value       = <<-EOT
    resource_group_name  = "${azurerm_resource_group.state.name}"
    storage_account_name = "${azurerm_storage_account.state.name}"
    container_name       = "${azurerm_storage_container.state.name}"
    use_azuread_auth     = true
  EOT
}
