# Terraform state bootstrap

Creates the remote backend that every other stack in this repository uses: a
resource group, a storage account and a blob container.

## Why this stack keeps its state locally

A remote backend cannot store the state of the stack that creates it. The
options are a local state file, or creating the storage account by hand outside
Terraform. This repository chooses a local state and accepts the consequence,
because the alternative moves a step out of version control and makes the
backend impossible to review.

Losing the local state is recoverable and does not destroy anything:

    terraform import azurerm_resource_group.state /subscriptions/<SUB>/resourceGroups/<RG>
    terraform import azurerm_storage_account.state /subscriptions/<SUB>/resourceGroups/<RG>/providers/Microsoft.Storage/storageAccounts/<NAME>

The state file is gitignored. It contains no secrets: shared keys are disabled
on the account, so there is no key to leak.

## No storage account key, anywhere

`shared_access_key_enabled = false` and `storage_use_azuread = true`. The data
plane is reached with the caller's Entra ID identity, so no account key exists
to be copied into a developer machine, a CI secret or a state file.

The price is that being subscription Owner is not enough: Owner grants control
plane rights, not data actions. This stack therefore assigns **Storage Blob Data
Owner** on the account to whoever runs it, and waits sixty seconds for the
assignment to propagate before creating the container. Without the wait the
first apply fails roughly half the time on an eventual consistency error.

## Usage

    cd infra/bootstrap
    terraform init
    terraform plan  -var subscription_id=<SUBSCRIPTION_ID> -out tfplan
    terraform apply tfplan
    terraform output backend_config

The storage account name carries a random suffix. Storage account names are
globally unique and stay reserved for a while after deletion, so a fixed name
would make `destroy` followed by `apply` fail. The suffix lives in state and
therefore survives a re-apply.

## What this stack deliberately does not do

- **No private endpoint.** The backend has to be reachable from GitHub-hosted
  runners, which have no fixed egress addresses, and from a developer machine
  outside any VNet. Access is controlled by Entra ID RBAC instead of by network
  position.
- **No customer-managed keys.** They would need a Key Vault, and this stack runs
  before any Key Vault exists. Microsoft-managed keys with infrastructure
  encryption is the accepted trade-off.

Both are recorded as `checkov:skip` annotations with the reason inline, so a
reviewer sees the justification next to the code rather than in a suppression
file.

## Inputs and outputs

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.9.0 |
| <a name="requirement_azurerm"></a> [azurerm](#requirement\_azurerm) | ~> 4.0 |
| <a name="requirement_random"></a> [random](#requirement\_random) | ~> 3.6 |
| <a name="requirement_time"></a> [time](#requirement\_time) | ~> 0.12 |

## Providers

| Name | Version |
| ---- | ------- |
| <a name="provider_azurerm"></a> [azurerm](#provider\_azurerm) | ~> 4.0 |
| <a name="provider_random"></a> [random](#provider\_random) | ~> 3.6 |
| <a name="provider_time"></a> [time](#provider\_time) | ~> 0.12 |

## Modules

No modules.

## Resources

| Name | Type |
| ---- | ---- |
| [azurerm_resource_group.state](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/resource_group) | resource |
| [azurerm_role_assignment.state_blob_owner](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/role_assignment) | resource |
| [azurerm_storage_account.state](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/storage_account) | resource |
| [azurerm_storage_container.state](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/storage_container) | resource |
| [random_string.suffix](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/string) | resource |
| [time_sleep.rbac_propagation](https://registry.terraform.io/providers/hashicorp/time/latest/docs/resources/sleep) | resource |
| [azurerm_client_config.current](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/data-sources/client_config) | data source |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| <a name="input_container_name"></a> [container\_name](#input\_container\_name) | Blob container holding the state files. | `string` | `"tfstate"` | no |
| <a name="input_location"></a> [location](#input\_location) | Azure region for the state storage account. | `string` | `"northeurope"` | no |
| <a name="input_resource_group_name"></a> [resource\_group\_name](#input\_resource\_group\_name) | Resource group holding the Terraform state storage account. | `string` | `"rg-tfstate-tradingbot-neu"` | no |
| <a name="input_state_retention_days"></a> [state\_retention\_days](#input\_state\_retention\_days) | Days a deleted or overwritten state blob stays recoverable. | `number` | `30` | no |
| <a name="input_storage_account_prefix"></a> [storage\_account\_prefix](#input\_storage\_account\_prefix) | Prefix for the state storage account name. A random suffix is appended to keep the globally unique name available after a destroy. | `string` | `"sttfstatetrading"` | no |
| <a name="input_subscription_id"></a> [subscription\_id](#input\_subscription\_id) | Azure subscription that hosts the Terraform state. | `string` | n/a | yes |
| <a name="input_tags"></a> [tags](#input\_tags) | Tags applied to every resource. project, env, owner and cost-center are mandatory across this repository. | `map(string)` | <pre>{<br/>  "component": "terraform-state",<br/>  "cost-center": "personal",<br/>  "env": "shared",<br/>  "owner": "eliasbaghazou",<br/>  "project": "azure-trading-platform"<br/>}</pre> | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| <a name="output_backend_config"></a> [backend\_config](#output\_backend\_config) | Ready to paste into a backend block or to pass with -backend-config. |
| <a name="output_container_name"></a> [container\_name](#output\_container\_name) | Blob container holding the state files. |
| <a name="output_resource_group_name"></a> [resource\_group\_name](#output\_resource\_group\_name) | Resource group holding the state storage account. |
| <a name="output_storage_account_name"></a> [storage\_account\_name](#output\_storage\_account\_name) | State storage account name. Needed by every other stack's backend block. |
<!-- END_TF_DOCS -->
