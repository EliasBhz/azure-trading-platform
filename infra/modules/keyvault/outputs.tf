output "id" {
  description = "Key Vault resource id."
  value       = azurerm_key_vault.this.id
}

output "name" {
  description = "Key Vault name."
  value       = azurerm_key_vault.this.name
}

output "uri" {
  description = "Key Vault URI, used by the bot to read the kill switch."
  value       = azurerm_key_vault.this.vault_uri
}

output "secret_versionless_ids" {
  description = "Versionless secret ids, safe to reference from Container Apps so a rotation does not need a redeploy."
  value       = { for name, secret in azurerm_key_vault_secret.this : name => secret.versionless_id }
}
