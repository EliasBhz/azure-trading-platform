output "action_group_id" {
  description = "Action group every alert in this module notifies."
  value       = azurerm_monitor_action_group.this.id
}

output "alert_names" {
  description = "The alert rules created, for the runbook to reference by name."
  value = [
    azurerm_monitor_scheduled_query_rules_alert_v2.cycle_failed.name,
    azurerm_monitor_scheduled_query_rules_alert_v2.no_cycle.name,
    azurerm_monitor_scheduled_query_rules_alert_v2.drawdown.name,
  ]
}

output "workbook_id" {
  description = "Versioned workbook resource id."
  value       = azurerm_application_insights_workbook.this.id
}
