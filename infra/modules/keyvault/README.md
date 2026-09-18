# keyvault

Key Vault in RBAC mode holding the database connection string, the kill switch and the Application Insights connection string. Purge protection is off so the environment can be destroyed and recreated.

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.9.0 |
| <a name="requirement_azurerm"></a> [azurerm](#requirement\_azurerm) | ~> 4.0 |
| <a name="requirement_time"></a> [time](#requirement\_time) | ~> 0.12 |

## Providers

| Name | Version |
| ---- | ------- |
| <a name="provider_azurerm"></a> [azurerm](#provider\_azurerm) | ~> 4.0 |
| <a name="provider_time"></a> [time](#provider\_time) | ~> 0.12 |

## Modules

No modules.

## Resources

| Name | Type |
| ---- | ---- |
| [azurerm_key_vault.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault) | resource |
| [azurerm_key_vault_secret.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_monitor_diagnostic_setting.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/monitor_diagnostic_setting) | resource |
| [azurerm_role_assignment.reader_secrets_user](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/role_assignment) | resource |
| [azurerm_role_assignment.secrets_officer](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/role_assignment) | resource |
| [time_sleep.rbac_propagation](https://registry.terraform.io/providers/hashicorp/time/latest/docs/resources/sleep) | resource |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| <a name="input_location"></a> [location](#input\_location) | Azure region. | `string` | n/a | yes |
| <a name="input_log_analytics_workspace_id"></a> [log\_analytics\_workspace\_id](#input\_log\_analytics\_workspace\_id) | Workspace receiving the vault audit log. | `string` | n/a | yes |
| <a name="input_name"></a> [name](#input\_name) | Key Vault name. Globally unique, 3 to 24 characters. | `string` | n/a | yes |
| <a name="input_resource_group_name"></a> [resource\_group\_name](#input\_resource\_group\_name) | Resource group that holds the vault. | `string` | n/a | yes |
| <a name="input_secret_reader_principal_ids"></a> [secret\_reader\_principal\_ids](#input\_secret\_reader\_principal\_ids) | Principals granted Key Vault Secrets User, keyed by a readable name. | `map(string)` | `{}` | no |
| <a name="input_secret_writer_principal_ids"></a> [secret\_writer\_principal\_ids](#input\_secret\_writer\_principal\_ids) | Every principal that may run apply, keyed by a readable name. All get Key Vault Secrets Officer, so a plan run by one does not propose removing another. | `map(string)` | n/a | yes |
| <a name="input_secrets"></a> [secrets](#input\_secrets) | Secrets to create, name to value. | `map(string)` | `{}` | no |
| <a name="input_tags"></a> [tags](#input\_tags) | Tags applied to every resource. | `map(string)` | n/a | yes |
| <a name="input_tenant_id"></a> [tenant\_id](#input\_tenant\_id) | Entra ID tenant that owns the vault. | `string` | n/a | yes |

## Outputs

| Name | Description |
| ---- | ----------- |
| <a name="output_id"></a> [id](#output\_id) | Key Vault resource id. |
| <a name="output_name"></a> [name](#output\_name) | Key Vault name. |
| <a name="output_secret_versionless_ids"></a> [secret\_versionless\_ids](#output\_secret\_versionless\_ids) | Versionless secret ids, safe to reference from Container Apps so a rotation does not need a redeploy. |
| <a name="output_uri"></a> [uri](#output\_uri) | Key Vault URI, used by the bot to read the kill switch. |
<!-- END_TF_DOCS -->
