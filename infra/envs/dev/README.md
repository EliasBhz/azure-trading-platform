# dev environment

Everything the platform needs, in one resource group, in North Europe.

## Prerequisites

`infra/bootstrap` must have been applied: this stack's backend lives in the
storage account it creates. Authentication is Entra ID, so `az login` is the
only credential step and there is no access key to export.

## Usage

    cd infra/envs/dev
    terraform init
    terraform plan  -var subscription_id=<SUBSCRIPTION_ID> -out tfplan
    terraform apply tfplan

## First deployment is necessarily two passes

Azure validates the image manifest when a Container Apps Job is created and
returns `MANIFEST_UNKNOWN` if the tag does not exist. The registry is created by
this stack, so on an empty subscription the order is:

1. `terraform apply` — fails on the two jobs, creates everything else
2. `az acr login --name $(terraform output -raw registry_name)`
3. build and push `$(terraform output -raw image_reference)`
4. `terraform apply` again — creates the jobs

This is a property of the platform, not of this configuration. Phase 4 removes
the manual step by pushing the image from CI before applying.

## Running the jobs

The database has no public endpoint, so migrations run inside the VNet:

    az containerapp job start -n $(terraform output -raw migrate_job_name) -g $(terraform output -raw resource_group_name)
    az containerapp job start -n $(terraform output -raw trading_cycle_job_name) -g $(terraform output -raw resource_group_name)

Logs land in Log Analytics as JSON:

    az monitor log-analytics query \
      --workspace <WORKSPACE_GUID> \
      --analytics-query "ContainerAppConsoleLogs_CL | where ContainerName_s == 'trading-cycle' | order by TimeGenerated desc | take 20"

## Cost

PostgreSQL dominates. Verify current prices on the Azure Pricing Calculator
before trusting any number here; these are orders of magnitude, not a quote.

| Resource | Monthly |
|---|---|
| PostgreSQL Flexible Server B1ms plus 32 GB | the dominant line |
| Container Registry, Basic | fixed and small |
| Log Analytics and Application Insights | capped at 1 GB per day |
| Container Apps jobs | effectively nothing at this cadence |
| VNet, NSGs, private DNS, Key Vault | negligible |

The budget on the resource group alerts at 50, 80 and 100 percent. **A budget
alerts, it does not stop anything.** The only control that actually caps spend
is destroying the environment:

    az monitor action-group delete -g rg-tradingbot-dev-neu -n "Application Insights Smart Detection"
    terraform destroy -var subscription_id=<SUBSCRIPTION_ID>

The first line is not optional. Azure creates that action group by itself
alongside Application Insights, Terraform does not know about it, and the
provider runs with `prevent_deletion_if_contains_resources = true`. The destroy
therefore removes all 35 resources and then refuses to delete the resource
group, because from its point of view the group still contains something a human
might have put there.

Turning the guard off would make destroy a single command at the cost of
silently deleting anything created outside Terraform in that group. Keeping it
and deleting the one known artefact explicitly is the safer trade, and it is the
reason this is written down rather than rediscovered during the next teardown.

Stopping the database instead keeps the data and drops the compute charge for up
to seven days:

    az postgres flexible-server stop -g <RG> -n <SERVER>

## Two settings that look like noise and are not

`public_network_access_enabled = false` on the server is mandatory, not
cosmetic: the provider sends `true` by default and Azure rejects the
combination with `ConflictingPublicNetworkAccessAndVirtualNetworkConfiguration`.

`workload_profile_name = "Consumption"` on the jobs is set explicitly because
Azure assigns it on creation. Leaving it out makes every later plan propose
clearing it, which is drift that never converges.

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

## Modules

| Name | Source | Version |
| ---- | ------ | ------- |
| <a name="module_acr"></a> [acr](#module\_acr) | ../../modules/acr | n/a |
| <a name="module_alerts"></a> [alerts](#module\_alerts) | ../../modules/alerts | n/a |
| <a name="module_container_apps"></a> [container\_apps](#module\_container\_apps) | ../../modules/container_apps | n/a |
| <a name="module_keyvault"></a> [keyvault](#module\_keyvault) | ../../modules/keyvault | n/a |
| <a name="module_network"></a> [network](#module\_network) | ../../modules/network | n/a |
| <a name="module_observability"></a> [observability](#module\_observability) | ../../modules/observability | n/a |
| <a name="module_postgres"></a> [postgres](#module\_postgres) | ../../modules/postgres | n/a |

## Resources

| Name | Type |
| ---- | ---- |
| [azurerm_consumption_budget_resource_group.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/consumption_budget_resource_group) | resource |
| [azurerm_resource_group.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/resource_group) | resource |
| [azurerm_user_assigned_identity.workload](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/user_assigned_identity) | resource |
| [random_password.postgres_admin](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/password) | resource |
| [random_string.suffix](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/string) | resource |
| [azurerm_client_config.current](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/data-sources/client_config) | data source |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| <a name="input_acr_push_principal_ids"></a> [acr\_push\_principal\_ids](#input\_acr\_push\_principal\_ids) | Principals granted AcrPush on the registry, keyed by a readable name. The deployment identity, never the workload identity. | `map(string)` | <pre>{<br/>  "cicd": "76975942-91f3-467b-9b18-9fbf5eb3208e"<br/>}</pre> | no |
| <a name="input_alert_contact_emails"></a> [alert\_contact\_emails](#input\_alert\_contact\_emails) | Addresses notified by the alerts. Empty by default so no address is committed to a public repository. | `list(string)` | `[]` | no |
| <a name="input_budget_alert_thresholds"></a> [budget\_alert\_thresholds](#input\_budget\_alert\_thresholds) | Percentages of the budget that raise an alert. | `list(number)` | <pre>[<br/>  50,<br/>  80,<br/>  100<br/>]</pre> | no |
| <a name="input_budget_end_date"></a> [budget\_end\_date](#input\_budget\_end\_date) | End of the budget period. | `string` | `"2030-01-01T00:00:00Z"` | no |
| <a name="input_budget_start_date"></a> [budget\_start\_date](#input\_budget\_start\_date) | First day of the budget period. Azure requires the first of a month. | `string` | `"2026-09-01T00:00:00Z"` | no |
| <a name="input_cost_center"></a> [cost\_center](#input\_cost\_center) | Value of the mandatory cost-center tag. | `string` | `"personal"` | no |
| <a name="input_cron_expression"></a> [cron\_expression](#input\_cron\_expression) | Trading cycle schedule, in UTC. | `string` | `"*/15 * * * *"` | no |
| <a name="input_drawdown_alert_ratio"></a> [drawdown\_alert\_ratio](#input\_drawdown\_alert\_ratio) | Intraday drawdown that raises an alert, as a fraction of the day's opening equity. | `number` | `0.05` | no |
| <a name="input_environment"></a> [environment](#input\_environment) | Environment name, also used as the env tag. | `string` | `"dev"` | no |
| <a name="input_exchange_backend"></a> [exchange\_backend](#input\_exchange\_backend) | simulated or ccxt\_sandbox. There is no third option. | `string` | `"simulated"` | no |
| <a name="input_image_repository"></a> [image\_repository](#input\_image\_repository) | Repository holding the bot image inside the registry. | `string` | `"trading-bot"` | no |
| <a name="input_image_tag"></a> [image\_tag](#input\_image\_tag) | Image tag the jobs run. CI replaces this with the commit SHA. | `string` | `"bootstrap"` | no |
| <a name="input_jobs_enabled"></a> [jobs\_enabled](#input\_jobs\_enabled) | Create the Container Apps jobs. The deployment pipeline sets this to false on the apply that precedes pushing the image, because Azure validates the image manifest when a job is created. | `bool` | `true` | no |
| <a name="input_location"></a> [location](#input\_location) | Azure region. | `string` | `"northeurope"` | no |
| <a name="input_log_daily_quota_gb"></a> [log\_daily\_quota\_gb](#input\_log\_daily\_quota\_gb) | Hard daily ingestion cap on the workspace. | `number` | `1` | no |
| <a name="input_log_level"></a> [log\_level](#input\_log\_level) | Bot log level. | `string` | `"INFO"` | no |
| <a name="input_log_retention_in_days"></a> [log\_retention\_in\_days](#input\_log\_retention\_in\_days) | Log Analytics retention. | `number` | `30` | no |
| <a name="input_monthly_budget_amount"></a> [monthly\_budget\_amount](#input\_monthly\_budget\_amount) | Monthly budget for the resource group, in the billing currency. | `number` | `15` | no |
| <a name="input_no_cycle_window"></a> [no\_cycle\_window](#input\_no\_cycle\_window) | How long the bot may be silent before the alert fires. Must stay consistent with the cron schedule. | `string` | `"PT45M"` | no |
| <a name="input_owner"></a> [owner](#input\_owner) | Value of the mandatory owner tag. | `string` | `"eliasbaghazou"` | no |
| <a name="input_project_short_name"></a> [project\_short\_name](#input\_project\_short\_name) | Short project name used to build resource names. | `string` | `"tradingbot"` | no |
| <a name="input_resource_group_name"></a> [resource\_group\_name](#input\_resource\_group\_name) | Single resource group holding the whole environment. | `string` | `"rg-tradingbot-dev-neu"` | no |
| <a name="input_secret_writer_principal_ids"></a> [secret\_writer\_principal\_ids](#input\_secret\_writer\_principal\_ids) | Identities besides the caller that may write Key Vault secrets. The pipeline is listed so a local plan does not propose removing its access. | `map(string)` | <pre>{<br/>  "cicd": "76975942-91f3-467b-9b18-9fbf5eb3208e"<br/>}</pre> | no |
| <a name="input_subscription_id"></a> [subscription\_id](#input\_subscription\_id) | Azure subscription the environment is deployed into. | `string` | n/a | yes |
| <a name="input_symbol"></a> [symbol](#input\_symbol) | Traded pair. | `string` | `"BTC/USDT"` | no |
| <a name="input_timeframe"></a> [timeframe](#input\_timeframe) | Candle timeframe. Must be consistent with the cron schedule. | `string` | `"15m"` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| <a name="output_alert_names"></a> [alert\_names](#output\_alert\_names) | Alert rules watching the bot. |
| <a name="output_image_reference"></a> [image\_reference](#output\_image\_reference) | Image the jobs expect. Build and push this before running them. |
| <a name="output_key_vault_name"></a> [key\_vault\_name](#output\_key\_vault\_name) | Key Vault name. |
| <a name="output_key_vault_uri"></a> [key\_vault\_uri](#output\_key\_vault\_uri) | Key Vault URI. |
| <a name="output_migrate_job_name"></a> [migrate\_job\_name](#output\_migrate\_job\_name) | Manually triggered job running Alembic migrations. |
| <a name="output_postgres_fqdn"></a> [postgres\_fqdn](#output\_postgres\_fqdn) | Database FQDN. Resolves only inside the VNet. |
| <a name="output_registry_login_server"></a> [registry\_login\_server](#output\_registry\_login\_server) | Registry host name. Used to tag and push the bot image. |
| <a name="output_registry_name"></a> [registry\_name](#output\_registry\_name) | Registry name, for az acr login. |
| <a name="output_resource_group_name"></a> [resource\_group\_name](#output\_resource\_group\_name) | Resource group holding the environment. |
| <a name="output_trading_cycle_job_name"></a> [trading\_cycle\_job\_name](#output\_trading\_cycle\_job\_name) | Scheduled job running one trading cycle. |
| <a name="output_workbook_id"></a> [workbook\_id](#output\_workbook\_id) | Versioned Azure Workbook showing equity, drawdown, decisions and failures. |
| <a name="output_workload_identity_client_id"></a> [workload\_identity\_client\_id](#output\_workload\_identity\_client\_id) | Client id of the identity the jobs run as. |
<!-- END_TF_DOCS -->
