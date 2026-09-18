# container_apps

Consumption-only Container Apps environment, the cron-scheduled trading cycle job and the manually triggered migration job.

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.9.0 |
| <a name="requirement_azapi"></a> [azapi](#requirement\_azapi) | ~> 2.0 |
| <a name="requirement_azuread"></a> [azuread](#requirement\_azuread) | ~> 3.0 |
| <a name="requirement_azurerm"></a> [azurerm](#requirement\_azurerm) | ~> 4.0 |
| <a name="requirement_time"></a> [time](#requirement\_time) | ~> 0.12 |

## Providers

| Name | Version |
| ---- | ------- |
| <a name="provider_azapi"></a> [azapi](#provider\_azapi) | ~> 2.0 |
| <a name="provider_azuread"></a> [azuread](#provider\_azuread) | ~> 3.0 |
| <a name="provider_azurerm"></a> [azurerm](#provider\_azurerm) | ~> 4.0 |
| <a name="provider_time"></a> [time](#provider\_time) | ~> 0.12 |

## Modules

No modules.

## Resources

| Name | Type |
| ---- | ---- |
| [azapi_resource.dashboard_auth](https://registry.terraform.io/providers/Azure/azapi/latest/docs/resources/resource) | resource |
| [azuread_application.dashboard](https://registry.terraform.io/providers/hashicorp/azuread/latest/docs/resources/application) | resource |
| [azuread_application_password.dashboard](https://registry.terraform.io/providers/hashicorp/azuread/latest/docs/resources/application_password) | resource |
| [azuread_service_principal.dashboard](https://registry.terraform.io/providers/hashicorp/azuread/latest/docs/resources/service_principal) | resource |
| [azurerm_container_app.dashboard](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/container_app) | resource |
| [azurerm_container_app_environment.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/container_app_environment) | resource |
| [azurerm_container_app_job.migrate](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/container_app_job) | resource |
| [azurerm_container_app_job.trading_cycle](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/container_app_job) | resource |
| [azurerm_key_vault_secret.dashboard_client_secret](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_role_assignment.token_store_deployer](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/role_assignment) | resource |
| [azurerm_role_assignment.token_store_workload](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/role_assignment) | resource |
| [azurerm_storage_account.token_store](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/storage_account) | resource |
| [azurerm_storage_container.token_store](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/storage_container) | resource |
| [time_sleep.token_store_rbac](https://registry.terraform.io/providers/hashicorp/time/latest/docs/resources/sleep) | resource |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| <a name="input_client_secret_end_date"></a> [client\_secret\_end\_date](#input\_client\_secret\_end\_date) | Expiry of the dashboard's Entra ID client secret. A credential without an expiry is one nobody ever rotates. | `string` | `"2027-09-01T00:00:00Z"` | no |
| <a name="input_cpu"></a> [cpu](#input\_cpu) | vCPU per replica. 0.25 is the smallest Consumption allows. | `number` | `0.25` | no |
| <a name="input_cron_expression"></a> [cron\_expression](#input\_cron\_expression) | Schedule for the trading cycle, in UTC. | `string` | `"*/15 * * * *"` | no |
| <a name="input_dashboard_allowed_principal_ids"></a> [dashboard\_allowed\_principal\_ids](#input\_dashboard\_allowed\_principal\_ids) | Object ids allowed to sign in. Empty means anyone in the tenant, which for a single-user tenant is the same thing stated less precisely. | `list(string)` | `[]` | no |
| <a name="input_dashboard_enabled"></a> [dashboard\_enabled](#input\_dashboard\_enabled) | Create the dashboard Container App. Off until the image exists, for the same reason the jobs are. | `bool` | `true` | no |
| <a name="input_deployer_object_id"></a> [deployer\_object\_id](#input\_deployer\_object\_id) | Owner recorded on the dashboard app registration, so it is never left ownerless. | `string` | n/a | yes |
| <a name="input_environment_variables"></a> [environment\_variables](#input\_environment\_variables) | Plain environment variables passed to every job. | `map(string)` | `{}` | no |
| <a name="input_image"></a> [image](#input\_image) | Fully qualified image reference, including the tag. | `string` | n/a | yes |
| <a name="input_infrastructure_subnet_id"></a> [infrastructure\_subnet\_id](#input\_infrastructure\_subnet\_id) | Subnet the environment is injected into. Must be /23 or larger. | `string` | n/a | yes |
| <a name="input_jobs_enabled"></a> [jobs\_enabled](#input\_jobs\_enabled) | Create the jobs. Off for the first apply against an empty registry, because Azure validates the image manifest at job creation. | `bool` | `true` | no |
| <a name="input_key_vault_id"></a> [key\_vault\_id](#input\_key\_vault\_id) | Vault holding the dashboard's Entra ID client secret. Passed in rather than created here so the module stays free of vault lifecycle. | `string` | n/a | yes |
| <a name="input_location"></a> [location](#input\_location) | Azure region. | `string` | n/a | yes |
| <a name="input_log_analytics_workspace_id"></a> [log\_analytics\_workspace\_id](#input\_log\_analytics\_workspace\_id) | Workspace receiving container stdout. | `string` | n/a | yes |
| <a name="input_memory"></a> [memory](#input\_memory) | Memory per replica. Must pair with cpu at a 1 to 2 ratio. | `string` | `"0.5Gi"` | no |
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Short prefix used in resource names. | `string` | n/a | yes |
| <a name="input_registry_server"></a> [registry\_server](#input\_registry\_server) | Container registry login server. | `string` | n/a | yes |
| <a name="input_replica_timeout_in_seconds"></a> [replica\_timeout\_in\_seconds](#input\_replica\_timeout\_in\_seconds) | Maximum duration of one execution. Must stay well below the schedule interval. | `number` | `600` | no |
| <a name="input_resource_group_name"></a> [resource\_group\_name](#input\_resource\_group\_name) | Resource group that holds the environment and the jobs. | `string` | n/a | yes |
| <a name="input_secret_environment_variables"></a> [secret\_environment\_variables](#input\_secret\_environment\_variables) | Environment variables sourced from a job secret, variable name to secret name. | `map(string)` | `{}` | no |
| <a name="input_secrets"></a> [secrets](#input\_secrets) | Job secrets, secret name to Key Vault versionless secret id. | `map(string)` | `{}` | no |
| <a name="input_tags"></a> [tags](#input\_tags) | Tags applied to every resource. | `map(string)` | n/a | yes |
| <a name="input_tenant_id"></a> [tenant\_id](#input\_tenant\_id) | Entra ID tenant issuing dashboard sign-in tokens. | `string` | n/a | yes |
| <a name="input_token_store_account_name"></a> [token\_store\_account\_name](#input\_token\_store\_account\_name) | Storage account holding dashboard session tokens. Globally unique, lowercase alphanumeric. | `string` | n/a | yes |
| <a name="input_user_assigned_identity_id"></a> [user\_assigned\_identity\_id](#input\_user\_assigned\_identity\_id) | Identity used to pull from the registry and to read Key Vault secrets. | `string` | n/a | yes |
| <a name="input_user_assigned_identity_principal_id"></a> [user\_assigned\_identity\_principal\_id](#input\_user\_assigned\_identity\_principal\_id) | Principal id of the workload identity, needed to grant it access to the token store. | `string` | n/a | yes |
| <a name="input_workload_profile_name"></a> [workload\_profile\_name](#input\_workload\_profile\_name) | Workload profile the jobs run on. Consumption is what a Consumption-only environment assigns. | `string` | `"Consumption"` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| <a name="output_dashboard_client_id"></a> [dashboard\_client\_id](#output\_dashboard\_client\_id) | Entra ID application users sign in to. |
| <a name="output_dashboard_fqdn"></a> [dashboard\_fqdn](#output\_dashboard\_fqdn) | Public host name of the dashboard. Null when the dashboard is disabled. |
| <a name="output_dashboard_name"></a> [dashboard\_name](#output\_dashboard\_name) | Dashboard Container App name. |
| <a name="output_environment_default_domain"></a> [environment\_default\_domain](#output\_environment\_default\_domain) | Default domain of the environment, used later by the dashboard ingress. |
| <a name="output_environment_id"></a> [environment\_id](#output\_environment\_id) | Container Apps environment resource id. |
| <a name="output_migrate_job_name"></a> [migrate\_job\_name](#output\_migrate\_job\_name) | Manually triggered job running Alembic migrations. |
| <a name="output_trading_cycle_job_name"></a> [trading\_cycle\_job\_name](#output\_trading\_cycle\_job\_name) | Scheduled job running one trading cycle. |
<!-- END_TF_DOCS -->
