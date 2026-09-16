# Governance

Watches what the subscription spends, and stops the expensive part when the
ceiling is reached.

Deliberately separate from `infra/envs/dev`: destroying the environment must not
remove the thing that watches spending.

## What it creates

| Resource | Purpose |
|---|---|
| Subscription budget | Alerts at 50 and 80 percent; at 100 percent it also starts the runbook |
| Automation account | Runs the runbook, with a system-assigned identity |
| Custom role | Read and stop PostgreSQL Flexible Servers, nothing else |
| Runbook, webhook, action group | The chain from a budget alert to a stopped server |

## The chain

    actual spend >= 100 percent of the budget
      -> budget notification
      -> action group
      -> webhook
      -> runbook Stop-CostDrivers
      -> PostgreSQL servers tagged project=azure-trading-platform are stopped

Only the 100 percent threshold on **actual** spend starts the automation. The
forecast alert is informational: a forecast is an estimate, and an estimate must
not stop a database.

## An Azure budget is not a spending limit

This is the part people get wrong, so it is written first. **A budget alerts. It
does not cap anything.** There is no setting on a Pay-As-You-Go subscription
that stops charges at an amount. The spending limit that genuinely cut service
exists only on credit-based offers.

This stack is the closest honest approximation, and it still has real gaps:

- **Latency.** Azure rates consumption eight to twenty-four hours late, so the
  threshold fires after the money is spent. The overshoot is bounded by roughly
  one day of consumption.
- **Seven days.** Azure restarts a stopped Flexible Server by itself after seven
  days. This buys time and makes the spend visible; it is not a permanent
  ceiling.
- **Only PostgreSQL.** Container Apps, the registry and Log Analytics keep
  running. They are negligible next to the database, and stopping them would
  need far broader permissions.

## Why the automation stops rather than deletes

Stopping is reversible and keeps the data. Deleting would also desynchronise the
Terraform state, turning a cost incident into an infrastructure incident.

## Why a custom role

`Contributor` would have worked, and would have meant that a budget alert is
able to delete the environment. Three lines of role definition turn "the
automation is trusted" into "the automation is incapable of anything worse":

    Microsoft.Resources/subscriptions/resourceGroups/read
    Microsoft.DBforPostgreSQL/flexibleServers/read
    Microsoft.DBforPostgreSQL/flexibleServers/stop/action

Servers are matched by the `project` tag, never by name, so a server created
later is covered without editing the script and a server belonging to something
else is never touched.

## Usage

    cd infra/governance
    terraform init
    terraform plan  -var subscription_id=<SUBSCRIPTION_ID> -out tfplan
    terraform apply tfplan

## Testing it without spending money

Start the runbook by hand. With no server to stop it exercises everything that
matters: managed identity sign-in, the custom role, and the ARM calls.

    az automation runbook start \
      --automation-account-name aa-tradingbot-cost-guard \
      --resource-group rg-tradingbot-governance-neu \
      --name Stop-CostDrivers

    az automation job show \
      --automation-account-name aa-tradingbot-cost-guard \
      --resource-group rg-tradingbot-governance-neu \
      --job-name <JOB_ID> --query status -o tsv

Reading the output needs the REST API; the CLI does not expose it:

    az rest --method get --url "https://management.azure.com/subscriptions/<SUB>/resourceGroups/rg-tradingbot-governance-neu/providers/Microsoft.Automation/automationAccounts/aa-tradingbot-cost-guard/jobs/<JOB_ID>/output?api-version=2019-06-01"

## Cost

Zero. An Automation account includes 500 free job minutes a month and this
runbook takes seconds. Budgets, action groups and role definitions are free.

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.9.0 |
| <a name="requirement_azurerm"></a> [azurerm](#requirement\_azurerm) | ~> 4.0 |

## Providers

| Name | Version |
| ---- | ------- |
| <a name="provider_azurerm"></a> [azurerm](#provider\_azurerm) | ~> 4.0 |

## Modules

No modules.

## Resources

| Name | Type |
| ---- | ---- |
| [azurerm_automation_account.cost_guard](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/automation_account) | resource |
| [azurerm_automation_runbook.stop_cost_drivers](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/automation_runbook) | resource |
| [azurerm_automation_webhook.stop_cost_drivers](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/automation_webhook) | resource |
| [azurerm_consumption_budget_subscription.monthly](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/consumption_budget_subscription) | resource |
| [azurerm_monitor_action_group.cost_guard](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/monitor_action_group) | resource |
| [azurerm_resource_group.governance](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/resource_group) | resource |
| [azurerm_role_assignment.cost_guard](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/role_assignment) | resource |
| [azurerm_role_definition.cost_guard](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/role_definition) | resource |
| [azurerm_subscription.current](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/data-sources/subscription) | data source |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| <a name="input_budget_end_date"></a> [budget\_end\_date](#input\_budget\_end\_date) | End of the budget period. | `string` | `"2030-01-01T00:00:00Z"` | no |
| <a name="input_budget_name"></a> [budget\_name](#input\_budget\_name) | Budget name, visible in Cost Management. | `string` | `"budget-subscription-monthly"` | no |
| <a name="input_budget_start_date"></a> [budget\_start\_date](#input\_budget\_start\_date) | First day of the budget period. Azure requires the first of a month. | `string` | `"2026-09-01T00:00:00Z"` | no |
| <a name="input_contact_emails"></a> [contact\_emails](#input\_contact\_emails) | Extra addresses notified. Empty by default so no address is committed to a public repository. | `list(string)` | `[]` | no |
| <a name="input_contact_roles"></a> [contact\_roles](#input\_contact\_roles) | Subscription roles notified. Owner reaches whoever holds the subscription without hardcoding an address. | `list(string)` | <pre>[<br/>  "Owner"<br/>]</pre> | no |
| <a name="input_location"></a> [location](#input\_location) | Azure region for the governance resources. | `string` | `"northeurope"` | no |
| <a name="input_monthly_budget_amount"></a> [monthly\_budget\_amount](#input\_monthly\_budget\_amount) | Monthly ceiling in the billing currency. This alerts; it does not stop anything. | `number` | `50` | no |
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Short prefix used in resource names. | `string` | `"tradingbot"` | no |
| <a name="input_project_tag"></a> [project\_tag](#input\_project\_tag) | Value of the project tag the automation matches. A server without it is never touched. | `string` | `"azure-trading-platform"` | no |
| <a name="input_resource_group_name"></a> [resource\_group\_name](#input\_resource\_group\_name) | Resource group holding the budget automation. Separate from the environment so that destroying the environment does not remove what watches spending. | `string` | `"rg-tradingbot-governance-neu"` | no |
| <a name="input_subscription_id"></a> [subscription\_id](#input\_subscription\_id) | Azure subscription the budget watches. | `string` | n/a | yes |
| <a name="input_tags"></a> [tags](#input\_tags) | Tags applied to every resource. | `map(string)` | <pre>{<br/>  "component": "governance",<br/>  "cost-center": "personal",<br/>  "env": "shared",<br/>  "owner": "eliasbaghazou",<br/>  "project": "azure-trading-platform"<br/>}</pre> | no |
| <a name="input_warning_alert_thresholds"></a> [warning\_alert\_thresholds](#input\_warning\_alert\_thresholds) | Percentages that warn people. The 100 percent threshold is declared separately because it also starts the automation. | `list(number)` | <pre>[<br/>  50,<br/>  80<br/>]</pre> | no |
| <a name="input_webhook_expiry_time"></a> [webhook\_expiry\_time](#input\_webhook\_expiry\_time) | Expiry of the webhook the action group calls. Azure refuses a webhook without one, so it has to be renewed deliberately rather than living forever. | `string` | `"2030-01-01T00:00:00Z"` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| <a name="output_automation_account_name"></a> [automation\_account\_name](#output\_automation\_account\_name) | Automation account running the cost guard runbook. |
| <a name="output_budget_id"></a> [budget\_id](#output\_budget\_id) | Subscription budget resource id. |
| <a name="output_cost_guard_role_name"></a> [cost\_guard\_role\_name](#output\_cost\_guard\_role\_name) | Custom role the automation holds. It can read and stop PostgreSQL Flexible Servers and nothing else. |
| <a name="output_monthly_budget_amount"></a> [monthly\_budget\_amount](#output\_monthly\_budget\_amount) | Monthly ceiling the budget alerts on. |
| <a name="output_runbook_name"></a> [runbook\_name](#output\_runbook\_name) | Runbook started when the budget is reached. |
<!-- END_TF_DOCS -->
