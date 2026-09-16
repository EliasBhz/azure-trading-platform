output "budget_id" {
  description = "Subscription budget resource id."
  value       = azurerm_consumption_budget_subscription.monthly.id
}

output "monthly_budget_amount" {
  description = "Monthly ceiling the budget alerts on."
  value       = azurerm_consumption_budget_subscription.monthly.amount
}

output "automation_account_name" {
  description = "Automation account running the cost guard runbook."
  value       = azurerm_automation_account.cost_guard.name
}

output "runbook_name" {
  description = "Runbook started when the budget is reached."
  value       = azurerm_automation_runbook.stop_cost_drivers.name
}

output "cost_guard_role_name" {
  description = "Custom role the automation holds. It can read and stop PostgreSQL Flexible Servers and nothing else."
  value       = azurerm_role_definition.cost_guard.name
}
