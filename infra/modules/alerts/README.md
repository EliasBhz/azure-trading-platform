# alerts

Alerts and a versioned workbook, both querying the structured logs the bot emits itself rather than a platform schema Azure can change. See ADR-0012.

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
| [azurerm_application_insights_workbook.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/application_insights_workbook) | resource |
| [azurerm_monitor_action_group.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/monitor_action_group) | resource |
| [azurerm_monitor_scheduled_query_rules_alert_v2.cycle_failed](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/monitor_scheduled_query_rules_alert_v2) | resource |
| [azurerm_monitor_scheduled_query_rules_alert_v2.drawdown](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/monitor_scheduled_query_rules_alert_v2) | resource |
| [azurerm_monitor_scheduled_query_rules_alert_v2.no_cycle](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/monitor_scheduled_query_rules_alert_v2) | resource |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| <a name="input_action_group_short_name"></a> [action\_group\_short\_name](#input\_action\_group\_short\_name) | Short name shown in notifications. Twelve characters maximum. | `string` | `"tradingbot"` | no |
| <a name="input_contact_emails"></a> [contact\_emails](#input\_contact\_emails) | Addresses notified. Empty by default so no address is committed to a public repository; alerts still fire and remain visible in the portal. | `list(string)` | `[]` | no |
| <a name="input_drawdown_alert_ratio"></a> [drawdown\_alert\_ratio](#input\_drawdown\_alert\_ratio) | Intraday drawdown that raises an alert, as a fraction of the day's opening equity. | `number` | `0.05` | no |
| <a name="input_location"></a> [location](#input\_location) | Azure region. | `string` | n/a | yes |
| <a name="input_log_analytics_workspace_id"></a> [log\_analytics\_workspace\_id](#input\_log\_analytics\_workspace\_id) | Workspace the alert queries run against. | `string` | n/a | yes |
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Short prefix used in resource names. | `string` | n/a | yes |
| <a name="input_no_cycle_window"></a> [no\_cycle\_window](#input\_no\_cycle\_window) | How long the bot may be silent before the alert fires. Three missed cycles at a fifteen minute cadence. | `string` | `"PT45M"` | no |
| <a name="input_resource_group_name"></a> [resource\_group\_name](#input\_resource\_group\_name) | Resource group that holds the alerts and the workbook. | `string` | n/a | yes |
| <a name="input_tags"></a> [tags](#input\_tags) | Tags applied to every resource. | `map(string)` | n/a | yes |
| <a name="input_workbook_uuid"></a> [workbook\_uuid](#input\_workbook\_uuid) | Workbook name, which Azure requires to be a GUID. Fixed in configuration so redeploying updates the same workbook instead of creating another. | `string` | `"6f1a4c2e-9b73-4d58-a0e1-2c7d5f8b3a49"` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| <a name="output_action_group_id"></a> [action\_group\_id](#output\_action\_group\_id) | Action group every alert in this module notifies. |
| <a name="output_alert_names"></a> [alert\_names](#output\_alert\_names) | The alert rules created, for the runbook to reference by name. |
| <a name="output_workbook_id"></a> [workbook\_id](#output\_workbook\_id) | Versioned workbook resource id. |
<!-- END_TF_DOCS -->
