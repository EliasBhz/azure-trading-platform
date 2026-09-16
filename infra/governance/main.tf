data "azurerm_subscription" "current" {}

# A subscription-scoped budget, separate from the resource group budget the dev
# environment carries.
#
# The resource group budget cannot see everything. Container Apps creates its
# own managed environment resource group outside the one this project declares,
# named ME_<environment>_<resource group>_<region>, and its cost lands there. A
# budget scoped to the project's resource group is blind to it, and so is blind
# to any resource created outside Terraform.
#
# This stack is deliberately not part of the dev environment: destroying the
# environment must not remove the thing that watches spending.
resource "azurerm_consumption_budget_subscription" "monthly" {
  name            = var.budget_name
  subscription_id = data.azurerm_subscription.current.id
  amount          = var.monthly_budget_amount
  time_grain      = "Monthly"

  time_period {
    start_date = var.budget_start_date
    end_date   = var.budget_end_date
  }

  # Early warnings notify people and nothing else.
  dynamic "notification" {
    for_each = var.warning_alert_thresholds
    content {
      enabled        = true
      threshold      = notification.value
      operator       = "GreaterThanOrEqualTo"
      threshold_type = "Actual"
      contact_roles  = var.contact_roles
      contact_emails = var.contact_emails
    }
  }

  # Reaching the ceiling on money already spent is the only condition that
  # triggers the automation. A forecast is a guess, and a guess must not stop a
  # database.
  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Actual"
    contact_roles  = var.contact_roles
    contact_emails = var.contact_emails
    contact_groups = [azurerm_monitor_action_group.cost_guard.id]
  }

  # Forecast alerts are noisy on a resource group whose cost is dominated by one
  # burstable database: they fire on the first day of the period and get
  # ignored. At subscription scope over a full month the forecast is stable
  # enough to be worth acting on, and it is the only alert that arrives before
  # the money is already spent.
  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThan"
    threshold_type = "Forecasted"
    contact_roles  = var.contact_roles
    contact_emails = var.contact_emails
  }

  lifecycle {
    # Azure rewrites the start date to the beginning of the current period, so
    # comparing it with a literal produces a diff on every plan.
    ignore_changes = [time_period[0].start_date]
  }
}
